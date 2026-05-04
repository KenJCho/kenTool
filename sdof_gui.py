"""SDOF Analysis GUI — three-column Qt desktop application.

Layout  : left inputs (22%) | center force diagram (39%) | right response (39%)
Design  : FINSUL reference palette — Agents_Skills/GUI_design_description.md
Run     : python sdof_gui.py
Requires: PyQt5 >= 5.15 (or PySide6 >= 6.4), matplotlib >= 3.7, numpy >= 1.24
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Qt compatibility shim — PySide6 preferred, PyQt5 fallback
# ---------------------------------------------------------------------------
try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QSplitter, QScrollArea,
        QVBoxLayout, QHBoxLayout, QFormLayout,
        QLabel, QDoubleSpinBox, QSpinBox, QComboBox,
        QPushButton, QStackedWidget, QSizePolicy,
        QFileDialog, QMessageBox,
    )
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtGui import QFont
    _QT = "PySide6"
    _SP_EXP = QSizePolicy.Policy.Expanding
    _HORIZONTAL = Qt.Orientation.Horizontal
except ImportError:
    try:
        from PyQt5.QtWidgets import (
            QApplication, QMainWindow, QWidget, QSplitter, QScrollArea,
            QVBoxLayout, QHBoxLayout, QFormLayout,
            QLabel, QDoubleSpinBox, QSpinBox, QComboBox,
            QPushButton, QStackedWidget, QSizePolicy,
            QFileDialog, QMessageBox,
        )
        from PyQt5.QtCore import Qt, pyqtSignal as Signal
        from PyQt5.QtGui import QFont
        _QT = "PyQt5"
        _SP_EXP = QSizePolicy.Expanding
        _HORIZONTAL = Qt.Horizontal
    except ImportError as exc:
        raise ImportError(
            "Install PyQt5 or PySide6:  pip install PyQt5"
        ) from exc

import matplotlib
# qtagg is the unified Qt backend — auto-detects PyQt5/PySide6; don't override it
# with matplotlib.use("Qt5Agg") because that points to a different backend module
# (backend_qt5agg) while we import from backend_qtagg, causing a paint-event crash.
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavToolbar
from matplotlib.figure import Figure

from sdof_analysis import (
    make_system,
    step_response, rectangular_pulse_response, triangular_pulse_response,
    periodic_sawtooth_response, irregular_periodic_response, response_spectrum,
    _build_pulse_accel,
)

# ---------------------------------------------------------------------------
# Design tokens  (FINSUL reference palette)
# ---------------------------------------------------------------------------
_BG      = "#F8F9FA"
_PRIMARY = "#7BAAD4"
_P_EDGE  = "#3A6090"
_DARK    = "#3A3A3A"
_ACCENT  = "#CC3344"
_DIM     = "#444444"
_H_PARAM = "#e8f4f8"
_H_DIAG  = "#f8f0e8"
_H_RES   = "#f0f8e8"
_FONT    = "Segoe UI"
_PT      = 9

import matplotlib as _mpl
_mpl.rcParams.update({
    "figure.facecolor": _BG,
    "axes.facecolor":   _BG,
    "axes.edgecolor":   "#c0c8d0",
    "axes.labelcolor":  _DARK,
    "xtick.color":      _DIM,
    "ytick.color":      _DIM,
    "grid.color":       "#d0d8e0",
    "grid.linewidth":   0.5,
    "font.family":      "sans-serif",
    "font.sans-serif":  ["Segoe UI", "Arial", "DejaVu Sans"],
    "font.size":        8.5,
    "axes.titlesize":   9,
    "axes.labelsize":   8.5,
    "legend.fontsize":  8,
})

_APP_QSS = f"""
QWidget {{
    background: {_BG};
    color: {_DARK};
    font-family: "{_FONT}";
    font-size: {_PT}pt;
}}
QLabel {{ background: transparent; }}
QDoubleSpinBox, QSpinBox, QComboBox {{
    height: 24px;
    border: 1px solid #c0c8d0;
    border-radius: 4px;
    padding: 0 4px;
    background: white;
}}
QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {_PRIMARY};
}}
QPushButton#calc {{
    height: 32px;
    background: {_PRIMARY};
    color: white;
    border: none;
    border-radius: 4px;
    font-weight: bold;
    padding: 0 16px;
}}
QPushButton#calc:hover   {{ background: {_P_EDGE}; }}
QPushButton#calc:pressed {{ background: {_DARK};   }}
QPushButton#load {{
    height: 24px;
    background: #e8eef4;
    color: {_DARK};
    border: none;
    border-radius: 4px;
    padding: 0 8px;
}}
QPushButton#load:hover {{ background: #d0dce8; }}
QSplitter::handle      {{ background: #d0d8e0; width: 3px; }}
QScrollArea            {{ border: none; }}
QStatusBar             {{ background: #e8eef4; color: {_DIM}; font-size: 8pt; }}
"""

_CASES = [
    "Case 1 — Sawtooth (Fourier)",
    "Case 2 — Irregular Periodic (FFT)",
    "Case 3a — Step Force",
    "Case 3b — Rectangular Pulse",
    "Case 3c — Triangular Blast",
    "Case 4 — Response Spectrum",
]


# ---------------------------------------------------------------------------
# Helper widget factories
# ---------------------------------------------------------------------------

def _chip(text: str, bg: str) -> QLabel:
    """Styled section-header chip."""
    lbl = QLabel(text)
    f = QFont(_FONT, _PT + 1)
    f.setBold(True)
    lbl.setFont(f)
    lbl.setStyleSheet(
        f"background: {bg}; color: {_P_EDGE}; "
        f"border-radius: 4px; padding: 4px 8px; margin-bottom: 2px;"
    )
    return lbl


def _dsb(value: float, lo: float, hi: float,
         decimals: int = 4, step: float = 0.01) -> QDoubleSpinBox:
    sb = QDoubleSpinBox()
    sb.setRange(lo, hi)
    sb.setDecimals(decimals)
    sb.setSingleStep(step)
    sb.setValue(value)
    return sb


def _isb(value: int, lo: int, hi: int) -> QSpinBox:
    sb = QSpinBox()
    sb.setRange(lo, hi)
    sb.setValue(value)
    return sb


# ---------------------------------------------------------------------------
# Embedded matplotlib canvas
# ---------------------------------------------------------------------------

class _Canvas(QWidget):
    """QWidget wrapping a matplotlib Figure + navigation toolbar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fig = Figure(facecolor=_BG)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setSizePolicy(_SP_EXP, _SP_EXP)
        toolbar = NavToolbar(self.canvas, self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(toolbar)
        lay.addWidget(self.canvas)

    def refresh(self) -> None:
        self.fig.tight_layout()
        self.canvas.draw_idle()


# ---------------------------------------------------------------------------
# Left panel — all parameter inputs
# ---------------------------------------------------------------------------

class LeftPanel(QWidget):
    calculate_requested = Signal(int, dict)   # (case_index, params_dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fft_data: tuple[np.ndarray, np.ndarray] | None = None
        self.setMinimumWidth(240)
        self.setMaximumWidth(380)
        self._build_ui()

    # ── Layout ────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        inner = QWidget()
        scroll.setWidget(inner)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        lay = QVBoxLayout(inner)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        # System parameters
        lay.addWidget(_chip("SDOF System", _H_PARAM))
        form = QFormLayout()
        form.setSpacing(4)
        self.sb_m = _dsb(1.0,   1e-9, 1e9,  decimals=4, step=0.1)
        self.sb_k = _dsb(100.0, 1e-3, 1e12, decimals=2, step=10.0)
        self.sb_z = _dsb(0.05,  0.0,  0.999, decimals=4, step=0.01)
        form.addRow("m (kg):", self.sb_m)
        form.addRow("k (N/m):", self.sb_k)
        form.addRow("ζ:", self.sb_z)
        self.lbl_omn = QLabel()
        self.lbl_fn  = QLabel()
        self.lbl_Tn  = QLabel()
        for lbl in (self.lbl_omn, self.lbl_fn, self.lbl_Tn):
            lbl.setStyleSheet(f"color: {_DIM}; font-size: 8pt;")
        form.addRow(self.lbl_omn)
        form.addRow(self.lbl_fn)
        form.addRow(self.lbl_Tn)
        lay.addLayout(form)
        for sb in (self.sb_m, self.sb_k, self.sb_z):
            sb.valueChanged.connect(self._update_derived)
        self._update_derived()

        # Case selector
        lay.addWidget(_chip("Analysis Case", _H_PARAM))
        self.cb_case = QComboBox()
        self.cb_case.addItems(_CASES)
        lay.addWidget(self.cb_case)

        # Case-specific parameter stack
        lay.addWidget(_chip("Parameters", _H_PARAM))
        self.stack = QStackedWidget()
        for page in (
            self._page_case1(),
            self._page_case2(),
            self._page_case3a(),
            self._page_case3b(),
            self._page_case3c(),
            self._page_case4(),
        ):
            self.stack.addWidget(page)
        lay.addWidget(self.stack)
        self.cb_case.currentIndexChanged.connect(self.stack.setCurrentIndex)

        # Calculate button
        self.btn = QPushButton("Calculate")
        self.btn.setObjectName("calc")
        self.btn.clicked.connect(self._on_calc)
        lay.addWidget(self.btn)
        lay.addStretch()

    # ── Derived-quantities display ────────────────────────────────────────

    def _update_derived(self) -> None:
        try:
            s = make_system(self.sb_m.value(), self.sb_k.value(), self.sb_z.value())
            fn = s.omega_n / (2.0 * 3.141592653589793)
            self.lbl_omn.setText(f"ωₙ = {s.omega_n:.5g} rad/s")
            self.lbl_fn.setText( f"fₙ = {fn:.5g} Hz")
            self.lbl_Tn.setText( f"Tₙ = {s.T_n:.5g} s")
        except ValueError:
            self.lbl_omn.setText("ωₙ = — (invalid)")
            self.lbl_fn.setText( "fₙ = —")
            self.lbl_Tn.setText( "Tₙ = —")

    # ── Parameter pages ───────────────────────────────────────────────────

    def _page_case1(self) -> QWidget:
        w = QWidget(); f = QFormLayout(w); f.setSpacing(4)
        self.c1_F0 = _dsb(100.0, 1e-6, 1e9,   decimals=2,  step=10.0)
        self.c1_T  = _dsb(1.0,   1e-4, 1000.,  decimals=4,  step=0.1)
        self.c1_nh = _isb(20, 1, 500)
        self.c1_te = _dsb(10.0,  1e-4, 1e6,    decimals=2,  step=1.0)
        self.c1_dt = _dsb(0.001, 1e-6, 1.0,    decimals=5,  step=0.001)
        f.addRow("F₀ (N):",        self.c1_F0)
        f.addRow("T_period (s):",  self.c1_T)
        f.addRow("n_harmonics:",   self.c1_nh)
        f.addRow("t_end (s):",     self.c1_te)
        f.addRow("dt (s):",        self.c1_dt)
        return w

    def _page_case2(self) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w); lay.setSpacing(4)
        btn = QPushButton("Load CSV (t, F)…"); btn.setObjectName("load")
        btn.clicked.connect(self._load_csv)
        self.c2_lbl = QLabel("No file loaded")
        self.c2_lbl.setStyleSheet(f"color: {_DIM}; font-size: 8pt;")
        f = QFormLayout(); f.setSpacing(4)
        self.c2_te = _dsb(5.0, 1e-4, 1e6, decimals=2, step=1.0)
        f.addRow("t_end (s):", self.c2_te)
        lay.addWidget(btn)
        lay.addWidget(self.c2_lbl)
        lay.addLayout(f)
        return w

    def _page_case3a(self) -> QWidget:
        w = QWidget(); f = QFormLayout(w); f.setSpacing(4)
        self.c3a_F0 = _dsb(50.0,  1e-6, 1e9, decimals=2, step=10.0)
        self.c3a_te = _dsb(5.0,   1e-4, 1e6, decimals=2, step=1.0)
        self.c3a_dt = _dsb(0.001, 1e-6, 1.0, decimals=5, step=0.001)
        f.addRow("F₀ (N):",    self.c3a_F0)
        f.addRow("t_end (s):", self.c3a_te)
        f.addRow("dt (s):",    self.c3a_dt)
        return w

    def _page_case3b(self) -> QWidget:
        w = QWidget(); f = QFormLayout(w); f.setSpacing(4)
        self.c3b_F0 = _dsb(100.0, 1e-6, 1e9, decimals=2, step=10.0)
        self.c3b_td = _dsb(0.3,   1e-6, 1e6, decimals=4, step=0.05)
        self.c3b_te = _dsb(2.0,   1e-4, 1e6, decimals=2, step=0.5)
        self.c3b_dt = _dsb(0.001, 1e-6, 1.0, decimals=5, step=0.001)
        f.addRow("F₀ (N):",    self.c3b_F0)
        f.addRow("t_d (s):",   self.c3b_td)
        f.addRow("t_end (s):", self.c3b_te)
        f.addRow("dt (s):",    self.c3b_dt)
        return w

    def _page_case3c(self) -> QWidget:
        w = QWidget(); f = QFormLayout(w); f.setSpacing(4)
        self.c3c_F0 = _dsb(100.0, 1e-6, 1e9, decimals=2, step=10.0)
        self.c3c_td = _dsb(0.3,   1e-6, 1e6, decimals=4, step=0.05)
        self.c3c_te = _dsb(2.0,   1e-4, 1e6, decimals=2, step=0.5)
        self.c3c_dt = _dsb(0.001, 1e-6, 1.0, decimals=5, step=0.001)
        f.addRow("F₀ (N):",    self.c3c_F0)
        f.addRow("t_d (s):",   self.c3c_td)
        f.addRow("t_end (s):", self.c3c_te)
        f.addRow("dt (s):",    self.c3c_dt)
        return w

    def _page_case4(self) -> QWidget:
        w = QWidget(); f = QFormLayout(w); f.setSpacing(4)
        self.c4_exc = QComboBox()
        self.c4_exc.addItems(["rectangular", "half_sine", "triangular"])
        self.c4_a0  = _dsb(9.81, 1e-6, 1e6,  decimals=3, step=1.0)
        self.c4_td  = _dsb(0.1,  1e-6, 1e6,  decimals=4, step=0.01)
        self.c4_Tmi = _dsb(0.05, 1e-4, 100., decimals=4, step=0.01)
        self.c4_Tma = _dsb(2.0,  0.01, 100., decimals=2, step=0.5)
        self.c4_np  = _isb(100, 10, 1000)
        self.c4_xax = QComboBox()
        self.c4_xax.addItems(["Period Tₙ (s)", "Frequency fₙ (Hz)"])
        f.addRow("Excitation:", self.c4_exc)
        f.addRow("a₀ (m/s²):", self.c4_a0)
        f.addRow("t_d (s):",    self.c4_td)
        f.addRow("T_min (s):",  self.c4_Tmi)
        f.addRow("T_max (s):",  self.c4_Tma)
        f.addRow("n_periods:",  self.c4_np)
        f.addRow("X-axis:",     self.c4_xax)
        return w

    # ── CSV loader (Case 2) ───────────────────────────────────────────────

    def _load_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Force Table", "",
            "CSV files (*.csv);;Text files (*.txt);;All files (*)"
        )
        if not path:
            return
        try:
            data = np.loadtxt(path, delimiter=",", skiprows=1)
            if data.ndim != 2 or data.shape[1] < 2:
                raise ValueError("Expected ≥ 2 columns: time, force")
            self._fft_data = (data[:, 0], data[:, 1])
            self.c2_lbl.setText(Path(path).name)
            self.c2_lbl.setStyleSheet(f"color: {_P_EDGE}; font-size: 8pt;")
        except Exception as exc:
            QMessageBox.warning(self, "Load Error", str(exc))

    # ── Gather params + emit ──────────────────────────────────────────────

    def _on_calc(self) -> None:
        idx = self.cb_case.currentIndex()
        p = self._gather(idx)
        if p is not None:
            self.calculate_requested.emit(idx, p)

    def _gather(self, idx: int) -> dict | None:
        try:
            make_system(self.sb_m.value(), self.sb_k.value(), self.sb_z.value())
        except ValueError as exc:
            QMessageBox.warning(self, "System Error", str(exc))
            return None

        p: dict = {
            "m": self.sb_m.value(),
            "k": self.sb_k.value(),
            "zeta": self.sb_z.value(),
        }

        if idx == 0:
            p.update(F0=self.c1_F0.value(), T_period=self.c1_T.value(),
                     n_harmonics=self.c1_nh.value(),
                     t_end=self.c1_te.value(), dt=self.c1_dt.value())
        elif idx == 1:
            if self._fft_data is None:
                QMessageBox.warning(self, "No Data", "Load a CSV file first.")
                return None
            p.update(t_input=self._fft_data[0], F_input=self._fft_data[1],
                     t_end=self.c2_te.value())
        elif idx == 2:
            p.update(F0=self.c3a_F0.value(),
                     t_end=self.c3a_te.value(), dt=self.c3a_dt.value())
        elif idx == 3:
            p.update(F0=self.c3b_F0.value(), t_d=self.c3b_td.value(),
                     t_end=self.c3b_te.value(), dt=self.c3b_dt.value())
        elif idx == 4:
            p.update(F0=self.c3c_F0.value(), t_d=self.c3c_td.value(),
                     t_end=self.c3c_te.value(), dt=self.c3c_dt.value())
        elif idx == 5:
            p.update(excitation_type=self.c4_exc.currentText(),
                     a0=self.c4_a0.value(), t_d=self.c4_td.value(),
                     T_min=self.c4_Tmi.value(), T_max=self.c4_Tma.value(),
                     n_periods=self.c4_np.value(),
                     xaxis_freq=self.c4_xax.currentIndex() == 1)
        return p


# ---------------------------------------------------------------------------
# Main window — orchestrates panels and calculations
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("kenTool — SDOF Vibration Analysis")
        self.resize(1400, 820)
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(0)

        self.splitter = QSplitter(_HORIZONTAL)
        root.addWidget(self.splitter)

        # Left: parameters
        self.left = LeftPanel()
        self.left.calculate_requested.connect(self._on_calculate)

        # Center: force / excitation
        center = QWidget()
        cl = QVBoxLayout(center)
        cl.setContentsMargins(4, 4, 4, 4)
        cl.setSpacing(4)
        cl.addWidget(_chip("Force / Excitation", _H_DIAG))
        self.c_canvas = _Canvas()
        cl.addWidget(self.c_canvas)

        # Right: response
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 4, 4, 4)
        rl.setSpacing(4)
        rl.addWidget(_chip("Response", _H_RES))
        self.r_canvas = _Canvas()
        rl.addWidget(self.r_canvas)

        self.splitter.addWidget(self.left)
        self.splitter.addWidget(center)
        self.splitter.addWidget(right)
        self.splitter.setSizes([280, 560, 560])

        self.statusBar().showMessage(
            "Ready — configure system parameters and click Calculate."
        )

    # ── Calculation dispatcher ────────────────────────────────────────────

    def _on_calculate(self, case_idx: int, params: dict) -> None:
        try:
            sys_ = make_system(params["m"], params["k"], params["zeta"])
            result, ft, fF, f_ylabel, f_title = self._run(case_idx, params, sys_)
        except Exception:
            QMessageBox.critical(self, "Calculation Error", traceback.format_exc())
            return

        self._draw_force(ft, fF, f_ylabel, f_title)
        self._draw_response(case_idx, result, sys_, params)
        self.statusBar().showMessage(
            f"Calculated: {_CASES[case_idx]}  |  "
            f"ωₙ = {sys_.omega_n:.4g} rad/s,  Tₙ = {sys_.T_n:.4g} s"
        )

    def _run(
        self, idx: int, p: dict, sys_
    ) -> tuple[dict, np.ndarray, np.ndarray, str, str]:
        """Execute one analysis case; return (result, t_force, F_force, ylabel, title)."""

        if idx == 0:
            res = periodic_sawtooth_response(
                sys_, F0=p["F0"], T_period=p["T_period"],
                n_harmonics=p["n_harmonics"], t_end=p["t_end"], dt=p["dt"],
            )
            return (res, res["t"], res["F"],
                    "Force F [N]",
                    f"Sawtooth Force  ({p['n_harmonics']} harmonics)")

        if idx == 1:
            res = irregular_periodic_response(
                sys_, t_input=p["t_input"], F_input=p["F_input"], t_end=p["t_end"],
            )
            return (res, res["t"], res["F_input"],
                    "Force F [N]", "Irregular Periodic Force")

        if idx == 2:
            res = step_response(sys_, F0=p["F0"], t_end=p["t_end"], dt=p["dt"])
            t = res["t"]
            return (res, t, np.full_like(t, p["F0"]),
                    "Force F [N]",
                    f"Step Force  (F₀ = {p['F0']:.4g} N)")

        if idx == 3:
            res = rectangular_pulse_response(
                sys_, F0=p["F0"], t_d=p["t_d"], t_end=p["t_end"], dt=p["dt"],
            )
            t = res["t"]
            F = p["F0"] * (t < p["t_d"]).astype(float)
            return (res, t, F,
                    "Force F [N]",
                    f"Rectangular Pulse  (t_d = {p['t_d']:.4g} s)")

        if idx == 4:
            res = triangular_pulse_response(
                sys_, F0=p["F0"], t_d=p["t_d"], t_end=p["t_end"], dt=p["dt"],
            )
            t = res["t"]
            F = p["F0"] * np.clip(1.0 - t / p["t_d"], 0.0, None)
            return (res, t, F,
                    "Force F [N]",
                    f"Triangular Blast Pulse  (t_d = {p['t_d']:.4g} s)")

        if idx == 5:
            res = response_spectrum(
                sys_, excitation_type=p["excitation_type"],
                a0=p["a0"], t_d=p["t_d"],
                T_min=p["T_min"], T_max=p["T_max"], n_periods=p["n_periods"],
            )
            dt_p = min(p["T_min"] / 20.0, p["t_d"] / 50.0)
            ag = _build_pulse_accel(
                p["excitation_type"], p["a0"], p["t_d"], dt_p, p["t_d"] * 4.0
            )
            return (res, np.arange(len(ag)) * dt_p, ag,
                    "Acceleration aᵍ [m/s²]",
                    f"{p['excitation_type'].replace('_', ' ').title()} Excitation")

        raise ValueError(f"Unknown case index {idx}")

    # ── Plot: center panel (force / excitation) ───────────────────────────

    def _draw_force(
        self, t: np.ndarray, F: np.ndarray, ylabel: str, title: str
    ) -> None:
        fig = self.c_canvas.fig
        fig.clear()
        ax = fig.add_subplot(111)
        ax.plot(t, F, color=_PRIMARY, linewidth=0.9)
        ax.set_xlabel("Time t [s]")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(True)
        self.c_canvas.refresh()

    # ── Plot: right panel (response) ──────────────────────────────────────

    def _draw_response(self, case_idx: int, result: dict, sys_, params: dict = {}) -> None:
        fig = self.r_canvas.fig
        fig.clear()
        if case_idx == 5:
            self._plot_spectrum(fig, result, sys_, xaxis_freq=params.get("xaxis_freq", False))
        else:
            self._plot_time_history(fig, result, sys_)
        self.r_canvas.refresh()

    def _plot_time_history(self, fig: Figure, result: dict, sys_) -> None:
        axes = fig.subplots(3, 1, sharex=True)
        t = result["t"]

        axes[0].plot(t, result["x"], color="darkorange", linewidth=0.9)
        axes[0].set_ylabel("x [m]")
        axes[0].grid(True)

        axes[1].plot(t, result["v"], color=_PRIMARY, linewidth=0.9)
        axes[1].set_ylabel("v [m/s]")
        axes[1].grid(True)

        axes[2].plot(t, result["a"], color=_ACCENT, linewidth=0.9)
        axes[2].set_ylabel("a [m/s²]")
        axes[2].set_xlabel("Time t [s]")
        axes[2].grid(True)

        fig.suptitle(
            f"m={sys_.m:.3g} kg,  k={sys_.k:.3g} N/m,  "
            f"ζ={sys_.zeta:.4g},  Tₙ={sys_.T_n:.4g} s",
            fontsize=8.5,
        )

    def _plot_spectrum(self, fig: Figure, result: dict, sys_, xaxis_freq: bool = False) -> None:
        import math
        axes = fig.subplots(2, 2)
        T = result["T_range"]
        T_n = sys_.T_n
        f_n = sys_.omega_n / (2.0 * math.pi)

        if xaxis_freq:
            x = 1.0 / T          # convert period → frequency
            x_mark = f_n
            x_label = "Frequency fₙ [Hz]"
            marker_label = f"fₙ = {f_n:.4g} Hz"
        else:
            x = T
            x_mark = T_n
            x_label = "Period Tₙ [s]"
            marker_label = f"Tₙ = {T_n:.4g} s"

        for ax, y, lbl in zip(
            [axes[0, 0], axes[0, 1], axes[1, 0]],
            [result["Sd"], result["Sv"], result["Sa"]],
            ["Sd [m]", "Sv (pseudo) [m/s]", "Sa (pseudo) [m/s²]"],
        ):
            ax.plot(x, y, color=_PRIMARY, linewidth=0.9)
            ax.axvline(x_mark, color="darkorange", linestyle="--", linewidth=0.9,
                       label=marker_label)
            ax.set_xlabel(x_label)
            ax.set_ylabel(lbl)
            ax.legend(fontsize=7)
            ax.grid(True)

        axes[1, 1].plot(result["t_hist"], result["x_hist"],
                        color="darkorange", linewidth=0.9)
        axes[1, 1].set_xlabel("Time t [s]")
        axes[1, 1].set_ylabel("x_rel [m]")
        axes[1, 1].set_title(f"Time history at Tₙ = {T_n:.4g} s", fontsize=8)
        axes[1, 1].grid(True)

        fig.suptitle(
            f"Response Spectrum  |  ζ = {sys_.zeta:.4g},  "
            f"Tₙ = {T_n:.4g} s,  fₙ = {f_n:.4g} Hz",
            fontsize=8.5,
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import traceback

    # Surface exceptions that Qt would otherwise swallow silently
    def _excepthook(exc_type, exc_value, exc_tb):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        try:
            QMessageBox.critical(
                None, "Unhandled Error",
                "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
            )
        except Exception:
            pass
    sys.excepthook = _excepthook

    # Enable high-DPI rendering on Windows before creating QApplication
    if _QT == "PyQt5":
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("kenTool SDOF")
    app.setStyleSheet(_APP_QSS)
    win = MainWindow()
    win.show()
    sys.exit(app.exec() if _QT == "PySide6" else app.exec_())


if __name__ == "__main__":
    main()
