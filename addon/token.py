from dataclasses import dataclass
from enum import Enum
from typing import Literal, Union

__package__ = "addon"

@dataclass(slots=True)
class Ident:
  name: str
  quoted: bool = False

class Type(Enum):
  lBrack = 2
  rBrack = 3
  lPar = 4
  rPar = 5
  const = 6
  dot = 7
  eq = 8
  colon = 9
  plus = 10
  minus = 11
  star = 12
  fSlash = 13
  caret = 14
  caretCaret = 15
  caretFSlash = 16
  starStar = 17
  amp = 18
  pipe = 19
  ampAmp = 20
  pipePipe = 21
  ident = type[Ident]
  int = type[int],
  float = type[float],
  str= type[str],
  bool = type[bool],

# this is really a type-tagged union, will probably need to extend with class types later once there is some overlap
Payload = Union[
  Ident,
  int,
  float,
  str,
  bool
]

@dataclass(slots=True)
class Token:
  tok: Payload
  slice: str
