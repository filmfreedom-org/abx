#!/usr/bin/env python
# Inject the unittest runner script into Blender and run it in batch mode:
import subprocess
subprocess.call(['blender279', '-b', '-P', '/project/terry/Dev/Git/abx/scripts/TestInBlender_bpy.py'])
