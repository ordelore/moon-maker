import sys
import os
import bpy

MESH_NAME = "moonmesh"

blend_dir = os.path.dirname(bpy.data.filepath)
if blend_dir not in sys.path:
   sys.path.append(blend_dir)

import moonsurface
import importlib
importlib.reload(moonsurface)
moonsurface.create_moon(MESH_NAME)
