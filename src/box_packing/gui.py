from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import webbrowser

# `python src/box_packing/gui.py` での実行にも対応
if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from box_packing.models import BoxSpec, ITEM_SPECS
from box_packing.optimizer import optimize_sagawa_shipments
from box_packing.visualizer import save_html


def _parse_count(raw: str) -> int:
    text = raw.strip()
    if text == "":
        return 0
    value = int(text)
    if value < 0:
        raise ValueError("数量は0以上を入力してください。")
    return value


class BoxPackingGui:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("3D Box Packing Optimizer - Sagawa mode")
        self.root.geometry("900x760")

        self.count_vars: dict[str, tk.StringVar] = {}
        self.output_var = tk.StringVar(value=self._default_output_path())
        self.open_browser_var = tk.BooleanVar(value=True)
        self.result_var = tk.StringVar(value="数量を入力して「最適化して可視化」を押してください。")
        self.custom_vars: list[dict[str, tk.StringVar]] = []
        for idx in range(1, 5):
            self.custom_vars.append(
                {
                    "name": tk.StringVar(value=f"custom_{idx}"),
                    "w": tk.StringVar(value="270"),
                    "d": tk.StringVar(value="380"),
                    "h": tk.StringVar(value="180"),
                    "count": tk.StringVar(value="0"),
                }
            )

        self._build_ui()

    def _default_output_path(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return str(Path("outputs") / f"box_packing_{timestamp}.html")

    def _build_ui(self) -> None:
        title = tk.Label(self.root, text="箱詰め最適化入力（佐川モード）", font=("Yu Gothic UI", 14, "bold"))
        title.pack(pady=(12, 6))

        frame = tk.Frame(self.root)
        frame.pack(fill="x", padx=16)

        row = 0
        for name in ITEM_SPECS:
            spec = ITEM_SPECS[name]
            tk.Label(frame, text=f"{name} ({spec.size[0]}x{spec.size[1]}x{spec.size[2]} mm)").grid(
                row=row,
                column=0,
                sticky="w",
                padx=(0, 8),
                pady=4,
            )
            var = tk.StringVar(value="0")
            self.count_vars[name] = var
            tk.Entry(frame, width=8, textvariable=var).grid(row=row, column=1, sticky="w", pady=4)
            row += 1

        output_frame = tk.LabelFrame(self.root, text="出力設定", padx=10, pady=8)
        output_frame.pack(fill="x", padx=16, pady=(10, 6))

        tk.Label(output_frame, text="HTML出力先").grid(row=0, column=0, sticky="w")
        tk.Entry(output_frame, textvariable=self.output_var, width=60).grid(row=1, column=0, padx=(0, 8), pady=(4, 0))
        tk.Button(output_frame, text="参照", command=self._choose_output).grid(row=1, column=1, pady=(4, 0))
        tk.Checkbutton(output_frame, text="実行後にブラウザで開く", variable=self.open_browser_var).grid(
            row=2, column=0, sticky="w", pady=(8, 0)
        )

        custom_frame = tk.LabelFrame(self.root, text="カスタム箱（任意・最大4種類）", padx=10, pady=8)
        custom_frame.pack(fill="x", padx=16, pady=(0, 6))
        tk.Label(custom_frame, text="No").grid(row=0, column=0, sticky="w")
        tk.Label(custom_frame, text="ラベル").grid(row=0, column=1, sticky="w")
        tk.Label(custom_frame, text="縦(mm)").grid(row=0, column=2, sticky="w")
        tk.Label(custom_frame, text="横(mm)").grid(row=0, column=3, sticky="w")
        tk.Label(custom_frame, text="高さ(mm)").grid(row=0, column=4, sticky="w")
        tk.Label(custom_frame, text="数量").grid(row=0, column=5, sticky="w")
        for idx, vars_ in enumerate(self.custom_vars, start=1):
            row = idx
            tk.Label(custom_frame, text=str(idx)).grid(row=row, column=0, sticky="w", pady=(4, 0))
            tk.Entry(custom_frame, textvariable=vars_["name"], width=16).grid(row=row, column=1, padx=(0, 8), pady=(4, 0))
            tk.Entry(custom_frame, textvariable=vars_["w"], width=8).grid(row=row, column=2, padx=(0, 8), pady=(4, 0))
            tk.Entry(custom_frame, textvariable=vars_["d"], width=8).grid(row=row, column=3, padx=(0, 8), pady=(4, 0))
            tk.Entry(custom_frame, textvariable=vars_["h"], width=8).grid(row=row, column=4, padx=(0, 8), pady=(4, 0))
            tk.Entry(custom_frame, textvariable=vars_["count"], width=8).grid(row=row, column=5, pady=(4, 0))

        tk.Button(
            self.root,
            text="最適化して可視化",
            command=self._run,
            height=2,
            bg="#2d6a4f",
            fg="white",
        ).pack(fill="x", padx=16, pady=(10, 8))

        result_frame = tk.LabelFrame(self.root, text="結果", padx=10, pady=8)
        result_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        tk.Label(result_frame, textvariable=self.result_var, justify="left", anchor="nw").pack(fill="both", expand=True)

    def _choose_output(self) -> None:
        selected = filedialog.asksaveasfilename(
            title="保存先を選択",
            defaultextension=".html",
            filetypes=[("HTML", "*.html")],
            initialfile=Path(self.output_var.get()).name,
        )
        if selected:
            self.output_var.set(selected)

    def _collect_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for name, var in self.count_vars.items():
            counts[name] = _parse_count(var.get())
        return {k: v for k, v in counts.items() if v > 0}

    def _collect_custom(self) -> tuple[dict[str, int], dict[str, BoxSpec]]:
        counts: dict[str, int] = {}
        specs: dict[str, BoxSpec] = {}
        for idx, vars_ in enumerate(self.custom_vars, start=1):
            custom_count = _parse_count(vars_["count"].get())
            if custom_count == 0:
                continue
            name = vars_["name"].get().strip() or f"custom_box_{idx}"
            w = int(vars_["w"].get().strip())
            d = int(vars_["d"].get().strip())
            h = int(vars_["h"].get().strip())
            if w <= 0 or d <= 0 or h <= 0:
                raise ValueError("カスタム箱の縦横高さは1以上の整数で入力してください。")
            if name in ITEM_SPECS:
                name = f"{name}_custom"
            while name in specs:
                name = f"{name}_x"
            specs[name] = BoxSpec(name=name, size=(w, d, h))
            counts[name] = custom_count
        return counts, specs

    def _run(self) -> None:
        try:
            counts = self._collect_counts()
            custom_counts, custom_specs = self._collect_custom()
            merged_counts = dict(counts)
            for n, c in custom_counts.items():
                merged_counts[n] = merged_counts.get(n, 0) + c

            if not merged_counts:
                raise ValueError("数量を1つ以上入力してください。")

            plan = optimize_sagawa_shipments(merged_counts, custom_specs=custom_specs)
            output_path = Path(self.output_var.get())
            output_path.parent.mkdir(parents=True, exist_ok=True)
            html_paths: list[Path] = []

            for idx, bundle in enumerate(plan.bundles, start=1):
                if len(plan.bundles) == 1:
                    bundle_output = output_path
                else:
                    bundle_output = output_path.with_name(f"{output_path.stem}_parcel{idx:02d}{output_path.suffix}")
                save_html(bundle, str(bundle_output))
                html_paths.append(bundle_output)

            lines = [
                "佐川モード最適化が完了しました。",
                f"入力アイテム: {merged_counts}",
                f"分割便数: {len(plan.bundles)}",
                "",
            ]

            for idx, bundle in enumerate(plan.bundles, start=1):
                lines.extend(
                    [
                        f"[便{idx}] 最終サイズ: {bundle.metrics.size_class} サイズ",
                        f"[便{idx}] 3辺合計: {bundle.metrics.size_sum_cm} cm",
                        f"[便{idx}] 最長辺: {bundle.metrics.longest_side_mm / 10:.1f} cm",
                        (
                            f"[便{idx}] 外形(mm): "
                            f"{bundle.metrics.width_mm}x{bundle.metrics.depth_mm}x{bundle.metrics.height_mm}"
                        ),
                        f"[便{idx}] 佐川制約判定: {'OK' if bundle.success else 'NG'}",
                        f"[便{idx}] 配置済み: {len(bundle.packed_items)} 個",
                        f"[便{idx}] HTML: {html_paths[idx - 1].resolve()}",
                        f"[便{idx}] 配置一覧 (箱タイプ @ 原点mm -> サイズmm):",
                    ]
                )
                for item in bundle.packed_items:
                    lines.append(f"  - {item.item_name} @ {item.origin} -> {item.size}")
                lines.append("")
            self.result_var.set("\n".join(lines))

            if self.open_browser_var.get():
                for path in html_paths:
                    webbrowser.open(path.resolve().as_uri())

        except Exception as exc:
            messagebox.showerror("エラー", str(exc))


def main() -> None:
    root = tk.Tk()
    app = BoxPackingGui(root)
    while True:
        try:
            root.mainloop()
            break
        except KeyboardInterrupt:
            # 実行環境から誤って Ctrl+C 相当が入るケースがあるため継続する
            continue


if __name__ == "__main__":
    main()
