
from dataclasses import dataclass
from typing import Literal, Union, Optional
from enum import Enum

ErrUnion = Union

class TokenType:
  ident = type("ident", (), {})
  lBrack = type("lBrack", (), {})
  rBrack = type("rBrack", (), {})
  lPar = type("lPar", (), {})
  rPar = type("rPar", (), {})
  const = type("const", (), {})
  dot = type("dot", (), {})
  eq = type("eq", (), {})
  colon = type("colon", (), {})
  plus = type("plus", (), {})
  minus = type("minus", (), {})
  star = type("star", (), {})
  fSlash = type("fSlash", (), {})
  caret = type("caret", (), {})
  caretCaret = type("caretCaret", (), {})
  caretFSlash = type("caretFSlash", (), {})
  starStar = type("starStar", (), {})
  amp = type("amp", (), {})
  pipe = type("pipe", (), {})
  ampAmp = type("ampAmp", (), {})
  pipePipe = type("pipePipe", (), {})

TokenPayload = Union[
  int,
  float,
  str,
  # TODO: need these to have optional payloads like a tagged union
  TokenType.ident,
  TokenType.lBrack,
  TokenType.rBrack,
  TokenType.lPar,
  TokenType.rPar,
  TokenType.const,
  TokenType.dot,
  TokenType.eq,
  TokenType.colon,
  TokenType.plus,
  TokenType.minus,
  TokenType.star,
  TokenType.fSlash,
  TokenType.caret,
  TokenType.caretCaret,
  TokenType.caretFSlash,
  TokenType.starStar,
  TokenType.amp,
  TokenType.pipe,
  TokenType.ampAmp,
  TokenType.pipePipe
]

@dataclass(slots=True)
class Token:
  tok: TokenPayload
  slice: str


class TokenizeErr(Enum):
  UnknownTok = 0

class ParseError(Enum):
  pass

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
  def try_next_tok_keyword_or_ident(self) -> ErrUnion[TokenizeErr, Token]:
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
      return Token(TokenType.ident, self.remaining_src()[:i])

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

  def consume_tok(self) -> ErrUnion[TokenizeErr, Optional[Token]]:
    if not self.skipAvailable(): return None
    maybeToken: ErrUnion[TokenizeErr, Optional[Token]] =
      if (std.mem.startsWith(u8, "^", self.remaining_src())) (
        if (std.mem.startsWith(u8, "^^", self.remaining_src())) Token.new(Tok.caretCaret, self.remaining_src()[0..2])
        else if (std.mem.startsWith(u8, "^/", self.remaining_src())) Token.new(Tok.caretFSlash, self.remaining_src()[0..2])
        else Token.new(Tok.caret, self.remaining_src()[0..1])
      )
      else if (std.mem.startsWith(u8, "+", self.remaining_src())) return Token.new(Tok.plus, self.remaining_src()[0..1])
      else if (std.mem.startsWith(u8, ":", self.remaining_src())) return Token.new(Tok.colon, self.remaining_src()[0..1])
      else if (std.mem.startsWith(u8, "-", self.remaining_src())) return Token.new(Tok.minus, self.remaining_src()[0..1])
      else if (switch (self.remaining_src()[0]) { 'a'...'z', 'A'...'Z', '_' => true, else => false })
        try self.try_next_tok_keyword_or_ident()
      else if (switch (self.remaining_src()[0]) { '0'...'9' => true, else => false })
        try self.try_next_tok_number()
      else null
    const token = (try maybeToken) orelse return null
    self.index += token.str.len
    return token

  def try_consume_tok_type(self, tok_type: TokenType) -> ErrUnion[TokenizeErr, Optional[Token]]:
    """consume a token, if it is not of the given tag, put it back"""
    const start = self.index
    const tok = (try self.consume_tok()) orelse return null
    if (tok.tok == tok_type) {
      return tok
    } else {
      self.reset(start)
      return null
    }
  

  def reset(self: *ParseContext, index: usize) void {
    self.index = index
  }
}

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
    if (tok.tok == Tok.ident) {
      return Ident{ .name = tok.str, .srcSlice = tok.str }
    } else {
      pctx.reset(start)
      return null
    }
  }
}

