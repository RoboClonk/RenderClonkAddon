#--------------------------
# Clonk Port
# 11.02.2022
#--------------------------
# Robin Hohnsbeen (Ryou)

import bpy
from bpy.props import StringProperty, BoolProperty

import math
import glob # for wildcard directory search

from bpy_extras.io_utils import ImportHelper
from pathlib import Path
import os
from . import AnimPort
from . import MeshPort
from . import MetaData
from . import PathUtilities
from . import IniPort
from . import SpritesheetMaker

script_file = os.path.realpath(__file__)
AddonDir = os.path.dirname(script_file)

found_meshes = []
found_actions = []
found_actionlists = []
last_search_path = ""

def get_res_multiplier():
	return bpy.context.scene.render.resolution_percentage / 100.0

def content_glob_search(path):
	global found_meshes
	global found_actions
	global found_actionlists

	found_meshes += glob.glob(os.path.join(path, "*.mesh"), recursive=False)
	found_actions += glob.glob(os.path.join(path, "*.anim"), recursive=False)
	found_actionlists += glob.glob(os.path.join(path, "*.act"), recursive=False)

def collect_clonk_content_files(path):
	global last_search_path
	if last_search_path == path:
		return

	global found_meshes
	global found_actions
	global found_actionlists
	found_meshes.clear()
	found_actions.clear()
	found_actionlists.clear()
	path = str(path)
	# Note: This does not use recursion, because it might use an inordinate amount of time on large directories.
	content_glob_search(path)
	searching_path = os.path.join(path , "**")
	content_glob_search(searching_path)

	print("Looking for Data.." + path)

def _ImportExtraMesh(meshname, meshfiles):
	if bpy.data.objects.find(meshname) > -1:
		return bpy.data.objects[meshname]
	
	for meshfilespath in meshfiles:
		meshfile = Path(meshfilespath)
		if meshfile.stem == meshname:
			new_object = import_mesh_and_parent_to_rig(meshfilespath, reuse_rig=True)
			MeshPort.lock_object(new_object, True)
			return new_object

	return None

def _ImportToolsIfAny(action_entry, animdata, meshfiles):
	tool1: bpy.types.Object = None
	tool2: bpy.types.Object = None
	if animdata.get("Tool1"):
		tool1 = _ImportExtraMesh(animdata["Tool1"], meshfiles)
	if animdata.get("Tool2"):
		tool2 = _ImportExtraMesh(animdata["Tool2"], meshfiles)
	
	if action_entry == None:
		return

	if tool1 and tool2:
		new_collection = bpy.data.collections.new(name=animdata["Action"].name + "_tools")
		new_collection.objects.link(tool1)
		new_collection.objects.link(tool2)
		bpy.context.scene.collection.children.link(new_collection)
		action_entry.additional_object_enum = "2_Collection"
		action_entry.additional_collection = new_collection
	elif tool1:
		action_entry.additional_object_enum = "1_Object"
		action_entry.additional_object = tool1
	elif tool2:
		action_entry.additional_object_enum = "1_Object"
		action_entry.additional_object = tool2

def ImportActList(path, animfiles, meshfiles, target, create_entry, import_tools):
	print("Read act " + path)
	file = open(path, "r")
	lines = file.readlines()

	is_reading_actions = False

	print("Looking in " + str(len(animfiles)) + " animfiles")

	animations_not_found = []
	for line in lines:
		line = line.replace("\n", "")
		if line == "[Actions]":
			is_reading_actions = True
			continue

		if is_reading_actions == False:
			continue

		found_animation = False
		for animfilepath in animfiles:
			animpath = Path(animfilepath)

			if animpath.stem == line:
				anim_data = AnimPort.LoadAction(animfilepath, target)

				new_entry = None
				if create_entry:
					new_entry = MetaData.MakeActionEntry(anim_data)
				if import_tools:
					_ImportToolsIfAny(new_entry, anim_data, meshfiles)
				
				found_animation = True
				break

		if found_animation == False:
			animations_not_found.append(line)

	file.close()

	if len(animations_not_found) > 0:
		missing_actions = ""
		for animation in animations_not_found:
			missing_actions += animation + ", "
		return "WARNING", "Could not find actions: %s" % [missing_actions]
	else:
		return "INFO", "Imported all actions from act file."

