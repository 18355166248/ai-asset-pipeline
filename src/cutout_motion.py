"""真实二维部件图的步态烘焙：交替承重、固定落地轨迹、共用画布，不调用生成服务。"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path

from PIL import Image, ImageEnhance

from asset_bundle import build as build_bundle, integer, number, read_json, within, write_json


def foot_phase(phase, stride, lift, duty=.6):
    phase %= 1
    if phase < duty:
        # 站立脚相对角色匀速后移；与角色前进速度抵消后，世界空间的脚保持落地。
        return stride / 2 - stride * phase / duty, 0.0, True, 0.0
    q = (phase - duty) / (1 - duty)
    slope = -stride / duty * (1 - duty)
    # 摆腿首尾沿用承重段速度，避免抬脚或下一次落地时位置/速度突然反向。
    x = (2*q**3-3*q**2+1)*(-stride/2) + (q**3-2*q**2+q)*slope
    x += (-2*q**3+3*q**2)*(stride/2) + (q**3-q**2)*slope
    return x, -lift*math.sin(math.pi*q)**2, False, -math.radians(8)*math.sin(math.pi*q)**2


def solve_knee(hip, ankle, upper, lower):
    dx, dy = ankle[0]-hip[0], ankle[1]-hip[1]
    distance = math.hypot(dx, dy)
    if not abs(upper-lower) < distance < upper+lower:
        raise ValueError("脚底目标不可达；必须调整步幅/腿长，不能默默拉伸骨骼")
    along = (upper*upper-lower*lower+distance*distance)/(2*distance)
    height = math.sqrt(max(0, upper*upper-along*along))
    return [hip[0]+dx*along/distance+dy*height/distance,
            hip[1]+dy*along/distance-dx*height/distance]


def rotate_point(point, angle):
    c,s = math.cos(angle),math.sin(angle)
    return [c*point[0]-s*point[1],s*point[0]+c*point[1]]


def sample(rig, action, phase):
    phase %= 1
    gait = rig["gait"]
    moving = action == "move"
    if action not in ("idle","move"):
        raise ValueError("当前二维步态烘焙只支持 idle / move")
    root = [rig["root"][0],rig["root"][1]+(gait["bob"]*math.sin(4*math.pi*phase) if moving else .65*math.sin(2*math.pi*phase))]
    lean = math.radians(.7)*math.sin(2*math.pi*phase) if moving else 0.0
    result = {"root":root,"lean":lean,"legs":{},"arms":{}}
    for name, offset in (("near",0),("far",.5)):
        def attach(key):
            delta = rotate_point(rig["attachments"][name+key],lean)
            return [root[0]+delta[0],root[1]+delta[1]]
        hip,shoulder = attach("Hip"),attach("Shoulder")
        if moving:
            x,y,ground,roll=foot_phase(phase+offset,gait["stride"],gait["lift"],gait["duty"])
        else:
            x,y,ground,roll=(-6 if name=="near" else 6),0,True,0
        ankle=[rig["root"][0]+x,gait["ankleY"]+y]
        knee=solve_knee(hip,ankle,rig["bones"]["thigh"],rig["bones"]["calf"])
        result["legs"][name]={"hip":hip,"knee":knee,"ankle":ankle,"ground":ground,"roll":roll}
        upper_angle=(-.30*math.cos(2*math.pi*(phase+offset)) if moving else -.10)+lean
        lower_angle=upper_angle+.25
        elbow=[shoulder[0]+rig["bones"]["upperArm"]*math.sin(upper_angle),shoulder[1]+rig["bones"]["upperArm"]*math.cos(upper_angle)]
        wrist=[elbow[0]+rig["bones"]["forearm"]*math.sin(lower_angle),elbow[1]+rig["bones"]["forearm"]*math.cos(lower_angle)]
        result["arms"][name]={"shoulder":shoulder,"elbow":elbow,"wrist":wrist}
    return result


def load_parts(rig, base):
    source=within(base,rig["image"])
    with Image.open(source) as im:
        if "A" not in im.getbands():
            raise ValueError("二维部件源图必须自带 alpha；不能把 RGB 背景默默当作角色部件")
        sheet=im.convert("RGBA")
    if set(rig["parts"]) != {"body","upperArm","forearm","thigh","calf","boot"}:
        raise ValueError("当前双足模板需要 body / upperArm / forearm / thigh / calf / boot 六个部件")
    parts,records={},[]
    for name,spec in rig["parts"].items():
        rect=spec["rect"]
        if len(rect)!=4 or not 0<=rect[0]<rect[2]<=sheet.width or not 0<=rect[1]<rect[3]<=sheet.height:
            raise ValueError("部件矩形越界: "+name)
        image=sheet.crop(tuple(rect))
        if image.getchannel("A").getbbox() is None:
            raise ValueError("部件全透明: "+name)
        if image.getchannel("A").getextrema()[0] != 0:
            raise ValueError("部件矩形缺少透明边距: "+name)
        anchor=spec["anchor"]
        if len(anchor)!=2 or any(not 0<=v<=1 for v in anchor):
            raise ValueError("部件锚点不合法: "+name)
        height=number(spec["height"],"部件高度",1,4096)
        parts[name]={"image":image,"anchor":[anchor[0]*image.width,anchor[1]*image.height],"height":height}
        # 远侧只在渲染时压暗，原始部件和 alpha 保留；所有帧复用同一张脸和服饰。
        dark=ImageEnhance.Brightness(image.convert("RGB")).enhance(.80).convert("RGBA")
        dark.putalpha(image.getchannel("A"))
        parts[name]["dark"]=dark
        records.append({"name":name,"sourceRect":rect,"anchor":anchor,"height":spec["height"]})
    return parts,{"source":str(source),"sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"parts":records}


def stamp(canvas, part, point, angle=0, dark=False, supersample=3):
    image=part["dark"] if dark else part["image"]
    scale=part["height"]/image.height
    ax,ay=part["anchor"]
    x,y=point
    c,s=math.cos(angle),math.sin(angle)
    # 在整张画布上做亚像素逆变换，避免每帧取整部件位置造成关节和脚底抖动。
    inverse=(c/(scale*supersample),s/(scale*supersample),ax-(c*x+s*y)/scale,
             -s/(scale*supersample),c/(scale*supersample),ay+(s*x-c*y)/scale)
    layer=image.transform(canvas.size,Image.Transform.AFFINE,inverse,Image.Resampling.BICUBIC)
    canvas.alpha_composite(layer)


def segment(canvas,part,start,end,dark):
    dx,dy=end[0]-start[0],end[1]-start[1]
    stamp(canvas,part,start,-math.atan2(dx,dy),dark)


def render(rig,parts,pose):
    canvas=Image.new("RGBA",tuple(v*3 for v in rig["cell"]))
    for name in ("far","near"):
        leg=pose["legs"][name]
        stamp(canvas,parts["boot"],leg["ankle"],leg["roll"],name=="far")
        segment(canvas,parts["calf"],leg["knee"],leg["ankle"],name=="far")
        segment(canvas,parts["thigh"],leg["hip"],leg["knee"],name=="far")
    arm=pose["arms"]["far"]
    segment(canvas,parts["forearm"],arm["elbow"],arm["wrist"],True)
    segment(canvas,parts["upperArm"],arm["shoulder"],arm["elbow"],True)
    stamp(canvas,parts["body"],pose["root"],pose["lean"])
    arm=pose["arms"]["near"]
    segment(canvas,parts["forearm"],arm["elbow"],arm["wrist"],False)
    segment(canvas,parts["upperArm"],arm["shoulder"],arm["elbow"],False)
    return canvas.resize(tuple(rig["cell"]),Image.Resampling.LANCZOS)


def bake(rig_path,out):
    rig=read_json(rig_path)
    if rig.get("version")!=1 or out.exists():
        raise ValueError("需要 version:1 配置与新的输出批次")
    if len(rig["cell"])!=2:
        raise ValueError("cell 需要 [宽,高]")
    for size in rig["cell"]:
        integer(size,"cell",4096)
    number(rig["gait"]["duty"],"承重比例",.05,.95)
    for key in ("stride","lift"):
        number(rig["gait"][key],key,1,4096)
    for key in ("root",):
        if len(rig[key])!=2:
            raise ValueError("root 需要二维坐标")
        for value in rig[key]:
            number(value,key,-4096,4096)
    for value in rig["bones"].values():
        number(value,"骨长",1,4096)
    parts,source=load_parts(rig,rig_path.parent)
    motions={}
    # 先采样全部姿态验证可达性，再写文件；错误参数不能留下貌似完成的动作包。
    for action,spec in rig["actions"].items():
        count=spec["frames"]
        if not isinstance(count,int) or not 2<=count<=240 or not 1<=spec["fps"]<=240:
            raise ValueError("帧数/帧率不合法")
        motions[action]=[sample(rig,action,i/count) for i in range(count)]
    out.mkdir(parents=True)
    # 带上原始部件和配置快照，整包搬走后也能重新烘焙，不能依赖开发机的输入绝对路径。
    source_name="source-parts"+Path(source["source"]).suffix.lower()
    shutil.copy2(source["source"],out/source_name)
    snapshot=dict(rig)
    snapshot["image"]=source_name
    write_json(out/"rig.json",snapshot)
    source["rigSha256"]=hashlib.sha256(rig_path.read_bytes()).hexdigest()
    source["snapshotSha256"]=hashlib.sha256((out/"rig.json").read_bytes()).hexdigest()
    source["rendererSha256"]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (out/"parts").mkdir()
    for name,part in parts.items():
        part["image"].save(out/"parts"/f"{name}.png")
    write_json(out/"parts.json",{"version":1,"kind":"2d-cutout-parts","parts":[
        {"name":name,"image":f"parts/{name}.png","anchor":rig["parts"][name]["anchor"],"height":part["height"]}
        for name,part in parts.items()]})
    records,tags=[],[]
    columns=8
    total=sum(len(poses) for poses in motions.values())
    w,h=rig["cell"]
    atlas=Image.new("RGBA",(columns*w,math.ceil(total/columns)*h))
    for action,poses in motions.items():
        folder=out/"frames"/action
        folder.mkdir(parents=True)
        for index,pose in enumerate(poses):
            image=render(rig,parts,pose)
            image.save(folder/f"{index:04d}.png")
            slot=len(records)
            x,y=slot%columns*w,slot//columns*h
            atlas.paste(image,(x,y))
            fps=rig["actions"][action]["fps"]
            # 60fps 不能把所有帧取整为 17ms，否则 800ms 的周期会被拉长到 816ms。
            duration=round((index+1)*1000/fps)-round(index*1000/fps)
            records.append({"frame":{"x":x,"y":y,"w":w,"h":h},"duration":duration,"trimmed":False,"rotated":False})
        tags.append({"name":action,"from":len(records)-len(poses),"to":len(records)-1,"direction":"forward"})
    atlas.save(out/"source-atlas.png")
    write_json(out/"source-frames.json",{"frames":records,"meta":{"image":"source-atlas.png","frameTags":tags}})
    recipe={"version":1,"kind":"motion","title":"薄荷冒险家 · 二维分层步态 v3","cell":rig["cell"],
            "anchor":[.5,rig["gait"]["groundY"]/rig["cell"][1]],"resample":"lanczos","background":"keep",
            "source":{"provider":"codex-imagegen-parts-and-local-2d-ik","rigSnapshot":"../rig.json","rigSha256":source["rigSha256"],
                      "note":"同一套真实二维部件连续渲染，非整张图集重抽或视频抽帧"},
            "states":[{"name":a,"fps":s["fps"],"loop":True} for a,s in rig["actions"].items()]}
    write_json(out/"recipe.json",recipe)
    write_json(out/"pose-tracks.json",{"version":1,"motions":motions,"note":"骨架轨迹检查不能替代美术接缝和游戏内验收"})
    write_json(out/"provenance.json",source)
    build_bundle(out/"recipe.json",out/"source-frames.json",out/"bundle",aseprite=True)
    return out/"bundle"/"manifest.json"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rig",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    print(bake(args.rig.resolve(),args.out.resolve()))


if __name__=="__main__":
    main()
