"""Invernadero IoT. Python 3.11+, SQLite local o PostgreSQL en Compose."""
import csv, datetime as dt, hashlib, hmac, json, math, os, random, sqlite3, threading, time, uuid
import weather_adapter
import groq_adapter
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT=Path(__file__).parent
LOCK=threading.RLock()
TOKEN=os.getenv('ADMIN_TOKEN','local-demo-cambiar')
SEEDING=False
WAKE={}
if os.getenv('DATABASE_URL'):
    import psycopg
    DB=psycopg.connect(os.environ['DATABASE_URL'],autocommit=True)
    def query(sql,args=()): return DB.execute(sql.replace('?','%s'),args)
else:
    DB=sqlite3.connect(os.getenv('DB_PATH',str(ROOT/'iot.db')),check_same_thread=False)
    def query(sql,args=()):
        cur=DB.execute(sql,args)
        if not SEEDING: DB.commit()
        return cur

DEVICES=[{'id':f'D{i:02}', 'zone':('Norte' if i%2 else 'Sur'),
 'source':('digital_twin' if i<=6 else 'api_fixture' if i<=8 else 'dataset_synthetic'),
 'hardware_ready':i<=2} for i in range(1,11)]
RANGES={'temperature':(0,60,'°C'),'humidity':(0,100,'%'), 'soil':(0,100,'%'), 'light':(0,100000,'lux')}

def init():
    query('CREATE TABLE IF NOT EXISTS readings(device TEXT, ts TEXT, variable TEXT, value REAL, source TEXT, PRIMARY KEY(device,ts,variable))')
    query('CREATE TABLE IF NOT EXISTS state(device TEXT PRIMARY KEY, enabled INTEGER, offset REAL, interval_s INTEGER)')
    query('CREATE TABLE IF NOT EXISTS commands(id TEXT PRIMARY KEY, device TEXT, ts TEXT, payload TEXT, status TEXT)')
    query('CREATE TABLE IF NOT EXISTS irrigation(id TEXT PRIMARY KEY, device TEXT, ts TEXT, amount_ml REAL)')
    for d in DEVICES:
        query('INSERT INTO state VALUES (?,1,0,60) ON CONFLICT(device) DO NOTHING',(d['id'],))

def ingest(device,ts,values,source):
    if device not in {d['id'] for d in DEVICES}: raise ValueError('Dispositivo desconocido')
    stamp=dt.datetime.fromisoformat(ts.replace('Z','+00:00'))
    if stamp.tzinfo is None: raise ValueError('timestamp sin zona')
    ts=stamp.astimezone(dt.timezone.utc).isoformat()
    if set(values)!=set(RANGES): raise ValueError('Se requieren cuatro variables')
    for k,v in values.items():
        lo,hi,_=RANGES[k]
        if not isinstance(v,(float,int)) or not math.isfinite(v) or not lo<=v<=hi: raise ValueError('Valor fuera de rango: '+k)
    with LOCK:
        for k,v in values.items():
            query('INSERT INTO readings VALUES (?,?,?,?,?) ON CONFLICT(device,ts,variable) DO NOTHING',(device,ts,k,v,source))

def seed():
    global SEEDING
    SEEDING=True
    rng=random.Random(42)
    start=dt.datetime(2026,10,26,tzinfo=dt.timezone.utc)
    for n in range(1440):
        t=start+dt.timedelta(minutes=5*n); hour=t.hour+t.minute/60
        for i,d in enumerate(DEVICES):
            sun=max(0,math.sin(math.pi*(hour-6)/12))
            hot=5 if d['id']=='D03' and 720<=n<756 else 0
            vals={'temperature':round(19+10*sun+i*.15+hot+rng.gauss(0,.3),2),
             'humidity':round(78-22*sun+rng.gauss(0,1),2),
             'soil':round(65-(n%144)*.22+i*.2+rng.gauss(0,.4),2),
             'light':round(45000*sun+rng.uniform(0,150),2)}
            ingest(d['id'],t.isoformat(),vals,d['source'])
    DB.commit()
    SEEDING=False
    export()

