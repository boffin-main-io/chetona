extends Node3D

## Main — Chetona3D-এর entry point। server/main.py-এর সাথে একই WebSocket
## protocol ব্যবহার করে (Android app-ও এটাই ব্যবহার করে) — সভ্যতার সব
## logic (agent/faction/objective) সার্ভারেই থাকে।
##
## Phase 2 সংযোজন: player avatar + camera follow, per-faction territory
## zone (cohesion অনুযায়ী transparency), day-night cycle, আর citizen-দের
## click/tap করে target বেছে whisper/incite action পাঠানো।

var socket := WebSocketPeer.new()
var connected: bool = false
var owner_token: String = ""

var citizen_scene: PackedScene = preload("res://scenes/Citizen.tscn")
var citizens: Dictionary = {}          # agent_id -> Citizen node
var target_positions: Dictionary = {}  # agent_id -> Vector3
var spawned_once: Dictionary = {}      # agent_id -> true (avoid re-snapping existing citizens)
var faction_colors: Dictionary = {}
var territory_meshes: Dictionary = {}  # faction_id -> MeshInstance3D

var selected_agent_id: String = ""

const PALETTE: Array[Color] = [
	Color(0.878, 0.478, 0.373), # ember orange
	Color(0.506, 0.698, 0.604), # loom teal
	Color(0.949, 0.800, 0.561), # gold
	Color(0.239, 0.353, 0.502), # steel blue
	Color(0.608, 0.365, 0.898), # violet
	Color(0.945, 0.357, 0.710), # pink
]
const NO_FACTION_COLOR := Color(0.4, 0.4, 0.48)

# ---- day/night ----
var time_of_day: float = 0.32  # 0..1, starts mid-morning
const DAY_LENGTH_SECONDS: float = 180.0
const DAY_SKY := Color(0.09, 0.11, 0.16, 1)
const NIGHT_SKY := Color(0.02, 0.02, 0.05, 1)
const DAY_AMBIENT := Color(0.35, 0.35, 0.4, 1)
const NIGHT_AMBIENT := Color(0.06, 0.06, 0.1, 1)

@onready var citizens_root: Node3D = $Citizens
@onready var territories_root: Node3D = $Territories
@onready var player: CharacterBody3D = $Player
@onready var camera: Camera3D = $Camera3D
@onready var sun: DirectionalLight3D = $DirectionalLight3D
@onready var world_environment: WorldEnvironment = $WorldEnvironment

@onready var url_input: LineEdit = $UI/Panel/VBox/UrlInput
@onready var status_label: Label = $UI/Panel/VBox/StatusLabel
@onready var objective_label: Label = $UI/Panel/VBox/ObjectiveLabel
@onready var connect_button: Button = $UI/Panel/VBox/ConnectButton
@onready var selected_label: Label = $UI/Panel/VBox/SelectedLabel
@onready var rumor_input: LineEdit = $UI/Panel/VBox/RumorInput
@onready var whisper_button: Button = $UI/Panel/VBox/ActionRow/WhisperButton
@onready var incite_button: Button = $UI/Panel/VBox/ActionRow/InciteButton


func _ready() -> void:
	connect_button.pressed.connect(_on_connect_pressed)
	whisper_button.pressed.connect(_on_whisper_pressed)
	incite_button.pressed.connect(_on_incite_pressed)


func _on_connect_pressed() -> void:
	_connect_to(url_input.text.strip_edges())


func _connect_to(url: String) -> void:
	if url.is_empty():
		return
	status_label.text = "connecting..."
	var err := socket.connect_to_url(url)
	if err != OK:
		status_label.text = "connect failed (%s)" % err


func _process(delta: float) -> void:
	_poll_socket()
	_update_day_night(delta)
	_update_camera_follow(delta)

	for id in citizens.keys():
		if target_positions.has(id):
			citizens[id].move_to(target_positions[id], delta)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		_try_select_citizen(event.position)
	elif event is InputEventScreenTouch and event.pressed:
		_try_select_citizen(event.position)


# ---- networking ------------------------------------------------------

