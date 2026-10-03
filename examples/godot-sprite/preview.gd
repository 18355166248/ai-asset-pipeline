extends Node2D

@onready var hero: AnimatedSprite2D = $Hero
@onready var info: Label = $Info
var names: PackedStringArray
var selected := 0

func _ready() -> void:
	names = hero.sprite_frames.get_animation_names()
	selected = names.find(hero.animation)
	show_info()

func _unhandled_key_input(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed or event.echo:
		return
	if event.keycode == KEY_SPACE:
		selected = (selected + 1) % names.size()
		hero.play(names[selected])
	elif event.keycode == KEY_R:
		hero.stop()
		hero.play(names[selected])
	elif event.keycode == KEY_LEFT or event.keycode == KEY_RIGHT:
		# 左向只是镜像检查，不能当成生成了新的角色朝向。
		hero.flip_h = event.keycode == KEY_LEFT
	show_info()

func show_info() -> void:
	info.text = "二维动作导入草稿 · %s\n空格切动作 / R重播 / 左右镜像\n仅检查原画，不含游戏物理或战斗" % hero.animation
