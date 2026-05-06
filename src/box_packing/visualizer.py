from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import plotly.graph_objects as go

from .optimizer import BundlePackingResult


COLOR_MAP: Dict[str, str] = {
    "50": "#e6194B",        # red
    "60": "#3cb44b",        # green
    "70": "#4363d8",        # blue
    "80_small": "#f58231",  # orange
    "80_medium": "#911eb4", # purple
    "80_large": "#46f0f0",  # cyan
    "100_small": "#ffe119", # yellow
    "100_medium": "#bcf60c",# lime
    "100_large": "#800000", # maroon
}

CUSTOM_COLOR_POOL: List[str] = [
    "#000000",  # black
    "#008080",  # teal
    "#a9a9a9",  # darkgray
    "#ffd8b1",  # apricot
    "#808000",  # olive
]


def color_for_name(name: str) -> str:
    if name in COLOR_MAP:
        return COLOR_MAP[name]
    idx = sum(ord(c) for c in name) % len(CUSTOM_COLOR_POOL)
    return CUSTOM_COLOR_POOL[idx]


def _vertices(origin: Tuple[int, int, int], size: Tuple[int, int, int]) -> Tuple[List[int], List[int], List[int]]:
    x0, y0, z0 = origin
    w, d, h = size
    x1, y1, z1 = x0 + w, y0 + d, z0 + h
    x = [x0, x1, x1, x0, x0, x1, x1, x0]
    y = [y0, y0, y1, y1, y0, y0, y1, y1]
    z = [z0, z0, z0, z0, z1, z1, z1, z1]
    return x, y, z


def _cuboid_mesh(
    origin: Tuple[int, int, int],
    size: Tuple[int, int, int],
    color: str,
    legend_name: str,
    hover_text: str,
) -> go.Mesh3d:
    x, y, z = _vertices(origin, size)
    i = [0, 0, 0, 1, 4, 4, 2, 6, 1, 5, 0, 4]
    j = [1, 2, 3, 2, 5, 6, 3, 7, 5, 6, 4, 7]
    k = [2, 3, 1, 3, 6, 7, 7, 2, 0, 1, 7, 3]
    return go.Mesh3d(
        x=x,
        y=y,
        z=z,
        i=i,
        j=j,
        k=k,
        color=color,
        opacity=0.95,
        name=legend_name,
        legendgroup=legend_name,
        hovertext=hover_text,
        hoverinfo="text",
        flatshading=True,
    )


def _cuboid_edges(origin: Tuple[int, int, int], size: Tuple[int, int, int], color: str) -> go.Scatter3d:
    x0, y0, z0 = origin
    w, d, h = size
    x1, y1, z1 = x0 + w, y0 + d, z0 + h
    edges = [
        ((x0, y0, z0), (x1, y0, z0)),
        ((x1, y0, z0), (x1, y1, z0)),
        ((x1, y1, z0), (x0, y1, z0)),
        ((x0, y1, z0), (x0, y0, z0)),
        ((x0, y0, z1), (x1, y0, z1)),
        ((x1, y0, z1), (x1, y1, z1)),
        ((x1, y1, z1), (x0, y1, z1)),
        ((x0, y1, z1), (x0, y0, z1)),
        ((x0, y0, z0), (x0, y0, z1)),
        ((x1, y0, z0), (x1, y0, z1)),
        ((x1, y1, z0), (x1, y1, z1)),
        ((x0, y1, z0), (x0, y1, z1)),
    ]
    xs: List[int] = []
    ys: List[int] = []
    zs: List[int] = []
    for a, b in edges:
        xs.extend([a[0], b[0], None])  # type: ignore[arg-type]
        ys.extend([a[1], b[1], None])  # type: ignore[arg-type]
        zs.extend([a[2], b[2], None])  # type: ignore[arg-type]
    return go.Scatter3d(
        x=xs,
        y=ys,
        z=zs,
        mode="lines",
        line=dict(color=color, width=7),
        showlegend=False,
        hoverinfo="skip",
    )


def _outline_edges(size: Tuple[int, int, int]) -> go.Scatter3d:
    trace = _cuboid_edges((0, 0, 0), size, "#b0b0b0")
    trace.line.width = 4
    trace.line.dash = "dash"
    return trace


def build_figure(result: BundlePackingResult) -> go.Figure:
    traces: List[go.BaseTraceType] = []
    legend_seen: set[str] = set()

    for item in result.packed_items:
        color = color_for_name(item.item_name)
        legend_name = f"{item.item_name}"
        hover_text = (
            f"{item.item_name}<br>"
            f"size: {item.size[0]}x{item.size[1]}x{item.size[2]} mm<br>"
            f"origin: {item.origin}"
        )
        mesh = _cuboid_mesh(item.origin, item.size, color, legend_name, hover_text)
        if legend_name in legend_seen:
            mesh.showlegend = False
        else:
            legend_seen.add(legend_name)
        traces.append(mesh)
        traces.append(_cuboid_edges(item.origin, item.size, "#000000"))

    traces.append(
        _outline_edges(
            (
                result.metrics.width_mm,
                result.metrics.depth_mm,
                result.metrics.height_mm,
            )
        )
    )

    title = (
        f"{result.service_name} {result.metrics.size_class} サイズ"
        f" | 3辺合計 {result.metrics.size_sum_cm} cm"
        f" | 最長辺 {result.metrics.longest_side_mm / 10:.1f} cm"
    )
    figure = go.Figure(data=traces)
    figure.update_layout(
        title=title,
        scene=dict(
            xaxis_title="X (mm)",
            yaxis_title="Y (mm)",
            zaxis_title="Z (mm)",
            aspectmode="data",
        ),
        legend=dict(title="箱タイプ"),
        margin=dict(l=0, r=0, t=55, b=0),
    )
    return figure


def save_html(result: BundlePackingResult, output_path: str) -> None:
    fig = build_figure(result)
    fig.write_html(output_path, auto_open=False, include_plotlyjs="cdn")
