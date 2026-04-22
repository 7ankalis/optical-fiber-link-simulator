"""Matplotlib widget for plotting received power vs distance."""

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class PowerDistancePlot(FigureCanvas):
    def __init__(self, parent=None) -> None:
        self.figure = Figure(facecolor="#1b1f2a")
        self.ax = self.figure.add_subplot(111)
        super().__init__(self.figure)
        self.setParent(parent)
        self._style_axes()

    def _style_axes(self) -> None:
        self.ax.set_facecolor("#151925")
        self.ax.grid(True, color="#2a3142", linestyle="--", linewidth=0.8, alpha=0.8)
        self.ax.tick_params(colors="#d7deed")
        for spine in self.ax.spines.values():
            spine.set_color("#4a5470")
        self.ax.set_xlabel("Distance (km)", color="#e8eeff")
        self.ax.set_ylabel("Received Power (dBm)", color="#e8eeff")
        self.ax.set_title("Power vs Distance", color="#e8eeff", pad=12)

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
    ) -> None:
        self.ax.clear()
        self._style_axes()

        upper = max(max_distance_km * 1.2, 1.0)
        x_values = np.linspace(0, upper, 400)
        connector_total_db = nb_connectors * connector_loss_db
        y_values = []
        for x in x_values:
            splice_count = max(0, int(x / spool_length_km) - 1) if spool_length_km > 0 else 0
            y = emitted_power_dbm - attenuation_db_per_km * x - splice_count * splice_loss_db - connector_total_db
            y_values.append(y)

        self.ax.plot(x_values, y_values, color="#58a6ff", linewidth=2.2)
        self.ax.axhline(
            receiver_sensitivity_dbm,
            color="#ff9f43",
            linestyle=":",
            linewidth=1.6,
            label=f"Sensibilite ({receiver_sensitivity_dbm:.1f} dBm)",
        )
        self.ax.axvline(
            target_length_km,
            color="#ff6b6b",
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
                self.ax.axvline(x=x, color="#7887ab", linestyle=":", alpha=0.35)

        self.ax.legend(loc="best", facecolor="#151925", edgecolor="#4a5470", labelcolor="#d7deed")
        self.figure.tight_layout()
        self.draw_idle()

    def save_png(self, file_path: str) -> None:
        """Save the current graph as a PNG image."""
        self.figure.savefig(file_path, dpi=180, bbox_inches="tight")
