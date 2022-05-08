"""
blender addon for seamlessly integrating nodelang into your material workflow

hopefully...
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from . import ast
from .types import BlenderNodeType, blender_material_type_to_primitive
from .bpy_wrap import bpy, in_blender


def analyze_output_node(module: ast.Module, output_node: bpy.types.Node) -> ast.Module:
  root = module

  # maybe calling them nodes and codes is an interesting idea
  node_to_code: Dict[bpy.types.Node, Any] = {}

  def get_code_for_input(node: bpy.types.Node, subfield: Optional[str] = None) -> Union[ast.VarRef, ast.Literal]:
    maybe_already_visited = node_to_code.get(node)
    if maybe_already_visited is not None: return maybe_already_visited

    ## handle primitives
    # TODO: use a mapping for all node types
    if node.type == "VALUE":
      node_to_code[node.name] = node.value

    ## handle compounds (currently a vardecl is created for every non-trivial node... this will be removed)

    @dataclass(slots=True)
    class Input:
      # the node which this input comes from
      node: bpy.types.Node
      from_name: str
      from_type: str # TODO: make this an enum
      to_type: str

    # create decmporl
    # TODO: assert there is not more than 1 input link
    try_get_input = lambda i: Input(
      node=i.links[0].from_socket.node,
      # TODO: analyze cast if the types aren't the same
      from_name=i.links[0].from_socket.name,
      from_type=i.links[0].from_socket.name,
      to_type=i.type,
    # TODO: check defaults
    ) if i.is_linked else i.default_value

    inputs = map(try_get_input, node.inputs)
    args = [get_code_for_input(i.node, i.from_name) for i in inputs if i]
    # TODO: use generic node type map here
    compound = ast.Call(name=ast.Ident(node.name), args=args)

    type_ = blender_material_type_to_primitive(node.outputs[0].type) if node.outputs else None

    # TODO: consolidate with ast.StructAssignment
    decl = ast.ConstDecl(name=ast.Ident(node.name), comment=node.label, type=type_, value=compound)
    root.prepend_decl(decl)
    node_to_code[node] = decl

    return ast.VarRef(decl.name, [subfield] if subfield else [])

  get_code_for_input(output_node)


def analyze_material(material: bpy.types.Material) -> ast.Module:
  module = ast.Module()
  tree = material.node_tree
  is_unlinked = lambda n: all(not o.links for o in n.outputs)
  end_nodes = [n for n in tree.nodes if is_unlinked(n)]
  for end_node in end_nodes:
    analyze_output_node(module, end_node)
  return module


if in_blender:
  out_ast = analyze_material(bpy.data.materials["Test"])
  print(out_ast.serialize())

# functions = bpy.data.node_groups['NodeGroup'].nodes['Group Input']
