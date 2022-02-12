#--------------------------
# MetaData: Including data structures for action data
# 11.02.2022
#--------------------------
# Robin Hohnsbeen (Ryou)

import bpy

from bpy.props import StringProperty, BoolProperty

class ActionMetaData(bpy.types.PropertyGroup):
	action : bpy.props.PointerProperty(type=bpy.types.Action, name='Action', description="The reference to the action that will be applied on the action target when rendering a spritesheet")
	override_resolution : bpy.props.BoolProperty(
		name='Override resolution', 
		default=False, 
		description="You can render sprites with resolutions other than in the render settings. Keep in mind thought that all resolutions are multiplied by the resolution percentage (100% => 1.0, 200% => 2.0, ...)"
	)
	start_frame : bpy.props.IntProperty(name='Start frame', default=1, soft_min=0, description="The number of the first frame of the action")
	max_frames : bpy.props.IntProperty(name='Max frames', default=16, min=1, soft_max=256, description="The amount of frames that are rendered for this action")
	width : bpy.props.IntProperty(name='Pixel width', default=16, min=1, max=2048, description="The pixel width of one sprite image. (Will be multiplied by the resolution percentage (100% => 1.0, 200% => 2.0, ...)")
	height : bpy.props.IntProperty(name='Pixel height', default=20, min=1, max=2048, description="The pixel height of one sprite image. (Will be multiplied by the resolution percentage (100% => 1.0, 200% => 2.0, ...)")
	override_name : bpy.props.BoolProperty(
		name='Override name', 
		default=False, 
		description="In case you want to have a separate clonk action that references the same blender action. e.g Sword Fight, Axe Fight. Each can use the same blender action but use different tools."
	)
	alternative_name : bpy.props.StringProperty(name='Name Override', default="", description="Fill in, if you want this action to have a different name. This is only usefull if two entries share the same action")
	render_type_enum : bpy.props.EnumProperty(
		items={
			("Spriteanimation", "Spriteanimation", "Render several frames and put them next to each other on the spritesheet."), 
			("Picture", "Picture", "Render one frame and put it where it fits. This is useful for Titleimages.")}, 
		default="Spriteanimation", options={"HIDDEN"}, name=''
		)
	additional_object_enum : bpy.props.EnumProperty(
		items={("1_Object", "Object", "Render one object", 1), ("2_Collection", "Collection", "Render whole collection", 2)}, 
		default="1_Object", options={"HIDDEN"}, name=''
		)
	additional_object : bpy.props.PointerProperty(type=bpy.types.Object, name='', description="An object that is only visible in this action. This can be used for tools that a clonk is holding for example")
	additional_collection : bpy.props.PointerProperty(type=bpy.types.Collection, name='', description="A collection that holds objects that are only visible in this action. This can be used for tools that a clonk is holding for example")
	find_material_name : bpy.props.StringProperty(name='Find material name', maxlen=32, description="Materials containing that name will be replaced by the replace material.")
	replace_material : bpy.props.PointerProperty(type=bpy.types.Material, name='Replace material', description="The material that it will be replaced with.")

class SpriteSheetMetaData(bpy.types.PropertyGroup):
	overlay_rendering_enum : bpy.props.EnumProperty(
		items={
			("Separate", "Separate", "Graphics and Overlay rendered separately. Materials with \"Overlay\" in their name will be replaced with the overlay material."), 
			("Combined", "Combined", "Graphics and Overlay in one image")}, 
		default="Separate", options={"HIDDEN"}, name='Overlay Render Setting'
		)
	overlay_material : bpy.props.PointerProperty(type=bpy.types.Material, name='Overlay Material', description="Materials with \"Overlay\" in its name will be replaced with this material upon render")
	fill_material : bpy.props.PointerProperty(type=bpy.types.Material, name='Fill Material', description="Materials with \"Overlay\" in its name will be replaced with this material upon render")


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