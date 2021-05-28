# std_lunatics_ink.py
"""
Functions to set up the standard ink and paint compositing arrangement
for "Lunatics"
"""

import os

import bpy, bpy.props, bpy.utils

# Hard-coded default parameters:
INK_THICKNESS = 3
INK_COLOR = (0,0,0)
THRU_INK_THICKNESS = 2
THRU_INK_COLOR = (20,100,50)



# TODO: probably should have a dialog somewhere that can change these through the UI?

class LunaticsShot(object):
    """
    General class for Lunatics Blender Scene data.
    """
    colorcode = {
        'paint':    (1.00, 1.00, 1.00),
        'ink':      (0.75, 0.50, 0.35),
        'thru':     (0.35, 0.50, 0.75),
        'bb':       (0.35, 0.75, 0.50),
        'bbthru':   (0.35, 0.75, 0.75),
        'sky':      (0.50, 0.25, 0.75),
        'compos':   (0.75, 0.75, 0.75),
        'output':   (0.35, 0.35, 0.35)
        }
    
    def __init__(self, scene, inkthru=False, billboards=False, sepsky=False):        
        self.scene = scene
        self.inkthru = bool(inkthru)
        self.billboards = bool(billboards)
        self.sepsky = bool(sepsky)
    
        self.series_id = scene.lunaprops.series_id
        self.episode_id = scene.lunaprops.episode_id
        self.seq_id = scene.lunaprops.seq_id
        self.block_id = scene.lunaprops.block_id
        self.shot_id = scene.lunaprops.shot_id
        self.cam_id = scene.lunaprops.cam_id
        self.shot_name = scene.lunaprops.shot_name
        
        self.render_root = '//../../Renders/'
        
    @property
    def fullname(self):
        return self.designation + '-' + self.name
            
    @property
    def designation(self):
        episode_code = "%2.2sE%2.2d" % (self.series_id, self.episode_id)
        return episode_code + '-' + self.shortname
        
    @property
    def shortname(self):
        desig = str(self.seq_id) + '-' + str(self.block_id)
        if self.cam_id:
            desig = desig + '-Cam' + str(self.cam_id) 
        if self.shot_id:
            desig = desig + '-' + str(self.shot_id)
        return desig
    
    @property
    def scene_name(self):
        if self.shot_name:
            return self.shortname + ' ' + self.shot_name
        else:
            return self.shortname
        
    def render_path(self, suffix='', framedigits=5, ext='png', rdr_fmt='PNG'):
        if suffix:
            suffix = '-' + suffix
        if rdr_fmt in ('AVI', 'MKV'):
            path = os.path.join(self.render_root, suffix,
                    self.designation + suffix + '.' + ext)
        else:
            path = os.path.join(self.render_root, suffix, self.designation,
                    self.designation + suffix + '-f' + '#'*framedigits + '.' + ext)
        return path

    def cfg_scene(self, scene=None, thru=True, exr=True, multicam=False, role='shot'):
        if not scene:
            scene = self.scene
    
        scene.name = self.scene_name
        scene.render.filepath = self.render_path()
        #os.path.join(self.render_root, 'PNG', self.designation, self.designation + '-f#####.png')
        scene.render.image_settings.file_format='PNG'
        scene.render.image_settings.compression = 50
        scene.render.image_settings.color_mode = 'RGB'
        scene.render.use_freestyle = True
        
        # Create Paint & Ink Render Layers
        for rlayer in scene.render.layers:
            rlayer.name = '~' + rlayer.name
            rlayer.use = False
            # Rename & turn off existing layers (but don't delete, in case they were wanted)
        
        scene.render.layers.new('Paint')
        self.cfg_paint(scene.render.layers['Paint'])     
        
        scene.render.layers.new('Ink')
        self.cfg_ink(scene.render.layers['Ink'],
                thickness=INK_THICKNESS, color=INK_COLOR)        
            
        if self.inkthru:
            scene.render.layers.new('Ink-Thru')
            self.cfg_ink(scene.render.layers['Ink-Thru'], 
                    thickness=THRU_INK_THICKNESS, color=THRU_INK_COLOR)
                        
        if self.billboards:
            scene.render.layers.new('BB-Alpha')
            self.cfg_bbalpha(scene.render.layers['BB-Alpha'])
            
            scene.render.layers.new('BB-Mat')
            self.cfg_bbmat(scene.render.layers['BB-Mat'], thru=False)
            
        if self.billboards and self.inkthru:
            scene.render.layers.new('BB-Mat-Thru')
            self.cfg_bbmat(scene.render.layers['BB-Mat-Thru'], thru=True)
            
        if self.sepsky:
            scene.render.layers.new('Sky')
            self.cfg_sky(scene.render.layers['Sky'])
            
        self.cfg_nodes(scene)
        
    def _new_rlayer_in(self, name, scene, rlayer, location, color):
        tree = scene.node_tree
        rlayer_in = tree.nodes.new('CompositorNodeRLayers')
        rlayer_in.name = '_'.join([n.lower() for n in name.split('-')])+'_in'
        rlayer_in.label = name+'-In'
        rlayer_in.scene = scene
        rlayer_in.layer = rlayer
        rlayer_in.color = color
        rlayer_in.use_custom_color = True
        rlayer_in.location = location        
        return rlayer_in
    
    def cfg_nodes(self, scene):
        # Create Compositing Node Tree
        scene.use_nodes = True
        tree = scene.node_tree
        # clear default nodes
        for node in tree.nodes:
            tree.nodes.remove(node)
        
        # Paint RenderLayer Nodes
        paint_in = self._new_rlayer_in('Paint', scene, 'Paint', 
            (0,1720), self.colorcode['paint'])
            
        if self.sepsky:
            sky_in = self._new_rlayer_in('Sky', scene, 'Sky',
                (0, 1200), self.colorcode['sky'])
    
        # Configure EXR format
        exr_paint = tree.nodes.new('CompositorNodeOutputFile')
        exr_paint.name = 'exr_paint'
        exr_paint.label = 'Paint EXR'
        exr_paint.location = (300,1215)
        exr_paint.color = self.colorcode['paint']
        exr_paint.use_custom_color = True
        exr_paint.format.file_format = 'OPEN_EXR_MULTILAYER'
        exr_paint.format.color_mode = 'RGBA'
        exr_paint.format.color_depth = '16'
        exr_paint.format.exr_codec = 'ZIP'
        exr_paint.base_path = os.path.join(self.render_root, 'EXR', 
            self.designation, self.designation + '-Paint-f#####' + '.exr')
        if 'Image' in exr_paint.layer_slots:
            exr_paint.layer_slots.remove(exr_paint.inputs['Image'])    
            
        # Create EXR layers and connect to render passes
        rpasses = ['Image', 'Depth', 'Normal', 'Vector', 
                   'Spec',  'Shadow','Reflect','Emit']
        for rpass in rpasses:
            exr_paint.layer_slots.new(rpass)
            tree.links.new(paint_in.outputs[rpass], exr_paint.inputs[rpass])
            
        if self.sepsky:
            exr_paint.layer_slots.new('Sky')
            tree.links.new(sky_in.outputs['Image'], exr_paint.inputs['Sky'])
    
        # Ink RenderLayer Nodes
        ink_in = self._new_rlayer_in('Ink', scene, 'Ink',
            (590, 1275), self.colorcode['ink'])
            
        if self.inkthru:
            thru_in = self._new_rlayer_in('Thru', scene, 'Ink-Thru',
                (590, 990), self.colorcode['thru'])
        
        if self.billboards:
            bb_in = self._new_rlayer_in('BB', scene, 'BB-Alpha',
                (0, 870), self.colorcode['bb'])
            
            bb_mat = self._new_rlayer_in('BB-Mat', scene, 'BB-Mat',
                (0, 590), self.colorcode['bb'])
            
        if self.inkthru and self.billboards:
            bb_mat_thru = self._new_rlayer_in('BB-Mat-Thru', scene, 'BB-Mat-Thru',
                (0, 280), self.colorcode['bbthru'])
    
        # Ink EXR
        exr_ink = tree.nodes.new('CompositorNodeOutputFile')
        exr_ink.name = 'exr_ink'
        exr_ink.label = 'Ink EXR'
        exr_ink.location = (1150,700)
        exr_ink.color = self.colorcode['ink']
        exr_ink.use_custom_color = True
        exr_ink.format.file_format = 'OPEN_EXR_MULTILAYER'
        exr_ink.format.color_mode = 'RGBA'
        exr_ink.format.color_depth = '16'
        exr_ink.format.exr_codec = 'ZIP'
        exr_ink.base_path = os.path.join(self.render_root, 'EXR', 
            self.designation, self.designation + '-Ink-f#####' + '.exr')
    
        # Create EXR Ink layers and connect
        if 'Image' in exr_ink.layer_slots:
            exr_ink.layer_slots.remove(exr_ink.inputs['Image'])
        exr_ink.layer_slots.new('Ink')
        tree.links.new(ink_in.outputs['Image'], exr_ink.inputs['Ink'])
        
        if self.inkthru:
            exr_ink.layer_slots.new('Ink-Thru')
            tree.links.new(thru_in.outputs['Image'], exr_ink.inputs['Ink-Thru'])
            
        if self.billboards:
            exr_ink.layer_slots.new('BB-Alpha')
            tree.links.new(bb_in.outputs['Alpha'], exr_ink.inputs['BB-Alpha'])
            
            exr_ink.layer_slots.new('BB-Mat')
            tree.links.new(bb_mat.outputs['IndexMA'], exr_ink.inputs['BB-Mat'])
            
        if self.inkthru and self.billboards:
            exr_ink.layer_slots.new('BB-Mat-Thru')
            tree.links.new(bb_mat_thru.outputs['IndexMA'], exr_ink.inputs['BB-Mat-Thru'])
            
    
        # Preview Compositing
        mix_shadow = tree.nodes.new('CompositorNodeMixRGB')
        mix_shadow.name = 'mix_shadow'
        mix_shadow.label = 'Mix-Shadow'
        mix_shadow.location = (510,1820)
        mix_shadow.color = self.colorcode['compos']
        mix_shadow.use_custom_color = True
        mix_shadow.blend_type = 'MULTIPLY'
        mix_shadow.inputs['Fac'].default_value = 0.6
        mix_shadow.use_clamp = True
        tree.links.new(paint_in.outputs['Image'], mix_shadow.inputs[1])
        tree.links.new(paint_in.outputs['Shadow'], mix_shadow.inputs[2])
    
        mix_reflect = tree.nodes.new('CompositorNodeMixRGB')
        mix_reflect.name  = 'mix_reflect'
        mix_reflect.label = 'Mix-Reflect'
        mix_reflect.location = (910, 1620)
        mix_reflect.color = self.colorcode['compos']
        mix_reflect.use_custom_color = True        
        mix_reflect.blend_type = 'ADD'
        mix_reflect.inputs['Fac'].default_value = 1.1
        mix_reflect.use_clamp = True
        tree.links.new(paint_in.outputs['Reflect'], mix_reflect.inputs[2])
     
        mix_emit = tree.nodes.new('CompositorNodeMixRGB')
        mix_emit.name  = 'mix_emit'
        mix_emit.label = 'Mix-Emit'
        mix_emit.location = (1110, 1520)
        mix_emit.blend_type = 'ADD'
        mix_emit.inputs['Fac'].default_value = 1.1
        mix_emit.use_clamp = True
        tree.links.new(mix_reflect.outputs['Image'], mix_emit.inputs[1])
        tree.links.new(paint_in.outputs['Emit'], mix_emit.inputs[2])
        
        if self.sepsky:
            sky_mix = tree.nodes.new('CompositorNodeMixRGB')
            sky_mix.name = 'sky_mix'
            sky_mix.label = 'Sky Mix'
            sky_mix.location = (710,1720)
            sky_mix.color = self.colorcode['sky']
            sky_mix.use_custom_color = True            
            sky_mix.blend_type = 'MIX'
            sky_mix.use_clamp = True
            tree.links.new(sky_in.outputs['Image'], sky_mix.inputs[1])
            tree.links.new(paint_in.outputs['Alpha'], sky_mix.inputs['Fac'])
            tree.links.new(mix_shadow.outputs['Image'], sky_mix.inputs[2])
            tree.links.new(sky_mix.outputs['Image'], mix_reflect.inputs[1])
        else:
            tree.links.new(mix_shadow.outputs['Image'], mix_reflect.inputs[1])
        
        if self.billboards:
            mat_idx = tree.nodes.new('CompositorNodeIDMask')
            mat_idx.name = "mat_idx"
            mat_idx.label = "BB-ID"
            mat_idx.location = (260, 670)
            mat_idx.index = 1
            mat_idx.use_antialiasing = True
            mat_idx.color = self.colorcode['bb']
            mat_idx.use_custom_color = True
            tree.links.new(bb_mat.outputs['IndexMA'], mat_idx.inputs['ID value'])
            
            combine_bb_ma = tree.nodes.new('CompositorNodeMath')
            combine_bb_ma.name = 'combine_bb_ma'
            combine_bb_ma.label = 'Material x BB'
            combine_bb_ma.location = (440,670)
            combine_bb_ma.color = self.colorcode['bb']
            combine_bb_ma.use_custom_color = True            
            combine_bb_ma.operation = 'MULTIPLY'
            combine_bb_ma.use_clamp = True
            tree.links.new(mat_idx.outputs['Alpha'], combine_bb_ma.inputs[0])
            tree.links.new(bb_in.outputs['Alpha'], combine_bb_ma.inputs[1])
                        
            invert_bb_mask = tree.nodes.new('CompositorNodeInvert')
            invert_bb_mask.name = 'invert_bb_mask'
            invert_bb_mask.label = 'Invert Mask'
            invert_bb_mask.location = (650,670)
            invert_bb_mask.color = self.colorcode['bb']
            invert_bb_mask.use_custom_color = True
            invert_bb_mask.invert_rgb = True
            tree.links.new(combine_bb_ma.outputs['Value'], invert_bb_mask.inputs['Color'])
            
            bb_ink_mask = tree.nodes.new('CompositorNodeMath')
            bb_ink_mask.name = 'bb_ink_mask'
            bb_ink_mask.label = 'BB Ink Mask'
            bb_ink_mask.location = (1150,1315)
            bb_ink_mask.color = self.colorcode['bb']
            bb_ink_mask.use_custom_color = True
            bb_ink_mask.operation = 'MULTIPLY'
            bb_ink_mask.use_clamp = True
            tree.links.new(invert_bb_mask.outputs['Color'], bb_ink_mask.inputs[0])
    
        blur_ink = tree.nodes.new('CompositorNodeBlur')
        blur_ink.name = 'blur_ink'
        blur_ink.label = 'Blur-Ink'
        blur_ink.location = (1620, 1110)
        blur_ink.color = self.colorcode['ink']
        blur_ink.use_custom_color = True        
        blur_ink.filter_type = 'FAST_GAUSS'
        blur_ink.size_x = 1.0
        blur_ink.size_y = 1.0
        blur_ink.use_extended_bounds = False
        blur_ink.inputs['Size'].default_value = 1.0
        
        if self.inkthru:
            merge_ink_ao = tree.nodes.new('CompositorNodeAlphaOver')
            merge_ink_ao.name = 'merge_ink'
            merge_ink_ao.label = 'Merge-Ink'
            merge_ink_ao.location = (1150,910)
            merge_ink_ao.color = self.colorcode['thru']
            merge_ink_ao.use_custom_color = True
            merge_ink_ao.use_premultiply = False
            merge_ink_ao.premul = 0.0
            merge_ink_ao.inputs['Fac'].default_value = 1.0 
            tree.links.new(ink_in.outputs['Image'], merge_ink_ao.inputs[1])
            tree.links.new(thru_in.outputs['Image'], merge_ink_ao.inputs[2])
            tree.links.new(merge_ink_ao.outputs['Image'], blur_ink.inputs['Image'])
        else:
            tree.links.new(ink_in.outputs['Image'], blur_ink.inputs['Image'])
    
        overlay_ink = tree.nodes.new('CompositorNodeAlphaOver')
        overlay_ink.name = 'Overlay Ink'
        overlay_ink.label = 'Overlay Ink'
        overlay_ink.location = (1820,1315)
        overlay_ink.color = self.colorcode['compos']
        overlay_ink.use_custom_color = True
        overlay_ink.use_premultiply = False
        overlay_ink.premul = 0.0
        overlay_ink.inputs['Fac'].default_value = 1.0
        tree.links.new(mix_emit.outputs['Image'], overlay_ink.inputs[1])
        tree.links.new(blur_ink.outputs['Image'], overlay_ink.inputs[2])
              
        if self.billboards:
            tree.links.new(ink_in.outputs['Alpha'], bb_ink_mask.inputs[1])
            tree.links.new(bb_ink_mask.outputs['Value'], overlay_ink.inputs['Fac'])
            
        if self.inkthru and self.billboards:
            mat_idx_thru = tree.nodes.new('CompositorNodeIDMask')
            mat_idx_thru.name = "mat_idx_thru"
            mat_idx_thru.label = "BB-ID-Thru"
            mat_idx_thru.location = (260, 425)
            mat_idx_thru.index = 1
            mat_idx_thru.use_antialiasing = True
            mat_idx_thru.color = self.colorcode['bbthru']
            mat_idx_thru.use_custom_color = True
            tree.links.new(bb_mat_thru.outputs['IndexMA'], mat_idx_thru.inputs['ID value'])            
            
            combine_bbthru_ma = tree.nodes.new('CompositorNodeMath')
            combine_bbthru_ma.name = 'combine_bbthru_ma'
            combine_bbthru_ma.label = 'Material x BB-Thru'
            combine_bbthru_ma.location = (440,425)
            combine_bbthru_ma.color = self.colorcode['bbthru']
            combine_bbthru_ma.use_custom_color = True            
            combine_bbthru_ma.operation = 'MULTIPLY'
            combine_bbthru_ma.use_clamp = True
            tree.links.new(mat_idx_thru.outputs['Alpha'], combine_bbthru_ma.inputs[0])
            tree.links.new(bb_in.outputs['Alpha'], combine_bbthru_ma.inputs[1])
                        
            invert_bbthru_mask = tree.nodes.new('CompositorNodeInvert')
            invert_bbthru_mask.name = 'invert_bbthru_mask'
            invert_bbthru_mask.label = 'Invert Mask'
            invert_bbthru_mask.location = (650,425)
            invert_bbthru_mask.color = self.colorcode['bbthru']
            invert_bbthru_mask.use_custom_color = True
            invert_bbthru_mask.invert_rgb = True
            tree.links.new(combine_bbthru_ma.outputs['Value'], invert_bbthru_mask.inputs['Color'])
            
            bb_thru_mask = tree.nodes.new('CompositorNodeMath')
            bb_thru_mask.name = 'bb_thru_mask'
            bb_thru_mask.label = 'BB Ink Thru Mask'
            bb_thru_mask.location = (1150,1115)
            bb_thru_mask.color = self.colorcode['bbthru']
            bb_thru_mask.use_custom_color = True
            bb_thru_mask.operation = 'MULTIPLY'
            bb_thru_mask.use_clamp = True
            tree.links.new(thru_in.outputs['Alpha'], bb_thru_mask.inputs[0])            
            tree.links.new(invert_bbthru_mask.outputs['Color'], bb_thru_mask.inputs[1])
            
            merge_bb_ink_masks = tree.nodes.new('CompositorNodeMath')
            merge_bb_ink_masks.name = 'merge_bb_ink_masks'
            merge_bb_ink_masks.label = 'Merge BB Ink Masks'
            merge_bb_ink_masks.location = (1415, 1215)
            merge_bb_ink_masks.color = self.colorcode['bbthru']
            merge_bb_ink_masks.use_custom_color = True
            merge_bb_ink_masks.operation = 'ADD'
            merge_bb_ink_masks.use_clamp = True
            tree.links.new(bb_ink_mask.outputs['Value'], merge_bb_ink_masks.inputs[0])
            tree.links.new(bb_thru_mask.outputs['Value'], merge_bb_ink_masks.inputs[1])
            
            tree.links.new(merge_bb_ink_masks.outputs['Value'], overlay_ink.inputs['Fac'])            
    
        composite = tree.nodes.new('CompositorNodeComposite')
        composite.name = 'Composite'
        composite.label = 'Preview Render'
        composite.location = (2050,1215)
        composite.color = self.colorcode['output']
        composite.use_custom_color = True
        composite.use_alpha = True
        composite.inputs['Alpha'].default_value = 1.0
        composite.inputs['Z'].default_value = 1.0
        tree.links.new(overlay_ink.outputs['Image'], composite.inputs['Image'])
        
    def _cfg_renderlayer(self, rlayer, 
            includes=False, passes=False, excludes=False, 
            layers=range(20)):
        # Utility to set all the includes and passes on or off, initially
        
        # Weird Includes (we never use these -- always have to turn these on explicitly)
        rlayer.use_zmask = False
        rlayer.invert_zmask = False
        rlayer.use_all_z = False
        
        # Includes
        rlayer.use_solid = includes
        rlayer.use_halo = includes
        rlayer.use_ztransp = includes
        rlayer.use_sky = includes
        rlayer.use_edge_enhance = includes
        rlayer.use_strand = includes 
        rlayer.use_freestyle = includes
        
        # Passes
        rlayer.use_pass_combined = passes
        rlayer.use_pass_z = passes
        rlayer.use_pass_vector = passes
        rlayer.use_pass_normal = passes  
        
        rlayer.use_pass_uv = passes
        rlayer.use_pass_mist = passes
        rlayer.use_pass_object_index = passes        
        rlayer.use_pass_material_index = passes 
        rlayer.use_pass_color = passes 
           
        rlayer.use_pass_diffuse = passes       
        rlayer.use_pass_specular = passes 
        rlayer.use_pass_shadow = passes    
        rlayer.use_pass_emit = passes  
        
        rlayer.use_pass_ambient_occlusion = passes
        rlayer.use_pass_environment = passes
        rlayer.use_pass_indirect = passes
         
        rlayer.use_pass_reflection = passes
        rlayer.use_pass_refraction = passes
        
        # Exclusions
        rlayer.exclude_specular = excludes
        rlayer.exclude_shadow = excludes
        rlayer.exclude_emit = excludes
        rlayer.exclude_ambient_occlusion = excludes
        rlayer.exclude_environment = excludes
        rlayer.exclude_indirect = excludes        
        rlayer.exclude_reflection = excludes
        rlayer.exclude_refraction = excludes
        
        for i in range(20):
            if i in layers:
                rlayer.layers[i] = True
            else:
                rlayer.layers[i] = False
        

    def cfg_paint(self, paint_layer, name="Paint"):
        
        self._cfg_renderlayer(paint_layer,
            includes=True, passes=False, excludes=False,
            layers = (0,1,2,3,4, 5,6,7, 10,11,12,13,14))
        
        # Includes         
        if self.sepsky:
            paint_layer.use_sky = False
            
        paint_layer.use_freestyle = False
    
        # Passes
        paint_layer.use_pass_combined = True
        paint_layer.use_pass_z = True
        paint_layer.use_pass_vector = True
        paint_layer.use_pass_normal = True
    
        paint_layer.use_pass_shadow = True
        paint_layer.exclude_shadow = True
    
        paint_layer.use_pass_emit = True
        paint_layer.exclude_emit = True
        
        paint_layer.use_pass_specular = True
        paint_layer.exclude_specular = True
    
        paint_layer.use_pass_reflection = True
        paint_layer.exclude_reflection = True

                
    def cfg_bbalpha(self, bb_render_layer):
        self._cfg_renderlayer(bb_render_layer,
            includes=False, passes=False, excludes=False,
            layers=(5,6, 14))
        # Includes
        bb_render_layer.use_solid = True
        bb_render_layer.use_ztransp = True
        # Passes
        bb_render_layer.use_pass_combined = True
        
    def cfg_bbmat(self, bb_mat_layer, thru=False):
        self._cfg_renderlayer(bb_mat_layer,
            includes=False, passes=False, excludes=False,
            layers=(0,1,2,3, 5,6,7, 10,11,12,13,14, 15,16))
        # Includes        
        bb_mat_layer.use_solid = True
        bb_mat_layer.use_ztransp = True
        
        # Passes
        bb_mat_layer.use_pass_combined = True
        bb_mat_layer.use_pass_material_index = True
        
        if not thru:
            bb_mat_layer.layers[4] = True
        
                
    def cfg_sky(self, sky_render_layer):
        self._cfg_renderlayer(sky_render_layer,
            includes=False, passes=False, excludes=False,
            layers=(0,1,2,3,4, 5,6,7, 10,11,12,13,14))
        # Includes
        sky_render_layer.use_sky = True
        # Passes
        sky_render_layer.use_pass_combined = True  
        
    
    def cfg_ink(self, ink_layer, name="Ink", thickness=3, color=(0,0,0)):
        self._cfg_renderlayer(ink_layer,
            includes=False, passes=False, excludes=False,
            layers=(0,1,2,3, 5,6,7, 10,11,12,13, 15,16))
        # Includes
        ink_layer.use_freestyle = True
        # Passes
        ink_layer.use_pass_combined = True
                
        # Freestyle
        ink_layer.freestyle_settings.crease_angle = 2.617944
        ink_layer.freestyle_settings.use_smoothness = True
        ink_layer.freestyle_settings.use_culling = True
        
        if len(ink_layer.freestyle_settings.linesets)>0:
            ink_layer.freestyle_settings.linesets[0].name = name
        else:
            ink_layer.freestyle_settings.linesets.new(name)

        lineset = ink_layer.freestyle_settings.linesets[name]
    
        self.cfg_lineset(lineset, thickness, color)
                        
        # Turn on the transparency layer for the regular ink:
        if ink_layer.name!='Ink-Thru':
            ink_layer.layers[4] = True
    

    def cfg_lineset(self, lineset, thickness=3, color=(0,0,0)):
        """
        Configure the lineset.
        """
        #lineset.name = 'NormalInk'
        # Selection options
        lineset.select_by_visibility = True
        lineset.select_by_edge_types = True
        lineset.select_by_image_border = True
        lineset.select_by_face_marks = False
        lineset.select_by_group = True
    
        # Visibility Option
        lineset.visibility = 'VISIBLE'
    
        # Edge Type Options
        lineset.edge_type_negation = 'INCLUSIVE'
        lineset.edge_type_combination = 'OR'
        lineset.select_silhouette = True
        lineset.select_border = True
        lineset.select_contour = True
        lineset.select_crease = True
        lineset.select_edge_mark = True
        lineset.select_external_contour = True
    
        # No Freestyle Group (If it exists)
        if 'No Freestyle' in bpy.data.groups:
            lineset.select_by_group = True
            lineset.group = bpy.data.groups['No Freestyle']
            lineset.group_negation = 'EXCLUSIVE'
        else:
            lineset.select_by_group = False 

        # Basic Ink linestyle:
        if 'Ink' in bpy.data.linestyles:
            lineset.linestyle = bpy.data.linestyles['Ink']
        else:
            lineset.linestyle.name = 'Ink'
            self.cfg_linestyle(lineset.linestyle, thickness, color)
        

    def cfg_linestyle(self, linestyle, thickness=INK_THICKNESS, color=INK_COLOR):
        # These are the only changeable parameters:
        linestyle.color = color 
        linestyle.thickness = thickness
    
        # The rest of this function just sets a common fixed style for "Lunatics!"
        linestyle.alpha = 1.0
        linestyle.thickness_position = 'CENTER'
        linestyle.use_chaining = True
        linestyle.chaining = 'PLAIN'
        linestyle.use_same_object = True
        linestyle.caps = 'ROUND'
    
        # ADD THE ALONG-STROKE MODIFIER CURVE
        # TODO: try using the .new(type=...) idiom to see if it works?
        # This probably needs the scene context set?
        # bpy.ops.scene.freestyle_thickness_modifier_add(type='ALONG_STROKE')
        
        linestyle.thickness_modifiers.new(type='ALONG_STROKE', name='taper')
        linestyle.thickness_modifiers['taper'].blend = 'MULTIPLY'
        linestyle.thickness_modifiers['taper'].mapping = 'CURVE'
    
        # These are defaults, so maybe unnecessary?
        linestyle.thickness_modifiers['taper'].influence = 1.0
        linestyle.thickness_modifiers['taper'].invert = False 
        linestyle.thickness_modifiers['taper'].value_min = 0.0
        linestyle.thickness_modifiers['taper'].value_max = 1.0
    
        # This API is awful, but what it has to do is to change the location of the first two
        # points (which can't be removed), then add a third point. Then update to pick up the
        # changes:
        linestyle.thickness_modifiers['taper'].curve.curves[0].points[0].location = (0.0,0.0)    
        linestyle.thickness_modifiers['taper'].curve.curves[0].points[1].location = (0.5,1.0)
        linestyle.thickness_modifiers['taper'].curve.curves[0].points.new(1.0,0.0)
        linestyle.thickness_modifiers['taper'].curve.update()

    