# ActMap.txt
def ImportActMap(path, animfiles, meshfiles, target):
	print("Read actmap " + path)
	file = open(path, "r")
	actmap = IniPort.Read(path)
	
	print("Looking in " + str(len(animfiles)) + " animfiles")

	# TODO: Filter animations
	actions = []

	animations_not_found = []
	for action in actions:
		found_animation = False
		for animfilepath in animfiles:
			animpath = Path(animfilepath)

			if animpath.stem == action:
				anim_data = AnimPort.LoadAction(animfilepath, target)

				new_entry = MetaData.MakeActionEntry(anim_data)
				_ImportToolsIfAny(new_entry, anim_data, meshfiles)
				
				found_animation = True
				break

		if found_animation == False:
			animations_not_found.append(action)

	file.close()

	if len(animations_not_found) > 0:
		missing_actions = ""
		for animation in animations_not_found:
			missing_actions += animation + ", "
		return "WARNING", "Could not find actions: %s" % [missing_actions]
	else:
		return "INFO", "Imported all actions from ActMap."

def AppendRenderClonkSetup():
	global AddonDir
	dir = Path(AddonDir)
	bpy.ops.wm.append(
		filepath="RenderClonk.blend",
		directory=str(Path.joinpath(dir, "RenderClonk.blend", "Collection")),
		filename="RenderClonk"
		)

def GetOrAppendOverlayMaterials():
	global AddonDir
	dir = Path(AddonDir)

	if bpy.data.materials.find("Overlay") == -1:
		bpy.ops.wm.append(
		filepath="RenderClonk.blend",
		directory=str(Path.joinpath(dir, "RenderClonk.blend", "Material")),
		filename="Overlay"
		)
	if bpy.data.materials.find("Holdout") == -1:
		bpy.ops.wm.append(
		filepath="RenderClonk.blend",
		directory=str(Path.joinpath(dir, "RenderClonk.blend", "Material")),
		filename="Holdout"
		)
	if bpy.data.materials.find("Fill") == -1:
		bpy.ops.wm.append(
		filepath="RenderClonk.blend",
		directory=str(Path.joinpath(dir, "RenderClonk.blend", "Material")),
		filename="Fill"
		)
	
	return bpy.data.materials["Overlay"], bpy.data.materials["Holdout"], bpy.data.materials["Fill"]

def GetOrAppendClonkRig(ReuseOld=True):
	rig_index = bpy.data.objects.find("ClonkRig")
	if rig_index == -1 or ReuseOld == False:
		global AddonDir
		dir = Path(AddonDir)
		bpy.ops.wm.append(
			filepath="RenderClonk.blend",
			directory=str(Path.joinpath(dir, "RenderClonk.blend", "Collection")),
			filename="ClonkRig"
			)

	for child in bpy.data.objects['ClonkRig'].children:
		if child.type == "CAMERA":
			bpy.context.scene.camera = child

	return bpy.data.objects['ClonkRig']

def import_mesh_and_parent_to_rig(path, reuse_rig, insert_collection=None):
	clonk_rig = GetOrAppendClonkRig(reuse_rig)
	
	clonk_object = MeshPort.import_mesh(path, insert_collection)

	clonk_object.parent = clonk_rig
	clonk_object.matrix_parent_inverse = clonk_rig.matrix_world.inverted()
	clonk_object.modifiers.new(name="ClonkRig", type="ARMATURE")
	clonk_object.modifiers["ClonkRig"].object = clonk_rig

	return clonk_object

