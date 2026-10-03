"""把二维动作包接入可操作 Canvas 示例；不修改源包或升级素材状态。"""
import argparse
import json
from pathlib import Path
import shutil
import tempfile


def build(manifest_path, out, controller_options=None):
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('kind') != 'motion':
        raise ValueError('需要二维 motion manifest')
    atlas = (manifest_path.parent / manifest['atlas']).resolve()
    # 只复制该包内实际图集，禁止 manifest 越界引入其他项目文件。
    atlas.relative_to(manifest_path.parent)
    if out.exists():
        raise ValueError('输出已存在，使用新目录保留对照')
    out.parent.mkdir(parents=True, exist_ok=True)
    repo = Path(__file__).resolve().parents[1]
    options = json.loads(controller_options.read_text()) if controller_options else {}
    allowed = {'speed','jumpHeight','launchMs','landMs','breathAmplitude','breathPeriod','stopContactFrames','contactHoldMs','stopClipsByContact','reverseStartOnRelease'}
    if not isinstance(options, dict) or set(options)-allowed:
        raise ValueError('controller options需要已知控制器参数的JSON对象')
    with tempfile.TemporaryDirectory(dir=out.parent, prefix='.sprite-playground-') as temp:
        root = Path(temp) / 'result'
        (root / 'bundle').mkdir(parents=True)
        shutil.copy2(atlas, root / 'bundle/atlas.png')
        manifest['atlas'] = 'atlas.png'
        (root / 'bundle/manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
        # 相位索引是消费配置，独立保存，不写回原素材包或假装新增原画。
        (root / 'controller-options.json').write_text(json.dumps(options,ensure_ascii=False,indent=2)+'\n')
        shutil.copy2(repo / 'examples/sprite-playground.html', root / 'index.html')
        for name in ['sprite-controller.mjs', 'motion.mjs']:
            shutil.copy2(repo / 'examples' / 'export-workbench' / name, root / name)
        root.rename(out)
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--controller-options', type=Path)
    args = parser.parse_args()
    print(build(args.manifest, args.out.resolve(), args.controller_options))
