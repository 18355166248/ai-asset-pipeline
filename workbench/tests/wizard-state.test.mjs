import test from 'node:test';
import assert from 'node:assert/strict';
import {createStore} from 'jotai';
import {wizardAtom,confirmedAtom,acceptedAtom,updateWizardAtom,restoreWizard} from '../src/state/wizard.ts';
test('Jotai改动身份清除确认和验收，修改动作只清除验收',()=>{const s=createStore();s.set(confirmedAtom,true);s.set(acceptedAtom,true);s.set(updateWizardAtom,{timing:'800ms'});assert.equal(s.get(confirmedAtom),true);assert.equal(s.get(acceptedAtom),false);s.set(acceptedAtom,true);s.set(updateWizardAtom,{identity:'猫'});assert.equal(s.get(confirmedAtom),false);assert.equal(s.get(acceptedAtom),false);assert.equal(s.get(wizardAtom).identity,'猫');});
test('旧草稿迁移仅恢复有效文本与尺寸，不恢复确认或非法动作',()=>{const v=restoreWizard({reference:'/hero.png',cell:'256',display:'128',actions:['走路','非法'],confirmed:true,accepted:true});assert.equal(v.reference,'/hero.png');assert.equal(v.cell,256);assert.deepEqual(v.actions,['走路']);assert.equal(v.confirmed,undefined);assert.equal(restoreWizard(null).cell,256);});
