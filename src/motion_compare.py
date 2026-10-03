"""导出可离线复用的二维动作同步比较页；使用原帧和实际时长。"""
import argparse
import hashlib
import html
import json
from pathlib import Path
import shutil
import tempfile

from asset_bundle import read_json, within, write_json
from character_workbench import load_sprite


def build(config_path, out):
    config_path, out = config_path.resolve(), out.resolve()
    config = read_json(config_path)
    if config.get('version') != 1 or not isinstance(config.get('inputs'), list) or len(config['inputs']) != 2:
        raise ValueError('需要version=1和两个inputs')
    sources = []
    for item in config['inputs']:
        path = (config_path.parent / item['manifest']).resolve()
        data, _ = load_sprite({'manifest': str(path)}, path.parent)
        manifest = read_json(path)
        state = next((s for s in manifest['states'] if s['name'] == config.get('action')), None)
        if state is None or not state['loop']:
            raise ValueError('需要双方存在的循环动作')
        if out.exists() or out == path.parent or path.parent in out.parents:
            raise ValueError('输出已存在或位于源包内')
        sources.append((path, within(path.parent, manifest['atlas']), data, state, item.get('label', path.parent.name)))
    first, second = sources
    duration = sum(f['durationMs'] for f in first[3]['frames'])
    # 循环长度不同会在共享时钟下逐轮错相；拒绝这种输入，不偷偷重采样或改时长。
    if duration != sum(f['durationMs'] for f in second[3]['frames']):
        raise ValueError('循环总时长必须一致')
    if first[2]['anchor'] != second[2]['anchor'] or (first[3]['frames'][0]['w'], first[3]['frames'][0]['h']) != (second[3]['frames'][0]['w'], second[3]['frames'][0]['h']):
        raise ValueError('画布与anchor必须一致')
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.motion-compare-', dir=out.parent) as temporary:
        stage = Path(temporary) / 'result'; stage.mkdir()
        payload = {'status': 'diagnostic-only', 'durationMs': duration, 'anchor': first[2]['anchor'], 'sources': []}
        for i, (path, atlas, data, state, label) in enumerate(sources):
            shutil.copy2(atlas, stage / f'atlas-{i}.png')
            payload['sources'].append({'label': label, 'atlas': f'atlas-{i}.png', 'frames': state['frames'],
                                       'manifestSha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                       'atlasSha256': hashlib.sha256(atlas.read_bytes()).hexdigest()})
        write_json(stage / 'comparison.json', payload)
        page = (Path(__file__).resolve().parents[1] / 'examples/motion-compare.html').read_text()
        replacements = {'@@TITLE@@': config.get('title', '二维动作同步比较'), '@@NOTE@@': config.get('note', '两侧使用原始帧时长，循环同步。'),
                        '@@LEFT@@': first[4], '@@RIGHT@@': second[4]}
        for key, value in replacements.items():
            if not isinstance(value, str): raise ValueError('标题、说明和label需要文本')
            page = page.replace(key, html.escape(value))
        page = page.replace('@@DATA@@', json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c'))
        (stage / 'index.html').write_text(page)
        stage.rename(out)
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try: print(build(args.config, args.out))
    except (ValueError, KeyError, OSError) as error: parser.exit(2, str(error) + '\n')
