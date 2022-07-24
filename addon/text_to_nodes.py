"""
blender addon for seamlessly integrating nodelang into your material workflow

hopefully...
"""

import sys

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, TypedDict, cast

from addon.blender_util import isinstance_bpy_prop_array
from . import ast
from .types import blender_material_node_to_operation, blender_material_type_to_primitive
from .bpy_wrap import bpy, in_blender
from .util import Ansi

def analyze_module(mod: ast.Module, targetGraph: bpy.types.Material) -> None:
  for decl in mod.decls:
    nodes = decl.to_blender_node()
    
  bpy.ops.node.add_node(type="ShaderNodeTexChecker", use_transform=True)

if in_blender:
  input_file = sys.stdin
  analyze_module(bpy.data.materials["Test"])


# functions = bpy.data.node_groups['NodeGroup'].nodes['Group Input']
