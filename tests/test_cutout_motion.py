"""验证步态的落地与周期约束，不把像素变化当成左右腿验收。"""
import json
import math
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from cutout_motion import bake,foot_phase,sample,solve_knee


class CutoutMotionTests(unittest.TestCase):
    def setUp(self):
        self.rig=json.loads((ROOT/"input/codex/mint-adventurer-walk-v3/rig.json").read_text())

    def test_ground_foot_is_stationary_in_world_space(self):
        stride,lift,duty=34,14,.6
        speed_per_cycle=stride/duty
        positions=[]
        for i in range(60):
            t=i/100
            x,y,ground,_=foot_phase(t,stride,lift,duty)
            self.assertTrue(ground)
            self.assertEqual(y,0)
            positions.append(x+speed_per_cycle*t)
        self.assertLess(max(positions)-min(positions),1e-9)

    def test_near_and_far_trade_contact_and_swing(self):
        for t in [.03,.18,.32,.45]:
            first,second=sample(self.rig,"move",t),sample(self.rig,"move",t+.5)
            for a,b in (("near","far"),("far","near")):
                for x,y in zip(first["legs"][a]["ankle"],second["legs"][b]["ankle"]):
                    self.assertAlmostEqual(x,y,places=9)
                self.assertEqual(first["legs"][a]["ground"],second["legs"][b]["ground"])
        pose=sample(self.rig,"move",.25)
        self.assertTrue(pose["legs"]["near"]["ground"])
        self.assertFalse(pose["legs"]["far"]["ground"])

    def test_toe_off_and_loop_join_have_continuous_position_and_velocity(self):
        eps=1e-6
        for seam in (0,.6):
            left,center,right=[foot_phase(t,34,14,.6) for t in (seam-eps,seam,seam+eps)]
            for axis in (0,1):
                self.assertAlmostEqual(left[axis],right[axis],delta=.001)
                self.assertAlmostEqual((center[axis]-left[axis])/eps,(right[axis]-center[axis])/eps,delta=.02)

    def test_entire_cycle_preserves_bone_lengths_and_reaches_feet(self):
        for action in ("idle","move"):
            for index in range(240):
                pose=sample(self.rig,action,index/240)
                for leg in pose["legs"].values():
                    self.assertAlmostEqual(math.dist(leg["hip"],leg["knee"]),self.rig["bones"]["thigh"],places=9)
                    self.assertAlmostEqual(math.dist(leg["knee"],leg["ankle"]),self.rig["bones"]["calf"],places=9)

    def test_unreachable_foot_fails_instead_of_stretching_leg(self):
        with self.assertRaisesRegex(ValueError,"不可达"):
            solve_knee([0,0],[0,100],30,30)

    def test_package_rebuilds_after_input_moves_and_preserves_fractional_fps(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            inputs=root/"input"
            inputs.mkdir()
            shutil.copy2(ROOT/"input/codex/mint-adventurer-walk-v3/parts.png",inputs/"parts.png")
            self.rig["actions"]={"idle":{"frames":2,"fps":24},"move":{"frames":2,"fps":60}}
            (inputs/"rig.json").write_text(json.dumps(self.rig))
            first=bake(inputs/"rig.json",root/"first")
            inputs.rename(root/"old-input")
            second=bake(root/"first/rig.json",root/"second")
            a,b=json.loads(first.read_text()),json.loads(second.read_text())
            self.assertEqual([sum(f["durationMs"] for f in state["frames"]) for state in a["states"]],[83,33])
            self.assertEqual(a["states"],b["states"])
            self.assertEqual((first.parent/"atlas.png").read_bytes(),(second.parent/"atlas.png").read_bytes())
            self.assertEqual(len(list((root/"second/parts").glob("*.png"))),6)


if __name__=="__main__":
    unittest.main()
