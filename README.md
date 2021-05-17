# abx
Anansi Blender Extensions (Add-On)

This is a collection of Blender studio tools used by Anansi Spaceworks productions, which is producing "Lunatics!" Project (http://lunatics.tv).

Current Features (Version 0.2.5):

3D View Tool Panels

=Copy Animation=

Allows animation to be copied from one armature (or proxy) to another, in bulk. It can copy the entire NLA editor contents as well as the "active action" (which is what is normally displayed in the Dopesheet). It can be set to transfer this animation directly or to (deep) copy it. When set to copy, an optional "scale factor" can be applied, which can be used to correctly scale animation to a new rig at a different (internal) scale.

This is primarily useful as a tool for correcting broken armatures (the most common case being a rig whose name has changed in the source file): you can create a new proxy from a character, copy the animation data over to it, and delete the original. In the process you can correct a scale error or give the proxy rig a new name.

= Ink/Paint Config

Sets up the scene, render layers, compositing nodes, and EXR/PNG output for the signature "Lunatics!" ink/paint compositing system, which uses Freestyle ink on a separate render layer and can support handling of transparent object with ink seen behind them ("Ink-Thru"), with a different ink style. There are also options for correctly processing alpha-transparent billboard objects so that ink lines are masked over the visible part of the billboard, but not the transparent parts. And it can optionally render the sky background on a separate layer, which allows the sky to be handled correctly in compositing.

This is a very specific tool intended to automate our most common configurations. It's not meant to be overly flexible.

== Scene Properties Panel

Currently supports "Lunatics Properties" which provide a systematic naming scheme for the file. Should be used to set up the correct Series, Episode, Sequence, Block, and Shot settings for the current scene before running Ink/Paint Config -- it uses this data to name the scene and output image directories for rendering.

The shot naming system is hard-coded in this version of ABX. In later versions, the YAML data system will interpret a "project_schema" in your project source files to determine how scenes and files should be named.

== Render Properties Panel

Provides "Render Profiles" with our most common pre-visualization renders and the full render for the Ink/Paint EXR output. These are currently hard-coded.
A future version will allow these to be customized from YAML files within your animation project files.
