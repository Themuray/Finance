#!/usr/bin/env python3
"""
Robo-Advisor — Markowitz Portfolio Optimizer.

Run this file to launch the application:
    python main.py

Requires: PyQt5, yfinance, matplotlib, pandas, numpy, scipy
Install:  pip install -r requirements.txt
"""

import sys
import os
from typing import Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QLineEdit, QLabel, QComboBox, QMessageBox, QGroupBox,
    QGridLayout, QStatusBar, QSizePolicy, QListWidget, QListWidgetItem,
    QAbstractItemView, QProgressBar, QFrame, QScrollArea, QSlider,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor

import matplotlib
matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar,
)
from matplotlib.figure import Figure
import matplotlib.ticker as mticker
import pandas as pd
import numpy as np

import data
import optimizer

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
GREEN = "#26a69a"
RED = "#ef5350"
DARK_BG = "#1e1e2e"
PANEL_BG = "#2a2a3c"
CARD_BG = "#33334d"
TEXT = "#cdd6f4"
TEXT_DIM = "#a6adc8"
ACCENT = "#89b4fa"
BORDER = "#45475a"
GOLD = "#f9e2af"
PURPLE = "#cba6f7"

PIE_COLORS = [
    "#89b4fa", "#f9e2af", "#a6e3a1", "#f38ba8",
    "#cba6f7", "#fab387", "#94e2d5", "#f5c2e7",
    "#74c7ec", "#eba0ac", "#b4befe", "#89dceb",
]


def _stylesheet() -> str:
    """Return global application stylesheet (dark theme)."""
    return f"""
    QMainWindow, QWidget {{
        background-color: {DARK_BG};
        color: {TEXT};
        font-family: 'Segoe UI', 'Ubuntu', 'Cantarell', sans-serif;
        font-size: 13px;
    }}
    QGroupBox {{
        border: 1px solid {BORDER};
        border-radius: 6px;
        margin-top: 12px;
        padding-top: 16px;
        font-weight: bold;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
    }}
    QPushButton {{
        background-color: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 6px 16px;
        color: {TEXT};
        min-height: 28px;
    }}
    QPushButton:hover {{
        background-color: {ACCENT};
        color: {DARK_BG};
    }}
    QPushButton:pressed {{
        background-color: #7ba3e0;
    }}
    QPushButton#addBtn {{
        background-color: {GREEN};
        color: white;
        font-weight: bold;
    }}
    QPushButton#removeBtn {{
        background-color: {RED};
        color: white;
    }}
    QPushButton#optimizeBtn {{
        background-color: {ACCENT};
        color: {DARK_BG};
        font-weight: bold;
        font-size: 15px;
        min-height: 42px;
        border-radius: 6px;
    }}
    QPushButton#optimizeBtn:hover {{
        background-color: #7ba3e0;
    }}
    QPushButton#presetBtn {{
        font-size: 11px;
        padding: 4px 10px;
        min-height: 24px;
    }}
    QLineEdit {{
        background-color: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 6px 10px;
        color: {TEXT};
        min-height: 28px;
    }}
    QLineEdit:focus {{
        border-color: {ACCENT};
    }}
    QComboBox {{
        background-color: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 6px 10px;
        color: {TEXT};
        min-height: 28px;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {CARD_BG};
        color: {TEXT};
        selection-background-color: {ACCENT};
    }}
    QTableWidget {{
        background-color: {PANEL_BG};
        alternate-background-color: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: 4px;
        gridline-color: {BORDER};
        color: {TEXT};
    }}
    QTableWidget::item {{
        padding: 4px 8px;
    }}
    QTableWidget::item:selected {{
        background-color: {ACCENT};
        color: {DARK_BG};
    }}
    QHeaderView::section {{
        background-color: {CARD_BG};
        color: {TEXT};
        border: 1px solid {BORDER};
        padding: 6px;
        font-weight: bold;
    }}
    QTabWidget::pane {{
        border: 1px solid {BORDER};
        border-radius: 4px;
    }}
    QTabBar::tab {{
        background-color: {CARD_BG};
        color: {TEXT_DIM};
        border: 1px solid {BORDER};
        padding: 8px 16px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background-color: {ACCENT};
        color: {DARK_BG};
        font-weight: bold;
    }}
    QListWidget {{
        background-color: {PANEL_BG};
        border: 1px solid {BORDER};
        border-radius: 4px;
        color: {TEXT};
    }}
    QListWidget::item {{
        padding: 8px;
        border-bottom: 1px solid {BORDER};
    }}
    QListWidget::item:selected {{
        background-color: {ACCENT};
        color: {DARK_BG};
    }}
    QStatusBar {{
        background-color: {PANEL_BG};
        color: {TEXT_DIM};
    }}
    QSplitter::handle {{
        background-color: {BORDER};
    }}
    QProgressBar {{
        background-color: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: 4px;
        text-align: center;
        color: {TEXT};
    }}
    QProgressBar::chunk {{
        background-color: {ACCENT};
        border-radius: 3px;
    }}
    QScrollArea {{
        border: none;
    }}
    QLabel#sectionHeader {{
        font-size: 15px;
        font-weight: bold;
        color: {ACCENT};
        padding: 4px 0;
    }}
    QLabel#metricValue {{
        font-size: 14px;
        font-weight: bold;
    }}
    QLabel#metricLabel {{
        font-size: 11px;
        color: {TEXT_DIM};
    }}
    QSlider::groove:horizontal {{
        background: {CARD_BG};
        height: 8px;
        border-radius: 4px;
    }}
    QSlider::handle:horizontal {{
        background: {ACCENT};
        width: 20px;
        height: 20px;
        margin: -6px 0;
        border-radius: 10px;
    }}
    QSlider::sub-page:horizontal {{
        background: {ACCENT};
        border-radius: 4px;
    }}
    """


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_metric_card(name: str, parent_layout: QGridLayout,
                      row: int, col: int) -> QLabel:
    """Create a styled metric card and return the value QLabel."""
    frame = QFrame()
    frame.setStyleSheet(
        f"background-color: {CARD_BG}; border-radius: 6px; padding: 8px;")
    fl = QVBoxLayout(frame)
    fl.setContentsMargins(10, 8, 10, 8)
    lbl = QLabel(name)
    lbl.setObjectName("metricLabel")
    val = QLabel("—")
    val.setObjectName("metricValue")
    fl.addWidget(lbl)
    fl.addWidget(val)
    parent_layout.addWidget(frame, row, col)
    return val


