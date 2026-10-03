import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import zipfile
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from motion_preview_site import build
from character_workbench import load_sprite


class PreviewSiteTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source';self.source.mkdir()
        Image.new('RGBA',(640,128),(60,120,160,128)).save(self.source/'atlas.png')
        self.manifest={'kind':'motion','title':'<角色 & 参考>','atlas':'atlas.png','anchor':[.5,1],'states':[{'name':n,'loop':n in ['idle','move'],'frames':[{'x':i*128,'y':0,'w':128,'h':128,'durationMs':d}]} for i,(n,d) in enumerate([('idle',3200),('move',100),('attack',330),('hit',160),('jump',440)])]}
        self.path=self.source/'manifest.json';self.path.write_text(json.dumps(self.manifest))

    def test_delivery_links_archives_and_relocated_consumers_preserve_actual_assets(self):
        before=self.path.read_bytes();atlas=(self.source/'atlas.png').read_bytes()
        out=build(self.path,self.root/'site')
        summary=json.loads((out/'delivery.json').read_text())
        self.assertEqual(summary['sourceManifestSha256'],hashlib.sha256(before).hexdigest())
        self.assertEqual(summary['status'],'draft');self.assertEqual(summary['imageGenerationCalls'],0)
        self.assertIn('href="../workbench/"',(out/'playable/index.html').read_text())
        page=(out/'index.html').read_text();self.assertIn('&lt;角色 &amp; 参考&gt;',page);self.assertNotIn('@@',page)
        for name in ['game-assets','godot-preview','web-playground']:
            with zipfile.ZipFile(out/'downloads'/f'{name}.zip') as archive:
                self.assertTrue(archive.testzip() is None)
                atlas_name='bundle/atlas.png' if name in ['game-assets','web-playground'] else 'atlas.png'
                self.assertEqual(archive.read(atlas_name),atlas)
                if name=='web-playground':
                    self.assertIn('workbench/index.html',archive.namelist())
                    self.assertIn('href="workbench/"',archive.read('index.html').decode())
        self.assertEqual((out/'material/bundle/manifest.json').read_bytes(),before)
        self.assertEqual(json.loads((out/'playable/bundle/manifest.json').read_text()),self.manifest)
        self.assertEqual(Image.open(out/'material/bundle/frames/idle/0000.png').convert('RGBA').tobytes(),Image.open(self.source/'atlas.png').convert('RGBA').crop((0,0,128,128)).tobytes())
        self.assertEqual((out/'godot/source-manifest.json').read_bytes(),before)
        self.assertEqual(self.path.read_bytes(),before)
        moved=self.root/'moved';shutil.move(out,moved);shutil.rmtree(self.source)
        load_sprite({'manifest':'material/bundle/manifest.json'},moved)
        load_sprite({'manifest':'playable/bundle/manifest.json'},moved)

    def test_missing_actions_and_overwrite_do_not_publish_or_destroy(self):
        out=build(self.path,self.root/'site');before=(out/'index.html').read_bytes()
        with self.assertRaisesRegex(ValueError,'输出已存在'):build(self.path,out)
        self.assertEqual((out/'index.html').read_bytes(),before)
        self.manifest['states'].pop();self.path.write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError,'五动作'):build(self.path,self.root/'bad')
        self.assertFalse((self.root/'bad').exists())

    def test_short_jump_requires_explicit_matching_window(self):
        self.manifest['states'][-1]['frames'][0]['durationMs']=200
        self.path.write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError,'起落窗口'):build(self.path,self.root/'bad')
        self.assertFalse((self.root/'bad').exists())
        options=self.root/'options.json';options.write_text(json.dumps({'launchMs':30,'landMs':150}))
        out=build(self.path,self.root/'matched',options)
        self.assertEqual(json.loads((out/'playable/controller-options.json').read_text()),{'launchMs':30,'landMs':150})

    def test_contact_stop_mapping_survives_delivery_and_invalid_targets_never_publish(self):
        self.manifest['states'].append({'name':'stop-front','loop':False,'frames':[{'x':0,'y':0,'w':128,'h':128,'durationMs':120}]})
        self.path.write_text(json.dumps(self.manifest))
        options=self.root/'contact-options.json'
        data={'stopContactFrames':[0],'stopClipsByContact':{'0':'stop-front'},'reverseStartOnRelease':True}
        options.write_text(json.dumps(data))
        out=build(self.path,self.root/'contact-site',options)
        self.assertEqual(json.loads((out/'playable/controller-options.json').read_text()),data)
        with zipfile.ZipFile(out/'downloads/web-playground.zip') as archive:
            self.assertEqual(json.loads(archive.read('controller-options.json')),data)
        for mapping in [None,[],{'1':'stop-front'},{'00':'stop-front'},{'0':'missing'},{'0':'idle'},{'0':'attack'}]:
            options.write_text(json.dumps({'stopContactFrames':[0],'stopClipsByContact':mapping}))
            with self.assertRaisesRegex(ValueError,'停步映射'):build(self.path,self.root/'bad',options)
            self.assertFalse((self.root/'bad').exists())
        self.manifest['states'][-1]['loop']=True;self.path.write_text(json.dumps(self.manifest));options.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'停步映射'):build(self.path,self.root/'bad',options)
        self.assertFalse((self.root/'bad').exists())

    def test_invalid_consumption_options_never_publish(self):
        options=self.root/'options.json'
        for key,value in [('reverseStartOnRelease',1),('speed',0),('jumpHeight',0),('breathAmplitude',-1e-13),('breathAmplitude',.03),('breathPeriod',.49),('contactHoldMs',201),('stopContactFrames',[0,0]),('stopContactFrames',[True])]:
            with self.subTest(key=key,value=value):
                options.write_text(json.dumps({key:value}))
                with self.assertRaises(ValueError):build(self.path,self.root/'bad',options)
                self.assertFalse((self.root/'bad').exists())
        options.write_text(json.dumps({'breathAmplitude':0,'breathPeriod':.5}))
        self.assertTrue(build(self.path,self.root/'valid',options).exists())


if __name__=='__main__':unittest.main()
