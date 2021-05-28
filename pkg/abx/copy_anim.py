# copy_anim.py
"""
Blender Python code to copy animation between armatures or proxy armatures.
"""

import bpy, bpy.types, bpy.utils, bpy.props

#----------------------------------------
## TOOLS
# This might be moved into another module later

def copy_object_animation(sourceObj, targetObjs,
        dopesheet=False, nla=False, rescale=False, scale_factor=1.0,
        report=print):
    """
    Copy Dope Sheet & NLA editor animation from active object to selected objects.
    Most useful with armatures. Assumes bones match. Can be rescaled in the process.
    
    From StackExchange post:
    https://blender.stackexchange.com/questions/74183/how-can-i-copy-nla-tracks-from-one-armature-to-another
    """
    for targetObj in targetObjs:
        if targetObj.animation_data is not None:
            targetObj.animation_data_clear()

        targetObj.animation_data_create()   

        source_animation_data = sourceObj.animation_data
        target_animation_data = targetObj.animation_data
        
        # copy the dopesheet animation (active animation)
        if dopesheet:
            report({'INFO'}, 'Copying Dopesheet animation')
            if source_animation_data.action is None:
                report({'WARNING'}, 
                    "CLEARING target dope sheet - old animation saved with 'fake user'")
                if target_animation_data.action is not None:
                    target_animation_data.action.use_fake_user = True
                target_animation_data.action = None
            else:
                if rescale:
                    target_animation_data.action = copy_animation_action_with_rescale(
                        source_animation_data.action, scale_factor)
                else:
                    target_animation_data.action = copy_animation_action_with_rescale(
                        source_animation_data.action, scale_factor)
                
                target_animation_data.action.name = targetObj.name + 'Action'
        
        if nla:
            report({'INFO'}, 'Copying NLA strips')
            if source_animation_data:
                # Create new NLA tracks based on the source
                for source_nla_track in source_animation_data.nla_tracks:
                    target_nla_track = target_animation_data.nla_tracks.new()
                    target_nla_track.name = source_nla_track.name
                    # In each track, create action strips base on the source
                    for source_action_strip in source_nla_track.strips:
                        
                        if rescale:
                            new_action = copy_animation_action_with_rescale(
                                    source_action_strip.action, scale_factor)
                        else:
                            new_action = source_action_strip.action
                        
                        target_action_strip = target_nla_track.strips.new(
                            new_action.name,
                            source_action_strip.frame_start,
                            new_action)   
                        
                        # For each strip, copy the properties -- EXCEPT the ones we
                        # need to protect or can't copy
                        # introspect property names (is there a better way to do this?)
                        props = [p for p in dir(source_action_strip) if
                                    not p in ('action',)
                                    and not p.startswith('__') and not p.startswith('bl_')
                                    and source_action_strip.is_property_set(p)
                                    and not source_action_strip.is_property_readonly(p)
                                    and not source_action_strip.is_property_hidden(p)]
                        for prop in props:
                            setattr(target_action_strip, prop, getattr(source_action_strip, prop))
                        

# Adapted from reference:
# https://www.reddit.com/r/blender/comments/eu3w6m/guide_how_to_scale_a_rigify_rig/
#

def reset_armature_stretch_constraints(rig_object):
    """
    Reset stretch-to constraints on an armature object - necessary after rescaling.
    """
    bone_count = 0
    for bone in rig_object.pose.bones:
        for constraint in bone.constraints:
            if constraint.type == "STRETCH_TO":
                constraint.rest_length = 0
                bone_count += 1
    return bone_count


def rescale_animation_action_in_place(action, scale_factor):
    """
    Rescale a list of animation actions by a scale factor (in-place).
    """
    #for fcurve in bpy.data.actions[action].fcurves:
    for fcurve in action.fcurves:
        data_path = fcurve.data_path
        if data_path.startswith('pose.bones[') and data_path.endswith('].location'):
            for p in fcurve.keyframe_points:
                p.co[1] *= scale_factor
                p.handle_left[1] *= scale_factor
                p.handle_right[1] *= scale_factor
    return action

def copy_animation_action_with_rescale(action, scale_factor):
    """
    Copy an animation action, rescaled.
    """
    new_action = action.copy()
    new_action.name = new_action.name[:-4]+'.rescale'
    return rescale_animation_action_in_place(new_action, scale_factor)


    

#----------------------------------------
