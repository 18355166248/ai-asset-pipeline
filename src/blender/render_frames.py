"""在 Blender 里把 3D 模型渲成透明背景的序列帧，供 2D 游戏当动作表用。

为什么要这条路：AI 逐张出图保不住跨帧一致性（实测主角 36 动作「画风跑成动漫」而废弃）。
同一个模型换姿态/换角度渲出来的帧，风格漂移在结构上不可能发生。

三种模式：
  turntable  绕 Z 轴转一圈，出 N 个方向的静态图。**不需要绑骨，现在就能跑。**
  animation  播放模型自带动画，按帧采样。等绑骨 + K 动作落地后用。
  still      只渲一帧，用于快速对机位。

关键约定：归一化只算一次，跨所有帧共用同一套缩放与位移。
逐帧各算各的会让角色在动作表里抖动、忽大忽小——这是序列帧渲染最容易踩的坑。

相机与灯光沿用 catch-the-goose 的 render_model_audit.py 基线（正交 + 三点光 + AgX），
保证新素材和既有模型的质检口径一致。灯光固定在世界坐标、只旋转模型，
所以角色转向时的受光方向是对的（太阳不跟着角色转）。

用法:
  blender --background --python src/blender/render_frames.py -- \
      --model apple.glb --out output/frames/apple --mode turntable --frames 8

  blender --background --python src/blender/render_frames.py -- \
      --model hero.glb --out output/frames/hero --mode animation --view side
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

# Blender 启动时的工作目录不是调用者的 cwd（实测是 C:\），
# 相对路径会渲到意想不到的地方，所以一律按仓库根解析。
ROOT = Path(__file__).resolve().parents[2]

# 相机预设：(仰角°, 方位角°, 正交尺寸)
# audit   = catch-the-goose 既有质检机位，3/4 俯视，便于和旧模型对比
# topdown = xianxia-roguelike 竖屏俯视战场
# side    = 横版闯关视角
#
# side 的方位角定在 62° 而不是 0 或 90，是实测比出来的（见 README「机位」）：
#   0°  正面——四肢朝镜头前后摆，透视压缩掉了，走路几乎看不出来
#   90° 纯侧面——摆幅最大，但身体只剩一条窄边，没有体积感
#   62° 3/4——身体有宽度、摆幅也读得全，横版动作游戏的标准机位
VIEWS = {
    "audit": (44.0, -8.0, 1.48),
    "topdown": (58.0, 0.0, 1.30),
    "side": (14.0, 62.0, 1.30),
}


def parse_args() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(description="3D 模型 -> 透明序列帧")
    ap.add_argument("--model", required=True, type=Path, help="输入 .glb/.gltf/.fbx")
    ap.add_argument("--out", required=True, type=Path, help="帧输出目录")
    ap.add_argument("--mode", choices=("turntable", "animation", "still"),
                    default="turntable")
    ap.add_argument("--frames", type=int, default=8,
                    help="turntable 的方向数；animation 模式下为采样帧数")
    ap.add_argument("--view", choices=tuple(VIEWS), default="topdown")
    ap.add_argument("--elevation", type=float, default=None, help="覆盖预设仰角")
    ap.add_argument("--azimuth", type=float, default=None, help="起始方位角偏移")
    ap.add_argument("--ortho", type=float, default=None, help="覆盖正交尺寸")
    ap.add_argument("--size", type=int, default=256, help="单帧宽度（像素）")
    ap.add_argument("--frame-height", type=int, default=None,
                    help="单帧高度；不给则为正方形。"
                         "长身体的四足用宽画面（如 256x160）能显著提高有效分辨率")
    ap.add_argument("--margin", type=float, default=0.88,
                    help="模型占画面比例，留白防动作幅度出框")
    ap.add_argument("--loop", action="store_true",
                    help="循环动作：末帧与首帧同姿态，采样时跳过末帧避免重复")
    ap.add_argument("--measure-only", action="store_true",
                    help="只量包围盒并写 manifest，不渲染。用于先跨动作求并集")
    ap.add_argument("--fit-bounds", default=None,
                    help="用给定包围盒归一化，格式 lx,ly,lz,hx,hy,hz。"
                         "同一角色的多个动作传同一组值，尺寸才不会在切动作时跳变")
    return ap.parse_args(raw)


def clear_scene() -> None:
    # 不清空的话 Blender 默认立方体会直挡在模型前面。
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def setup_render(size: int, height: int | None = None) -> None:
    scene = bpy.context.scene
    engines = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys()
    scene.render.engine = ("BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines
                           else "BLENDER_EEVEE")
    scene.render.resolution_x = size
    scene.render.resolution_y = height or size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    # 透明背景是这条管线相对 AI 出图的核心优势：直接带 alpha，
    # 不需要 chroma-key / rembg 抠图，也就没有抠坏某一格的可能。
    scene.render.film_transparent = True
    scene.view_settings.look = "AgX - Medium High Contrast"

    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs[0].default_value = (0.055, 0.042, 0.038, 1)
    background.inputs[1].default_value = 0.32


def setup_camera(elevation: float, ortho: float) -> None:
    scene = bpy.context.scene
    data = bpy.data.cameras.new("SheetCamera")
    data.type = "ORTHO"
    data.ortho_scale = ortho
    data.clip_start = 0.1
    data.clip_end = 100.0
    camera = bpy.data.objects.new("SheetCamera", data)
    scene.collection.objects.link(camera)

    # 球坐标定位。正交相机下距离只影响裁剪面，取够远即可。
    distance = 10.0
    elev = math.radians(elevation)
    camera.location = (0.0, -distance * math.cos(elev), distance * math.sin(elev))
    camera.rotation_euler = (
        Vector((0, 0, 0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera


def setup_lights() -> None:
    # 世界坐标固定的三点光。turntable 只转模型不转灯，
    # 所以角色转身时的背光/侧光关系是对的。
    lights = [
        ("Key", (2.8, -3.2, 5.0), 720.0, 3.0, (1.0, 0.72, 0.52)),
        ("Fill", (-3.5, -1.0, 3.2), 430.0, 4.0, (0.48, 0.67, 1.0)),
        ("Rim", (1.0, 3.6, 4.2), 620.0, 2.6, (1.0, 0.48, 0.30)),
    ]
    for name, location, energy, size, color in lights:
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        light = bpy.data.objects.new(name, data)
        light.location = location
        light.rotation_euler = (
            Vector((0, 0, 0)) - light.location).to_track_quat("-Z", "Y").to_euler()
        bpy.context.scene.collection.objects.link(light)


def import_model(path: Path) -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    before = set(bpy.context.scene.objects)
    suffix = path.suffix.lower()
    if suffix in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif suffix == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(path))
    else:
        raise SystemExit(f"不支持的输入格式: {suffix}")

    imported = [obj for obj in bpy.context.scene.objects if obj not in before]
    meshes = [obj for obj in imported if obj.type == "MESH"]
    if not meshes:
        raise SystemExit(f"{path.name} 里没有网格")

    # 导入结果常自带一层变换根节点。统一挂到一个 pivot 下、只变换 pivot；
    # 逐个变换已经父子相连的对象，会把同一套偏移叠加两次。
    roots = [obj for obj in imported if obj.parent not in imported]
    pivot = bpy.data.objects.new("SheetPivot", None)
    bpy.context.scene.collection.objects.link(pivot)
    for root in roots:
        root.parent = pivot
        root.matrix_parent_inverse = pivot.matrix_world.inverted()
    bpy.context.view_layer.update()
    return pivot, meshes, imported


def animation_range(imported: list[bpy.types.Object]) -> tuple[int, int] | None:
    """从导入对象自带的动作里取真实帧范围，没有动画返回 None。

    不能用 scene.frame_start/frame_end 判断：Blender 默认就是 1-250，
    跟模型有没有动画无关。信它的话，静态模型会渲出 N 张姿态相同的图，
    打包成动作表后「播起来不动」，而且每张哈希还不一样（EEVEE 采样抖动），
    很难一眼看出问题。
    """
    low: float | None = None
    high: float | None = None
    for obj in imported:
        sources = [obj.animation_data]
        data = getattr(obj, "data", None)
        if data is not None:
            sources.append(getattr(data, "animation_data", None))
            shape_keys = getattr(data, "shape_keys", None)
            if shape_keys is not None:
                sources.append(shape_keys.animation_data)
        for source in sources:
            action = getattr(source, "action", None)
            if action is None:
                continue
            start, end = action.frame_range
            low = start if low is None else min(low, start)
            high = end if high is None else max(high, end)
    if low is None or high is None or high <= low:
        return None
    return int(round(low)), int(round(high))


def evaluated_bounds(meshes: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    """当前帧下的世界包围盒。用 evaluated 版本才能拿到形变/修饰器之后的真实范围。"""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    low = Vector((1e9, 1e9, 1e9))
    high = Vector((-1e9, -1e9, -1e9))
    found = False
    for obj in meshes:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        if mesh is None:
            continue
        matrix = evaluated.matrix_world
        for vertex in mesh.vertices:
            point = matrix @ vertex.co
            low = Vector(min(low[i], point[i]) for i in range(3))
            high = Vector(max(high[i], point[i]) for i in range(3))
            found = True
        evaluated.to_mesh_clear()
    if not found:
        raise SystemExit("无法计算包围盒")
    return low, high


def frame_poses(mode: str, frames: int, start_azimuth: float,
                clip: tuple[int, int] | None, loop: bool) -> list[tuple[int, float]]:
    """每帧的 (场景帧号, 模型 Z 旋转角度)。"""
    scene = bpy.context.scene
    if mode == "still":
        return [(scene.frame_start, start_azimuth)]
    if mode == "turntable":
        step = 360.0 / frames
        return [(scene.frame_start, start_azimuth + i * step) for i in range(frames)]

    if clip is None:
        raise SystemExit(
            "这个模型没有动画数据。先绑骨 + K 动作，或改用 --mode turntable 出方向图。")
    first, last = clip
    span = last - first
    if loop:
        # 循环动作的末帧与首帧是同一姿态，采到 [first, last) 就够；
        # 包含末帧会在动作表里多出一张重复帧，播放时看着卡一下。
        return [(first + round(span * i / frames), start_azimuth) for i in range(frames)]
    # 一次性动作（挥砍、受击）必须采到末帧，
    # 否则收招或站稳的最后一下被截掉，动作看着没收干净。
    divisor = max(1, frames - 1)
    return [(first + round(span * i / divisor), start_azimuth) for i in range(frames)]


def normalize(pivot: bpy.types.Object, meshes: list[bpy.types.Object],
              poses: list[tuple[int, float]], margin: float,
              fit: tuple[Vector, Vector] | None = None) -> dict:
    """跨所有帧算一次统一的缩放与居中。

    逐帧各自归一化会让角色在动作表里抖动、忽大忽小，这是序列帧最容易踩的坑。
    做法是先遍历全部帧取包围盒并集，据此定死一套变换；
    之后渲染时只改帧号和旋转，不再碰缩放与位移。
    """
    scene = bpy.context.scene
    if fit is not None:
        # 外部指定包围盒：跨动作共用同一套缩放，
        # 否则每个动作各自贴边归一化，角色会在切动作时忽大忽小。
        union_low, union_high = fit
    else:
        union_low, union_high = measure_union(pivot, meshes, poses)

    center = (union_low + union_high) * 0.5

    # 按**相机看到的样子**来定缩放，而不是按世界空间最长边。
    #
    # 之前用 scale = margin / 最长边，等于把最长边映射成 margin 个世界单位，
    # 而相机 ortho_scale 覆盖 1.30 个单位——模型只占画面 66%，白白浪费三分之一。
    # 长身体的四足更吃亏：躯干横躺，正方形画面上下大片空白。
    #
    # 这里把包围盒八个角投影到相机空间量真实的横纵占幅，
    # 再取横纵两个方向里更紧的那个约束，模型就能真正贴合画面。
    camera = scene.camera
    to_camera = camera.matrix_world.inverted()
    corners = [Vector((x, y, z))
               for x in (union_low.x, union_high.x)
               for y in (union_low.y, union_high.y)
               for z in (union_low.z, union_high.z)]
    projected = [to_camera @ (corner - center) for corner in corners]
    span_x = (max(p.x for p in projected) - min(p.x for p in projected)) or 1e-6
    span_y = (max(p.y for p in projected) - min(p.y for p in projected)) or 1e-6
    mid_x = (max(p.x for p in projected) + min(p.x for p in projected)) * 0.5
    mid_y = (max(p.y for p in projected) + min(p.y for p in projected)) * 0.5

    # Blender 的 ortho_scale 覆盖分辨率较长的那一边（sensor_fit=AUTO）。
    ortho = camera.data.ortho_scale
    width, height = scene.render.resolution_x, scene.render.resolution_y
    if width >= height:
        frame_w, frame_h = ortho, ortho * height / width
    else:
        frame_w, frame_h = ortho * width / height, ortho
    scale = margin * min(frame_w / span_x, frame_h / span_y)

    # 缩放后包围盒中心在相机空间的偏移也随之放大，
    # 沿相机的右向量和上向量把它推回画面正中。
    right = camera.matrix_world.to_3x3() @ Vector((1, 0, 0))
    up = camera.matrix_world.to_3x3() @ Vector((0, 1, 0))
    pivot.scale = (scale, scale, scale)
    pivot.location = -center * scale - right * (mid_x * scale) - up * (mid_y * scale)
    bpy.context.view_layer.update()
    return {
        "unionLow": [round(v, 4) for v in union_low],
        "unionHigh": [round(v, 4) for v in union_high],
        "scale": round(scale, 6),
        "screenSpan": [round(span_x, 4), round(span_y, 4)],
        "frame": [round(frame_w, 4), round(frame_h, 4)],
        "sharedFit": fit is not None,
    }


def measure_union(pivot: bpy.types.Object, meshes: list[bpy.types.Object],
                  poses: list[tuple[int, float]]) -> tuple[Vector, Vector]:
    """遍历全部帧取包围盒并集。"""
    scene = bpy.context.scene
    union_low = Vector((1e9, 1e9, 1e9))
    union_high = Vector((-1e9, -1e9, -1e9))
    for frame, rotation in poses:
        scene.frame_set(frame)
        pivot.rotation_euler.z = math.radians(rotation)
        bpy.context.view_layer.update()
        low, high = evaluated_bounds(meshes)
        union_low = Vector(min(union_low[i], low[i]) for i in range(3))
        union_high = Vector(max(union_high[i], high[i]) for i in range(3))
    # 并集是在 pivot 未缩放、未平移的状态下量的，
    # 所以缩放后直接用 -center * scale 就能把并集中心对到原点。
    return union_low, union_high


def main() -> None:
    options = parse_args()
    if not options.model.is_absolute():
        options.model = ROOT / options.model
    if not options.out.is_absolute():
        options.out = ROOT / options.out
    if not options.model.exists():
        raise SystemExit(f"找不到模型: {options.model}")

    elevation, azimuth, ortho = VIEWS[options.view]
    if options.elevation is not None:
        elevation = options.elevation
    if options.azimuth is not None:
        azimuth = options.azimuth
    if options.ortho is not None:
        ortho = options.ortho

    clear_scene()
    setup_render(options.size, options.frame_height)
    setup_camera(elevation, ortho)
    setup_lights()
    pivot, meshes, imported = import_model(options.model)

    clip = animation_range(imported)
    poses = frame_poses(options.mode, options.frames, azimuth, clip, options.loop)

    if options.measure_only:
        # 只量不渲：给上层驱动脚本先跨动作求并集用。
        low, high = measure_union(pivot, meshes, poses)
        options.out.mkdir(parents=True, exist_ok=True)
        (options.out / "measure.json").write_text(json.dumps({
            "model": options.model.name,
            "unionLow": [round(v, 6) for v in low],
            "unionHigh": [round(v, 6) for v in high],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[render_frames] 测量 {options.model.name} "
              f"low={tuple(round(v, 3) for v in low)} "
              f"high={tuple(round(v, 3) for v in high)}")
        return

    fit = None
    if options.fit_bounds:
        values = [float(v) for v in options.fit_bounds.split(",")]
        if len(values) != 6:
            raise SystemExit("--fit-bounds 需要 6 个数：lx,ly,lz,hx,hy,hz")
        fit = (Vector(values[:3]), Vector(values[3:]))
    stats = normalize(pivot, meshes, poses, options.margin, fit)

    options.out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    written = []
    for index, (frame, rotation) in enumerate(poses):
        scene.frame_set(frame)
        pivot.rotation_euler.z = math.radians(rotation)
        bpy.context.view_layer.update()
        target = options.out / f"{options.model.stem}_{index:02d}.png"
        scene.render.filepath = str(target)
        bpy.ops.render.render(write_still=True)
        written.append(target.name)

    triangles = sum(len(poly.vertices) - 2
                    for obj in meshes for poly in obj.data.polygons)
    manifest = {
        "model": options.model.name,
        "mode": options.mode,
        "view": options.view,
        "elevation": elevation,
        "orthoScale": ortho,
        "frameSize": [options.size, options.frame_height or options.size],
        "frameCount": len(written),
        "animationRange": list(clip) if clip else None,
        "loop": options.loop,
        "frames": written,
        "triangles": triangles,
        "meshes": len(meshes),
        **stats,
    }
    (options.out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[render_frames] {len(written)} 帧 -> {options.out}  "
          f"三角面={triangles} 网格={len(meshes)} 缩放={stats['scale']}")


if __name__ == "__main__":
    main()
