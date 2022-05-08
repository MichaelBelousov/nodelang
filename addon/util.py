from typing import Dict, Tuple

class FrozenDict(type):
  def __get_item__(self, Key, Val):
    return Tuple[Tuple[Key, Val]]

# TODO: switch to using frozenset or the frozendict pypi package
def freezeDict(dict: Dict) -> FrozenDict:
  return tuple(map(tuple, dict.items()))
