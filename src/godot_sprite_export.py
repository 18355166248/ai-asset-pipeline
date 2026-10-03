"""将实际二维动作包导出为 Godot SpriteFrames；不修改源包或批准美术。"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from asset_bundle import read_json, within
from character_workbench import load_sprite


def export(manifest_path, out):
    manifest_path, out = manifest_path.resolve(), out.resolve()
    # 复用帧矩形/时长/loop/anchor校验，避免导出时猜格子或把非均匀时长等分。
    load_sprite({'manifest': str(manifest_path)}, manifest_path.parent)
    manifest = read_json(manifest_path)
    atlas = within(manifest_path.parent, manifest['atlas'])
    if out.exists():
        raise ValueError('输出已存在，不覆盖导出批次')
    out.parent.mkdir(parents=True, exist_ok=True)
    states = manifest['states']
    count = sum(len(state['frames']) for state in states)
    lines = [f'[gd_resource type="SpriteFrames" load_steps={count+2} format=3]',
             '[ext_resource type="Texture2D" path="atlas.png" id="atlas"]']
    animations = []
    index = 0
    for state in states:
        frames = []
        for frame in state['frames']:
            texture_id = f'frame_{index}'
            lines.extend([f'[sub_resource type="AtlasTexture" id="{texture_id}"]',
                          'atlas = ExtResource("atlas")',
                          f'region = Rect2({frame["x"]}, {frame["y"]}, {frame["w"]}, {frame["h"]})'])
            # Godot duration是相对帧时长；固定10fps后用ms/100，实际时间仍为原ms。
            frames.append(f'{{"duration": {frame["durationMs"]/100}, "texture": SubResource("{texture_id}")}}')
            index += 1
        animations.append('{"frames": ['+', '.join(frames)+'], "loop": '+str(state['loop']).lower()+', "name": &'+json.dumps(state['name'])+', "speed": 10.0}')
    lines.extend(['[resource]', 'animations = ['+',\n'.join(animations)+']'])
    first = states[0]['frames'][0]
    anchor = manifest.get('anchor', [.5, 1])
    offset = [(0.5-anchor[0])*first['w'], (0.5-anchor[1])*first['h']]
    default = 'idle' if any(s['name']=='idle' for s in states) else states[0]['name']
    repo = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='.godot-sprite-', dir=out.parent) as temporary:
        stage = Path(temporary) / 'result'; stage.mkdir()
        shutil.copy2(atlas, stage/'atlas.png')
        shutil.copy2(manifest_path, stage/'source-manifest.json')
        (stage/'hero_frames.tres').write_text('\n\n'.join(lines)+'\n')
        (stage/'export.json').write_text(json.dumps({'status':'draft','framePositions':count,
            'anchor':anchor,'spriteOffset':offset,'sourceRelease':manifest.get('release',{}),
            'sourceManifestSha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            'atlasSha256':hashlib.sha256(atlas.read_bytes()).hexdigest(),
            'note':'SpriteFrames import only; jump root, combat/cancel windows and game acceptance stay with consumer.'},ensure_ascii=False,indent=2)+'\n')
        (stage/'project.godot').write_text('config_version=5\n[application]\nconfig/name="GPT 2D Motion Import"\nrun/main_scene="res://preview.tscn"\n[display]\nwindow/size/viewport_width=760\nwindow/size/viewport_height=440\n[rendering]\nrenderer/rendering_method="gl_compatibility"\nenvironment/defaults/default_clear_color=Color(0.08,0.14,0.18,1)\n')
        (stage/'preview.tscn').write_text(f'''[gd_scene load_steps=3 format=3]
[ext_resource type="SpriteFrames" path="res://hero_frames.tres" id="frames"]
[ext_resource type="Script" path="res://preview.gd" id="script"]
[node name="Preview" type="Node2D"]
script = ExtResource("script")
[node name="Ground" type="Line2D" parent="."]
points = PackedVector2Array(80,380,680,380)
width = 1.0
default_color = Color(0.6,0.8,0.7,1)
[node name="Hero" type="AnimatedSprite2D" parent="."]
position = Vector2(380,380)
offset = Vector2({offset[0]},{offset[1]})
texture_filter = 2
sprite_frames = ExtResource("frames")
animation = &{json.dumps(default)}
autoplay = {json.dumps(default)}
[node name="Info" type="Label" parent="."]
position = Vector2(24,20)
''')
        for name in ['preview.gd','validate.gd']:
            shutil.copy2(repo/'examples/godot-sprite'/name,stage/name)
        stage.rename(out)
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    try: print(export(args.manifest,args.out))
    except (ValueError,KeyError,TypeError,OSError) as error: parser.error(str(error))
