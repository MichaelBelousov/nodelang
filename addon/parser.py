
from dataclasses import dataclass
from typing import TypeVar, Union, Optional
from enum import Enum
from . import token
from .token import Token

# cuz I'll probably convert back to zig once stage2 compiler is more stable
ErrUnion = Union

class TokenizeErr(Enum):
  UnknownTok = 0

class _ParseNonTokenizeErr(Enum):
  pass

ParseError = Union[TokenizeErr, _ParseNonTokenizeErr]

T = TypeVar('T')
MaybeParsed = ErrUnion[ParseError, Optional[T]]

@dataclass
class ParseContext:
  source: str
  index: int = 0

  def slice(self, start: int, end: int) -> str:
    return self.source[start:end]

  def remaining_src(self) -> str:
     return self.source[self.index:]

  def nth(self, n: int) -> Optional[str]:
    """indexing but with optionals"""
    return self.remaining_src()[n] if n < len(self.remaining_src()) else None

  # TODO: allow starting and ending single quotes with escapes
  def try_next_tok_keyword_or_ident(self) -> ErrUnion[TokenizeErr, token.Token]:
    """
    try to get the next token as if it's an identifier, assume unknown token if we fail
    - assumes whitespace has been skipped
    """
    i = 1; # skip first char since it is assumed to be an identifier start
    src = ""
    for c in self.remaining_src():
      if c.isalnum() or c == '_':
        i += 1
      else:
        src = self.remaining_src()[0:i]
        break

    if src == "const":
      return Token("const", self.remaining_src()[:i])
    else:
      return Token(token.Ident(src), self.remaining_src()[:i])

  def try_next_tok_number(self) -> ErrUnion[TokenizeErr, Token]:
      """
      try to get the next token as if it's a number, assume unknown token if we fail
       - assumes whitespace has been skipped
       - assumes context starts with a digit
      """
      # FIXME: this is bad
      # TODO: roll my own parser to not have redundant logic
      has_prefix_char = self.remaining_src()[1].isalpha() and self.remaining_src()[2].isdigit()
      had_point = False
      tok_end = 0
      for i, c in enumerate(self.remaining_src()): 
        if c == '.':
          had_point = True
          continue
        if c == '_': continue
        is_prefix_char = i == 1 and has_prefix_char
        if not c.isdigit() and not is_prefix_char:
          tok_end = i
          break
      
      src = self.remaining_src()[0:tok_end]
      parser = float if had_point else int
      try:
        val = parser(src)
        return Token(val, src)
      except:
        return TokenizeErr.UnknownTok


  # TODO: return ?enum{.eof}
  def skipAvailable(self) -> bool:
    """returns false if hit Eof"""
    while self.remaining_src() != '':
      c = self.remaining_src()[0]
      match c:
        case ' ' | '\t' | '\n':
          self.index += 1
        case _:
          break
      return True
    return False

  def consume_tok(self) -> ErrUnion[TokenizeErr, Optional[token.Token]]:
    if not self.skipAvailable(): return None
    _1 = self.remaining_src()[0:1]
    _2 = self.remaining_src()[0:2]
    maybeToken: ErrUnion[TokenizeErr, Optional[Token]] = (
      (
        Token(token.Type.caretCaret, _2)
          if self.remaining_src().startswith("^^")
        else Token(token.Type.caretFSlash, _2)
          if self.remaining_src().startswith("^/") 
        else Token(token.Type.caret, _1)
      ) if self.remaining_src().startswith("^")
      else Token(token.Type.plus, _1) if self.remaining_src().startswith("+")
      else Token(token.Type.colon, _1) if self.remaining_src().startswith(":")
      else Token(token.Type.minus, _1) if self.remaining_src().startswith("-")
      else self.try_next_tok_keyword_or_ident() if _1 == '_' or _1.isalpha()
      else self.try_next_tok_number() if _1.isdigit()
      else None
    )
    if not isinstance(maybeToken, TokenizeErr) and maybeToken is not None:
      self.index += len(maybeToken.slice)
    return maybeToken

  def try_consume_tok_type(self, tok_type: token.Type) -> ErrUnion[TokenizeErr, Optional[Token]]:
    """consume a token, if it is not of the given tag, put it back"""
    start = self.index
    tok = self.consume_tok()
    if isinstance(tok, TokenizeErr) or tok is None:
      return tok
    if tok.tok == tok_type:
      return tok
    else:
      self.reset(start)
      return None

  def reset(self, index: int) -> None:
    self.index = index

const Ident = struct {
  name: []const u8,
  // TODO: come up with a way to enforce the concept/comptime-interface of "Node"
  // maybe just a comptime function that ensures it, or one that adds it and generates a constructor for you
  srcSlice: []const u8,

  // FIXME: srcSlice is not always the name! once I added delimiter parsing, identifiers in nodelang can be `'` delimited which
  // is not in the name but is in the srcSlice
  pub def new(name: []const u8) Ident { return Ident{.name=name }; } //.srcSlice=name }

  /// tries to parse an Ident out of the context
  def parse(pctx: *ParseContext) ParseError!?Ident {
    const start = pctx.index
    const tok = (try pctx.consume_tok()) orelse return null
    if (tok.tok == Token.Type.ident) {
      return Ident{ .name = tok.str, .srcSlice = tok.str }
    } else {
      pctx.reset(start)
      return null
    }
  }
}

const Decl = struct {
  ident: Ident,
  srcSlice: []const u8,

  def parse(_pctx: *ParseContext) ?Decl {
    //if (parseMany(pctx, .{Token.Type.@"const", Ident, Token.Type.colon}) catch null) |toks| {

    const srcStart = pctx.index
    errdefer 
    _  = (try pctx.try_consume_tok_type(.@"const")) orelse { pctx.reset(srcStart); return }
    const ident = (try Ident.parse(pctx)) orelse { pctx.reset(srcStart); return }
    _ = (try pctx.try_consume_tok_type(.colon)) orelse { pctx.reset(srcStart); return }
    _ = (try pctx.try_consume_tok_type(.integer)) orelse { pctx.reset(srcStart); return }

    const srcEnd = pctx.index
    return Decl{ .ident=ident, .srcSlice=pctx.slice(srcStart, srcEnd) }

    return result catch null
  }
}

test "parse Decl" {
  var pctx = ParseContext.new("const x: Test = 5")
  const parsed = Decl.parse(&pctx)
  try t.expect(parsed != null)
  try t.expectEqualStrings("x", parsed.?.ident.name)
}

pub const BinOp = union (enum) {
  add,
  sub,
  dot
}

pub const Node = union (enum) {
  integer: i64,
  float: f64,
  @"bool": bool,
  string: []const u8,
  array: []const Node,
  call: struct { func: []const u8, args: []const Node },
  varRef: []const u8,
  binOp: struct { op: BinOp, left: *const Node, right: *const Node },
}
