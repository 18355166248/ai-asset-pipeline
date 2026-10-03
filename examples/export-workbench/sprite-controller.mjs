import { spriteFrame, spriteBreathScale } from './motion.mjs';

// 素材只决定姿态；位移与取消规则由消费端明确配置，不读取工作台 previewMotion。
export class SpriteController {
  constructor(manifest, { speed = 90, jumpHeight = 40, launchMs = 80, landMs = 340, breathAmplitude = 0.006, breathPeriod = 2.4, stopContactFrames = [], contactHoldMs = 40, stopClipsByContact = {}, reverseStartOnRelease = false } = {}) {
    if (manifest.kind !== 'motion' || !Array.isArray(manifest.states)) throw new Error('需要二维 motion manifest');
    if (!Array.isArray(manifest.anchor) || manifest.anchor.length !== 2 || manifest.anchor.some(n => !Number.isFinite(n) || n < 0 || n > 1)) throw new Error('需要有效归一化 anchor');
    this.clips = new Map(manifest.states.map(c => [c.name, { ...c, duration: c.frames.reduce((s, f) => s + f.durationMs, 0) / 1000 }]));
    if (this.clips.size !== manifest.states.length) throw new Error('动作名不可重复');
    for (const name of ['idle', 'move', 'attack', 'hit', 'jump']) if (!this.clips.has(name)) throw new Error(`缺动作 ${name}`);
    for (const c of this.clips.values()) {
      if (!c.frames.length || typeof c.loop !== 'boolean' || c.frames.some(f => !Number.isFinite(f.durationMs) || f.durationMs <= 0)) throw new Error('无效帧时长或循环配置');
      if (c.frames.some(f => ['x','y','w','h'].some(k => !Number.isFinite(f[k])) || f.x < 0 || f.y < 0 || f.w <= 0 || f.h <= 0)) throw new Error('无效图集帧坐标');
    }
    if (['jump','attack','hit'].some(name => this.clips.get(name).loop)) throw new Error('示例的跳跃、攻击与受击需要单次动作');
    if (['move-start','move-stop'].some(name => this.clips.get(name)?.loop)) throw new Error('起步/停步过渡需要单次动作');
    const move = this.clips.get('move');
    if (!Array.isArray(stopContactFrames) || stopContactFrames.some(i => !Number.isInteger(i) || i < 0 || i >= move.frames.length) || new Set(stopContactFrames).size !== stopContactFrames.length || (stopContactFrames.length && !move.loop)) throw new Error('落脚索引需要来自循环move的真实帧，且不重复');
    if (!Number.isFinite(contactHoldMs) || contactHoldMs <= 0 || contactHoldMs > 200) throw new Error('落脚保持时间需要0..200ms');
    // 落脚腿与摆臂不同，需由素材作者显式指定对应停步原画；不能靠索引猜姿态。
    if (!stopClipsByContact || typeof stopClipsByContact !== 'object' || Array.isArray(stopClipsByContact)) throw new Error('停步映射需要对象');
    for (const [key, name] of Object.entries(stopClipsByContact)) {
      const index = Number(key), clip = this.clips.get(name);
      if (!Number.isInteger(index) || String(index) !== key || !stopContactFrames.includes(index) || typeof name !== 'string' || !clip || clip.loop || ['idle','move','attack','hit','jump','move-start'].includes(name)) throw new Error('停步映射需要已配置落脚索引和存在的单次停步动作');
    }
    if (typeof reverseStartOnRelease !== 'boolean') throw new Error('起步反向取消需要布尔配置');
    this.reverseStartOnRelease = reverseStartOnRelease;
    this.stopClipsByContact = {...stopClipsByContact}; this.stopClip = null; this.stopContact = null;
    this.stopContacts = new Set(stopContactFrames); this.contactHoldMs = contactHoldMs;
    this.rampInitial = 0; this.settleClip = null;
    if ([speed, jumpHeight, launchMs, landMs].some(n => !Number.isFinite(n)) || speed <= 0 || jumpHeight <= 0 || launchMs < 0 || landMs <= launchMs || landMs / 1000 > this.clips.get('jump').duration) throw new Error('跳跃时间需落在源动作内');
    if (!Number.isFinite(breathAmplitude) || breathAmplitude < 0 || breathAmplitude > .02 || !Number.isFinite(breathPeriod) || breathPeriod < .5 || breathPeriod > 20) throw new Error('呼吸幅度0..2%，周期0.5..20秒');
    this.anchor = manifest.anchor;
    this.speed = speed; this.jumpHeight = jumpHeight;
    this.launch = launchMs / 1000; this.land = landMs / 1000;
    this.breathAmplitude = breathAmplitude; this.breathPeriod = breathPeriod;
    this.x = 0; this.y = 0; this.time = 0; this.action = 'idle'; this.facing = 1;
  }
  trigger(action) {
    if (!['jump', 'attack', 'hit'].includes(action)) return false;
    // 此示例没有空中攻击素材；空中不切到脚底着地的攻击图，也不重置高度。
    if (this.action === 'jump' || (this.action === 'attack' && action !== 'hit')) return false;
    this.action = action; this.time = 0; this.y = 0;
    return true;
  }
  currentClip() { return this.action === 'move-settle' ? this.settleClip : this.action === 'move-stop' && this.stopClip ? this.stopClip : this.clips.get(this.action); }
  currentSpeed() {
    if (this.action === 'move') return this.speed;
    const clip = this.currentClip();
    if (this.action === 'move-start') return this.rampInitial + (this.speed-this.rampInitial)*this.time/clip.duration;
    if (['move-stop','move-settle'].includes(this.action)) return this.rampInitial*(1-this.time/clip.duration);
    return 0;
  }
  prepareSettle() {
    const move = this.clips.get('move');
    const index = spriteFrame(move, this.time);
    this.stopContact = this.stopContacts.has(index) ? index : null;
    if (!this.stopContacts.size || this.stopContact !== null) return false;
    let elapsed = this.time % move.duration * 1000;
    for (let i=0; i<index; i++) elapsed -= move.frames[i].durationMs;
    const frames = [{...move.frames[index], durationMs: Math.max(1e-6, move.frames[index].durationMs-elapsed)}];
    // 继续真实相位到最近一次落脚，不从摆腿中途跳到共同停步图；这里只复用原画。
    for (let i=1; i<=move.frames.length; i++) {
      const next = (index+i)%move.frames.length;
      frames.push({...move.frames[next],durationMs:this.stopContacts.has(next) ? Math.min(this.contactHoldMs,move.frames[next].durationMs) : move.frames[next].durationMs});
      if (this.stopContacts.has(next)) { this.stopContact = next; break; }
    }
    this.settleClip = {name:'move-settle',loop:false,frames,duration:frames.reduce((s,f)=>s+f.durationMs,0)/1000};
    return true;
  }
  prepareStartCancel() {
    const start = this.clips.get('move-start');
    if (!this.reverseStartOnRelease || !start || start.frames.length < 2) return null;
    const index = spriteFrame(start, this.time);
    let elapsed = this.time*1000;
    for (let i=0; i<index; i++) elapsed -= start.frames[i].durationMs;
    // 短按仅撤回已经走过的真实起步姿态，不能先跳到完整后摆再回护身。
    const frames = start.frames.slice(0,index+1).reverse().map((f,i)=>({...f,durationMs:i===0 ? Math.max(1e-6,elapsed) : f.durationMs}));
    frames.push({...this.clips.get('idle').frames[0],durationMs:Math.min(this.contactHoldMs,this.clips.get('idle').frames[0].durationMs)});
    return {name:'move-start-cancel',loop:false,frames,duration:frames.reduce((s,f)=>s+f.durationMs,0)/1000};
  }
  update(dt, direction = 0) {
    if (!Number.isFinite(dt) || dt < 0) throw new Error('dt 必须为非负秒数');
    if (!Number.isFinite(direction)) throw new Error('移动方向必须有限');
    direction = Math.sign(direction);
    const start = this.clips.has('move-start') ? 'move-start' : 'move';
    const stop = () => this.stopClip || this.clips.has('move-stop') ? 'move-stop' : 'idle';
    const enter = (action, initialSpeed=0) => { this.action = action; this.time = 0; this.rampInitial = initialSpeed; };
    // 短按可立即进入停步，再次按住可重入起步；不能等待某个完成回调才解除移动状态。
    if (['idle','move-stop','move-settle'].includes(this.action) && direction) enter(start,this.currentSpeed());
    else if ((this.action === 'move' || this.action === 'move-start') && !direction) {
      const initial = this.currentSpeed();
      const settling = this.action === 'move' && this.prepareSettle();
      // 起步无步行落脚相位，可显式反向撤回；每次松开重选，防止沿用上次前摆图。
      const name = this.action === 'move' ? this.stopClipsByContact[this.stopContact] : null;
      this.stopClip = name ? this.clips.get(name) : this.action === 'move-start' ? this.prepareStartCancel() : null;
      enter(settling ? 'move-settle' : stop(),initial);
    }
    if (direction && ['move','move-start','jump'].includes(this.action)) this.facing = direction;
    let remaining = dt;
    while (remaining > 1e-12) {
      const current = this.currentClip();
      const step = current.loop ? remaining : Math.min(remaining, Math.max(0, current.duration-this.time));
      if (this.action === 'move' || this.action === 'jump') this.x += direction*this.speed*step;
      else if (['move-start','move-stop','move-settle'].includes(this.action)) {
        // 对速度坡度作解析积分；一次大dt和多个小dt在跨过渡边界时仍走同样距离。
        const ramp = ((this.time+step)**2-this.time**2)/(2*current.duration);
        this.x += this.action === 'move-start' ? direction*(this.rampInitial*step+(this.speed-this.rampInitial)*ramp) : this.facing*this.rampInitial*(step-ramp);
      }
      this.time += step; remaining -= step;
      // 分段消费剩余时间，避免一帧跨过短过渡后丢掉动作时间或多走一段路。
      if (!current.loop && this.time >= current.duration-1e-12) {
        enter(this.action === 'move-start' ? (direction ? 'move' : stop()) : this.action === 'move-settle' ? stop() : (direction ? start : 'idle'));
      }
    }
    // 解析弹道：固定飞行时段与顶点高度，避免帧率改变起落时刻；像素原画不插值。
    const q = Math.max(0, Math.min(1, (this.time - this.launch) / (this.land - this.launch)));
    this.y = this.action === 'jump' && q > 1e-12 && q < 1 - 1e-12 ? -4 * this.jumpHeight * q * (1 - q) : 0;
    const clip = this.currentClip();
    return { action: this.action, index: spriteFrame(clip, this.time), frame: clip.frames[spriteFrame(clip, this.time)], x: this.x, y: this.y, facing: this.facing, scaleY: this.action === 'idle' ? spriteBreathScale(this.time, this.breathAmplitude, this.breathPeriod) : 1 };
  }
}
