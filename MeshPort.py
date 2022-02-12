#--------------------------
# Mesh Porter
# 12.09.2007
#--------------------------
# Richard Gerum (Randrian)
#--------------------------
# API Upgrade 11.02.2022
# Robin Hohnsbeen (Ryou)

import bpy
import os.path
import glob
import os
from bpy import *
import sys
from enum import Enum
from pathlib import Path

from . import MetaDatas

def ReadFloatList(string):
	x = 0
	y = 0
	list = []
	for c in string:
		if c == " " or c == "\n":
			list.append(float(string[y:x]))
			y = x
		x += 1
	if y == x+1:
		list.append(float(string[y:x]))
	return list

def ReadIntList(string):
	x = 0
	y = 0
	list = []
	for c in string:
		if c == " " or c == "\n":
			if string[y:x] != " ":
				list.append(int(string[y:x]))
			y = x
		x += 1
	if y == x+1:
		list.append(int(string[y:x]))
	return list

class mesh_import_state(Enum):
	EMPTY = 0
	VERTICES = 1
	FACES = 2
	VGROUPS = 3
	FACEMATS = 4
	MATERIALS = 5
	UVCOORDS = 6
	TEXTURES = 7
	OBJECT = 8
	MODIFIERS = 9

def get_mesh_import_state(line):
	key = line[0:-1]

	if key == "[Object]":
		return mesh_import_state.OBJECT, "Loading Object"
	elif key == "[Vertices]":
		return mesh_import_state.VERTICES, "Loading Vertices"

	elif key == "[Faces]":
		return mesh_import_state.FACES, "Loading Faces"

	elif key == "[VGroups]":
		return mesh_import_state.VGROUPS, "Loading Vertex Groups"

	elif key == "[UVCoords]":
		return mesh_import_state.UVCOORDS, "Assigning UV Coordinates"

	elif key == "[Material]":
		return mesh_import_state.MATERIALS, "Loading Materials"
	
	elif key == "[FaceMats]":
		return mesh_import_state.FACEMATS, "Linking Faces to Materials"

	elif key == "[Texture]":
		return mesh_import_state.TEXTURES, "Loading Textures"

	return mesh_import_state.EMPTY, "Undefined"

	# war elif # TODO:
	if line[0:-1] == "[Modifier]":
		loadtext = "Loading Modifiers"
		mode = 9
	else: mode = 0

def GetParameters(line):
	name_and_values = line.split("=")
	return name_and_values[0], name_and_values[1].split(",")

def lock_object(object, is_locked=True):
	object.lock_location = [is_locked, is_locked, is_locked]
	if len(object.lock_rotation) == 3:
		object.lock_rotation = [is_locked, is_locked, is_locked]
	else:
		object.lock_rotation = [is_locked, is_locked, is_locked, is_locked]
	object.lock_scale =  [is_locked, is_locked, is_locked]

