"""
blender addon for seamlessly integrating nodelang into your material workflow

hopefully...
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Type, TypeVar, TypedDict, cast
from copy import copy

from addon.blender_util import isinstance_bpy_prop_array
from . import ast
from .types import blender_material_node_to_operation, blender_material_type_to_primitive
from .bpy_wrap import bpy, in_blender

class Referrer(TypedDict):
  node: bpy.types.ShaderNode
  link: bpy.types.NodeLink


@dataclass(slots=True)
class ProcessedNodesCollection:
  namespace: ast.Namespace
  # maybe calling them nodes and codes is an interesting idea
  node_to_code: Dict[bpy.types.ShaderNode, ast.Node] = field(default_factory=dict)

  # TODO: maybe just inherit from dict
  def get(self, k: bpy.types.ShaderNode):
    return self.node_to_code.get(k)

  def __getitem__(self, k: bpy.types.ShaderNode):
    return self.node_to_code[k]

  # TODO: deprecate, require consumers use add_node
  def __setitem__(self, k: bpy.types.ShaderNode, v: ast.Node):
    self.node_to_code[k] = v

  def ref_node_and_get(self, node: bpy.types.ShaderNode, referrer: Referrer):
    """get a node if it exists, if it exists, promote it if necessary"""
    if node in self.node_to_code:
      self._promote(node, referrer)
    return self.node_to_code.get(node)

  def _promote(self, node: bpy.types.ShaderNode, referrer: Referrer) -> None:
    """promote an ast node within the namespace, usually to a variable"""
    code = self.node_to_code[node]
    match code:
      case ast.VarRef() | ast.ConstDecl():
        pass
      case ast.Literal() | ast.BinOp():
        name = ast.Ident(referrer["link"].from_socket.name)
        value = copy(code)
        decl = ast.ConstDecl(name, value)
        self.inplace_become(code, ast.VarRef(name))
        # FIXME: determine if the target ever exists at all
        referring_code = self.node_to_code.get(referrer["node"])
        self.namespace.prepend_decl(decl, cast(ast.ConstDecl, referring_code))
      case _:
        raise RuntimeError(f"unhandled promotion case, {code.__class__.__name__}")

  @staticmethod
  def inplace_become(node: ast.Node, replacement: ast.Node) -> None:
    """must become a compatible syntactical construct"""
    node.__class__ = replacement.__class__
    node.__dict__ = replacement.__dict__  # could clear+update but this should be safe


def analyze_output_node(node_to_code: ProcessedNodesCollection, output_node: bpy.types.ShaderNode) -> ast.Module:

  def get_code_for_input(node: bpy.types.ShaderNode, referrer: Optional[Referrer] = None) -> ast.VarRef | ast.Literal:
    if referrer is not None:
      maybe_already_visited = node_to_code.ref_node_and_get(node, referrer)
      if maybe_already_visited is not None: return maybe_already_visited


    ## handle primitives
    # TODO: use a mapping (or a match) for all node types
    if isinstance(node, bpy.types.ShaderNodeValue):
      node_to_code[node] = node.color

    ## handle compounds (currently a vardecl is created for every non-trivial node... this will be removed)
    # TODO: use pyenv to force python version to match that in blender
    @dataclass(slots=True)
    class Input:
      # the node which this input comes from
      node: bpy.types.Node
      link: bpy.types.NodeLink
      from_name: str
      from_type: str # TODO: make this an enum
      to_type: str

    # TODO: move to some module for dealing with blender nodes
    def get_default_value(i: bpy.types.NodeSocket) -> Any:
      # if hasattr(i, 'default_value'):
      if isinstance(i, (bpy.types.NodeSocketFloat, bpy.types.NodeSocketBool, bpy.types.NodeSocketColor)):
        if isinstance_bpy_prop_array(i.default_value):
          return ast.Literal.from_value(list(i.default_value))
        return ast.Literal.from_value(i.default_value)
      return ast.Literal.from_value(None)

    # TODO: might need to check properties of node against its base class to see if any extra properties are acting as dropdowns...
    # or just figure out how to get the dropdown properties
    def get_input(i: bpy.types.NodeSocketShader) -> Input:
      if i.is_linked:
      # TODO: assert there is not more than 1 input link
        assert len(i.links) == 1, "there can only be one input link if it is linked"
        return Input(
          node=i.links[0].from_socket.node,
          link=i.links[0],
          # TODO: analyze cast if the types aren't the same
          from_name=i.links[0].from_socket.name,
          from_type=i.links[0].from_socket.name,
          to_type=i.type,
        )
      else:
        # TODO: defaults should probably not be listed for most operations, in favor of requiring some kind of named arguments
        # e.g. binary operators require default args but functions require named args like `principled_shader(translucency=0.56)`
        return get_default_value(i)

    inputs = [get_input(i) for i in node.inputs if i.enabled]
    # TODO: this could be cleaned up
    args = [get_code_for_input(i.node, {'node': node, 'link': i.link}) if isinstance(i, Input) else i for i in inputs]
    compound = blender_material_node_to_operation(node)(args)

    type_ = blender_material_type_to_primitive(node.outputs[0].type) if node.outputs else None

    if isinstance(node, bpy.types.ShaderNodeMath):
      node_to_code[node] = compound
      return compound
    else:
      # TODO: consolidate with ast.StructAssignment?
      decl = ast.ConstDecl(name=ast.Ident(node.name), comment=node.label, type=type_, value=compound)
      node_to_code.namespace.append_decl(decl)
      node_to_code[node] = decl
      subfields = []
      if referrer:
        subfields = [referrer["link"].from_socket.name]
      return ast.VarRef(decl.name, subfields)

  get_code_for_input(output_node)

  return node_to_code


def analyze_material(material: bpy.types.Material) -> ast.Module:
  module = ast.Module()
  tree = material.node_tree
  no_output_links: Callable[[bpy.types.Node], bool] = lambda n: all(not o.links for o in n.outputs)
  end_nodes = [n for n in tree.nodes if no_output_links(n)]

  node_to_code = ProcessedNodesCollection(module)

  for end_node in end_nodes:
    analyze_output_node(node_to_code, end_node)

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
