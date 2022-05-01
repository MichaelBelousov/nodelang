"""
Ast of nodelang for use in blender (and prototype)
"""

from abc import ABC
from dataclasses import dataclass
import typing
from typing import Dict, List, Literal, Optional, Union
from __future__ import annotations


# TODO: move types out of ast
primitive_types: List[PrimitiveType] = ['f32', 'i32', 'u32']

PrimitiveType = type(primitive_types)

class Struct:
  """A datatype"""
  members: List[Union[PrimitiveType, "Struct"]]

Type = Union[PrimitiveType, Struct]

primitive_literal_types = [str, int, float]
# python 3.11 required to unpack in a subscript
ArrayLiteral = List[str, int, float]
literal_types = [*primitive_literal_types, ArrayLiteral]
# ditto
Literal = Union[str, int, float, ArrayLiteral]

def isLiteral(val):
  return any(isinstance(val, T) for T in literal_types)

def serializeLiteral(literal: Literal) -> str:
  if isinstance(literal, list):
    return f"[{', '.join(serializeLiteral(l) for l in literal)}]"
  return str(literal)

class Node(ABC):
  """A node of the Ast"""
  pass

  def serialize(self) -> str:
    raise NotImplementedError()

@dataclass
class VarRef(Node):
  name: str
  derefs: List[str] # maybe convert this to binary dot operators

  def serialize(self):
    if not self.derefs:
      return self.name
    else:
      return f'{self.name}.{".".join(self.derefs)}'

Expr = Union[Literal, VarRef]

@dataclass
class Call(Node):
  name: str
  args: List[Expr]

  def serialize(self):
    return f'{self.name}({", ".join(a.serialize() for a in self.args)})'

@dataclass
class BinOp(Node):
  name: str
  left: Expr
  right: Expr
  op: typing.Literal["+", "-"]

  def serialize(self):
    return f'{self.name}({", ".join(self.args)})'

@dataclass
class ConstDecl(Node):
  name: str
  comment: Optional[str]
  type: Optional[Type]
  value: Union[Literal, VarRef]

  def serialize(self):
    return (
      (f'/// {self.comment}' + '\n' if self.comment else '')
      + f'const {self.name}'
      + (f': {self.type}' if self.type else '')
      + f' = {self.value.serialize()}'
    )

@dataclass
class StructAssignment(Node):
  variable: str
  field: Optional[str]
  value: Node

@dataclass
class Namespace(Node):
  decls: List[Node]
  decl_by_name: Dict[str, Node]

  def append_decl(self, decl: ConstDecl) -> None:
    self.decls.append(decl)
    self.decl_by_name[decl.name] = decl
  
  def prepend_decl(self, decl: ConstDecl) -> None:
    self.decls.insert(0, decl)
    self.decl_by_name[decl.name] = decl

  def serialize(self):
    return '\n'.join(d.serialize() for d in self.decls)

# A group of declarations
Group = Namespace

# The top level of the AST for a file
Module = Namespace
