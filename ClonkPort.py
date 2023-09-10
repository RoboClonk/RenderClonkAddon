# --------------------------
# Clonk Port
# 11.02.2022
# --------------------------
# Robin Hohnsbeen (Ryou)

from operator import mod
import bpy
from bpy.props import StringProperty, BoolProperty, IntProperty

import math
import glob  # for wildcard directory search

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

    found_meshes += glob.glob(os.path.join(path, "*.mesh*"), recursive=False)
    found_actions += glob.glob(os.path.join(path, "*.anim*"), recursive=False)
    found_actionlists += glob.glob(os.path.join(path,
                                   "*.act"), recursive=False)


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
    searching_path = os.path.join(path, "**")
    content_glob_search(searching_path)

    print("Looking for Data.." + path)


def _ImportExtraMesh(meshname, meshfiles):
    if bpy.data.objects.find(meshname) > -1:
        return [bpy.data.objects[meshname]]

    for meshfilespath in meshfiles:
        meshfile = Path(meshfilespath)
        if meshfile.stem == meshname:
            clonk_objects = MeshPort.import_mesh(meshfilespath)
            new_objects = reuse_rigs_and_parent_objects(
                clonk_objects, reuse_rig=True)

            return new_objects

    return []


def _ImportToolsIfAnyLegacy(action_entry, animdata, meshfiles):
    tool1 = []
    tool2 = []
    if animdata.get("Tool1"):
        tool1 = _ImportExtraMesh(animdata["Tool1"], meshfiles)
    if animdata.get("Tool2"):
        tool2 = _ImportExtraMesh(animdata["Tool2"], meshfiles)

    if action_entry == None:
        return

    if len(tool1) > 0 or len(tool2) > 0:
        if len(tool1) + len(tool2) > 1:
            new_collection = bpy.data.collections.new(
                name=animdata["Action"].name + "_tools")
            for tool in tool1:
                new_collection.objects.link(tool)
            for tool in tool2:
                new_collection.objects.link(tool)
            bpy.context.scene.collection.children.link(new_collection)
            action_entry.additional_object_enum = "2_Collection"
            action_entry.additional_collection = new_collection
        elif len(tool1) > 0:
            action_entry.additional_object_enum = "1_Object"
            action_entry.additional_object = tool1[0]
        elif len(tool2) > 0:
            action_entry.additional_object_enum = "1_Object"
            action_entry.additional_object = tool2[0]


def LoadAction(path, animation_target, force_import_action=False, import_tools=True):
    if ".animblend" in path or ".anim.blend" in path:

        with bpy.data.libraries.load(path) as (data_from, data_to):
            data_to.scenes = data_from.scenes

        new_entry = bpy.context.scene.animlist.add()

        for key, value in data_to.scenes[0].animlist[0].items():
            new_entry[key] = value

        tool_objects, collection = MetaData.get_action_entry_tools(new_entry)

        # These objects get implicitly imported when they are referenced inside an anim blend file.
        if import_tools:
            if collection:
                bpy.context.view_layer.layer_collection.collection.children.link(collection)
            elif len(tool_objects) == 1:
                bpy.context.view_layer.layer_collection.collection.objects.link(tool_objects[0])

            MetaData.replace_duplicate_materials(tool_objects)
            reuse_rigs_and_parent_objects(tool_objects, True)

        # Remove them again
        else:
            for tool in tool_objects:
                if tool:
                    if tool.type == "MESH":
                        for material_slot in tool.material_slots:
                            if material_slot.material:
                                bpy.data.materials.remove(material_slot.material)

                    bpy.data.objects.remove(tool)
                    if collection:
                        bpy.data.collections.remove(collection)

        bpy.data.scenes.remove(data_to.scenes[0])

        return None


    else:
        return AnimPort.LoadActionLegacy(path, animation_target, force_import_action)


def get_animfilemap(animfiles):
    animfilemap = {}
    for animfilepath in animfiles:
        animpath = Path(animfilepath)

        # Prioritize blend files
        if animpath.stem in animfilemap and "blend" not in animpath.suffix:
            pass
        else:
            animfilemap[animpath.stem] = animfilepath

    return animfilemap


