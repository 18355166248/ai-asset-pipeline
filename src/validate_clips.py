"""校验动作库：动作能不能用、循环接不接得上、有没有引用不存在的部件。

放在渲染之前跑。一次完整渲染要几分钟，而这些错误里有好几种**渲出来也不报错**，
只能靠肉眼在成品里发现——比如循环动作首尾姿态对不上，播起来每圈顿一下。

检查项：
  1 动作引用的部件必须在骨架里存在
  2 通道名必须是 rot / loc / scale
  3 关键帧号必须递增且不重复，且落在 1..end 内
  4 循环动作的首尾帧必须同姿态（这条最容易漏，而且渲染不会报错）
  5 每条轨道至少两个关键帧（只有一个等于没动画）
  6 骨架的父子引用必须存在且无环

用法:
  python src/validate_clips.py
  python src/validate_clips.py --library animation-library --skeleton humanoid-basic
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Windows 控制台默认 GBK，遇到范围外字符会抛 UnicodeEncodeError。
# 校验脚本不该因为一个符号打不出来就整体失败。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
CHANNELS = ("rot", "loc", "scale")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_skeleton(skeleton: dict) -> list[str]:
    problems = []
    ids = [p["id"] for p in skeleton["parts"]]
    seen = set()
    for part_id in ids:
        if part_id in seen:
            problems.append(f"骨架部件 id 重复: {part_id}")
        seen.add(part_id)

    parents = {p["id"]: p.get("parent") for p in skeleton["parts"]}
    for part_id, parent in parents.items():
        if parent is not None and parent not in parents:
            problems.append(f"部件 {part_id} 的父级 {parent} 不存在")

    # 环检测：顺着 parent 往上走，走不到 None 就是有环。
    for part_id in parents:
        seen_chain = set()
        cursor = part_id
        while cursor is not None:
            if cursor in seen_chain:
                problems.append(f"部件 {part_id} 的父子链成环")
                break
            seen_chain.add(cursor)
            cursor = parents.get(cursor)
    return problems


def check_clip(clip: dict, part_ids: set[str]) -> list[str]:
    problems = []
    name = clip.get("id", "?")
    end = clip.get("end")
    if not isinstance(end, int) or end < 2:
        problems.append(f"[{name}] end 必须是 >=2 的整数")
        return problems

    if not clip.get("tracks"):
        problems.append(f"[{name}] 没有任何轨道")
        return problems

    for part, tracks in clip["tracks"].items():
        if part not in part_ids:
            problems.append(f"[{name}] 引用了骨架里没有的部件: {part}")
            continue
        for channel, keys in tracks.items():
            label = f"[{name}] {part}.{channel}"
            if channel not in CHANNELS:
                problems.append(f"{label} 未知通道，只能是 {CHANNELS}")
                continue
            if len(keys) < 2:
                problems.append(f"{label} 只有 {len(keys)} 个关键帧，等于没动画")
                continue

            frames = [k[0] for k in keys]
            if frames != sorted(frames):
                problems.append(f"{label} 关键帧号不是递增的: {frames}")
            if len(set(frames)) != len(frames):
                problems.append(f"{label} 有重复帧号: {frames}")
            if frames[0] < 1 or frames[-1] > end:
                problems.append(f"{label} 帧号超出 1..{end}: {frames[0]}..{frames[-1]}")

            for frame, value in keys:
                if len(value) != 3:
                    problems.append(f"{label} 帧 {frame} 的值不是三元组: {value}")

            # 循环动作首尾必须同姿态。渲染不会报这个错，
            # 但播放时每圈都会在接缝处顿一下或跳一下。
            if clip.get("loop"):
                if frames[0] != 1 or frames[-1] != end:
                    problems.append(
                        f"{label} 循环动作的轨道必须覆盖首帧 1 和末帧 {end}，"
                        f"当前是 {frames[0]}..{frames[-1]}")
                elif keys[0][1] != keys[-1][1]:
                    problems.append(
                        f"{label} 循环动作首尾姿态不一致: "
                        f"{keys[0][1]} vs {keys[-1][1]}")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description="校验动作库")
    ap.add_argument("--library", type=Path, default=Path("animation-library"))
    ap.add_argument("--skeleton", default=None, help="只校验某个骨架")
    args = ap.parse_args()

    library = args.library if args.library.is_absolute() else ROOT / args.library
    index = load(library / "library.json")
    skeleton_ids = [args.skeleton] if args.skeleton else index["skeletons"]

    all_problems: list[str] = []
    total_clips = 0
    for skeleton_id in skeleton_ids:
        skeleton = load(library / f"skeletons/{skeleton_id}.json")
        problems = check_skeleton(skeleton)
        part_ids = {p["id"] for p in skeleton["parts"]}
        print(f"骨架 {skeleton_id}: {len(part_ids)} 个部件")

        clip_dir = library / f"clips/{skeleton_id}"
        for path in sorted(clip_dir.glob("*.json")):
            clip = load(path)
            if clip.get("skeleton") != skeleton_id:
                problems.append(
                    f"[{clip.get('id')}] 声明的骨架 {clip.get('skeleton')} "
                    f"与所在目录 {skeleton_id} 不符")
            found = check_clip(clip, part_ids)
            problems.extend(found)
            total_clips += 1
            status = "OK" if not found else f"{len(found)} 个问题"
            kind = "循环" if clip.get("loop") else "一次性"
            print(f"  {clip.get('id'):<8} {kind:<4} 末帧={clip.get('end'):<4} "
                  f"轨道={len(clip.get('tracks', {})):<3} {status}")
        all_problems.extend(problems)

    print()
    if all_problems:
        for problem in all_problems:
            print("  [X]", problem)
        print(f"\n{total_clips} 个动作，{len(all_problems)} 个问题")
        sys.exit(1)
    print(f"[OK] {total_clips} 个动作全部通过")


if __name__ == "__main__":
    main()
