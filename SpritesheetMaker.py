#--------------------------
# SpritesheetMaker: Used to pack several renders together in one spritesheet using NumPy.
# 11.02.2022
#--------------------------
# Robin Hohnsbeen (Ryou)

import math
import bpy
import mathutils
import numpy as np
import os
from enum import Enum
from pathlib import Path

from . import MetaData
from . import AnimPort


def GetOutputPath():
	save_path = bpy.path.abspath("/tmp")
	if bpy.data.is_saved:
		save_path = os.path.dirname(bpy.data.filepath)
	return os.path.join(save_path, "output_render")

def get_res_multiplier():
	return bpy.context.scene.render.resolution_percentage / 100.0

def get_sprite_width(action_entry):
	x_res_sprite = bpy.context.scene.render.resolution_x
	
	if action_entry.override_resolution:
		x_res_sprite = action_entry.width

	return x_res_sprite

def get_sprite_height(action_entry):
	y_res_sprite = bpy.context.scene.render.resolution_y
	
	if action_entry.override_resolution:
		y_res_sprite = action_entry.height

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
		"Name" : action_entry.action.name,
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
	pictures = []
	for action_entry in action_entries:
		if action_entry.render_type_enum == "Picture": # Will be placed later
			pictures.append(action_entry)
			continue

		sheetstrip_height = get_sheet_strip_height(action_entry, get_scaled=False)
		sheetstrip_width = get_sheet_strip_width(action_entry, get_scaled=False)
		
		if current_x_position > sheet_width - sheetstrip_width or last_height < sheetstrip_height and last_height != 0:
			rows.append({"x_remaining" : sheet_width - current_x_position, "row_height" : row_height})
			current_x_position = 0
			current_y_position += last_height
			row_height = 0
		
		sheet_strips[action_entry.action.name] = GetSpriteStripInfo(action_entry, current_x_position, current_y_position)
		
		current_x_position += sheetstrip_width
		action_index += 1
		last_height = sheetstrip_height

		if sheetstrip_height > row_height:
			row_height = sheetstrip_height
	
	###
	sheet_height = current_y_position + last_height
	rows.append({"x_remaining" : sheet_width - current_x_position, "row_height" : row_height})

	# Place pictures
	for picture in pictures:
		sprite_height = get_sprite_height(picture)
		sprite_width = get_sprite_width(picture)

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
					sheet_strips[picture.action.name] = GetSpriteStripInfo(picture, x_begin, y_begin)
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
			strip_info = GetSpriteStripInfo(picture, x_begin, y_begin)
			sheet_strips[picture.action.name] = strip_info
			
			sheet_height += strip_info["Height"]
			rows.append({"x_remaining" : strip_info["Width"], "row_height" : strip_info["Height"]})
			

	return int(sheet_width * get_res_multiplier()), int(sheet_height * get_res_multiplier()), sheet_strips

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

	return visible_objects

def reset_object(object):
	object.location = [0, 0, 0]
	if object.rotation_mode == "QUATERNION":
		object.rotation_quaternion = [1.0, 0, 0, 0]
	else:
		object.rotation_euler = [0, 0, 0]
	object.scale =  [1.0, 1.0, 1.0]

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

	for object in bpy.data.objects:
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

	bpy.context.scene.anim_target.animation_data.action = action_entry.action

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

def GetValidActionEntries():
	valid_action_entries = []
	for action_index, action_entry in enumerate(bpy.context.scene.animlist):
		if action_entry.action == None:
			print("Action " + str(action_index) + " omitted, because no blender action was referenced.")
			continue

		valid_action_entries.append(action_entry)

	return valid_action_entries

def CanWriteFile(path):
	if os.path.exists(path):
		if os.path.isfile(path):
			return os.access(path, os.W_OK)
		else:
			return False

def CanReadFile(path):
	return os.access(path, os.R_OK)

def DoesActmapExist():
	path = os.path.join(GetOutputPath(), "ActMap.txt") 
	return os.path.exists(path)

