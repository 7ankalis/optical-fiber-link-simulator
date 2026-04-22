"""Matplotlib widget for plotting received power vs distance."""

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class PowerDistancePlot(FigureCanvas):
    def __init__(self, parent=None) -> None:
        self.figure = Figure(facecolor="#1b1f2a")
        self.ax = self.figure.add_subplot(121)
        self.info_ax = self.figure.add_subplot(122)
        self.theme_name = "dark"
        self.theme_palette = {}
        self.line_colors = {
            "curve": "#58a6ff",
            "sensitivity": "#ff9f43",
            "target": "#ff6b6b",
            "splice_marker": "#7887ab",
        }
        super().__init__(self.figure)
        self.setParent(parent)
        self.set_theme("dark")
        self._init_layout()
        self._style_axes()

    def _init_layout(self) -> None:
        self.figure.clear()
        gs = self.figure.add_gridspec(1, 2, width_ratios=[3.2, 1.35], wspace=0.15)
        self.ax = self.figure.add_subplot(gs[0, 0])
        self.info_ax = self.figure.add_subplot(gs[0, 1])

    def _style_axes(self) -> None:
        self.ax.set_facecolor(self.theme_palette["axes_bg"])
        self.ax.grid(True, color=self.theme_palette["grid"], linestyle="--", linewidth=0.8, alpha=0.8)
        self.ax.tick_params(colors=self.theme_palette["tick"])
        for spine in self.ax.spines.values():
            spine.set_color(self.theme_palette["spine"])
        self.ax.set_xlabel("Distance (km)", color=self.theme_palette["text"])
        self.ax.set_ylabel("Received Power (dBm)", color=self.theme_palette["text"])
        self.ax.set_title("Power vs Distance", color=self.theme_palette["text"], pad=12)

    def _style_info_axes(self) -> None:
        self.info_ax.set_facecolor(self.theme_palette["axes_bg"])
        for spine in self.info_ax.spines.values():
            spine.set_color(self.theme_palette["spine"])
        self.info_ax.set_xticks([])
        self.info_ax.set_yticks([])
        self.info_ax.set_title("Simulation Table", color=self.theme_palette["text"], fontsize=11, pad=10)

    def set_theme(self, theme_name: str) -> None:
        if theme_name == "light":
            self.theme_name = "light"
            self.theme_palette = {
                "figure_bg": "#f6f8fc",
                "axes_bg": "#ffffff",
                "grid": "#d8dfec",
                "tick": "#33415d",
                "spine": "#8a98b5",
                "text": "#1f2a44",
                "table_header": "#dce6ff",
                "table_even": "#f5f8ff",
                "table_odd": "#edf3ff",
                "table_text": "#1f2a44",
                "legend_bg": "#ffffff",
            }
        else:
            self.theme_name = "dark"
            self.theme_palette = {
                "figure_bg": "#1b1f2a",
                "axes_bg": "#151925",
                "grid": "#2a3142",
                "tick": "#d7deed",
                "spine": "#4a5470",
                "text": "#e8eeff",
                "table_header": "#25304a",
                "table_even": "#0f1522",
                "table_odd": "#121a2b",
                "table_text": "#dfe8ff",
                "legend_bg": "#151925",
            }
        self.figure.set_facecolor(self.theme_palette["figure_bg"])

    def set_line_color(self, line_key: str, color_hex: str) -> None:
        if line_key in self.line_colors and color_hex:
            self.line_colors[line_key] = color_hex

    def update_curve(
        self,
        emitted_power_dbm: float,
        attenuation_db_per_km: float,
        max_distance_km: float,
        receiver_sensitivity_dbm: float,
        target_length_km: float,
        spool_length_km: float,
        splice_loss_db: float,
        connector_loss_db: float,
        nb_connectors: int,
        is_functional: bool,
        summary_rows: list[tuple[str, str]],
    ) -> None:
        self._init_layout()
        self._style_axes()
        self._style_info_axes()

        upper = max(max_distance_km * 1.2, 1.0)
        x_values = np.linspace(0, upper, 400)
        connector_total_db = nb_connectors * connector_loss_db
        y_values = []
        for x in x_values:
            splice_count = max(0, int(x / spool_length_km) - 1) if spool_length_km > 0 else 0
            y = emitted_power_dbm - attenuation_db_per_km * x - splice_count * splice_loss_db - connector_total_db
            y_values.append(y)

        self.ax.plot(x_values, y_values, color=self.line_colors["curve"], linewidth=2.2)
        self.ax.axhline(
            receiver_sensitivity_dbm,
            color=self.line_colors["sensitivity"],
            linestyle=":",
            linewidth=1.6,
            label=f"Sensibilite ({receiver_sensitivity_dbm:.1f} dBm)",
        )
        self.ax.axvline(
            target_length_km,
            color=self.line_colors["target"],
            linestyle="--",
            linewidth=1.6,
            label=f"L demandee ({target_length_km:.1f} km)",
        )
        if spool_length_km > 0:
            max_splice_marker = int(upper / spool_length_km) + 1
            for i in range(1, max_splice_marker + 1):
                x = i * spool_length_km
                if x > upper:
                    break
                self.ax.axvline(x=x, color=self.line_colors["splice_marker"], linestyle=":", alpha=0.35)

        status_text = "Functional" if is_functional else "Not Functional"
        status_color = "#1f9d55" if is_functional else "#c24141"
        self.info_ax.text(
            0.5,
            0.97,
            f"Status: {status_text}",
            fontsize=10,
            fontweight="bold",
            color="#ffffff",
            va="top",
            ha="center",
            bbox={"boxstyle": "round,pad=0.35", "facecolor": status_color, "edgecolor": status_color, "alpha": 0.95},
        )

        table_data = [[k, v] for k, v in summary_rows]
        table = self.info_ax.table(
            cellText=table_data,
            colLabels=["Parameter", "Value"],
            cellLoc="left",
            colLoc="left",
            bbox=[0.02, 0.02, 0.96, 0.88],
        )
        table.auto_set_font_size(False)
        table.set_fontsize(8.4)
        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.set_text_props(color=self.theme_palette["text"], weight="bold")
                cell.set_facecolor(self.theme_palette["table_header"])
            else:
                cell.set_text_props(color=self.theme_palette["table_text"])
                cell.set_facecolor(self.theme_palette["table_even"] if row % 2 == 0 else self.theme_palette["table_odd"])
            cell.set_edgecolor(self.theme_palette["spine"])

        self.ax.legend(
            loc="best",
            facecolor=self.theme_palette["legend_bg"],
            edgecolor=self.theme_palette["spine"],
            labelcolor=self.theme_palette["tick"],
        )
        self.figure.tight_layout()
        self.draw_idle()

    def save_png(self, file_path: str) -> None:
        """Save the current graph as a PNG image."""
        self.figure.savefig(file_path, dpi=180, bbox_inches="tight")