class OT_MeshFilebrowser(bpy.types.Operator, ImportHelper):
	bl_idname = "mesh.open_filebrowser"
	bl_label = "Import Clonk (.mesh)"

	filter_glob: StringProperty(default="*.mesh", options={"HIDDEN"})

	parent_to_clonk_rig: BoolProperty(name="Parent to Clonk Rig", default=True, description="This will parent the mesh to the clonk rig and apply an Armature Modifier")
	reuse_clonk_rig: BoolProperty(name="Reuse Clonk Rig", default=True, description="Whether an existing clonk rig should be used or a new one created")

	def execute(self, context):
		"""Do something with the selected file(s)."""
		print(self.filepath)

		extension = Path(self.filepath).suffix
		if extension == ".mesh":
			if self.parent_to_clonk_rig:
				collection : bpy.types.Collection = None
				if bpy.context.scene.always_rendered_objects != None:
					collection = bpy.context.scene.always_rendered_objects
				clonk_object = import_mesh_and_parent_to_rig(self.filepath, self.reuse_clonk_rig, collection)
			else:
				clonk_object = MeshPort.import_mesh(self.filepath)

			MeshPort.lock_object(clonk_object, True)
				
		else:
			print(self.filepath + " is no Clonk mesh!")

		context.scene.lastfilepath = self.filepath
		return {'FINISHED'}

class OT_AnimFilebrowser(bpy.types.Operator, ImportHelper):
	bl_idname = "anim.open_filebrowser"
	bl_label = "Import Action (.anim)"

	filter_glob: StringProperty(default="*.anim", options={"HIDDEN"})
	
	force_import_action: BoolProperty(name="Force action import", default=False, description="Import action although there is an action with the same name in blender")
	create_action_entry: BoolProperty(name="Create Action Entry", default=True, description="Create an entry in the actions list")
	import_tool_mesh: BoolProperty(name="Import Tool Mesh", default=True, description="Import tool meshes if the action references any")

	def execute(self, context):
		parent_path = Path(self.filepath).parents[1]
		collect_clonk_content_files(parent_path)
		global found_meshes

		print(self.filepath)

		extension = Path(self.filepath).suffix
		if extension == ".anim":
			global AddonDir
			clonk_rig = GetOrAppendClonkRig(True)
			if clonk_rig == None:
				self.report({"ERROR"}, f"ClonkRig not found.")
				print("ClonkRig not found")
				return {"CANCELLED"}

			anim_data = AnimPort.LoadAction(self.filepath, clonk_rig, self.force_import_action)
			new_entry = None
			if self.create_action_entry:
				new_entry = MetaData.MakeActionEntry(anim_data)
			if self.import_tool_mesh:
				_ImportToolsIfAny(new_entry, anim_data, found_meshes)

			if anim_data.get("ERROR"):
				self.report({"ERROR"}, f"" + anim_data["ERROR"])
				return {"CANCELLED"}

		else:
			print(self.filepath + " is no Animation!")

		context.scene.lastfilepath = self.filepath
		return {'FINISHED'}

class OT_ActListFilebrowser(bpy.types.Operator, ImportHelper):
	bl_idname = "act.open_filebrowser"
	bl_label = "Import Actionlist (.act)"

	filter_glob: StringProperty(default="*.act", options={"HIDDEN"})
	create_action_entry: BoolProperty(name="Create Action Entries", default=True, description="Create entries in the actions list")
	import_tool_mesh: BoolProperty(name="Import Tool Meshes", default=True, description="Import tool meshes if the actions reference any")


	def execute(self, context):
		parent_path = Path(self.filepath).parents[1]
		collect_clonk_content_files(parent_path)
		print(self.filepath)

		extension = Path(self.filepath).suffix
		if extension == ".act":
			global found_actions
			global found_meshes
			clonk_rig = GetOrAppendClonkRig()
			bpy.context.scene.anim_target = clonk_rig
			if bpy.data.collections.find("ClonkRig") == -1:
				raise AssertionError("No Collection named ClonkRig found.")
			bpy.context.scene.always_rendered_objects = bpy.data.collections["ClonkRig"]
			reporttype, message = ImportActList(self.filepath, found_actions, found_meshes, bpy.context.scene.anim_target, self.create_action_entry, self.import_tool_mesh)


			self.report({reporttype}, "%s" % [message])

		else:
			print(self.filepath + " is no Actionlist!")

		context.scene.lastfilepath = self.filepath
		return {"FINISHED"}

