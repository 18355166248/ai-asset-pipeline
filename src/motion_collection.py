"""合并同一角色的动作包，保留时长、循环和来源；拒绝默默修正不兼容画布。"""
import argparse
import hashlib
import shutil
import tempfile
from pathlib import Path

from PIL import Image

from asset_bundle import build, read_json, write_json, within
from character_workbench import load_sprite


def assemble(config_path, out):
    config_path, out = config_path.resolve(), out.resolve()
    config = read_json(config_path)
    if config.get("version") != 1 or not isinstance(config.get("inputs"), list) or not config["inputs"]:
        raise ValueError("需要 version=1 与非空 inputs")
    clips, inputs = [], []
    names, cell, anchor = set(), None, None
    for item in config["inputs"]:
        source = (config_path.parent / item["manifest"]).resolve()
        data, _ = load_sprite({"manifest": str(source)}, source.parent)
        manifest = read_json(source)
        atlas_path = within(source.parent, manifest["atlas"])
        atlas = Image.open(atlas_path).convert("RGBA")
        requested = item.get("actions", [s["name"] for s in manifest["states"]])
        if not isinstance(requested, list) or not requested or len(set(requested)) != len(requested):
            raise ValueError("actions 需要非空且不重复")
        states = {s["name"]: s for s in manifest["states"]}
        if any(name not in states for name in requested):
            raise ValueError("指定动作不存在")
        if anchor is None:
            anchor = data["anchor"]
        elif anchor != data["anchor"]:
            raise ValueError("角色锚点不一致，需要明确修正素材后再合并")
        for name in requested:
            if name in names:
                raise ValueError("动作重复: " + name)
            names.add(name)
            state = states[name]
            images = []
            for frame in state["frames"]:
                size = (frame["w"], frame["h"])
                if cell is None:
                    cell = size
                elif cell != size:
                    raise ValueError("角色画布不一致，不逐动作缩放掩盖差异")
                images.append(atlas.crop((frame["x"], frame["y"], frame["x"]+size[0], frame["y"]+size[1])))
            clips.append((state, images))
        inputs.append((source, atlas_path, requested))
    count = sum(len(images) for _, images in clips)
    if count*cell[0] > 16384:
        raise ValueError("源图集超过16384像素，请拆分角色集合")
    if out.exists():
        raise ValueError("输出已存在，不覆盖批次")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".motion-collection-", dir=out.parent) as temporary:
        stage = Path(temporary) / "result"
        stage.mkdir()
        source_records = []
        for i, (manifest_path, atlas_path, actions) in enumerate(inputs):
            folder = stage / "inputs" / f"{i:03d}"
            folder.mkdir(parents=True)
            # 搬运副本统一修改 atlas 地址，整套角色包离开原输出目录后仍保留可读来源。
            manifest = read_json(manifest_path)
            manifest["atlas"] = "atlas.png"
            write_json(folder / "manifest.json", manifest)
            shutil.copy2(manifest_path, folder / "original-manifest.json")
            shutil.copy2(atlas_path, folder / "atlas.png")
            audits = []
            # 保留上游审查副本但不继承“整套通过”；合并后的跨动作衔接需要另外验收。
            for filename in ("generation-review.json", "provenance.json"):
                package_root = manifest_path.parent.parent if manifest_path.parent.name == "bundle" else manifest_path.parent
                audit_path = package_root / filename
                if audit_path.is_file():
                    shutil.copy2(audit_path, folder / filename)
                    audits.append({"path": f"inputs/{i:03d}/{filename}", "sha256": hashlib.sha256(audit_path.read_bytes()).hexdigest()})
            source_records.append({"actions": actions, "manifest": f"inputs/{i:03d}/manifest.json", "originalManifest": f"inputs/{i:03d}/original-manifest.json", "atlas": f"inputs/{i:03d}/atlas.png",
                                   "originalManifestSha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                                   "atlasSha256": hashlib.sha256(atlas_path.read_bytes()).hexdigest(), "auditCopies": audits})
        sheet = Image.new("RGBA", (count*cell[0], cell[1]))
        descriptor = {"frames": [], "meta": {"image": "source.png", "frameTags": []}}
        index = 0
        for state, images in clips:
            start = index
            for im, frame in zip(images, state["frames"]):
                sheet.paste(im, (index*cell[0], 0))
                descriptor["frames"].append({"frame": {"x": index*cell[0], "y": 0, "w": cell[0], "h": cell[1]}, "duration": frame["durationMs"], "trimmed": False, "rotated": False})
                index += 1
            descriptor["meta"]["frameTags"].append({"name": state["name"], "from": start, "to": index-1, "direction": "forward"})
        sheet.save(stage / "source.png")
        write_json(stage / "source.json", descriptor)
        provenance = {"provider": "existing-motion-pack-assembly", "status": "draft", "inputs": source_records,
                      "note": "No image generation or frame interpolation; combined actions need visual and consumer acceptance."}
        recipe = {"version": 1, "kind": "motion", "title": config.get("title", "角色动作集合"), "cell": list(cell), "anchor": anchor, "background": "keep", "source": provenance,
                  "states": [{"name": s["name"], "loop": s["loop"], "fps": 10} for s, _ in clips]}
        write_json(stage / "recipe.json", recipe)
        write_json(stage / "provenance.json", provenance)
        build(stage / "recipe.json", stage / "source.json", stage / "bundle", aseprite=True)
        # 全部契约验证成功后才发布，原包保持完整，游戏正式目录仍由验收后的发布步骤决定。
        stage.rename(out)
    return out / "bundle" / "manifest.json"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(assemble(args.config, args.out))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))
