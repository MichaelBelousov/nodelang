"""
"""
#XXX: this is a lexer, parsing methods are in the ast...

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
    i = 1
    src = ""
    # skip first char since it is assumed to be an identifier start
    while True:
      c = self.remaining_src()[i]
      if c.isalnum() or c == '_':
        i += 1
      else:
        src = self.remaining_src()[0:i]
        break

    if src == "const":
      return Token(token.Type.const, self.remaining_src()[:i])
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
