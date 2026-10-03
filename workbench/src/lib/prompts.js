export function referencePrompt(v) {
  return `请使用当前GPT生图，为二维游戏制作一张角色参考原画。\n角色身份：${v.identity.trim()}。\n画风：${v.style}；轮廓清晰，配色固定，小尺寸可读，服饰结构简洁，便于逐帧保持一致。\n相机和姿态：${v.direction}，固定视角，全身中性站姿，四肢自然分开，手脚完整，双脚在同一地面，人物居中。不要跑跳攻击或夸张透视。\n构图：目标源画布512×512，人物占高度约85%，头顶和鞋底留边；实际生成尺寸不同需明确记录，后续统一归一化。\n输出：单个角色，透明背景，无场景、投影、文字、网格、多视角拼图或关节切片。\n先实际生成这一张图片，保存到当前项目的新文件并返回绝对路径。此步不生成动画。先让我确认脸、服饰、比例和朝向，再用此图锁定后续动作身份。`;
}
export function gate(step, v) {
  if (step >= 5) return ""; // 已有产物可直接进入后处理，不强制重做参考图。
  if (step >= 1 && !v.identity.trim())
    return "先写角色身份，或者选择一个起步设定。";
  if (step >= 3 && (!v.reference.trim().startsWith("/") || !v.confirmed))
    return "请填写真实参考图的绝对路径，并确认外观；复制Prompt不代表已经生图。";
  if (
    step >= 4 &&
    (!v.actions.length ||
      !v.timing.trim() ||
      !Number.isInteger(v.cell) ||
      v.cell < 64 ||
      v.cell > 1024 ||
      !Number.isInteger(v.display) ||
      v.display < 16 ||
      v.display > 2048)
  )
    return "请选择动作、填写节奏，并检查尺寸范围。";
  return "";
}
export function motionPrompt(v) {
  const error = gate(4, v);
  if (error) throw new Error(error);
  return `用 $character-motion-kit，先实际查看参考图 ${v.reference.trim()}，确认文件存在、角色完整，再制作二维逐帧动作。\n固定身份：${v.identity.trim()}。画风：${v.style}。朝向：${v.direction}。如果描述与真实参考图冲突，先指出差异并以我确认的参考图为准。\n动作：${v.actions.join("、")}（仅制作已选动作）。节奏方案中未选动作暂不执行：${v.timing.trim()}\n源画布暂用512×512，统一导出cell ${v.cell}×${v.cell}像素，游戏显示高度${v.display}像素；cell包含透明留边，不等于人物高度。检查真实脚底后确定统一地面与anchor。\n先设计关键姿态和每帧时长，先验证待机/走路（若已选择），再做其他动作。走路包含完整左右支撑周期，检查接触、下沉、经过和抬起，禁止滑步、腿交换和肢体残片；补帧保持目标周期时长。\n实际调用当前GPT生图，保留真实Prompt、参考顺序、原图和失败候选。不要改成GLB或关节切片；局部修正记录裁切区域并检查接缝。\n提供正常速度循环、逐帧检查、起停与跨动作衔接预览。输出真实PNG、atlas与manifest（duration、loop、anchor），按已选动作提供可用预览；缺少动作不要伪称完整游戏包。物理位移和命中窗口由消费游戏匹配。素材维持草稿，等待我验收。`;
}
const ABSOLUTE = (value) =>
  typeof value === "string" &&
  value.trim().startsWith("/") &&
  !/[\n\r\0]/.test(value);
