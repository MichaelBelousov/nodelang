"""
Utilities specific to blender
"""

from typing import Any


# TODO: figure out how to do this better
def isinstance_bpy_prop_array(x: Any) -> bool:
  return type(x).__name__ == 'bpy_prop_array'