def ImportActList(path, animfiles, meshfiles, target, create_entry, import_tools):
    print("Read act " + path)
    file = open(path, "r")
    lines = file.readlines()

    is_reading_actions = False

    print("Looking in " + str(len(animfiles)) + " animfiles")

    animfilemap = get_animfilemap(animfiles)

    animations_not_found = []
    for line in lines:
        line = line.replace("\n", "")
        if line == "[Actions]":
            is_reading_actions = True
            continue

        if is_reading_actions == False:
            continue

        if animfilemap.get(line) != None:
            anim_data = LoadAction(animfilemap[line], target, import_tools=import_tools)

            if anim_data: # Legacy import
                new_entry = None
                if create_entry:
                    new_entry = MetaData.MakeActionEntry(anim_data)
                if import_tools:
                    _ImportToolsIfAnyLegacy(new_entry, anim_data, meshfiles)

        else:
            animations_not_found.append(line)

    file.close()

    if len(animations_not_found) > 0:
        missing_actions = ""
        for animation in animations_not_found:
            missing_actions += animation + ", "
        return "WARNING", "Could not find actions: %s" % (missing_actions)
    else:
        return "INFO", "Imported all actions from act file."


# ActMap.txt
def ImportActMap(path, animfiles, meshfiles, target, create_entry, import_tools):
    print("Read actmap " + path)
    file = open(path, "r")
    actmap, messagetype, message = IniPort.Read(path)
    if messagetype == "ERROR":
        return messagetype, message

    print("Looking in " + str(len(animfiles)) + " animfiles")

    animfilemap = get_animfilemap(animfiles)

    animations_not_found = []
    for section in actmap:
        action = section["Name"]

        if animfilemap.get(action) != None:
            anim_data = LoadAction(animfilemap[action], target, import_tools=import_tools)

            if anim_data: # Legacy import
                new_entry = None
                if create_entry:
                    new_entry = MetaData.MakeActionEntry(anim_data)
                if import_tools:
                    _ImportToolsIfAnyLegacy(new_entry, anim_data, meshfiles)

        else:
            animations_not_found.append(action)

    file.close()
    if len(actmap) == len(animations_not_found):
        return "WARNING", "No actions could be found."
    elif len(animations_not_found) > 0:
        missing_actions = ""
        for animation in animations_not_found:
            missing_actions += animation + ", "
        return "INFO", "Imported %d actions, omitted: %s" % (len(actmap) - len(animations_not_found), missing_actions)
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
            directory=str(Path.joinpath(
                dir, "RenderClonk.blend", "Collection")),
            filename="ClonkRig"
        )

    for child in bpy.data.objects['ClonkRig'].children:
        if child.type == "CAMERA":
            bpy.context.scene.camera = child

    return bpy.data.objects['ClonkRig']


def GetOrAppendCamSetup(ReuseOld=True):
    collection_index = bpy.data.collections.find("CamSetup")
    if collection_index == -1 or ReuseOld == False:
        global AddonDir
        dir = Path(AddonDir)
        bpy.ops.wm.append(
            filepath="RenderClonk.blend",
            directory=str(Path.joinpath(
                dir, "RenderClonk.blend", "Collection")),
            filename="CamSetup"
        )

    return bpy.data.collections['CamSetup']

def are_armatures_equal(first, second) -> bool:
    if first is None or second is None:
        print("Can't compare armatures. One of them is None!")

    if len(first.data.bones) != len(second.data.bones):
        return False
    
    maching_names = 0
    for bone_first in first.data.bones:
        for bone_second in second.data.bones:
            if bone_first.name == bone_second.name:
                maching_names += 1
                break

    return maching_names == len(first.data.bones)
   

def get_armature_modifier(in_object):
    for modifier in in_object.modifiers:
        if modifier.type == "ARMATURE":
            return modifier
        
def parent_objects_to_rig(in_objects, rig):
    for clonk_object in in_objects:
        if clonk_object is None:
            continue
        if clonk_object.type == "ARMATURE":
            continue
        if clonk_object.parent and clonk_object.parent.type != "ARMATURE":
            continue # Ignore objects that are parented to other objects. So we don't destroy normal object parenting.

        clonk_object.parent = rig
        clonk_object.matrix_parent_inverse = rig.matrix_world.inverted()
        if clonk_object.parent_type == "BONE":
            continue

        armature_modifier = get_armature_modifier(clonk_object)
        if armature_modifier is None:
            armature_modifier = clonk_object.modifiers.new(
                name="ClonkRig", type="ARMATURE")
        armature_modifier.object = rig