test "parse Ident" {
  var pctx = ParseContext.new("hello const")
  const parsed = try Ident.parse(&pctx)
  try t.expect(parsed != null)
  try t.expectEqualStrings("hello", parsed.?.name)
}

def TokOrNodeTypesToTuple(comptime tokOrNodeTypes: anytype) type {
  var fields: [tokOrNodeTypes.len]std.builtin.TypeInfo.StructField = undefined
  for (tokOrNodeTypes) |tokOrNodeType, i| {
    const isParseable = @TypeOf(tokOrNodeType) == type
    //@compileLog("tokOrNodeType = ", tokOrNodeType)
    //const isToken = @TypeOf(tokOrNodeType) == @typeInfo(Tok).Union.tag_type.?
    fields[i] = std.builtin.TypeInfo.StructField{
      .name = std.fmt.comptimePrint("{}", .{i}),
      .field_type = if (isParseable) tokOrNodeType else Token,
      .default_value = null,
      .is_comptime = false,
      .alignment = 8,
    }
  }

  return @Type(std.builtin.TypeInfo{
    .Struct = .{
      .layout = std.builtin.TypeInfo.ContainerLayout.Auto,
      .fields = &fields,
      .decls = &.{},
      .is_tuple = true,
    }
  })
}

// FIXME: doesn't work due to a compiler error
/// parse several tokens, putting them all back if failing
def parseMany(pctx: *ParseContext, comptime tokOrNodeTypes: anytype) TokenizeErr!?TokOrNodeTypesToTuple(tokOrNodeTypes) {
  var result: ?TokOrNodeTypesToTuple(tokOrNodeTypes) = undefined
  inline for (tokOrNodeTypes) |tokOrNodeType, i| {
    const isParseable = @TypeOf(tokOrNodeType) == type
    const isToken = @TypeOf(tokOrNodeType) == @typeInfo(Tok).Union.tag_type.?
    var put_back_index_cuz_err: ?usize = null

    const maybe_consumed =
      if (isParseable)
        tokOrNodeType.parse(pctx)
      else if (isToken) _: {
        // FIXME: eof is treated as an error here... which is wrong, see notes on TokenizeErr.Eof above
        const tok = try pctx.consume_tok()
        break :_ if (tok.tok == tokOrNodeType) tok else null
      } else {
        @compileLog("bad tokOrNodeType = ", @TypeOf(tokOrNodeType))
        @compileError("parseMany list included something that was neither a token nor a parseable struct")
      }

    if (maybe_consumed) |consumed| {
      result.?[i] = consumed
    } else  {
      // this could probably be done more elegantly by adding a local function and returning a real error here
      put_back_index_cuz_err = i
      break
    }

    if (put_back_index_cuz_err) |put_back_index| {
      // there was an error, clean up and return early
      var j: isize = @intCast(isize, put_back_index)
      while (j > 0) : (j -= 1) {
        // FIXME
        //pctx.put_back(result[j])
      }

      result = null
      break
    }
  }
  return result
}

const Decl = struct {
  ident: Ident,
  srcSlice: []const u8,

  def parse(_pctx: *ParseContext) ?Decl {
    //if (parseMany(pctx, .{Tok.@"const", Ident, Tok.colon}) catch null) |toks| {

    const result = (struct {
      def impl(pctx: *ParseContext) !?Decl {
        const srcStart = pctx.index
        errdefer pctx.reset(srcStart)
        _  = (try pctx.try_consume_tok_type(.@"const")) orelse return error.PutBack
        const ident = (try Ident.parse(pctx)) orelse return error.PutBack
        _ = (try pctx.try_consume_tok_type(.colon)) orelse return error.PutBack
        _ = (try pctx.try_consume_tok_type(.integer)) orelse return error.PutBack

        const srcEnd = pctx.index
        return Decl{ .ident=ident, .srcSlice=pctx.slice(srcStart, srcEnd) }
      }
    }).impl(_pctx)

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
