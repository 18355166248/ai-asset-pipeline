import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, readdirSync} from 'node:fs';
import {sampleTrack, samplePose, spriteFrame, smooth, initialCharacter, samplePreviewRoot} from '../../examples/export-workbench/motion.mjs';
import {Quaternion, Euler, Vector3} from 'three';

test('默认进入二维角色，并保留显式模型选择', () => {
  const characters = [{id:'rig',kind:'pivot'},{id:'hero',kind:'sprite'},{id:'model',kind:'glb'}];
  assert.equal(initialCharacter(characters),1);
  assert.equal(initialCharacter(characters,'model'),2);
  assert.equal(initialCharacter(characters.slice(0,1)),0);
});

test('跳跃预览高度在起落处归零，顶点与动作切换不残留位移', () => {
  const clip = {previewMotion:{kind:'jump-arc',heightPixels:40,startMs:100,endMs:340}};
  assert.equal(samplePreviewRoot(clip, .05), 0);
  assert.equal(samplePreviewRoot(clip, .1), 0);
  assert.equal(samplePreviewRoot(clip, .22), -40);
  assert.equal(samplePreviewRoot(clip, .34), 0);
  assert.equal(samplePreviewRoot(clip, .5), 0);
  assert.equal(samplePreviewRoot({}, .22), 0);
  assert.ok(samplePreviewRoot(clip, .18) < 0);
  assert.ok(samplePreviewRoot(clip, .18) >= -40);
});

test('非均匀帧时长、循环与单次末帧不会被等分', () => {
  const clip = {loop:false, frames:[{durationMs:40},{durationMs:160},{durationMs:80}]};
  assert.equal(spriteFrame(clip, 0.039), 0);
  assert.equal(spriteFrame(clip, 0.04), 1);
  assert.equal(spriteFrame(clip, 0.199), 1);
  assert.equal(spriteFrame(clip, 4), 2);
  clip.loop = true;
  assert.equal(spriteFrame(clip, 0.28), 0);
  assert.equal(spriteFrame(clip, 0.32), 1);
});
test('保形插值不超调，关键帧精确且内侧速度连续', () => {
  const keys = [[1,[0,0,0]],[3,[1,1,1]],[7,[2,2,2]],[9,[0,0,0]]];
  assert.deepEqual(sampleTrack(keys, 3), [1,1,1]);
  for (let frame = 1; frame <= 9; frame += 0.01) {
    const values = sampleTrack(keys, frame);
    assert.ok(values.every(v => v >= -1e-8 && v <= 2 + 1e-8));
  }
  const eps = 1e-5;
  const before = (sampleTrack(keys,3)[0] - sampleTrack(keys,3-eps)[0])/eps;
  const after = (sampleTrack(keys,3+eps)[0] - sampleTrack(keys,3)[0])/eps;
  assert.ok(Math.abs(before-after)<0.0001);
});
test('周期邻点保证接缝速度连续，不把同姿态当作全部验证', () => {
  const keys = [[1,[0,0,0]],[3,[1,0,0]],[7,[-1,0,0]],[9,[0,0,0]]], e = 1e-5;
  const entry = (sampleTrack(keys,1+e,true,9)[0] - sampleTrack(keys,1,true,9)[0])/e;
  const exit = (sampleTrack(keys,9,true,9)[0] - sampleTrack(keys,9-e,true,9)[0])/e;
  assert.ok(entry > 0.1 && Math.abs(entry-exit)<0.0001);
});
test('浏览器 ZYX 与 Blender XYZ 的 X→Y→Z 复合旋转一致', () => {
  const angles = [0.4, -0.7, 0.3];
  const q = new Quaternion().setFromEuler(new Euler(...angles,'ZYX'));
  const expected = new Vector3(1,2,3).applyAxisAngle(new Vector3(1,0,0),angles[0]).applyAxisAngle(new Vector3(0,1,0),angles[1]).applyAxisAngle(new Vector3(0,0,1),angles[2]);
  assert.ok(new Vector3(1,2,3).applyQuaternion(q).distanceTo(expected)<1e-12);
});
test('混合边界保持原姿态，180 度附近旋转走最短弧', () => {
  assert.equal(smooth(0),0); assert.equal(smooth(1),1);
  const a = new Quaternion().setFromEuler(new Euler(0,0,179*Math.PI/180));
  const b = new Quaternion().setFromEuler(new Euler(0,0,-179*Math.PI/180));
  const middle = a.clone().slerp(b,smooth(0.5));
  assert.ok(a.angleTo(middle)<2*Math.PI/180);
  assert.ok(a.clone().slerp(b,smooth(0)).angleTo(a)<1e-7);
});
for (const skeletonId of ['humanoid-basic','quadruped-basic']) {
  const skeleton = JSON.parse(readFileSync(new URL(`../../animation-library/skeletons/${skeletonId}.json`, import.meta.url)));
  const dir = new URL(`../../animation-library/clips/${skeletonId}/`, import.meta.url);
  for (const filename of readdirSync(dir)) if (filename.endsWith('.json')) {
    const clip = JSON.parse(readFileSync(new URL(filename, dir)));
    clip.fps = 24; clip.duration = (clip.end-1)/24;
    test(`${skeletonId}/${clip.id} 全身采样有限，循环姿态与速度相接`, () => {
      for (let i = 0; i <= 120; i++) {
        const pose = samplePose(skeleton, clip, clip.duration*i/120);
        assert.equal(Object.keys(pose).length,skeleton.parts.length);
        assert.ok(Object.values(pose).every(channels => Object.values(channels).flat().every(Number.isFinite)));
      }
      if (!clip.loop) {
        assert.deepEqual(samplePose(skeleton,clip,clip.duration),samplePose(skeleton,clip,clip.duration*2));
        return;
      }
      const e = 1e-6, start = samplePose(skeleton,clip,0), before = samplePose(skeleton,clip,clip.duration-e), after = samplePose(skeleton,clip,e);
      for (const part of skeleton.parts) for (const channel of ['rot','loc','scale']) for (let axis=0; axis<3; axis++) {
        const left = (start[part.id][channel][axis]-before[part.id][channel][axis])/e;
        const right = (after[part.id][channel][axis]-start[part.id][channel][axis])/e;
        assert.ok(Math.abs(left-right)<0.02, `${part.id}.${channel}: ${left} / ${right}`);
      }
    });
  }
}
