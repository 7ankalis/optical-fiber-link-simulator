"""Main GUI window for the optical fiber link simulator."""

import json
from dataclasses import asdict
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.calculations import FIBER_LIBRARY, OpticalLinkCalculator, SimulationInputs
from plot.power_plot import PowerDistancePlot


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Optical Fiber Link Simulator")
        self.resize(1280, 780)
        self.last_inputs: SimulationInputs | None = None
        self.last_results = None
        self._build_ui()
        self._apply_styles()
        self._update_fiber_defaults()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(18)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_container = QWidget()
        left_panel = QVBoxLayout(left_container)
        left_panel.setSpacing(14)

        self.tx_box = self._build_transmitter_group()
        self.fiber_box = self._build_fiber_group()
        self.rx_box = self._build_receiver_group()
        self.results_box = self._build_results_group()

        self.simulate_btn = QPushButton("Simulate")
        self.simulate_btn.setCursor(Qt.PointingHandCursor)
        self.simulate_btn.clicked.connect(self._simulate)
        self.save_json_btn = QPushButton("Save JSON")
        self.save_json_btn.setCursor(Qt.PointingHandCursor)
        self.save_json_btn.clicked.connect(self._save_json)
        self.save_json_btn.setEnabled(False)
        self.save_graph_btn = QPushButton("Save Graph (PNG)")
        self.save_graph_btn.setCursor(Qt.PointingHandCursor)
        self.save_graph_btn.clicked.connect(self._save_graph)
        self.save_graph_btn.setEnabled(False)
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(10)
        buttons_row.addWidget(self.simulate_btn)
        buttons_row.addWidget(self.save_json_btn)
        buttons_row.addWidget(self.save_graph_btn)
        left_panel.addWidget(self.tx_box)
        left_panel.addWidget(self.fiber_box)
        left_panel.addWidget(self.rx_box)
        left_panel.addWidget(self.results_box)
        left_panel.addLayout(buttons_row)
        left_panel.addStretch(1)
        left_scroll.setWidget(left_container)

        right_panel = QVBoxLayout()
        title = QLabel("Power vs Distance")
        title.setObjectName("graphTitle")
        self.plot = PowerDistancePlot(self)
        right_panel.addWidget(title)
        right_panel.addWidget(self.plot, 1)

        root.addWidget(left_scroll, 2)
        root.addLayout(right_panel, 3)

    def _build_transmitter_group(self) -> QGroupBox:
        box = QGroupBox("Transmitter")
        form = QFormLayout(box)
        form.setSpacing(10)

        self.wavelength = self._spin(850, 1650, 1550.0, suffix=" nm", decimals=2)
        self.spectral_width = self._spin(0.001, 50, 0.10, suffix=" nm", decimals=3)
        self.pe = self._spin(-40, 30, 0.0, suffix=" dBm", decimals=2)
        self.line_code = QComboBox()
        self.line_code.addItems(["NRZ (0.7)", "RZ (0.35)"])
        self.required_bitrate = self._spin(0.001, 1000, 2.5, suffix=" Gbps", decimals=3)

        form.addRow("Wavelength λ:", self.wavelength)
        form.addRow("Spectral width Δλ:", self.spectral_width)
        form.addRow("Emitted power Pe:", self.pe)
        form.addRow("Line code:", self.line_code)
        form.addRow("Required bitrate:", self.required_bitrate)
        return box

    def _build_fiber_group(self) -> QGroupBox:
        box = QGroupBox("Fiber")
        form = QFormLayout(box)
        form.setSpacing(10)

        self.fiber_type = QComboBox()
        self.fiber_type.addItems(list(FIBER_LIBRARY.keys()))
        self.fiber_type.currentTextChanged.connect(self._update_fiber_defaults)

        self.alpha = self._spin(0.001, 5.0, 0.2, suffix=" dB/km", decimals=3)
        self.dc = self._spin(0.0, 200.0, 17.0, suffix=" ps/nm/km", decimals=2)
        self.length = self._spin(0.1, 5000.0, 50.0, suffix=" km", decimals=2)
        self.spool_length = self._spin(0.1, 1000.0, 2.0, suffix=" km", decimals=2)
        self.splice_loss = self._spin(0.0, 5.0, 0.3, suffix=" dB", decimals=2)
        self.connector_loss = self._spin(0.0, 5.0, 0.5, suffix=" dB", decimals=2)

        form.addRow("Fiber type:", self.fiber_type)
        form.addRow("Attenuation α:", self.alpha)
        form.addRow("Chromatic dispersion Dc:", self.dc)
        form.addRow("Link length L:", self.length)
        form.addRow("Spool length Lb:", self.spool_length)
        form.addRow("Loss per splice:", self.splice_loss)
        form.addRow("Loss per connector:", self.connector_loss)
        return box

    def _build_receiver_group(self) -> QGroupBox:
        box = QGroupBox("Receiver")
        form = QFormLayout(box)
        form.setSpacing(10)
        self.sensitivity = self._spin(-60, 10, -28.0, suffix=" dBm", decimals=2)
        self.safety_margin = self._spin(0.0, 20.0, 3.0, suffix=" dB", decimals=2)
        form.addRow("Sensitivity S:", self.sensitivity)
        form.addRow("Safety margin:", self.safety_margin)
        return box

    def _build_results_group(self) -> QGroupBox:
        box = QGroupBox("Results")
        layout = QGridLayout(box)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(8)

        self.status_indicator = QLabel("Not simulated")
        self.status_indicator.setObjectName("statusIndicator")
        self.verdict_label = QLabel("--")
        self.pr_label = QLabel("-- dBm")
        self.margin_label = QLabel("-- dB")
        self.lmax_label = QLabel("-- km")
        self.bmax_label = QLabel("-- Gbps")
        self.disp_total = QLabel("-- ps")
        self.disp_ch = QLabel("-- ps")
        self.disp_modal = QLabel("-- ps")
        self.loss_fiber = QLabel("-- dB")
        self.loss_splice = QLabel("-- dB")
        self.loss_connector = QLabel("-- dB")
        self.nb_splices = QLabel("--")

        row = 0
        for name, widget in [
            ("Link status:", self.status_indicator),
            ("Verdict:", self.verdict_label),
            ("Received power Pr:", self.pr_label),
            ("Computed margin:", self.margin_label),
            ("Maximum distance Lmax:", self.lmax_label),
            ("Maximum bit rate:", self.bmax_label),
            ("Total dispersion Δτ:", self.disp_total),
            ("Chromatic dispersion:", self.disp_ch),
            ("Modal dispersion:", self.disp_modal),
            ("Fiber loss:", self.loss_fiber),
            ("Total splice loss:", self.loss_splice),
            ("Total connector loss:", self.loss_connector),
            ("Number of splices:", self.nb_splices),
        ]:
            layout.addWidget(QLabel(name), row, 0)
            layout.addWidget(widget, row, 1)
            row += 1
        return box

    @staticmethod
    def _spin(min_v: float, max_v: float, default: float, suffix: str = "", decimals: int = 2) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(min_v, max_v)
        spin.setValue(default)
        spin.setDecimals(decimals)
        spin.setSuffix(suffix)
        spin.setSingleStep(0.1)
        spin.setMinimumHeight(32)
        return spin

    def _line_code_data(self) -> tuple[str, float]:
        if self.line_code.currentText().startswith("RZ"):
            return "RZ", 0.35
        return "NRZ", 0.7

    def _update_fiber_defaults(self) -> None:
        profile = FIBER_LIBRARY.get(self.fiber_type.currentText())
        if not profile:
            return
        self.alpha.setValue(profile["alpha_typique"])
        self.dc.setValue(profile["Dc"])

    def _simulate(self) -> None:
        try:
            line_code, coeff = self._line_code_data()
            fiber_profile = FIBER_LIBRARY.get(self.fiber_type.currentText(), {})

            data = SimulationInputs(
                wavelength_nm=self.wavelength.value(),
                spectral_width_nm=self.spectral_width.value(),
                emitted_power_dbm=self.pe.value(),
                fiber_type=self.fiber_type.currentText(),
                attenuation_db_per_km=self.alpha.value(),
                chromatic_dispersion_ps_nm_km=self.dc.value(),
                length_km=self.length.value(),
                receiver_sensitivity_dbm=self.sensitivity.value(),
                spool_length_km=self.spool_length.value(),
                splice_loss_db=self.splice_loss.value(),
                connector_loss_db=self.connector_loss.value(),
                safety_margin_db=self.safety_margin.value(),
                required_bitrate_gbps=self.required_bitrate.value(),
                line_code=line_code,
                line_code_coeff=coeff,
                core_index_nc=float(fiber_profile.get("n_c", 1.468)),
                delta_rel_index=float(fiber_profile.get("Delta", 0.0)),
            )

            results = OpticalLinkCalculator.run_simulation(data)
            self.last_inputs = data
            self.last_results = results
            self.pr_label.setText(f"{results.received_power_dbm:.2f} dBm")
            self.margin_label.setText(f"{results.computed_margin_db:.2f} dB")
            self.lmax_label.setText(f"{results.maximum_distance_km:.2f} km")
            self.bmax_label.setText(f"{results.maximum_bit_rate_gbps:.2f} Gbps")
            self.disp_total.setText(f"{results.total_dispersion_ps:.2f} ps")
            self.disp_ch.setText(f"{results.chromatic_dispersion_ps:.2f} ps")
            self.disp_modal.setText(f"{results.modal_dispersion_ps:.2f} ps")
            self.loss_fiber.setText(f"{results.fiber_loss_db:.2f} dB")
            self.loss_splice.setText(f"{results.splice_loss_total_db:.2f} dB")
            self.loss_connector.setText(f"{results.connector_loss_total_db:.2f} dB")
            self.nb_splices.setText(str(results.number_of_splices))
            self.verdict_label.setText(results.verdict_message)

            if results.is_link_functional:
                self.status_indicator.setText("Functional")
                self.status_indicator.setProperty("status", "ok")
            else:
                self.status_indicator.setText("Not Functional")
                self.status_indicator.setProperty("status", "bad")

            self.status_indicator.style().unpolish(self.status_indicator)
            self.status_indicator.style().polish(self.status_indicator)

            self.plot.update_curve(
                emitted_power_dbm=data.emitted_power_dbm,
                attenuation_db_per_km=data.attenuation_db_per_km,
                max_distance_km=max(results.maximum_distance_km, data.length_km),
                receiver_sensitivity_dbm=data.receiver_sensitivity_dbm,
                target_length_km=data.length_km,
                spool_length_km=data.spool_length_km,
                splice_loss_db=data.splice_loss_db,
                connector_loss_db=data.connector_loss_db,
                nb_connectors=data.nb_connectors,
            )
            self.save_json_btn.setEnabled(True)
            self.save_graph_btn.setEnabled(True)
        except Exception as exc:  # pragma: no cover - user-facing safeguard
            QMessageBox.critical(self, "Simulation Error", f"Unable to simulate:\n{exc}")

    def _save_json(self) -> None:
        if self.last_inputs is None or self.last_results is None:
            QMessageBox.information(self, "No Data", "Run a simulation before exporting JSON.")
            return
        default_name = f"simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Simulation as JSON",
            default_name,
            "JSON Files (*.json)",
        )
        if not file_path:
            return

        payload = {
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "inputs": asdict(self.last_inputs),
            "results": asdict(self.last_results),
        }
        try:
            with open(file_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
            QMessageBox.information(self, "Export Complete", f"JSON saved to:\n{file_path}")
        except Exception as exc:  # pragma: no cover - user-facing safeguard
            QMessageBox.critical(self, "Export Error", f"Could not save JSON:\n{exc}")

    def _save_graph(self) -> None:
        if self.last_results is None:
            QMessageBox.information(self, "No Graph", "Run a simulation before saving the graph.")
            return
        default_name = f"power_curve_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Graph as PNG",
            default_name,
            "PNG Image (*.png)",
        )
        if not file_path:
            return
        try:
            self.plot.save_png(file_path)
            QMessageBox.information(self, "Export Complete", f"Graph saved to:\n{file_path}")
        except Exception as exc:  # pragma: no cover - user-facing safeguard
            QMessageBox.critical(self, "Export Error", f"Could not save graph:\n{exc}")

    def _apply_styles(self) -> None:
        font = QFont("Segoe UI", 10)
        self.setFont(font)
        self.setStyleSheet(
            """
            QWidget {
                background-color: #10131a;
                color: #e6edf7;
            }
            QScrollArea {
                background: transparent;
            }
            QGroupBox {
                border: 1px solid #2c3345;
                border-radius: 12px;
                margin-top: 12px;
                padding: 12px;
                font-weight: 600;
                background-color: #161b26;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
                color: #c9d5f1;
            }
            QDoubleSpinBox, QComboBox {
                border: 1px solid #33415d;
                border-radius: 8px;
                padding: 6px 8px;
                background-color: #0f1522;
            }
            QDoubleSpinBox:focus, QComboBox:focus {
                border: 1px solid #58a6ff;
            }
            QPushButton {
                min-height: 42px;
                border: none;
                border-radius: 10px;
                font-weight: 600;
                background-color: #2f81f7;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #3c8cff;
            }
            QPushButton:pressed {
                background-color: #2368c4;
            }
            QLabel#graphTitle {
                font-size: 15px;
                font-weight: 700;
                color: #dbe8ff;
                padding-left: 6px;
            }
            QLabel#statusIndicator {
                border-radius: 8px;
                padding: 4px 10px;
                background-color: #3a3f4e;
                color: #ffffff;
                font-weight: 700;
            }
            QLabel#statusIndicator[status="ok"] {
                background-color: #1f9d55;
            }
            QLabel#statusIndicator[status="bad"] {
                background-color: #c24141;
            }
            """
        )
