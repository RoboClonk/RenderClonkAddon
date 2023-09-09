# --------------------------
# PathUtilities
# 05.03.2022
# --------------------------
# Robin Hohnsbeen (Ryou)

import os
import bpy


def CanWriteFile(path):
    if os.path.exists(path):
        if os.path.isfile(path):
            return os.access(path, os.W_OK)
        else:
            return False


def CanReadFile(path):
    return os.access(path, os.R_OK)


def GetOutputPath():
    save_path = bpy.path.abspath("/tmp")
    if bpy.data.is_saved:
        save_path = os.path.dirname(bpy.data.filepath)
    return os.path.join(save_path, "output_render")
