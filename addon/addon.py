"""
blender addon for seamlessly integrating nodelang into your material workflow

hopefully...
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from addon.blender_util import isinstance_bpy_prop_array
from . import ast
from .types import BlenderNodeType, blender_material_node_to_operation, blender_material_type_to_primitive
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

    # TODO: move to some module for dealing with blender nodes
    def get_default_value(i: bpy.types.NodeSocket) -> Any:
      if hasattr(i, 'default_value'):
        if isinstance_bpy_prop_array(i.default_value):
          return ast.Literal.from_value(list(i.default_value))
        return ast.Literal.from_value(i.default_value)
      return ast.Literal.from_value(None)

    # TODO: might need to check properties of node against its base class to see if any extra properties are acting as dropdowns...
    # or just figure out how to get the dropdown properties
    # TODO: assert there is not more than 1 input link
    get_input = lambda i: Input(
      node=i.links[0].from_socket.node,
      # TODO: analyze cast if the types aren't the same
      from_name=i.links[0].from_socket.name,
      from_type=i.links[0].from_socket.name,
      to_type=i.type,
    # TODO: defaults should probably not be listed for most operations, in favor of requiring some kind of named arguments
    # e.g. binary operators require default args but functions require named args like `principled_shader(translucency=0.56)`
    ) if i.is_linked else get_default_value(i)

    inputs = [get_input(i) for i in node.inputs if i.enabled]
    # TODO: this could be cleaned up
    args = [get_code_for_input(i.node, i.from_name) if isinstance(i, Input) else i for i in inputs]
    compound = blender_material_node_to_operation(node)(args)

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

# TEMP: for prettier output in tests
ansi_color_yellow = "\033[0;33m"
ansi_color_white = "\033[0;37m"

if in_blender:
  out_ast = analyze_material(bpy.data.materials["Test"])
  print(ansi_color_yellow)
  print(out_ast.serialize())
  print(ansi_color_white)

# functions = bpy.data.node_groups['NodeGroup'].nodes['Group Input']