# ---------------------------------------------------------------------------
# QThread Workers
# ---------------------------------------------------------------------------

class ValidateTickerWorker(QThread):
    """Validate a ticker symbol in the background."""
    finished = pyqtSignal(bool, str, str)  # is_valid, ticker, name_or_error

    def __init__(self, ticker: str, parent=None):
        super().__init__(parent)
        self.ticker = ticker

    def run(self):
        is_valid, msg = data.validate_ticker(self.ticker)
        self.finished.emit(is_valid, self.ticker.upper(), msg)


class DataFetchWorker(QThread):
    """Fetch historical data for all selected assets."""
    progress = pyqtSignal(str)
    finished = pyqtSignal(object)

    def __init__(self, tickers: list[str], period: str = "5y",
                 risk_free_rate: Optional[float] = None, parent=None):
        super().__init__(parent)
        self.tickers = tickers
        self.period = period
        self.risk_free_rate = risk_free_rate

    def run(self):
        self.progress.emit(f"Fetching data for {len(self.tickers)} assets...")
        result = data.fetch_portfolio_data(
            self.tickers, self.period, self.risk_free_rate)
        self.finished.emit(result)


class OptimizationWorker(QThread):
    """Run Markowitz optimization in the background."""
    progress = pyqtSignal(str)
    finished = pyqtSignal(object)

    def __init__(self, expected_returns: np.ndarray, cov_matrix: np.ndarray,
                 risk_free_rate: float, parent=None):
        super().__init__(parent)
        self.expected_returns = expected_returns
        self.cov_matrix = cov_matrix
        self.risk_free_rate = risk_free_rate

    def run(self):
        self.progress.emit("Computing efficient frontier...")
        result = optimizer.compute_efficient_frontier(
            self.expected_returns, self.cov_matrix, self.risk_free_rate)
        self.finished.emit(result)


# ---------------------------------------------------------------------------
# Asset Panel (left sidebar)
# ---------------------------------------------------------------------------

PRESETS = {
    "S&P Sectors": ["XLK", "XLF", "XLV", "XLE", "XLI", "XLY", "XLP", "XLU",
                     "XLB", "XLRE", "XLC"],
    "FAANG+": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"],
    "Balanced ETFs": ["SPY", "QQQ", "TLT", "GLD", "VNQ", "EFA", "EEM"],
}


