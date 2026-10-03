import { samplePose, spriteFrame, smooth, initialCharacter, samplePreviewRoot } from './motion.mjs';

const $ = id => document.getElementById(id);
let data, report, character, clip, time = 0, playing = true, tour = false, tourTime = 0;
let model, mixer, glbActions = [], nodes = {}, displayedPose = {}, transition = null, spriteImage;
let selectionVersion = 0, last = performance.now();
const visits = [];
let THREE, OrbitControls, GLTFLoader, renderer, scene, camera, controls, modelSetup;
async function ensureModelView() {
  // 二维素材使用 Canvas2D，不依赖 WebGL；只有用户选择模型时才加载三维库和场景。
  if (!modelSetup) modelSetup = (async () => {
    [THREE, {OrbitControls}, {GLTFLoader}] = await Promise.all([
      import('three'), import('three/addons/controls/OrbitControls.js'), import('three/addons/loaders/GLTFLoader.js')]);
    renderer = new THREE.WebGLRenderer({canvas: $('model'), antialias: true});
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;
    scene = new THREE.Scene(); scene.background = new THREE.Color(0x182832);
    camera = new THREE.PerspectiveCamera(38, 1, 0.01, 200);
    controls = new OrbitControls(camera, $('model')); controls.enableDamping = true;
    scene.add(new THREE.HemisphereLight(0xddefff, 0x283a35, 2));
    const light = new THREE.DirectionalLight(0xffe7c5, 3);
    light.position.set(4, 7, 5); light.castShadow = true; light.shadow.mapSize.set(1024, 1024);
    Object.assign(light.shadow.camera, {left: -5, right: 5, top: 5, bottom: -5, near: 0.1, far: 30});
    light.shadow.normalBias = 0.02; scene.add(light);
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.MeshStandardMaterial({color: 0x253b42, roughness: 1}));
    ground.rotation.x = -Math.PI / 2; ground.position.y = -0.01; ground.receiveShadow = true; scene.add(ground);
    scene.add(new THREE.GridHelper(12, 24, 0x506d74, 0x344c54));
    setView(); resize();
  })();
  return modelSetup;
}
let cameraScale = 1;
function setView() {
  if (!camera) return;
  const positions = {diagonal:[3, 2.3, -4.5], side:[4.5, 1.7, 0], front:[0, 1.7, -5], back:[0, 1.7, 5]};
  camera.position.fromArray(positions[$('view').value]).multiplyScalar(cameraScale);
  controls.target.set(0, cameraScale, 0); controls.update();
}
function resize() {
  const {width, height} = $('viewport').getBoundingClientRect();
  renderer?.setSize(width, height, false);
  if (camera) {camera.aspect = width / height; camera.updateProjectionMatrix();}
  $('sprite').width = Math.round(width * Math.min(devicePixelRatio, 2));
  $('sprite').height = Math.round(height * Math.min(devicePixelRatio, 2));
}
new ResizeObserver(resize).observe($('viewport'));