func _poll_socket() -> void:
	socket.poll()
	var state := socket.get_ready_state()

	if state == WebSocketPeer.STATE_OPEN:
		if not connected:
			connected = true
			status_label.text = "connected: %s" % url_input.text
		while socket.get_available_packet_count() > 0:
			var packet := socket.get_packet().get_string_from_utf8()
			_handle_message(packet)
	elif state == WebSocketPeer.STATE_CLOSED:
		if connected:
			connected = false
			status_label.text = "disconnected"


func _handle_message(raw: String) -> void:
	var json := JSON.new()
	if json.parse(raw) != OK:
		return
	var msg = json.get_data()
	if typeof(msg) != TYPE_DICTIONARY:
		return

	# first connection to a brand-new world reveals a one-time claim token —
	# save it and reconnect with ?token=... so mutating actions authenticate
	if msg.has("claim_token") and owner_token.is_empty():
		owner_token = str(msg["claim_token"])
		status_label.text = "claimed world — reconnecting with credentials"
		var base_url: String = url_input.text
		if not base_url.contains("token="):
			var sep := "&" if base_url.contains("?") else "?"
			var new_url := base_url + sep + "token=" + owner_token
			url_input.text = new_url
			socket.close()
			call_deferred("_connect_to", new_url)
		return

	match msg.get("type", ""):
		"snapshot":
			_render_snapshot(msg.get("data", {}))
		"action_result":
			_handle_action_result(msg.get("data", {}))
		"error":
			status_label.text = "error: %s" % msg.get("error", "")


func _send_action(payload: Dictionary) -> void:
	if socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
		status_label.text = "not connected"
		return
	socket.send_text(JSON.stringify(payload))


func _handle_action_result(data: Dictionary) -> void:
	if not data.get("ok", true):
		status_label.text = "action failed: %s" % data.get("error", "")
	elif data.get("defected", false):
		status_label.text = "a citizen has defected"


# ---- citizen selection (click/tap to target) --------------------------

func _try_select_citizen(screen_pos: Vector2) -> void:
	var from := camera.project_ray_origin(screen_pos)
	var to := from + camera.project_ray_normal(screen_pos) * 1000.0
	var space_state := get_world_3d().direct_space_state
	var query := PhysicsRayQueryParameters3D.create(from, to)
	var result := space_state.intersect_ray(query)
	if result.is_empty():
		return
	var collider = result.get("collider")
	if collider and collider.has_meta("agent_id"):
		_select_citizen(str(collider.get_meta("agent_id")))


func _select_citizen(id: String) -> void:
	if citizens.has(selected_agent_id):
		citizens[selected_agent_id].set_selected(false)
	selected_agent_id = id
	if citizens.has(id):
		var citizen = citizens[id]
		citizen.set_selected(true)
		selected_label.text = "Target: %s  (%s)" % [citizen.agent_name, id]


func _on_whisper_pressed() -> void:
	if selected_agent_id.is_empty() or rumor_input.text.strip_edges().is_empty():
		return
	_send_action({
		"action": "whisper_rumor",
		"target_id": selected_agent_id,
		"content": rumor_input.text,
		"credibility": 0.6,
	})


func _on_incite_pressed() -> void:
	if selected_agent_id.is_empty():
		return
	_send_action({
		"action": "incite_defection",
		"agent_id": selected_agent_id,
		"credibility": 0.7,
	})


# ---- world rendering ---------------------------------------------------

