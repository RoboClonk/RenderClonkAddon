# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
	"name" : "RenderClonk",
	"author" : "Robin H.",
	"description" : "For importing Clonk meshes and rendering spritesheets.",
	"blender" : (3, 0, 1),
	"version" : (2, 0, 0),
	"location" : "",
	"warning" : "",
	"category" : "Render"
}

# This addon is used to import Clonk meshes as well as creating spritesheets that are used in the game Clonk Rage or LegacyClonk.
#----------------------------- 
# 20.11.2006.
# 25.03.2007
# Richard Gerum (Randrian)
#------------------------------ 
# 11.02.2022
# Robin Hohnsbeen (Ryou)

from ast import alias
import math
import bpy
from bpy.props import StringProperty, BoolProperty
from bpy_extras.io_utils import ImportHelper
from pathlib import Path

import os.path # For checking a path
import os


from . import MeshPort
from . import AnimPort
from . import SpritesheetMaker
from . import ClonkPort
from . import MetaData
from . import IniPort
from . import PathUtilities
import importlib
importlib.reload(MeshPort)
importlib.reload(AnimPort)
importlib.reload(SpritesheetMaker)
importlib.reload(ClonkPort)
importlib.reload(PathUtilities)
importlib.reload(MetaData)
importlib.reload(IniPort)


print ("Render Clonk 2.0")


AddonDirectory = ""

class MAIN_PT_SettingsPanel(bpy.types.Panel):
	bl_label = "Render Clonk Utilities"
	bl_idname = "MAIN_PT_SettingsPanel"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Render Clonk"

	def draw(self, context):
		layout = self.layout
		scene = context.scene
		
		render_settings_layout = layout.column(align=True)
		if scene.has_applied_rendersettings == False:
			render_settings_layout.operator(Menu_Button.bl_idname, text="Apply Render Settings", icon="SCENE_DATA").menu_active = 3
			render_settings_layout.label(text="Sets optimal render settings for clonk style renders.", icon="INFO")
		else:
			layout.operator(Menu_Button.bl_idname, text="Re-Apply Render Settings", icon="SCENE_DATA").menu_active = 3

		layout.separator()

		actlist_layout = layout.column(align=True)
		actlist_layout.operator(Menu_Button.bl_idname, text="Import Action List (.act)", icon="IMPORT").menu_active = 6
		
		actlist_layout.operator(Menu_Button.bl_idname, text="Import ActMap.txt", icon="IMPORT").menu_active = 12
		

		layout.separator()

		layout.operator(Menu_Button.bl_idname, text="Import Clonk / Tool (.mesh)", icon="IMPORT").menu_active = 1
		layout.operator(Menu_Button.bl_idname, text="Import Action (.anim)", icon="ARMATURE_DATA").menu_active = 2

		layout.separator()

		layout.operator(Menu_Button.bl_idname, text="Append Clonk Rig", icon="OUTLINER_OB_ARMATURE").menu_active = 7
		