class OT_ActMapFilebrowser(bpy.types.Operator, ImportHelper):
	bl_idname = "actmap.open_filebrowser"
	bl_label = "Import ActMap.txt"

	filter_glob: StringProperty(default="ActMap.txt", options={"HIDDEN"})
	
	force_import_action: BoolProperty(name="Force action import", default=False, description="Import action although there is an action with the same name in blender")

	def execute(self, context):
		parent_path = Path(self.filepath).parents[1]
		collect_clonk_content_files(parent_path)
		print(self.filepath)

		extension = Path(self.filepath).name
		if extension == "ActMap.txt":
			global found_actions
			clonk_rig = GetOrAppendClonkRig()
			bpy.context.scene.anim_target = clonk_rig
			if bpy.data.collections.find("ClonkRig") == -1:
				raise AssertionError("No Collection named ClonkRig found.")
			bpy.context.scene.always_rendered_objects = bpy.data.collections["ClonkRig"]

			if len(found_actions) == 0:
				self.report({"ERROR"}, "Your ActMap.txt needs to be in the same folder (or neighboring folders) as your .anim files.")
				return {"CANCELLED"}

			reporttype, message = ImportActList(self.filepath, found_actions, found_meshes, bpy.context.scene.anim_target)

			self.report({reporttype}, "%s" % [message])

		else:
			print(self.filepath + " is no ActMap!")

		context.scene.lastfilepath = self.filepath
		return {"FINISHED"}

def DoesActmapExist():
	path = os.path.join(PathUtilities.GetOutputPath(), "ActMap.txt") 
	return os.path.exists(path)

def DoesDefCoreExist():
	path = os.path.join(PathUtilities.GetOutputPath(), "DefCore.txt") 
	return os.path.exists(path)
	

def PrintActmap(path, remove_unused_sections=False):
	valid_action_entries = MetaData.GetValidActionEntries()

	messagetype, message = MetaData.CheckIfActionListIsValid(valid_action_entries)

	if messagetype == "ERROR":
		return messagetype, message
	
	sheet_width, sheet_height, sprite_strips = SpritesheetMaker.GetSpritesheetInfo(valid_action_entries)
	actmap_path = os.path.join(path, "ActMap.txt")
	
	# Get old actmap data
	file_content = []
	if os.path.exists(actmap_path):
		if PathUtilities.CanReadFile(actmap_path) == False or PathUtilities.CanWriteFile(actmap_path) == False:
			return "ERROR", "Need read/write permissions at output path. Aborted."
		file_content = IniPort.Read(actmap_path)
	else:
		print("No old Actmap.txt found. Creating new..")

	# What section in the file is listed explicitly in the addon?
	remaining_action_entries = valid_action_entries.copy()
	remaining_file_content = file_content.copy()
	section_descriptions = []
	for action_entry in valid_action_entries:
		for content_section in file_content:
			if content_section["Name"] == MetaData.GetActionName(action_entry):
				section_descriptions.append({"Action" : action_entry, "FullCopy" : True, "Section" : content_section})
				remaining_action_entries.remove(action_entry)
				remaining_file_content.remove(content_section)
				break
	
	# What file section is related to what action but not explicitly listed in the addon?
	omitted_sections = remaining_file_content.copy()
	copied_descriptions = section_descriptions.copy()
	for section_index, section_description in enumerate(section_descriptions):
		for content_section in remaining_file_content:	
			if content_section["Facet"] == section_description["Section"]["Facet"]:
				new_description = {"Action" : section_description["Action"], "FullCopy" : False, "Section" : content_section}
				# Put it always after the related description
				insertion_index = copied_descriptions.index(section_description)
				copied_descriptions.insert(insertion_index+1, new_description) # Insert checks array bounds for us.
				omitted_sections.remove(content_section)
					
	section_descriptions = copied_descriptions

	
	# What remaining actions are not listed in the file? -> Create new sections
	for action_entry in remaining_action_entries:
		# But omit pictures .. 
		if action_entry.render_type_enum == "Picture":
			continue

		content_section = {}
		content_section["SectionName"] = "[Action]"
		section_descriptions.append({"Action" : action_entry, "FullCopy" : True, "Section" : content_section})


	# Update content
	output_content = []
	for section_description in section_descriptions:
		content_section = section_description["Section"]
		reference_action = section_description["Action"]
		
		sprite_strip = sprite_strips[MetaData.GetActionName(reference_action)]

		if section_description["FullCopy"]:
			content_section["Name"] = MetaData.GetActionName(reference_action)
			content_section["Length"] =  str(sprite_strip["Length"])

		x_pos = str(sprite_strip["X_pos"])
		y_pos = str(sprite_strip["Y_pos"])
		sprite_width = str(sprite_strip["Sprite_Width"])
		sprite_height = str(sprite_strip["Sprite_Height"])
		content_section["Facet"] = x_pos + "," + y_pos + "," + sprite_width + "," + sprite_height

		output_content.append(content_section)


	if remove_unused_sections == False:
		output_content = output_content + omitted_sections

	unmatched_actions = ""
	for section in omitted_sections:
		unmatched_actions += section["Name"] + ", "

	# Save content
	IniPort.Write(actmap_path, output_content)
	if len(unmatched_actions) > 0:
		return "WARNING", "Exported ActMap.txt but some actions couldn't be matched: %s. You can create entries for it in the action list and export the ActMap again." % [unmatched_actions]
	else:
		return "INFO", "Exported ActMap.txt"


