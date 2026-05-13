from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Dict, Iterable, List, Mapping, Tuple


Dimension = Tuple[int, int, int]


@dataclass(frozen=True)
class BoxSpec:
    name: str
    size: Dimension

    @property
    def volume(self) -> int:
        return self.size[0] * self.size[1] * self.size[2]

    def orientations(self) -> List[Dimension]:
        return list(set(permutations(self.size, 3)))


@dataclass(frozen=True)
class CartonSpec:
    size_class: int
    inner_size: Dimension

    @property
    def size_sum(self) -> int:
        return sum(self.inner_size)

    @property
    def volume(self) -> int:
        return self.inner_size[0] * self.inner_size[1] * self.inner_size[2]


@dataclass(frozen=True)
class PackedItem:
    item_name: str
    origin: Dimension
    size: Dimension

    @property
    def volume(self) -> int:
        return self.size[0] * self.size[1] * self.size[2]


ITEM_SPECS: Dict[str, BoxSpec] = {
    "50": BoxSpec("50", (180, 210, 112)),
    "60": BoxSpec("60", (185, 240, 150)),
    "70": BoxSpec("70", (220, 310, 145)),
    "80": BoxSpec("80", (310, 220, 230)),
    "80_medium": BoxSpec("80_medium", (310, 220, 190)),
    "80_small": BoxSpec("80_small", (310, 220, 100)),
    "100": BoxSpec("100", (290, 380, 300)),
    "100_medium": BoxSpec("100_medium", (290, 380, 200)),
    "100_small": BoxSpec("100_small", (290, 380, 100)),
    "120": BoxSpec("120", (400, 540, 250)),
}

# NOTE:
# 配送サイズ(60/80/100...)は通常「3辺合計」だけが定義されますが、
# 3D配置計算には内寸(縦横高さ)が必要なため、代表的な内寸を定義しています。
# 実運用ではここを実際の段ボール寸法に置き換えてください。
CARTON_SPECS: Dict[int, CartonSpec] = {
    60: CartonSpec(60, (260, 200, 140)),
    80: CartonSpec(80, (360, 260, 180)),
    100: CartonSpec(100, (400, 300, 300)),
    120: CartonSpec(120, (500, 350, 350)),
    140: CartonSpec(140, (600, 400, 400)),
    160: CartonSpec(160, (650, 500, 450)),
    180: CartonSpec(180, (700, 550, 550)),
    200: CartonSpec(200, (750, 650, 600)),
}


def expand_item_list(item_counts: Dict[str, int]) -> List[BoxSpec]:
    items: List[BoxSpec] = []
    for name, count in item_counts.items():
        if count <= 0:
            continue
        if name not in ITEM_SPECS:
            raise ValueError(f"Unknown item name: {name}")
        items.extend([ITEM_SPECS[name]] * count)
    return items


def expand_item_list_with_specs(item_counts: Dict[str, int], specs: Mapping[str, BoxSpec]) -> List[BoxSpec]:
    items: List[BoxSpec] = []
    for name, count in item_counts.items():
        if count <= 0:
            continue
        if name not in specs:
            raise ValueError(f"Unknown item name: {name}")
        items.extend([specs[name]] * count)
    return items


def all_cartons() -> Iterable[CartonSpec]:
    return sorted(CARTON_SPECS.values(), key=lambda c: c.size_class)