class Menu_Button(bpy.types.Operator):
	bl_idname = "menu.menu_op"
	bl_label = "Menu Button"
	bl_description = ""
	bl_options = {"REGISTER", "UNDO"}

	menu_active: bpy.props.IntProperty(name="Menu Index", options={"HIDDEN"})

	def execute(self, context):
		if context.scene.lastfilepath is None or context.scene.lastfilepath == "":
				context.scene.lastfilepath = AddonDirectory


		if self.menu_active == 1:
			bpy.ops.mesh.open_filebrowser("INVOKE_DEFAULT", filepath=context.scene.lastfilepath)
			
		if self.menu_active == 2:
			bpy.ops.anim.open_filebrowser("INVOKE_DEFAULT", filepath=context.scene.lastfilepath)

		if self.menu_active == 3:
			ClonkPort.SetOptimalRenderingSettings()
		
		if self.menu_active == 4:
			ClonkPort.AppendRenderClonkSetup(AddonDirectory)

		if self.menu_active == 5:
			bpy.ops.screen.animation_cancel()
			
			Overlay, Holdout, Fill = ClonkPort.GetOrAppendOverlayMaterials()
			if bpy.context.scene.spritesheet_settings.overlay_material == None:
				bpy.context.scene.spritesheet_settings.overlay_material = Overlay
			if bpy.context.scene.spritesheet_settings.fill_material == None:
				bpy.context.scene.spritesheet_settings.fill_material = Fill
			
			if bpy.context.scene.spritesheet_settings.overlay_rendering_enum == "Separate":	
				# Render overlay
				bpy.ops.timer.progress(output_image_name="Graphics", set_overlay_material=True, replace_overlay_material=False)
			else:
				bpy.ops.timer.progress(output_image_name="Graphics")

		# Import ActList
		if self.menu_active == 6:
			bpy.ops.act.open_filebrowser("INVOKE_DEFAULT", filepath=context.scene.lastfilepath)

		#Append Clonk Rig
		if self.menu_active == 7:
			ClonkPort.GetOrAppendClonkRig(False)

		# Preview Action
		if self.menu_active == 8:
			bpy.ops.preview.action()

		if self.menu_active == 9:
			bpy.ops.screen.animation_cancel()

		if self.menu_active == 10:
			# Prepare Path
			output_directorypath = PathUtilities.GetOutputPath()
			
			if context.scene.custom_output_dir != "":
				output_directorypath = bpy.path.abspath(context.scene.custom_output_dir)
				print("Output path: ", output_directorypath)
				if not os.path.exists(output_directorypath):
					self.report({"ERROR"}, f"Custom Directory not found.")
					return {'FINISHED'}
			else:
				print("Output path: ", output_directorypath)

			info_type, info_text = ClonkPort.PrintActmap(output_directorypath)
			self.report({info_type}, info_text)


		if self.menu_active == 11:
			# Prepare Path
			output_directorypath = PathUtilities.GetOutputPath()
			if context.scene.custom_output_dir != "":
				output_directorypath = bpy.path.abspath(context.scene.custom_output_dir)
				print("Output path: ", output_directorypath)
				if not os.path.exists(output_directorypath):
					self.cancel(context)
					self.report({"ERROR"}, f"Custom Directory not found.")
					return {'FINISHED'}
			else:
				print("Output path: ", output_directorypath)

			info_type, info_text = ClonkPort.PrintDefCore(output_directorypath)
			self.report({info_type}, info_text)

		# ActMap.txt	
		if self.menu_active == 12:
			bpy.ops.actmap.open_filebrowser("INVOKE_DEFAULT", filepath=context.scene.lastfilepath)
			

		return {"FINISHED"}


class Action_List_Button(bpy.types.Operator):
	bl_idname = "list.list_op"
	bl_label = "Action List Operator"
	bl_description = ""
	bl_options = {"REGISTER", "UNDO"}

	menu_active: bpy.props.IntProperty(name="Button Index")

	def execute(self, context):
		if self.menu_active == 1:
			pass
			
		if self.menu_active == 2:
			anim_entry = context.scene.animlist[context.scene.action_meta_data_index]
			#anim_entry = context.scene.animlist
			anim_entry.width = anim_entry.width + 1

		if self.menu_active == 3:
			context.scene.animlist.clear()

		# Move entry up
		if self.menu_active == 4:
			if context.scene.action_meta_data_index > 0:
				context.scene.animlist.move(context.scene.action_meta_data_index, context.scene.action_meta_data_index-1)
				context.scene.action_meta_data_index -= 1

		# Move entry down
		if self.menu_active == 5:
			if context.scene.action_meta_data_index < len(context.scene.animlist)-1:
				context.scene.animlist.move(context.scene.action_meta_data_index, context.scene.action_meta_data_index+1)
				context.scene.action_meta_data_index += 1

		# Add entry
		if self.menu_active == 6:
			item = context.scene.animlist.add()

			if len(bpy.data.actions) > 0:
				item.action = bpy.data.actions[0]

			if context.scene.action_meta_data_index < len(context.scene.animlist)-1:
				context.scene.animlist.move(len(context.scene.animlist)-1, context.scene.action_meta_data_index+1)
				context.scene.action_meta_data_index += 1

		# Remove Item
		if self.menu_active == 7:
			if context.scene.action_meta_data_index >= 0 and context.scene.action_meta_data_index < len(context.scene.animlist):
				context.scene.animlist.remove(context.scene.action_meta_data_index)
				context.scene.action_meta_data_index = min(context.scene.action_meta_data_index, len(context.scene.animlist)-1)
			
		return {"FINISHED"}


