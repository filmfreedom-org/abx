# Anansi Studio Extensions for Blender 'ABX'
"""
Collection of Blender extension tools to make our jobs easier.
This is not really meant to be an integrated plugin, but rather
a collection of useful scripts we can run to solve problems we
run into.
"""
#
#Copyright (C) 2019  Terry Hancock
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import os

import bpy, bpy.utils, bpy.types, bpy.props
from bpy.app.handlers import persistent

from . import file_context

# if bpy.data.filepath:
#     BlendfileContext = file_context.FileContext(bpy.data.filepath)
# else:
#     BlendfileContext = file_context.FileContext()
#
# abx_data = BlendfileContext.abx_data

from . import copy_anim
from abx import ink_paint
from . import render_profile


#configfile = os.path.join(os.path.dirname(__file__), 'config.yaml')

#print("Configuration file path: ", os.path.abspath(configfile))

# Lunatics Scene Panel

# Lunatics file/scene properties:

# TODO: This hard-coded table is a temporary solution until I have figured
# out a good way to look these up from the project files (maybe YAML?):
seq_id_table = {
    ('S1', 0): {'':'', 'mt':'Main Title'},
    ('S1', 1): {'':'',
        'TR':'Train',
        'SR':'Soyuz Rollout',
        'TB':'Touring Baikonur',
        'PC':'Press Conference',
        'SU':'Suiting Up',
        'LA':'Launch',
        'SF':'Soyuz Flight',
        'mt':'Main Title',
        'ad':'Ad Spot',
        'pv':'Preview',
        'et':'Episode Titles',
        'cr':'Credits'
        }, 
    ('S1', 2): {'':'',
        'MM':'Media Montage',
        'mt':'Main Title',
        'et':'Episode Titles',
        'SS':'Space Station',
        'LC':'Loading Cargo',
        'TL':'Trans Lunar Injection',
        'BT':'Bed Time',
        'ad':'Ad Spot',
        'pv':'Preview',
        'cr':'Credits'
        },
    ('S1', 3): {'':'', 
        'mt':'Main Title',
        'et':'Episode Titles',
        'ZG':'Zero G',
        'LI':'Lunar Injection',
        'LO':'Lunar Orbit',
        'ML':'Moon Landing',
        'IR':'Iridium',
        'TC':'Touring Colony',
        'FD':'Family Dinner',
        'ad':'Ad Spot',
        'pv':'Preview',
        'cr':'Credits'
        },
    ('S2', 0): {'':'', 'mt':'Main Title'},
    ('L', 0): {'':'',
        'demo':'Demonstration',
        'prop':'Property',
        'set': 'Set',
        'ext': 'Exterior Set',
        'int': 'Interior Set',
        'prac':'Practical',
        'char':'Character',
        'fx':  'Special Effect',
        'stock': 'Stock Animation'
        },
    None: ['']
    }


def get_seq_ids(self, context):
    """
    Specific function to retrieve enumerated values for sequence units.
    
    NOTE: due to be replaced by file_context features.
    """
    # 
    # Note: To avoid the reference bug mentioned in the Blender documentation,
    # we only return values held in the global seq_id_table, which
    # should remain defined and therefore hold a reference to the strings.
    #   
    if not context:
        seq_ids = seq_id_table[None]
    else:
        scene = context.scene
        series = scene.lunaprops.series_id
        episode = scene.lunaprops.episode_id
        if (series, episode) in seq_id_table:
            seq_ids = seq_id_table[(series, episode)]
        else:
            seq_ids = seq_id_table[None]
    seq_enum_items = [(s, s, seq_id_table[series,episode][s]) for s in seq_ids]
    return seq_enum_items

