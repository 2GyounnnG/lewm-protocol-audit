import unittest,sys,json,hashlib
from pathlib import Path
import numpy as np
from adapters.common import *
from adapters.M01 import pack,unpack,FastCost
from adapters.M03 import filter_bank
from adapters.M07 import validate_seed
from adapters.harness import run_case
from tools.check_fidelity import compare
class Scaler:
 n_features_in_=2
 def transform(self,x):return (np.asarray(x)-np.array([1,2]))/np.array([2,4])
class Tests(unittest.TestCase):
 def test_first_context(self):
  f,p,ix=history([np.ones((2,2,3))],[],3,Scaler());self.assertEqual(ix,[0]);self.assertEqual(p.shape,(0,10))
 def test_history_temporal_alignment(self):
  frames=[np.full((2,2,3),i) for i in range(26)];a=np.arange(50).reshape(25,2)
  f,p,ix=history(frames,a,3,Scaler());self.assertEqual(ix,[15,20,25]);np.testing.assert_array_equal(p.reshape(10,2),Scaler().transform(a[15:25]))
 def test_ap_early_ramp(self):self.assertEqual(history_indices(5,3),[0,5]);self.assertEqual(history_indices(10,3),[0,5,10])
 def test_no_future_leak(self):
  with self.assertRaises(ValueError):history([np.zeros(1)]*25,np.zeros((25,2)),3,Scaler())
 def test_fast_mapping_for_four_tasks(self):
  for d in (2,7):
   a=np.arange(2*3*5*5*d,dtype=np.float32).reshape(2,3,5,5*d);p=pack(a)
   self.assertEqual(p.shape,(2,3,1,25*d));self.assertTrue(first_equal(a,unpack(p)))
 def test_fast_bad_mapping(self):
  with self.assertRaises(ValueError):pack(np.zeros((1,300,4,10)))
 def test_prefix_is_not_new_future(self):
  f=np.full((1,3,5,10),99,np.float32);p=np.arange(20).reshape(2,10);all=prefix_candidates(f,p)
  self.assertEqual(all.shape,(1,3,7,10));np.testing.assert_array_equal(all[0,0,:2],p);np.testing.assert_array_equal(all[:,:,2:],f)
 def test_no_prefix_first_plan(self):
  f=np.arange(15000,dtype=np.float32).reshape(1,300,5,10);self.assertTrue(first_equal(f,prefix_candidates(f,np.empty((0,10),np.float32))))
 def test_stream_matches_sealed(self):
  root=Path(__file__).parents[2]
  manifest=json.loads((root/'cases/CASE_AND_RANDOM_STREAM_MANIFEST.json').read_text())
  for task,d in manifest['tasks'].items():
   for c in d['cases']:
    for s,v in c['planner_seeds'].items():
     for i,expected in enumerate(v):self.assertEqual(seed(task,c['case_id'],i,s),expected)
 def test_fresh_exclusion_and_duplicates(self):
  cases=[dict(source_episode_idx=2),dict(source_episode_idx=3)]
  self.assertEqual(filter_bank([1,2,3,4],cases),[1,4])
  with self.assertRaises(ValueError):filter_bank([1,1],cases)
 def test_all_train_seeds(self):
  for s in (3072,4096,6144):self.assertEqual(validate_seed(s),s)
  with self.assertRaises(ValueError):validate_seed(42)
 def test_missing_not_zero(self):
  with self.assertRaises(ValueError):summarize_steps([],50,True)
 def test_final_vs_any(self):
  x=[dict(success=i==0,truncated=False) for i in range(50)];s=summarize_steps(x,50,False);self.assertEqual((s['success_any'],s['success_final']),(1,0))
 def test_history_bitwise_strict(self):
  a=np.array([1],np.float32);self.assertFalse(first_equal(a,a.astype(np.float64)))
 def test_fidelity_detects_drift(self):
  native=[dict(case_id=str(i),raw_actions=[[1.,2.]],success=True,reset_sha256='a',goal_sha256='b') for i in range(4)]
  self.assertEqual(compare(native,native)['status'],'PASS');other=json.loads(json.dumps(native));other[2]['raw_actions'][0][0]+=0.1
  with self.assertRaises(AssertionError):compare(native,other)
 def test_stats_pairing_and_missing(self):
  from tools.statistics_d1 import matrix,paired,holm
  expected=dict(case_ids=['a','b'],models={'m':dict(train_seeds=[1],streams=['A','B','C'])})
  rows=[dict(case_id=c,model='m',train_seed=1,stream=s,success=1) for c in ['a','b'] for s in ['A','B','C']]
  a=matrix(rows,expected,'m');r=paired(a,a)
  self.assertEqual((r['delta_pp'],r['ci95_low_pp'],r['ci95_high_pp']),(0,0,0));self.assertTrue(r['practically_negligible'])
  with self.assertRaises(ValueError):matrix(rows[:-1],expected,'m')
  self.assertEqual(holm([.01,.04,.2]),[.03,.08,.2])
 def test_noise_refuses_fabricated_streams(self):
  from tools.statistics_d1 import noise
  with self.assertRaises(ValueError):noise(np.zeros((100,3)))
 def test_checkpoint_seed_identity(self):
  m={'assets':[dict(method='M07',task='cube',sha256='a'*64,filename='cube_seed3072_object.ckpt')]}
  validate_asset_identity(dict(checkpoint_sha256='a'*64,train_seed=3072),'M07','cube',m)
  with self.assertRaises(ValueError):validate_asset_identity(dict(checkpoint_sha256='a'*64,train_seed=4096),'M07','cube',m)
 def test_budget_unknown_and_overcap(self):
  from tools.budget_gate import forecast
  rows=[dict(condition_id='x',units=576.24)]
  with self.assertRaises(ValueError):forecast(rows,{})
  self.assertEqual(forecast(rows,{'x':dict(upper_minutes_per_unit=40)})['status'],'STOP_OVER_300')
 def test_envpool_none_and_pixel_batch_contract(self):
  from types import SimpleNamespace
  from adapters.swm_runtime import BoundWorld
  pixels=np.ones((1,1,3,4,3),np.uint8)
  pool=SimpleNamespace(step=lambda a:(None,np.array([0.]),np.array([True]),np.array([False]),dict(pixels=pixels)))
  world=BoundWorld(SimpleNamespace(envs=pool));obs,_,_,_,info=world.step(np.zeros(2))
  self.assertIsNone(obs);self.assertTrue(info['_d1_success']);self.assertEqual(world.render().shape,(3,4,3))
 def test_cold_import_no_model_libraries(self):
  import adapters.model_runtime,adapters.swm_runtime,adapters.original_mode
  self.assertTrue(all(m not in sys.modules for m in ['torch','gymnasium','stable_worldmodel','mujoco']))
if __name__=='__main__':unittest.main()
