"""把一个角色的整套动作渲成序列帧，**共用同一套归一化**。

为什么需要这个驱动：单独渲每个动作时，各自贴边归一化，
跳跃因为幅度大会被缩得比待机小——同一个角色在游戏里切动作时会忽大忽小。
实测 idle/move/slash/hit 各自归一化的 scale 是 0.410/0.413/0.401/0.408，
差 2.8%，切动作时看得出来跳一下。

做法是两趟：
  1 每个动作只量包围盒不渲染（--measure-only），快
  2 取所有动作的并集，用同一组 --fit-bounds 渲全部

跳跃这类幅度大的动作会把并集撑大，于是所有动作都相应缩小一点——
这是对的：整套动作共用一个尺寸基准，代价是待机时角色不贴边。

用法:
  python src/render_clip_set.py --rig-dir output/rig --out output/frames \
      --clips idle:12:loop move:16:loop slash:12 slash2:14 cast:16 jump:14 dash:14
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BLENDER = r"C:/Program Files/Blender Foundation/Blender 4.5/blender.exe"
RENDER_SCRIPT = ROOT / "src/blender/render_frames.py"


def parse_clip(spec: str) -> tuple[str, int, bool]:
    """解析 名字:帧数[:loop]。"""
    parts = spec.split(":")
    if len(parts) < 2:
        raise SystemExit(f"动作格式应为 名字:帧数[:loop]，收到 {spec}")
    loop = len(parts) > 2 and parts[2] == "loop"
    return parts[0], int(parts[1]), loop


def run_blender(blender: str, args: list[str]) -> str:
    result = subprocess.run(
        [blender, "--background", "--python", str(RENDER_SCRIPT), "--", *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        sys.stderr.write(result.stdout[-3000:] + result.stderr[-3000:])
        raise SystemExit(f"Blender 失败: {' '.join(args[:4])}")
    return result.stdout


def main() -> None:
    ap = argparse.ArgumentParser(description="整套动作共用归一化渲染")
    ap.add_argument("--rig-dir", type=Path, default=Path("output/rig"))
    ap.add_argument("--out", type=Path, default=Path("output/frames"))
    ap.add_argument("--prefix", default="hero")
    ap.add_argument("--clips", nargs="+", required=True)
    ap.add_argument("--view", default="side")
    ap.add_argument("--size", type=int, default=256)
    ap.add_argument("--margin", type=float, default=0.92)
    ap.add_argument("--frame-height", type=int, default=None,
                    help="非正方形画面高度。长身体的四足用宽画面更省像素")
    ap.add_argument("--blender", default=DEFAULT_BLENDER)
    args = ap.parse_args()

    clips = [parse_clip(c) for c in args.clips]
    rig_dir = args.rig_dir if args.rig_dir.is_absolute() else ROOT / args.rig_dir
    out_dir = args.out if args.out.is_absolute() else ROOT / args.out

    # 第一趟：只量不渲
    low = [1e9, 1e9, 1e9]
    high = [-1e9, -1e9, -1e9]
    for name, frames, loop in clips:
        model = rig_dir / f"{args.prefix}_{name}.glb"
        if not model.exists():
            raise SystemExit(f"找不到 {model}")
        target = out_dir / f"{args.prefix}_{name}"
        cmd = ["--model", str(model), "--out", str(target), "--mode", "animation",
               "--frames", str(frames), "--view", args.view, "--measure-only"]
        if loop:
            cmd.append("--loop")
        run_blender(args.blender, cmd)
        data = json.loads((target / "measure.json").read_text(encoding="utf-8"))
        low = [min(low[i], data["unionLow"][i]) for i in range(3)]
        high = [max(high[i], data["unionHigh"][i]) for i in range(3)]
        span = [round(data["unionHigh"][i] - data["unionLow"][i], 3) for i in range(3)]
        print(f"  量 {name:<8} 幅度={span}")

    fit = ",".join(f"{v:.6f}" for v in low + high)
    print(f"\n共用包围盒 low={[round(v, 3) for v in low]} high={[round(v, 3) for v in high]}")

    # 第二趟：用同一组包围盒渲全部
    for name, frames, loop in clips:
        model = rig_dir / f"{args.prefix}_{name}.glb"
        target = out_dir / f"{args.prefix}_{name}"
        # 必须写成 --fit-bounds=值：包围盒下界常是负数，
        # 分开传时 argparse 会把 "-0.65,..." 当成另一个选项名。
        cmd = ["--model", str(model), "--out", str(target), "--mode", "animation",
               "--frames", str(frames), "--view", args.view, "--size", str(args.size),
               "--margin", str(args.margin), f"--fit-bounds={fit}"]
        if args.frame_height:
            cmd += ["--frame-height", str(args.frame_height)]
        if loop:
            cmd.append("--loop")
        output = run_blender(args.blender, cmd)
        for line in output.splitlines():
            if line.startswith("[render_frames]"):
                print(" ", line)


if __name__ == "__main__":
    main()
