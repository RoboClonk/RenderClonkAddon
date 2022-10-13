#--------------------------
# SpritesheetMaker: Used to pack several renders together in one spritesheet using NumPy.
# 11.02.2022
#--------------------------
# Robin Hohnsbeen (Ryou)

import math
import bpy
import numpy as np
import os
from enum import Enum
from pathlib import Path

from . import MetaData
from . import AnimPort
from . import PathUtilities


def get_res_multiplier():
	return bpy.context.scene.render.resolution_percentage / 100.0

def get_sprite_width(action_entry, include_cropping=True):
	x_res_sprite = bpy.context.scene.render.resolution_x
	
	if action_entry.override_resolution:
		x_res_sprite = action_entry.width

	if action_entry.invert_region_cropping == False and MetaData.is_using_cutout(action_entry) and include_cropping:
		min_max_pixels, pixel_dimensions = MetaData.GetPixelFromCutout(action_entry)

		x_res_sprite = pixel_dimensions[0]

	return x_res_sprite

def get_sprite_height(action_entry, include_cropping=True):
	y_res_sprite = bpy.context.scene.render.resolution_y
	
	if action_entry.override_resolution:
		y_res_sprite = action_entry.height

	if action_entry.invert_region_cropping == False and MetaData.is_using_cutout(action_entry) and include_cropping:
		min_max_pixels, pixel_dimensions = MetaData.GetPixelFromCutout(action_entry)
		
		y_res_sprite = pixel_dimensions[1]

	return y_res_sprite

def get_sheet_strip_width(action_entry, get_scaled=True):
	x_res_sprite = get_sprite_width(action_entry)

	max_frames = action_entry.max_frames
	if action_entry.render_type_enum == "Picture":
		max_frames = 1

	if get_scaled:
		total_x_res = max_frames * x_res_sprite * get_res_multiplier()
	else:
		total_x_res = max_frames * x_res_sprite

	return math.floor(total_x_res)

def get_sheet_strip_height(action_entry, get_scaled=True):
	y_res_sprite = get_sprite_height(action_entry)

	if get_scaled:
		total_y_res = y_res_sprite * get_res_multiplier()
	else:
		total_y_res = y_res_sprite

	return math.floor(total_y_res)

def GetSpriteStripInfo(action_entry, x_position, y_position):
	sheetstrip_height = get_sheet_strip_height(action_entry, get_scaled=False)
	sheetstrip_width = get_sheet_strip_width(action_entry, get_scaled=False)
	sprite_height = get_sprite_height(action_entry)
	sprite_width = get_sprite_width(action_entry)
	sheet_strip_info = {
		"Height" : sheetstrip_height,
		"Width" : sheetstrip_width,
		"X_pos" : x_position,
		"Y_pos" : y_position,
		"Length" : action_entry.max_frames,
		"Name" : MetaData.GetActionName(action_entry),
		"Sprite_Height" : sprite_height,
		"Sprite_Width" : sprite_width
	}

	return sheet_strip_info