class ACTION_PT_LayoutPanel(bpy.types.Panel):
	bl_label = "Actions"
	bl_space_type = "VIEW_3D"
	bl_idname = "ACTION_PT_LayoutPanel"
	bl_region_type = "UI"
	bl_category = "Render Clonk"

	def draw(self, context):
		layout = self.layout
		scene = context.scene

		main_setting_column = layout.column(align=False)

		anim_target_row = main_setting_column.row()
		anim_target_row.alignment = "RIGHT"
		anim_target_row.label(text="Action target", icon="PLAY")
		anim_target_row.prop(scene, "anim_target", text="")
		main_setting_column.separator()

		always_rendered_row = main_setting_column.row()
		always_rendered_row.alignment = "RIGHT"
		always_rendered_row.label(text="Always rendered")
		always_rendered_row.prop(scene, "always_rendered_objects", text="")
		
		layout.separator(factor=1.0)	

		layout.label(text="Actions list", icon="ARMATURE_DATA")
		list_row_layout = layout.row()

		list_row_layout.template_list("ACTION_UL_actionslots", "", scene, "animlist", scene, "action_meta_data_index")
		menu_sort_layout_column = list_row_layout.column()
		menu_sort_layout = menu_sort_layout_column.column(align=True)
		menu_sort_layout.operator("list.list_op", text="", icon="ADD").menu_active = 6
		menu_sort_layout.operator("list.list_op", text="", icon="REMOVE").menu_active = 7
		menu_sort_layout2 = menu_sort_layout_column.column(align=True)
		menu_sort_layout.separator(factor=3.0)
		menu_sort_layout2.operator("list.list_op", text="", icon="TRIA_UP").menu_active = 4
		menu_sort_layout2.operator("list.list_op", text="", icon="TRIA_DOWN").menu_active = 5

		preview_button_layout = layout.column()
		preview_button_layout.alignment = "LEFT"
		
		if len(scene.animlist) == 0:
			return

		anim_entry = scene.animlist[scene.action_meta_data_index]
		preview_button_layout.enabled = (scene.anim_target != None and anim_entry.action != None)
		if SpritesheetMaker.preview_active:
			preview_button_layout.operator(Menu_Button.bl_idname, text="Playing..", icon="PAUSE").menu_active = 8
		else:
			preview_button_layout.operator(Menu_Button.bl_idname, text="Preview Action", icon="PLAY").menu_active = 8


class ACTIONSADD_OPERATOR_Button(bpy.types.Operator):
	bl_idname = "actionadd.settings_op"
	bl_label = "Action Add Operator"
	bl_description = "This will create a new action and applies it here"
	bl_options = {"REGISTER", "UNDO"}

	def execute(self, context):
		new_action = bpy.data.actions.new("NewClonkAction")

		scene = bpy.context.scene
		scene.animlist[scene.action_meta_data_index].action = new_action

		return {"FINISHED"}


