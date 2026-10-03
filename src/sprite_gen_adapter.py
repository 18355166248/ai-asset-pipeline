"""固定版本的sprite-gen适配层：显式时序、冻结原画、隔离候选与人工验收门禁。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib

from PIL import Image
from asset_bundle import read_json, write_json, within
from character_workbench import load_sprite

ROOT=Path(__file__).resolve().parents[1]
LOCK=ROOT/'config/sprite-gen.lock.json'
ENGINE=ROOT/'vendor/sprite-gen'
MODULES={'unpack':'sprite_gen.frames.unpack_atlas','compose':'sprite_gen.compose.compose_atlas','aseprite':'sprite_gen.compose.export_aseprite'}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def pixels(image):return hashlib.sha256(image.convert('RGBA').tobytes()).hexdigest()
def fingerprint(contract, action):
    state=next(s for s in contract['states'] if s['name']==action)
    return hashlib.sha256(json.dumps({'cell':contract['cell'],'anchor':contract['anchor'],'state':state},sort_keys=True).encode()).hexdigest()

def verify_engine():
    lock=read_json(LOCK)
    if not ENGINE.is_dir():raise ValueError('先运行scripts/fetch_sprite_gen.py获取固定引擎')
    for name,expected in lock['files'].items():
        data=within(ENGINE,name).read_bytes()
        actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if actual!=expected:raise ValueError('上游源码与锁版本不符：'+name)
    if tomllib.loads((ENGINE/'pyproject.toml').read_text())['project']['version']!=lock['version']:raise ValueError('引擎版本不符')
    return {k:lock[k] for k in ['repository','version','commit']}

def invoke(command, args, stage):
    # 不接受任意shell或自动改走视频；只执行已核验版本的本地素材命令。
    env=dict(os.environ,PYTHONPATH=str(ENGINE))
    result=subprocess.run([sys.executable,'-m',MODULES[command],*map(str,args)],env=env,cwd=stage,text=True,capture_output=True,timeout=60)
    (stage/f'engine-{command}.log').write_text(result.stdout+'\n'+result.stderr)
    if result.returncode:raise ValueError(f'sprite-gen {command}失败：'+(result.stderr or result.stdout)[-1500:])

def validate(run, contract):
    if contract.get('version')!=1 or not contract.get('states'):raise ValueError('无效动作契约')
    names=set()
    for s in contract['states']:
        if not re.fullmatch(r'[A-Za-z0-9_-]+',s['name']) or s['name'] in names:raise ValueError('动作名称无效或重复')
        names.add(s['name'])
        if type(s['loop']) is not bool or not s['frames']:raise ValueError('需要真实loop和非空序列')
        for frame in s['frames']:
            dt=frame['durationMs']
            if type(dt) is not int or not 1<=dt<=60000:raise ValueError('durationMs需1到60000的整数毫秒，拒绝导出静默取整')
            im=Image.open(within(run,frame['image'])).convert('RGBA')
            if list(im.size)!=contract['cell'] or pixels(im)!=frame['rgbaSha256']:raise ValueError('冻结原画被改动：'+frame['image'])
    return contract

def compose(stage, contract):
    validate(stage,contract)
    # 以显式原画实例重建引擎输入；不让旧curation、独立缩放或呼吸变形偷偷改变冻结帧。
    width,height=contract['cell']; count=sum(len(s['frames']) for s in contract['states'])
    if count*width>16384:raise ValueError('图集过宽，需拆分动作')
    atlas=Image.new('RGBA',(count*width,height));rows={};cursor=0
    for state in contract['states']:
        rects=[]
        for frame in state['frames']:
            im=Image.open(within(stage,frame['image'])).convert('RGBA');atlas.paste(im,(cursor*width,0))
            rects.append({'x':cursor*width,'y':0,'w':width,'h':height});cursor+=1
        rows[state['name']]=rects
    source=stage/'bridge';source.mkdir();atlas.save(source/'atlas.png')
    write_json(source/'manifest.json',{'game_input':'atlas.png','cell':{'width':width,'height':height},'frame_layout':{'rows':rows},'animation':{'rows':{s['name']:{'fps':10,'loop':s['loop']} for s in contract['states']}}})
    invoke('unpack',['--manifest',source/'manifest.json','--out-dir',stage/'engine-run'],stage)
    # 导入与合成各自校验，防止上游重新提取、调色板变化或引擎升级改变其他原画。
    for s in contract['states']:
        for i,frame in enumerate(s['frames']):
            if pixels(Image.open(stage/f"engine-run/frames/{s['name']}/frame-{i}.png"))!=frame['rgbaSha256']:raise ValueError('引擎导入改变原画像素')
    invoke('compose',['--run-dir',stage/'engine-run'],stage)
    upstream=stage/'engine-run/manifest.json';m=read_json(upstream);composed=Image.open(stage/'engine-run'/m['game_input']).convert('RGBA')
    repairs=0
    for s in contract['states']:
        rects=m['frame_layout']['rows'][s['name']]
        if len(rects)!=len(s['frames']):raise ValueError('引擎改动序列长度')
        for rect,frame in zip(rects,s['frames']):
            expected=Image.open(within(stage,frame['image'])).convert('RGBA');crop=composed.crop((rect['x'],rect['y'],rect['x']+rect['w'],rect['y']+rect['h']))
            if pixels(crop)!=frame['rgbaSha256']:
                # alpha_composite可能清除alpha=0像素的隐藏RGB。仅允许修复此类差异，不掩盖可见帧变动。
                if any(a!=b and (a[3]!=0 or b[3]!=0) for a,b in zip(crop.get_flattened_data(),expected.get_flattened_data())):raise ValueError('引擎合成改变可见原画')
                composed.paste(expected,(rect['x'],rect['y']));repairs+=1
        # 每次合成都从契约重建时序；上游fps只是布局预览参考，不能覆盖正式durationMs。
        m['animation']['rows'][s['name']]['durations_ms']=[f['durationMs'] for f in s['frames']]
        m['animation']['rows'][s['name']]['loop']=s['loop']
    composed.save(stage/'engine-run'/m['game_input']);write_json(upstream,m)
    invoke('aseprite',['--run-dir',stage/'engine-run'],stage)
    bundle=stage/'bundle';bundle.mkdir();shutil.copy2(stage/'engine-run'/m['game_input'],bundle/'atlas.png')
    ase=read_json(stage/'engine-run/exports/aseprite.json');ase['meta']['image']='atlas.png';write_json(bundle/'aseprite.json',ase)
    states=[]
    for s in contract['states']:
        states.append({'name':s['name'],'loop':s['loop'],'frames':[dict(rect,durationMs=frame['durationMs']) for rect,frame in zip(m['frame_layout']['rows'][s['name']],s['frames'])]})
    write_json(bundle/'manifest.json',{'version':1,'kind':'motion','title':contract['title'],'atlas':'atlas.png','anchor':contract['anchor'],'source':{'provider':'sprite-gen-adapter','status':'draft','engine':contract['engine']},'states':states})
    if [f['duration'] for f in ase['frames']]!=[f['durationMs'] for s in contract['states'] for f in s['frames']]:raise ValueError('Aseprite时序漂移')
    validate(stage,contract);write_json(stage/'compose-proof.json',{'engine':contract['engine'],'positions':count,'hiddenRgbRepairs':repairs,'rgbaVerified':True,'durationVerified':True,'imageGenerationCalls':0})
    write_json(stage/'motion-contract.json',contract)
    return bundle/'manifest.json'

def new_stage(out):
    out=out.resolve()
    if out.exists():raise ValueError('输出已存在，不覆盖批次')
    out.parent.mkdir(parents=True,exist_ok=True)
    return tempfile.TemporaryDirectory(prefix='.sprite-adapter-',dir=out.parent)

def import_bundle(manifest,out,actions):
    manifest,out=manifest.resolve(),out.resolve();engine=verify_engine();load_sprite({'manifest':str(manifest)},manifest.parent)
    m=read_json(manifest);atlas_path=within(manifest.parent,m['atlas']);atlas=Image.open(atlas_path).convert('RGBA')
    states=[s for s in m['states'] if not actions or s['name'] in actions]
    if not states or actions and set(actions)!={s['name'] for s in states}:raise ValueError('指定动作不存在')
    if out==manifest.parent or manifest.parent in out.parents:raise ValueError('输出不能放在源包中')
    with new_stage(out) as temporary:
        stage=Path(temporary)/'result';stage.mkdir();snapshot=stage/'source';snapshot.mkdir()
        shutil.copy2(manifest,snapshot/'manifest.json');shutil.copy2(atlas_path,snapshot/'atlas.png')
        contract={'version':1,'title':m.get('title','导入角色草稿'),'engine':engine,'cell':[states[0]['frames'][0]['w'],states[0]['frames'][0]['h']],'anchor':m['anchor'],'source':{'manifestSha256':sha(manifest),'atlasSha256':sha(atlas_path)},'states':[],'reviews':{}}
        for s in states:
            frames=[]
            for i,f in enumerate(s['frames']):
                if [f['w'],f['h']]!=contract['cell']:raise ValueError('动作画布不一致')
                if not re.fullmatch(r'[A-Za-z0-9_-]+',s['name']):raise ValueError('动作名称无效')
                image=atlas.crop((f['x'],f['y'],f['x']+f['w'],f['y']+f['h']));rel=f"frozen/{s['name']}/{i:04d}.png";path=stage/rel;path.parent.mkdir(parents=True,exist_ok=True);image.save(path)
                frames.append({'image':rel,'durationMs':f['durationMs'],'rgbaSha256':pixels(image)})
            contract['states'].append({'name':s['name'],'loop':s['loop'],'frames':frames})
        compose(stage,contract);stage.rename(out)
    return out/'bundle/manifest.json'

def candidate(run,action,index,image,out,note):
    run,out=run.resolve(),out.resolve();c=validate(run,read_json(run/'motion-contract.json'))
    state=next((s for s in c['states'] if s['name']==action),None)
    if state is None or type(index) is not int or not 0<=index<len(state['frames']):raise ValueError('候选动作或帧索引无效')
    im=Image.open(image).convert('RGBA')
    if list(im.size)!=c['cell']:raise ValueError('候选画布不同，不自动缩放或镜像')
    if not note.strip():raise ValueError('需要候选来源和修改说明')
    with new_stage(out) as temporary:
        stage=Path(temporary)/'candidate';stage.mkdir();shutil.copy2(image,stage/'raw.png');im.save(stage/'candidate.png')
        write_json(stage/'candidate.json',{'version':1,'action':action,'frame':index,'baselineFingerprint':fingerprint(c,action),'note':note,'rawSha256':sha(stage/'raw.png'),'rgbaSha256':pixels(im),'status':'candidate-only','generationCalls':'not-inferred'})
        stage.rename(out)
    return out/'candidate.json'

def select(run,candidate_dir,out):
    run,candidate_dir,out=run.resolve(),candidate_dir.resolve(),out.resolve();engine=verify_engine();c=validate(run,read_json(run/'motion-contract.json'));pick=read_json(candidate_dir/'candidate.json')
    state=next((s for s in c['states'] if s['name']==pick['action']),None)
    if state is None or type(pick['frame']) is not int or not 0<=pick['frame']<len(state['frames']):raise ValueError('候选帧索引无效')
    if pick['baselineFingerprint']!=fingerprint(c,pick['action']):raise ValueError('候选基准已过期')
    image=Image.open(candidate_dir/'candidate.png').convert('RGBA')
    if pixels(image)!=pick['rgbaSha256'] or list(image.size)!=c['cell'] or sha(candidate_dir/'raw.png')!=pick['rawSha256']:raise ValueError('候选文件被改动')
    with new_stage(out) as temporary:
        stage=Path(temporary)/'result';stage.mkdir();shutil.copytree(run/'frozen',stage/'frozen');shutil.copytree(run/'source',stage/'source');shutil.copytree(candidate_dir,stage/'selected-candidate')
        state=next(s for s in c['states'] if s['name']==pick['action']);frame=state['frames'][pick['frame']]
        shutil.copy2(candidate_dir/'candidate.png',within(stage,frame['image']));frame['rgbaSha256']=pick['rgbaSha256'];c['engine']=engine;c['reviews'].pop(pick['action'],None)
        c['selection']={'baseline':str(run),'candidate':'selected-candidate/candidate.json','action':pick['action'],'frame':pick['frame']}
        compose(stage,c);stage.rename(out)
    return out/'bundle/manifest.json'

def apply_plan(run,plan,out):
    run,out=run.resolve(),out.resolve();c=validate(run,read_json(run/'motion-contract.json'));request=read_json(plan)
    if request.get('version')!=1 or request.get('baselineContractSha256')!=sha(run/'motion-contract.json'):raise ValueError('时序草案基准已过期')
    if [s.get('name') for s in request.get('states',[])]!=[s['name'] for s in c['states']]:raise ValueError('草案不能新增或删除动作')
    known={(f['image'],f['rgbaSha256']) for s in c['states'] for f in s['frames']}
    for state,old in zip(request['states'],c['states']):
        if state['loop']!=old['loop']:raise ValueError('时序草案不能默默改变循环语义')
        for frame in state['frames']:
            if (frame['image'],frame['rgbaSha256']) not in known:raise ValueError('新原画需先隔离登记候选，不允许草案引入外部图片')
        if state!=old:c['reviews'].pop(state['name'],None)
    c['states']=request['states'];validate(run,c)
    with new_stage(out) as temporary:
        stage=Path(temporary)/'result';stage.mkdir();shutil.copytree(run/'frozen',stage/'frozen');shutil.copytree(run/'source',stage/'source');compose(stage,c);stage.rename(out)
    return out/'bundle/manifest.json'

def review(run,action,verdict,evidence,out):
    run,out=run.resolve(),out.resolve();c=validate(run,read_json(run/'motion-contract.json'));fp=fingerprint(c,action)
    if not evidence.strip():raise ValueError('需要实际检查或用户反馈证据')
    old=c['reviews'].get(action,{})
    if verdict=='user-accept' and (old.get('verdict')!='motion-pass' or old.get('fingerprint')!=fp):raise ValueError('先记录当前版本动作检查，再记录用户验收')
    with new_stage(out) as temporary:
        stage=Path(temporary)/'result';shutil.copytree(run,stage)
        c['reviews'][action]={'verdict':verdict,'fingerprint':fp,'evidence':evidence,'motionPassed':verdict=='motion-pass' or verdict=='user-accept','motionEvidence':old.get('evidence') if verdict=='user-accept' else evidence}
        write_json(stage/'motion-contract.json',c);stage.rename(out)
    return out/'motion-contract.json'

def export(run,out,release=False):
    run,out=run.resolve(),out.resolve();verify_engine();c=validate(run,read_json(run/'motion-contract.json'))
    # 文件有效、动作检查、用户验收分别记录；未验收走路不能通过正式交付门禁。
    if release:
        for s in c['states']:
            r=c['reviews'].get(s['name'],{})
            if r.get('verdict')!='user-accept' or r.get('fingerprint')!=fingerprint(c,s['name']):raise ValueError('未通过当前版本用户验收：'+s['name'])
    with new_stage(out) as temporary:
        stage=Path(temporary)/'result';stage.mkdir();shutil.copytree(run/'frozen',stage/'frozen');shutil.copytree(run/'source',stage/'source');compose(stage,c)
        write_json(stage/'delivery.json',{'status':'user-accepted' if release else 'draft','actions':[s['name'] for s in c['states']],'approvedActions':[s['name'] for s in c['states']] if release else [],'reviews':c['reviews'],'engine':c['engine']})
        stage.rename(out)
    return out/'bundle/manifest.json'

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);subs=p.add_subparsers(dest='command',required=True)
    a=subs.add_parser('import');a.add_argument('--manifest',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--actions',nargs='+')
    a=subs.add_parser('candidate');a.add_argument('--run',type=Path,required=True);a.add_argument('--action',required=True);a.add_argument('--frame',type=int,required=True);a.add_argument('--image',type=Path,required=True);a.add_argument('--note',required=True);a.add_argument('--out',type=Path,required=True)
    a=subs.add_parser('select');a.add_argument('--run',type=Path,required=True);a.add_argument('--candidate',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
    a=subs.add_parser('apply');a.add_argument('--run',type=Path,required=True);a.add_argument('--plan',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
    a=subs.add_parser('review');a.add_argument('--run',type=Path,required=True);a.add_argument('--action',required=True);a.add_argument('--verdict',choices=['motion-pass','user-accept','reject'],required=True);a.add_argument('--evidence',required=True);a.add_argument('--out',type=Path,required=True)
    a=subs.add_parser('export');a.add_argument('--run',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--release',action='store_true')
    args=p.parse_args()
    try:
        if args.command=='import':result=import_bundle(args.manifest,args.out,args.actions)
        elif args.command=='candidate':result=candidate(args.run,args.action,args.frame,args.image,args.out,args.note)
        elif args.command=='select':result=select(args.run,args.candidate,args.out)
        elif args.command=='apply':result=apply_plan(args.run,args.plan,args.out)
        elif args.command=='review':result=review(args.run,args.action,args.verdict,args.evidence,args.out)
        else:result=export(args.run,args.out,args.release)
        print(result)
    except (ValueError,KeyError,OSError,StopIteration) as e:p.error(str(e))
