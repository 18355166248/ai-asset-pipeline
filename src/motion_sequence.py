"""按显式配置跨动作选帧、复用与改时长；保留原画与来源，不生成或插值图像。"""
import argparse
import hashlib
import math
from pathlib import Path
import shutil
import tempfile

from PIL import Image

from asset_bundle import build, read_json, write_json, within
from character_workbench import load_sprite


def assemble(config_path, out):
    config_path, out = config_path.resolve(), out.resolve()
    config = read_json(config_path)
    if config.get('version') != 1 or not config.get('inputs') or not isinstance(config['inputs'], list):
        raise ValueError('需要version=1和非空inputs')
    if not isinstance(config.get('states'), list) or not config['states']:
        raise ValueError('需要非空states')
    sources, anchor = [], None
    for item in config['inputs']:
        path = (config_path.parent / item['manifest']).resolve()
        data, _ = load_sprite({'manifest':str(path)}, path.parent)
        manifest = read_json(path)
        if anchor is None:
            anchor = data['anchor']
        elif anchor != data['anchor']:
            raise ValueError('锚点不一致，不能跨角色直接编排')
        atlas_path = within(path.parent,manifest['atlas'])
        sources.append((path,atlas_path,manifest,Image.open(atlas_path).convert('RGBA')))
    clips, names, cell, count = [], set(), None, 0
    for state in config['states']:
        name = state.get('name')
        if not isinstance(name,str) or not name or name in names:
            raise ValueError('动作名需要非空且不重复')
        names.add(name)
        if type(state.get('loop')) is not bool or not isinstance(state.get('frames'),list) or not state['frames']:
            raise ValueError('需要明确loop与非空frames')
        frames = []
        for ref in state['frames']:
            index, frame_index = ref.get('input'),ref.get('frame')
            if type(index) is not int or not 0 <= index < len(sources):
                raise ValueError('input索引越界或不是整数')
            _,_,manifest,atlas = sources[index]
            source_state = next((s for s in manifest['states'] if s['name']==ref.get('action')),None)
            if source_state is None:
                raise ValueError('源动作不存在')
            if type(frame_index) is not int or not 0 <= frame_index < len(source_state['frames']):
                raise ValueError('frame索引越界或不是整数')
            original = source_state['frames'][frame_index]
            duration = ref.get('durationMs',original['durationMs'])
            if type(duration) not in (int,float) or not math.isfinite(duration) or duration <= 0:
                raise ValueError('durationMs需要正有限数')
            size = (original['w'],original['h'])
            if cell is None:
                cell = size
            elif cell != size:
                raise ValueError('画布不一致，不通过缩放掩盖差异')
            image = atlas.crop((original['x'],original['y'],original['x']+size[0],original['y']+size[1]))
            frames.append((image,duration,{'input':index,'action':source_state['name'],'frame':frame_index,'originalDurationMs':original['durationMs'],'durationMs':duration}))
        count += len(frames)
        clips.append((state,frames))
    if count*cell[0] > 16384:
        raise ValueError('源图集超过16384像素，请拆分动作')
    if out.exists():
        raise ValueError('输出已存在，不覆盖批次')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.motion-sequence-',dir=out.parent) as temporary:
        stage = Path(temporary)/'result'
        stage.mkdir()
        records = []
        for i,(path,atlas_path,manifest,_) in enumerate(sources):
            folder = stage/'inputs'/f'{i:03d}'
            folder.mkdir(parents=True)
            copied = dict(manifest,atlas='atlas.png')
            write_json(folder/'manifest.json',copied)
            shutil.copy2(path,folder/'original-manifest.json')
            shutil.copy2(atlas_path,folder/'atlas.png')
            audits = []
            root = path.parent.parent if path.parent.name=='bundle' else path.parent
            # 原始审查随包保存；编排与改时长仍是新草稿，不继承整套通过状态。
            for filename in ('generation-review.json','provenance.json','processing.json'):
                audit = root/filename
                if audit.is_file():
                    shutil.copy2(audit,folder/filename)
                    audits.append({'path':f'inputs/{i:03d}/{filename}','sha256':hashlib.sha256(audit.read_bytes()).hexdigest()})
            records.append({'manifest':f'inputs/{i:03d}/manifest.json','originalManifest':f'inputs/{i:03d}/original-manifest.json','atlas':f'inputs/{i:03d}/atlas.png','originalManifestSha256':hashlib.sha256(path.read_bytes()).hexdigest(),'atlasSha256':hashlib.sha256(atlas_path.read_bytes()).hexdigest(),'auditCopies':audits})
        sheet = Image.new('RGBA',(count*cell[0],cell[1]))
        descriptor = {'frames':[],'meta':{'image':'source.png','frameTags':[]}}
        sequence, cursor = [], 0
        for state,frames in clips:
            start = cursor
            for im,duration,ref in frames:
                # 直接搬运RGBA原画，不做alpha合成，避免半透明边缘被预乘或丢失。
                sheet.paste(im,(cursor*cell[0],0))
                descriptor['frames'].append({'frame':{'x':cursor*cell[0],'y':0,'w':cell[0],'h':cell[1]},'duration':duration,'trimmed':False,'rotated':False})
                cursor += 1
            descriptor['meta']['frameTags'].append({'name':state['name'],'from':start,'to':cursor-1,'direction':'forward'})
            sequence.append({'name':state['name'],'loop':state['loop'],'frames':[r for _,_,r in frames]})
        sheet.save(stage/'source.png')
        write_json(stage/'source.json',descriptor)
        provenance = {'provider':'explicit-motion-sequence','status':'draft','imageGenerationCalls':0,'inputs':records,'sequence':sequence,'note':'Reuse/retiming only. Source generation counts and reviews are retained in input records, not newly performed or approved.'}
        write_json(stage/'provenance.json',provenance)
        recipe = {'version':1,'kind':'motion','title':config.get('title','原画编排草稿'),'cell':list(cell),'anchor':anchor,'background':'keep','source':provenance,'states':[{'name':s['name'],'loop':s['loop'],'fps':10} for s,_ in clips]}
        write_json(stage/'recipe.json',recipe)
        build(stage/'recipe.json',stage/'source.json',stage/'bundle',aseprite=True)
        # 契约验证与导出完成后原子发布，失败不留下半包、不修改上游素材。
        stage.rename(out)
    return out/'bundle/manifest.json'


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    try:
        print(assemble(args.config,args.out))
    except (ValueError,KeyError,TypeError,OSError) as error:
        parser.error(str(error))