class ACTIONSETTINGS_OPERATOR_Button(bpy.types.Operator):
	bl_idname = "action.settings_op"
	bl_label = "Action Settings Operator"
	bl_description = "Use ctrl+b in the camera view to define a render region and manage it here"
	bl_options = {"REGISTER", "UNDO"}

	menu_active: bpy.props.IntProperty(name="Button Index")

	def execute(self, context):
		scene = bpy.context.scene
		anim_entry = scene.animlist[scene.action_meta_data_index]
		#set rect
		if self.menu_active == 1:
			
			anim_entry.region_cropping = (scene.render.border_min_x, scene.render.border_max_x, scene.render.border_min_y, scene.render.border_max_y)
			MetaData.MakeRectCutoutPixelPerfect(anim_entry)
			MetaData.SetRenderBorder(anim_entry)

		#copy rect
		if self.menu_active == 2:
			MetaData.SetRenderBorder(anim_entry)

			scene.render.use_border = True

		#remove rect
		if self.menu_active == 3:
			anim_entry.region_cropping[0] = 0.0
			anim_entry.region_cropping[1] = 1.0
			anim_entry.region_cropping[2] = 0.0
			anim_entry.region_cropping[3] = 1.0
			MetaData.SetRenderBorder(anim_entry)

			scene.render.use_border = False
			

		return {"FINISHED"}


class ACTIONSETTINGS_PT_SubPanel(bpy.types.Panel):
	bl_label = "Action Settings"
	bl_space_type = "VIEW_3D"
	bl_idname = "ACTIONSETTINGS_PT_SubPanel"
	bl_parent_id = "ACTION_PT_LayoutPanel"
	bl_region_type = "UI"
	bl_category = "Render Clonk"

	def draw(self, context):
		layout = self.layout
		scene = context.scene

		action_data_layout = layout.column(align=True)
		if len(scene.animlist) == 0:
			action_data_layout.label(text="Click on the + to see settings here.", icon="INFO")
		
		else:
			anim_entry = scene.animlist[scene.action_meta_data_index]
			blender_action_layout = action_data_layout.row(align=True)
			#blender_action_layout.alignment = "RIGHT"
			blender_action_layout.prop(anim_entry, "action")
			if anim_entry.action == None:
				blender_action_layout.operator("actionadd.settings_op", text="", icon="ADD")

			picture_layout = layout.column(align=True)
			render_type_icon = "ARMATURE_DATA"
			if anim_entry.render_type_enum == "Picture":
				render_type_icon = "USER"

			picture_layout.prop(anim_entry, "render_type_enum", icon=render_type_icon)
			frame_row = picture_layout.row(align=True)
			if anim_entry.render_type_enum == "Spriteanimation":
				frame_row.prop(anim_entry, "start_frame")
				frame_row.prop(anim_entry, "max_frames")

			layout.prop(anim_entry, "use_alternative_name")
			if anim_entry.use_alternative_name:
				action_data_layout2 = layout.row(align=True)
				action_data_layout2.prop(anim_entry, "alternative_name", text="Name")

			layout.prop(anim_entry, "override_resolution")
			if anim_entry.override_resolution:
				action_data_layout2 = layout.row(align=True)
				action_data_layout2.prop(anim_entry, "width")
				action_data_layout2.prop(anim_entry, "height")
				

			additional_objects_layout = layout.column(align=True)
			additional_objects_layout.alignment = "LEFT"
			
			additional_objects_layout.label(text="Rendered additionally:", icon="TOOL_SETTINGS")
			additional_objects_layout_row = additional_objects_layout.row(align=True)
			additional_objects_layout_row.prop(anim_entry, "additional_object_enum")

			if anim_entry.additional_object_enum == "1_Object":
				additional_objects_layout_row.prop(anim_entry, "additional_object")
			else:
				additional_objects_layout_row.prop(anim_entry, "additional_collection")	
			additional_objects_layout.separator()

			material_column = layout.column(align=True)
			material_name_row = material_column.row()
			material_name_row.alignment = "RIGHT"
			material_name_row.label(text="Material name")
			material_name_row.prop(anim_entry, "find_material_name", text="")

			replace_material_row = material_column.row()
			replace_material_row.alignment = "RIGHT"
			replace_material_row.enabled = len(anim_entry.find_material_name) > 0
			replace_material_row.label(text="Replace with")
			replace_material_row.prop(anim_entry, "replace_material", text="")
			
			region_cropping_layout_col = layout.column(align=True)
			if MetaData.is_using_cutout(anim_entry):
				min_max_pixels, pixel_dimensions = MetaData.GetPixelFromCutout(anim_entry)
				region_cropping_layout_col.label(text="Region cropping active", icon="CON_SIZELIMIT")
				sprite_height = SpritesheetMaker.get_sprite_height(anim_entry, include_cropping=False)
				region_cropping_info = "x: %d px  y: %d px  w: %d px  h: %d px" % (min_max_pixels[0], sprite_height - min_max_pixels[3], pixel_dimensions[0], pixel_dimensions[1])
				region_cropping_layout_col.label(text=region_cropping_info)
			else:
				region_cropping_layout_col.label(text="Region cropping inactive", icon="MATPLANE")
				region_cropping_info = " Use ctrl+b in the camera view"
				region_cropping_layout_col.label(text=region_cropping_info)
				region_cropping_layout_col.label(text=" Then click on 'Set'")

			
			region_cropping_layout_row = region_cropping_layout_col.row(align=True)
			region_cropping_layout_row.operator("action.settings_op", text="Set", icon="PASTEDOWN").menu_active = 1
			region_cropping_layout_row.operator("action.settings_op", text="Copy", icon="COPYDOWN").menu_active = 2
			region_cropping_layout_row.operator("action.settings_op", text="Remove", icon="X").menu_active = 3
			region_cropping_layout_col.prop(anim_entry, "invert_region_cropping")

			layout.prop(anim_entry, "use_normal_action_placement")


		layout.separator(factor=2.0)

