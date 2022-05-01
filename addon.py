"""
blender addon for seamlessly integrating nodelang into your material workflow

hopefully...
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from __future__ import annotations
import bpy
from collections import defaultdict
from . import ast
from .util import freezeDict, FrozenDict

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

BlenderNodeType = Literal[
  "CUSTOM",
  "OUTPUT_MATERIAL",
]

# TODO: move to code/data/types module
@dataclass
class OpType():
  """A primitive operation (operator or function) in the context"""
  name: str
  op_type: Literal["binary", "unary", "function"]

node_types: Dict[BlenderNodeType, OpType] = {
  'CUSTOM': '',
  'OUTPUT_MATERIAL': '',
}

# list of generic nodes in blender (e.g. Math) which we specialize
generic_node_types: Dict[Tuple[BlenderNodeType, FrozenDict[str, Any]], OpType] = {
  ('MATH', freezeDict({'operation': 'ADD'})): OpType(name='+', op_type="binary"),
  ('MATH', freezeDict({'operation': 'SUB'})): OpType(name='-', op_type="binary"),
  ('MATH', freezeDict({'operation': 'ATAN2'})): OpType(name='atan2', op_type="function"),
  ('MATH', freezeDict({'operation': 'SIN'})): OpType(name='sin', op_type="function"),
}

def material_nodes_to_ast(material: bpy.types.Material, subfield: Optional[str] = None) -> ast.Node:
  module = ast.Module()
  root = module

  tree = material.node_tree

  @dataclass(slots=True, frozen=True)
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

  def get_code_for_input(node: bpy.types.Node) -> Union[ast.VarRef, ast.Literal]:
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
    compound = ast.Call(name=node.name, args=args)
    # TODO: consolidate with ast.StructAssignment
    decl = ast.ConstDecl(name=node.name, comment=node.label, type=type, value=compound)
    root.prepend_decl(decl)
    node_to_code[node] = decl

    return ast.VarRef(decl.name, [subfield] if subfield else [])

  # FIXME: I just need to find all nodes with no outputs and run on them
  # that's actually better considering there are orphan nodes in real graphs that must be kept for parity
  # Not to mention that the orphan node's placement is important for figuring out what it's meant to replace...
  material_out = next(n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL')
  get_code_for_input(material_out)

material_nodes_to_ast(bpy.data.materials["Test"])

functions = bpy.data.node_groups['NodeGroup'].nodes['Group Input']

# TODO: add an __init__.py probably with a share common module
