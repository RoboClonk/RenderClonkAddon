#--------------------------
# Animation Exporter / Importer
# 12.09.2007
#--------------------------
# Richard Gerum (Randrian)
#--------------------------
# API Upgrade 11.02.2022
# Robin Hohnsbeen (Ryou)

from enum import Enum
import bpy
import os.path
import glob
import os

from . import MetaData

class anim_import_state(Enum):
	UNDEFINED = -1
	DATA = 0
	ACTION = 1

class pose_import_state(Enum):
	UNDEFINED = -1
	BONENAME = 0
	FRAME = 1
	LOCATION = 2
	ROTATION = 3
	SCALE = 4
	
def get_anim_import_state(line):
	key = line[0:-1]

	if key == "[DATA]":
		return anim_import_state.DATA
	elif key == "[Vertices]":
		return anim_import_state.ACTION
	else:
		return anim_import_state.UNDEFINED

def ResetArmature(armature : bpy.types.Armature):
	for bone in armature.bones:
		bone.location = [0, 0, 0]
		if bone.rotation_mode == "QUATERNION":
			bone.rotation_quaternion = [1.0, 0, 0, 0]
		else:
			bone.rotation_euler = [0, 0, 0]
		bone.scale =  [1.0, 1.0, 1.0]


def LoadAction(path, animation_target, force_import_action=False):
	splitpath = str.split(path, os.sep)
	(filename, extension) = os.path.splitext(splitpath[len(splitpath)-1])

	anim_data = {}
	if animation_target == None:
		raise UnboundLocalError("Animation Target is None!")
	
	if os.path.exists(path) == False:
		raise FileNotFoundError("No valid action file at: " + path)

	print("Import Action " + str(filename))

	actions = bpy.data.actions
	current_action = 0
	old_action_found = False
	
	if actions.find(filename) > -1:
		current_action = actions[filename]
		old_action_found = True

	if not current_action:
		current_action = actions.new(name=filename)
		current_action.use_fake_user = True

	armature_ob = animation_target
	
	
	armature_ob.animation_data.action = current_action
	anim_data["Action"] = current_action
	
	pose = armature_ob.pose
	bones = pose.bones


	file = open(path, "r")
	lines = file.readlines()
	
	current_bone_name = ""
	current_frame = 0
	current_pose_import_state = pose_import_state.BONENAME

	mode = anim_import_state.DATA
	for line in lines:
		line = line.strip().replace("\n", "")
		if line == "[Data]":
			mode = anim_import_state.DATA

		elif line == "[Action]":
			if old_action_found and force_import_action == False:
				return anim_data

			mode = anim_import_state.ACTION
			
		elif mode == anim_import_state.DATA:
			line = line.split("=")
			param_name, param_value = line[0], line[1].replace("\n", "")
			
			if param_name == "Width" or param_name == "Height" or param_name == "Length":
				anim_data[param_name] = int(param_value)
			#Tools..
			else:
				anim_data[param_name] = param_value

		elif mode == anim_import_state.ACTION:
			if line[0] == "[":
				current_frame = int(line.replace("[", "").replace("]", ""))
				current_pose_import_state = pose_import_state.LOCATION

			elif current_pose_import_state == pose_import_state.BONENAME:
				current_bone_name = line.replace(":", "").replace("\n", "")
				mapping = MetaData.get_vgroup_mapping(current_bone_name)
				if mapping:
					current_bone_name = mapping
				
				current_pose_import_state = pose_import_state.LOCATION

				# TODO: Add bone not found exception
				if bones[current_bone_name] == -1:
					print(current_bone_name + " does not exist on armature \"" + armature_ob.name + "\".")
			
			elif current_pose_import_state == pose_import_state.LOCATION:
				location = line.split(" ")
				bones[current_bone_name].location = [float(location[0]), float(location[1]), float(location[2])]
				bones[current_bone_name].keyframe_insert(data_path = "location", frame=current_frame)
				
				current_pose_import_state = pose_import_state.ROTATION

			elif current_pose_import_state == pose_import_state.ROTATION:
				rotation = line.split(" ")
				if len(rotation) == 3:
					bones[current_bone_name].rotation_euler = [float(rotation[0]), float(rotation[1]), float(rotation[2])]
					bones[current_bone_name].keyframe_insert(data_path = "rotation_euler", frame=current_frame)
				elif len(rotation) == 4:
					bones[current_bone_name].rotation_quaternion = [float(rotation[0]), float(rotation[1]), float(rotation[2]), float(rotation[3])]
					bones[current_bone_name].keyframe_insert(data_path = "rotation_quaternion", frame=current_frame)

				current_pose_import_state = pose_import_state.SCALE

			elif current_pose_import_state == pose_import_state.SCALE:
				scale = line.split(" ")
				bones[current_bone_name].scale =  [float(scale[0]), float(scale[1]), float(scale[2])]
				bones[current_bone_name].keyframe_insert(data_path = "scale", frame=current_frame)

				# In case the next line doesn't start with "[", there will be a new bone pose.
				current_pose_import_state = pose_import_state.BONENAME
		
	file.close()

	# So we get the meta data about the animation as well.
	return anim_data


