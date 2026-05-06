from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Dict

# `python src/box_packing/app.py` での実行にも対応
if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from box_packing.models import ITEM_SPECS
from box_packing.optimizer import optimize_sagawa_shipments
from box_packing.visualizer import save_html


def parse_counts(raw: str) -> Dict[str, int]:
    raw = raw.strip()
    if raw.startswith("{"):
        data = json.loads(raw)
        return {str(k): int(v) for k, v in data.items()}

    result: Dict[str, int] = {}
    if not raw:
        return result
    for part in raw.split(","):
        name, value = part.split("=")
        result[name.strip()] = int(value.strip())
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="3D Box Packing Optimizer")
    parser.add_argument(
        "--counts",
        required=True,
        help='例: "50=2,60=1,100_small=1" または JSON 文字列',
    )
    parser.add_argument(
        "--output",
        default="box_packing_result.html",
        help="可視化HTMLの出力先",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    counts = parse_counts(args.counts)

    unknown = [name for name in counts if name not in ITEM_SPECS]
    if unknown:
        raise ValueError(f"Unknown item names: {unknown}")

    plan = optimize_sagawa_shipments(counts)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("=== 3D Box Packing Optimizer (Sagawa mode) ===")
    print(f"入力アイテム: {counts}")
    print(f"分割便数: {len(plan.bundles)}")

    for idx, bundle in enumerate(plan.bundles, start=1):
        if len(plan.bundles) == 1:
            bundle_output = output_path
        else:
            bundle_output = output_path.with_name(f"{output_path.stem}_parcel{idx:02d}{output_path.suffix}")
        save_html(bundle, str(bundle_output))
        print(f"[便{idx}] 最終サイズ: {bundle.metrics.size_class} サイズ")
        print(
            f"[便{idx}] 外形(mm): "
            f"{bundle.metrics.width_mm}x{bundle.metrics.depth_mm}x{bundle.metrics.height_mm}"
        )
        print(f"[便{idx}] 3辺合計: {bundle.metrics.size_sum_cm} cm")
        print(f"[便{idx}] 最長辺: {bundle.metrics.longest_side_mm / 10:.1f} cm")
        print(f"[便{idx}] 配置済み: {len(bundle.packed_items)} 個")
        print(f"[便{idx}] 可視化HTML: {bundle_output.resolve()}")


if __name__ == "__main__":
    main()