class AssetPanel(QWidget):
    """Panel for adding/removing assets and configuring optimization."""

    optimize_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._assets: dict[str, str] = {}  # ticker -> display name
        self._worker: Optional[ValidateTickerWorker] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # --- Assets group ---
        assets_group = QGroupBox("Assets")
        ag_layout = QVBoxLayout(assets_group)

        # Ticker input row
        input_row = QHBoxLayout()
        self._ticker_input = QLineEdit()
        self._ticker_input.setPlaceholderText("Ticker (e.g. SPY)")
        self._ticker_input.returnPressed.connect(self._add_ticker)
        input_row.addWidget(self._ticker_input)
        add_btn = QPushButton("Add")
        add_btn.setObjectName("addBtn")
        add_btn.clicked.connect(self._add_ticker)
        input_row.addWidget(add_btn)
        ag_layout.addLayout(input_row)

        # Asset list
        self._asset_list = QListWidget()
        self._asset_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        ag_layout.addWidget(self._asset_list)

        # Remove button
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setObjectName("removeBtn")
        remove_btn.clicked.connect(self._remove_selected)
        ag_layout.addWidget(remove_btn)

        # Presets
        preset_label = QLabel("Quick Presets:")
        preset_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        ag_layout.addWidget(preset_label)
        preset_row = QHBoxLayout()
        for name in PRESETS:
            btn = QPushButton(name)
            btn.setObjectName("presetBtn")
            btn.clicked.connect(lambda _, n=name: self._load_preset(n))
            preset_row.addWidget(btn)
        ag_layout.addLayout(preset_row)

        layout.addWidget(assets_group)

        # --- Parameters group ---
        params_group = QGroupBox("Parameters")
        pg_layout = QGridLayout(params_group)

        pg_layout.addWidget(QLabel("Lookback:"), 0, 0)
        self._period_combo = QComboBox()
        self._period_combo.addItems(["1y", "2y", "3y", "5y", "10y"])
        self._period_combo.setCurrentText("5y")
        pg_layout.addWidget(self._period_combo, 0, 1)

        pg_layout.addWidget(QLabel("Risk-Free Rate (%):"), 1, 0)
        self._rf_input = QLineEdit()
        self._rf_input.setPlaceholderText("Auto (^TNX)")
        self._rf_input.setMaximumWidth(100)
        pg_layout.addWidget(self._rf_input, 1, 1)

        layout.addWidget(params_group)

        # --- Optimize button ---
        self._optimize_btn = QPushButton("Optimize Portfolio")
        self._optimize_btn.setObjectName("optimizeBtn")
        self._optimize_btn.clicked.connect(self.optimize_requested.emit)
        layout.addWidget(self._optimize_btn)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # indeterminate
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        layout.addWidget(self._status_label)

        layout.addStretch()

    def _add_ticker(self):
        ticker = self._ticker_input.text().strip().upper()
        if not ticker:
            return
        if ticker in self._assets:
            self._status_label.setText(f"{ticker} already added.")
            return
        self._ticker_input.setEnabled(False)
        self._status_label.setText(f"Validating {ticker}...")
        self._worker = ValidateTickerWorker(ticker, self)
        self._worker.finished.connect(self._on_validation)
        self._worker.start()

    def _on_validation(self, is_valid: bool, ticker: str, msg: str):
        self._ticker_input.setEnabled(True)
        if is_valid:
            self._assets[ticker] = msg
            item = QListWidgetItem(f"{ticker}  —  {msg}")
            item.setData(Qt.UserRole, ticker)
            self._asset_list.addItem(item)
            self._ticker_input.clear()
            self._status_label.setText(f"Added {ticker}")
        else:
            self._status_label.setText(msg)

    def _remove_selected(self):
        for item in self._asset_list.selectedItems():
            ticker = item.data(Qt.UserRole)
            self._assets.pop(ticker, None)
            self._asset_list.takeItem(self._asset_list.row(item))

    def _load_preset(self, name: str):
        tickers = PRESETS.get(name, [])
        for t in tickers:
            if t not in self._assets:
                self._assets[t] = t
                item = QListWidgetItem(f"{t}  —  (preset)")
                item.setData(Qt.UserRole, t)
                self._asset_list.addItem(item)
        self._status_label.setText(f"Loaded preset: {name}")

    def get_tickers(self) -> list[str]:
        return list(self._assets.keys())

    def get_period(self) -> str:
        return self._period_combo.currentText()

    def get_risk_free_rate(self) -> Optional[float]:
        text = self._rf_input.text().strip()
        if text:
            try:
                return float(text) / 100.0
            except ValueError:
                pass
        return None

    def set_busy(self, busy: bool):
        self._optimize_btn.setEnabled(not busy)
        self._progress.setVisible(busy)


