"""
blender addon for seamlessly integrating nodelang into your material workflow

hopefully...
"""

from ctypes import Union
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple
from __future__ import annotations
import bpy
from collections import defaultdict


primitive_types: List[PrimitiveType] = ['f32', 'i32', 'u32']

PrimitiveType = type(primitive_types)

blender_type_to_primitive = {
  'CUSTOM': '',
  'VALUE': 'f32',
  'INT': 'i32',
  'BOOLEAN': 'b1',
  'VECTOR': 'f32[3]',
  'STRING': 'str',
  'RGBA': 'f32[4]',
  'SHADER': 'shader',
  'IMAGE': 'f32[4]',
  'GEOMETRY': 'f32',
}

class Struct:
  """A datatype"""
  members: List[Union[PrimitiveType, "Struct"]]

Type = Union[PrimitiveType, Struct]

class Ast:
  ArrayLiteral = List
  Literal = Union[str, int, float, ArrayLiteral]

  @dataclass
  class Node:
    """A node of the Ast"""
    name: str
    first: Optional[Ast.Node]
    second: Optional[Ast.Node]
    third: Optional[Ast.Node]

  @dataclass
  class VarRef(Node):
    name: str
    derefs: List[str] # maybe convert this to binary dot operators

  Expr = Union[Ast.Literal, VarRef]

  @dataclass
  class Call(Node):
    name: str
    args: List[Ast.Expr]

  @dataclass
  class BinOp(Node):
    name: str
    left: Ast.Expr
    right: Ast.Expr
    op: Union["+", "-"]

  @dataclass
  class ConstDecl(Node):
    name: str
    comment: Optional[str]
    type: Type
    value: Union[Ast.Literal, Ast.VarRef]

  @dataclass
  class StructAssignment(Node):
    variable: str
    field: Optional[str]
    value: Ast.Node

  @dataclass
  class Namespace(Node):
    decls: List[Ast.Node]
    decl_by_name: Dict[str, Ast.Node]

    def append_decl(self, decl: Ast.ConstDecl) -> None:
      self.decls.append(decl)
      self.decl_by_name[decl.name] = decl
    
    def prepend_decl(self, decl: Ast.ConstDecl) -> None:
      self.decls.insert(0, decl)
      self.decl_by_name[decl.name] = decl

  # A group of declarations
  Group = Namespace

  # The top level of the AST for a file
  Module = Namespace

NodeType = Literal[
  "CUSTOM",
  "OUTPUT_MATERIAL",
]

@dataclass
class OpType():
  """A primitive operation (operator or function) in the context"""
  name: str
  op_type: Union["binary", "unary", "function"]

node_types: Dict[NodeType, OpType] = {
  'CUSTOM': '',
  'OUTPUT_MATERIAL': '',
}

# list of generic nodes with specializations
generic_node_types: Dict[Tuple[NodeType, Dict[str, Any]], OpType] = {
  ('MATH', {'operation': 'add'}): OpType(name='+', op_type="binary"),
  ('MATH', {'operation': 'sub'}): OpType(name='-', op_type="binary"),
  ('MATH', {'operation': 'atan2'}): OpType(name='atan2', op_type="function"),
  ('MATH', {'operation': 'sin'}): OpType(name='sin', op_type="function"),
}

def material_nodes_to_ast(material: bpy.types.Material) -> Ast:
  module = Ast.Module()
  root = module

  tree = material.node_tree

  # link to the nodes it comes from
  link_sources: defaultdict[bpy.types.NodeLink, List[bpy.types.Node]] = defaultdict(list)
  # link to the nodes it goes to
  link_targets: defaultdict[bpy.types.NodeLink, List[bpy.types.Node]] = defaultdict(list)

  for n in tree.nodes:
    for o in n.outputs:
      link_sources[o].append(n)
    for i in n.inputs:
      link_targets[i].append(n)

  # map of a node to its inputs
  inputs_graph: Dict[bpy.types.NodeLink, List[bpy.types.NodeLink]] = defaultdict(list)

  for link in tree.links:
    source, *otherSources = link_sources[link]
    target, *otherTargets = link_targets[link]
    assert len(otherSources) == 0, "links must have one source node"
    assert len(otherTargets) == 0, "links must have one target node"
    inputs_graph[target].append(source)

  # maybe calling them nodes and codes is a good idea
  node_to_code: Dict[bpy.types.Node, Any] = {}

  def get_code_for_input(node: bpy.types.Node) -> Union[Ast.VarRef, Ast.Literal]:
    maybe_already_visited = node_to_code.get(node)
    if maybe_already_visited is not None: return maybe_already_visited

    # handle primitives
    # TODO: use a mapping for this
    if node.type == "VALUE":
      node_to_code[node.name] = node.value

    # handle compounds

    # create decl
    args = [get_code_for_input(input_node) for input_node in inputs_graph[node]]
    decl = Ast.ConstDecl(name=node.name, comment=node.label, type=type, value=[])
    root.prepend_decl(decl)
    node_to_code[node] = decl

    in_node = link_sources[out_link]
    # TODO: cache outputs from links?
    node_output = next(o for o in in_node.outputs if o.links[0] == out_link)
    return Ast.VarRef(decl.name, [node_output.name])

    types = [blender_type_to_primitive[socket.type] for socket in node.outputs]
    type = (
      types[0]
      if len(node.outputs) == 1
      else Struct(members=types)
    )

    # FIXME: calculate input
    root.append_decl(Ast.StructAssignment(name=input.name, field=node.inputs[0], value=""))

  # FIXME: so apparently you can have separate outputs for eevee/cycles, need to handle that somehow...
  material_out = next(n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL')
  get_code_for_input(material_out)


material_nodes_to_ast(bpy.data.materials["Test"])

functions = bpy.data.node_groups['NodeGroup'].nodes['Group Input']