def get_anim_target_armatures():
    armatures = []
    for anim_target in MetaData.get_anim_targets():
        if anim_target is None:
            continue
        if anim_target.type == "ARMATURE":
            armatures.append(anim_target)

    return armatures

def reuse_rigs_and_parent_objects(in_objects, reuse_rig, insert_collection=None):
    # On import there is the posibility to import armatures as well. There could even be several armatures that are linked to individual objects.
    # Furthermore, we usually want wo reuse the rigs we have, since the imported rig might be identical to the clonk rig (or other rigs in the scene already)
    # So we compare the imported rigs with the ones available and then decide what rigs to keep.
    clonk_rig = GetOrAppendClonkRig(reuse_rig)

    objects_without_rig = []
    armatures_to_object = {}

    # Sort objects by armature
    # Find out what objects aren't attached to armatures
    for clonk_object in in_objects:
        if clonk_object is None:
            continue

        if clonk_object.type == "ARMATURE":
            continue

        armature_modifier = get_armature_modifier(clonk_object)
        if (armature_modifier and armature_modifier.object) or (clonk_object.parent and clonk_object.parent.type == "ARMATURE" and clonk_object.parent_type == "BONE"):
            parent_armature = None
            if armature_modifier:
                parent_armature = armature_modifier.object
            else:
                parent_armature = clonk_object.parent
            
            if parent_armature in armatures_to_object:
                armatures_to_object[parent_armature].append(clonk_object)
            else:
                armatures_to_object[parent_armature] = [clonk_object]
        else:
            objects_without_rig.append(clonk_object)

    unused_armatures = set()
    for imported_armature in armatures_to_object.keys():
        if imported_armature is None:
            continue

        anim_targets = get_anim_target_armatures()
        if len(anim_targets) > 0:
            found_matching_anim_target = False
            for anim_target in anim_targets:
                if are_armatures_equal(anim_target, imported_armature):
                    objects_with_armature = armatures_to_object[imported_armature]
                    parent_objects_to_rig(objects_with_armature, anim_target)
                    unused_armatures.add(imported_armature)
                    found_matching_anim_target = True
                    print(f"Armature {anim_target.name} is equal to {imported_armature.name}. Removing imported armature.")
                    break

            if found_matching_anim_target == False:
                anim_target_collection = bpy.context.scene.anim_target_collection
                if anim_target_collection is None:
                    anim_target_collection = bpy.data.collections.new("AnimTargets")
                    bpy.context.scene.anim_target_collection = anim_target_collection
                    bpy.context.view_layer.layer_collection.collection.children.link(anim_target_collection)

                if bpy.context.scene.anim_target is not None:
                    anim_target_collection.objects.link(bpy.context.scene.anim_target)

                if bpy.context.scene.anim_target_enum == "1_Object":
                    bpy.context.scene.anim_target_enum = "2_Collection"

                anim_target_collection.objects.link(imported_armature)

    for unused_armature in unused_armatures:
        if unused_armature in in_objects:
            in_objects.remove(unused_armature)
        bpy.data.objects.remove(unused_armature)

    parent_objects_to_rig(objects_without_rig, clonk_rig)

    return in_objects


class OT_MeshFilebrowser(bpy.types.Operator, ImportHelper):
    bl_idname = "mesh.open_filebrowser"
    bl_label = "Import Mesh (.mesh/blend)"

    filter_glob: StringProperty(default="*.mesh*", options={"HIDDEN"})

    parent_to_clonk_rig: BoolProperty(name="Parent to Clonk Rig", default=True,
                                      description="This will parent the mesh to the clonk rig and apply an Armature Modifier")
    reuse_clonk_rig: BoolProperty(name="Reuse Clonk Rig", default=True,
                                  description="Whether an existing clonk rig should be used or a new one created")

    def execute(self, context):
        print(self.filepath)

        if ".mesh" in self.filepath:
            if self.parent_to_clonk_rig:
                collection: bpy.types.Collection = None
                if bpy.context.scene.always_rendered_objects != None:
                    collection = bpy.context.scene.always_rendered_objects
                clonk_objects = MeshPort.import_mesh(self.filepath, collection)
                clonk_objects = reuse_rigs_and_parent_objects(
                    clonk_objects, self.reuse_clonk_rig)
            else:
                clonk_objects = MeshPort.import_mesh(self.filepath)

        else:
            print(self.filepath + " is no Clonk mesh!")

        context.scene.lastfilepath = self.filepath
        return {'FINISHED'}