def export():
    with open(ROOT/'data'/'telemetry.csv','w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['device','ts','variable','value','source'])
        w.writerows(query('SELECT * FROM readings ORDER BY ts,device,variable').fetchall())

def command(device,body,cid=None):
    if device not in {d['id'] for d in DEVICES}: raise ValueError('Dispositivo desconocido')
    if not body or set(body)-{'enabled','offset','interval_s','irrigation_ml'}: raise ValueError('Comando no permitido')
    if 'irrigation_ml' in body and (set(body)!={'irrigation_ml'} or type(body['irrigation_ml']) is not int or not 50<=body['irrigation_ml']<=1000): raise ValueError('Riego separado: 50 a 1000 ml')
    if 'enabled' in body and type(body['enabled']) is not bool: raise ValueError('enabled debe ser booleano')
    if 'offset' in body and (type(body['offset']) not in (int,float) or not math.isfinite(body['offset']) or abs(body['offset'])>5): raise ValueError('offset: -5 a 5 °C')
    if 'interval_s' in body and (type(body['interval_s']) is not int or not 5<=body['interval_s']<=3600): raise ValueError('interval_s: 5 a 3600')
    cid=cid or str(uuid.uuid4())
    with LOCK:
        old=query('SELECT device,payload FROM commands WHERE id=?',(cid,)).fetchone()
        if old:
            if old!=(device,json.dumps(body,sort_keys=True)): raise ValueError('ID reutilizado con otro comando')
            return cid
        row=query('SELECT enabled,offset,interval_s FROM state WHERE device=?',(device,)).fetchone()
        if 'irrigation_ml' in body:
            latest=query("SELECT ts,value,source FROM readings WHERE device=? AND variable='soil' ORDER BY ts DESC LIMIT 1",(device,)).fetchone()
            now=dt.datetime.now(dt.timezone.utc)
            if not row[0]: raise ValueError('Activa la publicación del gemelo antes de regar')
            if not latest or latest[2]!='live_simulated' or (now-dt.datetime.fromisoformat(latest[0])).total_seconds()>600: raise ValueError('Se requiere una lectura simulada reciente (menos de 10 min)')
            if latest[1]>=85: raise ValueError('Suelo por encima de 85 %; no se aplicará más riego')
            last=query('SELECT ts FROM irrigation WHERE device=? ORDER BY ts DESC LIMIT 1',(device,)).fetchone()
            if last and (now-dt.datetime.fromisoformat(last[0])).total_seconds()<600: raise ValueError('Espera 10 minutos entre riegos del mismo gemelo')
            query('INSERT INTO irrigation VALUES (?,?,?,?)',(cid,device,now.isoformat(),body['irrigation_ml']))
        query('UPDATE state SET enabled=?,offset=?,interval_s=? WHERE device=?',
         (int(body.get('enabled',bool(row[0]))),body.get('offset',row[1]),body.get('interval_s',row[2]),device))
        query('INSERT INTO commands VALUES (?,?,?,?,?)',(cid,device,dt.datetime.now(dt.timezone.utc).isoformat(),json.dumps(body,sort_keys=True),'applied_twin'))
        WAKE[device]=time.time()
    return cid

def forecast(samples):
    """Extrapolación local: sólo una hora homogénea, 6 puntos y 20 min."""
    if len(samples)<6: return None
    stamps=[dt.datetime.fromisoformat(t).timestamp()/3600 for t,_ in samples]
    if stamps[-1]-stamps[0]<1/3: return None
    xs=[t-stamps[-1] for t in stamps];ys=[v for _,v in samples]
    mx=sum(xs)/len(xs);my=sum(ys)/len(ys)
    denom=sum((x-mx)**2 for x in xs)
    slope=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/denom if denom else 0
    if abs(slope)>5: return None
    return {'slope_per_hour':round(slope,3),'in_6h':round(max(0,min(100,ys[-1]+slope*6)),1),'samples':len(samples),'hours_to_40':round((ys[-1]-40)/-slope,1) if slope<-.05 and ys[-1]>40 else None}

def insights():
    now=dt.datetime.now(dt.timezone.utc);nodes=[]
    with LOCK:
        for d in DEVICES:
            device=d['id']; latest=query("SELECT ts,value,source FROM readings WHERE device=? AND variable='soil' ORDER BY ts DESC LIMIT 1",(device,)).fetchone()
            last=query('SELECT ts,amount_ml FROM irrigation WHERE device=? ORDER BY ts DESC LIMIT 1',(device,)).fetchone()
            enabled=query('SELECT enabled FROM state WHERE device=?',(device,)).fetchone()[0]
            recent=query("SELECT ts,value,source FROM readings WHERE device=? AND variable='soil' AND ts>=? ORDER BY ts",(device,(now-dt.timedelta(hours=1)).isoformat())).fetchall()
            if last: recent=[r for r in recent if r[0]>=last[0]]
            age=max(0,(now-dt.datetime.fromisoformat(latest[0])).total_seconds()) if latest else None
            fresh=age is not None and age<=600
            pred=forecast([(t,v) for t,v,s in recent]) if fresh and len({s for _,_,s in recent})==1 else None
            soil=latest[1] if latest else None
            status='stale' if not fresh or not enabled else 'dry' if soil<40 else 'watch' if pred and pred['in_6h']<40 else 'ok'
            rec=('Reanuda la adquisición y revisa una lectura reciente.' if status=='stale' else 'Humedad baja: comprueba el sustrato y considera un riego.' if status=='dry' else 'La tendencia podría cruzar el umbral: revisa el suelo antes de regar.' if status=='watch' else 'Humedad dentro del umbral; mantén la observación.')
            cooldown=last is not None and (now-dt.datetime.fromisoformat(last[0])).total_seconds()<600
            nodes.append({**d,'soil':soil,'ts':latest[0] if latest else None,'source':latest[2] if latest else None,'fresh':fresh,'enabled':bool(enabled),'status':status,'forecast':pred,'recommendation':rec,'last_irrigation':{'ts':last[0],'amount_ml':last[1]} if last else None,'can_irrigate':bool(fresh and enabled and latest[2]=='live_simulated' and soil<85 and not cooldown)})
    return {'generated_at':now.isoformat(),'method':'Reglas locales y regresión lineal de la última hora; sin modelo generativo. Estimación orientativa, no validada agronómicamente.','mode':'simulation','nodes':nodes}

def groq_context():
    local=insights();weather=weather_adapter.snapshot()
    for node in local['nodes']:
        with LOCK:temp=query("SELECT ts,value,source FROM readings WHERE device=? AND variable='temperature' ORDER BY ts DESC LIMIT 1",(node['id'],)).fetchone()
        node['temperature']={'ts':temp[0],'value_c':temp[1],'source':temp[2]} if temp else None
    external={}
    for device,node in weather.get('nodes',{}).items():
        v=node.get('values',{})
        external[device]={'status':node.get('status'),'fetched_at':node.get('fetched_at'),'observed_at':v.get('observed_at'),'temperature_c':v.get('temperature_c'),'humidity_pct':v.get('humidity_pct'),'precipitation':v.get('precipitation'),'global_index':v.get('global_index')}
    return {'generated_at':local['generated_at'],'devices':local['nodes'],'external_weather':external,'thresholds':{'soil_low_pct':40,'temperature_high_c':32},'scope':'Riego simulado; ninguna bomba física conectada. No se envían coordenadas ni claves.'}

def live():
    due={}
    previous={}
    rng=random.Random(7)
    while True:
        for d in DEVICES:
            with LOCK: enabled,offset,interval=query('SELECT enabled,offset,interval_s FROM state WHERE device=?',(d['id'],)).fetchone()
            current=(enabled,offset,interval,WAKE.get(d['id']))
            if current!=previous.get(d['id']):
                due[d['id']]=0
                previous[d['id']]=current
            if enabled and time.time()>=due.get(d['id'],0):
                now=dt.datetime.now(dt.timezone.utc)
                sun=max(0,math.sin(math.pi*((now.hour+now.minute/60)-6)/12))
                with LOCK: water=query('SELECT ts,amount_ml FROM irrigation WHERE device=? AND ts>=?',(d['id'],(now-dt.timedelta(hours=12)).isoformat())).fetchall()
                boost=sum(ml/25*max(0,1-(now-dt.datetime.fromisoformat(t)).total_seconds()/43200) for t,ml in water)
                vals={'temperature':round(20+8*sun+offset+rng.random(),2),'humidity':round(75-20*sun,2),'soil':round(min(95,55+boost),2),'light':round(45000*sun,2)}
                ingest(d['id'],now.isoformat(),vals,'live_simulated')
                due[d['id']]=time.time()+interval
        time.sleep(1)

def mqtt_worker():
    import paho.mqtt.client as mqtt
    c=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id='iot-service')
    c.username_pw_set('service',os.environ['MQTT_PASSWORD'])
    def connect(client,userdata,flags,reason,props):
        client.subscribe('greenhouse/+/telemetry',qos=1)
        client.subscribe('greenhouse/+/command',qos=1)
    def receive(client,userdata,msg):
        try:
            _,device,kind=msg.topic.split('/'); b=json.loads(msg.payload)
            if kind=='telemetry': ingest(device,b['ts'],b['values'],'mqtt_external')
            else:
                if abs(time.time()-float(b['issued_at']))>60: raise ValueError('Comando expirado')
                cid=command(device,b['settings'],b['id'])
                client.publish(f'greenhouse/{device}/ack',json.dumps({'id':cid,'status':'applied_twin'}),qos=1)
        except Exception as e: print('MQTT rechazado:',str(e),flush=True)
    c.on_connect=connect; c.on_message=receive
    while True:
        try: c.connect(os.getenv('MQTT_HOST','mosquitto'),1883); c.loop_forever()
        except OSError: time.sleep(5)