def GetSpritesheetInfo(action_entries):
	# The widest action strip determines the width of the spritesheet.
	sheet_width = 0
	for action_entry in action_entries:
		total_x_res = get_sheet_strip_width(action_entry, get_scaled=False)
		if total_x_res > sheet_width:
			sheet_width = total_x_res
	
	sheet_strips = {}

	# Get Height
	current_x_position = 0
	current_y_position = 0
	last_height = 0
	action_index = 0
	rows = []
	row_height = 0
	special_placement_actions = []
	for action_entry in action_entries:
		if action_entry.use_normal_action_placement == False: # Will be placed later
			special_placement_actions.append(action_entry)
			continue

		sheetstrip_height = get_sheet_strip_height(action_entry, get_scaled=False)
		sheetstrip_width = get_sheet_strip_width(action_entry, get_scaled=False)
		
		if current_x_position > sheet_width - sheetstrip_width and last_height != 0:
			# Go to new row
			rows.append({"x_remaining" : sheet_width - current_x_position, "row_height" : row_height})
			current_x_position = 0
			current_y_position += row_height
			row_height = 0
		
		sheet_strips[MetaData.GetActionName(action_entry)] = GetSpriteStripInfo(action_entry, current_x_position, current_y_position)
		
		current_x_position += sheetstrip_width
		action_index += 1
		last_height = sheetstrip_height

		if sheetstrip_height > row_height:
			row_height = sheetstrip_height
	
	###
	sheet_height = current_y_position + last_height
	rows.append({"x_remaining" : sheet_width - current_x_position, "row_height" : row_height})

	# Try to place these actions at the end of the other action's rows. If no place is found, make a new row.
	for special_placement_action in special_placement_actions:
		sprite_height = get_sprite_height(special_placement_action)
		sprite_width = get_sprite_width(special_placement_action)

		y_begin = 0
		x_begin = 0
		height_remaining = sprite_height
		found_place = False
		rows_changed = []

		for row_number, row in enumerate(rows):
			if row["x_remaining"] >= sprite_width:
				if sheet_width - row["x_remaining"] > x_begin:
					x_begin = sheet_width - row["x_remaining"]

				height_remaining -= row["row_height"]
				rows_changed.append(row_number)

				if height_remaining <= 0:
					sheet_strips[MetaData.GetActionName(special_placement_action)] = GetSpriteStripInfo(special_placement_action, x_begin, y_begin)
					found_place = True
					for changed_row_number in rows_changed:
						rows[changed_row_number]["x_remaining"] = max(sheet_width - x_begin + sprite_width, 0)
					break

			else:
				y_begin += row["row_height"]
				x_begin = 0
				height_remaining = sprite_height
				rows_changed.clear()

		if found_place == False:
			y_begin = sheet_height
			x_begin = 0
			strip_info = GetSpriteStripInfo(special_placement_action, x_begin, y_begin)
			sheet_strips[MetaData.GetActionName(special_placement_action)] = strip_info
			
			sheet_height += strip_info["Height"]
			rows.append({"x_remaining" : strip_info["Width"], "row_height" : strip_info["Height"]})
			

	return math.floor(sheet_width * get_res_multiplier()), math.floor(sheet_height * get_res_multiplier()), sheet_strips

def get_action_visible_objects(action_entry : MetaData.ActionMetaData):
	visible_objects = []
	visible_objects.append(bpy.context.scene.anim_target)
	
	if bpy.context.scene.always_rendered_objects != None:
		for object in bpy.context.scene.always_rendered_objects.objects:
			visible_objects.append(object)

	if action_entry.additional_object_enum == "1_Object" and action_entry.additional_object != None:
		visible_objects.append(action_entry.additional_object)
	elif action_entry.additional_object_enum == "2_Collection" and action_entry.additional_collection != None:
		for object in action_entry.additional_collection.objects:
			visible_objects.append(object)

	# Make sure no objects that live in inactive collections are used.
	visible_objects_filtered = []
	for object in visible_objects:
		if object.name in bpy.context.view_layer.objects:
			visible_objects_filtered.append(object)

	return visible_objects_filtered

def reset_object(object):
	object.location = [0, 0, 0]
	if object.rotation_mode == "QUATERNION":
		object.rotation_quaternion = [1.0, 0, 0, 0]
	else:
		object.rotation_euler = [0, 0, 0]
	object.scale =  [1.0, 1.0, 1.0]

def get_action_camera(action_entry):
	if action_entry.override_camera and action_entry.override_camera.type == "CAMERA":
		return action_entry.override_camera

	return bpy.context.scene.camera