def GetSelectedObjects(context):
    active_object = None
    out_objects = []

    if context.active_object is not None and context.active_object.type != "ARMATURE":
        active_object = context.active_object

    for selected_object in context.selected_objects:
        if selected_object.type != "ARMATURE":
            out_objects.append(selected_object)

    return out_objects, active_object


class OT_MeshExport(bpy.types.Operator):
    bl_idname = "mesh.export"
    bl_label = "Export Clonk/Tool (.mesh)"

    @classmethod
    def poll(cls, context):
        preferences = context.preferences
        addon_prefs = preferences.addons["RenderClonkAddon"].preferences

        if addon_prefs.content_folder == "" or os.path.exists(addon_prefs.content_folder) == False:
            return False

        mesh_objects, active_mesh_object = GetSelectedObjects(context)

        return active_mesh_object is not None

    # TODO: Open filebrowser
    def execute(self, context):
        preferences = context.preferences
        addon_prefs = preferences.addons["RenderClonkAddon"].preferences

        mesh_objects, active_mesh_object = GetSelectedObjects(context)

        export_scene = bpy.data.scenes.new(
            name=f"Export_{active_mesh_object.name}")
        export_collection = bpy.data.collections.new(
            name=active_mesh_object.name)
        try:

            export_scene.view_layers[0].layer_collection.collection.children.link(
                export_collection)
            for mesh_object in mesh_objects:
                if mesh_object.animation_data is not None:
                    mesh_object.animation_data.action = None # We don't want to export other animations
                export_collection.objects.link(mesh_object)

            export_collection.asset_mark()

            data_blocks = set()
            data_blocks.add(export_scene)
            meshes_path = os.path.join(addon_prefs.content_folder, "Meshes")
            if os.path.exists(meshes_path) == False:
                os.mkdir(meshes_path)

            export_path = os.path.join(
                meshes_path, f"{active_mesh_object.name}.meshblend")

            bpy.data.libraries.write(export_path, data_blocks, fake_user=True)
            self.report(
                {"INFO"}, f"Exported mesh \'{active_mesh_object.name}\' successfully to \'{meshes_path}\'")

        except BaseException as Err:
            self.report({"ERROR"}, f"{Err}")
            return {"CANCELLED"}

        finally:
            bpy.data.collections.remove(export_collection)
            bpy.data.scenes.remove(export_scene)

        return {'FINISHED'}


class OT_AnimFilebrowser(bpy.types.Operator, ImportHelper):
    bl_idname = "anim.open_filebrowser"
    bl_label = "Import Action (.anim/.animblend)"

    filter_glob: StringProperty(default="*.anim*", options={"HIDDEN"})

    force_import_action: BoolProperty(name="Force action import", default=False,
                                      description="Import action although there is an action with the same name in blender")
    import_tools: BoolProperty(name="Import Tool Objects", default=True,
                                   description="Import tool objects if the action references any")

    def execute(self, context):
        parent_path = Path(self.filepath).parents[1]
        collect_clonk_content_files(parent_path)
        global found_meshes

        print(self.filepath)

        if ".anim" in self.filepath:
            clonk_rig = GetOrAppendClonkRig(True)
            if clonk_rig == None:
                self.report({"ERROR"}, f"ClonkRig not found.")
                print("ClonkRig not found")
                return {"CANCELLED"}

            anim_data = LoadAction(
                self.filepath, clonk_rig, self.force_import_action, import_tools=self.import_tools)
            
            if anim_data: # Legacy import
                new_entry = MetaData.MakeActionEntry(anim_data)
                if self.import_tools:
                    _ImportToolsIfAnyLegacy(new_entry, anim_data, found_meshes)

                if anim_data.get("ERROR"):
                    self.report({"ERROR"}, f"" + anim_data["ERROR"])
                    return {"CANCELLED"}

        else:
            print(self.filepath + " is no Animation!")

        context.scene.lastfilepath = self.filepath
        return {'FINISHED'}


