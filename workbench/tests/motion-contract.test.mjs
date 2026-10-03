import test from 'node:test';
import assert from 'node:assert/strict';
import {frameAt,totalMs,withDuration,reorder,splitPose,editAction} from '../src/motion-contract.ts';
const pose=(id,ms)=>({image:id,rgbaSha256:id,durationMs:ms});
const move={name:'move',loop:true,frames:[pose('a',110),pose('b',80),pose('c',80),pose('d',60)]};
test('原画精确边界与完整循环由durationMs驱动',()=>{assert.equal(totalMs(move),330);for(const [time,index] of [[0,0],[109,0],[110,1],[189,1],[190,2],[269,2],[270,3],[329,3],[330,0]])assert.equal(frameAt(move,time),index);assert.equal(frameAt({...move,loop:false},330),3);});
test('补帧拆分保持总时长，重排与重复引用按真实实例计时',()=>{const split=splitPose(move,0,pose('new',1),60);assert.equal(totalMs(split),330);assert.deepEqual(split.frames.map(f=>f.durationMs),[60,50,80,80,60]);assert.equal(totalMs(reorder(move,[3,2,1,0])),330);assert.equal(totalMs(reorder(move,[0,1,1,2,3])),410);assert.equal(move.frames.length,4);});
test('修改仅清除目标动作验收，不修改原契约',()=>{const contract={version:1,title:'role',cell:[256,256],anchor:[.5,.95],states:[move,{...move,name:'idle'}],reviews:{move:{verdict:'user-accept',fingerprint:'old',evidence:'user'},idle:{verdict:'user-accept',fingerprint:'idle',evidence:'user'}}};const next=editAction(contract,withDuration(move,1,50));assert.equal(next.reviews.move,undefined);assert.equal(next.reviews.idle.verdict,'user-accept');assert.equal(contract.reviews.move.verdict,'user-accept');assert.equal(contract.states[0].frames[1].durationMs,80);});
test('非法时长、拆分与空序列拒绝，不能静默取整',()=>{for(const value of [0,80.5,NaN,Infinity,60001])assert.throws(()=>withDuration(move,0,value));assert.throws(()=>reorder(move,[]));assert.throws(()=>reorder(move,[-1]));assert.throws(()=>splitPose(move,0,pose('n',1),110));});
