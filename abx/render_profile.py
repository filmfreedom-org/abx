# render_profile.py
"""
Blender Python code to set parameters based on render profiles.
"""

import bpy, bpy.types, bpy.utils, bpy.props

from . import std_lunatics_ink

render_formats = {
    # VERY simplified and limited list of formats from Blender that we need:
    # <API 'format'>: (<bpy file format>, <filename extension>),
    'PNG':      ('PNG',  'png'),
    'JPG':      ('JPEG', 'jpg'),
    'EXR':      ('OPEN_EXR_MULTILAYER', 'exr'),
    'AVI':      ('AVI_JPEG', 'avi'),
    'MKV':      ('FFMPEG', 'mkv')
    }


def set_render_from_profile(scene, profile):
    if 'engine' in profile:
        if profile['engine'] == 'gl':
            pass
        elif profile['engine'] == 'bi':
            scene.render.engine = 'BLENDER_RENDER'
        elif profile['engine'] == 'cycles':
            scene.render.engine = 'CYCLES'
        elif profile['engine'] == 'bge':
            scene.render.engine = 'BLENDER_GAME'
            
    if 'fps' in profile:
        scene.render.fps = profile['fps']
    
    if 'fps_skip' in profile:
        scene.frame_step = profile['fps_skip']
        
    if 'format' in profile:
        scene.render.image_settings.file_format = render_formats[profile['format']][0]
        
    if 'freestyle' in profile:
        scene.render.use_freestyle = profile['freestyle']
        
    if 'antialias' in profile:
        if profile['antialias']:
            scene.render.use_antialiasing = True
            if profile['antialias'] in (5,8,11,16):
                scene.render.antialiasing_samples = str(profile['antialias'])
        else:
            scene.render.use_antialiasing = False
    
    if 'motionblur' in profile:
        if profile['motionblur']:
            scene.render.use_motion_blur = True
            if type(profile['motionblur'])==int:
                scene.render.motion_blur_samples = profile['motionblur']
        else:
            scene.render.use_motion_blur = False
    
    # Use Lunatics naming scheme for render target:
    if 'framedigits' in profile:
        framedigits = profile['framedigits']
    else:
        framedigits = 5
        
    if 'suffix' in profile:
        suffix = profile['suffix']
    else:
        suffix = ''
        
    if 'format' in profile:
        rdr_fmt = render_formats[profile['format']][0]
        ext = render_formats[profile['format']][1]
    else:
        rdr_fmt = 'PNG'
        ext = 'png'
    
    path = std_lunatics_ink.LunaticsShot(scene).render_path(
        suffix=suffix, framedigits=framedigits, ext=ext, rdr_fmt=rdr_fmt)
    
    scene.render.filepath = path
    
        