function disposeRoot(root) {
  if (!root) return;
  const textures = new Set(), materials = new Set(), geometries = new Set();
  root.traverse(node => {
    if (node.geometry) geometries.add(node.geometry);
    for (const material of [].concat(node.material || [])) {
      materials.add(material);
      for (const value of Object.values(material)) if (value?.isTexture) textures.add(value);
    }
  });
  textures.forEach(t => t.dispose()); materials.forEach(m => m.dispose()); geometries.forEach(g => g.dispose());
  root.removeFromParent();
}
function clearModel() {
  mixer?.stopAllAction(); if (mixer && model) mixer.uncacheRoot(model);
  mixer = null; glbActions = []; disposeRoot(model); model = null;
  nodes = {}; displayedPose = {}; transition = null;
}
function makePivot(skeleton) {
  model = new THREE.Group();
  // 来源库是 Z 向上；一次变换父容器，保留全部关节的原始局部旋转语义。
  model.rotation.x = -Math.PI / 2;
  for (const part of skeleton.parts) nodes[part.id] = new THREE.Group();
  for (const part of skeleton.parts) {
    const node = nodes[part.id], parent = skeleton.parts.find(p => p.id === part.parent);
    node.position.fromArray(part.joint.map((v, i) => v - (parent?.joint[i] || 0)));
    node.userData.rest = node.position.clone();
    (parent ? nodes[parent.id] : model).add(node);
    if (part.shape) {
      const shape = part.shape, color = skeleton.materials[shape.material];
      const material = new THREE.MeshStandardMaterial({color: new THREE.Color().setRGB(...color.slice(0,3)), roughness: 0.8});
      const mesh = new THREE.Mesh(new THREE.BoxGeometry(...shape.size), material);
      mesh.position.fromArray(shape.offset); mesh.castShadow = true; mesh.receiveShadow = true; node.add(mesh);
    }
  }
  scene.add(model); cameraScale = 1; setView();
}
function poseAsTransforms(pose) {
  return Object.fromEntries(Object.entries(pose).map(([id, channels]) => [id, {
    loc: new THREE.Vector3(...channels.loc), scale: new THREE.Vector3(...channels.scale),
    // Blender 的 XYZ 按 X→Y→Z 应用；three.js 的内禀 ZYX 才对应同一复合矩阵。
    rotation: new THREE.Quaternion().setFromEuler(new THREE.Euler(...channels.rot.map(v => THREE.MathUtils.degToRad(v)), 'ZYX'))
  }]));
}
function drawPivot() {
  const target = poseAsTransforms(samplePose(character.skeleton, clip, time));
  const alpha = transition ? smooth(transition.elapsed / transition.duration) : 1;
  for (const [id, value] of Object.entries(target)) {
    const before = transition?.pose[id];
    if (before) {
      value.loc.lerpVectors(before.loc, value.loc.clone(), alpha);
      value.scale.lerpVectors(before.scale, value.scale.clone(), alpha);
      value.rotation.slerpQuaternions(before.rotation, value.rotation.clone(), alpha);
    }
    nodes[id].position.copy(nodes[id].userData.rest).add(value.loc);
    nodes[id].scale.copy(value.scale); nodes[id].quaternion.copy(value.rotation);
  }
  displayedPose = target;
  if (alpha === 1) transition = null;
}
function drawSprite() {
  const canvas = $('sprite'), ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!spriteImage || !clip) return;
  const rect = clip.frames[spriteFrame(clip, time)];
  // 验收倍率只整体放大共用画布，保留各帧相对锚点；不按逐帧 bbox 缩放掩盖漂移。
  const scale = Math.min(canvas.width / rect.w * 0.6, canvas.height / rect.h * 0.76) * (Number($('spriteZoom').value) || 1);
  const w = rect.w * scale, h = rect.h * scale, base = canvas.height * 0.87;
  ctx.strokeStyle = '#87b6aa'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(canvas.width * 0.15, base); ctx.lineTo(canvas.width * 0.85, base); ctx.stroke();
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(spriteImage, rect.x, rect.y, rect.w, rect.h, canvas.width / 2 - w * character.anchor[0], base - h * character.anchor[1] + samplePreviewRoot(clip, time) * scale, w, h);
}
function updateButtons() {
  for (const button of $('actions').children) button.classList.toggle('active', button.dataset.id === clip?.id);
}
function setAction(id, preserveTour = false) {
  const next = character.clips.find(c => c.id === id); if (!next) return;
  // 打断时从屏幕上的混合姿态继续，不能从上一动作的原始关键帧重新起跳。
  // 二维直接切真实原画，不执行模型淡入；检查记录也必须反映实际播放方式。
  const seconds = character.kind === 'sprite' ? 0 : Number($('blend').value) / 1000;
  transition = character.kind === 'pivot' && seconds && Object.keys(displayedPose).length ? {pose: displayedPose, elapsed: 0, duration: seconds} : null;
  if (mixer) {
    const action = glbActions[character.clips.indexOf(next)];
    for (const other of glbActions) if (other !== action && other.enabled && other.getEffectiveWeight() > 0) {
      const weight = other.getEffectiveWeight(); other.stopFading().setEffectiveWeight(weight);
      if (seconds) other.fadeOut(seconds); else other.stop();
    }
    action.reset().setEffectiveWeight(1).setEffectiveTimeScale(1);
    action.setLoop(next.loop ? THREE.LoopRepeat : THREE.LoopOnce, next.loop ? Infinity : 1);
    action.clampWhenFinished = true;
    action.play(); if (seconds) action.fadeIn(seconds);
  }
  clip = next; time = 0; tourTime = 0;
  $('loop').disabled = character.kind !== 'glb'; $('loop').checked = clip.loop;
  if (!preserveTour) tour = false;
  visits.push({character: character.id, action: id, blendMs: seconds * 1000, at: new Date().toISOString()});
  updateButtons();
}
function showCoverage() {
  const entry = report.characters.find(r => r.id === character.id);
  $('coverage').replaceChildren();
  const title = document.createElement('strong'); title.textContent = `${character.clips.length} 个动作 · ${character.direction || 'model-local'} · 待验收`; $('coverage').append(title);
  const lines = entry ? [entry.missingActions.length ? `缺动作：${entry.missingActions.join(' / ')}` : '配置要求的动作已齐全', entry.missingDirections.length ? `缺方向：${entry.missingDirections.join(' / ')}` : '配置要求的方向已齐全', ...entry.warnings] : ['本地 GLB；检查动画名称、方向和循环设置后再接入游戏'];
  const ul = document.createElement('ul');
  for (const text of lines) {const li = document.createElement('li'); li.textContent = text; ul.append(li);} $('coverage').append(ul);
}
async function selectCharacter(index) {
  const version = ++selectionVersion;
  clearModel(); clip = null; tour = false; time = 0; spriteImage = null;
  $('review').hidden = true;
  $('actions').replaceChildren(); $('status').textContent = '正在读取本地资源…';
  character = data.characters[index];
  $('sprite').style.display = character.kind === 'sprite' ? 'block' : 'none';
  $('model').style.display = character.kind === 'sprite' ? 'none' : 'block';
  $('spriteHelp').hidden = character.kind !== 'sprite';
  $('spriteTools').hidden = character.kind !== 'sprite';
  $('modelTools').open = character.kind !== 'sprite';
  $('loopContainer').hidden = character.kind !== 'glb';
  try {
    if (character.kind !== 'sprite') {
      await ensureModelView();
      if (version !== selectionVersion) return;
    }
    if (character.kind === 'pivot') makePivot(character.skeleton);
    if (character.kind === 'sprite') {
      const image = new Image(); image.src = character.atlasData; await image.decode();
      if (version !== selectionVersion) return; spriteImage = image;
    }
    if (character.kind === 'glb') {
      const gltf = await new GLTFLoader().loadAsync(character.modelData);
      // 异步加载期间用户可能切换角色；旧模型只能清理，不能覆盖新选择。
      if (version !== selectionVersion) {disposeRoot(gltf.scene); return;}
      model = gltf.scene; scene.add(model);
      model.traverse(node => {if (node.isMesh) {node.castShadow = true; node.receiveShadow = true;}});
      const bounds = new THREE.Box3().setFromObject(model), size = bounds.getSize(new THREE.Vector3()), center = bounds.getCenter(new THREE.Vector3());
      if (bounds.isEmpty() || !Number.isFinite(size.length()) || size.length() === 0) throw new Error('模型没有可见几何');
      model.position.x -= center.x; model.position.z -= center.z; model.position.y -= bounds.min.y;
      cameraScale = Math.max(size.x, size.y, size.z) / 2; setView();
      mixer = new THREE.AnimationMixer(model);
      glbActions = gltf.animations.map(c => mixer.clipAction(c));
      character.clips = gltf.animations.map((c, i) => ({id: c.name || `animation_${i}`, duration: c.duration, loop: character.clips[i]?.loop ?? false}));
      if (character.clips.some(c => !Number.isFinite(c.duration) || c.duration <= 0)) throw new Error('模型包含零时长或无效动作，请修正后重新导出');
    }
    for (const c of character.clips) {
      const button = document.createElement('button'); button.textContent = c.id; button.dataset.id = c.id;
      button.onclick = () => setAction(c.id); $('actions').append(button);
    }
    const initial = character.clips.find(c => c.id === character.defaultAction) || character.clips[0];
    if (initial) setAction(initial.id);
    showCoverage(); $('status').textContent = initial ? '' : '模型没有动画：需要先绑定并制作动作，再导出 GLB。';
  } catch (error) {if (version === selectionVersion) {clearModel(); $('status').textContent = `读取失败：${error.message}`;}}
}
function seek(t) {
  time = t; transition = null;
  if (mixer && clip) {
    const active = glbActions[character.clips.indexOf(clip)];
    glbActions.forEach(a => {if (a !== active) a.stop();});
    active.stopFading().setEffectiveWeight(1); active.enabled = true; active.paused = false; active.time = t; mixer.update(0);
  }
}
$('character').onchange = () => selectCharacter(Number($('character').value));
$('view').onchange = setView;
$('loop').onchange = () => {if (character.kind === 'glb' && clip) {clip.loop = $('loop').checked; setAction(clip.id);}};
$('blend').oninput = () => {$('blendValue').textContent = `${$('blend').value}ms`;};
function pause(value) {playing = value; $('pause').textContent = playing ? '暂停' : '播放'; last = performance.now();}
$('pause').onclick = () => pause(!playing);
$('restart').onclick = () => {if (clip) {setAction(clip.id); pause(true);}};
$('timeline').oninput = () => {if (clip) {pause(false); tour = false; seek(Number($('timeline').value) / 1000 * clip.duration);}};
$('step').onclick = () => {
  if (!clip) return; pause(false); tour = false;
  const next = character.kind === 'sprite' ?
    (clip.loop ? Math.floor(time / clip.duration) * clip.duration : 0) + clip.frames.slice(0, spriteFrame(clip, time) + 1).reduce((sum, f) => sum + f.durationMs, 0) / 1000 :
    time + 1 / (clip.fps || 30);
  seek(clip.loop ? next % clip.duration : Math.min(next, clip.duration));
};
$('sequence').onclick = () => {if (character.clips.length) {setAction(character.clips[0].id, true); tour = true; pause(true);}};
document.addEventListener('visibilitychange', () => {if (document.hidden) pause(false);});
let reviewUrl;
$('download').onclick = () => {
  const record = {status:'previewed-only', character:character.id, spritePreviewZoom:character.kind === 'sprite' ? Number($('spriteZoom').value) : null, clips:character.clips.map(c => ({name:c.id, duration:c.duration, loop:c.loop, previewMotion:c.previewMotion ?? null})), visitedActions:visits, manualChecks:['左右腿交替承重','脚底与武器轨迹','循环接缝','过渡与收招','目标游戏时间窗口'], runtimeEvidence:null};
  const text = JSON.stringify(record, null, 2);
  if (reviewUrl) URL.revokeObjectURL(reviewUrl);
  reviewUrl = URL.createObjectURL(new Blob([text], {type:'application/json'}));
  // 部分内嵌浏览器拦截脚本下载；提供真实可点击链接和可复制记录，不依赖瞬时撤销 URL。
  $('review').hidden = false; $('reviewData').value = text; $('saveReview').href = reviewUrl;
  $('status').textContent = '检查记录已生成，可保存 JSON 或复制下方内容。';
};
$('importButton').onclick = () => $('import').click();
$('import').onchange = async () => {
  const file = $('import').files[0]; if (!file) return;
  try {
    if (file.size > 64 * 1024 * 1024) throw new Error('首版限制为 64MiB 自包含 GLB');
    const buffer = await file.arrayBuffer(), header = new DataView(buffer);
    if (buffer.byteLength < 20 || header.getUint32(0, true) !== 0x46546c67 || header.getUint32(4, true) !== 2 || header.getUint32(8, true) !== buffer.byteLength || header.getUint32(16, true) !== 0x4e4f534a || 20 + header.getUint32(12, true) > buffer.byteLength) throw new Error('无效 GLB 2.0');
    const info = JSON.parse(new TextDecoder().decode(new Uint8Array(buffer, 20, header.getUint32(12, true))));
    if (['images','buffers'].some(group => info[group]?.some(item => 'uri' in item))) throw new Error('请将纹理和几何嵌入一个 GLB，不能引用外部 URI');
    // 转成内嵌数据保留在当前会话；撤销临时 blob URL 会让切回该角色时加载失败。
    const url = await new Promise((resolve, reject) => {const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = reject; reader.readAsDataURL(file);});
    {
      const index = data.characters.length;
      data.characters.push({id:`local-${index}`, title:file.name, kind:'glb', clips:[], modelData:url});
      const option = document.createElement('option'); option.value = index; option.textContent = file.name; $('modelGroup').append(option); $('character').value = index;
      await selectCharacter(index);
    }
  } catch (error) {$('status').textContent = error.message;}
  $('import').value = '';
};
try {
  [data, report] = await Promise.all(['manifest.json','report.json'].map(async path => {const response = await fetch(path); if (!response.ok) throw new Error(`${path}: ${response.status}`); return response.json();}));
  $('title').textContent = data.title;
  data.characters.forEach((c, i) => {const option = document.createElement('option'); option.value = i; option.textContent = c.title; $(c.kind === 'sprite' ? 'spriteGroup' : 'modelGroup').append(option);});
  const first = initialCharacter(data.characters, data.defaultCharacter);
  $('character').value = first;
  await selectCharacter(first);
} catch (error) {$('status').textContent = `初始化失败：${error.message}。请按 START.txt 从本地 HTTP 服务打开。`;}

