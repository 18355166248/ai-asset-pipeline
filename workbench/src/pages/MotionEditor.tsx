import { useEffect, useRef, useState } from "react";
import { useAtom } from "jotai";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  pilotAtom,
  contractAtom,
  motionDirtyAtom,
  type Pilot,
} from "@/state/motion";
import {
  frameAt,
  totalMs,
  withDuration,
  reorder,
  editAction,
  type Motion,
} from "@/motion-contract";
export default function MotionEditor() {
  const [pilot, setPilot] = useAtom(pilotAtom),
    [contract, setContract] = useAtom(contractAtom),
    [dirty, setDirty] = useAtom(motionDirtyAtom);
  const [action, setAction] = useState("move"),
    [position, setPosition] = useState(0),
    [playing, setPlaying] = useState(false),
    [duration, setDuration] = useState(""),
    [order, setOrder] = useState(""),
    [issue, setIssue] = useState(""),
    [prompt, setPrompt] = useState(""),
    [plan, setPlan] = useState(""),
    [status, setStatus] = useState(""),
    [error, setError] = useState("");
  const state =
    contract?.states.find((s) => s.name === action) || contract?.states[0];
  const index = state ? frameAt(state, position) : 0,
    frame = state?.frames[index];
  useEffect(() => {
    if (pilot) return;
    const controller = new AbortController();
    fetch("/data/pilot/review-data.json", { signal: controller.signal })
      .then((r) => {
        if (!r.ok)
          throw new Error("试点素材加载失败，请运行npm run prepare:data");
        return r.json();
      })
      .then((data: Pilot) => {
        data.contract.states.forEach(totalMs);
        setPilot(data);
        setContract(data.contract);
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(String(e));
      });
    return () => controller.abort();
  }, [pilot, setPilot, setContract]);
  useEffect(
    () => setDuration(String(frame?.durationMs || "")),
    [action, index, frame?.durationMs],
  );
  const latest = useRef(state);
  latest.current = state;
  // 切路由、后台和暂停均清理RAF；恢复页面后由用户主动播放，避免跳过长时间间隔。
  useEffect(() => {
    if (!playing) return;
    let id = 0,
      last = performance.now();
    const tick = (now: number) => {
      const s = latest.current;
      if (s)
        setPosition((t) =>
          s.loop
            ? (t + now - last) % totalMs(s)
            : Math.min(totalMs(s) - 1, t + now - last),
        );
      last = now;
      id = requestAnimationFrame(tick);
    };
    id = requestAnimationFrame(tick);
    const hide = () => {
      if (document.hidden) setPlaying(false);
    };
    document.addEventListener("visibilitychange", hide);
    return () => {
      cancelAnimationFrame(id);
      document.removeEventListener("visibilitychange", hide);
    };
  }, [playing]);
  function apply(next: Motion) {
    if (!contract) return;
    setContract(editAction(contract, next));
    setDirty(true);
    setPlaying(false);
    setPosition((t) => Math.min(t, totalMs(next) - 1));
    setPlan("");
    setPrompt("");
    setStatus("本地草案已修改；应用到新批次后需要重新检查该动作。");
  }
  function edit(fn: () => void) {
    try {
      fn();
    } catch (e) {
      setStatus(String(e));
    }
  }
  async function copy(text: string) {
    setStatus("文本已展示，复制不可用时可手动选中。");
    try {
      await navigator.clipboard.writeText(text);
      setStatus("已复制，请交给Codex执行。");
    } catch {
      setStatus("请手动复制下面文本。");
    }
  }
  function buildPlan(download = false) {
    if (!pilot || !contract) return;
    const text = JSON.stringify(
      {
        version: 1,
        baselineContractSha256: pilot.baselineSha256,
        states: contract.states,
      },
      null,
      2,
    );
    setPlan(text);
    if (download) {
      const url = URL.createObjectURL(
        new Blob([text], { type: "application/json" }),
      );
      const a = document.createElement("a");
      a.href = url;
      a.download = "motion-plan.json";
      document.body.append(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setStatus("已发起下载，同时展示JSON作为后备。");
    } else void copy(text);
  }
  function repair() {
    if (!pilot || !state) return;
    if (dirty) {
      setStatus("请先应用时序草案，再打开新批次指定修复帧。");
      return;
    }
    if (!issue.trim()) {
      setStatus("先描述这个相位的问题。");
      return;
    }
    const before =
        state.frames[(index + state.frames.length - 1) % state.frames.length],
      after = state.frames[(index + 1) % state.frames.length];
    const text = `用 $character-motion-kit，只修任务 ${pilot.run} 中 ${state.name} 的零起始第${index}帧。问题：${issue.trim()}。先查看身份参考与真实前后帧 ${pilot.run}/${before.image}、${pilot.run}/${after.image}。用当前GPT实际生成替代原画，保持统一画布、身份、比例、脚底和目标时长；不走Grok视频或RIFE，不逐帧缩放掩盖漂移。记录真实Prompt、参考顺序、原图、耗时和候选次数。通过src/sprite_gen_adapter.py candidate登记隔离候选，展示候选及前后衔接，明确采纳后才通过select生成新批次。其他冻结PNG字节与RGBA哈希必须不变。分开报告生成成功、文件有效、动作检查和用户验收，不自动标记通过。`;
    setPrompt(text);
    void copy(text);
  }
  if (error)
    return (
      <Card>
        <CardHeader>
          <CardTitle>素材暂时无法加载</CardTitle>
        </CardHeader>
        <CardContent>
          <p role="alert">{error}</p>
          <Button onClick={() => location.reload()}>重新加载</Button>
        </CardContent>
      </Card>
    );
  if (!pilot || !contract || !state || !frame)
    return <p role="status">正在读取真实试点素材…</p>;
  return (
    <>
      <div className="page-heading">
        <div>
          <Badge variant="secondary">
            sprite-gen {pilot.proof.engine.version} ·{" "}
            {pilot.proof.engine.commit.slice(0, 12)}
          </Badge>
          <h1>动作工作层</h1>
          <p>{contract.title} · 已有素材导入，新增生图0次</p>
        </div>
        <Badge variant="outline">动作观感未验收</Badge>
      </div>
      <div className="editor-grid">
        <Card>
          <CardHeader>
            <CardTitle>真实时序 · 128px预览</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <label className="field">
              动作
              <select
                value={state.name}
                onChange={(e) => {
                  setAction(e.target.value);
                  setPosition(0);
                  setPrompt("");
                  setPlaying(false);
                }}
              >
                {contract.states.map((s) => (
                  <option key={s.name}>{s.name}</option>
                ))}
              </select>
            </label>
            <div className="animation-stage">
              <img
                src={`/data/pilot/${frame.image}`}
                alt="当前角色实际原画"
                width={128}
                height={128}
              />
            </div>
            <div className="flex gap-3">
              <Button onClick={() => setPlaying(!playing)}>
                {playing ? "暂停" : "播放"}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setPlaying(false);
                  const i = (index + 1) % state.frames.length;
                  setPosition(
                    state.frames
                      .slice(0, i)
                      .reduce((n, f) => n + f.durationMs, 0),
                  );
                }}
              >
                下一原画
              </Button>
            </div>
            <p>
              {position.toFixed(0)} / {totalMs(state)} ms · 原画 {index + 1}/
              {state.frames.length} · {frame.durationMs}ms
            </p>
            <label className="field">
              时间 / ms
              <input
                type="range"
                min="0"
                max={totalMs(state) - 1}
                step="1"
                value={position}
                onChange={(e) => {
                  setPlaying(false);
                  setPosition(Number(e.target.value));
                }}
              />
            </label>
            <label className="field">
              当前原画时长 / ms
              <Input
                type="number"
                min="1"
                max="60000"
                value={duration}
                onFocus={() => setPlaying(false)}
                onChange={(e) => setDuration(e.target.value)}
              />
            </label>
            <Button
              onClick={() =>
                edit(() => apply(withDuration(state, index, Number(duration))))
              }
            >
              写入本地时序草案
            </Button>
            <label className="field">
              播放顺序（零起始，可重复）
              <Input
                value={order}
                placeholder="0,1,2,3"
                onChange={(e) => setOrder(e.target.value)}
              />
            </label>
            <Button
              variant="outline"
              onClick={() =>
                edit(() => {
                  if (!order.trim()) throw new Error("先填写播放顺序");
                  apply(reorder(state, order.split(",").map(Number)));
                })
              }
            >
              预览新顺序
            </Button>
          </CardContent>
        </Card>
        <div className="space-y-5">
          <Card>
            <CardHeader>
              <CardTitle>应用到新批次</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p>
                修改只影响本地草案，原画保持冻结。每次导出重新读取 durationMs。
              </p>
              <div className="flex flex-wrap gap-3">
                <Button onClick={() => buildPlan()}>展示并复制时序草案</Button>
                <Button variant="outline" onClick={() => buildPlan(true)}>
                  下载JSON
                </Button>
              </div>
              <label className="field">
                时序JSON
                <Textarea readOnly value={plan} />
              </label>
              <label className="field">
                下一步交给Codex
                <Textarea
                  readOnly
                  value={`保存上述JSON为motion-plan.json，运行 src/sprite_gen_adapter.py apply --run ${pilot.run} --plan <JSON绝对路径> --out <新批次目录>。不要覆盖原批次。核验RGBA、总时长和Aseprite时序，重新检查改变的动作。再运行npm run prepare:data --prefix workbench -- --run <新批次目录>并刷新页面。`}
                />
              </label>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>只修失败帧</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <label className="field">
                这个相位的问题
                <Textarea
                  value={issue}
                  placeholder="例如：经过姿态提前伸腿，支撑脚跳动"
                  onChange={(e) => {
                    setIssue(e.target.value);
                    setPrompt("");
                  }}
                />
              </label>
              <Button onClick={repair}>生成并复制定点修复Prompt</Button>
              <Textarea aria-label="定点修复Prompt" readOnly value={prompt} />
              <p>
                新图先进入候选；未通过动作检查与用户验收的版本不能正式交付。
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
      <p role="status" className="status">
        {status || "文件核验通过；这是工程接入试点，不代表真实生图成功率。"}
      </p>
    </>
  );
}
