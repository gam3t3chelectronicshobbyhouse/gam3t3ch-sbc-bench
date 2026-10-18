extends Node3D
## Fixed, optional 3D showcase. This never contributes to baseline scores.

const WORKLOAD_ID = "reactor-showcase-0.3"
const SCENE_SECONDS = 10.0
const SCENE_NAMES = ["REACTOR / geometry", "ORBITAL / moving objects", "FLUX / particles"]
var output_path := ""
var smoke_test := false
var elapsed := 0.0
var scene_elapsed := 0.0
var warmup := 0.0
var stage := 0
var frames: Array[float] = []
var results: Array[Dictionary] = []
var rotor: Node3D
var orbital: Node3D
var particles: MultiMeshInstance3D
var camera: Camera3D
var title: Label
var detail: Label
var finished := false
var fullscreen_requested := false
var tick := 0
var hud_elapsed := 0.0

func material(color: Color, emissive := false) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.35
	mat.metallic = 0.55 if not emissive else 0.0
	if emissive:
		mat.emission_enabled = true
		mat.emission = color
		mat.emission_energy_multiplier = 2.0
	return mat

func piece(mesh: Mesh, mat: Material, position_value: Vector3, parent: Node3D = null) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.mesh = mesh
	instance.material_override = mat
	instance.position = position_value
	(parent if parent != null else self).add_child(instance)
	return instance

func box(size_value: Vector3) -> BoxMesh:
	var mesh := BoxMesh.new()
	mesh.size = size_value
	return mesh

func ring(radius: float, thickness: float, mat: Material, parent: Node3D, y: float) -> MeshInstance3D:
	var mesh := TorusMesh.new()
	mesh.inner_radius = radius - thickness
	mesh.outer_radius = radius + thickness
	mesh.rings = 48
	mesh.ring_segments = 12
	return piece(mesh, mat, Vector3(0, y, 0), parent)

func brand_sign(angle: float, mat: Material, backing: Material) -> void:
	var sign_root := Node3D.new()
	sign_root.position = Vector3(sin(angle) * 8.3, 1.8, cos(angle) * 8.3)
	sign_root.rotation.y = angle
	add_child(sign_root)
	piece(box(Vector3(5.6, 1.5, 0.18)), backing, Vector3.ZERO, sign_root)
	piece(box(Vector3(5.3, 0.025, 0.02)), mat, Vector3(0, 0.62, 0.12), sign_root)
	piece(box(Vector3(5.3, 0.025, 0.02)), mat, Vector3(0, -0.62, 0.12), sign_root)
	var wordmark := TextMesh.new()
	wordmark.text = "GAM3T3CH"
	wordmark.font_size = 80
	wordmark.pixel_size = 0.009
	wordmark.depth = 0.025
	piece(wordmark, mat, Vector3(0, 0.06, 0.13), sign_root)
	var subtitle := TextMesh.new()
	subtitle.text = "3D BENCHMARK"
	subtitle.font_size = 40
	subtitle.pixel_size = 0.004
	subtitle.depth = 0.01
	piece(subtitle, mat, Vector3(0, -0.4, 0.13), sign_root)

