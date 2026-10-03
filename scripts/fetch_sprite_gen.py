"""下载锁定的上游源码子集，跳过演示媒体；Git blob校验通过后原子发布。"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]

def fetch(out):
    lock = json.loads((ROOT / 'config/sprite-gen.lock.json').read_text())
    out = out.resolve()
    if out.exists(): raise ValueError('目标已存在，不覆盖上游源码')
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.sprite-gen-', dir=out.parent) as temporary:
        stage = Path(temporary) / 'source'; stage.mkdir()
        def download(item):
            path, expected = item
            if Path(path).is_absolute() or '..' in Path(path).parts: raise ValueError('锁文件路径越界')
            url = f"https://raw.githubusercontent.com/aldegad/sprite-gen/{lock['commit']}/{path}"
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(url, timeout=25) as response: data=response.read()
                    digest=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
                    if digest != expected: raise ValueError('Git blob不匹配：'+path)
                    target=stage/path; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
                    return
                except OSError:
                    if attempt==2: raise
        with ThreadPoolExecutor(max_workers=8) as pool: list(pool.map(download,lock['files'].items()))
        (stage/'UPSTREAM_LOCK.json').write_text(json.dumps(lock,indent=2)+'\n')
        stage.rename(out)
    return out

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=ROOT/'vendor/sprite-gen');args=parser.parse_args()
    print(fetch(args.out))
