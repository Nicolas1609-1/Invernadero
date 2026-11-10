import os,tempfile,unittest,datetime as dt
os.environ['DB_PATH']=tempfile.mktemp(suffix='.db')
import app
from unittest.mock import patch
import io,json

class IoTTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): app.init()
    def test_validation_and_dedup(self):
        ts='2026-10-26T00:00:00+00:00'; v=dict(temperature=25,humidity=60,soil=50,light=100)
        app.ingest('D01',ts,v,'test');app.ingest('D01',ts,v,'test')
        self.assertEqual(app.query('SELECT COUNT(*) FROM readings WHERE device=?',('D01',)).fetchone()[0],4)
        with self.assertRaises(ValueError): app.ingest('D01',ts,dict(v,temperature=99),'test')
    def test_return_control_and_idempotency(self):
        cid=app.command('D02',{'enabled':False,'offset':1.5,'interval_s':10},'test-1')
        self.assertEqual(cid,app.command('D02',{'enabled':False,'offset':1.5,'interval_s':10},'test-1'))
        self.assertEqual(app.query('SELECT enabled,offset,interval_s FROM state WHERE device=?',('D02',)).fetchone(),(0,1.5,10))
        with self.assertRaises(ValueError): app.command('D02',{'offset':8})
        with self.assertRaises(ValueError): app.command('D02',{'enabled':True},'test-1')
    def test_invalid_command(self):
        for b in [{'enabled':'false'},{'interval_s':3},{'offset':float('nan')},{'unknown':1}]:
            with self.assertRaises(ValueError): app.command('D03',b)
    def test_forecast_falling_and_insufficient_data(self):
        start=dt.datetime.now(dt.timezone.utc)
        samples=[((start+dt.timedelta(minutes=10*i)).isoformat(),60-.2*i) for i in range(6)]
        result=app.forecast(samples)
        self.assertAlmostEqual(result['slope_per_hour'],-1.2)
        self.assertAlmostEqual(result['in_6h'],51.8)
        self.assertIsNone(app.forecast(samples[:3]))
        self.assertIsNone(app.forecast([(t,60-i*10) for i,(t,v) in enumerate(samples)]))
    def test_irrigation_persistence_dedup_and_cooldown(self):
        ts=dt.datetime.now(dt.timezone.utc).isoformat()
        app.ingest('D10',ts,dict(temperature=25,humidity=60,soil=35,light=100),'live_simulated')
        app.command('D10',{'irrigation_ml':250},'water-test')
        app.command('D10',{'irrigation_ml':250},'water-test')
        self.assertEqual(app.query('SELECT COUNT(*) FROM irrigation WHERE device=?',('D10',)).fetchone()[0],1)
        with self.assertRaises(ValueError): app.command('D10',{'irrigation_ml':250},'water-duplicate')
        with self.assertRaises(ValueError): app.command('D10',{'irrigation_ml':-10})
        with self.assertRaises(ValueError): app.command('D10',{'irrigation_ml':250,'enabled':True})
    def test_insights_rejects_stale_forecast(self):
        ts=(dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=1)).isoformat()
        app.ingest('D09',ts,dict(temperature=25,humidity=60,soil=35,light=100),'live_simulated')
        node=next(n for n in app.insights()['nodes'] if n['id']=='D09')
        self.assertFalse(node['fresh']);self.assertFalse(node['can_irrigate'])
        self.assertEqual(node['status'],'stale');self.assertIsNone(node['forecast'])
    def test_azure_weather_normalization(self):
        r=app.weather_adapter.normalize('API-WEATHER',{'results':[{'dateTime':'2026-11-06T10:00:00Z','temperature':{'value':25.1},'relativeHumidity':72,'hasPrecipitation':True,'wind':{'speed':{'value':8}}}]})
        self.assertEqual(r['temperature_c'],25.1);self.assertTrue(r['precipitation']);self.assertEqual(r['humidity_pct'],72)
    def test_azure_air_normalization(self):
        r=app.weather_adapter.normalize('API-AIR',{'results':[{'dateTime':'2026-11-06T10:00:00Z','globalIndex':22,'category':'Fair','pollutants':[{'type':'PM2.5','concentration':{'value':3.2,'unit':'µg/m³'}}]}]})
        self.assertEqual(r['global_index'],22);self.assertEqual(r['pollutants'][0]['value'],3.2)
    def test_groq_response_and_rate_limit(self):
        module=app.groq_adapter;module.LAST_REQUEST=0
        payload={'choices':[{'message':{'content':'Revisar la humedad del suelo de D01.'}}],'model':'test-model'}
        def response(req,timeout):
            self.assertEqual(req.full_url,'https://api.groq.com/openai/v1/chat/completions')
            data=json.loads(req.data)
            self.assertNotIn('tools',data)
            self.assertNotIn('private-test-key',req.data.decode())
            return io.BytesIO(json.dumps(payload).encode())
        with patch.object(module,'config',return_value=('private-test-key','test-model')),patch.object(module.urllib.request,'urlopen',side_effect=response):
            result=module.analyze({'soil':35})
            self.assertEqual(result['text'],'Revisar la humedad del suelo de D01.')
            with self.assertRaisesRegex(ValueError,'60 segundos'):module.analyze({'soil':35})
        module.LAST_REQUEST=0
    def test_groq_requires_server_key(self):
        with patch.object(app.groq_adapter,'config',return_value=('','test-model')):
            with self.assertRaisesRegex(ValueError,'GROQ_API_KEY'):app.groq_adapter.analyze({})

if __name__=='__main__': unittest.main()
