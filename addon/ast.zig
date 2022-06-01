//! parser for nodelang written in zig 

const std = @import("std");
const t = std.testing;
const debug = std.debug;

pub const Tok = union (enum) {
  ident,
  integer: i64,
  float: f64,
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

  pub fn new(tok: Tok, str: [] const u8) Token {
    return Token{.tok=tok, .str=str};
  }
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
  fn nth(self: ParseContext, n: usize) ?u8 {
    return if (n < self.remaining_src().len) self.remaining_src()[n] else null;
  }

  // TODO: allow starting and ending single quotes with escapes
  /// try to get the next token as if it's an identifier, assume unknown token if we fail
  /// - assumes whitespace has been skipped
  fn try_next_tok_keyword_or_ident(self: *ParseContext) TokenizeErr!Token {
    var i: usize = 1; // skip first char since it is assumed to be an identifier start
    var src: []const u8 = "";
    while (self.nth(i)) |c| {
      switch (c) {
        'a'...'z', 'A'...'Z', '0'...'9', '_' => { i += 1; },
        else => { src = self.remaining_src()[0..i]; break; }
      }
    }
    if (std.mem.eql(u8, src, "const")) {
      return Token.new(.@"const", self.remaining_src()[0..i]);
    } else {
      return Token.new(.ident, self.remaining_src()[0..i]);
    }
  }

  /// try to get the next token as if it's a number, assume unknown token if we fail
  /// - assumes whitespace has been skipped
  /// - assumes context starts with a digit
  fn try_next_tok_number(self: *ParseContext) TokenizeErr!Token {
      // TODO: roll my own parser to not have redundant logic
      const hasPrefixChar = std.ascii.isAlpha(self.remaining_src()[1]) and std.ascii.isDigit(self.remaining_src()[2]);
      var hadPoint = false;
      var tokEnd: usize = 0;
      for (self.remaining_src()) |c, i| {
        if (c == '.') {
          hadPoint = true;
          continue;
        }
        if (c == '_') continue;
        const isPrefixChar = i == 1 and hasPrefixChar;
        if (!std.ascii.isDigit(c) and !isPrefixChar) {
          tokEnd = i;
          break;
        }
      }
      const src = self.remaining_src()[0..tokEnd];
      if (hadPoint) {
        const val = std.fmt.parseFloat(f64, src) catch return TokenizeErr.UnknownTok;
        return Token.new(.{.float=val}, src);
      } else {
        const val = std.fmt.parseInt(i64, src, 0) catch return TokenizeErr.UnknownTok;
        return Token.new(.{.integer=val}, src);
      }
  }

  fn skip_available(self: *ParseContext) TokenizeErr!void {
    while (self.nth(0)) |c| {
      switch (c) {
        ' ' , '\t' , '\n' => { self.index += 1; },
        else => return,
      }
    }
    return TokenizeErr.Eof;
  }

  fn consume_tok(self: *ParseContext) TokenizeErr!Token {
    try self.skip_available();
    const tokenOrErr: TokenizeErr!Token = if (self.nth(0)) |zeroth| switch (zeroth) {
      // 'c' => if (self.nth(1)) |oneth| switch (oneth) {
      //   'o' => self.try_next_tok_const(),
      //   else => self.try_next_tok_ident(),
      // } else TokenizeErr.Eof,
      '+' => Token.new(.plus, self.remaining_src()[0..1]),
      '-' => Token.new(.minus, self.remaining_src()[0..1]),
      'a'...'z', 'A'...'Z' => self.try_next_tok_keyword_or_ident(),
      '0'...'9' => self.try_next_tok_number(),
      else => TokenizeErr.UnknownTok
    } else TokenizeErr.Eof;
    const token = try tokenOrErr;
    self.index += token.str.len;
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

  pub fn new(s: []const u8) Ident { return Ident{.s=s}; }

  /// always returns a Node.ident or null
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
  var pctx = ParseContext.new("hello const");
  const parsed = Ident.parse(&pctx);
  try t.expect(Node.ident == parsed.?);
  try t.expectEqualStrings("hello", parsed.?.ident.s);
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