# Another hard-coded table -- for render profiles
render_profile_table = {
    'previz': {
        'name': 'PreViz',
        'desc': 'GL/AVI Previz Render for Animatics',
        'engine':'gl',
        'version':'any',
        'fps': 30,
        'fps_div': 1000,
        'fps_skip': 1,
        'suffix': 'GL',
        'format': 'AVI',
        'freestyle': False
        },
    
    'paint6': {
        'name': '6fps Paint',
        'desc': '6fps Simplified Paint-Only Render',
        'engine':'bi',
        'fps': 30,
        'fps_skip': 5,
        'suffix': 'P6',
        'format': 'AVI',
        'freestyle': False,
        'antialias': False,
        'motionblur': False
        },
    
    'paint3': {
        'name': '3fps Paint',
        'desc': '3fps Simplified Paint-Only Render',
        'engine': 'bi',
        'fps': 30,
        'fps_skip': 10,
        'suffix': 'P3',
        'format': 'AVI',
        'freestyle': False,
        'antialias': False,
        'motionblur': False,
        },
    
    'paint': {
        'name': '30fps Paint',
        'desc': '30fps Simplified Paint-Only Render',
        'engine': 'bi',
        'fps': 30,
        'fps_skip': 1,
        'suffix': 'PT',
        'format': 'AVI',
        'freestyle': False,
        'antialias': False,
        'motionblur': False
        },
    
    'check': {
        'name': '1fps Check',
        'desc': '1fps Full-Features Check Renders',
        'engine': 'bi',
        'fps': 30,
        'fps_skip': 30,
        'suffix': 'CH',
        'format': 'JPG',
        'framedigits': 5,
        'freestyle': True,
        'antialias': 8
        },
    
    'full': {
        'name': '30fps Full',
        'desc': 'Full Render with all Features Turned On',
        'engine': 'bi',
        'fps': 30,
        'fps_skip': 1,
        'suffix': '',
        'format': 'PNG',
        'framedigits': 5,
        'freestyle': True,
        'antialias': 8
        },
    }

    
