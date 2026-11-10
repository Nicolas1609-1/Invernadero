"""Azure Maps: clave sólo en backend; dos consultas cada 15 minutos."""
import datetime as dt,json,os,threading,time,urllib.request,urllib.parse,urllib.error
from pathlib import Path
STATE={'configured':False,'provider':'Azure Maps','interval_s':900,'nodes':{},'note':'Configura AZURE_MAPS_KEY en el archivo .env del servidor.'}
STATE_LOCK=threading.RLock()
PATHS={'API-WEATHER':'/weather/currentConditions/json','API-AIR':'/weather/airQuality/current/json'}
def config():
    env={}
    path=Path(__file__).parent/'.env'
    if path.exists():
        for line in path.read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                k,v=line.split('=',1);env[k.strip()]=v.strip().strip('\"\'')
    key=env.get('AZURE_MAPS_KEY') or os.getenv('AZURE_MAPS_KEY','')
    lat=float(env.get('WEATHER_LAT') or os.getenv('WEATHER_LAT','7.11703'))
    lon=float(env.get('WEATHER_LON') or os.getenv('WEATHER_LON','-73.10534'))
    if not -90<=lat<=90 or not -180<=lon<=180:raise ValueError('Coordenadas inválidas')
    return key,f'{lat},{lon}'
def normalize(kind,raw):
    r=raw['results'][0]
    if kind=='API-WEATHER':
        return {'observed_at':r['dateTime'],'temperature_c':r.get('temperature',{}).get('value'),'humidity_pct':r.get('relativeHumidity'),'description':r.get('phrase',''),'precipitation':r.get('hasPrecipitation'),'wind_kmh':r.get('wind',{}).get('speed',{}).get('value')}
    return {'observed_at':r['dateTime'],'index':r.get('index'),'global_index':r.get('globalIndex'),'category':r.get('category'),'dominant_pollutant':r.get('dominantPollutant'),'pollutants':[{'type':p.get('type'),'value':p.get('concentration',{}).get('value'),'unit':p.get('concentration',{}).get('unit')} for p in r.get('pollutants',[])]}
def snapshot():
    with STATE_LOCK:return json.loads(json.dumps(STATE))
def run(query,db_lock):
    with db_lock:query('CREATE TABLE IF NOT EXISTS external_weather(device TEXT, ts TEXT, payload TEXT, PRIMARY KEY(device,ts))')
    # Recuperar historial público sin almacenar credenciales.
    with db_lock:
        for kind in PATHS:
            row=query('SELECT ts,payload FROM external_weather WHERE device=? ORDER BY ts DESC LIMIT 1',(kind,)).fetchone()
            if row:STATE['nodes'][kind]={'status':'cached','fetched_at':row[0],'values':json.loads(row[1])}
    previous=None;next_at=0
    while True:
        try:
            key,coords=config()
            with STATE_LOCK:
                STATE['configured']=bool(key);STATE['coordinates']=coords
                STATE['note']='Consultas HTTPS desde el servidor; sin datos meteorológicos simulados.' if key else 'Configura AZURE_MAPS_KEY en el .env del servidor. No la pegues en el chat.'
            if key and (time.time()>=next_at or (key,coords)!=previous):
                previous=(key,coords);next_at=time.time()+900
                for kind,path in PATHS.items():
                    try:
                        params={'api-version':'1.1','query':coords,'language':'es-MX'}
                        if kind=='API-WEATHER':params.update({'details':'true','unit':'metric'})
                        req=urllib.request.Request('https://atlas.microsoft.com'+path+'?'+urllib.parse.urlencode(params),headers={'subscription-key':key,'Accept':'application/json'})
                        with urllib.request.urlopen(req,timeout=15) as response:raw=json.load(response)
                        values=normalize(kind,raw);values['coordinates']=coords;now=dt.datetime.now(dt.timezone.utc).isoformat()
                        with db_lock:query('INSERT INTO external_weather VALUES (?,?,?) ON CONFLICT(device,ts) DO NOTHING',(kind,now,json.dumps(values,ensure_ascii=False)))
                        with STATE_LOCK:STATE['nodes'][kind]={'status':'connected','fetched_at':now,'values':values}
                    except Exception as e:
                        message=f'Azure respondió HTTP {e.code}; revisa permisos, clave o cuota.' if isinstance(e,urllib.error.HTTPError) else 'No se pudo consultar Azure; revisa red, cobertura y configuración.'
                        with STATE_LOCK:
                            node=STATE['nodes'].setdefault(kind,{})
                            node.update(status='error',error=message)
            elif not key:
                with STATE_LOCK:
                    for n in STATE['nodes'].values():n['status']='cached'
        except Exception:
            with STATE_LOCK:STATE.update(configured=False,note='Revisa WEATHER_LAT y WEATHER_LON en el .env del servidor.')
        time.sleep(30)