function renderFrame(now) {
  requestAnimationFrame(renderFrame);
  const elapsed = Math.min(0.1, (now - last) / 1000); last = now;
  const dt = playing ? elapsed * Number($('speed').value) : 0;
  if (clip) {
    time += dt; tourTime += dt;
    if (transition) transition.elapsed += dt;
    mixer?.update(dt);
    for (const action of glbActions) if (action !== glbActions[character.clips.indexOf(clip)] && action.getEffectiveWeight() === 0) action.stop();
    if (tour && tourTime >= clip.duration * (clip.loop ? 2 : 1) + (character.kind === 'sprite' ? 0 : Number($('blend').value)/1000)) {
      const next = character.clips[(character.clips.indexOf(clip) + 1) % character.clips.length]; setAction(next.id, true);
    } else if (!tour && playing && !clip.loop && time >= clip.duration && $('returnIdle').checked && clip.id !== 'idle' && character.clips.some(c => c.id === 'idle')) setAction('idle');
    if (character.kind === 'pivot') drawPivot();
    if (character.kind === 'sprite') drawSprite();
    const local = clip.loop ? time % clip.duration : Math.min(time, clip.duration);
    $('timeline').value = clip.duration ? local / clip.duration * 1000 : 0;
    $('badge').textContent = `${character.kind.toUpperCase()} · ${clip.id} · ${clip.loop ? '循环' : '单次'}`;
    $('info').textContent = `${local.toFixed(3)} / ${clip.duration.toFixed(3)} s` + (character.kind === 'sprite' ? ` · 原画 ${spriteFrame(clip,time)+1}/${clip.frames.length}` : ` · ${character.kind === 'pivot' ? character.skeleton.parts.length + ' 个部件' : 'GLB 原始动作'}`) + (clip.previewMotion ? ` · 预览高度 ${(-samplePreviewRoot(clip,time)).toFixed(1)} px` : '') + (tour ? ' · 巡演中' : '');
  }
  controls?.update(); if (renderer && character?.kind !== 'sprite') renderer.render(scene, camera);
}
requestAnimationFrame(renderFrame);
