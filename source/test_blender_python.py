"""
File is used to test the vscode-blender-connection.
Tooltips should work after installing fake-bpy-module.

ctrl-shift-p -> type blender -> blender:start (chose your blennder installation)
Then blender:Run script

Hint: Change your key preferences for running the scripts in VSCode.
"""
import bpy

bpy.ops.mesh.primitive_cube_add(size=10)

cube1 = bpy.context.active_object
cube1.location.z = 3