class Handler(BaseHTTPRequestHandler):
    def reply(self,status,obj):
        blob=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(blob))); self.end_headers(); self.wfile.write(blob)
    def do_GET(self):
        from urllib.parse import urlparse,parse_qs
        u=urlparse(self.path); p=parse_qs(u.query)
        static={'/':('dashboard.html','text/html'),'/glass.css':('glass.css','text/css'),'/warm-glass.css':('warm-glass.css','text/css'),'/layout.js':('layout.js','application/javascript'),'/greenhouse.jpg':('greenhouse.jpg','image/jpeg'),'/ai.js':('ai.js','application/javascript'),'/ai.css':('ai.css','text/css'),'/weather.js':('weather.js','application/javascript'),'/weather.css':('weather.css','text/css'),'/groq.js':('groq.js','application/javascript'),'/telemetry.js':('telemetry.js','application/javascript')}
        if u.path in static:
            filename,mime=static[u.path]
            blob=(ROOT/filename).read_bytes(); self.send_response(200); self.send_header('Content-Type',mime+'; charset=utf-8'); self.send_header('Cache-Control','no-cache'); self.end_headers(); self.wfile.write(blob); return
        if u.path=='/health': return self.reply(200,{'status':'ok','mode':'simulation'})
        if u.path=='/api/telemetry/status':
            with LOCK:
                r=query("SELECT COUNT(*),MIN(ts),MAX(ts),COUNT(DISTINCT device) FROM readings WHERE source='live_simulated'").fetchone()
                a=query('SELECT device,COUNT(*),MIN(ts),MAX(ts) FROM external_weather GROUP BY device').fetchall()
            return self.reply(200,{'live':{'values':r[0],'first':r[1],'last':r[2],'devices':r[3]},'azure':[{'device':d,'captures':c,'first':f,'last':l} for d,c,f,l in a]})
        if u.path=='/api/devices':
            with LOCK: states=query('SELECT * FROM state ORDER BY device').fetchall()
            return self.reply(200,{'devices':DEVICES,'states':states})
        if u.path=='/api/insights': return self.reply(200,insights())
        if u.path=='/api/weather': return self.reply(200,weather_adapter.snapshot())
        if u.path=='/api/ai/status': return self.reply(200,groq_adapter.status())
        if u.path=='/api/weather/history':
            with LOCK:
                query('CREATE TABLE IF NOT EXISTS external_weather(device TEXT, ts TEXT, payload TEXT, PRIMARY KEY(device,ts))')
                rows=query('SELECT device,ts,payload FROM external_weather WHERE ts>=? ORDER BY ts DESC LIMIT 2000',((dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=5)).isoformat(),)).fetchall()
            return self.reply(200,{'source':'Azure Maps','history':[{'device':d,'fetched_at':t,'values':json.loads(b)} for d,t,b in rows]})
        if u.path=='/api/data':
            device=p.get('device',['D01'])[0]; var=p.get('variable',['temperature'])[0]
            start=p.get('start',['2026-10-26'])[0]; end=p.get('end',['2026-10-31'])[0]
            with LOCK: rows=query('SELECT ts,value FROM readings WHERE device=? AND variable=? AND ts>=? AND ts<? ORDER BY ts LIMIT 10000',(device,var,start,end)).fetchall()
            vs=[r[1] for r in rows]
            return self.reply(200,{'rows':rows,'count':len(vs),'avg':sum(vs)/len(vs) if vs else None,'min':min(vs) if vs else None,'max':max(vs) if vs else None,'alerts':sum(v>32 for v in vs) if var=='temperature' else sum(v<40 for v in vs) if var=='soil' else 0})
        self.reply(404,{'error':'No encontrado'})
    def do_POST(self):
        # Las consultas de IA son de lectura; el control de dispositivos exige token.
        if self.path!='/api/ai/groq' and not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+TOKEN): return self.reply(401,{'error':'Token requerido'})
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=4096: raise ValueError('Tamaño inválido')
            b=json.loads(self.rfile.read(n))
            if not isinstance(b,dict): raise ValueError('Se requiere un objeto JSON')
            if self.path=='/api/ai/groq': return self.reply(200,groq_adapter.analyze(groq_context(),b.get('question','')))
            if self.path=='/api/command': return self.reply(200,{'id':command(b['device'],b['settings'],b.get('id')),'status':'applied_twin'})
            if self.path=='/api/telemetry':
                ingest(b['device'],b['ts'],b['values'],'http_external'); return self.reply(201,{'status':'stored'})
            self.reply(404,{'error':'No encontrado'})
        except (ValueError,KeyError,TypeError) as e: self.reply(400,{'error':str(e)})

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('--seed',action='store_true'); ap.add_argument('--live',action='store_true'); args=ap.parse_args()
    (ROOT/'data').mkdir(exist_ok=True); init()
    if args.seed: seed()
    else:
        threading.Thread(target=weather_adapter.run,args=(query,LOCK),daemon=True).start()
        if args.live: threading.Thread(target=live,daemon=True).start()
        if os.getenv('MQTT_HOST'): threading.Thread(target=mqtt_worker,daemon=True).start()
        ThreadingHTTPServer((os.getenv('BIND_HOST','0.0.0.0'),int(os.getenv('PORT','8080'))),Handler).serve_forever()
