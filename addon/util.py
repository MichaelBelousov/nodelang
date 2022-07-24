from typing import Dict, Sequence, Tuple, TypeVar

K = TypeVar('K')
V = TypeVar('V')

FrozenDict = Sequence[Tuple[K, V]]

# TODO: switch to using frozenset or the frozendict pypi package
def freezeDict(dict: Dict[K, V]) -> FrozenDict[K, V]:
  return tuple((k,v) for k,v in dict.items())

class IgnoreDerefs:
  def __getattr__(self,_): return self
  def __getitem__(self,_): return self

class Ansi:
  class Colors:
    white = "\033[0;37m"
    yellow = "\033[0;33m"