class OT_AnimExport(bpy.types.Operator):
    bl_idname = "anim.export"
    bl_label = "Export action (.animblend)"

    @classmethod
    def poll(cls, context):
        preferences = context.preferences
        addon_prefs = preferences.addons["RenderClonkAddon"].preferences

        if addon_prefs.content_folder == "" or os.path.exists(addon_prefs.content_folder) == False:
            return False

        action_name = MetaData.GetActionNameFromIndex(
            bpy.context.scene.action_meta_data_index)

        if action_name == "":
            return False

        return True

    def execute(self, context):
        preferences = context.preferences
        addon_prefs = preferences.addons["RenderClonkAddon"].preferences

        action_name = MetaData.GetActionNameFromIndex(
            context.scene.action_meta_data_index)
        if action_name == "":
            self.report({"ERROR"}, "No valid action entry selected.")
            return {"CANCELLED"}

        export_scene = bpy.data.scenes.new(
            name=f"Export_{action_name}")
        export_collection = bpy.data.collections.new(
            name=action_name)

        try:
            export_scene.view_layers[0].layer_collection.collection.children.link(
                export_collection)

            new_entry = export_scene.animlist.add()
            selected_entry = context.scene.action_meta_data_index

            for key, value in context.scene.animlist[selected_entry].items():
                print(str(key))
                new_entry[key] = value

            data_blocks = set()
            data_blocks.add(export_scene)
            actions_path = os.path.join(addon_prefs.content_folder, "Actions")
            if os.path.exists(actions_path) == False:
                os.mkdir(actions_path)

            export_path = os.path.join(
                actions_path, f"{action_name}.animblend")

            bpy.data.libraries.write(export_path, data_blocks, fake_user=True)
            self.report(
                {"INFO"}, f"Exported action \'{action_name}\' successfully to \'{export_path}\'")

        except BaseException as Err:
            self.report({"ERROR"}, f"{Err}")
            return {"CANCELLED"}

        finally:
            bpy.data.collections.remove(export_collection)
            bpy.data.scenes.remove(export_scene)

        return {'FINISHED'}


class OT_PictureFilebrowser(bpy.types.Operator, ImportHelper):
    bl_idname = "picture.open_filebrowser"
    bl_label = "Load image"

    filter_glob: StringProperty(default="*.png")

    load_overlay_image: BoolProperty(
        name="Image To Load", default=False, description="")

    def execute(self, context):
        parent_path = Path(self.filepath).parents[1]

        print(self.filepath)

        extension = Path(self.filepath).suffix
        if extension == ".png":
            global AddonDir
            try:
                scene = bpy.context.scene
                loaded_image = bpy.data.images.load(self.filepath)
                anim_entry = scene.animlist[scene.action_meta_data_index]

                if self.load_overlay_image:
                    anim_entry.image_for_picture_overlay = loaded_image
                else:
                    anim_entry.image_for_picture_combined = loaded_image

                for region in context.area.regions:
                    if region.type == "UI":
                        region.tag_redraw()

            except BaseException as Err:
                self.report({"ERROR"}, f"{Err}")
                return {"CANCELLED"}
        else:
            self.report({"ERROR"}, f"{self.filepath} is no png!")
            return {"CANCELLED"}

        context.scene.lastfilepath = self.filepath
        return {'FINISHED'}


class OT_ActListFilebrowser(bpy.types.Operator, ImportHelper):
    bl_idname = "act.open_filebrowser"
    bl_label = "Import Actionlist (.act)"

    filter_glob: StringProperty(default="*.act", options={"HIDDEN"})
    create_action_entry: BoolProperty(
        name="Create Action Entries", default=True, description="Create entries in the actions list")
    import_tool_mesh: BoolProperty(name="Import Tool Meshes", default=True,
                                   description="Import tool meshes if the actions reference any")

    def draw(self, context):
        layout = self.layout

        layout.label(text="An action list (.act) contains names of actions")

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
            reporttype, message = ImportActList(self.filepath, found_actions, found_meshes,
                                                bpy.context.scene.anim_target, self.create_action_entry, self.import_tool_mesh)

            self.report({reporttype}, "%s" % (message))

        else:
            print(self.filepath + " is no Actionlist!")

        context.scene.lastfilepath = self.filepath
        return {"FINISHED"}


