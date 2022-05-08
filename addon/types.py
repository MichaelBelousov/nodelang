
from typing import Any, Literal, Dict, Tuple
from dataclasses import dataclass
from . import ast
from .util import FrozenDict, freezeDict
from .bpy_wrap import bpy

BlenderNodeType = Literal[
  "CUSTOM",
  "OUTPUT_MATERIAL",
]

_blender_material_type_to_primitive_map: Dict[BlenderNodeType, ast.Type] = {
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

def blender_material_type_to_primitive(type_: str) -> ast.Type:
  return _blender_material_type_to_primitive_map[type_]

@dataclass
class OpType():
  """A primitive operation (operator or function) in the context"""
  name: str
  op_type: Literal["binary", "unary", "function"]

node_types: Dict[BlenderNodeType, OpType] = {
  'CUSTOM': '',
  'OUTPUT_MATERIAL': '',
}

# blender nodes with arguments to their specialized operation
generic_node_types: Dict[Tuple[BlenderNodeType, FrozenDict[str, Any]], OpType] = {
  ('BSDF_PRINCIPLED', freezeDict({})):          OpType(name='pbr_shader', op_type='function'),
  ('MATH', freezeDict({'operation': 'ADD'})):   OpType(name='+', op_type='binary'),
  ('MATH', freezeDict({'operation': 'SUB'})):   OpType(name='-', op_type='binary'),
  ('MATH', freezeDict({'operation': 'ATAN2'})): OpType(name='atan2', op_type='function'),
  ('MATH', freezeDict({'operation': 'SIN'})):   OpType(name='sin', op_type='function'),
}

def blender_material_node_to_operation(node: bpy.types.Node) -> OpType:
  # linear search for now, probably better to do more efficient subset equality
  for (blender_node_type, required_props), op in generic_node_types.items():
    if blender_node_type == node.type and all(node[k] == v for k,v in required_props.items()):
      return op
  raise NotImplementedError()
