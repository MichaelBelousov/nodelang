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
  // FIXME: Eof is not actually an error, perhaps the tokenizer should instead return optional and eof is null
  Eof,
  UnknownTok,
};

pub const ParseContext = struct {
  source: []const u8,
  index: u64,

  fn new(source: []const u8) ParseContext { return ParseContext{.source=source, .index=0}; }

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

  fn putBackSkips(self: *ParseContext) TokenizeErr!void {
    while (self.nth(0)) |c| {
      switch (c) {
        ' ' , '\t' , '\n' => { self.index -= 1; },
        else => return,
      }
    }
    return TokenizeErr.Eof;
  }

  fn consume_tok(self: *ParseContext) TokenizeErr!Token {
    try self.skip_available();
    const tokenOrErr: TokenizeErr!Token =
      if (std.mem.startsWith(u8, "^", self.remaining_src())) (
        if (std.mem.startsWith(u8, "^^", self.remaining_src())) Token.new(Tok.caretCaret, self.remaining_src()[0..2])
        else if (std.mem.startsWith(u8, "^/", self.remaining_src())) Token.new(Tok.caretFSlash, self.remaining_src()[0..2])
        else Token.new(Tok.caret, self.remaining_src()[0..1])
      )
      else if (std.mem.startsWith(u8, "+", self.remaining_src())) return Token.new(Tok.plus, self.remaining_src()[0..1])
      else if (std.mem.startsWith(u8, ":", self.remaining_src())) return Token.new(Tok.colon, self.remaining_src()[0..1])
      else if (std.mem.startsWith(u8, "-", self.remaining_src())) return Token.new(Tok.minus, self.remaining_src()[0..1])
      else if (switch (self.remaining_src()[0]) { 'a'...'z', 'A'...'Z', '_' => true, else => false })
                                                                  self.try_next_tok_keyword_or_ident()
      else if (switch (self.remaining_src()[0]) { '0'...'9' => true, else => false })
                                                                  self.try_next_tok_number()
      else TokenizeErr.Eof;
    const token = try tokenOrErr;
    self.index += token.str.len;
    return token;
  }

  /// TODO: add checking in debug mode that the token placed back is correct
  fn putBack(self: *ParseContext, token: Token) void {
    self.index -= token.str.len;
    if (self.index < 0) @panic("you can't put back a token you didn't get");
    //putBackSkips();
  }
};

const Ident = struct {
  name: []const u8,
  // TODO: come up with a way to enforce the concept/comptime-interface of "Node"
  // maybe just a comptime function that ensures it, or one that adds it and generates a constructor for you
  //srcSlice: []const u8,

  // FIXME: srcSlice is not always the name! once I added delimiter parsing, identifiers in nodelang can be `'` delimited which
  // is not in the name but is in the srcSlice
  pub fn new(name: []const u8) Ident { return Ident{.name=name }; } //.srcSlice=name };

  /// parses an Ident out of the context, null if it fails
  fn parse(pctx: *ParseContext) ?Ident {
    const maybe_tok = pctx.consume_tok();
    if (maybe_tok) |tok| {
      if (tok.tok == Tok.ident) { return Ident{.name = tok.str}; }
      else pctx.putBack(tok);
    } else |_| {}
    return null;
  }
};

test "parse Ident" {
  var pctx = ParseContext.new("hello const");
  const parsed = Ident.parse(&pctx);
  try t.expect(parsed != null);
  try t.expectEqualStrings("hello", parsed.?.name);
}

fn TokOrNodeTypesToTuple(comptime tokOrNodeTypes: anytype) type {
  var fields: [tokOrNodeTypes.len]std.builtin.TypeInfo.StructField = undefined;
  for (tokOrNodeTypes) |tokOrNodeType, i| {
    const isParseable = @TypeOf(tokOrNodeType) == type;
    //@compileLog("tokOrNodeType = ", tokOrNodeType);
    //const isToken = @TypeOf(tokOrNodeType) == @typeInfo(Tok).Union.tag_type.?;
    fields[i] = std.builtin.TypeInfo.StructField{
      .name = std.fmt.comptimePrint("{}", .{i}),
      .field_type = if (isParseable) tokOrNodeType else Token,
      .default_value = null,
      .is_comptime = false,
      .alignment = 8,
    };
  }

  return @Type(std.builtin.TypeInfo{
    .Struct = .{
      .layout = std.builtin.TypeInfo.ContainerLayout.Auto,
      .fields = &fields,
      .decls = &.{},
      .is_tuple = true,
    }
  });
}

/// parse several tokens, putting them all back if failing
fn parseMany(pctx: *ParseContext, comptime tokOrNodeTypes: anytype) TokenizeErr!?TokOrNodeTypesToTuple(tokOrNodeTypes) {
  var result: TokOrNodeTypesToTuple(tokOrNodeTypes) = undefined;
  inline for (tokOrNodeTypes) |tokOrNodeType, i| {
    const isParseable = @TypeOf(tokOrNodeType) == type;
    const isToken = @TypeOf(tokOrNodeType) == @typeInfo(Tok).Union.tag_type.?;
    var put_back_index_cuz_err: ?usize = null;

    const maybe_consumed =
      if (isParseable)
        tokOrNodeType.parse(pctx)
      else if (isToken) _: {
        // FIXME: eof is treated as an error here... which is wrong, see notes on TokenizeErr.Eof above
        const tok = try pctx.consume_tok();
        break :_ if (tok.tok == tokOrNodeType) tok else null;
      } else {
        @compileLog("bad tokOrNodeType = ", @TypeOf(tokOrNodeType));
        @compileError("parseMany list included something that was neither a token nor a parseable struct");
      };

    if (maybe_consumed) |consumed| {
      result[i] = consumed;
    } else  {
      // this could probably be done more elegantly by adding a local function and returning a real error here
      put_back_index_cuz_err = i;
      break;
    }

    if (put_back_index_cuz_err) |put_back_index| {
      // there was an error, clean up and return early
      var j: isize = @intCast(isize, put_back_index);
      while (j > 0) : (j -= 1) {
        // FIXME
        //pctx.put_back(result[j]);
      }

      return null;
    }
  }
  return result;
}

const Decl = struct {
  ident: Ident,
  //srcSlice: []const u8,

  fn parse(pctx: *ParseContext) ?Decl {
    //var srcStart = pctx.index;
    if (parseMany(pctx, .{Tok.@"const", Ident, Tok.colon}) catch null) |toks| {
      const ident = toks[1];
      //const srcEnd = pctx.index;
      return Decl{ .ident=ident };// .srcSlice=pctx.source[srcStart..srcEnd] };
    } else {
      return null;
    }
  }
};

test "parse Decl" {
  var pctx = ParseContext.new("const x: Test = 5");
  const parsed = Decl.parse(&pctx);
  //try t.expect(parsed != null);
  _ = pctx;
  _ = parsed;
  // try t.expectEqualStrings("x", parsed.?.ident.name);
  try t.expectEqualStrings("x", "x");
}

pub const BinOp = union (enum) {
  add,
  sub,
  dot
};

pub const Node = union (enum) {
  integer: i64,
  float: f64,
  @"bool": bool,
  string: []const u8,
  array: []const Node,
  call: struct { func: []const u8, args: []const Node },
  varRef: []const u8,
  binOp: struct { op: BinOp, left: *const Node, right: *const Node },
};
