"""
blender addon for seamlessly integrating nodelang into your material workflow

hopefully...
"""

from ctypes import Union
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from __future__ import annotations
import bpy

PrimitiveType = str

primitive_types: List[PrimitiveType] = ['f32', 'i32', 'u32']

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
  @dataclass
  class Node:
    """A node of the Ast"""
    name: str
    first: Optional[Ast.Node]
    second: Optional[Ast.Node]
    third: Optional[Ast.Node]

  @dataclass
  class ConstDecl(Node):
    name: str
    comment: Optional[str]
    type: Type

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

  ArrayLiteral = List

  Literal = Union[str, int, float, ArrayLiteral]

# figure out how to do string enums in python typing
NodeType = Union[
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

  # maybe calling them nodes and codes is a good idea
  node_to_code: Dict[str, Any] = {}

  tree = material.node_tree

  def visit_node(node: bpy.types.Node) -> Union[Ast.ConstDecl, Ast.Literal]:
    # TODO: use a mapping for this
    if node.type == "VALUE":
      node_to_code[node.name] = node.value

    for links in node.inputs:
      assert len(links) <= 1, "can not have multiple input links"
      link, = links
      # probably better to just traverse all links and all nodes into a direct neighbor graph at startup
      node = next(n for n in tree.nodes if link in node.output.links) # need to map outputs to their links actually...
      types = [blender_type_to_primitive[socket.type] for socket in node.outputs]
      type = types[0] if len(node.outputs) == 1 else Struct(members=types)
      root.prepend_decl(Ast.ConstDecl(name=node.name, comment=node.label, type=type))
      input: Ast.ConstDecl = (
        node_to_code[node.name]
        if node.name in node_to_code
        else visit_node(node)
      )

    # FIXME: calculate input
    root.append_decl(Ast.StructAssignment(name=input.name, field=node.inputs[0], value=""))

  # FIXME: so apparently you can have separate outputs for eevee/cycles, need to handle that somehow...
  output = next(n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL')
  visit_node(output)

material_nodes_to_ast(bpy.data.materials["Test"])

functions = bpy.data.node_groups['NodeGroup'].nodes['Group Input']