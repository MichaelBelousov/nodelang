"""
Ast of nodelang for use in blender (and prototype)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import typing
from typing import cast, Dict, List, Optional, ClassVar
import re
import unittest

from .parser import MaybeParsed, ParseContext, ParseError, TokenizeErr
from . import token

# FIXME: in python3.11 add a primitive_types_raw list and unpack it into the Literal type below
primitive_types_raw = []

PrimitiveType = typing.Literal['f32', 'i32', 'u32', 'b8', 'bsdf']

# TODO: move types out of ast
primitive_types = ['f32', 'i32', 'u32']

@dataclass(slots=True)
class SerializeCtx:
  outstream: str = ""
  indent_level: int = 0
  # TODO: need to build the string here and keep track of how large the
  # current line is to control wrapping

  def write(self, s: str) -> None:
    """write out a string, (performing formatting implicitly in this subclass)"""
    pass

class Node(ABC):
  """
  A node in the Ast.

  NOTE: slots are not allowed since these need to be fully mutable, some upstream consumers
  [ab]use that precondition to dynamically restructure the ast while building it
  For performance might want to use slots and include a higher level referencing node that
  can have its type changed.
  """
  start: int
  end: int
  src: str

  def slice(self) -> str:
    return self.src[self.start:self.end]

  @abstractmethod
  def serialize(self, c: SerializeCtx = SerializeCtx()) -> str:
    pass

@dataclass(unsafe_hash=True)
class Ident(Node):
  name: str
  quotes_not_needed_pattern: ClassVar[re.Pattern[str]] = re.compile(r'[a-zA-Z]\w*')

  def serialize(self, c: SerializeCtx = SerializeCtx()):
    # TODO: escape quotes and space and nonprintables
    quotes_not_needed = Ident.quotes_not_needed_pattern.fullmatch(self.name) is not None
    if quotes_not_needed: return self.name
    else: return f"'{self.name}'"
  
  @staticmethod
  def parse(pctx: ParseContext) -> MaybeParsed["Ident"]:
    tok = pctx.try_consume_tok_type(token.Type.ident)
    # TODO: create a zig-like _try function
    if tok is None or isinstance(tok, ParseError):
      return tok
    return Ident(cast(token.Ident, tok.tok).name)

class _TestIdent(unittest.TestCase):
  def test_parse(self):
    pctx = ParseContext("hello const")
    parsed = Ident.parse(pctx)
    self.assertIsNotNone(parsed)
    self.assertEqual("hello", parsed.name)

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

  def serialize(self, c: SerializeCtx = SerializeCtx()) -> str:
    if isinstance(self.val, list):
      return f"[{', '.join(Literal.from_value(l).serialize(c) for l in self.val)}]"
    return str(self.val)

  @staticmethod
  def from_value(val: PrimitiveValue) -> "Literal":
    if not isinstance(val, (str, float, int, bool, list, type(None))):
      raise RuntimeError(f"unknown value '{val}' with type '{type(val)}' attempted to be used as a literal")
    return Literal(val)

@dataclass
class VarRef(Node, Named):
  derefs: List[str] = field(default_factory=list) # maybe convert this to binary dot operators

  def serialize(self, c: SerializeCtx = SerializeCtx()):
    if not self.derefs:
      return self.name.serialize(c)
    else:
      return f'{self.name.serialize(c)}.{".".join(self.derefs)}'

# need this (yes)
Expr = Literal | VarRef # | Call | BinOp

@dataclass
class NamedArg(Node, Named):
  val: Expr

  def serialize(self, c: SerializeCtx = SerializeCtx()):
    return f".{self.name.serialize(c)}={self.val.serialize(c)}"

@dataclass
class Call(Node, Named):
  args: List[NamedArg | Expr]

  def serialize(self, c: SerializeCtx = SerializeCtx()):
    arg_per_line = len(self.args) > 4
    nl = '\n'
    indent = '  ' # TODO: do real tree formatting
    return f'''{self.name.serialize(c)}({
      nl+indent if arg_per_line else ''
    }{(','+nl+indent if arg_per_line else ', ').join(a.serialize(c) for a in self.args)}{
      nl if arg_per_line else ''
    })'''

@dataclass
class BinOp(Node):
  op: typing.Literal['+', '-', '*', '/', '^', '^^', '^/', '**', '&', '|', '&&', '||']
  left: Node
  right: Node

  # TODO: instead of always wrapping in `()` that should be a part of the AST not of the serialization
  # TODO: print print using serialization context
  def serialize(self, c: SerializeCtx = SerializeCtx()):
    return f'({self.left.serialize(c)} {self.op} {self.right.serialize(c)})'


@dataclass
class ConstDecl(Node):
  name: Ident
  value: Literal | VarRef | BinOp # TODO: this should really be an Expr sum type
  comment: Optional[str] = None
  type: Optional[Type] = None
  
  def serialize_type(self, c: SerializeCtx) -> str:
    if not self.type: return ''
    elif isinstance(self.type, Struct): return self.type.name.serialize(c)
    else: return self.type

  def serialize(self, c: SerializeCtx = SerializeCtx()):
    return (
      (f'/// {self.comment}' + '\n' if self.comment else '')
      + f'const {self.name.serialize(c)}'
      + (f': {self.serialize_type(c)}' if self.type else '')
      + f' = {self.value.serialize(c)}'
    )

  @staticmethod
  def parse(pctx: ParseContext) -> MaybeParsed["ConstDecl"]:
    start = pctx.index
    results: list[token.Token] = []

    # TODO: support Node types with parse methods, and parse any expression not just int
    for nodeOrTokType in (token.Type.const,
                          token.Type.ident,
                          token.Type.colon,
                          token.Type.ident,
                          token.Type.int):
      parsed = pctx.try_consume_tok_type(nodeOrTokType)
      # TODO: create a zig-like _try function
      if parsed is None or isinstance(parsed, TokenizeErr):
        pctx.reset(start)
        return
      results.append(parsed)

    _, ident, _, _type_expr, _, val = results

    ident = Ident(cast(token.Ident, ident.tok).name)

    return ConstDecl(
      ident,
      Literal(cast(int, val)),
      None,
      # _type_expr # need to check the name against known types? (and parse full expressions)
    )

class _TestConstDecl(unittest.TestCase):
  def test_parse(self):
    pctx = ParseContext("const x: Test = 5")
    parsed = ConstDecl.parse(pctx)
    self.assertIsNotNone(parsed)
    self.assertEqual("x", parsed.name.name)

@dataclass
class StructAssignment(Node):
  variable: str
  field: Optional[str]
  value: Node

@dataclass
class Namespace(Node):
  # TODO: consider having it be a list of ConstDecl or Stmt
  decls: List[Node] = field(default_factory=list)
  decl_by_name: Dict[Ident, Node] = field(default_factory=dict)

  def append_decl(self, decl: ConstDecl) -> None:
    self.decls.append(decl)
    self.decl_by_name[decl.name] = decl
  
  def prepend_decl(self, new_decl: ConstDecl, target: Optional[ConstDecl] = None) -> None:
    index = 0 if target is None else self.decls.index(target)
    self.decls.insert(index, new_decl)
    self.decl_by_name[new_decl.name] = new_decl

  def serialize(self, c: SerializeCtx = SerializeCtx()):
    return '\n'.join(d.serialize(c) for d in self.decls)

# A group of declarationS
Group = Namespace

# The top level of the AST for a file
Module = Namespace
