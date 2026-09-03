extends Node3D
class_name Citizen

## Citizen — একটা agent-এর 3D representation। Main.gd প্রতিটা snapshot-এ
## setup() কল করে এর রঙ, নাম, আর alive/defected অবস্থা আপডেট করে।
## StaticBody3D/CollisionShape3D আছে যাতে ক্যামেরা raycast দিয়ে click/tap
## করে target হিসেবে বেছে নেওয়া যায় (দেখো Main.gd-এর _try_select_citizen)।

var agent_id: String = ""
var agent_name: String = ""
var faction_id: String = ""
var base_color: Color = Color.WHITE

@onready var mesh_instance: MeshInstance3D = $MeshInstance3D
@onready var label: Label3D = $Label3D
@onready var static_body: StaticBody3D = $StaticBody3D


func setup(id: String, display_name: String, color: Color, alive: bool, faction: String) -> void:
	agent_id = id
	agent_name = display_name
	faction_id = faction
	base_color = color
	label.text = display_name
	static_body.set_meta("agent_id", id)

	_apply_material(color, alive, false)


func set_selected(selected: bool, alive: bool = true) -> void:
	_apply_material(base_color, alive, selected)


func _apply_material(color: Color, alive: bool, selected: bool) -> void:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	if not alive:
		mat.albedo_color.a = 0.35
		mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	if selected:
		mat.emission_enabled = true
		mat.emission = Color(1, 0.9, 0.6)
		mat.emission_energy_multiplier = 0.8
	mesh_instance.set_surface_override_material(0, mat)


## smoothly glide to a new position instead of snapping — keeps the world feeling alive
func move_to(target_position: Vector3, delta: float, speed: float = 2.5) -> void:
	position = position.lerp(target_position, clamp(speed * delta, 0.0, 1.0))