class LunaticsSceneProperties(bpy.types.PropertyGroup):
    """
    Properties of the current scene.
    
    NOTE: due to be replaced by 'ProjectProperties', using the schema data
    retrieved by file_context.
    """
    series_id = bpy.props.EnumProperty(
        items=[
            ('S1', 'S1', 'Series One'),
            ('S2', 'S2', 'Series Two'),
            ('S3', 'S3', 'Series Three'),
            ('A1', 'Aud','Audiodrama'),
            ('L',  'Lib','Library')
            ],
        name="Series",
        default='S1',
        description="Series/Season of Animated Series, Audiodrama, or Library"      
        )
    
    episode_id = bpy.props.IntProperty(
        name="Episode",
        default=0,
        description="Episode number (0 means multi-use), ignored for Library",
        min=0,
        max=1000,
        soft_max=18
        )
    
    seq_id = bpy.props.EnumProperty(
        name='',
        items=get_seq_ids,
        description="Sequence ID"
        )
    
    block_id = bpy.props.IntProperty(
        name='',
        default=1,
        min=0,
        max=20,
        soft_max=10,
        description="Block number"
        )
    
    use_multicam = bpy.props.BoolProperty(
        name="Multicam",
        default=False,
        description="Use multicam camera/shot numbering?"
        )
    
    cam_id = bpy.props.IntProperty(
        name="Cam",
        default=0,
        min=0,
        max=20,
        soft_max=10,
        description="Camera number"
        )
    
    shot_id = bpy.props.EnumProperty(
        name='Shot',
        #items=[('NONE', '', 'Single')]+[(c,c,'Shot '+c) for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'],
        items=[(c,c,'Shot '+c) for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'],
        default='A',
        description="Shot ID, normally a single capital letter, can be empty, two letters for transitions"
        )
    
    shot_name = bpy.props.StringProperty(
        name='Name',
        description='Short descriptive codename',
        maxlen=0
        )
        


class LunaticsScenePanel(bpy.types.Panel):
    """
    Add a panel to the Properties-Scene screen
    
    NOTE: To be replaced by 'ProjectPropertiesPanel'.
    """
    bl_idname = 'SCENE_PT_lunatics'
    bl_label = 'Lunatics Project'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'scene'
    
    def draw(self, context):
        lunaprops = bpy.context.scene.lunaprops
        self.layout.label(text='Lunatics! Project Properties')
        row = self.layout.row()
        row.prop(lunaprops, 'series_id')
        row.prop(lunaprops, 'episode_id')
        row = self.layout.row()
        row.prop(lunaprops, 'use_multicam')
        row = self.layout.row()
        row.prop(lunaprops, 'seq_id')
        row.prop(lunaprops, 'block_id')
        if lunaprops.use_multicam:
            row.prop(lunaprops, 'cam_id')
        row.prop(lunaprops, 'shot_id')
        row.prop(lunaprops, 'shot_name')

# Buttons

class RenderProfileSettings(bpy.types.PropertyGroup):
    """
    Settings for Render Profiles control.
    
    NOTE: currently (0.2.6) uses hard-coded values. Planned to
    switch to project-defined values.
    """    
    render_profile = bpy.props.EnumProperty(
        name='Profile',
        items=[(k, v['name'], v['desc'])
                            for k,v in render_profile_table.items()],
        description="Select from pre-defined profiles of render settings",
        default='full')
    


class RenderProfilesOperator(bpy.types.Operator):
    """
    Operator invoked implicitly when render profile is changed.
    """
    bl_idname = 'render.render_profiles'
    bl_label = 'Apply Render Profile'
    bl_options = {'UNDO'}
    
    def invoke(self, context, event):
        scene = context.scene
        profile = render_profile_table[scene.render_profile_settings.render_profile]
        
        render_profile.set_render_from_profile(scene, profile)
        
        return {'FINISHED'}


class RenderProfilesPanel(bpy.types.Panel):
    """
    Add simple drop-down selector for generating common render settings with
    destination set according to project defaults.
    """
    bl_idname = 'SCENE_PT_render_profiles'
    bl_label = 'Render Profiles'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    
    def draw(self, context):
        rps = bpy.context.scene.render_profile_settings
        row = self.layout.row()
        row.prop(rps, 'render_profile')
        row = self.layout.row()
        row.operator('render.render_profiles')
        


class copy_animation(bpy.types.Operator):
    """
    Copy animation from active object to selected objects (select source last!).
    
    Useful for fixing broken proxy rigs (create a new proxy, and used this tool
    to copy all animation from the original -- avoids tedious/error-prone NLA work).
    
    Can also migrate to a re-scaled rig.
    """
    bl_idname = 'object.copy_anim'
    bl_label  = 'Copy Animation'
    bl_options = {'UNDO'}
    
    def invoke(self, context, event):
        #print("Copy NLA from selected armature to active armatures.")
        
        src_ob = context.active_object
        tgt_obs = [ob for ob in context.selected_objects if ob != context.active_object]
        
        # TODO 
        # Are these type checks necessary?
        # Is there any reason to restrict this operator to armature objects?
        # I think there isn't.
        
        if src_ob.type != 'ARMATURE':
            self.report({'WARNING'}, 'Cannot copy NLA data from object that is not an ARMATURE.')
            return {'CANCELLED'}
            
        tgt_arm_obs = []
        for ob in tgt_obs:
            if ob.type == 'ARMATURE':
                tgt_arm_obs.append(ob)
        if not tgt_arm_obs:
            self.report({'WARNING'}, 'No armature objects selected to copy animation data to.')
            return {'CANCELLED'}
                    
        copy_anim.copy_object_animation(src_ob, tgt_arm_obs,
            dopesheet=context.scene.copy_anim_settings.dopesheet,
            nla=context.scene.copy_anim_settings.nla,
            rescale=context.scene.copy_anim_settings.rescale,
            scale_factor=context.scene.copy_anim_settings.scale_factor,
            report=self.report)
        
        return {'FINISHED'}
    

        
class copy_animation_settings(bpy.types.PropertyGroup):
    """
    Settings for the 'copy_animation' operator.
    """
    dopesheet = bpy.props.BoolProperty(
        name = "Dope Sheet",
        description = "Copy animation from Dope Sheet",
        default=True)
    
    nla = bpy.props.BoolProperty(
        name = "NLA Strips",
        description = "Copy all strips from NLA Editor",
        default=True)
    
    rescale =  bpy.props.BoolProperty(
        name = "Re-Scale/Copy",
        description = "Make rescaled COPY of actions instead of LINK to original",
        default = False)
    
    scale_factor = bpy.props.FloatProperty(
        name = "Scale",
        description = "Scale factor for scaling animation (Re-Scale w/ 1.0 copies actions)",
        default = 1.0)
    


class CharacterPanel(bpy.types.Panel):
    """
    Features for working with characters and armatures.
    
    Currently only includes the CopyAnimation operator.
    """
    bl_space_type = "VIEW_3D" # window type panel is displayed in
    bl_context = "objectmode"
    bl_region_type = "TOOLS" # region of window panel is displayed in
    bl_label = "Character"
    bl_category = "ABX"

    def draw(self, context):
        settings = bpy.context.scene.copy_anim_settings
        layout = self.layout.column(align = True)
        layout.label("Animation Data")
        layout.operator('object.copy_anim')
        layout.prop(settings, 'dopesheet')
        layout.prop(settings, 'nla')
        layout.prop(settings, 'rescale')
        layout.prop(settings, 'scale_factor')
        

         
    
class lunatics_compositing_settings(bpy.types.PropertyGroup):
    """
    Settings for Ink/Paint Config.
    """
    inkthru = bpy.props.BoolProperty(
        name = "Ink-Thru",
        description = "Support transparent Freestyle ink effect",
        default=True)
    
    billboards =  bpy.props.BoolProperty(
        name = "Billboards",
        description = "Support material pass for correct billboard inking",
        default = False)
    
    sepsky = bpy.props.BoolProperty(
        name = "Separate Sky",
        description = "Render sky separately with compositing support (better shadows)",
        default = True)   
    
  
class lunatics_compositing(bpy.types.Operator):
    """
    Ink/Paint Config Operator.
    """
    bl_idname = "scene.lunatics_compos"
    bl_label = "Ink/Paint Config"
    bl_options = {'UNDO'}
    bl_description = "Set up standard Lunatics Ink/Paint compositing in scene"
    
    def invoke(self, context, event):
        """
        Add standard 'Lunatics!' shot compositing to the currently-selected scene.
        """
        scene = context.scene
        
        shot = ink_paint.LunaticsShot(scene, 
                inkthru=context.scene.lx_compos_settings.inkthru,
                billboards=context.scene.lx_compos_settings.billboards,
                sepsky=context.scene.lx_compos_settings.sepsky )
        
        shot.cfg_scene()
        
        return {'FINISHED'}
    
#     def draw(self, context):
#         settings = context.scene.lx_compos_settings
#         self.col = self.layout.col()
#         col.prop(settings, "inkthru", text="Ink Thru")
#         col.prop(settings, "billboards", text="Ink Thru")
      

         
class LunaticsPanel(bpy.types.Panel):
    """
    Ink/Paint Configuration panel.
    """
    bl_space_type = "VIEW_3D"
    bl_context = "objectmode"
    bl_region_type = "TOOLS"
    bl_label = "Lunatics"
    bl_category = "ABX"
    
    def draw(self, context):
        settings = bpy.context.scene.lx_compos_settings
        layout = self.layout.column(align = True)
        layout.label("Compositing")
        layout.operator('scene.lunatics_compos')
        layout.prop(settings, 'inkthru', text="Ink-Thru")
        layout.prop(settings, 'billboards', text="Billboards")
        layout.prop(settings, 'sepsky', text="Separate Sky")
        
        
BlendFile = file_context.FileContext()
        
@persistent
def update_handler(ctxt):
    """
    Keeps FileContext up-to-date with Blender file loaded.
    """
    BlendFile.update(bpy.data.filepath)
     
        
def register():
    bpy.utils.register_class(LunaticsSceneProperties)
    bpy.types.Scene.lunaprops = bpy.props.PointerProperty(type=LunaticsSceneProperties)    
    bpy.utils.register_class(LunaticsScenePanel)
    
    bpy.utils.register_class(RenderProfileSettings)
    bpy.types.Scene.render_profile_settings = bpy.props.PointerProperty(
        type=RenderProfileSettings)
    bpy.utils.register_class(RenderProfilesOperator)
    bpy.utils.register_class(RenderProfilesPanel)  
        
    bpy.utils.register_class(copy_animation)
    bpy.utils.register_class(copy_animation_settings)
    bpy.types.Scene.copy_anim_settings = bpy.props.PointerProperty(type=copy_animation_settings)
    bpy.utils.register_class(CharacterPanel)  
    
    bpy.utils.register_class(lunatics_compositing_settings)
    bpy.types.Scene.lx_compos_settings = bpy.props.PointerProperty(type=lunatics_compositing_settings)
    bpy.utils.register_class(lunatics_compositing)
    bpy.utils.register_class(LunaticsPanel)
    
    bpy.app.handlers.save_post.append(update_handler)
    bpy.app.handlers.load_post.append(update_handler)
    bpy.app.handlers.scene_update_post.append(update_handler)
    
def unregister():
    bpy.utils.unregister_class(LunaticsSceneProperties)
    bpy.utils.unregister_class(LunaticsScenePanel)
    
    bpy.utils.unregister_class(RenderProfileSettings)
    bpy.utils.unregister_class(RenderProfilesOperator)
    bpy.utils.unregister_class(RenderProfilesPanel)  
        
    bpy.utils.unregister_class(copy_animation)
    bpy.utils.unregister_class(copy_animation_settings)
    bpy.utils.unregister_class(CharacterPanel)  
    
    bpy.utils.unregister_class(lunatics_compositing_settings)
    bpy.utils.unregister_class(lunatics_compositing)
    bpy.utils.unregister_class(LunaticsPanel)  
