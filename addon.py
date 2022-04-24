"""
blender addon for seamlessly integrating nodelang into your material workflow

hopefully...
"""

from abc import ABC
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

  class Node(ABC):
    """A node of the Ast"""
    pass

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

def material_nodes_to_ast(material: bpy.types.Material, subfield: Optional[str] = None) -> Ast:
  module = Ast.Module()
  root = module

  tree = material.node_tree

  @dataclass
  class InputNode:
    node: bpy.types.Node
    source_socket: bpy.types.NodeSocketShader

  # link to the nodes it comes from
  link_sources: defaultdict[bpy.types.NodeLink, List[bpy.types.Node]] = defaultdict(list)
  # link to the nodes it goes to
  link_targets: defaultdict[bpy.types.NodeLink, List[bpy.types.Node]] = defaultdict(list)

  # FIXME: looks like there is in fact a link.to_socket.node property so this entire thing is unnecessary
  for n in tree.nodes:
    for o in n.outputs:
      link_sources[o].append(n)
    for i in n.inputs:
      link_targets[i].append(n)

  # map of a node to its inputs
  inputs_graph: Dict[bpy.types.Node, List[InputNode]] = defaultdict(list)

  for link in tree.links:
    source, *otherSources = link_sources[link]
    target, *otherTargets = link_targets[link]
    assert len(otherSources) == 0, "links must have one source node"
    assert len(otherTargets) == 0, "links must have one target node"
    inputs_graph[target].append(InputNode(source, link.from_socket))

  # maybe calling them nodes and codes is a good idea
  node_to_code: Dict[bpy.types.Node, Any] = {}

  def get_code_for_input(node: bpy.types.Node) -> Union[Ast.VarRef, Ast.Literal]:
    maybe_already_visited = node_to_code.get(node)
    if maybe_already_visited is not None: return maybe_already_visited

    ## handle primitives
    # TODO: use a mapping for this
    if node.type == "VALUE":
      node_to_code[node.name] = node.value

    ## handle compounds

    # create decl
    # TODO: assert there is not more than 1 input link
    args = [get_code_for_input(i.node, i.link[0].from_socket.name) if i.is_linked else i for i in node.inputs]
    # TODO: use generic node type map here
    compound = Ast.Call(name=node.name, args=args)
    # TODO: consolidate with Ast.StructAssignment
    decl = Ast.ConstDecl(name=node.name, comment=node.label, type=type, value=compound)
    root.prepend_decl(decl)
    node_to_code[node] = decl

    return Ast.VarRef(decl.name, [subfield] if subfield else [])

  # FIXME: so apparently you can have separate outputs for eevee/cycles, need to handle that somehow...
  material_out = next(n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL')
  get_code_for_input(material_out)


material_nodes_to_ast(bpy.data.materials["Test"])

functions = bpy.data.node_groups['NodeGroup'].nodes['Group Input']