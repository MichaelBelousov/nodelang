from typing import Dict, Generic, Tuple, TypeVar

K = TypeVar('K')
V = TypeVar('V')

class FrozenDict(Generic[K, V]):
  pass

# TODO: switch to using frozenset or the frozendict pypi package
def freezeDict(dict: Dict) -> FrozenDict:
  return tuple(map(tuple, dict.items()))

class IgnoreDerefs:
  def __getattr__(s,_): return s
  def __getitem__(s,_): return s
