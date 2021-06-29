# render_profile.py
"""
Blender Python code to set parameters based on render profiles.

The purpose of the "Render Profiles" feature is to simplify setting up
Blender to render animation according to a small number of standardized, 
named profiles, instead of having to control each setting separately.

They're sort of like predefined radio buttons for your render settings.

I wrote this because I kept having to repeat the same steps to go from
quick "GL" or "Paint" renders at low frame rates to fully-configured
final renders, and I found the process was error-prone.

In particular, it was very easy to accidentally forget to change the render
filepath and have a previous render get overwritten! Or, alternatively, I
might forget to set things back up for a final render after I did a previz
animation.
"""

import os

import bpy
import bpy, bpy.types, bpy.utils, bpy.props

from abx import ink_paint

from . import file_context

class RenderProfileMap(dict):
    """
    Specialized dictionary for mapping Render profile names to profiles.
    """
    def __init__(self, profile_map=None):
        self._blender_enum = []
        if not profile_map:
            profile_map = {}
        for key in profile_map:
            self[key] = RenderProfile(key, profile_map[key])
            
        for key in self.keys():
            self._blender_enum.append((key, self[key].name, self[key].desc))
            
    def keys(self):
        return sorted(super().keys())
    
    def blender_enum(self):
        return self._blender_enum
    
    def apply(self, scene, key):
        self[key].apply(scene)
        
def blender_enum_lookup(self, context):
    from abx import BlendFile
    return RenderProfileMap(BlendFile.render_profiles).blender_enum()

class RenderProfile(object):
    """
    A named set of render settings for Blender.
    
    The profile is designed to be defined by a dictionary of fields, typically
    loaded from a project YAML file (under the key 'render_profiles').
    
    Attributes:
        name (str):
            Drop-down name for profile.
            
        desc (str):
            Longer descriptive name used for tooltips in the UI.
            
        engine (str):
            Mandatory choice of engine. Some aliases are supported, but the
            standard values are: 'gl', meaning a setup for GL viewport
            rendering, or one 'bi'/'BLENDER_INTERNAL', 'cycles'/'CYCLES',
            or 'bge' / 'BLENDER_GAME' for rendering with the respective 
            engines. There is no support for Eevee, because this is a 2.7-only
            Add-on. It should be included in the port. No third-party engines
            are currently supported.
            
        fps (float):
            Frames-per-second.
            
        fps_skip (int):
            Frames to skip between rendered frames (effectively divides the
            frame rate).
            
        fps_divisor (float):
            This is the weird hack for specifying NTSC-compliant fps of 29.97
            by using 1.001 as a divisor, instead of 1.0. Avoid if you can!
            
        rendersize (int):
            Percentage size of defined pixel dimensions to render. Note that
            we don't support setting the pixel size directly. You should
            configure that in Blender, but you can use this feature to make
            a lower-resolution render.
            
        compress (int):
            Compression ratio for image formats that support it.
            
        format (str):
            Image or video output format.
            One of: 'PNG', 'JPG', 'EXR', 'AVI' or 'MKV'.
            Note that we don't support the full range of options, just some
            common ones for previz and final rendering.
            
        freestyle (bool):
            Whether to turn on Freestyle ink rendering.
            
        antialiasing_samples (str):
            Controlled by 'antialias' key, which can be a number: 5,8,11, or 16.
            Note that this attribute, which is used to directly set the value
            in Blender is a string, not an integer.
            
        use_antialiasing (bool):
            Controlled by 'antialias' key. Whether to turn on antialiasing.
            Any value other than 'False' or 'None' will turn it on.
            False turns it off. None leaves it as-is.
            
        motion_blur_samples (int):
            Controlled by 'motionblur' key, which can be a number determining
            the number of samples.
            
        use_motion_blur (bool):
            Controlled by 'motionblur' key. Any value other than False or None
            will turn on motion blur. A value of True turns it on without
            changing the samples. A value of False turns it off. None causes
            is to be left as-is.
            
        framedigits (int):
            The number of '#' characters to use in the render filename to
            indicate frame number. Only used if the format is an image stream.
            
        suffix (str):
            A string suffix placed after the base name, but before the frame
            number to indicate what profile was used for the render. This
            avoids accidentally overwriting renders made with other profiles.
            
    Note that these attributes are not intended to be manipulated directly
    by the user. The production designer is expected to define these
    profiles in the <project>.yaml file under the 'render_profiles' key,
    like this:
        
        render_profiles:
            previz:
                engine: gl
                suffix: MP
                fps: 30
                fps_skip: 6
                motionblur: False
                antialias: False
                freestyle: False
                rendersize: 50
                
    and so on. This is then loaded by ABX into a list of RenderProfile
    objects. Calling the RenderProfile.apply() method actually causes the
    settings to be made.
    """
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
    
    
    def __init__(self, code, fields):
        
        # Note:  Settings w/ value *None* are left unaltered
        #        That is, they remain whatever they were before
        #        If a setting isn't included in the fields, then
        #        the attribute will be *None*.
        
        if 'name' in fields:
            self.name = fields['name']
        else:
            self.name = code
            
        if 'desc' in fields:
            self.desc = fields['desc']
        else:
            self.desc = code
        
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
        
        NOTE: in 0.2.6 this function isn't fully implemented, and the
        render filepath will not include the proper unit name.
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
            
            prefix = os.path.join(
                scene.project_properties.render_folder,
                scene.project_properties.render_prefix)
            if self.suffix:
                scene.render.filepath = (prefix + '-' + self.suffix + '-' +
                    'f'+('#'*self.framedigits) + '.' +
                    self.render_formats[self.format][1])
            else:
                scene.render.filepath = (prefix + '-f'+('#'*self.framedigits) + '.' +
                    self.render_formats[self.format][1])               
                

        