# ---------------------------------------------------------------------------
# Risk Slider
# ---------------------------------------------------------------------------

class RiskSlider(QWidget):
    """Risk appetite control from Conservative to Aggressive."""

    risk_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        # Title
        title = QLabel("Risk Appetite")
        title.setObjectName("sectionHeader")
        layout.addWidget(title)

        # Slider row
        slider_row = QHBoxLayout()
        left_label = QLabel("Conservative")
        left_label.setStyleSheet(f"color: {GREEN}; font-size: 11px;")
        slider_row.addWidget(left_label)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setValue(50)
        self._slider.setTickPosition(QSlider.TicksBelow)
        self._slider.setTickInterval(25)
        self._slider.valueChanged.connect(self._on_value_changed)
        slider_row.addWidget(self._slider, stretch=1)

        right_label = QLabel("Aggressive")
        right_label.setStyleSheet(f"color: {RED}; font-size: 11px;")
        slider_row.addWidget(right_label)
        layout.addLayout(slider_row)

        # Value label
        self._value_label = QLabel("Risk Appetite: 0.50 (Balanced)")
        self._value_label.setAlignment(Qt.AlignCenter)
        self._value_label.setStyleSheet(f"color: {TEXT}; font-size: 12px;")
        layout.addWidget(self._value_label)

    def _on_value_changed(self, value: int):
        risk = value / 100.0
        labels = [
            (0.15, "Min Variance"), (0.35, "Conservative"),
            (0.65, "Balanced"), (0.85, "Growth"), (1.01, "Max Return"),
        ]
        desc = next(label for threshold, label in labels if risk < threshold)
        self._value_label.setText(f"Risk Appetite: {risk:.2f} ({desc})")
        self.risk_changed.emit(risk)

    def value(self) -> float:
        return self._slider.value() / 100.0


# ---------------------------------------------------------------------------
# Efficient Frontier Chart
# ---------------------------------------------------------------------------