def prepare_action(action_entry : MetaData.ActionMetaData):
	if bpy.context.scene.anim_target == None:
		raise AssertionError("No anim target assigned!")
	if action_entry == None:
		raise AssertionError("Action entry not assigned.")
	if action_entry.action == None:
		raise AssertionError("No Blender action set inside action entry.")
	
	if bpy.context.scene.anim_target.type == "ARMATURE":
		AnimPort.ResetArmature(bpy.context.scene.anim_target.pose)
	else:
		reset_object(bpy.context.scene.anim_target)

	for object in bpy.context.view_layer.objects:
		object.hide_set(True)
		object.hide_render = True

	for object in get_action_visible_objects(action_entry):
		object.hide_set(False)
		object.hide_render = False

	if action_entry.render_type_enum == "Picture":
		bpy.context.scene.frame_current = 1
		bpy.context.scene.frame_start = 1
		bpy.context.scene.frame_end = 1
	else:
		bpy.context.scene.frame_current = action_entry.start_frame
		bpy.context.scene.frame_start = action_entry.start_frame
		bpy.context.scene.frame_end = action_entry.start_frame + action_entry.max_frames-1

	if bpy.context.scene.anim_target.animation_data == None:
		bpy.context.scene.anim_target.animation_data_create()

	bpy.context.scene.anim_target.animation_data.action = action_entry.action

	x_dim, y_dim = get_current_render_dimensions(action_entry)
	bpy.context.scene.render.resolution_x = x_dim
	bpy.context.scene.render.resolution_y = y_dim

	use_region_cropping = action_entry.invert_region_cropping == False and MetaData.is_using_cutout(action_entry)
	bpy.context.scene.render.use_border = use_region_cropping
	bpy.context.scene.render.use_crop_to_border = use_region_cropping
	if use_region_cropping:
		# In case the resolution changed after the region was set, we still want to have pixel perfect render regions.
		MetaData.MakeRectCutoutPixelPerfect(action_entry)
		MetaData.SetRenderBorder(action_entry)
	else:
		MetaData.UnsetRenderBorder()

	bpy.context.scene.camera = get_action_camera(action_entry)

	if action_entry.override_camera_shift:
		bpy.context.scene.camera.data.shift_x = 1.0/x_dim * action_entry.camera_shift_x
		bpy.context.scene.camera.data.shift_y = 1.0/y_dim * action_entry.camera_shift_y
	

def get_current_render_dimensions(action_entry):
	if action_entry.override_resolution:
		return action_entry.width, action_entry.height
	else:
		return bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y

def GetMaterialsToReplace():
	materials_to_replace = []
 
	# Just iterate over every object to make things easier
	for object in bpy.context.scene.objects:
		if object.type != "MESH":
			continue

		for material_index, material_slot in enumerate(object.material_slots):
			if material_slot.material == None:
				continue
			
			is_overlay = "overlay" in material_slot.material.name.lower()
			
			material_info = {
				"owner" : object,
				"material_index" : material_index,
				"original_material" : material_slot.material,
				"is_overlay" : is_overlay
			}

			materials_to_replace.append(material_info)

	return materials_to_replace

		
def ReplaceOverlayMaterials(materials_to_replace, replace_overlay=True):
	overlay_material = bpy.context.scene.spritesheet_settings.overlay_material
	holdout_material = bpy.data.materials["Holdout"]
	
	for material_info in materials_to_replace:
		material_index = material_info["material_index"]
		
		if replace_overlay:
			if material_info["is_overlay"]:
				material_info["owner"].material_slots[material_index].material = overlay_material
			else:
				material_info["owner"].material_slots[material_index].material = holdout_material
		else:
			if material_info["is_overlay"]:
				material_info["owner"].material_slots[material_index].material = holdout_material
			else:
				material_info["owner"].material_slots[material_index].material = material_info["original_material"]

def ReplaceFillMaterials(materials_to_replace):
	fill_material = bpy.context.scene.spritesheet_settings.fill_material

	for material_info in materials_to_replace:
		material_index = material_info["material_index"]
		
		if material_info["is_overlay"]:
			material_info["owner"].material_slots[material_index].material = fill_material