class SPRITESHEET_PT_Panel(bpy.types.Panel):
	bl_label = "Spritesheet Rendering"
	bl_idname = "SPRITESHEET_PT_Panel"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Render Clonk"

	def draw(self, context):
		layout = self.layout
		scene = context.scene

		additional_settings_layout = layout.column(align=True)
		additional_settings_layout.alignment = "LEFT"
		additional_settings_layout.prop(scene.spritesheet_settings, "overlay_rendering_enum")
		if scene.spritesheet_settings.overlay_rendering_enum == "Separate":
			additional_settings_layout.label(text="Renders the spritesheet twice.", icon="INFO")

		layout.separator()

		col = layout.column(align=True)

		render_button = col.column()
		render_button.enabled = len(bpy.context.scene.animlist) > 0
		render_button_text = "Render Spritesheet"
		if context.scene.is_rendering_spritesheet:
			render_button_text = "Rendering.. (Press Escape to cancel)"

		render_button.operator(Menu_Button.bl_idname, text=render_button_text, icon="RENDER_RESULT").menu_active = 5
		
		if context.scene.is_rendering_spritesheet:
			progress_layout = col.row()
			progress_layout.prop(bpy.context.scene, "spritesheet_render_progress", text="Render Progress")
			progress_layout.label(text="Sheet " + str(SpritesheetMaker.current_sheet_number) + "/" + str(SpritesheetMaker.current_max_sheets) + " " + SpritesheetMaker.current_action_name)
			layout.separator()
		else:
			col.prop(scene.render, "resolution_x")
			col.prop(scene.render, "resolution_y")

			if scene.scene_render_resolution != str(scene.render.resolution_percentage)+"%":
				col.label(text="Custom resolution percentage used: %d%s" % (scene.render.resolution_percentage, "%"), icon="ERROR")
				col.label(text="It is recommended to use the dropdown")
			
			res_percentage_layout = col.row(align=True)
			res_percentage_layout.label(text="Resolution Percentage:")
			res_percentage_layout.prop(scene, "scene_render_resolution")
		
		layout.separator()

		x_resolution = math.floor(scene.render.resolution_x * scene.render.resolution_percentage/100)
		y_resolution = math.floor(scene.render.resolution_y * scene.render.resolution_percentage/100)
		col.label(text="Output Resolution Per Sprite   x: " + str(x_resolution) + " px   y: " + str(y_resolution) + " px")
		
		if bpy.context.scene.custom_output_dir != "":
			layout.label(text="Individual sprites will be saved at: " + PathUtilities.GetOutputPath(), icon="INFO")
		else:
			layout.label(text="Output path: " + PathUtilities.GetOutputPath())
		
		custom_output_layout = layout.column(align=True)
		custom_output_layout.label(text="Custom output directory:")
		custom_output_layout.prop(bpy.context.scene, "custom_output_dir", text="")

		layout.separator()
		
		if ClonkPort.DoesActmapExist():
			layout.operator(Menu_Button.bl_idname, text="Update ActMap.txt", icon="FILE_TEXT").menu_active = 10
		else:
			layout.operator(Menu_Button.bl_idname, text="Save ActMap.txt", icon="FILE_TEXT").menu_active = 10

		if ClonkPort.DoesDefCoreExist():
			layout.operator(Menu_Button.bl_idname, text="Update DefCore.txt", icon="FILE_TEXT").menu_active = 11
		else:
			layout.operator(Menu_Button.bl_idname, text="Save DefCore.txt", icon="FILE_TEXT").menu_active = 11

		layout.separator(factor=3.0)

		pcoll = preview_collections["main"]
		clonk_icon = pcoll["clonk_icon"]
		layout.template_icon(icon_value=clonk_icon.icon_id,scale=3)


