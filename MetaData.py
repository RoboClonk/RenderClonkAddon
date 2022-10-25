#--------------------------
# MetaData: Including data structures for action data
# 11.02.2022
#--------------------------
# Robin Hohnsbeen (Ryou)

import bpy
import math

class ActionMetaData(bpy.types.PropertyGroup):
	is_used : bpy.props.BoolProperty(
		name='Enabled', 
		default=True, 
		description="Determines if this action entry is currently in use. Can be useful if you want to keep an entry for later"
	)
	action : bpy.props.PointerProperty(type=bpy.types.Action, name='Action', description="The reference to the action that will be applied on the action target when rendering a spritesheet")
	override_resolution : bpy.props.BoolProperty(
		name='Override resolution', 
		default=False, 
		description="You can render sprites with resolutions other than in the render settings. Keep in mind thought that all resolutions are multiplied by the resolution percentage (100% => 1.0, 200% => 2.0, ...). Use [arrows keys] while in preview to change these values on the fly"
	)
	start_frame : bpy.props.IntProperty(name='Start frame', default=1, soft_min=0, description="The number of the first frame of the action")
	max_frames : bpy.props.IntProperty(name='Max frames', default=16, min=1, soft_max=256, description="The amount of frames that are rendered for this action")
	width : bpy.props.IntProperty(name='Pixel width', default=16, min=1, max=2048, description="The pixel width of one sprite image. (Will be multiplied by the resolution percentage (100% => 1.0, 200% => 2.0, ...)")
	height : bpy.props.IntProperty(name='Pixel height', default=20, min=1, max=2048, description="The pixel height of one sprite image. (Will be multiplied by the resolution percentage (100% => 1.0, 200% => 2.0, ...)")
	use_alternative_name : bpy.props.BoolProperty(
		name='Override name', 
		default=False, 
		description="In case you want to have a separate clonk action that references the same blender action. e.g Sword Fight, Axe Fight. Each can use the same blender action but use different tools."
	)
	alternative_name : bpy.props.StringProperty(name='Name Override', default="", maxlen=25, description="Fill in, if you want this action to have a different name. This is only usefull if two entries share the same action")
	is_rendered : bpy.props.BoolProperty(
		name='Is Rendered To Spritesheet', 
		default=True, 
		description="When this is false, it will reference another action and print it with a different name to the ActMap"
	)
	render_type_enum : bpy.props.EnumProperty(
		items={
			("Spriteanimation", "Spriteanimation", "Render several frames and put them next to each other on the spritesheet.", 0), 
			("Picture", "Picture", "Render one frame and put it where it fits. This is useful for title images.", 1)}, 
		default="Spriteanimation", options={"HIDDEN"}, name=''
		)
	image_for_picture_combined : bpy.props.PointerProperty(type=bpy.types.Image, name='', description="Use an image for the title picture directly and omit rendering. This image will be used for the combined or the graphics sprite sheet")
	image_for_picture_overlay : bpy.props.PointerProperty(type=bpy.types.Image, name='', description="Use an image for the title picture directly and omit rendering. This image will be used for the overlay sprite sheet")
	additional_object_enum : bpy.props.EnumProperty(
		items={("1_Object", "Object", "Render one object", 1), ("2_Collection", "Collection", "Render whole collection", 2)}, 
		default="1_Object", options={"HIDDEN"}, name=''
		)
	additional_object : bpy.props.PointerProperty(type=bpy.types.Object, name='', description="An object that is only visible in this action. This can be used for tools that a clonk is holding for example")
	additional_collection : bpy.props.PointerProperty(type=bpy.types.Collection, name='', description="A collection that holds objects that are only visible in this action. This can be used for tools that a clonk is holding for example")
	find_material_name : bpy.props.StringProperty(name='Find material name', maxlen=32, description="Materials containing that name will be replaced by the replace material")
	replace_material : bpy.props.PointerProperty(type=bpy.types.Material, name='Replace material', description="The material that it will be replaced with")
	region_cropping : bpy.props.FloatVectorProperty(
		name='Region Cropping', 
		default=[0.0, 1.0, 0.0, 1.0], 
		description="This uses the render region to crop the rendered image to a smaller piece. This is useful for animated doors on buildings for example",
		size=4)
	invert_region_cropping : bpy.props.BoolProperty(
		name='Cut out region instead of cropping', 
		default=False, 
		description="Instead of cropping the rendered image, the region itself will be transparent"
	)
	use_normal_action_placement : bpy.props.BoolProperty(
		name='Use default action placement', 
		default=True, 
		description="Determines whether this action is placed on the spritesheet in order of its list index (Default) or placed at the end where it fits (Non default). Uncheck this for title images of objects or Clonks"
	)
	override_camera : bpy.props.PointerProperty(type=bpy.types.Object, name='', description="The camera that will be used during this action instead of the default one. Can be left empty")
	override_facet_offset : bpy.props.BoolProperty(
		name='Override facet offset', 
		default=False, 
		description="Overrides the facet offset inside ActMap.txt. Has no effect on rendering the action, so you can simply hit export/update ActMap.txt"
	)
	facet_offset_x : bpy.props.IntProperty(name='Facet offset x', default=0, description="X direction offset in which the facet will be moved inside the game")
	facet_offset_y : bpy.props.IntProperty(name='Facet offset y', default=0, description="Y direction offset in which the facet will be moved inside the game")
	override_camera_shift : bpy.props.BoolProperty(name='Override camera shift', description="Change the camera shift for this action. Use [shift + arrow keys] while in preview to change these values on the fly. You need to rerender the sprite sheet and update the ActMap to see an effect in the game")
	camera_shift_x : bpy.props.IntProperty(name='Camera shift x', default=0, description="X direction shift of the camera (in pixels)")
	camera_shift_y : bpy.props.IntProperty(name='Camera shift y', default=0, description="Y direction shift of the camera (in pixels)")
	camera_shift_changes_facet_offset : bpy.props.BoolProperty(name='Camera shift changes facet offset', default=True, description="The facet offset will automatically be changed to keep the sprite at its original position in the game")

