import { useEffect, useState } from "react";
import { useAtom, useAtomValue, useSetAtom } from "jotai";
import { useNavigate, useParams, Link } from "react-router";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  wizardAtom,
  confirmedAtom,
  acceptedAtom,
  updateWizardAtom,
  type Wizard,
} from "@/state/wizard";
import {
  gate,
  referencePrompt,
  motionPrompt,
  followupPrompt,
  localPreview,
} from "@/lib/prompts.js";
const steps = [
  "角色设定",
  "参考图Prompt",
  "确认参考图",
  "动作与节奏",
  "动作生图",
  "图片加工",
  "预览与修正",
  "导出素材",
  "接入游戏",
];
const intro = [
  "写清固定身份，先从简洁服饰和一个朝向开始。",
  "把下面的Prompt交给Codex，实际生成一张全身身份母版。",
  "填入Codex返回的真实路径，确认外观后锁定身份。",
  "先做待机和完整走路周期，通过后再增加其他动作。",
  "复制请求交给Codex制作；页面不会自动调用生图。",
  "已有图片可以直接从这里继续，先检查真实产物类型。",
  "先看正常速度和128px效果，再指定失败动作与相位。",
  "仅打包你已查看的这批素材，游戏内验收另做。",
  "在目标游戏中做可回退的测试接入，匹配物理与动作。",
];
export default function Pipeline() {
  const v = useAtomValue(wizardAtom),
    update = useSetAtom(updateWizardAtom),
    [confirmed, setConfirmed] = useAtom(confirmedAtom),
    [accepted, setAccepted] = useAtom(acceptedAtom);
  const { step } = useParams(),
    navigate = useNavigate(),
    index = Math.max(0, Math.min(8, Number(step || 1) - 1)) || 0;
  const [status, setStatus] = useState(""),
    [prompt, setPrompt] = useState(""),
    [image, setImage] = useState<File>(),
    [imageUrl, setImageUrl] = useState("");
  useEffect(() => {
    if (!image) {
      setImageUrl("");
      return;
    }
    const url = URL.createObjectURL(image);
    setImageUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [image]);
  // 参数直达仍受门禁约束；后处理允许已有素材独立进入，不要求重做参考图。
  useEffect(() => {
    const error = gate(index, { ...v, confirmed });
    if (error) {
      setStatus(error);
      navigate("/pipeline/1", { replace: true });
    }
  }, [index, v, confirmed, navigate]);
  useEffect(() => {
    setPrompt("");
  }, [v, confirmed, accepted, index]);
  const values = { ...v, confirmed, accepted };
  function go(i: number) {
    const error = i > index ? gate(i, values) : "";
    if (error) {
      setStatus(error);
      return;
    }
    setStatus("");
    navigate(`/pipeline/${i + 1}`);
  }
  function build() {
    try {
      setPrompt(
        index === 1
          ? referencePrompt(values)
          : index === 4
            ? motionPrompt(values)
            : followupPrompt(
                [
                  "",
                  "",
                  "",
                  "",
                  "",
                  "process",
                  "review",
                  "export",
                  "integrate",
                ][index],
                values,
              ),
      );
      setStatus("请求已整理，尚未执行。复制后交给Codex，用实际返回路径继续。");
    } catch (e) {
      setPrompt("");
      setStatus(String(e));
    }
  }
  function field(key: keyof Wizard, label: string, area = false) {
    return (
      <label className="field" key={key}>
        {label}
        {area ? (
          <Textarea
            value={String(v[key])}
            onChange={(e) => update({ [key]: e.target.value })}
          />
        ) : (
          <Input
            value={String(v[key])}
            onChange={(e) =>
              update({
                [key]: ["cell", "display"].includes(key)
                  ? Number(e.target.value)
                  : e.target.value,
              })
            }
          />
        )}
      </label>
    );
  }
  function select(key: keyof Wizard, label: string, options: string[][]) {
    return (
      <label className="field">
        {label}
        <select
          value={String(v[key])}
          onChange={(e) => update({ [key]: e.target.value })}
        >
          {options.map(([value, text]) => (
            <option key={value} value={value}>
              {text || value}
            </option>
          ))}
        </select>
      </label>
    );
  }
  async function copy() {
    setStatus("请求已展示；浏览器未允许复制时可手动选中文本。");
    try {
      await navigator.clipboard.writeText(prompt);
      setStatus("已复制，发送给Codex执行。");
    } catch {
      setStatus("请手动复制下面的请求。");
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <Badge variant="secondary">二维角色 · 分步制作</Badge>
          <h1>从角色想法，到可用动画</h1>
          <p>没有参考图也能开始。已生成图片？直接进入第6步继续。</p>
        </div>
        <Button asChild variant="outline">
          <Link to="/motion">查看真实动作试点</Link>
        </Button>
      </div>
      <div className="workspace-grid">
        <aside className="steps" aria-label="制作步骤">
          {steps.map((s, i) => (
            <button
              key={s}
              aria-current={index === i ? "step" : undefined}
              className={index === i ? "active" : ""}
              onClick={() => go(i)}
            >
              <span>{String(i + 1).padStart(2, "0")}</span>
              {s}
            </button>
          ))}
        </aside>
        <Card>
          <CardHeader>
            <CardDescription>第 {index + 1} / 9 步</CardDescription>
            <CardTitle>{steps[index]}</CardTitle>
            <p>{intro[index]}</p>
          </CardHeader>
          <CardContent className="space-y-5">
            {index === 0 && (
              <>
                {field("identity", "角色身份与服饰", true)}
                {field("style", "画风")}
                {select("direction", "动画朝向", [
                  ["向右侧面"],
                  ["向左侧面"],
                  ["正面"],
                ])}
              </>
            )}
            {index === 2 && (
              <>
                {field("reference", "参考图绝对路径")}
                <label className="field">
                  选择图片，仅本地预览
                  <Input
                    type="file"
                    accept="image/*"
                    onChange={(e) => {
                      setImage(e.target.files?.[0]);
                      setConfirmed(false);
                      setAccepted(false);
                    }}
                  />
                </label>
                {imageUrl && (
                  <img
                    className="reference-preview"
                    src={imageUrl}
                    alt="本地参考图预览"
                  />
                )}
                <label className="check">
                  <Checkbox
                    checked={confirmed}
                    onCheckedChange={(x) => setConfirmed(x === true)}
                  />
                  我已查看真实参考图，确认身份、全身和朝向
                </label>
                <p>页面不读取本机路径；制作时由Codex检查真实文件。</p>
              </>
            )}
            {index === 3 && (
              <>
                <div className="flex flex-wrap gap-4">
                  {["待机", "走路", "出拳", "受击", "跳跃"].map((a) => (
                    <label className="check" key={a}>
                      <Checkbox
                        checked={v.actions.includes(a)}
                        onCheckedChange={(x) =>
                          update({
                            actions: x
                              ? [...v.actions, a]
                              : v.actions.filter((n) => n !== a),
                          })
                        }
                      />
                      {a}
                    </label>
                  ))}
                </div>
                {field("timing", "节奏与玩法要求", true)}
                <div className="two-columns">
                  {field("cell", "导出cell边长 / px")}
                  {field("display", "游戏显示高度 / px")}
                </div>
              </>
            )}
            {index === 5 && (
              <>
                {select("artifactKind", "当前产物类型", [
                  ["auto", "不确定，先检查"],
                  ["reference", "角色参考图"],
                  ["sheet", "动作图集"],
                  ["frames", "独立帧目录"],
                  ["bundle", "atlas与manifest素材包"],
                ])}
                {field("artifact", "图片、目录或manifest的绝对路径")}
                {field("handoff", "已有制作记录或补充要求", true)}
              </>
            )}
            {index === 6 && (
              <>
                {field("manifest", "本批次manifest.json绝对路径")}
                {field("previewUrl", "本机预览地址")}
                {localPreview(v.previewUrl) && (
                  <a
                    href={localPreview(v.previewUrl)}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    打开我的角色预览
                  </a>
                )}
                {field("issues", "需要修正的问题与相位", true)}
              </>
            )}
            {index === 7 && (
              <>
                <label className="check">
                  <Checkbox
                    checked={accepted}
                    onCheckedChange={(x) => setAccepted(x === true)}
                  />
                  我已查看实际动画，确认可以进入导出
                </label>
                {select("exportTarget", "导出格式", [
                  ["universal", "通用PNG / atlas / manifest"],
                  ["web", "通用素材 + Web示例"],
                  ["godot", "通用素材 + Godot资源"],
                ])}
              </>
            )}
            {index === 8 && (
              <>
                {field("project", "目标游戏项目绝对路径")}
                {field("bundle", "已导出素材目录绝对路径")}
                {field("integration", "接入范围", true)}
              </>
            )}
            {[1, 4, 5, 6, 7, 8].includes(index) && (
              <>
                <Button onClick={build}>整理本步骤完整Prompt</Button>
                <label className="field">
                  交给Codex执行
                  <Textarea className="prompt" value={prompt} readOnly />
                </label>
                <Button variant="outline" disabled={!prompt} onClick={copy}>
                  复制Prompt
                </Button>
              </>
            )}
            <p role="status" className="status">
              {status}
            </p>
            <div className="flex justify-between">
              <Button
                variant="outline"
                disabled={index === 0}
                onClick={() => go(index - 1)}
              >
                上一步
              </Button>
              {index < 8 && (
                <Button onClick={() => go(index + 1)}>下一步</Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
