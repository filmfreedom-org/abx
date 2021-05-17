#!/usr/bin/env python
"""
MakeAddOnZip.py

Utility script to package ABX into the "abx-##.##.zip" file needed for Installation
in Blender.
"""
import subprocess, os

import bpy, bpy.utils

import abx

VERSION_PKG = ('a',)
VERSION = abx.bl_info['version'] + VERSION_PKG

#VERSION = (0,1,2,'a')

#AODIR = 'abx%d%d%d%s' % VERSION  # Addon directory name for Blender
AODIR = 'abx'
PKGNAME = 'abx-%d.%d.%d%s' % VERSION  # Package name for ZIP file

# PROJDIR is the project directory, one above the source tree, where my associated
#         stuff lives: documentation, management scripts, etc.
#         Normally this script is in it, and so the directory of __file__ is what I want.
#         But not if I'm testing this code out on the console!
try:
    # Normally if I'm running from a script, I want the directory the script is in
    PROJDIR = os.path.dirname(os.path.abspath(__file__))
except:
    # Occasionally I might be trying to run from a console, in which case there's
    # no file, and I probably just want to use the "present working directory"
    # Hopefully, at that point, I'm smart enough to have set it correctly!
    PROJDIR = os.getcwd()
    
PKGDIR = os.path.join(PROJDIR, 'pkg')   # Directory used for building packages.

print( "VERSION: %d.%d.%d%s" % VERSION)
print( "PACKAGE DIRECTORY: ", PKGDIR)
print( "WORKING DIRECTORY: ", PROJDIR)


subprocess.run(('rm', '-rf',  AODIR), cwd=PKGDIR)
subprocess.run(('rm', PKGNAME+'.zip'), cwd=PKGDIR)
subprocess.run(('mkdir', AODIR), cwd=PKGDIR)

files = os.listdir(os.path.join(PROJDIR, 'abx'))
pkg_files = []
for ext in ('.py', '.yaml', '.cfg'):
    pkg_files.extend([
        os.path.abspath(os.path.join(PROJDIR, 'abx', f))
            for f in files if f.endswith(ext)])
    
subprocess.run(('cp',) + tuple(pkg_files) + (
                     os.path.join(PKGDIR, AODIR),), cwd=PROJDIR)
subprocess.run(('zip', '-r',  PKGNAME+'.zip', AODIR), cwd=PKGDIR)
    
# TODO: It would be good to clean the copied source tree, to get rid of unwanted files
#       or else I could make the copy operation more selective. As it is, I'm packaging
#       a lot of unnecessary files.


    
    