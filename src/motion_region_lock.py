"""按显式裁切线复用头部，或按矩形保留局部变化；不自动识别部位或推断视觉验收。"""
import argparse
import hashlib
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

from asset_bundle import build, read_json, write_json, within, integer
from character_workbench import load_sprite


def splice(frame, reference, cut_y, feather, dy):
    if frame.size != reference.size:
        raise ValueError("参考与动作必须共用完整画布，不能逐帧缩放")
    shifted = Image.new("RGBA", frame.size)
    shifted.paste(reference, (0, dy))
    source = np.asarray(frame.convert("RGBA"), dtype=float) / 255
    fixed = np.asarray(shifted, dtype=float) / 255
    # 透明轮廓先预乘 alpha 再混合，避免低透明像素出现黑边或重复衰减。
    weights = np.clip((cut_y + dy - np.arange(frame.height)) / feather, 0, 1)[:, None, None]
    alpha = source[:, :, 3:4] * (1-weights) + fixed[:, :, 3:4] * weights
    color = source[:, :, :3] * source[:, :, 3:4] * (1-weights) + fixed[:, :, :3] * fixed[:, :, 3:4] * weights
    color = np.divide(color, alpha, out=np.zeros_like(color), where=alpha > 0)
    result = Image.fromarray(np.rint(np.concatenate([color, alpha], axis=2) * 255).astype("uint8"))
    # 接缝下方完全沿用源原画字节，透明像素的隐藏RGB也保留，避免加工改变未指定身体区域。
    unchanged_y = max(0, min(frame.height, cut_y + dy))
    result.paste(frame.crop((0, unchanged_y, frame.width, frame.height)), (0, unchanged_y))
    return result


def rectangle_patch(reference, candidate, rect, feather):
    if reference.size != candidate.size:
        raise ValueError("矩形局部复用要求相同画布")
    left, top, right, bottom = rect
    if not (0 <= left < right <= reference.width and 0 <= top < bottom <= reference.height) or feather < 1:
        raise ValueError("局部矩形或接缝带无效")
    base = np.asarray(reference.crop(rect).convert("RGBA"), dtype=float) / 255
    patch = np.asarray(candidate.crop(rect).convert("RGBA"), dtype=float) / 255
    y, x = np.indices((bottom-top, right-left))
    edge = np.minimum.reduce([x, right-left-1-x, y, bottom-top-1-y])
    weights = np.clip(edge / feather, 0, 1)[:, :, None]
    # 仅羽化空间接缝，不混合播放时间；矩形之外直接保留原字节，避免无关服饰漂移。
    alpha = base[:, :, 3:4] * (1-weights) + patch[:, :, 3:4] * weights
    color = base[:, :, :3] * base[:, :, 3:4] * (1-weights) + patch[:, :, :3] * patch[:, :, 3:4] * weights
    color = np.divide(color, alpha, out=np.zeros_like(color), where=alpha > 0)
    result = reference.copy()
    result.paste(Image.fromarray(np.rint(np.concatenate([color, alpha], axis=2)*255).astype("uint8")), (left, top))
    return result