export function localPreview(value) {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) &&
      ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname) &&
      !url.username &&
      !url.password
      ? url.href
      : "";
  } catch {
    return "";
  }
}
export function followupPrompt(kind, v) {
  const start =
    "用 $character-motion-kit，读取当前项目规范，在新批次目录继续处理，保留原始素材、实际来源和失败记录。\n";
  if (kind === "process") {
    if (!ABSOLUTE(v.artifact))
      throw new Error("请填写实际图片、目录或manifest的绝对路径。");
    const routes = {
      auto: "先实际查看文件，判断是参考图、动作图集、独立帧还是已加工素材包，再选择对应处理路径。若只有参考图且没有已明确的动作计划，先以待机/走路做起步，说明时长假设并实际生成原画。",
      reference:
        "当前只有角色参考图。先读取原图，确认身份和朝向，再按下述动作要求实际生成关键原画，不能把站姿复制多份当动作。",
      sheet:
        "当前是动作图集。先查看真实行列、空格和姿态顺序，明确裁切矩形；不要猜均匀网格，不要裁掉手脚。",
      frames:
        "当前是独立帧目录。按实际动作与自然数字顺序检查原画，不重复生成已有可用帧。",
      bundle:
        "当前是已有素材包。读取真实manifest和atlas，校验区域、时长、loop与anchor，优先复用，不再次切图或生图。",
    };
    if (!routes[v.artifactKind]) throw new Error("请选择有效的产物类型。");
    if (
      v.artifactKind === "reference" &&
      gate(4, { ...v, reference: v.artifact, confirmed: true })
    )
      throw new Error("只有参考图时，请在第4步填写动作、有效尺寸和节奏。");
    const specification =
      v.artifactKind === "reference"
        ? `目标动作：${v.actions.join("、")}；节奏：${v.timing}；cell ${v.cell}×${v.cell}，游戏显示高度${v.display}px。只执行已选动作，真实参考图决定身份；第1步默认设定若冲突不可覆盖原图。\n`
        : "已有帧按真实制作记录保留动作和时长；缺少时长时先明确假设，不能默默套用页面默认值。\n";
    return (
      start +
      `本次产物：${v.artifact.trim()}。\n${routes[v.artifactKind]}\n${specification}补充记录：${v.handoff.trim() || "未提供，先核对真实素材；不要虚构历史Prompt或生成次数。"}\n检查透明背景、完整四肢、身份和近远腿。统一画布、角色比例、地面与脚底anchor；不按各帧包围盒分别缩放来掩盖漂移。导出透明PNG、atlas.png、manifest.json（每帧durationMs、loop、anchor），保留原图和加工范围。\n仅做已存在或明确要求的动作，缺失动作列出。提供正常速度、逐帧检查预览；返回本次manifest绝对路径和本机预览URL，供页面第7步继续。不要用旧示例替代本次角色。`
    );
  }
  if (kind === "review" || kind === "export") {
    if (!ABSOLUTE(v.manifest))
      throw new Error("请先在第7步填写本批次manifest.json的绝对路径。");
    if (kind === "review")
      return (
        start +
        `本批次manifest：${v.manifest.trim()}。先实际读取素材与逐帧时间。\n${v.issues.trim() ? `需要修正：${v.issues.trim()}。只修失败动作/相位；需要新原画时实际调用GPT并记录，保留旧候选做对比。` : "先生成或更新这批角色的正常1×循环和逐帧预览，并检查首尾循环、脚底稳定、身份与服饰、近远腿、起停和跨动作衔接；输出具体问题和时间点，不自动宣称美术通过。"}\n保持目标时长、循环与身份；补帧后核对落脚和停止片段映射。局部修正明确ROI并检查接缝和旧肢体残片；存在物理试玩时匹配步幅与移动速度。只有部分动作时先做工作台，不伪造完整战斗试玩。\n返回新的manifest绝对路径（若未改素材则说明沿用）和本机预览URL、修改记录与剩余问题，让我在正常速度下验收。`
      );
    if (!v.accepted)
      throw new Error("请先查看实际动画，并勾选确认可以进入导出。");
    const formats = {
      universal: "通用透明PNG、atlas.png、manifest.json及来源记录",
      web: "通用素材与Web预览/试玩示例",
      godot: "通用素材与Godot SpriteFrames资源/预览项目",
    };
    if (!formats[v.exportTarget]) throw new Error("请选择有效的导出格式。");
    return (
      start +
      `导出我已查看的这批动画：${v.manifest.trim()}。格式：${formats[v.exportTarget]}。\n先校验图集区域、每帧时长、循环和anchor，保留实际PNG与已有动作。只有待机/走路也可导出通用包；完整试玩或交付站缺必要动作时明确缺项并提供部分动作预览，不伪造动作，不套用旧角色坐标或起落窗口。\n提供新导出目录、ZIP、资源清单和使用说明；核对ZIP完整性及导出素材与来源一致。有引擎时运行对应资源导入检查，说明实际验证范围。记录用户允许导出，素材仍为draft，正式游戏验收另做。\n返回导出目录绝对路径和预览/下载地址，供页面第9步填写；不要覆盖原始图片或直接替换游戏主角。`
    );
  }
  if (kind === "integrate") {
    if (!ABSOLUTE(v.project) || !ABSOLUTE(v.bundle))
      throw new Error("请填写目标游戏项目和已导出素材目录的绝对路径。");
    return `在游戏项目 ${v.project.trim()} 中接入这批二维角色素材：${v.bundle.trim()}。\n先阅读项目AGENTS与资源规范，检查真实文件，识别引擎、资源加载、角色状态机、地面和单位换算。\n接入范围：${v.integration.trim() || "先新增可回退的测试角色或测试场景，保留现有主角，只接已有动作。"}\n保持原图、逐帧duration、loop和脚底anchor；不要改成GLB。缺失动作明确回退，物理位移、输入、起停、跳跃及命中/取消窗口由游戏状态机匹配，不靠动画时长硬改物理。\n实际运行测试场景，检查移动速度与步幅、脚底滑动、镜像、短按起停、跨动作切换和单次动作结束。按游戏平台验证，浏览器结果不能替代真机。报告修改文件、运行方式、可回退方式和未完成验收；不自动提交或发布。`;
  }
  throw new Error("未知后续步骤。");
}
const TEXT_FIELDS = [
  "identity",
  "style",
  "direction",
  "reference",
  "timing",
  "cell",
  "display",
  "preset",
  "artifactKind",
  "artifact",
  "handoff",
  "manifest",
  "previewUrl",
  "issues",
  "exportTarget",
  "project",
  "bundle",
  "integration",
];
export function restoreDraft(saved) {
  const result = {};
  if (!saved || ![1, 2].includes(saved.version)) return result;
  for (const key of TEXT_FIELDS)
    if (typeof saved[key] === "string") result[key] = saved[key];
  if (Array.isArray(saved.actions))
    result.actions = saved.actions.filter((a) =>
      ["待机", "走路", "出拳", "受击", "跳跃"].includes(a),
    );
  return result; // 确认与验收状态不从草稿恢复，避免旧候选自动通过新一轮。
}
export function invalidate(field) {
  return {
    reference: [
      "identity",
      "style",
      "direction",
      "reference",
      "preset",
    ].includes(field),
    acceptance: [
      "artifact",
      "artifactKind",
      "handoff",
      "manifest",
      "issues",
      "identity",
      "style",
      "direction",
      "reference",
      "timing",
      "cell",
      "display",
      "action",
      "preset",
    ].includes(field),
  };
}