class OT_ActMapFilebrowser(bpy.types.Operator, ImportHelper):
    bl_idname = "actmap.open_filebrowser"
    bl_label = "Import ActMap.txt"

    filter_glob: StringProperty(default="*.txt", options={"HIDDEN"})

    force_import_action: BoolProperty(name="Force action import", default=False,
                                      description="Import action although there is an action with the same name in blender")
    create_action_entry: BoolProperty(
        name="Create Action Entries", default=True, description="Create entries in the actions list")
    import_tool_mesh: BoolProperty(name="Import Tool Meshes", default=True,
                                   description="Import tool meshes if the actions reference any")

    def execute(self, context):
        extension = Path(self.filepath).name
        if "actmap" in extension.lower():
            parent_path = Path(self.filepath).parents[1]
            collect_clonk_content_files(parent_path)
            print(self.filepath)
            global found_actions
            clonk_rig = GetOrAppendClonkRig()
            bpy.context.scene.anim_target = clonk_rig
            if bpy.data.collections.find("ClonkRig") == -1:
                raise AssertionError("No Collection named ClonkRig found.")
            bpy.context.scene.always_rendered_objects = bpy.data.collections["ClonkRig"]

            if len(found_actions) == 0:
                self.report(
                    {"ERROR"}, "Your ActMap.txt needs to be in the same folder (or neighboring folders) as your .anim files.")
                return {"CANCELLED"}

            reporttype, message = ImportActMap(self.filepath, found_actions, found_meshes,
                                               bpy.context.scene.anim_target, self.create_action_entry, self.import_tool_mesh)

            self.report({reporttype}, f"{message}")

        else:
            print(self.filepath + " is no ActMap!")
            self.report(
                {"ERROR"}, "Could not load file. Make sure the file you tried to load is an actmap.")

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

    messagetype, message = MetaData.CheckIfActionListIsValid(
        valid_action_entries)

    if messagetype == "ERROR":
        return messagetype, message

    sheet_width, sheet_height, sprite_strips = SpritesheetMaker.GetSpritesheetInfo(
        valid_action_entries)
    actmap_path = os.path.join(path, "ActMap.txt")

    # Get old actmap data
    file_content = []
    if os.path.exists(actmap_path):
        if PathUtilities.CanReadFile(actmap_path) == False or PathUtilities.CanWriteFile(actmap_path) == False:
            return "ERROR", "Need read/write permissions at output path. Aborted."
        file_content, messagetype, message = IniPort.Read(actmap_path)
        if messagetype == "ERROR":
            return messagetype, message
    else:
        print("No old Actmap.txt found. Creating new..")

    # What section in the file is listed explicitly in the addon?
    remaining_action_entries = valid_action_entries.copy()
    remaining_file_content = file_content.copy()
    section_descriptions = []
    for action_entry in valid_action_entries:
        for content_section in file_content:
            if content_section["Name"] == MetaData.GetActionName(action_entry):
                section_descriptions.append(
                    {"Action": action_entry, "FullCopy": True, "Section": content_section})
                remaining_action_entries.remove(action_entry)
                remaining_file_content.remove(content_section)
                break

    # What file section is related to what action but not explicitly listed in the addon?
    omitted_sections = remaining_file_content.copy()
    copied_descriptions = section_descriptions.copy()
    for section_index, section_description in enumerate(section_descriptions):
        for content_section in remaining_file_content:
            if content_section["Facet"] == section_description["Section"]["Facet"]:
                new_description = {
                    "Action": section_description["Action"], "FullCopy": False, "Section": content_section}
                # Put it always after the related description
                insertion_index = copied_descriptions.index(
                    section_description)
                # Insert checks array bounds for us.
                copied_descriptions.insert(insertion_index+1, new_description)
                omitted_sections.remove(content_section)

    section_descriptions = copied_descriptions

    # What remaining actions are not listed in the file? -> Create new sections
    for action_entry in remaining_action_entries:
        # But omit pictures ..
        if action_entry.render_type_enum == "Picture":
            continue

        content_section = {}
        content_section["SectionName"] = "[Action]"
        section_descriptions.append(
            {"Action": action_entry, "FullCopy": True, "Section": content_section})

    # Update content
    output_content = []
    for section_description in section_descriptions:
        content_section = section_description["Section"]
        reference_action_entry: MetaData.ActionMetaData = section_description["Action"]

        sprite_strip = sprite_strips[MetaData.GetActionName(
            reference_action_entry)]

        if section_description["FullCopy"]:
            content_section["Name"] = MetaData.GetActionName(
                reference_action_entry)
            content_section["Length"] = str(sprite_strip["Length"])

        x_pos = str(sprite_strip["X_pos"])
        y_pos = str(sprite_strip["Y_pos"])
        sprite_width = str(sprite_strip["Sprite_Width"])
        sprite_height = str(sprite_strip["Sprite_Height"])

        Facet = x_pos + "," + y_pos + "," + sprite_width + "," + sprite_height

        if reference_action_entry.invert_region_cropping == False and MetaData.is_using_cutout(reference_action_entry):
            min_max_pixels, pixel_dimensions = MetaData.GetPixelFromCutout(
                reference_action_entry)
            # Add cropping offset to facet
            y_offset = SpritesheetMaker.get_sprite_height(
                reference_action_entry, include_cropping=False) - min_max_pixels[3]
            Facet += "," + str(min_max_pixels[0]) + "," + str(y_offset)

        else:
            x_offset, y_offset = MetaData.get_automatic_facet_offset(
                bpy.context.scene, reference_action_entry)

            if reference_action_entry.override_facet_offset:
                x_offset += reference_action_entry.facet_offset_x
                y_offset += reference_action_entry.facet_offset_y

            if reference_action_entry.override_camera_shift and reference_action_entry.camera_shift_changes_facet_offset:
                x_offset += reference_action_entry.camera_shift_x
                y_offset += reference_action_entry.camera_shift_y

            if x_offset != 0 or y_offset != 0:
                Facet += "," + str(x_offset) + "," + str(y_offset)

        content_section["Facet"] = Facet

        output_content.append(content_section)

    if remove_unused_sections == False:
        output_content = output_content + omitted_sections

    unmatched_actions = ""
    for section in omitted_sections:
        unmatched_actions += section["Name"] + ", "

    # Save content
    messagetype, message = IniPort.Write(actmap_path, output_content)
    if messagetype == "ERROR":
        return messagetype, message
    if len(unmatched_actions) > 0:
        return "WARNING", "Exported ActMap.txt but some actions couldn't be matched: %s. You can create entries for it in the action list and export the ActMap again." % [unmatched_actions]
    else:
        return "INFO", "Exported ActMap.txt"