class EfficientFrontierChart(QWidget):
    """Matplotlib chart showing the efficient frontier and key portfolios."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._figure = Figure(facecolor=DARK_BG, edgecolor=DARK_BG)
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._nav = NavigationToolbar(self._canvas, self)
        self._nav.setStyleSheet(
            f"background-color: {PANEL_BG}; color: {TEXT}; border: none;")
        layout.addWidget(self._nav)
        layout.addWidget(self._canvas)
        self._individual_vols: Optional[np.ndarray] = None
        self._individual_rets: Optional[np.ndarray] = None
        self._tickers: list[str] = []
        self._rf: float = 0.045

    def set_individual_assets(self, expected_returns: np.ndarray,
                              cov_matrix: np.ndarray, tickers: list[str],
                              risk_free_rate: float):
        """Store per-asset stats for plotting individual asset dots."""
        self._individual_rets = expected_returns
        self._individual_vols = np.sqrt(np.diag(cov_matrix))
        self._tickers = tickers
        self._rf = risk_free_rate

    def plot_frontier(self, frontier: optimizer.EfficientFrontierResult,
                      selected: Optional[optimizer.PortfolioResult] = None):
        self._figure.clear()
        ax = self._figure.add_subplot(111)
        ax.set_facecolor(DARK_BG)

        # Random portfolio cloud
        scatter = ax.scatter(
            frontier.random_volatilities, frontier.random_returns,
            c=frontier.random_sharpes, cmap="RdYlGn", alpha=0.3, s=8,
            edgecolors="none", zorder=1)
        cbar = self._figure.colorbar(scatter, ax=ax, shrink=0.8, pad=0.02)
        cbar.set_label("Sharpe Ratio", color=TEXT, fontsize=9)
        cbar.ax.yaxis.set_tick_params(color=TEXT)
        for label in cbar.ax.yaxis.get_ticklabels():
            label.set_color(TEXT)

        # Efficient frontier line
        ax.plot(frontier.frontier_volatilities, frontier.frontier_returns,
                color=ACCENT, linewidth=2.5, label="Efficient Frontier", zorder=5)

        # Min-variance marker
        mv = frontier.min_variance_portfolio
        ax.scatter(mv.volatility, mv.expected_return, marker="D", s=200,
                   color=GREEN, edgecolors="white", linewidth=1.5, zorder=10,
                   label=f"Min Variance (SR: {mv.sharpe_ratio:.2f})")

        # Max-Sharpe marker
        ms = frontier.max_sharpe_portfolio
        ax.scatter(ms.volatility, ms.expected_return, marker="*", s=400,
                   color=GOLD, edgecolors="white", linewidth=1.5, zorder=10,
                   label=f"Max Sharpe (SR: {ms.sharpe_ratio:.2f})")

        # Capital Market Line
        max_vol = max(frontier.frontier_volatilities) * 1.2
        cml_x = np.linspace(0, max_vol, 100)
        cml_y = self._rf + ms.sharpe_ratio * cml_x
        ax.plot(cml_x, cml_y, color=TEXT_DIM, linestyle="--", linewidth=1,
                alpha=0.7, label="Capital Market Line")

        # Individual assets
        if self._individual_vols is not None:
            for i, ticker in enumerate(self._tickers):
                ax.scatter(self._individual_vols[i], self._individual_rets[i],
                           marker="o", s=60, color=PIE_COLORS[i % len(PIE_COLORS)],
                           edgecolors="white", linewidth=1, zorder=8)
                ax.annotate(ticker,
                            (self._individual_vols[i], self._individual_rets[i]),
                            textcoords="offset points", xytext=(8, 4),
                            fontsize=9, color=TEXT, zorder=8)

        # Selected portfolio
        if selected is not None:
            ax.scatter(selected.volatility, selected.expected_return,
                       marker="o", s=250, color=RED, edgecolors="white",
                       linewidth=2, zorder=11,
                       label=f"Your Portfolio (SR: {selected.sharpe_ratio:.2f})")

        # Formatting
        ax.set_xlabel("Annualized Volatility", color=TEXT, fontsize=11)
        ax.set_ylabel("Annualized Return", color=TEXT, fontsize=11)
        ax.set_title("Efficient Frontier", color=TEXT, fontsize=14,
                      fontweight="bold")
        ax.xaxis.set_major_formatter(mticker.PercentFormatter(1.0))
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
        ax.tick_params(colors=TEXT)
        ax.grid(True, alpha=0.15, color=TEXT_DIM)
        for spine in ax.spines.values():
            spine.set_color(BORDER)
        ax.legend(loc="upper left", fontsize=8, facecolor=CARD_BG,
                  edgecolor=BORDER, labelcolor=TEXT)
        self._figure.tight_layout()
        self._canvas.draw()


# ---------------------------------------------------------------------------
# Allocation Chart (pie + table)
# ---------------------------------------------------------------------------

class AllocationChart(QWidget):
    """Portfolio allocation pie chart and weights table."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Pie chart
        self._figure = Figure(facecolor=DARK_BG, edgecolor=DARK_BG)
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._canvas, stretch=3)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(
            ["Ticker", "Name", "Weight %", "Amount ($)"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table, stretch=2)

    def update_allocation(self, tickers: list[str], names: dict[str, str],
                          weights: np.ndarray, total_investment: float = 10000.0):
        self._figure.clear()
        ax = self._figure.add_subplot(111)
        ax.set_facecolor(DARK_BG)

        # Sort by weight descending
        order = np.argsort(-weights)
        sorted_tickers = [tickers[i] for i in order]
        sorted_weights = weights[order]
        sorted_names = [names.get(t, t) for t in sorted_tickers]

        # Group small allocations into "Other"
        labels = []
        sizes = []
        colors = []
        other_weight = 0.0
        color_idx = 0
        for i, (t, w) in enumerate(zip(sorted_tickers, sorted_weights)):
            if w >= 0.01:
                labels.append(f"{t}\n{w*100:.1f}%")
                sizes.append(w)
                colors.append(PIE_COLORS[color_idx % len(PIE_COLORS)])
                color_idx += 1
            else:
                other_weight += w
        if other_weight > 0.001:
            labels.append(f"Other\n{other_weight*100:.1f}%")
            sizes.append(other_weight)
            colors.append(BORDER)

        if sizes:
            wedges, texts = ax.pie(
                sizes, labels=labels, colors=colors, startangle=90,
                textprops={"color": TEXT, "fontsize": 9},
                wedgeprops={"edgecolor": DARK_BG, "linewidth": 2})
        ax.set_title("Portfolio Allocation", color=TEXT, fontsize=14,
                      fontweight="bold")
        self._figure.tight_layout()
        self._canvas.draw()

        # Update table
        self._table.setRowCount(len(sorted_tickers))
        for row, (t, n, w) in enumerate(
                zip(sorted_tickers, sorted_names, sorted_weights)):
            self._table.setItem(row, 0, QTableWidgetItem(t))
            self._table.setItem(row, 1, QTableWidgetItem(n))
            pct_item = QTableWidgetItem(f"{w*100:.2f}%")
            pct_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._table.setItem(row, 2, pct_item)
            amt_item = QTableWidgetItem(f"${w * total_investment:,.2f}")
            amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._table.setItem(row, 3, amt_item)


# ---------------------------------------------------------------------------
# Statistics Panel
# ---------------------------------------------------------------------------

class StatsPanel(QWidget):
    """Card grid showing portfolio statistics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._labels: dict[str, QLabel] = {}
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(12, 12, 12, 12)
        scroll.setWidget(inner)
        outer.addWidget(scroll)

        hdr = QLabel("Portfolio Statistics")
        hdr.setObjectName("sectionHeader")
        layout.addWidget(hdr)

        grid = QGridLayout()
        grid.setSpacing(12)
        metrics = [
            "Expected Return", "Volatility", "Sharpe Ratio", "Sortino Ratio",
            "Max Drawdown", "VaR 95%", "CVaR 95%", "Risk-Free Rate",
        ]
        for i, name in enumerate(metrics):
            row, col = divmod(i, 4)
            self._labels[name] = _make_metric_card(name, grid, row, col)
        layout.addLayout(grid)
        layout.addStretch()

    def update_stats(self, stats: dict):
        mapping = {
            "Expected Return": ("expected_return", True),
            "Volatility": ("volatility", True),
            "Sharpe Ratio": ("sharpe_ratio", False),
            "Sortino Ratio": ("sortino_ratio", False),
            "Max Drawdown": ("max_drawdown", True),
            "VaR 95%": ("var_95", True),
            "CVaR 95%": ("cvar_95", True),
            "Risk-Free Rate": ("risk_free_rate", True),
        }
        for label_name, (key, is_pct) in mapping.items():
            val = stats.get(key)
            if val is None:
                self._labels[label_name].setText("—")
                continue
            if is_pct:
                text = f"{val*100:+.2f}%" if key in ("expected_return",) else f"{val*100:.2f}%"
            else:
                text = f"{val:.3f}"
            self._labels[label_name].setText(text)

            # Color-code some values
            if key == "expected_return":
                color = GREEN if val >= 0 else RED
                self._labels[label_name].setStyleSheet(
                    f"font-size: 14px; font-weight: bold; color: {color};")
            elif key == "max_drawdown":
                self._labels[label_name].setStyleSheet(
                    f"font-size: 14px; font-weight: bold; color: {RED};")
            elif key == "sharpe_ratio":
                color = GREEN if val >= 1.0 else (TEXT if val >= 0.5 else RED)
                self._labels[label_name].setStyleSheet(
                    f"font-size: 14px; font-weight: bold; color: {color};")


# ---------------------------------------------------------------------------
# Backtest Chart
# ---------------------------------------------------------------------------

class BacktestChart(QWidget):
    """Historical performance backtest with drawdown."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._figure = Figure(facecolor=DARK_BG, edgecolor=DARK_BG)
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._nav = NavigationToolbar(self._canvas, self)
        self._nav.setStyleSheet(
            f"background-color: {PANEL_BG}; color: {TEXT}; border: none;")
        layout.addWidget(self._nav)
        layout.addWidget(self._canvas)

    def plot_backtest(self, backtest_df: pd.DataFrame, tickers: list[str],
                      weights: np.ndarray):
        self._figure.clear()
        axes = self._figure.subplots(
            2, 1, sharex=True,
            gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05})

        ax_val = axes[0]
        ax_dd = axes[1]

        for ax in axes:
            ax.set_facecolor(DARK_BG)
            ax.tick_params(colors=TEXT)
            ax.grid(True, alpha=0.15, color=TEXT_DIM)
            for spine in ax.spines.values():
                spine.set_color(BORDER)

        # Portfolio value
        ax_val.plot(backtest_df.index, backtest_df["Portfolio_Value"],
                    color=ACCENT, linewidth=2, label="Portfolio")

        # Individual assets
        for i, t in enumerate(tickers):
            if t in backtest_df.columns and weights[i] > 0.01:
                ax_val.plot(backtest_df.index, backtest_df[t],
                            color=PIE_COLORS[i % len(PIE_COLORS)],
                            linewidth=1, alpha=0.6, label=t)

        ax_val.set_title("Historical Backtest (Static Allocation)", color=TEXT,
                          fontsize=14, fontweight="bold")
        ax_val.set_ylabel("Portfolio Value ($)", color=TEXT, fontsize=10)
        ax_val.legend(loc="upper left", fontsize=8, facecolor=CARD_BG,
                      edgecolor=BORDER, labelcolor=TEXT)

        # Drawdown
        ax_dd.fill_between(backtest_df.index, backtest_df["Drawdown"], 0,
                           color=RED, alpha=0.4)
        ax_dd.plot(backtest_df.index, backtest_df["Drawdown"],
                   color=RED, linewidth=1)
        ax_dd.set_ylabel("Drawdown", color=TEXT, fontsize=10)
        ax_dd.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))

        try:
            self._figure.tight_layout()
        except ValueError:
            pass
        self._canvas.draw()