def DoesDefCoreExist():
	path = os.path.join(GetOutputPath(), "DefCore.txt") 
	return os.path.exists(path)

def ReadIni(filepath):
	file_content = []

	file = None
	if os.path.exists(filepath):
		try:
			# opening the file in read mode
			file = open(filepath, "r")
			lines = file.readlines()
			current_section_index = -1
			
			for line in lines:
				if line == "\n":
					continue
				
				line = line.strip()
				
				if line.startswith("["):
					section_content = {}
					section_content["SectionName"] = line
					current_section_index += 1
					file_content.append(section_content)
				
				elif current_section_index > -1:
					section_content = file_content[current_section_index]
					name_and_values = line.split("=", 1)
					section_content[name_and_values[0].strip()] = name_and_values[1].strip()
					file_content[current_section_index] = section_content

			path = Path(filepath)
			print("Finished reading " + path.name)
		
		except:
			print("There is no file at path " + filepath)

		finally:
			if file:
				file.close()
			
	return file_content

def PrintIni(filepath, file_content):
	file = None
	try:
		file = open(filepath, "w")
		
		for section_content in file_content:
			for entry_key in section_content:
				entry = section_content[entry_key]
				if entry_key == "SectionName":
					file.write(entry + "\n")
				else:
					file.write(entry_key + "=" + entry + "\n")
			
			file.write("\n")

		path = Path(filepath)
		print("Finished writing " + path.name)

	except:
		print("Could not open file at " + filepath)

	finally:
		if file:
			file.close()
		

def PrintActmap(path, sprite_strips, valid_action_entries):
	actmap_path = os.path.join(path, "ActMap.txt")
	
	# Get old actmap data
	file_content = []
	if os.path.exists(actmap_path):
		if CanReadFile(actmap_path) == False or CanWriteFile(actmap_path) == False:
			return "ERROR", "Need read/write permissions at output path. Aborted."
		file_content = ReadIni(actmap_path)
	else:
		print("No old Actmap.txt found. Creating new..")

	# Prepare output content
	output_content = []
	for action_entry in valid_action_entries:
		if action_entry.render_type_enum == "Picture":
			continue
		action_name = action_entry.action.name
		found_entry = False
		for content_section in file_content:
			if content_section["Name"] == action_name: # This also filters entries, that are not used.
				output_content.append(content_section)
				found_entry = True
				break
		
		if found_entry == False:
			content_section = {}
			content_section["SectionName"] = "[Action]"
			content_section["Name"] = action_name
			output_content.append(content_section)

	# Update content
	for action_entry in valid_action_entries:
		if action_entry.render_type_enum == "Picture":
			continue
		action_name = action_entry.action.name
		for content_section_index in range(len(output_content)):
			if output_content[content_section_index]["Name"] == action_name:

				output_content[content_section_index]["Length"] =  str(sprite_strips[action_name]["Length"])

				x_pos = str(sprite_strips[action_name]["X_pos"])
				y_pos = str(sprite_strips[action_name]["Y_pos"])
				sprite_width = str(sprite_strips[action_name]["Sprite_Width"])
				sprite_height = str(sprite_strips[action_name]["Sprite_Height"])
				output_content[content_section_index]["Facet"] = x_pos + "," + y_pos + "," + sprite_width + "," + sprite_height

	# Save content
	PrintIni(actmap_path, output_content)
	return "INFO", "Exported ActMap.txt"

