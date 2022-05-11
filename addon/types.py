
from typing import Any, List, Literal, Dict, Tuple
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

# TODO: remove
node_types: Dict[BlenderNodeType, OpType] = {
  'CUSTOM': '',
  'OUTPUT_MATERIAL': '',
}

# blender nodes with arguments to their specialized operation
generic_node_types: Dict[Tuple[BlenderNodeType, FrozenDict[str, Any]], 'Function[ast.Node, List[ast.Node]]'] = {
  ('BSDF_PRINCIPLED', freezeDict({})):          lambda args: ast.Call(ast.Ident('pbr_shader'), args),
  ('MATH', freezeDict({'operation': 'ADD'})):   lambda args: ast.BinOp('+', *args),
  ('MATH', freezeDict({'operation': 'SUB'})):   lambda args: ast.BinOp('-', *args),
  ('MATH', freezeDict({'operation': 'MULTIPLY'})):   lambda args: ast.BinOp('*', *args),
  ('MATH', freezeDict({'operation': 'DIV'})):   lambda args: ast.BinOp('/', *args),
  ('MATH', freezeDict({'operation': 'ATAN2'})): lambda args: ast.Call(ast.Ident('atan2'), args),
  ('MATH', freezeDict({'operation': 'SIN'})):   lambda args: ast.Call(ast.Ident('sin'), args),
  # TODO: need a better way to output this...?
  ('OUTPUT_MATERIAL', freezeDict({})):          lambda args: ast.Call(ast.Ident('output'), args),
}

def blender_material_node_to_operation(node: bpy.types.Node) -> 'Function[ast.Node, List[ast.Node]]':
  # linear search for now, probably better to do more efficient subset equality
  for (blender_node_type, required_props), op_maker in generic_node_types.items():
    if blender_node_type == node.type and all(getattr(node, k, object()) == v for k,v in required_props):
      return op_maker
  raise NotImplementedError(f"node type was '{node.type}', operation was '{node.operation}'")