class SpriteSheetMetaData(bpy.types.PropertyGroup):
	overlay_rendering_enum : bpy.props.EnumProperty(
		items={
			("Separate", "Separate", "Graphics and Overlay rendered separately. Materials with \"Overlay\" in their name will be replaced with the overlay material", 0), 
			("Combined", "Combined", "Graphics and Overlay in one image. (Materials with \"Overlay\" in their name will be replaced with a blue fill material)", 1)}, 
		default="Separate", options={"HIDDEN"}, name='Overlay Render Setting'
		)
	overlay_material : bpy.props.PointerProperty(type=bpy.types.Material, name='Overlay Material', description="Materials with \"Overlay\" in its name will be replaced with this material upon render")
	fill_material : bpy.props.PointerProperty(type=bpy.types.Material, name='Fill Material', description="Materials with \"Overlay\" in its name will be replaced with this material upon render")
	add_suffix_for_combined : bpy.props.BoolProperty(name='Add suffix \"_Combined\"', default=True, description="This will add \"_Combined\" at the end of the sprite sheet file name. Useful for testing because it prevents to override the Graphics.png")
	spritesheet_suffix : bpy.props.StringProperty(name='Spritesheet name suffix', maxlen=32, description="A text that will be added at the end of the output file")
	render_direction : bpy.props.EnumProperty(
		items={
			("Horizontal", "Horizontal", "Sprites in one animation will be placed horizontally", 0), 
			("Vertical", "Vertical", "Sprites in one animation will be placed vertically", 1)}, 
		default="Horizontal", options={"HIDDEN"}, name='Sprite packing'
		)

def MakeRectCutoutPixelPerfect(action_entry : ActionMetaData):
	scene = bpy.context.scene

	render_width = action_entry.width if action_entry.override_resolution else scene.render.resolution_x
	render_height = action_entry.height if action_entry.override_resolution else scene.render.resolution_y

	pixel_ratio_x = 1.0 / render_width
	pixel_ratio_y = 1.0 / render_height
	action_entry.region_cropping[0] = math.floor(action_entry.region_cropping[0] / pixel_ratio_x) * pixel_ratio_x
	action_entry.region_cropping[1] = math.floor(action_entry.region_cropping[1] / pixel_ratio_x) * pixel_ratio_x
	action_entry.region_cropping[2] = math.floor(action_entry.region_cropping[2] / pixel_ratio_y) * pixel_ratio_y
	action_entry.region_cropping[3] = math.floor(action_entry.region_cropping[3] / pixel_ratio_y) * pixel_ratio_y

	return action_entry

def get_automatic_face_offset(scene, anim_entry, do_round=True):
	x_offset = -(anim_entry.width - scene.render.resolution_x) / 2.0
	y_offset = -(anim_entry.height - scene.render.resolution_y) / 2.0

	if do_round:
		return round(x_offset), round(y_offset)
	else:
		return round(x_offset, 2), round(y_offset, 2)


def get_res_multiplier():
	return bpy.context.scene.render.resolution_percentage / 100.0