def ReplaceMaterialWithName(materials_to_replace, search_name, replacement_material):
	for material_info in materials_to_replace:
		material_index = material_info["material_index"]
		current_material = material_info["owner"].material_slots[material_index].material
		material_name : str = current_material.name

		if current_material is material_info["original_material"] and material_name.find(search_name) > -1:
			material_info["owner"].material_slots[material_index].material = replacement_material

def ResetMaterialReplacementByName(materials_to_replace, search_name, replacement_material): # replacement_material is used as a key to find the material that was replaced.
	for material_info in materials_to_replace:
		material_index = material_info["material_index"]
		current_material = material_info["owner"].material_slots[material_index].material
		original_material_name : str = material_info["original_material"].name

		if replacement_material == current_material and original_material_name.find(search_name) > -1:
			material_info["owner"].material_slots[material_index].material = material_info["original_material"]


def ResetOverlayMaterials(materials_to_replace):
	for material_info in materials_to_replace:
		material_index = material_info["material_index"]
		material_info["owner"].material_slots[material_index].material = material_info["original_material"]

current_action_name = ""
current_sheet_number = 1
current_max_sheets = 1

def GetOrthoScale(anim_entry):
	action_camera = get_action_camera(anim_entry)
	if action_camera.data.sensor_fit == "VERTICAL":
		zoom_multiplier = anim_entry.height / bpy.context.scene.render.resolution_y
	elif action_camera.data.sensor_fit == "HORIZONTAL":
		zoom_multiplier = anim_entry.width / bpy.context.scene.render.resolution_x
	else: # "AUTO"
		if anim_entry.width > anim_entry.height:
			zoom_multiplier = anim_entry.width / bpy.context.scene.render.resolution_x
		else:
			zoom_multiplier = anim_entry.height / bpy.context.scene.render.resolution_y

	return action_camera.data.ortho_scale * zoom_multiplier

def GetImageForPicture(current_action, sprite_width, sprite_height):
	predefined_image = None
	if current_action.render_type_enum == "Picture" and (current_action.image_for_picture_combined != None or current_action.image_for_picture_overlay != None):
		global current_sheet_number
		
		used_image = None
		if current_action.image_for_picture_combined and current_sheet_number == 1:
			used_image = current_action.image_for_picture_combined 

		if current_sheet_number == 2:
			if current_action.image_for_picture_overlay:
				used_image = current_action.image_for_picture_overlay
			elif current_action.image_for_picture_combined:
				used_image = current_action.image_for_picture_combined 

		if used_image:
			predefined_image = used_image.copy()
			predefined_image.scale(sprite_width, sprite_height)

	return predefined_image

def AdjustOrthoScale(anim_entry):
	default_camera_zoom = {}
	action_camera = get_action_camera(anim_entry)
	
	if anim_entry.override_resolution and anim_entry.render_type_enum == "Spriteanimation" and action_camera.data.type == "ORTHO":
		default_camera_zoom[action_camera] = action_camera.data.ortho_scale

		action_camera.data.ortho_scale = GetOrthoScale(anim_entry)

	return default_camera_zoom

