extends Node3D
class_name Citizen

## Citizen — একটা agent-এর 3D representation। Main.gd প্রতিটা snapshot-এ
## setup() কল করে এর রঙ, নাম, আর alive/defected অবস্থা আপডেট করে।

var agent_id: String = ""
var agent_name: String = ""
var faction_id: String = ""

@onready var mesh_instance: MeshInstance3D = $MeshInstance3D
@onready var label: Label3D = $Label3D

func setup(id: String, display_name: String, color: Color, alive: bool, faction: String) -> void:
	agent_id = id
	agent_name = display_name
	faction_id = faction
	label.text = display_name

	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	if not alive:
		mat.albedo_color.a = 0.35
		mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mesh_instance.set_surface_override_material(0, mat)

## smoothly glide to a new position instead of snapping — keeps the world feeling alive
func move_to(target_position: Vector3, delta: float, speed: float = 2.5) -> void:
	position = position.lerp(target_position, clamp(speed * delta, 0.0, 1.0))
