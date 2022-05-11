"""
this module re-exports bpy with some wrapping for some environments
"""

from addon.util import IgnoreDerefs


try:
  in_blender = True
  import bpy
  # FIXME: need to add a stub file to use bpy.types instead of this directly
  import bpy_types

except ModuleNotFoundError:
  # raise Exception("not running in blender")
  # TODO: throw error when not testing
  in_blender = False
  bpy = IgnoreDerefs()

__all__ = ['bpy', 'bpy_types']
