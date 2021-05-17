Design Notes
============

**ABX** or "Anansi Blender Extensions" is a catch-all Blender plugin to hold
current, custom, and experimental Blender extensions we use in Anansi
Spaceworks Studio projects. As we mature projects, we may choose to move
some of them into a more stable package or packages for wider distribution.

This file accumulates some design notes for additional projects to incorporate
into ABX, from my daily worklog notes.

Copy Animation
--------------

Options:

* Copy Active Action (Dopesheet animation)
* Copy All NLA Actions
* Apply a scale factor and copy animations instead of linking
* Floating-point scale factor

This was my first goal with ABX. Blender provides no simple way to copy
ALL of the animation from one object to another. This makes it very awkward
to refactor or repair broken animation rig proxies -- a problem that can
easily happen on a large project if things get renamed or files get moved.

Sometimes it's necessary to just create a new proxy from a character and
transfer the animation to it. "Copy Animation" allows that.

With the new rescaling feature (added April 2021), it also allows us to fix
scaling errors. For example, when we set up the "TR-Train" sequence in
"Lunatics!" S1E01, the file's scale was set up wrong -- the rest of the project
is in meter scale. But it was very awkward to try to change anything. It may
still be hard, but we should be able to apply scales using this tool.

References:

https://blender.stackexchange.com/questions/74183/how-can-i-copy-nla-tracks-from-one-armature-to-another
https://www.reddit.com/r/blender/comments/eu3w6m/guide_how_to_scale_a_rigify_rig/

 

Change Armature Proxy Name
--------------------------

An alternative approach would be to change the name of a proxy armature.

Seems to work, but not sure::
	>>> bpy.data.objects['Georgiana_Pinafore_proxy'].proxy.data.name = 'georgiana_pinafore-TEST'

I wonder if we can just fix the broken proxy case without having to copy?


Ink/Paint Configuration
-----------------------

The "Ink/Paint Config" operator allows us to set up standard shot files ink/paint
compositing, including several tricks I've come up with for "Lunatics!" to handle
transparency, billboard objects, and the sky background correctly with the ink/paint
setup.

So far (April 2021), it only supports "shot rendering" ("cam") files. I should
also provide support at least for setting up "shot compositing" ("compos") files,
which would take their input from the EXR files I create in the rendering phase.


Setup Compositing Files
-----------------------

    Also should be able to automate compositing and repacking setups
    - find ranges of numbered frame files (EXR or PNG streams, etc),
    and choose from them to set up ranges (maybe checkbox list?). 
    
    Command line script using Blender to repack EXR files from
    source EXR directory or glob to target directory or with new extension/prefix.  Currently can do this one by one in Blender,
    or by manually setting up ranges (but images must exist).
    
    Want to automatically detect what frames exist and render those.
    We can use this to repack bulky EXRs from 2.71 into a more
    compact format in 2.79.
    
 

Compare Armatures
-----------------

Getting bone objects from an armature in a proxy::

	bpy.data.objects['Georgiana_Pinafore_proxy'].proxy.data.bones[0]

Research how to walk the armature to find all the bone names (and check one against the other).
(Bones are not hierarchically organized in file. You have to trace the parent relationships
and construct the hierarchy)::

	[(root_A, [(A1, []), (A2, []), (A3, [(A3a,[]), (A3b,[])], (root_B, [])]

Then print indented & ordered::

	root_A
    	A1
    	A2
    	A3
        	A3a
        	A3b
	root_B

or as paths::

	root_A
	root_A/A1
	root_A/A2
	root_A/A3
	root_A/A3/A3a
	root_A/A3/A3b
	root_B

Find "missing" bones -- in src, but not tgt
Find "extra" bones   -- in tgt, but not src


Link Character into Scene
-------------------------

How to add a character along with proxy for animation. Can we do this with tagging on character libraries?

Could add render profile & automatic naming tool here to set up correct
rendering for project.
    
Initialize Files
----------------

Wizard to create basic types of files we need:

	- char
	- set
	- prop
	- anim
	- extra
	- mech
	- cam
	- compos


Freestyle Camera-Clipping Configuration
---------------------------------------

Create a companion scene from the current scene, with a Freestyle camera to
be used to generate ink lines, but with a shorter camera clipping range.

fs_scene_name = bpy.context.scene.name + '-FS'
CamOb = bpy.context.scene.camera
FsCamOb = bpy.context.scene.camera.copy()
FsCamOb.name = Cam.name + '-FS'


NewScene = bpy.data.scenes.new(name=bpy.context.scene.name + '-FS')
(Equivalent to bpy.ops.scene.new(type="NEW"), does not copy settings)

NewScene = bpy.ops.scene.new(type="EMPTY")
(Better. Copies settings. But does not allow setting the name. Named by the current scene
plus .001 -- probably will be .002 if there is already a .001)
NewScene = bpy.data.scenes[OldScene.name = '.001']

NewScene.name = OldScene.name + '-FS'

No settings!

Instead:
bpy.ops.scene.new(type="LINK_OBJECTS")
NewScene = bpy.context.scene  # Because ops updates the context
# OR
NewScene = bpy.data.scenes[OldScene.name + '.001']
# IF that name wasn't used

NewScene.name = OldScene.name + '-FS'

for ob in OldScene.objects:
     if ob != OldScene.camera:
         NewScene.objects.link(ob)

NewScene.objects.link(FsCamOb)
FsCamOb.data = FsCam.data.copy()
FsCamOb.data.name = FsCam.data.name + '-FS'

NewScene.objects.unlink(OldScene.camera)

FsCamOb.data.clip_end = 10.0  # Just setting it to 10 meters

Had to fix my script to name the Color and Ink input renderlayer nodes
(Now 'Color-In' and 'Ink-In'. Was just "Render Layer" and "Render Layer.001")

# Cross the streams!
OldScene.node_tree.nodes['Ink-In'].scene = NewScene

NewScene.render.layers['Ink'].use = True
if 'Ink-Thru' in NewScene.render.layers:
	NewScene.render.layers['Ink-Thru'].use = True
NewScene.render.layers['Color'].use = False

OldScene.render.layers['Color'].use = True
OldScene.render.layers['Ink'].use = False
if 'Ink-Thru' in OldScene.render.layers:
	OldScene.render.layers['Ink-Thru'].use = False

    