import test from 'node:test';
import assert from 'node:assert/strict';
import { SpriteController } from '../../examples/export-workbench/sprite-controller.mjs';
const frame = ms => ({ x: 0, y: 0, w: 256, h: 256, durationMs: ms });
const manifest = () => ({ kind: 'motion', anchor: [.5, .947], states: [
  { name: 'idle', loop: true, frames: [frame(400)] },
  { name: 'move', loop: true, frames: Array.from({length: 8}, () => frame(100)) },
  { name: 'attack', loop: false, frames: [frame(110), frame(80), frame(140)] },
  { name: 'hit', loop: false, frames: [frame(160)] },
  { name: 'jump', loop: false, frames: [frame(80),frame(60),frame(120),frame(80),frame(100)] }
] });
test('movement and release switch source poses without changing ground height', () => {
  const p = new SpriteController(manifest()); p.update(.1, 1); assert.equal(p.action, 'move'); assert.equal(p.x, 9);
  p.update(.1, -1); assert.equal(p.facing, -1); assert.equal(p.x, 0);
  p.update(.1, 0); assert.equal(p.action, 'idle'); assert.equal(p.y, 0);
});
test('jump uses source timing and separate height, rejects ground attack in air', () => {
  const p = new SpriteController(manifest()); p.trigger('jump'); p.update(.21); assert.equal(p.y, -40);
  assert.equal(p.trigger('attack'), false); assert.equal(p.y, -40);
  p.update(.13); assert.equal(p.y, 0); assert.equal(p.action, 'jump');
  p.update(.1); assert.equal(p.action, 'idle'); assert.equal(p.y, 0);
});
test('frame rate does not change the analytic jump at the same elapsed time', () => {
  const a = new SpriteController(manifest()), b = new SpriteController(manifest()); a.trigger('jump'); b.trigger('jump');
  a.update(.2); for(let i=0;i<20;i++) b.update(.01); assert.ok(Math.abs(a.y-b.y)<1e-9);
});
test('hit interrupts attack and attack ends back in idle', () => {
  const p = new SpriteController(manifest()); p.trigger('attack'); p.update(.15); assert.equal(p.update(0).index, 1);
  p.trigger('hit'); assert.equal(p.action, 'hit'); p.update(.16); assert.equal(p.action, 'idle');
  p.trigger('attack'); p.update(.33); assert.equal(p.action, 'idle');
});
test('invalid source durations and jump windows fail explicitly', () => {
  const m = manifest(); m.states[0].frames[0].durationMs = 0; assert.throws(()=>new SpriteController(m));
  assert.throws(()=>new SpriteController(manifest(),{landMs:500}));
  assert.throws(()=>new SpriteController(manifest()).update(NaN));
  const bad = manifest(); bad.anchor = [NaN,1]; assert.throws(()=>new SpriteController(bad));
  const looping = manifest(); looping.states.at(-1).loop = true; assert.throws(()=>new SpriteController(looping));
  const coords = manifest(); coords.states[0].frames[0].x = -1; assert.throws(()=>new SpriteController(coords));
});
test('idle breathing is continuous and resets for movement without root displacement', () => {
  const p = new SpriteController(manifest()); assert.equal(p.update(0).scaleY, 1);
  assert.equal(p.update(1.2).scaleY, 1.006); assert.equal(p.y, 0);
  assert.equal(p.update(1.2).scaleY, 1); assert.equal(p.y, 0);
  assert.equal(p.update(.1,1).scaleY, 1);
  const off = new SpriteController(manifest(), {breathAmplitude:0}); assert.equal(off.update(1.2).scaleY,1);
  assert.throws(()=>new SpriteController(manifest(),{breathAmplitude:.5}));
});
const transitions = () => {
  const m = manifest(); m.states.push({name:'move-start',loop:false,frames:[frame(60)]},{name:'move-stop',loop:false,frames:[frame(80)]}); return m;
};
test('optional start/stop clips handle short taps, re-entry and attack interruption', () => {
  const p = new SpriteController(transitions());p.update(.02,1);assert.equal(p.action,'move-start');
  p.update(.01,0);assert.equal(p.action,'move-stop');p.update(.01,1);assert.equal(p.action,'move-start');
  p.trigger('attack');assert.equal(p.action,'attack');p.update(.33);assert.equal(p.action,'idle');
  p.update(.06,1);assert.equal(p.action,'move');p.update(.08,0);assert.equal(p.action,'idle');assert.equal(p.y,0);
});
test('start/stop movement conserves elapsed time and distance across frame rates', () => {
  const a = new SpriteController(transitions()),b = new SpriteController(transitions());
  a.update(.2,1);for(let i=0;i<20;i++) b.update(.01,1);assert.ok(Math.abs(a.x-b.x)<1e-9);assert.ok(Math.abs(a.time-b.time)<1e-9);
  const before=a.x;a.update(.2,0);for(let i=0;i<20;i++)b.update(.01,0);assert.ok(Math.abs(a.x-b.x)<1e-9);assert.ok(Math.abs(a.x-before-3.6)<1e-9);
  assert.equal(a.action,'idle');assert.throws(()=>a.update(.1,NaN));
});
test('releasing in swing preserves the current source pose and reaches the next authored contact', () => {
  const m=transitions();m.states.find(c=>c.name==='move').frames.forEach((f,i)=>f.x=i*256);
  for(const index of [1,2,3,5,6,7]) {
    const p=new SpriteController(m,{stopContactFrames:[0,4]});p.update(.06+index*.1+.05,1);
    const before=p.update(0,1).frame;const released=p.update(0,0);
    assert.equal(released.action,'move-settle');assert.equal(released.frame.x,before.x);
    const next=index<4?4:0;assert.equal(p.settleClip.frames.at(-1).x,next*256);
    p.update(1,0);assert.equal(p.action,'idle');assert.equal(p.y,0);
  }
});
test('settling preserves distance across timestep sizes and allows immediate re-entry or hit', () => {
  const options={stopContactFrames:[0,4]};const a=new SpriteController(transitions(),options),b=new SpriteController(transitions(),options);
  a.update(.21,1);b.update(.21,1);const start=a.x;
  a.update(.5,0);for(let i=0;i<50;i++)b.update(.01,0);
  assert.ok(Math.abs(a.x-b.x)<1e-8);assert.ok(Math.abs(a.x-start-13.05)<1e-8);assert.equal(a.action,'idle');
  const p=new SpriteController(transitions(),options);p.update(.21,1);p.update(.05,0);assert.equal(p.action,'move-settle');
  const speed=p.currentSpeed();p.update(0,1);assert.equal(p.action,'move-start');assert.ok(Math.abs(p.currentSpeed()-speed)<1e-9);
  p.update(.1,1);p.update(.01,0);p.trigger('hit');assert.equal(p.action,'hit');
});
test('short-tap release decelerates from actual speed instead of jumping to full speed', () => {
  const p=new SpriteController(transitions());p.update(.02,1);const start=p.x;
  p.update(.08,0);assert.ok(Math.abs(p.x-start-1.2)<1e-9);assert.equal(p.action,'idle');
});
test('contact hints must be distinct valid indices of a looping move clip', () => {
  for(const indices of [[8],[-1],[.5],[0,0]]) assert.throws(()=>new SpriteController(transitions(),{stopContactFrames:indices}));
  const m=transitions();m.states.find(c=>c.name==='move').loop=false;
  assert.throws(()=>new SpriteController(m,{stopContactFrames:[0]}));
});
const contactStops = () => {
  const m = transitions();
  m.states.push({name:'stop-front',loop:false,frames:[{...frame(120),x:512}]});
  return m;
};
test('authored contact stop is selected both on contact and after settling, then returns idle', () => {
  for (const phase of [.4,.25]) {
    const p = new SpriteController(contactStops(),{stopContactFrames:[0,4],stopClipsByContact:{4:'stop-front'}});
    p.update(.06+phase,1); p.update(0,0);
    if (phase===.25) {assert.equal(p.action,'move-settle');p.update(.15+.04,0);}
    assert.equal(p.action,'move-stop'); assert.equal(p.currentClip().name,'stop-front');
    assert.equal(p.update(0).frame.x,512);p.update(.12,0);assert.equal(p.action,'idle');
  }
});
test('contact variants conserve time and distance and allow interruption without stale selection', () => {
  const options={stopContactFrames:[0,4],stopClipsByContact:{4:'stop-front'}};
  const a=new SpriteController(contactStops(),options),b=new SpriteController(contactStops(),options);
  a.update(.31,1);b.update(.31,1);a.update(.5,0);for(let i=0;i<50;i++)b.update(.01,0);
  assert.equal(a.action,'idle');assert.equal(b.action,'idle');assert.ok(Math.abs(a.x-b.x)<1e-9);
  a.update(.46,1);a.update(0,0);assert.equal(a.currentClip().name,'stop-front');
  a.update(.01,1);assert.equal(a.action,'move-start');a.update(0,0);assert.equal(a.currentClip().name,'move-stop');
  a.trigger('hit');assert.equal(a.action,'hit');
});
test('contact stop mapping rejects missing, looping, core and non-contact clips', () => {
  for(const mapping of [null,[],{3:'stop-front'},{4:'missing'},{4:'idle'},{4:'attack'},{'04':'stop-front'}]) {
    assert.throws(()=>new SpriteController(contactStops(),{stopContactFrames:[0,4],stopClipsByContact:mapping}));
  }
  const m=contactStops();m.states.at(-1).loop=true;
  assert.throws(()=>new SpriteController(m,{stopContactFrames:[4],stopClipsByContact:{4:'stop-front'}}));
});
const stagedStart = () => {
  const m=transitions();m.states.find(s=>s.name==='move-start').frames=Array.from({length:4},(_,i)=>({...frame(25),x:i*256}));return m;
};
test('short start cancellation reverses only visited source poses, then actual idle', () => {
  const p=new SpriteController(stagedStart(),{reverseStartOnRelease:true});p.update(.04,1);const before=p.update(0,1);
  const r=p.update(0,0);assert.equal(r.frame.x,before.frame.x);assert.equal(p.currentClip().name,'move-start-cancel');
  assert.deepEqual(p.currentClip().frames.map(f=>f.x),[256,0,0]);
  assert.deepEqual(p.currentClip().frames.map(f=>f.durationMs),[15,25,40]);
  p.update(.08,0);assert.equal(p.action,'idle');
});
test('reversing a cancelled start preserves integration and allows immediate movement or hit', () => {
  const a=new SpriteController(stagedStart(),{reverseStartOnRelease:true}),b=new SpriteController(stagedStart(),{reverseStartOnRelease:true});
  a.update(.065,1);b.update(.065,1);a.update(.2,0);for(let i=0;i<20;i++)b.update(.01,0);assert.ok(Math.abs(a.x-b.x)<1e-9);assert.equal(a.action,'idle');
  a.update(.04,1);a.update(.01,0);const speed=a.currentSpeed();a.update(0,1);assert.equal(a.action,'move-start');assert.equal(a.currentSpeed(),speed);a.trigger('hit');assert.equal(a.action,'hit');
});
test('reverse-start option rejects non-booleans and leaves single-frame fallback unchanged', () => {
  assert.throws(()=>new SpriteController(stagedStart(),{reverseStartOnRelease:1}));
  const p=new SpriteController(transitions(),{reverseStartOnRelease:true});p.update(.02,1);p.update(0,0);assert.equal(p.currentClip().name,'move-stop');
});
