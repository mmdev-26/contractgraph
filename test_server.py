import unittest,subprocess,sys,socket,time,json,urllib.request,urllib.error
from pathlib import Path
class ServerTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  s=socket.socket();s.bind(('127.0.0.1',0));cls.port=s.getsockname()[1];s.close();cls.url=f'http://127.0.0.1:{cls.port}'
  cls.process=subprocess.Popen([sys.executable,'app.py','serve','--port',str(cls.port),'--isolated','--public-origin','https://agencia.sk'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  for i in range(50):
   try:urllib.request.urlopen(cls.url,timeout=.2).close();break
   except (OSError,urllib.error.URLError):time.sleep(.03)
  else:cls.process.terminate();raise RuntimeError('Server failed to start')
 @classmethod
 def tearDownClass(cls):cls.process.terminate();cls.process.wait(timeout=5)
 def post(self,raw,headers=None):return urllib.request.urlopen(urllib.request.Request(self.url+'/analyze',data=raw,headers={'Content-Type':'application/json',**(headers or {})}),timeout=5)
 def test_real_example(self):
  with self.post(Path('example.json').read_bytes()) as r:self.assertIn('summary',json.load(r))
 def test_reject_nonfinite(self):
  with self.assertRaises(urllib.error.HTTPError) as e:self.post(b'{"value": NaN}')
  self.assertEqual(e.exception.code,400)
 def test_cross_origin_rejected(self):
  with self.assertRaises(urllib.error.HTTPError) as e:self.post(b'{}',{'Origin':'https://other.example'})
  self.assertEqual(e.exception.code,403)
 def test_unknown_path(self):
  with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(self.url+'/../engine.py')
  self.assertEqual(e.exception.code,404)
 def test_no_cors_or_cache(self):
  with urllib.request.urlopen(self.url) as r:self.assertEqual(r.headers['Cache-Control'],'no-store');self.assertIsNone(r.headers.get('Access-Control-Allow-Origin'))

 def test_public_origin_accepted(self):
  with self.post(Path('example.json').read_bytes(),{'Origin':'https://agencia.sk'}) as r:self.assertIn('summary',json.load(r))
 def test_disclosure(self):
  with urllib.request.urlopen(self.url) as r:self.assertIn('Public demo: input is sent to our server',r.read().decode())
 def test_invalid_structure(self):
  with self.assertRaises(urllib.error.HTTPError) as e:self.post(b'null')
  self.assertEqual(e.exception.code,400)
