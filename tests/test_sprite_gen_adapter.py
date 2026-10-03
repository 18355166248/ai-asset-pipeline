import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from sprite_gen_adapter import import_bundle, candidate, select, review, export, pixels, fingerprint, apply_plan, sha

class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        source=self.root/'source';source.mkdir();atlas=Image.new('RGBA',(32,8),(20,30,40,0))
        for i in range(4):atlas.paste((50*i,70,90,128),(i*8+1,1,i*8+7,7))
        atlas.save(source/'atlas.png');self.source=source/'manifest.json'
        self.source.write_text(json.dumps({'kind':'motion','atlas':'atlas.png','anchor':[.5,.875],'states':[{'name':'move','loop':True,'frames':[{'x':i*8,'y':0,'w':8,'h':8,'durationMs':dt} for i,dt in enumerate([110,80,80,60])]}]}))
        self.run=self.root/'run';import_bundle(self.source,self.run,['move'])
    def load(self,run=None):return json.loads(((run or self.run)/'motion-contract.json').read_text())
    def test_import_preserves_rgba_including_hidden_rgb_and_nonuniform_durations(self):
        c=self.load();self.assertEqual([f['durationMs'] for f in c['states'][0]['frames']],[110,80,80,60])
        atlas=Image.open(self.run/'bundle/atlas.png').convert('RGBA');m=json.loads((self.run/'bundle/manifest.json').read_text())
        for f,r in zip(c['states'][0]['frames'],m['states'][0]['frames']):self.assertEqual(pixels(atlas.crop((r['x'],r['y'],r['x']+8,r['y']+8))),f['rgbaSha256'])
        self.assertEqual((self.run/'source/atlas.png').read_bytes(),(self.source.parent/'atlas.png').read_bytes())
    def test_reorder_repeat_and_split_durations_survive_reexport(self):
        c=self.load();frames=c['states'][0]['frames'];c['states'][0]['frames']=[dict(frames[0],durationMs=60),dict(frames[1],durationMs=50),frames[2],frames[3],frames[1]]
        (self.run/'motion-contract.json').write_text(json.dumps(c));out=self.root/'retimed';export(self.run,out)
        durations=[f['durationMs'] for f in json.loads((out/'bundle/manifest.json').read_text())['states'][0]['frames']]
        self.assertEqual(durations,[60,50,80,60,80]);self.assertEqual(sum(durations),330)
        self.assertEqual(durations,[f['duration'] for f in json.loads((out/'bundle/aseprite.json').read_text())['frames']])
    def test_candidate_isolated_selection_only_changes_one_frozen_frame(self):
        before=self.load();original=[(self.run/f['image']).read_bytes() for f in before['states'][0]['frames']]
        image=self.root/'candidate.png';Image.new('RGBA',(8,8),(90,200,40,128)).save(image)
        picked=self.root/'candidate';candidate(self.run,'move',1,image,picked,'fixture repair, not GPT')
        self.assertEqual(self.load(),before);out=self.root/'selected';select(self.run,picked,out);after=self.load(out)
        for i,f in enumerate(after['states'][0]['frames']):
            self.assertEqual(f['durationMs'],before['states'][0]['frames'][i]['durationMs'])
            if i!=1:self.assertEqual((out/f['image']).read_bytes(),original[i])
        self.assertNotEqual(after['states'][0]['frames'][1]['rgbaSha256'],before['states'][0]['frames'][1]['rgbaSha256'])
        self.assertEqual([(self.run/f['image']).read_bytes() for f in before['states'][0]['frames']],original)
    def test_stale_candidate_and_wrong_size_are_rejected_without_publication(self):
        image=self.root/'candidate.png';Image.new('RGBA',(9,8)).save(image)
        with self.assertRaisesRegex(ValueError,'画布'):candidate(self.run,'move',0,image,self.root/'bad','fixture')
        self.assertFalse((self.root/'bad').exists());Image.new('RGBA',(8,8),(30,40,50,255)).save(image);candidate(self.run,'move',0,image,self.root/'candidate','fixture')
        c=self.load();c['states'][0]['frames'][0]['durationMs']=120;(self.run/'motion-contract.json').write_text(json.dumps(c))
        with self.assertRaisesRegex(ValueError,'过期'):select(self.run,self.root/'candidate',self.root/'selected')
        self.assertFalse((self.root/'selected').exists())
    def test_corrupted_frozen_frame_or_fractional_timing_cannot_export(self):
        c=self.load();c['states'][0]['frames'][0]['durationMs']=80.5;(self.run/'motion-contract.json').write_text(json.dumps(c))
        with self.assertRaisesRegex(ValueError,'整数'):export(self.run,self.root/'bad')
        c['states'][0]['frames'][0]['durationMs']=110;(self.run/'motion-contract.json').write_text(json.dumps(c));Image.new('RGBA',(8,8),(0,0,0,255)).save(self.run/c['states'][0]['frames'][0]['image'])
        with self.assertRaisesRegex(ValueError,'冻结'):export(self.run,self.root/'bad')
        self.assertFalse((self.root/'bad').exists())
    def test_release_gate_requires_current_motion_review_and_user_evidence(self):
        with self.assertRaisesRegex(ValueError,'验收'):export(self.run,self.root/'release',True)
        with self.assertRaisesRegex(ValueError,'先记录'):review(self.run,'move','user-accept','fixture human evidence',self.root/'accepted')
        checked=self.root/'checked';review(self.run,'move','motion-pass','fixture motion check',checked)
        accepted=self.root/'accepted';review(checked,'move','user-accept','fixture explicit user feedback',accepted)
        export(accepted,self.root/'release',True)
        c=self.load(accepted);c['states'][0]['frames'][0]['durationMs']=120;(accepted/'motion-contract.json').write_text(json.dumps(c))
        with self.assertRaisesRegex(ValueError,'验收'):export(accepted,self.root/'stale-release',True)

    def test_timing_plan_uses_baseline_and_existing_frozen_images(self):
        c=self.load();plan={'version':1,'baselineContractSha256':sha(self.run/'motion-contract.json'),'states':c['states']}
        plan['states'][0]['frames'].reverse();path=self.root/'plan.json';path.write_text(json.dumps(plan));out=self.root/'reordered';apply_plan(self.run,path,out)
        self.assertEqual([f['durationMs'] for f in self.load(out)['states'][0]['frames']],[60,80,80,110])
        plan['baselineContractSha256']='stale';path.write_text(json.dumps(plan))
        with self.assertRaisesRegex(ValueError,'过期'):apply_plan(self.run,path,self.root/'bad')
        plan['baselineContractSha256']=sha(self.run/'motion-contract.json');plan['states'][0]['frames'][0]['image']='source/atlas.png';path.write_text(json.dumps(plan))
        with self.assertRaisesRegex(ValueError,'外部图片'):apply_plan(self.run,path,self.root/'bad')
