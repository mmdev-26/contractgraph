import unittest,json
from pathlib import Path
from copy import deepcopy
from engine import analyze
class Tests(unittest.TestCase):
 def setUp(self):self.d=json.loads(Path(__file__).with_name('example.json').read_text())
 def test_detects_breaking(self):self.assertGreaterEqual(analyze(self.d)['summary']['breaking'],2)
 def test_transitive_chain(self):self.assertEqual(next(i for i in analyze(self.d)['impact'] if i['consumer']=='checkout')['chain'],['billing-sdk','checkout'])
 def test_identical(self):self.d['after']=deepcopy(self.d['before']);self.assertEqual(analyze(self.d)['summary']['breaking'],0)
 def test_removed_operation(self):self.d['after']['paths']={};self.assertIn('operation_removed',[x['code'] for x in analyze(self.d)['findings']])
 def test_cycles_terminate(self):self.d['consumers'][0]['dependsOn']=['checkout'];self.assertEqual(analyze(self.d)['summary']['impactedConsumers'],2)
 def test_missing_dependency(self):self.d['consumers'][0]['dependsOn']=['missing'];self.assertRaises(ValueError,analyze,self.d)
 def test_duplicates(self):self.d['consumers'].append(self.d['consumers'][0]);self.assertRaises(ValueError,analyze,self.d)
 def test_fingerprint_reproducible(self):self.assertEqual(analyze(self.d)['provenance'],analyze(deepcopy(self.d))['provenance'])
 def test_enum_request_widening_safe(self):
  self.d['after']=deepcopy(self.d['before']);s=self.d['after']['paths']['/invoices']['post']['requestBody']['content']['application/json']['schema'];s['properties']['state']['enum'].append('extra');self.assertFalse(any(x['code']=='enum_incompatible' for x in analyze(self.d)['findings']))
 def test_composition_unknown(self):
  self.d['after']['paths']['/invoices']['post']['requestBody']['content']['application/json']['schema']['allOf']=[{}];self.assertGreater(analyze(self.d)['summary']['manualReview'],0)
if __name__=='__main__':unittest.main()