func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	for i in range(args.size()):
		if args[i] == "--output" and i + 1 < args.size():
			output_path = args[i + 1]
		if args[i] == "--smoke-test":
			smoke_test = true
		if args[i] == "--presentation-fullscreen":
			fullscreen_requested = true
	if output_path.is_empty():
		push_error("Showcase requires --output PATH")
		get_tree().quit(2)
		return
	if DisplayServer.get_name() == "headless" and not smoke_test:
		finish("unavailable", "A graphical display is required.")
		return
	get_tree().auto_accept_quit = false
	# Fullscreen presentation must not scale the measured 3D workload.
	get_window().content_scale_size = Vector2i(1280, 720)
	get_window().content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	get_window().content_scale_aspect = Window.CONTENT_SCALE_ASPECT_KEEP
	if DisplayServer.get_name() != "headless":
		get_window().always_on_top = true
		var icon := Image.new()
		if icon.load_svg_from_string(FileAccess.get_file_as_string("res://brand/g3-mark.svg")) == OK:
			DisplayServer.set_icon(icon)
	Engine.max_fps = 0
	var environment := WorldEnvironment.new()
	var settings := Environment.new()
	settings.background_mode = Environment.BG_COLOR
	settings.background_color = Color("09111c")
	settings.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	settings.ambient_light_color = Color("7195b5")
	settings.ambient_light_energy = 0.55
	environment.environment = settings
	add_child(environment)
	var key := DirectionalLight3D.new()
	key.rotation_degrees = Vector3(-50, -30, 0)
	key.light_energy = 1.7
	add_child(key)
	var metal := material(Color("26394e"))
	var dark := material(Color("142132"))
	var mint := material(Color("51f4cb"), true)
	var amber := material(Color("ff9b48"), true)
	var violet := material(Color("9b78ff"), true)
	var brand_ink := StandardMaterial3D.new()
	brand_ink.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	brand_ink.albedo_color = Color("6cf1c8")
	for i in range(4):
		brand_sign(i * TAU / 4.0, brand_ink, dark)
	piece(box(Vector3(60, 0.2, 60)), dark, Vector3(0, -0.3, 0))
	for i in range(-15, 16):
		piece(box(Vector3(0.018, 0.012, 60)), metal, Vector3(i * 2, -0.18, 0))
		piece(box(Vector3(60, 0.012, 0.018)), metal, Vector3(0, -0.18, i * 2))
	var base := CylinderMesh.new()
	base.top_radius = 4.8
	base.bottom_radius = 5.2
	base.height = 0.65
	base.radial_segments = 64
	piece(base, metal, Vector3(0, 0.1, 0))
	ring(4.6, 0.05, mint, self, 0.47)
	ring(5.3, 0.025, amber, self, -0.1)
	rotor = Node3D.new()
	rotor.position.y = 2.6
	add_child(rotor)
	var core := SphereMesh.new()
	core.radius = 0.85
	core.height = 1.7
	piece(core, mint, Vector3.ZERO, rotor)
	for i in range(4):
		var arc := ring(1.5 + i * 0.35, 0.065, mint if i % 2 == 0 else amber, rotor, 0)
		arc.rotation_degrees = Vector3(30 + i * 35, i * 40, i * 22)
	for i in range(12):
		var angle := i * TAU / 12.0
		var location := Vector3(cos(angle) * 6.3, 1.4, sin(angle) * 6.3)
		var pillar := piece(box(Vector3(0.8, 3.2, 0.8)), metal, location)
		pillar.rotation.y = -angle
		var strip := piece(box(Vector3(0.13, 2.5, 0.85)), amber if i % 3 == 0 else mint, Vector3.ZERO, pillar)
		strip.position.z = 0.03
		piece(box(Vector3(0.9, 0.1, 0.9)), violet, location + Vector3(0, 1.65, 0))
	for i in range(4):
		var lamp := OmniLight3D.new()
		lamp.position = Vector3(cos(i * TAU / 4) * 3, 3, sin(i * TAU / 4) * 3)
		lamp.light_color = Color("50edce") if i % 2 == 0 else Color("ff9b48")
		lamp.light_energy = 2.2
		lamp.omni_range = 12
		add_child(lamp)
	orbital = Node3D.new()
	add_child(orbital)
	var satellite := box(Vector3(0.22, 0.22, 0.65))
	for i in range(192):
		var angle := i * 2.399963
		var radius := 7.7 + (i % 4) * 0.65
		var item := piece(satellite, mint if i % 2 == 0 else violet, Vector3(cos(angle) * radius, 1.0 + (i % 9) * 0.4, sin(angle) * radius), orbital)
		item.rotation = Vector3(angle, angle * 0.7, 0)
	orbital.visible = false
	particles = MultiMeshInstance3D.new()
	var multi := MultiMesh.new()
	multi.transform_format = MultiMesh.TRANSFORM_3D
	multi.mesh = box(Vector3(0.045, 0.045, 0.16))
	multi.instance_count = 1536
	for i in range(1536):
		var angle := i * 2.399963
		var radius := 2.8 + (i % 71) / 12.0
		multi.set_instance_transform(i, Transform3D(Basis.IDENTITY, Vector3(cos(angle) * radius, (i % 79) / 13.0, sin(angle) * radius)))
	particles.multimesh = multi
	particles.material_override = amber
	particles.visible = false
	add_child(particles)
	camera = Camera3D.new()
	camera.position = Vector3(13, 8, 15)
	camera.fov = 58
	add_child(camera)
	camera.look_at(Vector3(0, 2, 0))
	var layer := CanvasLayer.new()
	add_child(layer)
	var panel := ColorRect.new()
	panel.color = Color(0.025, 0.04, 0.065, 0.9)
	panel.position = Vector2(24, 24)
	panel.size = Vector2(640, 150)
	layer.add_child(panel)
	var accent := ColorRect.new()
	accent.color = Color("6cf1c8")
	accent.position = Vector2(24, 24)
	accent.size = Vector2(4, 150)
	layer.add_child(accent)
	var badge := Label.new()
	badge.text = "G3"
	badge.position = Vector2(42, 32)
	badge.add_theme_font_size_override("font_size", 42)
	badge.modulate = Color("ffad68")
	layer.add_child(badge)
	title = Label.new()
	title.position = Vector2(117, 31)
	title.add_theme_font_size_override("font_size", 34)
	title.modulate = Color("62efd0")
	layer.add_child(title)
	var product := Label.new()
	product.text = "3D BENCHMARK / REACTOR LAB"
	product.position = Vector2(119, 77)
	product.add_theme_font_size_override("font_size", 14)
	layer.add_child(product)
	detail = Label.new()
	detail.position = Vector2(42, 112)
	detail.add_theme_font_size_override("font_size", 15)
	layer.add_child(detail)
	var signature := Label.new()
	signature.text = "GAM3T3CH PERFORMANCE LAB  /  " + WORKLOAD_ID + "  /  FIXED WORKLOAD"
	signature.position = Vector2(26, 684)
	signature.add_theme_font_size_override("font_size", 12)
	signature.modulate = Color("91b1ad")
	layer.add_child(signature)
	set_physics_process(false)
	warmup = 2.0
	update_overlay()
	if DisplayServer.get_name() != "headless":
		if fullscreen_requested:
			get_window().mode = Window.MODE_FULLSCREEN
		get_window().grab_focus()

