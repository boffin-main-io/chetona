extends CharacterBody3D

## Player — গেমারের নিজস্ব avatar। WASD বা arrow key দিয়ে world-এর মধ্যে
## হাঁটাচলা করা যায়, ঠিক অন্য citizen-দের মতোই ground-এ দাঁড়িয়ে।

const SPEED: float = 5.0
const GRAVITY: float = 9.8


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= GRAVITY * delta
	else:
		velocity.y = 0.0

	var input_dir := Vector2.ZERO
	input_dir.x = Input.get_axis("ui_left", "ui_right")
	input_dir.y = Input.get_axis("ui_up", "ui_down")

	# WASD as an explicit fallback alongside the arrow-key default input map
	if Input.is_key_pressed(KEY_A):
		input_dir.x -= 1.0
	if Input.is_key_pressed(KEY_D):
		input_dir.x += 1.0
	if Input.is_key_pressed(KEY_W):
		input_dir.y -= 1.0
	if Input.is_key_pressed(KEY_S):
		input_dir.y += 1.0

	if input_dir.length() > 1.0:
		input_dir = input_dir.normalized()

	var direction := Vector3(input_dir.x, 0.0, input_dir.y)
	velocity.x = direction.x * SPEED
	velocity.z = direction.z * SPEED

	move_and_slide()

	if direction.length_squared() > 0.01:
		look_at(global_position + direction, Vector3.UP)