def PrintDefCore(path, sprite_strips, valid_action_entries):
	defcore_path = os.path.join(path, "DefCore.txt")
	
	# Get old defcore data
	file_content = []
	if os.path.exists(defcore_path):
		if CanReadFile(defcore_path) == False or CanWriteFile(defcore_path) == False:
			return "ERROR", "Need read/write permissions at output path. Aborted."
		file_content = ReadIni(defcore_path)
	else:
		print("No old DefCore.txt found. Creating new..")

	

	# Prepare output content
	output_content = []
	if len(file_content) == 0:
		content_section = {"SectionName" : "[DefCore]"}
		output_content.append(content_section)
	else:
		for content_section in file_content:
			output_content.append(content_section)

	# Update content
	content_section = output_content[0] # DefCore section
	content_section["Width"] = str(bpy.context.scene.render.resolution_x)
	content_section["Height"] = str(bpy.context.scene.render.resolution_y)
	x_offset = -math.floor(bpy.context.scene.render.resolution_x / 2.0)
	y_offset = -math.floor(bpy.context.scene.render.resolution_y / 2.0)
	content_section["Offset"] = str(x_offset) + "," + str(y_offset)

	picture = {
		"x" : str(0), 
		"y" : str(0), 
		"w" : str(math.floor(bpy.context.scene.render.resolution_x*get_res_multiplier())), 
		"h" : str(math.floor(bpy.context.scene.render.resolution_y*get_res_multiplier()))}
	for action_entry in valid_action_entries:
		if action_entry.render_type_enum == "Picture":
			strip = sprite_strips[action_entry.action.name]
			picture["x"] = str(math.floor(strip["X_pos"]*get_res_multiplier()))
			picture["y"] = str(math.floor(strip["Y_pos"]*get_res_multiplier()))
			picture["w"] = str(math.floor(strip["Sprite_Width"]*get_res_multiplier()))
			picture["h"] = str(math.floor(strip["Sprite_Height"]*get_res_multiplier()))
			break

	content_section["Picture"] = picture["x"] + "," + picture["y"] + "," + picture["w"] + "," + picture["h"]

	if content_section.get("Scale"):
		content_section.pop("Scale")
	if bpy.context.scene.render.resolution_percentage != 100:
		content_section["Scale"] = str(bpy.context.scene.render.resolution_percentage)

	# Save content
	PrintIni(defcore_path, output_content)
	return "INFO", "Exported DefCore.txt"


