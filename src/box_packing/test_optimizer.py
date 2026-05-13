from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from box_packing.models import BoxSpec, ITEM_SPECS
from box_packing.optimizer import (
    SAGAWA_MAX_LONGEST_MM,
    SAGAWA_MAX_SIZE_CLASS,
    optimize_sagawa_bundle,
    optimize_sagawa_shipments,
)


def test_optimize_single_small_item_success() -> None:
    result = optimize_sagawa_bundle({"50": 1})
    assert result.success
    assert result.metrics.size_class >= 60
    assert len(result.packed_items) == 1


def test_optimize_reports_size_class_and_longest_side() -> None:
    result = optimize_sagawa_bundle({"50": 2, "60": 1})
    assert result.metrics.size_class > 0
    assert result.metrics.longest_side_mm > 0


def test_constraints_flags_when_oversized() -> None:
    result = optimize_sagawa_bundle({"100": 4})
    assert result.metrics.size_class <= SAGAWA_MAX_SIZE_CLASS
    assert result.metrics.longest_side_mm <= SAGAWA_MAX_LONGEST_MM
    assert result.success


def test_shipments_auto_split_when_needed() -> None:
    plan = optimize_sagawa_shipments({"100": 5})
    assert len(plan.bundles) >= 2
    assert all(bundle.success for bundle in plan.bundles)


def test_unknown_item_raises_error() -> None:
    with pytest.raises(ValueError):
        optimize_sagawa_bundle({"NOT_FOUND": 1})


def test_item_specs_non_empty() -> None:
    assert len(ITEM_SPECS) >= 8


def test_custom_spec_can_be_packed() -> None:
    custom = {"my_cut": BoxSpec("my_cut", (220, 310, 145))}
    result = optimize_sagawa_bundle({"my_cut": 2}, custom_specs=custom)
    assert result.success
    assert len(result.packed_items) == 2