class ABOUT_PT_LayoutPanel(bpy.types.Panel):
	bl_label = "About"
	bl_space_type = "VIEW_3D"
	bl_idname = "ABOUT_PT_LayoutPanel"
	bl_region_type = "UI"
	bl_category = "Render Clonk"
	bl_options = {"DEFAULT_CLOSED"}

	def draw(self, context):
		layout = self.layout
		scene = context.scene

		pcoll = preview_collections["main"]
		my_icon = pcoll["my_icon"]
		clonk_icon = pcoll["clonk_icon"]
		col2row = layout.row()
		col2row.template_icon(icon_value=clonk_icon.icon_id,scale=3)
		
		col2row.template_icon(icon_value=my_icon.icon_id,scale=3)
		layout.separator()

		col2 = layout.column()
		col2.label(text="Originally developed in 2007 by:")
		col2.label(text="   Richard Gerum (Randrian)")

		layout.separator()

		col3 = layout.column()
		col3.label(text="API Upgrade in 2022 by:")
		col3.label(text="   Robin Hohnsbeen (Ryou)")


preview_collections = {}

class ACTION_UL_actionslots(bpy.types.UIList):
	
	def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
		if self.layout_type in {"DEFAULT", "COMPACT"}:
			entry_layout = layout.row(align=False)
			entry_layout.alignment = "LEFT"

			if item.action == None:
				action_name = "--no action selected--"
				entry_layout.label(text=str(index) + ":   " + action_name, icon="ERROR")
			else:
				icon_name = "ARMATURE_DATA"
				if item.render_type_enum == "Picture":
					icon_name = "USER"
				
				alternate_name_layout = entry_layout.row(align=True)
				alternate_name_layout.alignment = "LEFT"
				alternate_name_layout.label(text=str(index) + ":")
				if item.use_alternative_name and len(item.alternative_name) > 0:	
					alternate_name_layout.label(text=" \"" + item.alternative_name + "\"", icon=icon_name)
				else:
					alternate_name_layout.prop(item.action, "name", text="", emboss=False, icon=icon_name, expand=True)
			
			if item.additional_object_enum == "1_Object" and item.additional_object != None:
				object_count = 1
				entry_layout.label(text=str(object_count) + " ", icon="TOOL_SETTINGS")
			if item.additional_object_enum == "2_Collection" and item.additional_collection != None:
				object_count = len(item.additional_collection.objects)
				entry_layout.label(text=str(object_count) + " ", icon="TOOL_SETTINGS")

			if item.override_resolution:
				entry_layout.label(text=str(item.width) + "x" + str(item.height), icon="TEXTURE_DATA")


def SceneRenderUpdate(self, context):
	scene = bpy.context.scene
	resolution = scene.scene_render_resolution
	
	if resolution == "100%":
		scene.render.resolution_percentage = 100
	if resolution == "200%":
		scene.render.resolution_percentage = 200
	if resolution == "300%":
		scene.render.resolution_percentage = 300

