from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

import streamlit as st

# `streamlit run src/box_packing/web_app.py` での実行に対応
if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from box_packing.models import BoxSpec, ITEM_SPECS
from box_packing.optimizer import optimize_sagawa_shipments
from box_packing.visualizer import build_figure


def _collect_fixed_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    st.subheader("固定箱の数量")
    cols = st.columns(2)
    names = list(ITEM_SPECS.keys())
    for idx, name in enumerate(names):
        spec = ITEM_SPECS[name]
        with cols[idx % 2]:
            value = st.number_input(
                f"{name} ({spec.size[0]}x{spec.size[1]}x{spec.size[2]} mm)",
                min_value=0,
                value=0,
                step=1,
                key=f"fixed_{name}",
            )
        if value > 0:
            counts[name] = int(value)
    return counts


def _collect_custom_box() -> tuple[dict[str, int], dict[str, BoxSpec]]:
    st.subheader("カスタム箱（任意）")
    custom_enabled = st.checkbox("カスタム箱を追加する", value=False)
    if not custom_enabled:
        return {}, {}

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        name = st.text_input("ラベル", value="custom_100_cut")
    with c2:
        w = st.number_input("縦(mm)", min_value=1, value=220, step=1)
    with c3:
        d = st.number_input("横(mm)", min_value=1, value=310, step=1)
    with c4:
        h = st.number_input("高さ(mm)", min_value=1, value=145, step=1)
    with c5:
        count = st.number_input("数量", min_value=0, value=0, step=1)

    if count <= 0:
        return {}, {}

    label = name.strip() or "custom_box"
    spec = BoxSpec(label, (int(w), int(d), int(h)))
    return {label: int(count)}, {label: spec}


def main() -> None:
    st.set_page_config(page_title="3D Box Packing Optimizer", layout="wide")
    st.title("3D Box Packing Optimizer（佐川モード）")
    st.caption("制約: 最長辺 <= 90cm, サイズ <= 160。超える場合は自動で複数便に分割。")

    fixed_counts = _collect_fixed_counts()
    custom_counts, custom_specs = _collect_custom_box()

    merged_counts = dict(fixed_counts)
    for n, c in custom_counts.items():
        merged_counts[n] = merged_counts.get(n, 0) + c

    left, right = st.columns([1, 1])
    with left:
        run = st.button("最適化して表示", type="primary", use_container_width=True)
    with right:
        default_name = f"box_packing_web_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        save_html = st.checkbox("結果をHTML保存", value=False)
        html_name = st.text_input("保存ファイル名（拡張子不要）", value=default_name, disabled=not save_html)

    if not run:
        return

    if not merged_counts:
        st.error("数量を1つ以上入力してください。")
        return

    try:
        plan = optimize_sagawa_shipments(merged_counts, custom_specs=custom_specs)
    except Exception as exc:
        st.error(f"最適化中にエラー: {exc}")
        return

    st.success(f"計算完了: {len(plan.bundles)}便")
    st.write("入力アイテム:", merged_counts)

    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    for idx, bundle in enumerate(plan.bundles, start=1):
        st.markdown(f"### 便{idx}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("最終サイズ", f"{bundle.metrics.size_class}")
        c2.metric("3辺合計(cm)", f"{bundle.metrics.size_sum_cm}")
        c3.metric("最長辺(cm)", f"{bundle.metrics.longest_side_mm / 10:.1f}")
        c4.metric("箱数", f"{len(bundle.packed_items)}")
        st.write(
            "外形(mm): "
            f"{bundle.metrics.width_mm} x {bundle.metrics.depth_mm} x {bundle.metrics.height_mm}"
        )

        fig = build_figure(bundle)
        st.plotly_chart(fig, use_container_width=True)

        if save_html:
            if len(plan.bundles) == 1:
                path = output_dir / f"{html_name}.html"
            else:
                path = output_dir / f"{html_name}_parcel{idx:02d}.html"
            fig.write_html(str(path), auto_open=False, include_plotlyjs="cdn")
            st.write(f"HTML保存: {path.resolve()}")

        with st.expander("配置一覧"):
            for item in bundle.packed_items:
                st.write(f"- {item.item_name} @ {item.origin} -> {item.size}")


if __name__ == "__main__":
    main()