def run(plan_path, out):
    plan_path, out = plan_path.resolve(), out.resolve()
    plan = read_json(plan_path)
    if plan.get("version") != 1:
        raise ValueError("仅支持 version=1")
    manifest_path = (plan_path.parent / plan["manifest"]).resolve()
    # 使用已有动作契约校验时长、loop、帧范围与 atlas 路径；只做明确指定的二维加工。
    load_sprite({"manifest": str(manifest_path)}, manifest_path.parent)
    manifest = read_json(manifest_path)
    states = [s for s in manifest["states"] if s["name"] == plan["action"]]
    if len(states) != 1:
        raise ValueError("加工 action 不存在或重复")
    state = states[0]
    atlas_path = within(manifest_path.parent, manifest["atlas"])
    atlas = Image.open(atlas_path).convert("RGBA")
    frames = [atlas.crop((f["x"], f["y"], f["x"]+f["w"], f["y"]+f["h"])) for f in state["frames"]]
    reference_index = integer(plan["referenceFrame"], "referenceFrame", minimum=0, maximum=len(frames)-1)
    width, height = frames[reference_index].size
    if any(im.size != (width, height) for im in frames) or width*len(frames) > 16384:
        raise ValueError("帧画布不一致或图集过宽")
    operation = plan.get("operation", "upper-region")
    if operation not in ("upper-region", "rectangle-patch"):
        raise ValueError("未知局部复用方式")
    reference = frames[reference_index]
    extra_sources = []
    reference_frames = None
    indices = plan.get("frameIndices", list(range(len(frames))))
    if not isinstance(indices, list) or not indices or len(set(indices)) != len(indices):
        raise ValueError("frameIndices需要非空且不重复的帧索引")
    for index in indices:
        integer(index, "frameIndices", minimum=0, maximum=len(frames)-1)
    if "referenceImage" in plan:
        reference_path = (plan_path.parent / plan["referenceImage"]).resolve()
        with Image.open(reference_path) as source:
            reference = source.convert("RGBA")
        if reference.size != (width, height):
            raise ValueError("外部参考必须使用同一完整画布，不自动缩放")
        extra_sources.append(reference_path)
    if "referenceManifest" in plan:
        if operation != "rectangle-patch" or "referenceImage" in plan:
            raise ValueError('逐帧参考包仅用于rectangle-patch，不能同时指定referenceImage')
        source_path = (plan_path.parent / plan['referenceManifest']).resolve()
        load_sprite({'manifest':str(source_path)},source_path.parent)
        source_data = read_json(source_path)
        source_state = next((s for s in source_data['states'] if s['name']==plan.get('referenceAction',plan['action'])),None)
        if source_state is None or len(source_state['frames'])!=len(frames):
            raise ValueError('逐帧参考动作不存在或帧数不一致')
        if source_data['anchor']!=manifest['anchor'] or source_state['loop']!=state['loop'] or [f['durationMs'] for f in source_state['frames']]!=[f['durationMs'] for f in state['frames']]:
            raise ValueError('逐帧参考需要同锚点、循环与时长，先显式编排对应相位')
        source_atlas_path = within(source_path.parent,source_data['atlas'])
        source_atlas = Image.open(source_atlas_path).convert('RGBA')
        if any((f['w'],f['h'])!=(width,height) for f in source_state['frames']):
            raise ValueError('逐帧参考画布不一致')
        # 基础区域必须来自对应相位，不能把第0帧身体复制到整套，抹掉已生成的摆臂/迈步。
        reference_frames = [source_atlas.crop((f['x'],f['y'],f['x']+f['w'],f['y']+f['h'])) for f in source_state['frames']]
        extra_sources.extend([source_path,source_atlas_path])
    protected = plan.get('protectedRects',[])
    if not isinstance(protected,list) or (protected and operation!='rectangle-patch'):
        raise ValueError('protectedRects仅用于矩形局部加工')
    for area in protected:
        if not isinstance(area,list) or len(area)!=4:
            raise ValueError('保护区域需要四个坐标')
        for i,v in enumerate(area):integer(v,'protectedRects',minimum=0,maximum=width if i%2==0 else height)
        if area[2]<=area[0] or area[3]<=area[1]:raise ValueError('保护区域不得为空')
    if operation == "rectangle-patch":
        rect = plan["rect"]
        if not isinstance(rect, list) or len(rect) != 4:
            raise ValueError("rect 需要 [left,top,right,bottom]")
        for i, value in enumerate(rect):
            integer(value, "rect", minimum=0, maximum=width if i % 2 == 0 else height)
        if rect[2] <= rect[0] or rect[3] <= rect[1]:
            raise ValueError("rect 不得为空")
        feather = integer(plan["feather"], "feather", minimum=1, maximum=min(rect[2]-rect[0], rect[3]-rect[1])//2)
        shifts = [0] * len(frames)
    else:
        cut_y = integer(plan["cutY"], "cutY", minimum=1, maximum=height-1)
        feather = integer(plan["feather"], "feather", minimum=1, maximum=cut_y)
        shifts = plan["headOffsetY"]
    if len(shifts) != len(frames):
        raise ValueError("每帧必须明确 headOffsetY")
    for dy in shifts:
        integer(dy, "headOffsetY", minimum=-height//4, maximum=height//4)
        bounds = reference.crop((0, 0, width, cut_y)).getchannel("A").getbbox() if operation == "upper-region" else None
        if operation == "upper-region" and (bounds is None or bounds[1]+dy < 0 or cut_y+dy >= height):
            raise ValueError("位移会裁掉复用区域或越界")
    if out.exists():
        raise ValueError("输出已存在，不覆盖批次")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".region-lock-", dir=out.parent) as temporary:
        stage = Path(temporary) / "result"
        stage.mkdir()
        sheet = Image.new("RGBA", (width*len(frames), height))
        descriptor = {"frames": [], "meta": {"image": "source.png", "frameTags": [{"name": state["name"], "from": 0, "to": len(frames)-1, "direction": "forward"}]}}
        for i, im in enumerate(frames):
            # 单相位修正只处理显式索引；其余帧保留原像素，避免整套动作被同一姿态覆盖。
            base = reference_frames[i] if reference_frames is not None else reference
            patched = im if i not in indices else (rectangle_patch(base, im, rect, feather) if operation == "rectangle-patch" else splice(im, base, cut_y, feather, shifts[i]))
            if i in indices:
                for area in protected:patched.paste(base.crop(tuple(area)),(area[0],area[1]))
            sheet.paste(patched, (i*width, 0))
            descriptor["frames"].append({"filename": f"{i:04d}", "frame": {"x": i*width, "y": 0, "w": width, "h": height}, "duration": state["frames"][i]["durationMs"], "trimmed": False, "rotated": False})
        sheet.save(stage / "source.png")
        write_json(stage / "source.json", descriptor)
        provenance = {"status": "draft", "operation": "explicit-rectangle-patch" if operation == "rectangle-patch" else "explicit-upper-region-reuse", "plan": plan,
                      "sources": [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in [plan_path, manifest_path, atlas_path] + extra_sources],
                      "note": "Derived crops of existing GPT frames; no new GPT call, no frame interpolation. Neck seam and full cycle require visual review."}
        write_json(stage / "provenance.json", provenance)
        recipe = {"version": 1, "kind": "motion", "title": manifest.get("title", "角色") + " · 固定区域复用草稿", "cell": [width, height], "anchor": manifest["anchor"], "background": "keep", "source": provenance,
                  "states": [{"name": state["name"], "loop": state["loop"], "fps": 10}]}
        write_json(stage / "recipe.json", recipe)
        build(stage / "recipe.json", stage / "source.json", stage / "bundle", aseprite=True)
        # 仅导出用户指定动作，不能把这一步称作自动完成角色全套动作。
        stage.rename(out)
    return out / "bundle" / "manifest.json"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(run(args.plan, args.out))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))