registered_classes = [
	Menu_Button, 
	ClonkPort.OT_MeshFilebrowser, 
	ClonkPort.OT_AnimFilebrowser,
	ClonkPort.OT_ActListFilebrowser,
	ClonkPort.OT_ActMapFilebrowser, 
	ACTION_UL_actionslots, 
	Action_List_Button,
	SpritesheetMaker.TIMER_OT,
	SpritesheetMaker.PREVIEW_OT,
	MetaData.ActionMetaData,
	MetaData.SpriteSheetMetaData,
	MAIN_PT_SettingsPanel, 
	ACTION_PT_LayoutPanel, 
	ACTIONSETTINGS_PT_SubPanel,
	SPRITESHEET_PT_Panel,
	ACTIONSETTINGS_OPERATOR_Button,
	ACTIONSADD_OPERATOR_Button,
]


def register():
		import bpy.utils.previews

		global AddonDirectory
		script_file = os.path.realpath(__file__)
		AddonDirectory = os.path.dirname(script_file)
		
		global preview_collections
		pcoll = bpy.utils.previews.new()
		pcoll.load("clonk_icon", os.path.join(AddonDirectory, "Clonk.png"), "IMAGE")

		preview_collections["main"] = pcoll
		

		for registered_class in registered_classes:
			bpy.utils.register_class(registered_class)
		

		bpy.types.Scene.anim_target = bpy.props.PointerProperty(
			type=bpy.types.Object, 
			name="Action target", 
			description="Actions that are listed below will be applied to this object as soon as \"Render Spritesheet\" is pressed. Using an armature is recommended, but not necessary", 
			poll=None,
		)
		bpy.types.Scene.always_rendered_objects = bpy.props.PointerProperty(
			type=bpy.types.Collection, 
			name="Always rendered", 
			description="This collection should contain all objects that are visible in all actions. This includes lights and cameras and if you render a clonk, it should be inside this collection as well", 
			poll=None,
		)

		bpy.types.Scene.action_meta_data_index = bpy.props.IntProperty(name="Action index")
		bpy.types.Scene.animlist = bpy.props.CollectionProperty(type=MetaData.ActionMetaData)
		bpy.types.Scene.spritesheet_settings = bpy.props.PointerProperty(type=MetaData.SpriteSheetMetaData)
		bpy.types.Scene.lastfilepath = bpy.props.StringProperty()
		bpy.types.Scene.has_applied_rendersettings = bpy.props.BoolProperty(name="has_applied_rendersettings", default=False)
		bpy.types.Scene.custom_output_dir = bpy.props.StringProperty(name="Custom Output Directory", subtype="DIR_PATH")
		bpy.types.Scene.scene_render_resolution = bpy.props.EnumProperty(items={
			("100%", "100%", "Render at 100% Resolution", 1), 
			("200%", "200%", "Render at 200% Resolution", 2),
			("300%", "300%", "Render at 300% Resolution", 3)},
		default="100%", name='', update=SceneRenderUpdate
		)
		
		bpy.types.Scene.is_rendering_spritesheet = bpy.props.BoolProperty(name="Is rendering spritesheet", default=False)
		bpy.types.Scene.spritesheet_render_progress = bpy.props.IntProperty(name="Spritesheet Render Progress", subtype="PERCENTAGE", min=0, max=100)


def unregister():
	for registered_class in registered_classes:
			bpy.utils.unregister_class(registered_class)
		
	global preview_collections
	bpy.utils.previews.remove(preview_collections["main"])

	del bpy.types.Scene.anim_target
	del bpy.types.Scene.action_meta_data_index
	del bpy.types.Scene.animlist
	del bpy.types.Scene.always_rendered_objects
	del bpy.types.Scene.lastfilepath
	del bpy.types.Scene.spritesheet_settings
	del bpy.types.Scene.scene_render_resolution


if __name__ == "__main__":
		register()




