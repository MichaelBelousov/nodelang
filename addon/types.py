
from typing import Literal, Dict
from . import ast

BlenderNodeType = Literal[
  "CUSTOM",
  "OUTPUT_MATERIAL",
]

_blender_type_to_primitive_map: Dict[BlenderNodeType, ast.Type] = {
  'CUSTOM': '',
  'VALUE': 'f32',
  'INT': 'i32',
  'BOOLEAN': 'b8',
  'VECTOR': 'f32[3]',
  'STRING': 'str',
  'RGBA': 'f32[4]',
  'SHADER': 'shader',
  'IMAGE': 'f32[4]',
  'GEOMETRY': 'f32',
}

def blender_type_to_primitive(type_: str) -> ast.Type:
  return _blender_type_to_primitive_map[type_]
