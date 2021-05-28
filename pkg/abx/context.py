# context.py
"""
Combines context sources to create AbxContext object (dictionary tree).
"""

import bpy, bpy.app, bpy.data, bpy.ops

from bpy.app.handlers import persistent
#from accumulate import UnionList, RecursiveDict

from . import file_context

if os.path.exists(bpy.data.filepath):
    BlendfileContext = file_context.FileContext(bpy.data.filepath)
else:
    BlendfileContext = file_context.FileContext()

# Attach a handler to keep our filepath context up to date with Blender
@persistent
def update_handler(ctxt):
    BlendfileContext.update(bpy.data.filepath)

bpy.app.handlers.save_post.append(update_handler)
bpy.app.handlers.load_post.append(update_handler)
bpy.app.handlers.scene_update_post.append(update_handler)

