from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Dict, List, Mapping, Sequence, Tuple

from .models import BoxSpec, ITEM_SPECS, PackedItem, expand_item_list, expand_item_list_with_specs


Dimension = Tuple[int, int, int]
Origin = Tuple[int, int, int]

SAGAWA_MAX_SIZE_CLASS = 160
SAGAWA_MAX_LONGEST_MM = 900
DEFAULT_MULTI_START_ATTEMPTS = 24


@dataclass(frozen=True)
class BundleMetrics:
    width_mm: int
    depth_mm: int
    height_mm: int
    longest_side_mm: int
    size_sum_cm: int
    size_class: int
    volume_mm3: int


@dataclass
class BundlePackingResult:
    packed_items: List[PackedItem]
    metrics: BundleMetrics
    service_name: str = "Sagawa"
    max_size_class: int = SAGAWA_MAX_SIZE_CLASS
    max_longest_mm: int = SAGAWA_MAX_LONGEST_MM

    @property
    def success(self) -> bool:
        return (
            self.metrics.size_class <= self.max_size_class
            and self.metrics.longest_side_mm <= self.max_longest_mm
        )


@dataclass
class ShipmentPlan:
    bundles: List[BundlePackingResult]
    service_name: str = "Sagawa"


def _to_cm_ceil(mm: int) -> int:
    return (mm + 9) // 10


