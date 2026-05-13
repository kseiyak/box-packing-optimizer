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
from box_packing.visualizer import COLOR_MAP, build_figure

try:
    from box_packing.visualizer import color_for_name
except ImportError:
    def color_for_name(name: str) -> str:
        return COLOR_MAP.get(name, "#3a86ff")

LEGEND_ORDER = [
    "50",
    "60",
    "70",
    "80",
    "80_medium",
    "80_small",
    "100",
    "100_medium",
    "100_small",
]


def _collect_fixed_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    st.subheader("固定箱の数量")
    names = list(ITEM_SPECS.keys())
    for name in names:
        spec = ITEM_SPECS[name]
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

    counts: dict[str, int] = {}
    specs: dict[str, BoxSpec] = {}

    for idx in range(1, 5):
        st.markdown(f"**カスタム箱{idx}**")
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            name = st.text_input("ラベル", value=f"custom_{idx}", key=f"custom_name_{idx}")
        with c2:
            w = st.number_input("縦(mm)", min_value=1, value=220, step=1, key=f"custom_w_{idx}")
        with c3:
            d = st.number_input("横(mm)", min_value=1, value=310, step=1, key=f"custom_d_{idx}")
        with c4:
            h = st.number_input("高さ(mm)", min_value=1, value=145, step=1, key=f"custom_h_{idx}")
        with c5:
            count = st.number_input("数量", min_value=0, value=0, step=1, key=f"custom_count_{idx}")

        if count <= 0:
            continue

        label = name.strip() or f"custom_box_{idx}"
        if label in ITEM_SPECS:
            label = f"{label}_custom"
        while label in specs:
            label = f"{label}_x"
        specs[label] = BoxSpec(label, (int(w), int(d), int(h)))
        counts[label] = int(count)

    return counts, specs


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

    if "latest_plan" not in st.session_state:
        st.session_state["latest_plan"] = None
    if "latest_counts" not in st.session_state:
        st.session_state["latest_counts"] = None
    if "latest_error" not in st.session_state:
        st.session_state["latest_error"] = None

    if run:
        if not merged_counts:
            st.session_state["latest_error"] = "数量を1つ以上入力してください。"
            st.session_state["latest_plan"] = None
            st.session_state["latest_counts"] = None
        else:
            try:
                plan = optimize_sagawa_shipments(merged_counts, custom_specs=custom_specs)
                st.session_state["latest_plan"] = plan
                st.session_state["latest_counts"] = merged_counts
                st.session_state["latest_error"] = None
            except Exception as exc:
                st.session_state["latest_error"] = f"最適化中にエラー: {exc}"
                st.session_state["latest_plan"] = None
                st.session_state["latest_counts"] = None

    if st.session_state["latest_error"]:
        st.error(st.session_state["latest_error"])
        return

    plan = st.session_state["latest_plan"]
    if plan is None:
        return

    st.success(f"計算完了: {len(plan.bundles)}便")
    st.write("入力アイテム:", st.session_state["latest_counts"])

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
        st.markdown("**凡例（箱タイプ → 色）**")
        used_name_set = {item.item_name for item in bundle.packed_items}
        used_names = [name for name in LEGEND_ORDER if name in used_name_set]
        # カスタム箱など既定順にない名前は末尾へ
        used_names.extend(sorted(name for name in used_name_set if name not in LEGEND_ORDER))
        legend_items: list[str] = []
        for name in used_names:
            color = color_for_name(name)
            legend_items.append(
                (
                    f"<div style='display:flex;align-items:center;gap:8px;padding:2px 0;'>"
                    f"<span style='display:inline-block;width:14px;height:14px;background:{color};"
                    f"border:1px solid #333;'></span>"
                    f"<span>{name}</span>"
                    f"</div>"
                )
            )
        st.markdown(
            (
                "<div style='display:grid;grid-template-columns:repeat(2,minmax(0,1fr));"
                "column-gap:16px;row-gap:2px;'>"
                + "".join(legend_items)
                + "</div>"
            ),
            unsafe_allow_html=True,
        )
        zoom = st.slider(
            f"3D表示ズーム（便{idx}）",
            min_value=0.6,
            max_value=2.0,
            value=1.0,
            step=0.1,
            key=f"zoom_bundle_{idx}",
        )

        fig = build_figure(bundle)
        base_eye = dict(x=1.65, y=1.65, z=1.15)
        fig.update_layout(
            scene_camera=dict(
                eye=dict(
                    x=base_eye["x"] / zoom,
                    y=base_eye["y"] / zoom,
                    z=base_eye["z"] / zoom,
                )
            )
        )
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": False,
                "displaylogo": False,
                "scrollZoom": True,
                "doubleClick": "reset",
            },
        )

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
