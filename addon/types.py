
from typing import Any, Callable, List, Literal, Dict, Optional, Tuple
from dataclasses import dataclass
from . import ast
from .util import FrozenDict, freezeDict
from .bpy_wrap import bpy

BlenderNodeType = Literal[
  'CUSTOM',
  'VALUE',
  'INT',
  'BOOLEAN',
  'VECTOR',
  'STRING',
  'RGBA',
  'SHADER',
  'IMAGE',
  'GEOMETRY',
]

# TODO: use class(Enum) pattern
BlenderNodeTypeEnum = Literal[
  'MATH',
  'BSDF_PRINCIPLED',
  'OUTPUT_MATERIAL',
]

_blender_material_type_to_primitive_map: Dict[BlenderNodeType, ast.Type] = {
  'CUSTOM': '',
  'VALUE': 'f32',
  'INT': 'i32',
  'BOOLEAN': 'b8',
  'VECTOR': 'f32[3]',
  'STRING': 'str',
  'RGBA': 'f32[4]',
  'SHADER': 'bsdf', # not actually accurate, there are more shader types than just bsdf
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

MaybeNamedArgs = List[Tuple[Optional[str], ast.Node]]

def ignore_name(namedArgs: MaybeNamedArgs) -> List[ast.Node]:
  return [a[1] for a in namedArgs]

def from_named(namedArgs: MaybeNamedArgs) -> List[ast.NamedArg]:
  """from a NamedArgs list create an actual ast slice"""
  if len(namedArgs) > 0:
    assert namedArgs[0][0] is not None, "optional name not supported for this type"
  return [ast.NamedArg(ast.Ident(n), a) for n, a in namedArgs]

# NOTE: possibly replace this with a `match` block that allows generics?
# blender nodes with arguments to their specialized operation
generic_node_types: Dict[Tuple[BlenderNodeTypeEnum, FrozenDict[str, Any]],
                         Callable[[MaybeNamedArgs], ast.Node]] = {
  ('BSDF_PRINCIPLED', freezeDict({})):          lambda args: ast.Call(ast.Ident('pbr_shader'), from_named(args)),
  ('MATH', freezeDict({'operation': 'ADD'})):   lambda args: ast.BinOp('+', *ignore_name(args)),
  ('MATH', freezeDict({'operation': 'SUB'})):   lambda args: ast.BinOp('-', *ignore_name(args)),
  ('MATH', freezeDict({'operation': 'MULTIPLY'})):   lambda args: ast.BinOp('*', *ignore_name(args)),
  ('MATH', freezeDict({'operation': 'DIV'})):   lambda args: ast.BinOp('/', *ignore_name(args)),
  ('MATH', freezeDict({'operation': 'ATAN2'})): lambda args: ast.Call(ast.Ident('atan2'), ignore_name(args)),
  ('MATH', freezeDict({'operation': 'SIN'})):   lambda args: ast.Call(ast.Ident('sin'), ignore_name(args)),
  # TODO: need a better way to output this...?
  ('OUTPUT_MATERIAL', freezeDict({})):          lambda args: ast.Call(ast.Ident('output'), from_named(args)),
}

def blender_material_node_to_operation(node: bpy.types.ShaderNode) -> Callable[[List[ast.Node]], ast.Node]:
  # linear search for now, probably better to do more efficient subset equality
  for (blender_node_type, required_props), op_maker in generic_node_types.items():
    if blender_node_type == node.type and all(getattr(node, k, object()) == v for k,v in required_props):
      return op_maker
  raise NotImplementedError(f"node type was '{node.type}', operation was '{node.operation}'")