# Spritesheet rendering
class TIMER_OT(bpy.types.Operator):
	"""Operator that shows a progress bar while rendering the spritesheet"""
	bl_idname = "timer.progress"
	bl_label = "Progress Timer"

	_timer = None

	# Set from outside
	output_image_name : bpy.props.StringProperty("OutputImageName", default="Graphics")
	set_overlay_material : bpy.props.BoolProperty("SetOverlayMaterial", default=False)
	replace_overlay_material : bpy.props.BoolProperty("ReplaceOverlayMaterial", default=False)
	###

	action_entries = []
	replacement_materials : list

	has_render_finished = False
	sheet_width : int
	sheet_height : int
	sprite_strips : list
	output_image_data : np.ndarray
	strip_image_data : np.ndarray
	output_image : bpy.types.Image = None
	output_directorypath : str

	base_x = 16
	base_y = 20
	current_action_index : bpy.props.IntProperty("CurrentActionIndex", default=0)
	current_frame_number = 0

	render_state = 0
	total_frames = 1
	current_total_frames = 0

	has_been_cancelled = False

	default_camera = None
	default_camera_zoom = {} # Map from camera to default ortho scale
	default_camera_shift = {} # Map from camera to default camera shift

	cancel_message_type = ""
	cancel_message = ""

	def execute(self, context):
		wm = context.window_manager
		self._timer = wm.event_timer_add(0.005, window=context.window)
		wm.modal_handler_add(self)

		# Prepare Data
		self.action_entries = MetaData.GetValidActionEntries()

		messagetype, message = MetaData.CheckIfActionListIsValid(self.action_entries)

		self.base_x = bpy.context.scene.render.resolution_x
		self.base_y = bpy.context.scene.render.resolution_y

		self.default_camera = bpy.context.scene.camera

		if messagetype == "ERROR" or messagetype == "WARNING":
			self.cancel(context)
			self.cancel_message_type = messagetype
			self.cancel_message = message
			return {'RUNNING_MODAL'}

		self.has_render_finished = True
		self.sheet_width, self.sheet_height, self.sprite_strips = GetSpritesheetInfo(self.action_entries)
		self.output_image_data = np.zeros((self.sheet_height, self.sheet_width, 4), 'f')
		self.output_image = bpy.data.images.new(self.output_image_name, width=self.sheet_width, height=self.sheet_height)
		print("Spritesheetdimensions: " + str(self.sheet_width) + "x" + str(self.sheet_height))

		self.replacement_materials = GetMaterialsToReplace()

		# Prepare Path
		self.output_directorypath = PathUtilities.GetOutputPath()
		if context.scene.custom_output_dir != "":
			self.output_directorypath = bpy.path.abspath(context.scene.custom_output_dir)
			if not os.path.exists(self.output_directorypath):
				self.cancel(context)
				self.cancel_message_type = "ERROR"
				self.cancel_message = "Custom Directory not found. Aborted."
				return {'RUNNING_MODAL'}
		else:
			self.output_directorypath = os.path.join(self.output_directorypath, "spritesheets")

		image_output_path = os.path.join(self.output_directorypath, self.output_image_name + ".png")
		print("Output" + image_output_path)
		if os.path.exists(image_output_path):
			if PathUtilities.CanReadFile(image_output_path) == False or PathUtilities.CanWriteFile(image_output_path) == False:
				self.cancel(context)
				self.cancel_message_type = "ERROR"
				self.cancel_message = "Need read/write permissions at output path. Aborted."
				return {'RUNNING_MODAL'}

		global current_action_name
		current_action_name = ""
		global current_sheet_number
		global current_max_sheets
		current_sheet_number = 1
		current_max_sheets = 1

		if self.set_overlay_material:
			ReplaceOverlayMaterials(self.replacement_materials, replace_overlay=self.replace_overlay_material)
			current_max_sheets = 2

			if self.replace_overlay_material == True:
				current_sheet_number = 2
		else:
			ReplaceFillMaterials(self.replacement_materials)
		
		self.render_state = 0
		self.current_action_index = 0
		self.current_frame_number = 0

		context.scene.is_rendering_spritesheet = True

		self.total_frames = 0
		for entry in self.action_entries:
			self.total_frames += entry.max_frames

		return {'RUNNING_MODAL'}

	def reset_ortho_scale(self):
		for camera, default_ortho_scale in self.default_camera_zoom.items():
			camera.data.ortho_scale = default_ortho_scale
		
		self.default_camera_zoom.clear()

	def reset_camera_shift(self):
		for camera, shift in self.default_camera_shift.items():
			camera.data.shift_x = shift[0]
			camera.data.shift_y = shift[1]
		
		self.default_camera_shift.clear()

	def store_camera_shift(self, action_entry):
		camera = get_action_camera(action_entry)

		self.default_camera_shift[camera] = [camera.data.shift_x, camera.data.shift_y]

	def modal(self, context: bpy.types.Context, event: bpy.types.Event):
		if event.type in {'ESC'}:
			self.cancel(context)
			return {'CANCELLED'}

		if self.has_been_cancelled:
			self.report({self.cancel_message_type}, "%s" % (self.cancel_message))
			return {'CANCELLED'}


		if event.type == "TIMER" and self.has_render_finished:
			self.has_render_finished = False
			
			# Prepare for new action strip
			if self.render_state == 0:
				current_action = self.action_entries[self.current_action_index]
				bpy.context.scene.render.resolution_x = self.base_x
				bpy.context.scene.render.resolution_y = self.base_y
				self.reset_ortho_scale()
				bpy.context.scene.camera = self.default_camera
				self.default_camera_zoom = AdjustOrthoScale(current_action)
				self.reset_camera_shift()
				self.store_camera_shift(current_action)
				
				prepare_action(current_action)


				if current_action.find_material_name != "" and current_action.replace_material != None:
					ReplaceMaterialWithName(self.replacement_materials, current_action.find_material_name, current_action.replace_material)

				sheetstrip_width = get_sheet_strip_width(current_action)
				sheetstrip_height = get_sheet_strip_height(current_action)
				self.strip_image_data = np.zeros((sheetstrip_height, sheetstrip_width, 4), 'f')

				self.render_state = 1
				self.current_frame_number = 0
				global current_action_name
				current_action_name = MetaData.GetActionName(current_action)

			# Render one sprite of sprite strip
			if self.render_state == 1:
				current_action = self.action_entries[self.current_action_index]
				sprite_width = math.floor(get_sprite_width(current_action) * get_res_multiplier())
				sprite_height = math.floor(get_sprite_height(current_action) * get_res_multiplier())
				
				if current_action.render_type_enum != "Picture":
					bpy.context.scene.frame_current = self.current_frame_number + current_action.start_frame
				
				rendered_sprite_image = GetImageForPicture(current_action, sprite_width, sprite_height)

				if rendered_sprite_image == None:
					output_filepath = os.path.join(PathUtilities.GetOutputPath(), "sprites", MetaData.GetActionName(current_action) + "_" + str(bpy.context.scene.frame_current))
					
					bpy.context.scene.render.filepath = output_filepath
					bpy.ops.render.render(write_still=True)
					
					rendered_sprite_image = bpy.data.images.load(output_filepath + ".png")
				
				# Allocate a numpy array to manipulate pixel data.
				sprite_pixel_data = np.zeros((sprite_height, sprite_width, 4), 'f')
				# Fast copy of pixel data from bpy.data to numpy array.
				rendered_sprite_image.pixels.foreach_get(sprite_pixel_data.ravel())

				# Cutout if region is enabled
				if current_action.invert_region_cropping and MetaData.is_using_cutout(current_action):
					min_max_pixels, pixel_dimensions = MetaData.GetPixelFromCutout(current_action, scaled=True)
					sprite_pixel_data[min_max_pixels[2]:min_max_pixels[3], min_max_pixels[0]:min_max_pixels[1], :] = np.zeros((pixel_dimensions[1], pixel_dimensions[0], 4), 'f')

				# Cleanup
				bpy.data.images.remove(rendered_sprite_image)

				# Paste sprite onto sheet
				self.strip_image_data[:sprite_height, self.current_frame_number*sprite_width:(self.current_frame_number+1)*sprite_width, :] = sprite_pixel_data[:, :, :]

				self.current_frame_number += 1
				if self.current_frame_number == current_action.max_frames or current_action.render_type_enum == "Picture":
					self.render_state = 2

				# Just for progress bar
				self.current_total_frames += 1

			# Paste sprite strip onto sheet
			if self.render_state == 2:
				current_action : MetaData.ActionMetaData = self.action_entries[self.current_action_index]
				sprite_strip = self.sprite_strips[MetaData.GetActionName(current_action)]

				x_pos = math.floor(sprite_strip["X_pos"] * get_res_multiplier())
				y_pos = math.floor(sprite_strip["Y_pos"] * get_res_multiplier())
			
				# Paste sprite onto sheet
				sheetstrip_width = get_sheet_strip_width(current_action)
				sheetstrip_height = get_sheet_strip_height(current_action)
				paste_y_position = self.sheet_height-y_pos-sheetstrip_height
				paste_y_position_end = self.sheet_height-y_pos
				self.output_image_data[paste_y_position:paste_y_position_end, x_pos:x_pos+sheetstrip_width, :] = self.strip_image_data[:, :, :]
				####

				if current_action.find_material_name != "" and current_action.replace_material != None:
					ResetMaterialReplacementByName(self.replacement_materials, current_action.find_material_name, current_action.replace_material)

				self.current_action_index += 1
				if self.current_action_index == len(self.action_entries):
					self.render_state = 3
				else:
					self.render_state = 0

			# Output image if last action was rendered.
			if self.render_state == 3:
				bpy.context.scene.render.resolution_x = self.base_x
				bpy.context.scene.render.resolution_y = self.base_y
				print("Finished rendering Spritesheet.")
				# Copy of pixel data from numpy array back to the output image.
				self.output_image.pixels.foreach_set(self.output_image_data.ravel())
				self.output_image.update()
				
				output_file = os.path.join(self.output_directorypath, self.output_image_name + ".png")
				print("Output at: " + output_file)
				self.output_image.save_render(output_file)
				
				self.cancel(context)

				if self.set_overlay_material == True and self.replace_overlay_material == False:
					bpy.ops.timer.progress(output_image_name="Overlay", set_overlay_material=True, replace_overlay_material=True)

				self.report({"INFO"}, "Finished rendering: %s" % (self.output_image_name))
				return {'FINISHED'}

		
			self.has_render_finished = True


		if len(self.action_entries) > 0:
			context.scene.spritesheet_render_progress = round(self.current_total_frames / self.total_frames * 100.0)

		return {'RUNNING_MODAL'}

	def cancel(self, context):
		bpy.context.scene.render.resolution_x = self.base_x
		bpy.context.scene.render.resolution_y = self.base_y
		bpy.context.scene.render.use_border = False
		bpy.context.scene.render.use_crop_to_border = False
		bpy.context.scene.camera = self.default_camera
		self.reset_ortho_scale()
		self.reset_camera_shift()

		if self.current_action_index < len(self.action_entries):
			current_action : MetaData.ActionMetaData = self.action_entries[self.current_action_index]
			if current_action.find_material_name != "" and current_action.replace_material != None:
				ResetMaterialReplacementByName(self.replacement_materials, current_action.find_material_name, current_action.replace_material)
				
		if len(self.replacement_materials) > 0:
			ResetOverlayMaterials(self.replacement_materials)

		if self.output_image:
			bpy.data.images.remove(self.output_image)

		wm = context.window_manager
		wm.event_timer_remove(self._timer)
		context.scene.is_rendering_spritesheet = False
		self.has_been_cancelled = True