# ---------------------------------------------------------------------------
# Correlation Heatmap
# ---------------------------------------------------------------------------

class CorrelationHeatmap(QWidget):
    """Asset correlation matrix heatmap."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._figure = Figure(facecolor=DARK_BG, edgecolor=DARK_BG)
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._canvas)

    def plot_correlation(self, corr: np.ndarray, tickers: list[str]):
        self._figure.clear()
        ax = self._figure.add_subplot(111)
        ax.set_facecolor(DARK_BG)

        n = len(tickers)
        im = ax.imshow(corr, cmap="RdYlGn", vmin=-1, vmax=1, aspect="auto")
        cbar = self._figure.colorbar(im, ax=ax, shrink=0.8)
        cbar.set_label("Correlation", color=TEXT, fontsize=9)
        cbar.ax.yaxis.set_tick_params(color=TEXT)
        for label in cbar.ax.yaxis.get_ticklabels():
            label.set_color(TEXT)

        # Annotate cells
        for i in range(n):
            for j in range(n):
                val = corr[i, j]
                color = "white" if abs(val) > 0.5 else TEXT
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        color=color, fontsize=max(7, 11 - n // 3))

        ax.set_xticks(range(n))
        ax.set_xticklabels(tickers, color=TEXT, fontsize=9, rotation=45,
                           ha="right")
        ax.set_yticks(range(n))
        ax.set_yticklabels(tickers, color=TEXT, fontsize=9)
        ax.set_title("Asset Correlation Matrix", color=TEXT, fontsize=14,
                      fontweight="bold")
        ax.tick_params(colors=TEXT)
        self._figure.tight_layout()
        self._canvas.draw()


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    """Application shell orchestrating all panels."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robo-Advisor  —  Markowitz Portfolio Optimizer")
        self.resize(1500, 950)

        self._portfolio_data: Optional[data.PortfolioData] = None
        self._frontier_result: Optional[optimizer.EfficientFrontierResult] = None
        self._current_portfolio: Optional[optimizer.PortfolioResult] = None
        self._workers: list[QThread] = []
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Left panel
        self._asset_panel = AssetPanel()
        self._asset_panel.setFixedWidth(370)
        self._asset_panel.optimize_requested.connect(self._on_optimize)

        # Right panel — tabs
        self._tabs = QTabWidget()

        # Tab 1: Efficient Frontier + Risk Slider
        frontier_widget = QWidget()
        frontier_layout = QVBoxLayout(frontier_widget)
        frontier_layout.setContentsMargins(0, 0, 0, 0)
        self._frontier_chart = EfficientFrontierChart()
        frontier_layout.addWidget(self._frontier_chart, stretch=1)
        self._risk_slider = RiskSlider()
        self._risk_slider.risk_changed.connect(self._on_risk_changed)
        frontier_layout.addWidget(self._risk_slider)
        self._tabs.addTab(frontier_widget, "Efficient Frontier")

        # Tab 2: Allocation
        self._allocation_chart = AllocationChart()
        self._tabs.addTab(self._allocation_chart, "Allocation")

        # Tab 3: Statistics
        self._stats_panel = StatsPanel()
        self._tabs.addTab(self._stats_panel, "Statistics")

        # Tab 4: Backtest
        self._backtest_chart = BacktestChart()
        self._tabs.addTab(self._backtest_chart, "Backtest")

        # Tab 5: Correlation
        self._correlation_heatmap = CorrelationHeatmap()
        self._tabs.addTab(self._correlation_heatmap, "Correlation")

        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._asset_panel)
        splitter.addWidget(self._tabs)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter)

        # Status bar
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage(
            "Add assets and click 'Optimize Portfolio' to begin.")

    # --- Optimization pipeline ---

    def _on_optimize(self):
        tickers = self._asset_panel.get_tickers()
        if len(tickers) < 2:
            QMessageBox.warning(self, "Need More Assets",
                                "Add at least 2 assets to optimize a portfolio.")
            return

        self._asset_panel.set_busy(True)
        self._statusbar.showMessage("Fetching historical data...")

        period = self._asset_panel.get_period()
        rf = self._asset_panel.get_risk_free_rate()

        worker = DataFetchWorker(tickers, period, rf, self)
        worker.progress.connect(self._statusbar.showMessage)
        worker.finished.connect(self._on_data_ready)
        self._workers.append(worker)
        worker.start()

    def _on_data_ready(self, portfolio_data: data.PortfolioData):
        self._portfolio_data = portfolio_data

        if portfolio_data.errors:
            self._statusbar.showMessage(
                f"Warnings: {'; '.join(portfolio_data.errors)}")

        if len(portfolio_data.tickers) < 2:
            self._asset_panel.set_busy(False)
            QMessageBox.critical(self, "Insufficient Data",
                                 "Could not fetch data for enough assets.\n"
                                 + "\n".join(portfolio_data.errors))
            return

        # Show correlation immediately
        self._correlation_heatmap.plot_correlation(
            portfolio_data.correlation_matrix, portfolio_data.tickers)

        # Store individual asset data for frontier chart
        self._frontier_chart.set_individual_assets(
            portfolio_data.expected_returns, portfolio_data.cov_matrix,
            portfolio_data.tickers, portfolio_data.risk_free_rate)

        # Start optimization
        worker = OptimizationWorker(
            portfolio_data.expected_returns, portfolio_data.cov_matrix,
            portfolio_data.risk_free_rate, self)
        worker.progress.connect(self._statusbar.showMessage)
        worker.finished.connect(self._on_optimization_done)
        self._workers.append(worker)
        worker.start()

    def _on_optimization_done(self, frontier: optimizer.EfficientFrontierResult):
        self._frontier_result = frontier
        self._asset_panel.set_busy(False)

        risk = self._risk_slider.value()
        self._update_selected_portfolio(risk)

        n = len(self._portfolio_data.tickers)
        ms = frontier.max_sharpe_portfolio
        self._statusbar.showMessage(
            f"Optimization complete — {n} assets, "
            f"Max Sharpe: {ms.sharpe_ratio:.3f}")

    def _on_risk_changed(self, risk: float):
        if self._frontier_result is None or self._portfolio_data is None:
            return
        self._update_selected_portfolio(risk)

    def _update_selected_portfolio(self, risk: float):
        pd_ = self._portfolio_data
        fr = self._frontier_result

        self._current_portfolio = optimizer.interpolate_frontier(
            risk, fr, pd_.expected_returns, pd_.cov_matrix,
            pd_.risk_free_rate)

        # Frontier chart
        self._frontier_chart.plot_frontier(fr, self._current_portfolio)

        # Allocation
        self._allocation_chart.update_allocation(
            pd_.tickers, pd_.names, self._current_portfolio.weights)

        # Stats
        stats = optimizer.compute_portfolio_stats(
            self._current_portfolio.weights,
            pd_.expected_returns, pd_.cov_matrix,
            pd_.returns, pd_.risk_free_rate)
        self._stats_panel.update_stats(stats)

        # Backtest
        backtest_df = optimizer.backtest_portfolio(
            self._current_portfolio.weights, pd_.returns)
        self._backtest_chart.plot_backtest(
            backtest_df, pd_.tickers, self._current_portfolio.weights)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Robo-Advisor")
    app.setStyle("Fusion")
    app.setStyleSheet(_stylesheet())

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
