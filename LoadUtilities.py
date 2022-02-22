#--------------------------
# Load Utilities
# 11.02.2022
#--------------------------
# Robin Hohnsbeen (Ryou)

import bpy
from bpy.props import StringProperty, BoolProperty

from bpy_extras.io_utils import ImportHelper
from pathlib import Path
import os
from . import AnimPort
from . import MeshPort
from . import MetaData

script_file = os.path.realpath(__file__)
AddonDir = os.path.dirname(script_file)

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
		
	if tool1 and tool2:
		new_collection = bpy.data.collections.new(name=animdata["Action"].name + "_tools")
		new_collection.objects.link(tool1)
		new_collection.objects.link(tool2)
		action_entry.additional_object_enum = "2_Collection"
		action_entry.additional_collection = new_collection
	elif tool1:
		action_entry.additional_object_enum = "1_Object"
		action_entry.additional_object = tool1
	elif tool2:
		action_entry.additional_object_enum = "1_Object"
		action_entry.additional_object = tool2


def ImportActList(path, animfiles, meshfiles, target):
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

				new_entry : MetaData.ActionMetaData = bpy.context.scene.animlist.add()
				new_entry.action = anim_data["Action"]
				if bpy.context.scene.render.resolution_x != anim_data["Width"] or bpy.context.scene.render.resolution_y != anim_data["Height"]:
					new_entry.override_resolution = True
				new_entry.height = anim_data["Height"]
				new_entry.width = anim_data["Width"]
				new_entry.max_frames = anim_data["Length"]

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
	bl_label = "Import Animation (.anim)"

	filter_glob: StringProperty(default="*.anim", options={"HIDDEN"})
	
	force_import_action: BoolProperty(name="Force action import", default=False, description="Import action although there is an action with the same name in blender")

	def execute(self, context):
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

			if anim_data.get("ERROR"):
				self.report({"ERROR"}, f"" + anim_data["ERROR"])
				return {"CANCELLED"}

		else:
			print(self.filepath + " is no Animation!")

		context.scene.lastfilepath = self.filepath
		return {'FINISHED'}



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