preview_active = False

class PREVIEW_OT(bpy.types.Operator):
	"""Operator that is responsible for an action preview"""
	bl_idname = "preview.action"
	bl_label = "Action Preview"

	_timer = None

	materials_to_replace = []
	search_name = ""
	replacement_material = None

	framestart = 1
	frameend = 16
	currentframe = 1

	base_x = 16
	base_y = 20

	default_camera = None

	default_camera_zoom = {}
	default_camera_shift_x = 0
	default_camera_shift_y = 0

	current_action_entry = None

	def prepare_preview(self):
		action_entry = bpy.context.scene.animlist[bpy.context.scene.action_meta_data_index]

		self.framestart = bpy.context.scene.frame_start
		self.frameend = bpy.context.scene.frame_end
		self.currentframe = bpy.context.scene.frame_current
		self.base_x = bpy.context.scene.render.resolution_x
		self.base_y = bpy.context.scene.render.resolution_y
		self.default_camera = bpy.context.scene.camera
		action_camera = get_action_camera(action_entry)
		self.default_camera_shift_x = action_camera.data.shift_x
		self.default_camera_shift_y = action_camera.data.shift_y
		self.default_camera_zoom = AdjustOrthoScale(action_entry)

		prepare_action(action_entry)


		if action_entry.find_material_name != "" and action_entry.replace_material != None:
			self.materials_to_replace = GetMaterialsToReplace()
			self.search_name = action_entry.find_material_name
			self.replacement_material = action_entry.replace_material
			ReplaceMaterialWithName(self.materials_to_replace, self.search_name, self.replacement_material)

		bpy.ops.screen.animation_cancel()
		bpy.ops.screen.animation_play()
		global preview_active
		preview_active = True
		self.current_action_entry = action_entry

	def execute(self, context):
		context.window_manager.modal_handler_add(self)

		self.prepare_preview()
		
		return {'RUNNING_MODAL'}

	def reset_ortho_scale(self):
		for camera, default_ortho_scale in self.default_camera_zoom.items():
			camera.data.ortho_scale = default_ortho_scale
		
		self.default_camera_zoom.clear()

	def reset(self):
		if self.search_name != "" and self.replacement_material != None:
			ResetMaterialReplacementByName(self.materials_to_replace, self.search_name, self.replacement_material)
			
		bpy.ops.screen.animation_cancel()
		
		global preview_active
		preview_active = False
		bpy.context.scene.frame_start = self.framestart
		bpy.context.scene.frame_end = self.frameend
		bpy.context.scene.frame_current = self.currentframe
		bpy.context.scene.render.resolution_x = self.base_x
		bpy.context.scene.render.resolution_y = self.base_y
		bpy.context.scene.render.use_border = False
		bpy.context.scene.render.use_crop_to_border = False
		bpy.context.scene.camera.data.shift_x = self.default_camera_shift_x
		bpy.context.scene.camera.data.shift_y = self.default_camera_shift_y
		bpy.context.scene.camera = self.default_camera
		self.reset_ortho_scale()

		self.current_action_entry = None

	def modal(self, context, event):
		if event.type in {"LEFT_ARROW", "RIGHT_ARROW", "UP_ARROW", "DOWN_ARROW"} and event.value == "PRESS":
			if event.shift:
				if event.type in {"LEFT_ARROW"}:
					self.current_action_entry.camera_shift_x += 1
				if event.type in {"RIGHT_ARROW"}:
					self.current_action_entry.camera_shift_x -= 1
				if event.type in {"UP_ARROW"}:
					self.current_action_entry.camera_shift_y -= 1
				if event.type in {"DOWN_ARROW"}:
					self.current_action_entry.camera_shift_y += 1

				self.current_action_entry.override_camera_shift = True
			else:

				if event.type in {"LEFT_ARROW"}:
					self.current_action_entry.width -= 1
				if event.type in {"RIGHT_ARROW"}:
					self.current_action_entry.width += 1
				if event.type in {"UP_ARROW"}:
					self.current_action_entry.height += 1
				if event.type in {"DOWN_ARROW"}:
					self.current_action_entry.height -= 1

				self.current_action_entry.override_resolution = True
				

			bpy.context.scene.camera.data.show_passepartout = True
			bpy.context.scene.camera.data.passepartout_alpha = 0.6

			self.reset()
			self.prepare_preview()

			


		if event.type in {"RIGHTMOUSE", "ESC", "LEFTMOUSE"}:
			self.reset()
			return {'FINISHED'}

		return {'RUNNING_MODAL'}

	
