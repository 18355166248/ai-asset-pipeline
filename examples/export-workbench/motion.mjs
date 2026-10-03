// 通道使用保形 Hermite：在关键帧保留连续速度，局部极值切线置零以避免超调。
export function sampleTrack(keys, frame, loop = false, end = 1) {
  if (frame <= keys[0][0]) return [...keys[0][1]];
  if (frame >= keys.at(-1)[0]) return [...keys.at(-1)[1]];
  let i = 0;
  while (keys[i + 1][0] < frame) i++;
  const tangent = (index, axis) => {
    let before = keys[index - 1], after = keys[index + 1];
    const current = keys[index];
    // 闭合周期末帧是首帧副本，邻点必须取上一/下一周期而不是重复点。
    if (loop && keys[0][0] === 1 && keys.at(-1)[0] === end) {
      if (index === 0) before = [keys.at(-2)[0] - (end - 1), keys.at(-2)[1]];
      if (index === keys.length - 1) after = [keys[1][0] + end - 1, keys[1][1]];
    }
    if (!before || !after) return 0;
    const a = (current[1][axis] - before[1][axis]) / (current[0] - before[0]);
    const b = (after[1][axis] - current[1][axis]) / (after[0] - current[0]);
    if (a * b <= 0) return 0;
    const h0 = current[0] - before[0], h1 = after[0] - current[0];
    const w0 = 2 * h1 + h0, w1 = h1 + 2 * h0;
    return (w0 + w1) / (w0 / a + w1 / b);
  };
  const h = keys[i + 1][0] - keys[i][0], t = (frame - keys[i][0]) / h;
  return [0, 1, 2].map(axis => (2*t**3 - 3*t**2 + 1)*keys[i][1][axis] +
    (t**3 - 2*t**2 + t)*h*tangent(i, axis) + (-2*t**3 + 3*t**2)*keys[i+1][1][axis] +
    (t**3 - t**2)*h*tangent(i + 1, axis));
}

export function samplePose(skeleton, clip, time) {
  const localTime = clip.loop ? ((time % clip.duration) + clip.duration) % clip.duration : Math.max(0, Math.min(time, clip.duration));
  const frame = 1 + localTime * clip.fps;
  return Object.fromEntries(skeleton.parts.map(part => {
    const tracks = clip.tracks[part.id] || {};
    return [part.id, Object.fromEntries([['rot', [0,0,0]], ['loc', [0,0,0]], ['scale', [1,1,1]]].map(([channel, fallback]) =>
      [channel, tracks[channel] ? sampleTrack(tracks[channel], frame, clip.loop, clip.end) : fallback]))];
  }));
}

export function spriteFrame(clip, time) {
  const duration = clip.frames.reduce((sum, frame) => sum + frame.durationMs, 0);
  let ms = clip.loop ? ((time * 1000 % duration) + duration) % duration : Math.max(0, Math.min(time * 1000, duration));
  for (let i = 0; i < clip.frames.length; i++) {
    if (ms < clip.frames[i].durationMs) return i;
    ms -= clip.frames[i].durationMs;
  }
  return clip.frames.length - 1;
}

export const smooth = t => { t = Math.max(0, Math.min(1, t)); return t*t*(3 - 2*t); };

// 待机呼吸只对整张原画做微小纵向伸展；绘制端围绕脚底 anchor 缩放，不能抬起落地脚。
export function spriteBreathScale(time, amplitude = 0.006, period = 2.4) {
  return 1 + amplitude * (1 - Math.cos(2 * Math.PI * time / period)) / 2;
}

export function initialCharacter(characters, preferred) {
  const explicit = characters.findIndex(c => c.id === preferred);
  if (explicit >= 0) return explicit;
  const sprite = characters.findIndex(c => c.kind === 'sprite');
  return sprite >= 0 ? sprite : 0;
}
// 只移动整张姿态原画，不混合帧像素；切动作时由新 clip 自行归零，避免残留跳跃高度。
export function samplePreviewRoot(clip, time) {
  const curve = clip?.previewMotion;
  if (!curve || curve.kind !== 'jump-arc') return 0;
  const q = Math.max(0, Math.min(1, (time * 1000 - curve.startMs) / (curve.endMs - curve.startMs)));
  if (q === 0 || q === 1) return 0;
  return -4 * curve.heightPixels * q * (1 - q);
}
