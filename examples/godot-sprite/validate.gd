extends SceneTree

func _initialize() -> void:
	call_deferred("run_validation")

func check(condition: bool, message: String) -> bool:
	if not condition:
		push_error(message)
	return condition

func run_validation() -> void:
	var source: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://source-manifest.json"))
	var frames := load("res://hero_frames.tres") as SpriteFrames
	if not check(frames != null, "SpriteFrames加载失败"):
		quit(1)
		return
	var checks := 0
	for state in source["states"]:
		var name := StringName(state["name"])
		if not check(frames.has_animation(name), "缺动作: %s" % name):
			quit(1); return
		if not check(frames.get_animation_loop(name) == state["loop"], "循环不符"):
			quit(1); return
		if not check(frames.get_frame_count(name) == state["frames"].size(), "帧数不符"):
			quit(1); return
		checks += 3
		for i in range(state["frames"].size()):
			var expected: Dictionary = state["frames"][i]
			var ms := frames.get_frame_duration(name,i) / frames.get_animation_speed(name) * 1000.0
			var texture := frames.get_frame_texture(name,i) as AtlasTexture
			if not check(abs(ms-float(expected["durationMs"])) < 0.0001, "实际时长不符"):
				quit(1); return
			if not check(texture != null and texture.region == Rect2(expected["x"],expected["y"],expected["w"],expected["h"]), "图集区域不符"):
				quit(1); return
			checks += 2
	# 实例化真实节点并跑一次单次动作，验证资源不止能反序列化。
	var sprite := AnimatedSprite2D.new()
	sprite.sprite_frames = frames
	root.add_child(sprite)
	if frames.has_animation("attack"):
		var completed := {"done": false}
		sprite.animation_finished.connect(func(): completed["done"] = true)
		sprite.play("attack")
		await create_timer(2.0).timeout
		if not check(completed["done"] and not sprite.is_playing(), "单次攻击未结束"):
			quit(1); return
		checks += 1
	var preview := load("res://preview.tscn") as PackedScene
	if not check(preview != null, "预览场景加载失败"):
		quit(1); return
	var node := preview.instantiate()
	root.add_child(node)
	await process_frame
	var actor := node.get_node("Hero") as AnimatedSprite2D
	var metadata: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://export.json"))
	if not check(actor.offset == Vector2(metadata["spriteOffset"][0],metadata["spriteOffset"][1]), "脚底偏移不符"):
		quit(1); return
	checks += 2
	# 可选搬目录检查，测试者复制资源到relocated后重新import即可，正常包不强制额外副本。
	if ResourceLoader.exists("res://relocated/hero_frames.tres"):
		var moved := load("res://relocated/hero_frames.tres") as SpriteFrames
		if not check(moved != null and (moved.get_frame_texture("idle",0) as AtlasTexture).atlas.resource_path == "res://relocated/atlas.png", "子目录图集路径不符"):
			quit(1); return
		checks += 1
	print("GODOT_SPRITE_EXPORT_PASS checks=%d animations=%d" % [checks,frames.get_animation_names().size()])
	quit(0)
