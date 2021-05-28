# render_profile.py
"""
Blender Python code to set parameters based on render profiles.
"""

import bpy
import bpy, bpy.types, bpy.utils, bpy.props

from . import std_lunatics_ink

from . import file_context


class RenderProfile(object):
    render_formats = {
        # VERY simplified and limited list of formats from Blender that we need:
        # <API 'format'>: (<bpy file format>, <filename extension>),
        'PNG':      ('PNG',  'png'),
        'JPG':      ('JPEG', 'jpg'),
        'EXR':      ('OPEN_EXR_MULTILAYER', 'exr'),
        'AVI':      ('AVI_JPEG', 'avi'),
        'MKV':      ('FFMPEG', 'mkv')
        }    
    
    engines = {
        'bi': 'BLENDER_RENDER',
        'BLENDER_RENDER': 'BLENDER_RENDER',
        'BI': 'BLENDER_RENDER',
        
        'cycles': 'CYCLES',
        'CYCLES': 'CYCLES',
        
        'bge':  'BLENDER_GAME',
        'BLENDER_GAME': 'BLENDER_GAME',
        'BGE': 'BLENDER_GAME',
        
        'gl': None,
        'GL': None
        }
    
    
    def __init__(self, fields):
        
        # Note:  Settings w/ value *None* are left unaltered
        #        That is, they remain whatever they were before
        #        If a setting isn't included in the fields, then
        #        the attribute will be *None*.
        
        if 'engine' not in fields:
            fields['engine'] = None
            
        if fields['engine']=='gl':
            self.viewport_render = True
            self.engine = None
        else:
            self.viewport_render = False
            
        if fields['engine'] in self.engines:
            self.engine = self.engines[fields['engine']]
        else:
            self.engine = None
            
        # Parameters which are stored as-is, without modification:
        self.fps      = 'fps'      in fields and int(fields['fps'])      or None
        self.fps_skip = 'fps_skip' in fields and int(fields['fps_skip']) or None
        self.fps_divisor = 'fps_divisor' in fields and float(fields['fps_divisor']) or None
        self.rendersize  = 'rendersize'  in fields and int(fields['rendersize']) or None
        self.compress    = 'compress'    in fields and int(fields['compress']) or None
        
        self.format   = 'format'   in fields and str(fields['format'])   or None
        
        self.freestyle = 'freestyle' in fields and bool(fields['freestyle']) or None
        
        self.antialiasing_samples = None
        self.use_antialiasing = None
        if 'antialias' in fields:
            if fields['antialias']:
                self.use_antialiasing = True
                if fields['antialias'] in (5,8,11,16):
                    self.antialiasing_samples = str(fields['antialias'])
            else:
                self.use_antialiasing = False
        
        self.use_motion_blur = None
        self.motion_blur_samples = None
        if 'motionblur' in fields:
            if fields['motionblur']:
                self.use_motion_blur = True
                if type(fields['motionblur'])==int:
                    self.motion_blur_samples = int(fields['motionblur'])
            else:
                self.use_motion_blur = False
                
        if 'framedigits' in fields:
            self.framedigits = fields['framedigits']
        else:
            self.framedigits = 5        
            
        if 'suffix' in fields:
            self.suffix = fields['suffix']
        else:
            self.suffix = ''        
            
    def apply(self, scene):
        """
        Apply the profile settings to the given scene.
        """
        if self.engine:         scene.render.engine = self.engine
        if self.fps:            scene.render.fps = self.fps
        if self.fps_skip:       scene.frame_step = self.fps_skip
        if self.fps_divisor:    scene.render.fps_base = self.fps_divisor
        if self.rendersize:     scene.render.resolution_percentage = self.rendersize
        if self.compress:       scene.render.image_settings.compression = self.compress
        
        if self.format:
            scene.render.image_settings.file_format = self.render_formats[self.format][0]
        
        if self.freestyle:      scene.render.use_freestyle = self.freestyle
        if self.use_antialiasing:
            scene.render.use_antialiasing = self.use_antialiasing
            
        if self.antialiasing_samples:
            scene.render.antialiasing_samples = self.antialiasing_samples
        if self.use_motion_blur:
            scene.render.use_motion_blur = self.use_motion_blur
            
        if self.motion_blur_samples:
            scene.render.motion_blur_samples = self.motion_blur_samples
            
        if self.format:
            # prefix = scene.name_context.render_path
            # prefix = BlendfileContext.name_contexts[scene.name_context].render_path
            prefix = 'path_to_render'  # We actually need to get this from NameContext
            if self.suffix:
                scene.render.filepath = (prefix + '-' + self.suffix + '-' +
                    'f'+('#'*self.framedigits) + '.' +
                    self.render_formats[self.format][1])
                
        

# def set_render_from_profile(scene, profile):
#     if 'engine' in profile:
#         if profile['engine'] == 'gl':
#             pass
#         elif profile['engine'] == 'bi':
#             scene.render.engine = 'BLENDER_RENDER'
#         elif profile['engine'] == 'cycles':
#             scene.render.engine = 'CYCLES'
#         elif profile['engine'] == 'bge':
#             scene.render.engine = 'BLENDER_GAME'
#
#     if 'fps' in profile:
#         scene.render.fps = profile['fps']
#
#     if 'fps_skip' in profile:
#         scene.frame_step = profile['fps_skip']
#
#     if 'format' in profile:
#         scene.render.image_settings.file_format = render_formats[profile['format']][0]
#
#     if 'freestyle' in profile:
#         scene.render.use_freestyle = profile['freestyle']
#
#     if 'antialias' in profile:
#         if profile['antialias']:
#             scene.render.use_antialiasing = True
#             if profile['antialias'] in (5,8,11,16):
#                 scene.render.antialiasing_samples = str(profile['antialias'])
#         else:
#             scene.render.use_antialiasing = False
#
#     if 'motionblur' in profile:
#         if profile['motionblur']:
#             scene.render.use_motion_blur = True
#             if type(profile['motionblur'])==int:
#                 scene.render.motion_blur_samples = profile['motionblur']
#         else:
#             scene.render.use_motion_blur = False
#
#     # Use Lunatics naming scheme for render target:
#     if 'framedigits' in profile:
#         framedigits = profile['framedigits']
#     else:
#         framedigits = 5
#
#     if 'suffix' in profile:
#         suffix = profile['suffix']
#     else:
#         suffix = ''
#
#     if 'format' in profile:
#         rdr_fmt = render_formats[profile['format']][0]
#         ext = render_formats[profile['format']][1]
#     else:
#         rdr_fmt = 'PNG'
#         ext = 'png'
#
#     path = std_lunatics_ink.LunaticsShot(scene).render_path(
#         suffix=suffix, framedigits=framedigits, ext=ext, rdr_fmt=rdr_fmt)
#
#     scene.render.filepath = path
    
        