def PrintDefCore(path):
    valid_action_entries = MetaData.GetValidActionEntries()
    sheet_width, sheet_height, sprite_strips = SpritesheetMaker.GetSpritesheetInfo(
        valid_action_entries)

    defcore_path = os.path.join(path, "DefCore.txt")

    # Get old defcore data
    file_content = []
    if os.path.exists(defcore_path):
        if PathUtilities.CanReadFile(defcore_path) == False or PathUtilities.CanWriteFile(defcore_path) == False:
            return "ERROR", "Need read/write permissions at output path. Aborted."
        file_content, messagetype, message = IniPort.Read(defcore_path)
        if messagetype == "ERROR":
            return messagetype, message
    else:
        print("No old DefCore.txt found. Creating new..")

    # Prepare output content
    output_content = []
    if len(file_content) == 0:
        content_section = {"SectionName": "[DefCore]"}
        output_content.append(content_section)
    else:
        for content_section in file_content:
            output_content.append(content_section)

    # Update content
    content_section = output_content[0]  # DefCore section
    if bpy.context.scene.spritesheet_settings.custom_object_dimensions:
        content_section["Width"] = str(
            bpy.context.scene.spritesheet_settings.object_width)
        content_section["Height"] = str(
            bpy.context.scene.spritesheet_settings.object_height)
    else:
        content_section["Width"] = str(bpy.context.scene.render.resolution_x)
        content_section["Height"] = str(bpy.context.scene.render.resolution_y)

    if bpy.context.scene.spritesheet_settings.override_object_offset:
        x_offset = -bpy.context.scene.spritesheet_settings.object_center_x
        y_offset = -bpy.context.scene.spritesheet_settings.object_center_y
    elif bpy.context.scene.spritesheet_settings.custom_object_dimensions:
        x_offset = - \
            math.floor(
                bpy.context.scene.spritesheet_settings.object_width / 2.0)
        y_offset = - \
            math.floor(
                bpy.context.scene.spritesheet_settings.object_height / 2.0)
    else:
        x_offset = -math.floor(bpy.context.scene.render.resolution_x / 2.0)
        y_offset = -math.floor(bpy.context.scene.render.resolution_y / 2.0)

    content_section["Offset"] = f"{x_offset}, {y_offset}"

    picture = {
        "x": str(0),
        "y": str(0),
        "w": str(math.floor(bpy.context.scene.render.resolution_x)),
        "h": str(math.floor(bpy.context.scene.render.resolution_y))}
    for action_entry in valid_action_entries:
        if action_entry.render_type_enum == "Picture":
            strip = sprite_strips[MetaData.GetActionName(action_entry)]
            picture["x"] = str(math.floor(strip["X_pos"]))
            picture["y"] = str(math.floor(strip["Y_pos"]))
            picture["w"] = str(math.floor(strip["Sprite_Width"]))
            picture["h"] = str(math.floor(strip["Sprite_Height"]))
            break

    content_section["Picture"] = picture["x"] + "," + \
        picture["y"] + "," + picture["w"] + "," + picture["h"]

    if content_section.get("Scale"):
        content_section.pop("Scale")
    if bpy.context.scene.render.resolution_percentage != 100:
        content_section["Scale"] = str(
            bpy.context.scene.render.resolution_percentage)

    # Save content
    messagetype, message = IniPort.Write(defcore_path, output_content)
    if messagetype == "ERROR":
        return messagetype, message
    return "INFO", "Exported DefCore.txt"


