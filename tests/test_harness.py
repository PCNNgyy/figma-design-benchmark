import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('harness',ROOT/'scripts/claude_code_harness.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
from benchmark_blank_screens import image_metrics,structural_empty_frames
from benchmark_screen_count import evaluate_named_screens

class HarnessTests(unittest.TestCase):
 def test_config_requires_three_distinct_judges_and_explicit_gate(self):
  config=h.read(ROOT/'examples/judges.example.json');h.validate(config,'judge')
  del config['gate_policy']
  with self.assertRaises(ValueError):h.validate(config,'judge')
  config['gate_policy']='disabled';config['judges'][2]['cli_model']=config['judges'][0]['cli_model']
  with self.assertRaises(ValueError):h.validate(config,'judge')

 def test_shared_copy_rejected(self):
  config=h.read(ROOT/'examples/inference.example.json')
  config['jobs'].append(dict(config['jobs'][0],id='second-job'))
  with self.assertRaisesRegex(ValueError,'distinct writable'):h.validate(config,'inference')

 def test_read_needs_successful_image_result(self):
  events=[{'message':{'content':[{'type':'tool_use','name':'Read','id':'r','input':{'file_path':'/tmp/image.png'}}]}},
   {'message':{'content':[{'type':'tool_result','tool_use_id':'r','content':[{'type':'text','text':'seen'}]}]}}]
  self.assertEqual(h.opened_images(events),set())
  events[-1]['message']['content'][0]['content']=[{'type':'image'}]
  self.assertEqual(h.opened_images(events),{'/tmp/image.png'})
  events[-1]['message']['content'][0]['is_error']=True
  self.assertEqual(h.opened_images(events),set())

 def test_missing_scores_have_no_mean(self):
  config=h.read(ROOT/'examples/judges.example.json')
  score=h.summarize_scores(config,[{'id':'artifact-a','judge_id':'judge-a','status':'completed','score_total':31}])[0]
  self.assertIsNone(score['mean_score']);self.assertIsNone(score['judges'][0]['mean'])
  self.assertFalse(score['complete'])

 def test_parent_auth_and_agent_environment_removed(self):
  with patch.dict(os.environ,{'ANTHROPIC_API_KEY':'hidden','CLAUDECODE':'parent','CLAUDE_CONFIG_DIR':'parent-config'}):
   env=h.clean_environment()
   for k in ['ANTHROPIC_API_KEY','CLAUDECODE','CLAUDE_CONFIG_DIR']:self.assertNotIn(k,env)

 def test_white_shell_and_structural_empty_checks(self):
  with tempfile.TemporaryDirectory() as folder:
   file=Path(folder)/'image.png';image=Image.new('RGB',(360,640),'white');draw=ImageDraw.Draw(image)
   draw.rectangle((0,0,360,30),fill='black');draw.rectangle((0,610,360,640),fill='black');image.save(file)
   self.assertEqual(image_metrics(file)['blank_reason'],'empty_body_with_chrome')
   draw.rectangle((40,120,320,480),fill=(80,130,180));image.save(file)
   self.assertFalse(image_metrics(file)['blank'])
  self.assertEqual(structural_empty_frames({'layer_summary':{'boards':[{'id':'a','nodes':0}]}},[{'id':'a'}]),[{'id':'a'}])

 def test_missing_and_duplicate_screen_names(self):
  inventory={'workspace':{'children':[{'id':'a','type':'FRAME','name':'01_Catalog'},{'id':'b','type':'FRAME','name':'01_Catalog'}]}}
  value=evaluate_named_screens(inventory,['01_Catalog','02_Detail'])
  self.assertFalse(value['passed']);self.assertEqual(value['missing_screen_names'],['02_Detail'])
  self.assertEqual(value['duplicate_screen_names'],{'01_Catalog':2})

 def test_lease_serializes_independent_processes(self):
  with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'FIGMA_HARNESS_LOCK_DIR':folder}):
   marker=Path(folder)/'entered'
   code="import importlib.util; from pathlib import Path; s=importlib.util.spec_from_file_location('h',"+repr(str(ROOT/'scripts/claude_code_harness.py'))+"); h=importlib.util.module_from_spec(s); s.loader.exec_module(h)\nwith h.lease('account'): Path("+repr(str(marker))+").touch()"
   with h.lease('account'):
    proc=subprocess.Popen([sys.executable,'-c',code])
    try:
     with self.assertRaises(subprocess.TimeoutExpired):proc.wait(timeout=.3)
     self.assertFalse(marker.exists())
    except BaseException:proc.kill();proc.wait();raise
   proc.wait(timeout=5);self.assertTrue(marker.exists())

 def test_batch_with_mock_cli_hashes_reads_parsing_and_telemetry(self):
  # Simulates CLI events; this is explicitly not a live provider test.
  with tempfile.TemporaryDirectory() as folder:
   folder=Path(folder);cli=folder/'fake-claude'
   cli.write_text('#!'+sys.executable+'\n'+r'''
import json,sys
from pathlib import Path
if '--version' in sys.argv: print('fixture-cli');sys.exit(0)
sys.stdin.read()
for i,p in enumerate(Path.cwd().glob('*.png')):
 print(json.dumps({'type':'assistant','message':{'model':'fixture-model','content':[{'type':'tool_use','name':'Read','id':str(i),'input':{'file_path':str(p)}}]}}))
 print(json.dumps({'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':str(i),'content':[{'type':'image'}]}]}}))
rubric=json.loads(Path(__file__).with_name('rubric.json').read_text())
print(json.dumps({'type':'result','result':json.dumps({'scores':[{'key':q['key'],'score':0,'evidence':'第 1 屏：fixture evidence'} for q in rubric['questions']]}),'is_error':False,'usage':{'input_tokens':10,'output_tokens':20},'num_turns':2}))
''')
   cli.chmod(0o700)
   (folder/'rubric.json').write_bytes((ROOT/'benchmarks/rubrics/fixed-v4.json').read_bytes())
   Image.new('RGB',(128,128),(30,80,160)).save(folder/'one.png')
   (folder/'query.txt').write_text('Synthetic query')
   (folder/'layers.json').write_bytes((ROOT/'examples/layer-summary.example.json').read_bytes())
   config=h.read(ROOT/'examples/judges.example.json');config.update(claude_bin=str(cli),repetitions=2,concurrency=3)
   config['artifacts']=[{'id':'fixture','query_file':'query.txt','images':['one.png'],'layer_summary_file':'layers.json'}]
   h.save(folder/'config.json',config)
   result=subprocess.run([sys.executable,str(ROOT/'scripts/claude_code_harness.py'),'judge','--config',str(folder/'config.json'),'--output',str(folder/'outputs')],env={**os.environ,'MODEL_API_KEY':'fixture-credential'},text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stderr)
   batch=json.loads(result.stdout.splitlines()[-1]);self.assertEqual(batch['passed'],6)
   scores=h.read(Path(batch['directory'])/'scores.json');self.assertTrue(scores[0]['complete']);self.assertEqual(scores[0]['mean_score'],0)
   cases=list(Path(batch['directory']).glob('*/result.json'));self.assertEqual(len(cases),6)
   for case in cases:
    value=h.read(case);self.assertEqual(value['usage']['output_tokens'],20);self.assertEqual(value['images_read'],1)
    invocation=(case.parent/'invocation.json').read_text();self.assertNotIn('fixture-credential',invocation)
    self.assertIn('--strict-mcp-config',invocation);self.assertIn('--restricted',invocation)

if __name__=='__main__':unittest.main()
