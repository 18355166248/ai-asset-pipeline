export interface Pose {
  image: string;
  rgbaSha256: string;
  durationMs: number;
}
export interface Motion {
  name: string;
  loop: boolean;
  frames: Pose[];
}
export interface Contract {
  version: 1;
  title: string;
  cell: [number, number];
  anchor: [number, number];
  states: Motion[];
  reviews: Record<
    string,
    { verdict: string; fingerprint: string; evidence: string }
  >;
}
export function totalMs(state: Motion): number {
  if (!state.frames.length) throw new Error("动作不能为空");
  for (const frame of state.frames)
    if (
      !Number.isInteger(frame.durationMs) ||
      frame.durationMs < 1 ||
      frame.durationMs > 60000
    )
      throw new Error("每帧时长需要1到60000的整数毫秒");
  return state.frames.reduce((sum, f) => sum + f.durationMs, 0);
}
export function frameAt(state: Motion, time: number): number {
  const duration = totalMs(state);
  if (!Number.isFinite(time)) throw new Error("时间无效");
  let remaining = state.loop
    ? ((time % duration) + duration) % duration
    : Math.max(0, Math.min(time, duration - 1));
  for (let i = 0; i < state.frames.length; i++) {
    remaining -= state.frames[i].durationMs;
    if (remaining < 0) return i;
  }
  return state.frames.length - 1;
}
export function withDuration(
  state: Motion,
  index: number,
  durationMs: number,
): Motion {
  if (!Number.isInteger(index) || !state.frames[index])
    throw new Error("帧索引无效");
  const next = {
    ...state,
    frames: state.frames.map((f, i) =>
      i === index ? { ...f, durationMs } : { ...f },
    ),
  };
  totalMs(next);
  return next;
}
export function reorder(state: Motion, order: number[]): Motion {
  if (
    !order.length ||
    order.some((i) => !Number.isInteger(i) || !state.frames[i])
  )
    throw new Error("播放顺序索引无效");
  const next = { ...state, frames: order.map((i) => ({ ...state.frames[i] })) };
  totalMs(next);
  return next;
}
export function splitPose(
  state: Motion,
  index: number,
  pose: Pose,
  firstMs: number,
): Motion {
  if (
    !state.frames[index] ||
    !Number.isInteger(firstMs) ||
    firstMs < 1 ||
    firstMs >= state.frames[index].durationMs
  )
    throw new Error("拆分时长必须在原帧时长内");
  const frames = state.frames.map((f) => ({ ...f }));
  frames.splice(
    index,
    1,
    { ...frames[index], durationMs: firstMs },
    { ...pose, durationMs: frames[index].durationMs - firstMs },
  );
  const next = { ...state, frames };
  totalMs(next);
  return next;
}
export function editAction(contract: Contract, state: Motion): Contract {
  if (!contract.states.some((s) => s.name === state.name))
    throw new Error("动作不存在");
  totalMs(state);
  const reviews = { ...contract.reviews };
  delete reviews[state.name];
  // 修改时长、排序或补帧即失去该动作的旧验收，文件有效不能代替动作/用户确认。
  return {
    ...contract,
    states: contract.states.map((s) => (s.name === state.name ? state : s)),
    reviews,
  };
}
