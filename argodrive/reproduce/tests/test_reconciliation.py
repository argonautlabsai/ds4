import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('reconcile',Path(__file__).parents[1]/'reconcile-bytes.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ReconciliationTests(unittest.TestCase):
 def test_windows_and_unattributed_residual(self):
  log='ARGODRIVE_BYTES prefill_start 0 0 0 0\nARGODRIVE_BYTES prefill_end 4 2 2 10\nARGODRIVE_BYTES decode_start 4 2 2 10\nARGODRIVE_BYTES decode_end 104 52 52 20\nds4: Argodrive source[0] bytes=104\nds4: Argodrive source[1] bytes=52\nds4: Argodrive source[2] bytes=52\n'
  phases={k:{'seconds':1,'drives':{l:{'read_gb':200/1e9,'read_gb_bounds':[180/1e9,220/1e9]} for l in ['a','b','c']}} for k in ['prefill','decode']}
  r=m.reconcile(log,phases,['a','b','c']);self.assertTrue(r['application_counter_closure']);self.assertFalse(r['physical_attribution_complete']);self.assertEqual(r['phases']['decode']['drives']['a']['instrumented_application_bytes'],110);self.assertEqual(r['phases']['decode']['drives']['a']['physical_minus_instrumented_bytes'],90)
  with self.assertRaises(ValueError):m.reconcile(log.replace('104 52 52 20','1 1 1 1'),phases,['a','b','c'])
if __name__=='__main__':unittest.main()