def GetPixelFromCutout(action_entry : ActionMetaData, scaled=False):
	scene = bpy.context.scene

	render_width = action_entry.width if action_entry.override_resolution else scene.render.resolution_x
	render_height = action_entry.height if action_entry.override_resolution else scene.render.resolution_y

	res_multiplier = get_res_multiplier() if scaled else 1.0

	# Rounding the solution should mitigate the risk of losing a pixel
	pixel_ratio_x = 1.0 / render_width
	x_pixel_min = round(action_entry.region_cropping[0] / pixel_ratio_x * res_multiplier)
	x_pixel_max = round(action_entry.region_cropping[1] / pixel_ratio_x * res_multiplier)

	pixel_ratio_y = 1.0 / render_height
	y_pixel_min = round(action_entry.region_cropping[2] / pixel_ratio_y * res_multiplier)
	y_pixel_max = round(action_entry.region_cropping[3] / pixel_ratio_y * res_multiplier)

	width = x_pixel_max - x_pixel_min
	height = y_pixel_max - y_pixel_min

	min_max_pixels = [x_pixel_min, x_pixel_max, y_pixel_min, y_pixel_max]
	pixel_dimensions = [width, height]

	return min_max_pixels, pixel_dimensions

def SetRenderBorder(action_entry):
	scene = bpy.context.scene
	scene.render.border_min_x = action_entry.region_cropping[0]
	scene.render.border_max_x = action_entry.region_cropping[1]
	scene.render.border_min_y = action_entry.region_cropping[2]
	scene.render.border_max_y = action_entry.region_cropping[3]

def UnsetRenderBorder():
	scene = bpy.context.scene
	scene.render.border_min_x = 0.0
	scene.render.border_max_x = 1.0
	scene.render.border_min_y = 0.0
	scene.render.border_max_y = 1.0

def is_using_cutout(action_entry):
	return action_entry.region_cropping[0] != 0.0 or action_entry.region_cropping[1] != 1.0 or action_entry.region_cropping[2] != 0.0 or action_entry.region_cropping[3] != 1.0

def GetActionNameFromIndex(list_index):
	if len(bpy.context.scene.animlist) == 0 or bpy.context.scene.animlist[list_index].action is None:
		return ""
	
	else:
		return GetActionName(bpy.context.scene.animlist[list_index])

def GetActionName(action_entry : ActionMetaData):
	name = action_entry.action.name
	if action_entry.use_alternative_name and len(action_entry.alternative_name) > 0:
		name = action_entry.alternative_name

	return name

def CheckIfActionListIsValid(action_entries):
	action_entry_names = set()
	for entry in action_entries:
		if GetActionName(entry) not in action_entry_names:
			action_entry_names.add(GetActionName(entry))
		else:
			return "ERROR", "Can't have two actions with the same name: %s. Use \"override name\" in one of each action." % (GetActionName(entry))

	return "INFO", "All entries are valid."

def GetValidActionEntries():
	valid_action_entries = []
	for action_index, action_entry in enumerate(bpy.context.scene.animlist):
		if action_entry.action == None:
			print(f"Action {action_index} omitted, because no blender action was referenced.")
			continue

		if action_entry.is_used == False:
			print(f"Action {action_index} omitted, because it was disabled.")
			continue

		valid_action_entries.append(action_entry)

	return valid_action_entries

def MakeActionEntry(anim_data):
	new_entry : ActionMetaData = bpy.context.scene.animlist.add()
	new_entry.action = anim_data["Action"]
	if bpy.context.scene.render.resolution_x != anim_data["Width"] or bpy.context.scene.render.resolution_y != anim_data["Height"]:
		new_entry.override_resolution = True
	new_entry.height = anim_data["Height"]
	new_entry.width = anim_data["Width"]
	new_entry.max_frames = anim_data["Length"]

	return new_entry

vgroup_map = {
"dagger": "Tool1",
"arrow": "Tool2",
"spear": "Tool1",
"minigun": "Tool1",
"sword": "Tool1",
"crossbow": "Tool1",
"staff": "Tool1",
"hammer": "Tool1",
"pistole": "Tool1",
"rocketlauncher": "Tool1",
"bottle": "Tool1",
"rocket": "Tool1",
"mg": "Tool1",
"bow": "Tool1",
"shield": "Tool2",
"axe": "Tool1",
"shovel": "Tool1",
"fightaxe": "Tool1",
"magic": "Tool2",
"pumpgun": "Tool1",
"grenadelauncher": "Tool1",
"kopf": "Head",
"hals1": "Neck",
"schulterl": "R Shoulder",
"schuterr": "L Shoulder",
"armobenl": "R Upper Arm",
"armobenr": "L Upper Arm",
"armuntenl": "R Forearm",
"armuntenr": "L Forearm",
"handl": "R Hand",
"handr": "L Hand",
"örper": "Body",
"beckenl": "R Pelvis",
"beckenr": "L Pelvis",
"beinobenl": "R Upper Leg",
"beinobenr": "L Upper Leg",
"beinuntenl": "R Foreleg",
"beinuntenr": "L Foreleg",
"fuß2": "R Foot",
"fußr": "L Foot",
"cloak": "Cloak",
"camera": "Camera",
"tube": "Tool1",
"feather": "Tool2",
"tool1": "Tool1",
"tool2": "Tool2"
}

def get_vgroup_mapping(name):
	name = name.lower()
	if vgroup_map.get(name) != None:
		return vgroup_map[name]

	return None