func update_overlay() -> void:
	title.text = "GAM3T3CH"
	var fps := Engine.get_frames_per_second()
	detail.text = "%s  |  %.1f s  |  %d FPS  |  ESC to stop\nOptional showcase · excluded from baseline scores" % ["WARMUP" if warmup > 0 else SCENE_NAMES[stage], scene_elapsed, fps]

func _process(delta: float) -> void:
	if finished or not is_instance_valid(camera):
		return
	tick += 1
	elapsed += delta
	hud_elapsed += delta
	rotor.rotation = Vector3(elapsed * 0.13, elapsed * 0.32, elapsed * 0.09)
	orbital.rotation.y = elapsed * 0.18
	particles.rotation.y = elapsed * -0.12
	camera.position = Vector3(sin(elapsed * 0.12 + 0.7) * 17, 7.3 + sin(elapsed * 0.19) * 1.5, cos(elapsed * 0.12 + 0.7) * 17)
	camera.look_at(Vector3(0, 2, 0))
	if smoke_test:
		if tick >= 4:
			finish("smoke_validated", "Scene initialized headlessly; no graphics performance claim.")
		return
	if warmup > 0:
		warmup -= delta
		return
	scene_elapsed += delta
	frames.append(delta)
	if hud_elapsed >= 0.5:
		update_overlay()
		hud_elapsed = 0
	if scene_elapsed >= SCENE_SECONDS:
		var ordered := frames.duplicate()
		ordered.sort()
		var slow_count := maxi(1, ceili(ordered.size() * 0.01))
		var slow_time := 0.0
		for i in range(ordered.size() - slow_count, ordered.size()):
			slow_time += ordered[i]
		results.append({"name": SCENE_NAMES[stage], "frames": frames.size(), "seconds": scene_elapsed, "average_fps": frames.size() / scene_elapsed, "one_percent_low_fps": slow_count / slow_time})
		stage += 1
		if stage >= SCENE_NAMES.size():
			finish("passed", "Three fixed showcase scenes completed.")
			return
		frames.clear()
		scene_elapsed = 0
		orbital.visible = stage >= 1
		particles.visible = stage >= 2
		warmup = 2.0
		update_overlay()

func finish(status: String, reason: String) -> void:
	if finished:
		return
	finished = true
	set_process(false)
	if status == "passed" and fullscreen_requested and get_window().mode not in [Window.MODE_FULLSCREEN, Window.MODE_EXCLUSIVE_FULLSCREEN]:
		status = "unavailable"
		reason = "Fullscreen presentation was requested but the window manager did not retain it. Retry --windowed for a labelled windowed run."
	var size_value := get_viewport().get_visible_rect().size
	var result := {"workload_id": WORKLOAD_ID, "status": status, "reason": reason, "scored": false, "smoke_test": smoke_test, "engine_version": Engine.get_version_info().string, "renderer": RenderingServer.get_video_adapter_name(), "rendering_method": RenderingServer.get_current_rendering_method(), "rendering_driver": RenderingServer.get_current_rendering_driver_name(), "api_version": RenderingServer.get_video_adapter_api_version(), "display_server": DisplayServer.get_name(), "width": size_value.x, "height": size_value.y, "msaa_3d": get_viewport().msaa_3d, "warmup_seconds_per_scene": 2, "scene_seconds": SCENE_SECONDS, "scenes": results}
	var file := FileAccess.open(output_path, FileAccess.WRITE)
	result["window_width"] = get_window().size.x
	result["window_height"] = get_window().size.y
	result["window_mode"] = get_window().mode
	result["focus_requested"] = DisplayServer.get_name() != "headless"
	result["fullscreen_requested"] = fullscreen_requested
	if file:
		file.store_string(JSON.stringify(result, "\t"))
		file.close()
	else:
		push_error("Could not write showcase result")
		get_tree().quit(2)
		return
	get_tree().quit(0)

func _input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		finish("interrupted", "Stopped by user.")

func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST:
		finish("interrupted", "Window closed by user.")