def import_mesh(path, insert_collection=None):
	meshpath = Path(path)
	print('Importing "' + path + '"')
	filename = meshpath.stem

	if os.path.exists(path) == False:
		raise FileNotFoundError("No valid mesh file at: " + path)


	file = meshpath.open() # Loading a .mesh file
	tex = 0

	mode = 0

	lines = file.readlines()

	verts = []
	faces = []
	new_mesh = bpy.data.meshes.new(filename + "_mesh")
	new_object = bpy.data.objects.new(filename, new_mesh)
	faceloop_index = 0 # This is used to measure at what UV index we are. It depends on the number of vertices per face we checked.
	current_mat_name = ""

	# TODO: Progressbar
	for line in lines:
		if line[0] == "[":
			
			last_mode = mode
			mode, loadtext = get_mesh_import_state(line)

			if last_mode == mesh_import_state.FACES and mode != mesh_import_state.FACES:
				new_mesh.from_pydata(verts, [], faces)
				new_object.data.uv_layers.new()


		else:
			if mode == mesh_import_state.OBJECT:
				param_name, values = GetParameters(line)
				if param_name == "Loc":
					new_object.location = [float(values[0]), float(values[1]), float(values[2])]
				if param_name == "Rot":
					if len(values) == 3:
						new_object.rotation_euler = [float(values[0]), float(values[1]), float(values[2])]
					elif len(values) == 4:
						new_object.rotation_quaternion = [float(values[0]), float(values[1]), float(values[2]), float(values[4])]
				if param_name == "Size":
					new_object.scale = [float(values[0]), float(values[1]), float(values[2])]

				if param_name == "Mode":
					#mesh.mode = int(values[0])
					# Unfortunately, I don't know what this is used for. It could refer to Object Modes, but we don't really have to store/load them.
					pass

			if mode == mesh_import_state.VERTICES:
				verts.append(ReadFloatList(line))
				
			if mode == mesh_import_state.FACES:
				faces.append(ReadIntList(line))

			if mode == mesh_import_state.VGROUPS:
				if line != "\n":
					if line[-2] == ":":
						group_name = line[0:-2]

						mapping = MetaDatas.get_vgroup_mapping(group_name)
						if mapping:
							group_name = mapping

						new_object.vertex_groups.new(name=group_name)
					else:
						new_object.vertex_groups.active.add(ReadIntList(line), 1.0, "REPLACE")
			
			if mode == mesh_import_state.UVCOORDS:
				coordinates = line.split("=")[1]
				UVs = coordinates.split(",")
				
				for index in range(0, len(UVs), 2):
					new_mesh.uv_layers.active.data[faceloop_index].uv = [float(UVs[index]), float(UVs[index+1])]
					faceloop_index += 1

			if mode == mesh_import_state.MATERIALS:
				param_name, values = GetParameters(line)
				if param_name == "Name":

					current_mat_name = values[0][0:-1]
					mat : bpy.types.Material = None
					if bpy.data.materials.find(current_mat_name) > -1:
						mat = bpy.data.materials[current_mat_name]
					else:
						mat = bpy.data.materials.new(name=current_mat_name)
					
					current_mat_name = mat.name
					new_object.data.materials.append(mat)

					mat.use_nodes = True
					
				elif param_name == "Color":
					bpy.data.materials.get(current_mat_name).node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = [float(values[0]), float(values[1]), float(values[2]), 1.0]

				elif param_name == "Ref":
					bpy.data.materials.get(current_mat_name).node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 1.0 - float(values[0])

				elif param_name == "Spec":
					bpy.data.materials.get(current_mat_name).node_tree.nodes['Principled BSDF'].inputs['Specular'].default_value = float(values[0])

				elif param_name == "Hardness":
					# Legacy from Blender 2.7
					# 'convert' to roughness which is somewhat the opposite.
					hardness = float(int(values[0]))/100.0
					bpy.data.materials.get(current_mat_name).node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 1.0 - max(min(hardness, 1.0), 0.0)

			# For new shader values
				elif param_name == "Metallic":
					bpy.data.materials.get(current_mat_name).node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value = float(values[0])
				
				elif param_name == "Roughness":
					bpy.data.materials.get(current_mat_name).node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = float(values[0])
				
				elif param_name == "Emission_Strength":
					bpy.data.materials.get(current_mat_name).node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = float(values[0])

				elif param_name == "Emission_Color":
					bpy.data.materials.get(current_mat_name).node_tree.nodes['Principled BSDF'].inputs['Emission'].default_value = [float(values[0]), float(values[1]), float(values[2]), 1.0]

				elif param_name == "Subsurface_Color":
					bpy.data.materials.get(current_mat_name).node_tree.nodes['Principled BSDF'].inputs['Subsurface Color'].default_value = [float(values[0]), float(values[1]), float(values[2]), 1.0]

				elif param_name == "Subsurface_Strength":
					bpy.data.materials.get(current_mat_name).node_tree.nodes['Principled BSDF'].inputs['Subsurface'].default_value = float(values[0])

			if mode == mesh_import_state.FACEMATS: 
				list =  ReadIntList(line)
				list_index = 0
				for material_index in list:
					new_object.data.polygons[list_index].material_index = material_index
					list_index += 1

			if mode == mesh_import_state.TEXTURES:
				param_name, values = GetParameters(line)

				if param_name == "Name":
					tex = bpy.data.textures.find(values[0])
					if tex is None:
						tex = bpy.data.textures.new(values[0])

				if param_name == "Image":
					current_material = bpy.data.materials.get(current_mat_name)
					node_tree = current_material.node_tree
					texture_node = node_tree.nodes.new("ShaderNodeTexImage")
					
					node_tree.links.new(node_tree.nodes['Principled BSDF'].inputs['Base Color'], texture_node.outputs['Color'])

					tex_file_name = values[0].split("/")
					searching_path = os.path.join(os.path.dirname(path) , "**" , tex_file_name[len(tex_file_name)-1].replace("\n", ""))
					paths_to_image = glob.glob(searching_path)
					
					if len(paths_to_image) > 0:
						img = bpy.data.images.load(paths_to_image[0])
						texture_node.image = img
					else:
						print("Texture " + tex_file_name[len(tex_file_name)-1] + " was not found. Searched recursively for " + searching_path)

				if param_name == "Type":
					# Could be added, if needed.
					#tex.setType(values[0])
					pass

				if param_name == "Texco":
					# This is usually just UVCoordinates which is the default
					#texco = values[0]
					pass


			# TODO: Load Modifiers

			if mode == mesh_import_state.MODIFIERS:
				param_name, values = GetParameters(line)
				print("Loading modifiers is not supported yet. " + str(values[0]))
				continue
				if ReadParameter(line,0,0) == "Type":
					tex = ob.modifiers.append(ReadParameter(line,1,2))
				if ReadParameter(line,0,0) == "Height":
					tex[Modifier.Settings.HEIGHT] = ReadParameter(line,1,1)


	if len(new_object.vertex_groups) == 0 and MetaDatas.get_vgroup_mapping(new_object.name):
		new_object.vertex_groups.new(name=MetaDatas.get_vgroup_mapping(new_object.name))
		new_object.vertex_groups.active.add(range(len(new_object.data.vertices)), 1.0, "REPLACE")

	# Default: Add to scene collection
	if insert_collection == None:
		bpy.context.view_layer.layer_collection.collection.objects.link(new_object)
	else:
		insert_collection.objects.link(new_object)
	# Select and make active
	bpy.context.view_layer.objects.active = new_object
	new_object.select_set(True)
	bpy.ops.object.shade_smooth()

	file.close()

	return new_object
