"""复现本次显式原画裁切与六帧出拳编排；不调用GPT或批准美术。"""
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
from motion_region_lock import rectangle_patch


def assemble(out):
    if out.exists():
        raise ValueError('不覆盖已有批次')
    folder = Path(__file__).resolve().parent
    job = load_job(folder / 'job.json')
    source = folder / 'assembly-reference'
    def read(action, index):
        return Image.open(source / f'{action}-{index:04d}.png').convert('RGBA')
    old = [read('attack', i) for i in range(3)]
    intermediates, checks = [], []
    rect, protect = (85,88,218,138), (0,0,163,100)
    for index, base in enumerate(old[:2]):
        frame = job['frames'][f'attack-inbetween-{index:03d}']
        attempt = frame['attempts'][frame['selected']]
        path = folder / attempt['frame']
        if hashlib.sha256(path.read_bytes()).hexdigest() != attempt['frameSha256']:
            raise ValueError('选定来源已改动')
        candidate = Image.open(path).convert('RGBA').resize(base.size, Image.Resampling.LANCZOS)
        # 手臂与背景守势拳贴近脸，单矩形会混入下巴；显式保护母版头部，避免第三只拳与脸部重影。
        patched = rectangle_patch(base,candidate,rect,2)
        patched.paste(base.crop(protect),(protect[0],protect[1]))
        for area in [(0,0,256,88),(0,138,256,256),(0,88,85,138),(218,88,256,138),protect]:
            assert patched.crop(area).tobytes() == base.crop(area).tobytes()
        intermediates.append(patched)
        checks.append({'index':index,'sourceFrame':attempt['frame'],'sourceSha256':attempt['frameSha256'],'reference':f'attack/{index:04d}.png','rect':rect,'feather':2,'protectedHead':protect,'outsideAndHeadEqual':True})
    frames=[old[0],intermediates[0],old[1],intermediates[1],old[2],read('idle',0)]
    durations=[70,40,80,45,35,60]
    # 冲击原画仍从110ms开始到190ms结束，总长330ms；末帧复用idle，避免收招结束再切一次不同站姿。
    assert sum(durations)==330 and sum(durations[:2])==110 and sum(durations[:3])==190
    out.mkdir(parents=True)
    sheet=Image.new('RGBA',(256*6,256))
    for i, image in enumerate(frames): sheet.paste(image,(i*256,0))
    sheet.save(out/'source.png')
    descriptor={'frames':[{'filename':f'{i:04d}','frame':{'x':i*256,'y':0,'w':256,'h':256},'duration':duration,'trimmed':False,'rotated':False} for i,duration in enumerate(durations)],'meta':{'image':'source.png','frameTags':[{'name':'attack','from':0,'to':5,'direction':'forward'}]}}
    (out/'source.json').write_text(json.dumps(descriptor,indent=2)+'\n')
    provenance={'provider':'codex-builtin-imagegen-plus-existing-frame-assembly','status':'draft','actualGptCalls':3,'job':str(folder/'job.json'),'failedRetractionPreserved':True,'patches':checks,'durationsMs':durations,'impactStartMs':110,'impactEndMs':190,'totalMs':330,'finalFrame':'existing idle/0000.png','note':'2 selected new source poses, four existing poses; cropped arms with explicit protected head. Whole new drawings not accepted.'}
    (out/'processing.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n')
    manifest=json.loads((folder/'assembly-source-manifest.json').read_text())
    recipe={'version':1,'kind':'motion','title':'六相位出拳候选','cell':[256,256],'anchor':manifest['anchor'],'background':'keep','source':provenance,'states':[{'name':'attack','loop':False,'fps':10}]}
    (out/'recipe.json').write_text(json.dumps(recipe,ensure_ascii=False,indent=2)+'\n')
    return build(out/'recipe.json',out/'source.json',out/'bundle',aseprite=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    print(assemble(parser.parse_args().out.resolve()))