def LoadRenderClonkWorld():
    global AddonDir
    dir = Path(AddonDir)

    if bpy.data.worlds.find("RenderClonkWorld") == -1:
        bpy.ops.wm.append(
            filepath="RenderClonk.blend",
            directory=str(Path.joinpath(dir, "RenderClonk.blend", "World")),
            filename="RenderClonkWorld"
        )

    bpy.context.scene.world = bpy.data.worlds['RenderClonkWorld']


def SetOptimalRenderingSettings():
    bpy.context.scene.has_applied_rendersettings = True

    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.device = "GPU"
    bpy.context.scene.render.film_transparent = True
    bpy.context.scene.cycles.pixel_filter_type = "GAUSSIAN"
    bpy.context.scene.cycles.filter_width = 1.5
    bpy.context.scene.display_settings.display_device = "sRGB"
    bpy.context.scene.view_settings.view_transform = "Standard"
    if bpy.context.scene.render.resolution_x == 1920:
        bpy.context.scene.render.resolution_x = 16
        bpy.context.scene.render.resolution_y = 20

    bpy.context.scene.render.image_settings.file_format = "PNG"
    bpy.context.scene.render.image_settings.color_mode = "RGBA"
    bpy.context.scene.render.image_settings.compression = 0
    bpy.context.scene.cycles.use_denoising = False
    bpy.context.scene.cycles.caustics_reflective = False
    bpy.context.scene.cycles.caustics_refractive = False
    bpy.context.scene.cycles.max_bounces = 1
    bpy.context.scene.cycles.diffuse_bounces = 0
    bpy.context.scene.cycles.glossy_bounces = 1
    bpy.context.scene.render.use_persistent_data = True
    bpy.context.scene.cycles.samples = 1024
    bpy.context.scene.render.fps = 15

    Overlay, Holdout, Fill = GetOrAppendOverlayMaterials()

    bpy.context.scene.spritesheet_settings.overlay_material = Overlay
    bpy.context.scene.spritesheet_settings.fill_material = Fill

    LoadRenderClonkWorld()