func _render_snapshot(data: Dictionary) -> void:
	var factions: Array = data.get("factions", [])
	faction_colors.clear()
	var faction_offsets: Dictionary = {}
	faction_offsets[""] = Vector3.ZERO  # the "wilds" — where defected citizens drift

	for i in range(factions.size()):
		var f: Dictionary = factions[i]
		var fid: String = f["id"]
		faction_colors[fid] = PALETTE[i % PALETTE.size()]
		var big_angle: float = (float(i) / float(max(factions.size(), 1))) * TAU
		var center := Vector3(cos(big_angle) * 15.0, 0.0, sin(big_angle) * 15.0)
		faction_offsets[fid] = center
		_update_territory_zone(fid, center, f)

	var agents: Array = data.get("agents", [])
	var by_faction: Dictionary = {}
	for agent in agents:
		var fid: String = str(agent.get("faction_id", ""))
		if fid == "null" or agent.get("faction_id") == null:
			fid = ""
		if not by_faction.has(fid):
			by_faction[fid] = []
		by_faction[fid].append(agent)

	for fid in by_faction.keys():
		var group: Array = by_faction[fid]
		var center: Vector3 = faction_offsets.get(fid, Vector3.ZERO)
		var radius: float = 2.5 + group.size() * 0.5

		for i in range(group.size()):
			var agent: Dictionary = group[i]
			var id: String = agent["id"]

			var citizen = citizens.get(id)
			if citizen == null:
				citizen = citizen_scene.instantiate()
				citizens_root.add_child(citizen)
				citizens[id] = citizen

			var angle: float = (float(i) / float(max(group.size(), 1))) * TAU
			var pos: Vector3 = center + Vector3(cos(angle) * radius, 0.0, sin(angle) * radius)
			target_positions[id] = pos
			if not spawned_once.has(id):
				citizen.position = pos
				spawned_once[id] = true

			var color: Color = faction_colors.get(fid, NO_FACTION_COLOR)
			var alive: bool = agent.get("alive", true)
			citizen.setup(id, agent.get("name", "?"), color, alive, fid)
			if id == selected_agent_id:
				citizen.set_selected(true, alive)

	var objective: Dictionary = data.get("objective", {})
	if not objective.is_empty():
		objective_label.text = "Stage %s: %s\n%s" % [
			objective.get("stage", "?"),
			objective.get("stage_name", ""),
			objective.get("description", ""),
		]


## faction cohesion যত বেশি, territory zone তত বেশি opaque/solid দেখাবে —
## ভাঙনের মুখে থাকা faction-এর এলাকা চোখেই ফিকে হয়ে আসবে।
func _update_territory_zone(fid: String, center: Vector3, faction_data: Dictionary) -> void:
	var mesh_instance: MeshInstance3D
	if territory_meshes.has(fid):
		mesh_instance = territory_meshes[fid]
	else:
		mesh_instance = MeshInstance3D.new()
		var cyl := CylinderMesh.new()
		cyl.top_radius = 1.0
		cyl.bottom_radius = 1.0
		cyl.height = 0.05
		mesh_instance.mesh = cyl
		var mat := StandardMaterial3D.new()
		mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		mesh_instance.material_override = mat
		territories_root.add_child(mesh_instance)
		territory_meshes[fid] = mesh_instance

	var member_count: int = faction_data.get("member_count", 4)
	var cohesion: float = faction_data.get("cohesion", 0.7)
	var radius: float = 3.0 + member_count * 0.6
	mesh_instance.scale = Vector3(radius, 1.0, radius)
	mesh_instance.position = center + Vector3(0, 0.02, 0)

	var mat: StandardMaterial3D = mesh_instance.material_override
	var color: Color = faction_colors.get(fid, NO_FACTION_COLOR)
	color.a = lerp(0.10, 0.32, cohesion)
	mat.albedo_color = color


# ---- day/night + camera -------------------------------------------------

func _update_day_night(delta: float) -> void:
	time_of_day = fmod(time_of_day + delta / DAY_LENGTH_SECONDS, 1.0)
	var sun_angle: float = time_of_day * TAU
	sun.rotation.x = -sun_angle
	var daylight: float = clamp(sin(sun_angle), 0.0, 1.0)
	sun.light_energy = lerp(0.05, 1.1, daylight)

	var env: Environment = world_environment.environment
	if env:
		env.background_color = DAY_SKY.lerp(NIGHT_SKY, 1.0 - daylight)
		env.ambient_light_color = DAY_AMBIENT.lerp(NIGHT_AMBIENT, 1.0 - daylight)


func _update_camera_follow(delta: float) -> void:
	if player == null:
		return
	var target_pos: Vector3 = player.global_position + Vector3(0, 16, 20)
	camera.global_position = camera.global_position.lerp(target_pos, clamp(3.0 * delta, 0.0, 1.0))
	camera.look_at(player.global_position, Vector3.UP)
