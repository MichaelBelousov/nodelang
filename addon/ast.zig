//! parser for nodelang written in zig 

const t = @import("std").testing;

pub const Tok = union (enum) {
  ident,
  integer,
  float,
  string,
  lBrack, //[
  rBrack, //]
  lPar, //(
  rPar, //)
  @"const",
  dot,
  eq,
  colon,
  plus,
  minus,
  star,
  fSlash,
  caret,
  caretCaret,
  caretFSlash,
  starStar,
  amp, // &
  pipe,
  ampAmp, // &&
  pipePipe,
};

const Token = struct {
  tok: Tok,
  str: []const u8,
};

pub const TokenizeErr = error {
  Eof,
  UnknownTok,
};

pub const ParseContext = struct {
  source: []const u8,
  index: u64,

  fn new(s: []const u8) ParseContext { return ParseContext{.source=s, .index=0}; }

  fn remaining_src(self: ParseContext) []const u8 { return self.source[self.index..]; }

  /// indexing but with optionals
  fn nth(self: ParseContext, n: u32) ?u8 {
    return if (n < self.remaining_src().len) self.remaining_src()[n] else null;
  }

  /// try to get the next token as if it's a const, assume unknown token if we fail
  /// assumes whitespace has been skipped
  fn try_next_tok_const(self: *ParseContext) TokenizeErr!Token {
    _ = self;
    return TokenizeErr.UnknownTok;
  }

  /// try to get the next token as if it's an identifier, assume unknown token if we fail
  /// assumes whitespace has been skipped
  fn try_next_tok_ident(self: *ParseContext) TokenizeErr!Token {
    _ = self;
    return TokenizeErr.UnknownTok;
  }

  fn skip_whitespace(self: *ParseContext) TokenizeErr!void {
    while (self.source[self.index]) |c| {
      switch (c) {
        ' ' | '\t' | '\n' => { self.index += 1; },
        else => return,
      }
    }
    return TokenizeErr.Eof;
  }

  fn consume_tok(self: *ParseContext) TokenizeErr!Token {
    try self.skip_whitespace();
    const token = switch (self.nth(0)) {
      null => TokenizeErr.Eof,
      'c' => switch (self.remining_src()[1]) {
        null => TokenizeErr.Eof,
        'o' => self.try_next_tok_const(),
        else => self.next_ident(),
      },
      // TODO: have another function specifically for grabbing the next n chars as a token
      '+' => Token{.plus, self.remaining_src()[0..1]},
      '-' => Token{.minus, self.remaining_src()[0..1]},
      else => TokenizeErr.UnknownTok
    };
    self.index += token.len;
    return token;
  }

  /// not checked
  fn put_back(self: *ParseContext, token: Token) void {
    self.index -= token.str.len;
    if (self.index < 0) @panic("you can't put back a token you didn't get");
  }
};

const Ident = struct {
  s: []const u8,

  /// always returns a Node.ident
  fn parse(pctx: *ParseContext) ?Node {
    const maybe_tok = pctx.consume_tok();
    if (maybe_tok) |tok| {
      if (tok.tok == Tok.ident) { return Node{.ident = Ident{.s = tok.str}}; }
      else pctx.put_back(tok);
    } else |_| {}
    return null;
  }
};

test "parse Ident" {
  var pctx = ParseContext.new("hello");
  try t.expectEqual(
    Ident.parse(&pctx),
    Node{.ident = Ident{.s="hello"}}
  );
}

pub const BinOp = union (enum) {
  add,
  sub,
  dot,
};

pub const Node = union (enum) {
  ident: Ident,
  integer: i64,
  float: f64,
  @"bool": bool,
  string: []const u8,
  array: []const Node,
  call: struct { func: []const u8, args: []const Node },
  varRef: []const u8,
  binOp: struct { op: BinOp, left: *const Node, right: *const Node },
};
