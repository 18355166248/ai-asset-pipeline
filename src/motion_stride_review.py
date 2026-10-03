"""检查人工标记的步行支撑点与移动速度；不识别肢体，不修改原画或批准步态。"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import tempfile

import numpy as np
from PIL import Image, ImageDraw

from asset_bundle import read_json, within, write_json
from character_workbench import load_sprite


def drift(samples, speed, scale, direction=1):
    groups = {}
    for sample in samples:
        groups.setdefault(sample['group'], []).append(sample)
    total = 0
    result = []
    for name, points in groups.items():
        xs = np.array([p['timeMs']/1000*speed*direction+p['point'][0]*scale for p in points])
        residual = xs-xs.mean()
        total += float(np.sum(residual**2))
        result.append({'group':name, 'rangePixels':float(np.ptp(xs)), 'relativeWorldX':[float(x-xs[0]) for x in xs]})
    return {'rmsPixels':math.sqrt(total/len(samples)), 'groups':result}


def review(config_path, out):
    config_path, out = config_path.resolve(), out.resolve()
    config = read_json(config_path)
    if config.get('version') != 1:
        raise ValueError('需要version=1')
    source = (config_path.parent/config['manifest']).resolve()
    data, _ = load_sprite({'manifest':str(source)},source.parent)
    manifest = read_json(source)
    state = next((s for s in manifest['states'] if s['name']==config.get('action')),None)
    if state is None or not state['loop']:
        raise ValueError('需要存在的循环动作')
    kind = config.get('markerKind')
    if kind not in {'fixed-point','contact-region'}:
        raise ValueError('明确markerKind为fixed-point或contact-region')
    direction=config.get('direction',1)
    if type(direction) is not int or direction not in (-1,1):raise ValueError('direction需要1或-1，源图朝向需与它匹配')
    speed, scale = config.get('speed',90),config.get('renderScale',1)
    for n,label,minimum in [(speed,'speed',0),(scale,'renderScale',1e-9)]:
        if type(n) not in (int,float) or not math.isfinite(n) or n<minimum:
            raise ValueError('无效'+label)
    if speed>10000 or scale>16:raise ValueError('检查速度需0..10000，原画缩放需0..16')
    threshold = config.get('alphaThreshold',128)
    if type(threshold) is not int or not 1<=threshold<=255:
        raise ValueError('alphaThreshold需要1..255整数')
    observations = config.get('observations')
    if not isinstance(observations,list) or len(observations)<2:
        raise ValueError('至少两个显式标记')
    if out.exists() or out==source.parent or source.parent in out.parents:
        raise ValueError('输出已存在或位于源包内')
    atlas_path = within(source.parent,manifest['atlas'])
    atlas = Image.open(atlas_path).convert('RGBA')
    samples, crops, seen = [],[],set()
    starts = [sum(f['durationMs'] for f in state['frames'][:i]) for i in range(len(state['frames']))]
    for item in observations:
        if not isinstance(item,dict):raise ValueError('标记需要JSON对象')
        index,group = item.get('frame'),item.get('group')
        if type(index) is not int or not 0<=index<len(state['frames']) or not isinstance(group,str) or not group or (index,group) in seen:
            raise ValueError('需要有效且不重复的frame/group')
        seen.add((index,group))
        f = state['frames'][index]
        image = atlas.crop((f['x'],f['y'],f['x']+f['w'],f['y']+f['h']))
        if kind=='contact-region':
            rect = item.get('rect')
            if not isinstance(rect,list) or len(rect)!=4 or any(type(n) is not int for n in rect) or not 0<=rect[0]<rect[2]<=f['w'] or not 0<=rect[1]<rect[3]<=f['h']:
                raise ValueError('需要画布内的显式rect')
            pixels = np.array(image.crop(tuple(rect)))
            ys,xs = np.where(pixels[:,:,3]>=threshold)
            if len(xs)==0:
                raise ValueError('区域没有达到alpha阈值的像素')
            # 只测量人工框内最下两行的轮廓接触区域，不把轮廓中心冒充固定脚掌关节。
            bottom = int(ys.max()); band = ys>=bottom-1
            point = [float(np.mean(xs[band]+rect[0])),float(bottom+rect[1])]
        else:
            point = item.get('point');rect=None
            if not isinstance(point,list) or len(point)!=2 or any(type(n) not in (int,float) or not math.isfinite(n) for n in point) or not 0<=point[0]<f['w'] or not 0<=point[1]<f['h']:
                raise ValueError('需要画布内的显式point')
        samples.append({'frame':index,'group':group,'timeMs':starts[index],'point':point,'region':rect})
        crops.append(image)
    # 标记输入可乱序；按真实帧时间排序，避免图表把未来点折回过去。
    ordered=sorted(zip(samples,crops),key=lambda pair:(pair[0]['timeMs'],pair[0]['group']))
    samples,crops=map(list,zip(*ordered))
    if any(sum(s['group']==g for s in samples)<2 for g in {s['group'] for s in samples}):
        raise ValueError('每组至少两个标记')
    groups = {g:[s for s in samples if s['group']==g] for g in {s['group'] for s in samples}}
    numerator = denominator = 0
    for points in groups.values():
        ts = np.array([p['timeMs']/1000 for p in points]);xs=np.array([p['point'][0]*scale for p in points])
        numerator += float(np.sum((ts-ts.mean())*(xs-xs.mean())))
        denominator += float(np.sum((ts-ts.mean())**2))
    if denominator==0:
        raise ValueError('组内需要不同时间的标记')
    fit = -numerator/denominator/direction
    report = {'markerKind':kind,'direction':direction,'samples':samples,'speed':speed,'renderScale':scale,'diagnosticFitSpeed':fit,
              'current':drift(samples,speed,scale,direction),'fit':drift(samples,fit,scale,direction),'status':'diagnostic-only',
              'sourceManifestSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'atlasSha256':hashlib.sha256(atlas_path.read_bytes()).hexdigest(),
              'note':'人工标记；contact-region会随脚掌滚动/轮廓变化而移动。拟合只比较标记轨迹，不自动调速，不证明脚掌身份、承重或步态通过。恒速检查不覆盖起停、跳跃或镜像。'}
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.stride-review-',dir=out.parent) as temporary:
        stage=Path(temporary)/'result';stage.mkdir()
        write_json(stage/'report.json',report);write_json(stage/'input.json',config)
        width=max(im.width for im in crops);height=max(im.height for im in crops)+34
        sheet=Image.new('RGB',(width*4,height*math.ceil(len(crops)/4)),(28,42,50))
        draw=ImageDraw.Draw(sheet)
        for i,(image,sample) in enumerate(zip(crops,samples)):
            x,y=(i%4)*width,(i//4)*height
            sheet.paste(image,(x,y+28),image)
            draw.text((x+6,y+5),f'{sample["frame"]} / {sample["group"]}',fill='white')
            if sample['region']:
                l,t,r,b=sample['region'];draw.rectangle((x+l,y+28+t,x+r-1,y+28+b-1),outline='#719eab')
            px,py=sample['point'];draw.ellipse((x+px-3,y+28+py-3,x+px+3,y+28+py+3),fill='#ffd083')
        sheet.save(stage/'markers.png')
        template=(Path(__file__).resolve().parents[1]/'examples/stride-review.html').read_text()
        payload=json.dumps(report,ensure_ascii=False).replace('<','\\u003c')
        (stage/'index.html').write_text(template.replace('@@REPORT@@',payload))
        stage.rename(out)
    return out


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    try:print(review(args.config,args.out))
    except (ValueError,KeyError,OSError) as e:parser.exit(2,str(e)+'\n')
