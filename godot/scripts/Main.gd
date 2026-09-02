extends Node3D

## Main — Chetona3D-এর entry point। একই WebSocket protocol ব্যবহার করে
## যা Android app-ও ব্যবহার করে (server/main.py দেখো) — সভ্যতার "মস্তিষ্ক"
## (agent/faction/objective logic) পুরোপুরি Python সার্ভারে থেকে যায়;
## এই client শুধু সেটা 3D-তে দেখায়।

var socket := WebSocketPeer.new()
var connected: bool = false
var citizen_scene: PackedScene = preload("res://scenes/Citizen.tscn")
var citizens: Dictionary = {}       # agent_id -> Citizen node
var target_positions: Dictionary = {}  # agent_id -> Vector3
var faction_colors: Dictionary = {}

const PALETTE: Array[Color] = [
	Color(0.878, 0.478, 0.373), # ember orange
	Color(0.506, 0.698, 0.604), # loom teal
	Color(0.949, 0.800, 0.561), # gold
	Color(0.239, 0.353, 0.502), # steel blue
	Color(0.608, 0.365, 0.898), # violet
	Color(0.945, 0.357, 0.710), # pink
]

@onready var citizens_root: Node3D = $Citizens
@onready var url_input: LineEdit = $UI/Panel/VBox/UrlInput
@onready var status_label: Label = $UI/Panel/VBox/StatusLabel
@onready var objective_label: Label = $UI/Panel/VBox/ObjectiveLabel
@onready var connect_button: Button = $UI/Panel/VBox/ConnectButton


func _ready() -> void:
	connect_button.pressed.connect(_on_connect_pressed)


func _on_connect_pressed() -> void:
	var url := url_input.text.strip_edges()
	if url.is_empty():
		return
	status_label.text = "connecting..."
	var err := socket.connect_to_url(url)
	if err != OK:
		status_label.text = "connect failed (%s)" % err


func _process(delta: float) -> void:
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

	# glide every citizen toward its latest known position
	for id in citizens.keys():
		if target_positions.has(id):
			citizens[id].move_to(target_positions[id], delta)


func _handle_message(raw: String) -> void:
	var json := JSON.new()
	if json.parse(raw) != OK:
		return
	var msg = json.get_data()
	if typeof(msg) != TYPE_DICTIONARY:
		return

	match msg.get("type", ""):
		"snapshot":
			_render_snapshot(msg.get("data", {}))
		"error":
			status_label.text = "error: %s" % msg.get("error", "")


func _render_snapshot(data: Dictionary) -> void:
	var factions: Array = data.get("factions", [])
	faction_colors.clear()
	for i in range(factions.size()):
		var f: Dictionary = factions[i]
		faction_colors[f["id"]] = PALETTE[i % PALETTE.size()]

	var agents: Array = data.get("agents", [])
	var count: int = agents.size()
	var radius: float = 6.0 + count * 0.35

	for i in range(count):
		var agent: Dictionary = agents[i]
		var id: String = agent["id"]

		var citizen: Citizen
		if citizens.has(id):
			citizen = citizens[id]
		else:
			citizen = citizen_scene.instantiate()
			citizens_root.add_child(citizen)
			citizens[id] = citizen
			# spawn fresh citizens at their target immediately, no glide-in from origin
			var angle_now: float = (float(i) / float(max(count, 1))) * TAU
			citizen.position = Vector3(cos(angle_now) * radius, 0.0, sin(angle_now) * radius)

		var angle: float = (float(i) / float(max(count, 1))) * TAU
		target_positions[id] = Vector3(cos(angle) * radius, 0.0, sin(angle) * radius)

		var faction_id = agent.get("faction_id")
		var color: Color = faction_colors.get(faction_id, Color(0.4, 0.4, 0.48))
		var alive: bool = agent.get("alive", true)
		citizen.setup(id, agent.get("name", "?"), color, alive, str(faction_id))

	var objective: Dictionary = data.get("objective", {})
	if not objective.is_empty():
		objective_label.text = "Stage %s: %s\n%s" % [
			objective.get("stage", "?"),
			objective.get("stage_name", ""),
			objective.get("description", ""),
		]
