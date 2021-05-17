
bl_info = {
    "name": "ABX",
    "author": "Terry Hancock / Lunatics.TV Project / Anansi Spaceworks",
    "version": (0, 2, 5),
    "blender": (2, 79, 0),
    "location": "SpaceBar Search -> ABX",
    "description": "Anansi Studio Extensions for Blender",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Object",
    }

blender_present = False
try:
    # These are protected so we can read the add-on metadata from my
    # management scripts, which run in the O/S standard Python 3    
    import bpy, bpy.utils, bpy.types
    blender_present = True
    
except ImportError:
    print("Blender Add-On 'ABX' requires the Blender Python environment to run.")
    
print("blender_present = ", blender_present)
    
if blender_present:
    from . import abx_ui

    def register():
        bpy.utils.register_module(__name__)

    def unregister():
        bpy.utils.unregister_module(__name__)

     
if __name__ == "__main__":
    register()