def _size_class_from_dims(size: Dimension) -> int:
    w, d, h = size
    size_sum_cm = _to_cm_ceil(w) + _to_cm_ceil(d) + _to_cm_ceil(h)
    if size_sum_cm <= 60:
        return 60
    return ((size_sum_cm + 19) // 20) * 20


def _calc_metrics(items: Sequence[PackedItem]) -> BundleMetrics:
    if not items:
        return BundleMetrics(0, 0, 0, 0, 0, 0, 0)

    max_x = max(item.origin[0] + item.size[0] for item in items)
    max_y = max(item.origin[1] + item.size[1] for item in items)
    max_z = max(item.origin[2] + item.size[2] for item in items)
    dims = (max_x, max_y, max_z)
    size_sum_cm = _to_cm_ceil(max_x) + _to_cm_ceil(max_y) + _to_cm_ceil(max_z)
    return BundleMetrics(
        width_mm=max_x,
        depth_mm=max_y,
        height_mm=max_z,
        longest_side_mm=max(dims),
        size_sum_cm=size_sum_cm,
        size_class=_size_class_from_dims(dims),
        volume_mm3=max_x * max_y * max_z,
    )


def _overlap(a: PackedItem, b_origin: Origin, b_size: Dimension) -> bool:
    ax0, ay0, az0 = a.origin
    ax1, ay1, az1 = ax0 + a.size[0], ay0 + a.size[1], az0 + a.size[2]
    bx0, by0, bz0 = b_origin
    bx1, by1, bz1 = bx0 + b_size[0], by0 + b_size[1], bz0 + b_size[2]

    return (
        ax0 < bx1
        and ax1 > bx0
        and ay0 < by1
        and ay1 > by0
        and az0 < bz1
        and az1 > bz0
    )


def _is_placeable(existing: Sequence[PackedItem], origin: Origin, size: Dimension) -> bool:
    for item in existing:
        if _overlap(item, origin, size):
            return False
    return True


def _candidate_origins(existing: Sequence[PackedItem]) -> List[Origin]:
    if not existing:
        return [(0, 0, 0)]

    points: set[Origin] = {(0, 0, 0)}
    for item in existing:
        x, y, z = item.origin
        w, d, h = item.size
        points.add((x + w, y, z))
        points.add((x, y + d, z))
        points.add((x, y, z + h))

    # lower origin first
    return sorted(points, key=lambda p: (p[2], p[1], p[0]))


def _objective_key(metrics: BundleMetrics) -> Tuple[int, int, int, int, int]:
    feasible = int(not (metrics.size_class <= SAGAWA_MAX_SIZE_CLASS and metrics.longest_side_mm <= SAGAWA_MAX_LONGEST_MM))
    return (
        feasible,
        metrics.size_class,
        metrics.size_sum_cm,
        metrics.longest_side_mm,
        metrics.volume_mm3,
    )


def _place_items(items: List[BoxSpec]) -> List[PackedItem]:
    placed: List[PackedItem] = []
    for box in sorted(items, key=lambda i: i.volume, reverse=True):
        best_candidate: PackedItem | None = None
        best_key: Tuple[int, int, int, int, int] | None = None

        for origin in _candidate_origins(placed):
            for orient in box.orientations():
                if not _is_placeable(placed, origin, orient):
                    continue
                candidate_item = PackedItem(item_name=box.name, origin=origin, size=orient)
                metrics = _calc_metrics([*placed, candidate_item])
                key = _objective_key(metrics)
                if best_key is None or key < best_key:
                    best_key = key
                    best_candidate = candidate_item

        if best_candidate is None:
            raise RuntimeError(f"Failed to place item: {box.name}")
        placed.append(best_candidate)

    return placed


def _place_items_with_order(items: List[BoxSpec], rng: random.Random | None = None) -> List[PackedItem]:
    placed: List[PackedItem] = []
    item_order = items[:]
    if rng is None:
        item_order.sort(key=lambda i: i.volume, reverse=True)
    else:
        # 体積降順を基本にしつつ、同体積や近いサイズの並びを崩して局所解を回避しやすくする
        item_order.sort(key=lambda i: i.volume, reverse=True)
        rng.shuffle(item_order)

    for box in item_order:
        best_candidate: PackedItem | None = None
        best_key: Tuple[int, int, int, int, int] | None = None

        origins = _candidate_origins(placed)
        orientations = box.orientations()
        if rng is not None:
            rng.shuffle(origins)
            rng.shuffle(orientations)

        for origin in origins:
            for orient in orientations:
                if not _is_placeable(placed, origin, orient):
                    continue
                candidate_item = PackedItem(item_name=box.name, origin=origin, size=orient)
                metrics = _calc_metrics([*placed, candidate_item])
                key = _objective_key(metrics)
                if best_key is None or key < best_key:
                    best_key = key
                    best_candidate = candidate_item

        if best_candidate is None:
            raise RuntimeError(f"Failed to place item: {box.name}")
        placed.append(best_candidate)

    return placed


def _build_bundle_result(packed_items: List[PackedItem]) -> BundlePackingResult:
    metrics = _calc_metrics(packed_items)
    return BundlePackingResult(
        packed_items=packed_items,
        metrics=metrics,
        service_name="Sagawa",
        max_size_class=SAGAWA_MAX_SIZE_CLASS,
        max_longest_mm=SAGAWA_MAX_LONGEST_MM,
    )


def _optimize_bundle_multistart(items: List[BoxSpec], attempts: int = DEFAULT_MULTI_START_ATTEMPTS) -> BundlePackingResult:
    if attempts < 1:
        attempts = 1

    # 1回目は従来と同じ決定的配置、2回目以降は固定シードで探索
    best_result = _build_bundle_result(_place_items_with_order(items, rng=None))
    best_key = _objective_key(best_result.metrics)

    for seed in range(1, attempts):
        rng = random.Random(seed)
        result = _build_bundle_result(_place_items_with_order(items, rng=rng))
        key = _objective_key(result.metrics)
        if key < best_key:
            best_key = key
            best_result = result

    return best_result


def _merge_specs(custom_specs: Mapping[str, BoxSpec] | None = None) -> Dict[str, BoxSpec]:
    specs = dict(ITEM_SPECS)
    if custom_specs:
        specs.update(custom_specs)
    return specs


def optimize_sagawa_bundle(
    item_counts: Dict[str, int],
    custom_specs: Mapping[str, BoxSpec] | None = None,
) -> BundlePackingResult:
    if custom_specs:
        specs = _merge_specs(custom_specs)
        items = expand_item_list_with_specs(item_counts, specs)
    else:
        items = expand_item_list(item_counts)
    if not items:
        raise ValueError("No items to pack. Set at least one count > 0.")

    return _optimize_bundle_multistart(items)


def _is_feasible(metrics: BundleMetrics) -> bool:
    return metrics.size_class <= SAGAWA_MAX_SIZE_CLASS and metrics.longest_side_mm <= SAGAWA_MAX_LONGEST_MM


def _evaluate_bundle(items: List[BoxSpec]) -> BundlePackingResult:
    return _optimize_bundle_multistart(items)


def optimize_sagawa_shipments(
    item_counts: Dict[str, int],
    custom_specs: Mapping[str, BoxSpec] | None = None,
) -> ShipmentPlan:
    if custom_specs:
        specs = _merge_specs(custom_specs)
        all_items = expand_item_list_with_specs(item_counts, specs)
    else:
        all_items = expand_item_list(item_counts)
    if not all_items:
        raise ValueError("No items to pack. Set at least one count > 0.")

    # 便ごとの元アイテム配列（同一サイズの複数個は別要素として保持）
    bundle_items_list: List[List[BoxSpec]] = []
    sorted_items = sorted(all_items, key=lambda i: i.volume, reverse=True)

    for item in sorted_items:
        best_bundle_idx: int | None = None
        best_key: Tuple[int, int, int, int] | None = None

        for idx, bundle_items in enumerate(bundle_items_list):
            candidate_items = [*bundle_items, item]
            candidate_result = _evaluate_bundle(candidate_items)
            if not candidate_result.success:
                continue
            key = (
                candidate_result.metrics.size_class,
                candidate_result.metrics.size_sum_cm,
                candidate_result.metrics.longest_side_mm,
                candidate_result.metrics.volume_mm3,
            )
            if best_key is None or key < best_key:
                best_key = key
                best_bundle_idx = idx

        if best_bundle_idx is not None:
            bundle_items_list[best_bundle_idx].append(item)
            continue

        single_result = _evaluate_bundle([item])
        if not single_result.success:
            raise ValueError(
                f"Single item cannot be shipped by Sagawa constraints: {item.name}, "
                f"size_class={single_result.metrics.size_class}, "
                f"longest_mm={single_result.metrics.longest_side_mm}"
            )
        bundle_items_list.append([item])

    bundle_results = [_evaluate_bundle(items) for items in bundle_items_list]
    if not all(_is_feasible(bundle.metrics) for bundle in bundle_results):
        raise RuntimeError("Internal error: infeasible bundle generated.")

    bundle_results.sort(key=lambda b: (b.metrics.size_class, b.metrics.size_sum_cm, b.metrics.longest_side_mm))
    return ShipmentPlan(bundles=bundle_results, service_name="Sagawa")
