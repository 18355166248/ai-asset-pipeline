import json
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from motion_stride_review import review


class StrideReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'source').mkdir()
        Image.new('RGBA',(300,100),(80,140,160,255)).save(self.root/'source/atlas.png')
        self.manifest={'kind':'motion','anchor':[.5,1],'atlas':'atlas.png','states':[{'name':'move','loop':True,'frames':[{'x':i*100,'y':0,'w':100,'h':100,'durationMs':d} for i,d in enumerate([100,200,100])]}]}
        (self.root/'source/manifest.json').write_text(json.dumps(self.manifest))
        self.config={'version':1,'manifest':'source/manifest.json','action':'move','markerKind':'fixed-point','speed':200,'observations':[{'frame':i,'group':'support','point':[x,99]} for i,x in enumerate([90,70,30])]}
        self.path=self.root/'config.json'

    def run_review(self,name='result'):
        self.path.write_text(json.dumps(self.config));out=review(self.path,self.root/name)
        return json.loads((out/'report.json').read_text())

    def test_fixed_foot_stays_in_world_at_matching_speed_with_uneven_frame_times(self):
        before=(self.root/'source/atlas.png').read_bytes()
        report=self.run_review()
        self.assertAlmostEqual(report['diagnosticFitSpeed'],200)
        self.assertAlmostEqual(report['current']['rmsPixels'],0)
        self.assertEqual(report['current']['groups'][0]['relativeWorldX'],[0,0,0])
        self.assertEqual((self.root/'source/atlas.png').read_bytes(),before)
        self.config['speed']=0
        wrong=self.run_review('stationary')
        self.assertEqual(wrong['current']['groups'][0]['rangePixels'],60)
        self.assertGreater(wrong['current']['rmsPixels'],20)
        self.config['renderScale']=2;self.config['speed']=400
        scaled=self.run_review('scaled');self.assertAlmostEqual(scaled['current']['rmsPixels'],0)
        self.assertAlmostEqual(scaled['diagnosticFitSpeed'],400)

    def test_unordered_annotations_are_reported_in_actual_frame_order(self):
        self.config['observations']=[self.config['observations'][i] for i in [2,0,1]]
        report=self.run_review();self.assertEqual([s['frame'] for s in report['samples']],[0,1,2])
        self.assertAlmostEqual(report['current']['rmsPixels'],0)

    def test_left_facing_authored_points_use_negative_root_motion_and_reject_bad_direction(self):
        self.config['direction']=-1
        self.config['observations']=[{'frame':i,'group':'support','point':[x,99]} for i,x in enumerate([10,30,70])]
        report=self.run_review();self.assertAlmostEqual(report['diagnosticFitSpeed'],200);self.assertAlmostEqual(report['current']['rmsPixels'],0)
        for value in [0,True,'left']:
            self.config['direction']=value
            with self.assertRaisesRegex(ValueError,'direction'):self.run_review('bad-direction')

    def test_contact_region_is_explicit_diagnostic_and_empty_region_fails(self):
        self.config['markerKind']='contact-region'
        self.config['observations']=[{'frame':i,'group':'support','rect':[20,80,40,100]} for i in range(3)]
        report=self.run_review();self.assertEqual(report['samples'][0]['point'],[29.5,99.0]);self.assertEqual(report['status'],'diagnostic-only')
        Image.new('RGBA',(300,100),(0,0,0,0)).save(self.root/'source/atlas.png')
        with self.assertRaisesRegex(ValueError,'alpha'):self.run_review('empty')
        self.assertFalse((self.root/'empty').exists())

    def test_bad_markers_and_overwrite_never_destroy_source_or_previous_output(self):
        report=self.run_review();before=(self.root/'result/report.json').read_bytes()
        with self.assertRaises(ValueError):self.run_review()
        self.assertEqual((self.root/'result/report.json').read_bytes(),before)
        for entry in [{'frame':3,'group':'support','point':[20,99]},{'frame':1,'group':'support','point':[100,99]},{'frame':1,'group':'support','point':[float('nan'),99]}]:
            self.config['observations'][1]=entry
            with self.assertRaises(ValueError):self.run_review('bad')
            self.assertFalse((self.root/'bad').exists())
        self.config['observations']=[{'frame':0,'group':'a','point':[20,99]},{'frame':1,'group':'b','point':[10,99]}]
        with self.assertRaisesRegex(ValueError,'每组'):self.run_review('one-per-group')


if __name__=='__main__':unittest.main()
