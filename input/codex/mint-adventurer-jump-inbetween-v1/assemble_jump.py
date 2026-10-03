"""编排整张原画跳跃；保持起落窗口，不合成关节或新增生成记录。"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
from asset_bundle import build
from motion_generation import load_job


def assemble(out):
    if out.exists():
        raise ValueError('不覆盖已有批次')
    folder = Path(__file__).resolve().parent
    refs = folder / 'assembly-reference'
    for name, digest in json.loads((folder / 'assembly-reference-index.json').read_text()).items():
        if hashlib.sha256((refs / name).read_bytes()).hexdigest() != digest:
            raise ValueError('旧原画来源已改动')
    def old(action, i):
        return Image.open(refs / f'{action}-{i:04d}.png').convert('RGBA')
    job = load_job(folder / 'job/job.json')
    new, selected = [], []
    for i in range(2):
        frame = job['frames'][f'jump-inbetween-{i:03d}']
        attempt = frame['attempts'][frame['selected']]
        path = folder / 'job' / attempt['frame']
        if hashlib.sha256(path.read_bytes()).hexdigest() != attempt['frameSha256']:
            raise ValueError('选定原画来源已改动')
        new.append(Image.open(path).convert('RGBA').resize((256,256),Image.Resampling.LANCZOS))
        selected.append({'frame':attempt['frame'],'sha256':attempt['frameSha256']})
    # 空中帧保留原画局部收腿，整体高度由消费端提供；不按脚底把悬空原画移回地面。
    frames = [new[0],old('jump',0),old('jump',1),new[1],old('jump',2),new[1],old('jump',3),old('jump',0),new[0],old('idle',0)]
    durations = [40,40,60,40,80,40,40,40,30,30]
    # 340ms接触地面后先复用压缩姿态吸收冲击，再回浅压缩与真实idle；440ms结束无额外换姿。
    assert sum(durations)==440 and sum(durations[:2])==80 and sum(durations[:7])==340
    out.mkdir(parents=True)
    sheet = Image.new('RGBA',(256*len(frames),256))
    for i, im in enumerate(frames): sheet.paste(im,(i*256,0))
    sheet.save(out/'source.png')
    descriptor={'frames':[{'filename':f'{i:04d}','frame':{'x':i*256,'y':0,'w':256,'h':256},'duration':d,'trimmed':False,'rotated':False} for i,d in enumerate(durations)],'meta':{'image':'source.png','frameTags':[{'name':'jump','from':0,'to':9,'direction':'forward'}]}}
    (out/'source.json').write_text(json.dumps(descriptor,indent=2)+'\n')
    provenance={'status':'draft','actualGptCalls':4,'selectedNewDrawings':2,'selected':selected,'sourceJob':str(folder/'job/job.json'),'durationsMs':durations,'launchMs':80,'landMs':340,'totalMs':440,'rootHeightPixels':40,'wholeFrames':True,'note':'10 frame positions, 7 distinct drawings. Half tuck is reused on ascent/descent; old crouch reused for landing absorption; final idle reused. No joint transform, temporal interpolation or new root height baked into art. Full animation acceptance pending.'}
    (out/'processing.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n')
    recipe={'version':1,'kind':'motion','title':'十相位跳跃候选','cell':[256,256],'anchor':[.5,.947265625],'background':'keep','source':provenance,'states':[{'name':'jump','loop':False,'fps':10}]}
    (out/'recipe.json').write_text(json.dumps(recipe,ensure_ascii=False,indent=2)+'\n')
    return build(out/'recipe.json',out/'source.json',out/'bundle',aseprite=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    print(assemble(parser.parse_args().out.resolve()))
