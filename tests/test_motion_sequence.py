import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from motion_sequence import assemble
from character_workbench import load_sprite


class SequenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.pack('old',12,[.5,1],(190,50,20,128))
        self.pack('new',12,[.5,1],(20,80,190,64))
        self.config={'version':1,'inputs':[{'manifest':'old/manifest.json'},{'manifest':'new/manifest.json'}],'states':[{'name':'hit','loop':False,'frames':[{'input':0,'action':'pose','frame':0,'durationMs':80},{'input':1,'action':'pose','frame':0,'durationMs':50},{'input':0,'action':'pose','frame':0,'durationMs':30}]}]}
        self.path=self.root/'config.json'

    def pack(self,name,cell,anchor,color):
        folder=self.root/name
        folder.mkdir(exist_ok=True)
        im=Image.new('RGBA',(cell,cell));im.paste(color,(1,1,cell-1,cell-1));im.save(folder/'atlas.png')
        (folder/'manifest.json').write_text(json.dumps({'kind':'motion','atlas':'atlas.png','anchor':anchor,'states':[{'name':'pose','loop':True,'frames':[{'x':0,'y':0,'w':cell,'h':cell,'durationMs':100}]}]}))
        (folder/'generation-review.json').write_text(json.dumps({'verdict':'reject'}))

    def run_build(self,name='result'):
        self.path.write_text(json.dumps(self.config))
        return assemble(self.path,self.root/name)

    def test_rgba_reuse_retiming_loop_and_provenance_survive_relocation(self):
        originals={n:(self.root/n/'atlas.png').read_bytes() for n in ('old','new')}
        path=self.run_build();m=json.loads(path.read_text());state=m['states'][0]
        self.assertFalse(state['loop'])
        self.assertEqual([f['durationMs'] for f in state['frames']],[80,50,30])
        atlas=Image.open(path.parent/m['atlas']).convert('RGBA')
        for ref,frame in zip(self.config['states'][0]['frames'],state['frames']):
            expected=Image.open(self.root/('old' if ref['input']==0 else 'new')/'atlas.png').convert('RGBA')
            actual=atlas.crop((frame['x'],frame['y'],frame['x']+frame['w'],frame['y']+frame['h']))
            self.assertEqual(actual.tobytes(),expected.tobytes())
        self.assertEqual(m['source']['status'],'draft')
        self.assertEqual(m['source']['imageGenerationCalls'],0)
        self.assertEqual(m['source']['sequence'][0]['frames'][1]['originalDurationMs'],100)
        for record in m['source']['inputs']:
            self.assertEqual(hashlib.sha256((path.parent.parent/record['originalManifest']).read_bytes()).hexdigest(),record['originalManifestSha256'])
            self.assertEqual(json.loads((path.parent.parent/record['auditCopies'][0]['path']).read_text())['verdict'],'reject')
        for n in originals:self.assertEqual((self.root/n/'atlas.png').read_bytes(),originals[n])
        moved=self.root/'moved';shutil.move(path.parent.parent,moved)
        shutil.rmtree(self.root/'old');shutil.rmtree(self.root/'new')
        load_sprite({'manifest':'bundle/manifest.json'},moved)
        load_sprite({'manifest':'inputs/001/manifest.json'},moved)

    def test_invalid_references_and_durations_never_publish(self):
        for field,value in [('input',-1),('input',True),('frame',1),('frame',False),('action','missing'),('durationMs',0),('durationMs',float('nan')),('durationMs',True)]:
            with self.subTest(field=field,value=value):
                original=self.config['states'][0]['frames'][0].copy()
                self.config['states'][0]['frames'][0][field]=value
                with self.assertRaises(ValueError):self.run_build()
                self.assertFalse((self.root/'result').exists())
                self.config['states'][0]['frames'][0]=original

    def test_incompatible_source_canvas_and_anchor_rejected(self):
        for cell,anchor in [(14,[.5,1]),(12,[.5,.9])]:
            self.pack('new',cell,anchor,(0,0,0,128))
            with self.assertRaises(ValueError):self.run_build()
            self.assertFalse((self.root/'result').exists())

    def test_default_source_duration_and_no_overwrite(self):
        self.config['states'][0]['frames'][0].pop('durationMs')
        path=self.run_build();self.assertEqual(json.loads(path.read_text())['states'][0]['frames'][0]['durationMs'],100)
        original=path.read_bytes()
        with self.assertRaisesRegex(ValueError,'输出已存在'):self.run_build()
        self.assertEqual(path.read_bytes(),original)


if __name__=='__main__':unittest.main()
