"""把现有二维动作包交付成一个可浏览、下载与接入的验收站；不调用生图或批准素材。"""
import argparse
import hashlib
import html
import math
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile
from PIL import Image

from asset_bundle import read_json, write_json, within
from character_workbench import build as build_workbench, load_sprite
from godot_sprite_export import export as export_godot

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'examples'))
from make_sprite_playground import build as build_playable


def zip_tree(root, destination):
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob('*')):
            if path.is_symlink():
                raise ValueError('交付包不包含符号链接')
            if path.is_file():
                archive.write(path,path.relative_to(root))


def build(manifest_path, out, controller_options=None):
    manifest_path,out=manifest_path.resolve(),out.resolve()
    data,_=load_sprite({'manifest':str(manifest_path)},manifest_path.parent)
    manifest=read_json(manifest_path)
    if out.exists():
        raise ValueError('输出已存在，保留已有验收批次')
    if out==manifest_path.parent or manifest_path.parent in out.parents:
        raise ValueError('输出不能位于源素材包内部')
    atlas_path=within(manifest_path.parent,manifest['atlas'])
    names={s['name'] for s in manifest['states']}
    if not {'idle','move','attack','hit','jump'} <= names:
        raise ValueError('可操作交付需要idle/move/attack/hit/jump五动作')
    if any(s['loop'] for s in manifest['states'] if s['name'] in {'attack','hit','jump'}):
        raise ValueError('受击/攻击/跳跃需要非循环')
    options=read_json(controller_options) if controller_options else {}
    if not isinstance(options,dict):raise ValueError('控制器配置需要JSON对象')
    for key,default,minimum,maximum in [('speed',90,0,None),('jumpHeight',40,0,None),('breathAmplitude',.006,0,.02),('breathPeriod',2.4,.5,20),('contactHoldMs',40,0,200)]:
        value=options.get(key,default)
        inclusive=key in {'breathAmplitude','breathPeriod'}
        if type(value) not in (int,float) or not math.isfinite(value) or (value<minimum if inclusive else value<=minimum) or (maximum is not None and value>maximum):
            raise ValueError('无效控制器参数: '+key)
    move=next(s for s in manifest['states'] if s['name']=='move')
    contacts=options.get('stopContactFrames',[])
    if not isinstance(contacts,list) or any(type(i) is not int or not 0<=i<len(move['frames']) for i in contacts) or len(set(contacts))!=len(contacts) or (contacts and not move['loop']):
        raise ValueError('落脚索引需来自循环move且不重复')
    if type(options.get('reverseStartOnRelease',False)) is not bool:raise ValueError('起步反向取消需要布尔配置')
    stops=options.get('stopClipsByContact',{})
    if not isinstance(stops,dict):raise ValueError('停步映射需要JSON对象')
    clips={s['name']:s for s in manifest['states']}
    # 导出前验证映射，避免静态交付成功但消费页因缺停步图无法启动。
    for key,name in stops.items():
        if not isinstance(key,str) or not key.isascii() or not key.isdecimal() or str(int(key))!=key or int(key) not in contacts or not isinstance(name,str) or name not in clips or clips[name]['loop'] or name in {'idle','move','attack','hit','jump','move-start'}:
            raise ValueError('停步映射需要已配置落脚索引和存在的单次停步动作')
    if any(s['loop'] for s in manifest['states'] if s['name'] in {'move-start','move-stop'}):
        raise ValueError('起停过渡需要非循环')
    launch,land=options.get('launchMs',80),options.get('landMs',340)
    if any(type(n) not in (int,float) or not math.isfinite(n) for n in [launch,land]):raise ValueError('跳跃窗口需有限数')
    jump=next(s for s in manifest['states'] if s['name']=='jump')
    if not 0 <= launch < land <= sum(f['durationMs'] for f in jump['frames']):
        raise ValueError('跳跃原画总时长需要覆盖控制器起落窗口；请显式提供匹配配置')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.motion-site-',dir=out.parent) as tmp:
        stage=Path(tmp)/'result'
        bundle=stage/'material/bundle'
        bundle.mkdir(parents=True)
        # 原manifest/atlas直接复制，不改时长、锚点或来源；原始生成任务不冒充已打入此下载包。
        shutil.copy2(manifest_path,bundle/'manifest.json')
        target=within(bundle,manifest['atlas']);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(atlas_path,target)
        for name in ['aseprite.json','grid.json','preview.html']:
            path=manifest_path.parent/name
            if path.is_file() and not path.is_symlink():shutil.copy2(path,bundle/name)
        for state in manifest['states']:
            for i,frame in enumerate(state['frames']):
                relative=f"frames/{state['name']}/{i:04d}.png"
                target=within(bundle,relative);target.parent.mkdir(parents=True,exist_ok=True)
                # 图集是实际消费来源，按manifest矩形导出帧；源包没有散帧时首页也能显示真实原画。
                with Image.open(atlas_path) as atlas:
                    atlas.convert('RGBA').crop((frame['x'],frame['y'],frame['x']+frame['w'],frame['y']+frame['h'])).save(target)
        source_root=manifest_path.parent.parent if manifest_path.parent.name=='bundle' else manifest_path.parent
        # 集合的来源副本位于包根inputs；保留它们便于审查，但不声称具备全部上游任务的原始提示词。
        inputs=source_root/'inputs'
        if inputs.is_dir():
            if any(p.is_symlink() for p in [inputs,*inputs.rglob('*')]):raise ValueError('来源副本不包含符号链接')
            shutil.copytree(inputs,stage/'material/inputs')
        for name in ['provenance.json','processing.json','generation-review.json']:
            source=source_root/name
            if source.is_file() and not source.is_symlink():shutil.copy2(source,stage/'material'/name)
        source_manifest=bundle/'manifest.json'
        profile={'version':1,'title':manifest.get('title','二维角色动作'),'defaultCharacter':'hero','characters':[{'id':'hero','title':'当前素材','kind':'sprite','manifest':'material/bundle/manifest.json','defaultAction':'idle','requiredActions':['idle','move','attack','hit','jump'],'reviewNotes':['当前动作包验收预览，正式游戏接入需匹配自身位移和玩法窗口。']}]}
        # 工作台与可操作示例用同一消费配置，避免姿态检查页不跳、试玩页又叠加另一套高度。
        profile['characters'][0]['previewMotion']={'jump':{'kind':'jump-arc','startMs':launch,'endMs':land,'heightPixels':options.get('jumpHeight',40)}}
        write_json(stage/'profile.json',profile)
        build_workbench(stage/'profile.json',stage/'workbench')
        build_playable(source_manifest,stage/'playable',controller_options)
        playable_page=stage/'playable/index.html'
        original_link='href="../">返回动作工作台'
        page=playable_page.read_text()
        if page.count(original_link)!=1:raise ValueError('试玩返回链接模板已改变，请检查站点导航')
        playable_page.write_text(page.replace(original_link,'href="../workbench/">返回动作工作台'))
        export_godot(source_manifest,stage/'godot')
        summary={'status':'draft','sourceManifestSha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),'atlasSha256':hashlib.sha256(atlas_path.read_bytes()).hexdigest(),'actions':len(manifest['states']),'framePositions':sum(len(s['frames']) for s in manifest['states']),'anchor':data['anchor'],'imageGenerationCalls':0,'note':'Delivery of existing art. Includes asset files and available source-pack audit copies; complete GPT raw tasks remain in the generation workspace. Engine export is not full game integration.'}
        write_json(stage/'delivery.json',summary)
        (stage/'material/README.txt').write_text('二维角色素材候选\n入口：bundle/manifest.json，atlas.png与透明frames。原始durationMs/loop/anchor保留。\ninputs为现有来源包审查副本，若存在；完整GPT原始生成任务仍在生产工作区，不包含在此下载包。\n本包是草稿，正式游戏请确认物理位移、命中窗口与正常速度动画。\n')
        downloads=stage/'downloads';downloads.mkdir()
        zip_tree(stage/'material',downloads/'game-assets.zip')
        zip_tree(stage/'godot',downloads/'godot-preview.zip')
        # 下载Web示例时工作台也随包带走，返回链接指向包内路径，避免离开服务器后导航失效。
        web_copy=stage/'web-download'
        shutil.copytree(stage/'playable',web_copy)
        shutil.copytree(stage/'workbench',web_copy/'workbench')
        web_page=web_copy/'index.html'
        web_page.write_text(web_page.read_text().replace('href="../workbench/">返回动作工作台','href="workbench/">返回动作工作台'))
        zip_tree(web_copy,downloads/'web-playground.zip')
        shutil.rmtree(web_copy)
        rows=''.join(f'<tr><td>{html.escape(s["name"])}</td><td>{len(s["frames"])}</td><td>{sum(f["durationMs"] for f in s["frames"]):g} ms</td><td>{"循环" if s["loop"] else "单次"}</td></tr>' for s in manifest['states'])
        page=(Path(__file__).resolve().parents[1]/'examples/motion-preview-site.html').read_text()
        replacements={'@@TITLE@@':html.escape(manifest.get('title','二维角色动作')),'@@STATS@@':f'{summary["actions"]} 个动作 · {summary["framePositions"]} 个播放位置','@@ROWS@@':rows,'@@ANCHOR@@':html.escape(str(data['anchor'])),'@@HASH@@':summary['sourceManifestSha256'][:12]}
        for key,value in replacements.items():page=page.replace(key,value)
        (stage/'index.html').write_text(page)
        # 所有子产物完成后才发布；禁止把某个链接构建失败的半成品当验收入口。
        stage.rename(out)
    return out


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--controller-options',type=Path)
    args=parser.parse_args()
    try:print(build(args.manifest,args.out,args.controller_options))
    except (ValueError,KeyError,TypeError,OSError) as error:parser.error(str(error))