def PrintDefCore(path):
	valid_action_entries = MetaData.GetValidActionEntries()
	sheet_width, sheet_height, sprite_strips = SpritesheetMaker.GetSpritesheetInfo(valid_action_entries)

	defcore_path = os.path.join(path, "DefCore.txt")
	
	# Get old defcore data
	file_content = []
	if os.path.exists(defcore_path):
		if PathUtilities.CanReadFile(defcore_path) == False or PathUtilities.CanWriteFile(defcore_path) == False:
			return "ERROR", "Need read/write permissions at output path. Aborted."
		file_content = IniPort.Read(defcore_path)
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
			strip = sprite_strips[MetaData.GetActionName(action_entry)]
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
	IniPort.Write(defcore_path, output_content)
	return "INFO", "Exported DefCore.txt"

def SetOptimalRenderingSettings():
	bpy.context.scene.has_applied_rendersettings = True

	bpy.context.scene.render.engine = "CYCLES"
	bpy.context.scene.cycles.device = "GPU"
	bpy.context.scene.render.film_transparent = True
	#bpy.context.scene.cycles.pixel_filter_type = "BOX"
	bpy.context.scene.cycles.pixel_filter_type = "GAUSSIAN"
	bpy.context.scene.cycles.filter_width = 1.5
	bpy.context.scene.display_settings.display_device = "sRGB"
	bpy.context.scene.view_settings.view_transform = "Standard"
	if bpy.context.scene.render.resolution_x == 1920:
		bpy.context.scene.render.resolution_x = 16
		bpy.context.scene.render.resolution_y = 20

	bpy.context.scene.render.image_settings.compression = 0
	bpy.context.scene.cycles.use_denoising = False
	bpy.context.scene.cycles.caustics_reflective = False
	bpy.context.scene.cycles.caustics_refractive = False
	bpy.context.scene.cycles.max_bounces = 1
	bpy.context.scene.cycles.diffuse_bounces = 0
	bpy.context.scene.cycles.glossy_bounces = 1
	bpy.context.scene.render.use_persistent_data = True
	bpy.context.scene.cycles.samples = 1024
	bpy.context.scene.render.image_settings.compression = 0
	bpy.context.scene.render.fps = 15

	Overlay, Holdout, Fill = GetOrAppendOverlayMaterials()

	bpy.context.scene.spritesheet_settings.overlay_material = Overlay
	bpy.context.scene.spritesheet_settings.fill_material = Fill