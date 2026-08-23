"""按动作库里的骨架与动作定义，在 Blender 里搭出带关节枢轴的角色并 K 上动作。

骨架和动作全部来自 `animation-library/`，本文件只负责"照着数据搭"。
这样调动作参数不用改代码，同一套动作也能给不同角色复用——
只要它们声明的是同一个 skeleton id。

几何目前是占位盒子（骨架 JSON 里的 shape.box），所以这仍是**管线验证件**：
形体简单，好让人一眼看出问题出在动作还是造型。
真角色的几何应该来自 sculpt-spec 那条建模流程，届时只需换掉 shape 部分，
骨架层级和动作数据可以原样复用。

关键差别：**不做 transform_apply**。
catch-the-goose 那边把几何烘进网格、原点全归到世界原点，适合静态道具，
但角色的手臂必须绕肩膀转，不能绕身体中心转。这里每个部件的原点建在关节上。

用法:
  blender --background --python src/blender/make_test_rig.py -- \
      --clip slash --out output/rig/hero_slash.glb
  blender --background --python src/blender/make_test_rig.py -- --list
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "animation-library"

# 动作库的通道名 -> (Blender 数据路径, 值是否为角度)
CHANNELS = {
    "rot": ("rotation_euler", True),
    "loc": ("location", False),
    "scale": ("scale", False),
}


def parse_args() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(description="按动作库生成带关节枢轴的角色")
    ap.add_argument("--out", type=Path, help="输出 .glb")
    ap.add_argument("--clip", help="动作 id")
    ap.add_argument("--skeleton", default="humanoid-basic")
    ap.add_argument("--library", type=Path, default=LIBRARY)
    ap.add_argument("--list", action="store_true", help="列出库里的动作后退出")
    return ap.parse_args(raw)


def load_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"找不到: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for blocks in (bpy.data.meshes, bpy.data.materials, bpy.data.actions):
        for item in list(blocks):
            blocks.remove(item)


def material(name: str, color: list[float]) -> bpy.types.Material:
    existing = bpy.data.materials.get(name)
    if existing:
        return existing
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    principled = result.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = tuple(color)
    principled.inputs["Roughness"].default_value = 0.62
    principled.inputs["Metallic"].default_value = 0.0
    return result


def build_parts(skeleton: dict) -> dict[str, bpy.types.Object]:
    palette = skeleton.get("materials", {})
    created: dict[str, bpy.types.Object] = {}

    for part in skeleton["parts"]:
        shape = part.get("shape")
        if shape is None:
            obj = bpy.data.objects.new(part["id"], None)
            bpy.context.scene.collection.objects.link(obj)
        else:
            bpy.ops.mesh.primitive_cube_add(size=1.0)
            obj = bpy.context.active_object
            obj.name = part["id"]
            obj.data.name = f"{part['id']}-mesh"
            # 缩放盒子，再把顶点推到关节外侧：apply 后原点仍留在关节上。
            # 这是整件事的关键——转肩膀时手臂绕肩膀转，不绕自身几何中心转。
            obj.scale = tuple(shape["size"])
            bpy.ops.object.transform_apply(scale=True)
            offset = shape.get("offset", [0, 0, 0])
            for vertex in obj.data.vertices:
                vertex.co.x += offset[0]
                vertex.co.y += offset[1]
                vertex.co.z += offset[2]
            name = shape.get("material")
            if name:
                obj.data.materials.append(material(name, palette[name]))
            bevel = obj.modifiers.new("Bevel", "BEVEL")
            bevel.width = 0.02
            bevel.segments = 2
        obj.location = tuple(part["joint"])
        obj.rotation_mode = "XYZ"
        created[part["id"]] = obj

    for part in skeleton["parts"]:
        parent = part.get("parent")
        if parent:
            child = created[part["id"]]
            child.parent = created[parent]
            child.matrix_parent_inverse = created[parent].matrix_world.inverted()
    bpy.context.view_layer.update()
    return created


def apply_clip(parts: dict[str, bpy.types.Object], clip: dict) -> None:
    for part_name, tracks in clip["tracks"].items():
        obj = parts.get(part_name)
        if obj is None:
            raise SystemExit(
                f"动作 {clip['id']} 引用了骨架里没有的部件: {part_name}")
        base_location = tuple(obj.location)
        for channel, keys in tracks.items():
            if channel not in CHANNELS:
                raise SystemExit(f"未知通道 {channel}（动作 {clip['id']}）")
            path, is_angle = CHANNELS[channel]
            for frame, value in keys:
                if is_angle:
                    obj.rotation_euler = tuple(math.radians(v) for v in value)
                elif channel == "loc":
                    # 位移是相对建模位置的偏移，直接写绝对值会把部件挪走。
                    obj.location = tuple(base_location[i] + value[i]
                                         for i in range(3))
                else:
                    obj.scale = tuple(value)
                obj.keyframe_insert(data_path=path, frame=frame)

    for obj in parts.values():
        action = obj.animation_data.action if obj.animation_data else None
        if not action:
            continue
        for curve in action.fcurves:
            if clip["loop"]:
                # 循环动作用连续加速插值：首尾姿态相同还不够，
                # 接缝处的速度也必须连续，否则每圈都会顿一下。
                curve.auto_smoothing = "CONT_ACCEL"
            for point in curve.keyframe_points:
                # AUTO_CLAMPED 防止贝塞尔在极值处过冲——
                # 过冲会让挥砍的定格帧先荡过去再荡回来，力道就散了。
                point.interpolation = "BEZIER"
                point.handle_left_type = "AUTO_CLAMPED"
                point.handle_right_type = "AUTO_CLAMPED"


def main() -> None:
    options = parse_args()
    library = options.library if options.library.is_absolute() else ROOT / options.library

    if options.list:
        index = load_json(library / "library.json")
        print(f"骨架: {', '.join(index['skeletons'])}")
        for clip in index["clips"]:
            kind = "循环" if clip["loop"] else "一次性"
            print(f"  {clip['id']:<8} {kind}  末帧={clip['end']:<4} "
                  f"部件={clip['parts']:<3} 关键帧={clip['keyframes']}")
        return

    if not options.clip or not options.out:
        raise SystemExit("需要 --clip 和 --out（或用 --list 查看动作库）")

    skeleton = load_json(library / f"skeletons/{options.skeleton}.json")
    clip = load_json(library / f"clips/{options.skeleton}/{options.clip}.json")
    if clip.get("skeleton") != skeleton["id"]:
        raise SystemExit(
            f"动作 {clip['id']} 声明的骨架是 {clip.get('skeleton')}，"
            f"和 {skeleton['id']} 对不上")

    out = options.out if options.out.is_absolute() else ROOT / options.out

    clear_scene()
    parts = build_parts(skeleton)
    apply_clip(parts, clip)
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = clip["end"]

    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    # 必须打包成**一条**动画，两个开关缺一不可：
    #   export_animation_mode="SCENE"        按场景导，而不是按 action 导
    #   export_anim_scene_split_object=False 这个默认是 True，
    #                                        即使 SCENE 模式也会再按对象拆开
    # 默认设置下 11 个部件会导成 11 条独立动画，重新导入时只有一条激活、
    # 其余进 NLA 静默不播，表现就是"角色几乎不动"——而全程不报错。
    bpy.ops.export_scene.gltf(filepath=str(out), export_format="GLB",
                              export_animations=True,
                              export_animation_mode="SCENE",
                              export_anim_scene_split_object=False,
                              export_frame_range=True)
    meshes = [o for o in parts.values() if o.type == "MESH"]
    triangles = sum(len(p.vertices) - 2 for o in meshes for p in o.data.polygons)
    print(f"[make_test_rig] clip={clip['id']} loop={clip['loop']} "
          f"部件={len(meshes)} 三角面={triangles} 帧范围=1..{clip['end']} -> {out}")


if __name__ == "__main__":
    main()
