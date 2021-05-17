#script to run:
SCRIPT="/project/terry/Dev/eclipse-workspace/ABX/src/abx.py"  
    
#path to the PyDev folder that contains a file named pydevd.py:
PYDEVD_PATH='/home/terry/.eclipse/360744294_linux_gtk_x86_64/plugins/org.python.pydev.core_7.3.0.201908161924/pysrc/'

#PYDEVD_PATH='/home/terry/.config/blender/2.79/scripts/addons/modules/pydev_debug.py'

import pydev_debug as pydev #pydev_debug.py is in a folder from Blender PYTHONPATH 

pydev.debug(SCRIPT, PYDEVD_PATH, trace = True)
