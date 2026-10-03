"""构建通用工作台，可选读取 Frontier 的现有源图；绝不修改消费游戏。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from asset_bundle import build as build_bundle, read_json, write_json
from character_workbench import build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--frontier", type=Path, help="frontier-brawler 仓库目录，读取已有二维主角")
    parser.add_argument("--motion-pack", type=Path, help="已有 asset_bundle motion manifest.json")
    parser.add_argument("--models", action="store_true", help="显式加入双足/四足模型检查；默认只做二维")
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        parser.error("输出已存在，请换一个批次目录")
    # 该样例的全部产物位于本次批次；profile 使用相对路径，可搬运重建。
    out.mkdir(parents=True)
    profile = {"version":1,"title":"二维角色动作工作台","characters":[]}
    if args.models:
        models = read_json(ROOT / "recipes/workbench-models.json")["characters"]
        for spec in models:
            spec["library"] = str(ROOT / "animation-library")
        profile["characters"].extend(models)
    if args.motion_pack:
        profile["characters"].append({"id":"my-sprite","title":"我的二维动作包","kind":"sprite",
                                      "manifest":str(args.motion_pack.resolve()), "direction":"side"})
    if args.frontier:
        frontier = args.frontier.resolve()
        data = read_json(frontier / "native/godot/data/first_stage.json")
        sheet = data["sheets"]["hero"]
        source = frontier / "native/godot" / sheet["path"].removeprefix("res://")
        definitions = data["player_actions"]
        frames = out / "frontier-input"
        with Image.open(source) as image:
            if image.width % sheet["columns"] or image.height % len(sheet["rows"]):
                parser.error("源图不能按数据声明的行列等分")
            w, h = image.width // sheet["columns"], image.height // len(sheet["rows"])
            for row, name in enumerate(sheet["rows"]):
                folder = frames / name; folder.mkdir(parents=True)
                for col in range(sheet["columns"]):
                    image.crop((col*w, row*h, (col+1)*w, (row+1)*h)).save(folder / f"{col:04d}.png")
        recipe = {"version":1, "kind":"motion", "title":"Frontier · 现有原画检查",
                  "cell":[w,h], "anchor":[0.5,sheet["baseline"]/h], "background":"keep", "resample":"nearest",
                  "source":{"provider":"existing-project-art", "path":str(source),
                            "note":"均分源图时间用于检查原画；不是 Godot 的分阶段采样、形变或战斗预览"},
                  "states":[{"name":n, "directory":n, "loop":definitions[n]["loop"],
                             "fps":sheet["columns"] * data["tick_rate"] / definitions[n]["frames"]} for n in sheet["rows"]]}
        recipe_path = out / "frontier-recipe.json"; write_json(recipe_path, recipe)
        build_bundle(recipe_path, frames, out / "frontier-motion")
        profile["characters"].append({"id":"frontier-hero", "title":"Frontier · 现有二维角色", "kind":"sprite",
                                     "manifest":"frontier-motion/manifest.json", "defaultAction":"idle", "direction":"side",
                                     # 数据导出包含其他职业和敌人招式，不能全算成首阶段主角的素材缺口。
                                     "requiredActions":["idle","move","slash","slash2","slash3","dash","hit","skill","execute","jump","airSlash"],
                                     "sourceAliases":{"slash3":"slash2", "skill":"slash2", "execute":"slash2", "airSlash":"slash2", "jump":"move"},
                                     "reference":str(source), "identity":"保留 Frontier 当前主角的造型、武器、服饰和侧面比例"})
    if not args.frontier and not args.motion_pack:
        from make_demo import create_demo
        create_demo(out / "fixture")
        profile["characters"].append({"id":"sprite-fixture","title":"二维几何样例 · 仅验证流程","kind":"sprite",
                                      "manifest":"fixture/motion/manifest.json","defaultAction":"idle","direction":"side"})
    write_json(out / "profile.json", profile)
    print(build(out / "profile.json", out / "viewer"))


if __name__ == "__main__":
    main()