current_action_name = ""
current_sheet_number = 1
current_max_sheets = 1

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
	output_image : bpy.types.Image
	output_directorypath : str

	base_x = 16
	base_y = 20
	current_action_index : bpy.props.IntProperty("CurrentActionIndex", default=0)
	current_frame_number = 0

	render_state = 0
	total_frames = 1
	current_total_frames = 0

	has_been_cancelled = False

	def execute(self, context):
		wm = context.window_manager
		self._timer = wm.event_timer_add(0.005, window=context.window)
		wm.modal_handler_add(self)

		# Prepare Data
		self.action_entries = GetValidActionEntries()
		self.has_render_finished = True
		self.sheet_width, self.sheet_height, self.sprite_strips = GetSpritesheetInfo(self.action_entries)
		self.output_image_data = np.zeros((self.sheet_height, self.sheet_width, 4), 'f')
		self.output_image = bpy.data.images.new(self.output_image_name, width=self.sheet_width, height=self.sheet_height)
		print("Spritesheetdimensions: " + str(self.sheet_width) + "x" + str(self.sheet_height))

		self.replacement_materials = GetMaterialsToReplace()

		# Prepare Path
		self.output_directorypath = GetOutputPath()
		if context.scene.custom_output_dir != "":
			self.output_directorypath = bpy.path.abspath(context.scene.custom_output_dir)
			if not os.path.exists(self.output_directorypath):
				self.cancel(context)
				self.report({"ERROR"}, "Custom Directory not found.")
				return {'RUNNING_MODAL'}
		else:
			self.output_directorypath = os.path.join(self.output_directorypath, "spritesheets")

		image_output_path = os.path.join(self.output_directorypath, self.output_image_name + ".png")
		print("Output" + image_output_path)
		if os.path.exists(image_output_path):
			if CanReadFile(image_output_path) == False or CanWriteFile(image_output_path) == False:
				self.cancel(context)
				self.report({"ERROR"}, "Need read/write permissions at output path. Aborted.")
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
		

		self.base_x = bpy.context.scene.render.resolution_x
		self.base_y = bpy.context.scene.render.resolution_y

		self.render_state = 0
		self.current_action_index = 0
		self.current_frame_number = 0

		context.scene.is_rendering_spritesheet = True

		self.total_frames = 0
		for entry in self.action_entries:
			self.total_frames += entry.max_frames


		return {'RUNNING_MODAL'}


	def modal(self, context: bpy.types.Context, event: bpy.types.Event):
		if event.type in {'ESC'} or self.has_been_cancelled:
			self.cancel(context)
			return {'CANCELLED'}

		if event.type == "TIMER" and self.has_render_finished:
			self.has_render_finished = False
			
			# Prepare for new action strip
			if self.render_state == 0:
				print("Sheetwidth " + str(self.sheet_width))

				current_action = self.action_entries[self.current_action_index]
				prepare_action(current_action)
				if current_action.find_material_name != "" and current_action.replace_material != None:
					ReplaceMaterialWithName(self.replacement_materials, current_action.find_material_name, current_action.replace_material)

				sheetstrip_width = get_sheet_strip_width(current_action)
				sheetstrip_height = get_sheet_strip_height(current_action)
				self.strip_image_data = np.zeros((sheetstrip_height, sheetstrip_width, 4), 'f')

				self.render_state = 1
				self.current_frame_number = 0
				global current_action_name
				current_action_name = current_action.action.name


			# Render one sprite of sprite strip
			if self.render_state == 1:
				current_action = self.action_entries[self.current_action_index]
				
				if current_action.render_type_enum != "Picture":
					bpy.context.scene.frame_current = self.current_frame_number + current_action.start_frame
				output_filepath = os.path.join(GetOutputPath(), "sprites", current_action.action.name + "_" + str(bpy.context.scene.frame_current))
				
				x_dim, y_dim = get_current_render_dimensions(current_action)
				bpy.context.scene.render.resolution_x = x_dim
				bpy.context.scene.render.resolution_y = y_dim
				bpy.context.scene.render.filepath = output_filepath
				bpy.ops.render.render(write_still=True)
				bpy.context.scene.render.resolution_x = self.base_x
				bpy.context.scene.render.resolution_y = self.base_y
				rendered_sprite_image = bpy.data.images.load(output_filepath + ".png")
				
				# Allocate a numpy array to manipulate pixel data.
				sprite_width = math.floor(get_sprite_width(current_action) * get_res_multiplier())
				sprite_height = math.floor(get_sprite_height(current_action) * get_res_multiplier())
				sprite_pixel_data = np.zeros((sprite_height, sprite_width, 4), 'f')
				# Fast copy of pixel data from bpy.data to numpy array.
				rendered_sprite_image.pixels.foreach_get(sprite_pixel_data.ravel())

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
				sprite_strip = self.sprite_strips[current_action.action.name]

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
		if self.current_action_index < len(self.action_entries):
			current_action : MetaData.ActionMetaData = self.action_entries[self.current_action_index]
			if current_action.find_material_name != "" and current_action.replace_material != None:
				ResetMaterialReplacementByName(self.replacement_materials, current_action.find_material_name, current_action.replace_material)
				
		if self.set_overlay_material and len(self.replacement_materials) > 0:
			ResetOverlayMaterials(self.replacement_materials)

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

	def execute(self, context):
		context.window_manager.modal_handler_add(self)
		action_entry = bpy.context.scene.animlist[bpy.context.scene.action_meta_data_index]

		self.framestart = bpy.context.scene.frame_start
		self.frameend = bpy.context.scene.frame_end
		self.currentframe = bpy.context.scene.frame_current

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
		return {'RUNNING_MODAL'}

	def modal(self, context, event):
		if event.type in {"RIGHTMOUSE", "ESC", "LEFTMOUSE"}:
			if self.search_name != "" and self.replacement_material != None:
				ResetMaterialReplacementByName(self.materials_to_replace, self.search_name, self.replacement_material)
			
			bpy.ops.screen.animation_cancel()
			
			global preview_active
			preview_active = False
			bpy.context.scene.frame_start = self.framestart
			bpy.context.scene.frame_end = self.frameend
			bpy.context.scene.frame_current = self.currentframe

			return {'FINISHED'}

		return {'RUNNING_MODAL'}
