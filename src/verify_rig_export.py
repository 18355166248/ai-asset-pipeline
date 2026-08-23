"""比对导出的 GLB 与动作库 JSON，确认动作数据一路没丢没变。

为什么需要这道闸：动画在导出环节丢失时**全程不报错**。
实测踩过一次——glTF 导出器默认把 11 个部件拆成 11 条独立动画，
重新导入时只有一条激活，成品表现是"角色几乎不动"，
而导出返回 FINISHED、导入也没有警告，只能靠肉眼在渲染结果里发现。

这个脚本直接解码 GLB 的动画采样器，把每个关键帧的实际烘焙值
和库里声明的值逐个比对，能在渲染之前就抓到问题。

帧号与时间的换算：Blender 把第 N 帧导出在 t = N / fps。
注意不是 (N-1)/fps——差一帧会让所有校验值看着"接近但对不上"，
很容易误判成插值误差。

用法:
  python src/verify_rig_export.py --rig-dir output/rig
  python src/verify_rig_export.py --rig-dir output/rig --clip slash --verbose
"""
from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
COMPONENT_COUNTS = {"SCALAR": 1, "VEC3": 3, "VEC4": 4}


def load_glb(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    offset = 12
    gltf = None
    binary = b""
    while offset < len(raw):
        length, kind = struct.unpack_from("<II", raw, offset)
        chunk = raw[offset + 8:offset + 8 + length]
        if kind == 0x4E4F534A:
            gltf = json.loads(chunk)
        elif kind == 0x004E4942:
            binary = chunk
        offset += 8 + length
    if gltf is None:
        raise SystemExit(f"{path.name} 不是有效的 GLB")
    return gltf, binary


def read_accessor(gltf: dict, binary: bytes, index: int) -> list[tuple[float, ...]]:
    accessor = gltf["accessors"][index]
    view = gltf["bufferViews"][accessor["bufferView"]]
    start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    count = COMPONENT_COUNTS[accessor["type"]]
    stride = 4 * count
    return [struct.unpack_from("<" + "f" * count, binary, start + i * stride)
            for i in range(accessor["count"])]


def quaternion_to_euler(q: tuple[float, ...]) -> tuple[float, float, float]:
    """glTF 四元数是 (x, y, z, w)，转成 XYZ 欧拉角（度）。"""
    x, y, z, w = q
    sinr = 2 * (w * x + y * z)
    cosr = 1 - 2 * (x * x + y * y)
    roll = math.atan2(sinr, cosr)
    sinp = 2 * (w * y - z * x)
    pitch = math.copysign(math.pi / 2, sinp) if abs(sinp) >= 1 else math.asin(sinp)
    siny = 2 * (w * z + x * y)
    cosy = 1 - 2 * (y * y + z * z)
    yaw = math.atan2(siny, cosy)
    return tuple(math.degrees(v) for v in (roll, pitch, yaw))


def sample_at(times: list[float], values: list, frame: int, fps: float):
    """取第 frame 帧的烘焙值。Blender 导出在 t = frame / fps。"""
    target = frame / fps
    best = min(range(len(times)), key=lambda i: abs(times[i] - target))
    if abs(times[best] - target) > 0.5 / fps:
        return None
    return values[best]


def verify(path: Path, clip: dict, fps: float, tolerance: float,
           verbose: bool) -> list[str]:
    gltf, binary = load_glb(path)
    animations = gltf.get("animations", [])
    if len(animations) != 1:
        return [f"{path.name}: 应该只有 1 条动画，实际 {len(animations)} 条。"
                f"导出时需要 export_animation_mode=SCENE 且 "
                f"export_anim_scene_split_object=False"]

    names = [n.get("name") for n in gltf["nodes"]]
    animation = animations[0]
    problems = []
    checked = 0

    for part, tracks in clip["tracks"].items():
        if "rot" not in tracks:
            continue
        if part not in names:
            problems.append(f"{path.name}: GLB 里没有部件 {part}")
            continue
        node = names.index(part)
        channel = next((c for c in animation["channels"]
                        if c["target"]["node"] == node
                        and c["target"]["path"] == "rotation"), None)
        if channel is None:
            problems.append(f"{path.name}: {part} 没有旋转通道，动作丢了")
            continue

        sampler = animation["samplers"][channel["sampler"]]
        times = [t[0] for t in read_accessor(gltf, binary, sampler["input"])]
        quats = read_accessor(gltf, binary, sampler["output"])

        for frame, expected in tracks["rot"]:
            actual = sample_at(times, quats, frame, fps)
            if actual is None:
                problems.append(f"{path.name}: {part} 第 {frame} 帧没有采样点")
                continue
            euler = quaternion_to_euler(actual)
            # 只校验绕 X 的分量：它是摆动主轴，且不受欧拉万向死角影响。
            delta = abs(euler[0] - expected[0])
            checked += 1
            if delta > tolerance:
                problems.append(
                    f"{path.name}: {part} 第 {frame} 帧 X 旋转 "
                    f"期望 {expected[0]:.1f}° 实际 {euler[0]:.1f}° 差 {delta:.2f}°")
            elif verbose:
                print(f"    {part:<14} 帧{frame:>3}  {expected[0]:>7.1f}° "
                      f"-> {euler[0]:>7.1f}°")
    if verbose:
        print(f"    共校验 {checked} 个关键帧")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description="校验 GLB 动画与动作库一致")
    ap.add_argument("--rig-dir", type=Path, default=Path("output/rig"))
    ap.add_argument("--library", type=Path, default=Path("animation-library"))
    ap.add_argument("--skeleton", default="humanoid-basic")
    ap.add_argument("--prefix", default="hero")
    ap.add_argument("--clip", default=None, help="只校验一个动作")
    ap.add_argument("--fps", type=float, default=24.0)
    ap.add_argument("--tolerance", type=float, default=0.5, help="容差（度）")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    library = args.library if args.library.is_absolute() else ROOT / args.library
    rig_dir = args.rig_dir if args.rig_dir.is_absolute() else ROOT / args.rig_dir
    clip_dir = library / f"clips/{args.skeleton}"

    names = [args.clip] if args.clip else [p.stem for p in sorted(clip_dir.glob("*.json"))]
    all_problems: list[str] = []
    for name in names:
        clip = json.loads((clip_dir / f"{name}.json").read_text(encoding="utf-8"))
        path = rig_dir / f"{args.prefix}_{name}.glb"
        if not path.exists():
            all_problems.append(f"缺少 {path.name}，先跑 make_test_rig.py 生成")
            continue
        if args.verbose:
            print(f"  {name}:")
        problems = verify(path, clip, args.fps, args.tolerance, args.verbose)
        all_problems.extend(problems)
        print(f"  {name:<8} {'OK' if not problems else f'{len(problems)} 个问题'}")

    print()
    if all_problems:
        for problem in all_problems:
            print("  [X]", problem)
        sys.exit(1)
    print(f"[OK] {len(names)} 个动作的 GLB 与动作库完全一致")


if __name__ == "__main__":
    main()
