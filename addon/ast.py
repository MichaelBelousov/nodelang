"""
Ast of nodelang for use in blender (and prototype)
"""

from abc import ABC
from dataclasses import dataclass, field, InitVar
import typing
from typing import Dict, List, Literal, Optional, Union, ClassVar
import re

# FIXME: in python3.11 add a primitive_types_raw list and unpack it into the Literal type below
primitive_types_raw = []

PrimitiveType = Literal['f32', 'i32', 'u32']

# TODO: move types out of ast
primitive_types = ['f32', 'i32', 'u32']

class Node(ABC):
  """A node in the Ast"""
  def serialize(self) -> str:
    raise NotImplementedError()

# slots=True?
@dataclass(unsafe_hash=True)
class Ident(Node):
  name: str
  quotes_not_needed_pattern: ClassVar[re.Pattern] = re.compile(r'[a-zA-Z]\w*')
  def serialize(self):
    # TODO: escape quotes and space and nonprintables
    quotes_not_needed = Ident.quotes_not_needed_pattern.fullmatch(self.name) is not None
    if quotes_not_needed: return self.name
    else: return f"'{self.name}'"

@dataclass
class _Named:
  name: Ident

class Named(_Named):
  def __init__(self, name: Union[str, Ident]):
    super().__init__(name if isinstance(name, Ident) else Ident(name))

@dataclass
class Struct(Named):
  """A compound datatype"""
  members: List[Union[PrimitiveType, "Struct"]] = field(default_factory=[])

Type = Union[PrimitiveType, Struct]

primitive_literal_types = [str, int, float, bool]
# python 3.11 required to unpack in a subscript
ArrayLiteral = Union[List[str], List[int], List[float], List[bool]]
literal_types = [*primitive_literal_types, ArrayLiteral]
# ditto
Literal = Union[str, int, float, bool, ArrayLiteral]

def isLiteral(val):
  return any(isinstance(val, T) for T in literal_types)

def serializeLiteral(literal: Literal) -> str:
  if isinstance(literal, list):
    return f"[{', '.join(serializeLiteral(l) for l in literal)}]"
  return str(literal)

@dataclass
class VarRef(Node, Named):
  derefs: List[str] = field(default_factory=list) # maybe convert this to binary dot operators

  def serialize(self):
    if not self.derefs:
      return self.name.serialize()
    else:
      return f'{self.name.serialize()}.{".".join(self.derefs)}'

Expr = Union[Literal, VarRef]

@dataclass
class Call(Node, Named):
  args: List[Expr]

  def serialize(self):
    return f'{self.name.serialize()}({", ".join(a.serialize() for a in self.args)})'

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
  name: Ident
  value: Union[Literal, VarRef]
  comment: Optional[str]
  type: Optional[Type]
  
  def serialize_type(self) -> str:
    if not self.type: return ''
    elif isinstance(self.type, Struct): return self.type.name
    else: return self.type

  def serialize(self):
    return (
      (f'/// {self.comment}' + '\n' if self.comment else '')
      + f'const {self.name.serialize()}'
      + (f': {self.serialize_type()}' if self.type else '')
      + f' = {self.value.serialize()}'
    )

@dataclass
class StructAssignment(Node):
  variable: str
  field: Optional[str]
  value: Node

@dataclass
class Namespace(Node):
  decls: List[Node] = field(default_factory=list)
  decl_by_name: Dict[str, Node] = field(default_factory=dict)

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
