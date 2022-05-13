"""
Ast of nodelang for use in blender (and prototype)
"""

from abc import ABC
from dataclasses import dataclass, field
import typing
from typing import Dict, List, Optional, ClassVar
import re

# FIXME: in python3.11 add a primitive_types_raw list and unpack it into the Literal type below
primitive_types_raw = []

PrimitiveType = typing.Literal['f32', 'i32', 'u32', 'b8', 'bsdf']

# TODO: move types out of ast
primitive_types = ['f32', 'i32', 'u32']

class Node(ABC):
  """A node in the Ast"""
  def serialize(self) -> str:
    raise NotImplementedError()

@dataclass(unsafe_hash=True, slots=True)
class Ident(Node):
  name: str
  quotes_not_needed_pattern: ClassVar[re.Pattern[str]] = re.compile(r'[a-zA-Z]\w*')
  def serialize(self):
    # TODO: escape quotes and space and nonprintables
    quotes_not_needed = Ident.quotes_not_needed_pattern.fullmatch(self.name) is not None
    if quotes_not_needed: return self.name
    else: return f"'{self.name}'"

@dataclass
class _Named:
  name: Ident

class Named(_Named):
  def __init__(self, name: str | Ident):
    super().__init__(name if isinstance(name, Ident) else Ident(name))

@dataclass
class Struct(Named):
  """A compound datatype"""
  members: List[PrimitiveType | "Struct"] = field(default_factory=list)

Type = PrimitiveType | Struct

# including None for now since not yet sure how to represent an empty optional shader
PrimitiveValue = str | int | float | bool | None | List["PrimitiveValue"]

@dataclass
class Literal(Node):
  val: PrimitiveValue

  def serialize(self) -> str:
    if isinstance(self.val, list):
      return f"[{', '.join(Literal.from_value(l).serialize() for l in self.val)}]"
    return str(self.val)

  @staticmethod
  def from_value(val: PrimitiveValue) -> "Literal":
    if not isinstance(val, (str, float, int, bool, list, type(None))):
      raise RuntimeError(f"unknown value '{val}' with type '{type(val)}' attempted to be used as a literal")
    return Literal(val)

@dataclass
class VarRef(Node, Named):
  derefs: List[str] = field(default_factory=list) # maybe convert this to binary dot operators

  def serialize(self):
    if not self.derefs:
      return self.name.serialize()
    else:
      return f'{self.name.serialize()}.{".".join(self.derefs)}'

# need this?
Expr = Literal | VarRef

@dataclass
class Call(Node, Named):
  args: List[Node]

  def serialize(self):
    arg_per_line = len(self.args) > 4
    nl = '\n'
    indent = '  ' # TODO: do real tree formatting
    return f'''{self.name.serialize()}({
      nl+indent if arg_per_line else ''
    }{(','+nl+indent if arg_per_line else ', ').join(a.serialize() for a in self.args)}{
      nl if arg_per_line else ''
    })'''

@dataclass
class BinOp(Node):
  op: typing.Literal['+', '-', '*', '/', '^', '^^', '^/', '**', '&', '|', '&&', '||']
  left: Node
  right: Node

  # TODO: this probably needs some serialization context in order to pretty print the op tree
  def serialize(self):
    return f'({self.left.serialize()} {self.op} {self.right.serialize()})'


@dataclass
class ConstDecl(Node):
  name: Ident
  value: Literal | VarRef
  comment: Optional[str]
  type: Optional[Type]
  
  def serialize_type(self) -> str:
    if not self.type: return ''
    elif isinstance(self.type, Struct): return self.type.name.serialize()
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
  decl_by_name: Dict[Ident, Node] = field(default_factory=dict)

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
