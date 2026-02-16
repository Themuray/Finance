#!/usr/bin/env python3
"""
Stock Analyzer — a desktop application for retail investors.

Run this file to launch the application:
    python main.py

Requires: PyQt5, yfinance, matplotlib, pandas, numpy
Install:  pip install -r requirements.txt
"""

import sys
import os
import webbrowser
from datetime import datetime
from functools import partial
from typing import Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QLineEdit, QLabel, QComboBox, QMessageBox, QFileDialog,
    QGroupBox, QGridLayout, QStatusBar, QAction, QMenu, QToolBar,
    QSizePolicy, QListWidget, QListWidgetItem, QAbstractItemView,
    QProgressBar, QFrame, QScrollArea, QInputDialog,
)
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, pyqtSlot, QSize, QTimer,
)
from PyQt5.QtGui import QFont, QColor, QIcon, QPainter, QPen, QBrush

import matplotlib
matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar,
)
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import pandas as pd
import numpy as np

import data
import storage


# ---------------------------------------------------------------------------
# Colour palette — keeps the UI consistent
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
    QLabel#priceLabel {{
        font-size: 28px;
        font-weight: bold;
    }}
    QLabel#tickerLabel {{
        font-size: 20px;
        font-weight: bold;
        color: {ACCENT};
    }}
    """


# ---------------------------------------------------------------------------
# Background worker threads
# ---------------------------------------------------------------------------

class QuoteFetchWorker(QThread):
    """Fetches stock quotes in a background thread."""
    finished = pyqtSignal(object)

    def __init__(self, ticker: str, parent=None):
        super().__init__(parent)
        self.ticker = ticker

    def run(self):
        self.finished.emit(data.fetch_quote(self.ticker))


class HistoryFetchWorker(QThread):
    """Fetches price history in a background thread."""
    finished = pyqtSignal(str, str, object)

    def __init__(self, ticker: str, period: str, parent=None):
        super().__init__(parent)
        self.ticker = ticker
        self.period = period

    def run(self):
        df = data.fetch_history(self.ticker, self.period)
        if not df.empty:
            df = data.compute_technical_indicators(df)
        self.finished.emit(self.ticker, self.period, df)


class MultiFetchWorker(QThread):
    """Fetches quotes for multiple tickers (used by watchlist refresh)."""
    progress = pyqtSignal(int, int)
    quote_ready = pyqtSignal(object)
    finished = pyqtSignal()

    def __init__(self, tickers: list[str], parent=None):
        super().__init__(parent)
        self.tickers = tickers

    def run(self):
        for i, ticker in enumerate(self.tickers):
            self.quote_ready.emit(data.fetch_quote(ticker))
            self.progress.emit(i + 1, len(self.tickers))
        self.finished.emit()


class NewsFetchWorker(QThread):
    """Fetches news headlines in a background thread."""
    finished = pyqtSignal(str, list)

    def __init__(self, ticker: str, parent=None):
        super().__init__(parent)
        self.ticker = ticker

    def run(self):
        self.finished.emit(self.ticker, data.fetch_news(self.ticker))


class AnalystFetchWorker(QThread):
    """Fetches analyst data in a background thread."""
    finished = pyqtSignal(object)

    def __init__(self, ticker: str, parent=None):
        super().__init__(parent)
        self.ticker = ticker

    def run(self):
        self.finished.emit(data.fetch_analyst_data(self.ticker))


# ---------------------------------------------------------------------------
# 52-week / price target range bar
# ---------------------------------------------------------------------------

class RangeBar(QWidget):
    """Visual bar showing a value's position within a range (e.g. 52-week)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(60)
        self._low = 0.0
        self._high = 0.0
        self._current = 0.0
        self._label_low = ""
        self._label_high = ""

    def set_values(self, low: float, high: float, current: float):
        self._low = low
        self._high = high
        self._current = current
        self._label_low = f"${low:,.2f}"
        self._label_high = f"${high:,.2f}"
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width() - 20
        h = self.height()
        x0 = 10
        track_y = h // 2
        track_h = 8

        # Track background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(BORDER)))
        painter.drawRoundedRect(x0, track_y - track_h // 2, w, track_h, 4, 4)

        # Position percentage
        if self._high > self._low:
            pct = max(0.0, min(1.0,
                (self._current - self._low) / (self._high - self._low)))
        else:
            pct = 0.5

        fill_w = max(1, int(w * pct))

        # Color depends on position — green is value territory, red is overextended
        if pct < 0.7:
            color = QColor(GREEN)
        elif pct < 0.9:
            color = QColor(ACCENT)
        else:
            color = QColor(RED)

        # Filled track
        painter.setBrush(QBrush(color))
        painter.drawRoundedRect(x0, track_y - track_h // 2, fill_w, track_h, 4, 4)

        # Pointer dot
        ptr_x = x0 + fill_w
        painter.setBrush(QBrush(QColor(TEXT)))
        painter.drawEllipse(ptr_x - 5, track_y - 5, 10, 10)

        # Low / High labels
        painter.setPen(QPen(QColor(TEXT_DIM)))
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(x0, track_y - 14, self._label_low)

        fm = painter.fontMetrics()
        high_w = fm.horizontalAdvance(self._label_high)
        painter.drawText(x0 + w - high_w, track_y - 14, self._label_high)

        # Current price at pointer
        painter.setPen(QPen(QColor(TEXT)))
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        price_text = f"${self._current:,.2f}"
        pw = painter.fontMetrics().horizontalAdvance(price_text)
        painter.drawText(max(x0, min(ptr_x - pw // 2, x0 + w - pw)),
                         track_y + 22, price_text)
        painter.end()


# ---------------------------------------------------------------------------
# Chart widget (matplotlib embedded in Qt)
# ---------------------------------------------------------------------------

class ChartWidget(QWidget):
    """Interactive price chart with technical overlays."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_ticker = ""
        self._current_period = "1y"
        self._show_sma20 = True
        self._show_sma50 = True
        self._show_volume = True
        self._show_rsi = False
        self._show_bollinger = False
        self._show_macd = False
        self._show_ema200 = False
        self._df: Optional[pd.DataFrame] = None
        self._worker: Optional[HistoryFetchWorker] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar row — period buttons + indicator toggles
        toolbar = QHBoxLayout()

        toolbar.addWidget(QLabel("Period:"))
        self._period_buttons: dict[str, QPushButton] = {}
        for label in data.CHART_PERIODS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(label == "1Y")
            btn.clicked.connect(partial(self._on_period, label))
            toolbar.addWidget(btn)
            self._period_buttons[label] = btn

        toolbar.addStretch()
        toolbar.addWidget(QLabel("Show:"))

        # Indicator toggle buttons
        toggles = [
            ("SMA 20", True,  "_sma20_btn",  "_show_sma20"),
            ("SMA 50", True,  "_sma50_btn",  "_show_sma50"),
            ("EMA 200", False, "_ema200_btn", "_show_ema200"),
            ("BB",     False, "_bb_btn",     "_show_bollinger"),
            ("Volume", True,  "_vol_btn",    "_show_volume"),
            ("RSI",    False, "_rsi_btn",    "_show_rsi"),
            ("MACD",   False, "_macd_btn",   "_show_macd"),
        ]
        for text, checked, btn_attr, flag_attr in toggles:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setChecked(checked)
            btn.clicked.connect(partial(self._on_toggle, flag_attr, btn))
            toolbar.addWidget(btn)
            setattr(self, btn_attr, btn)

        layout.addLayout(toolbar)

        # Matplotlib figure
        self._figure = Figure(facecolor=DARK_BG, edgecolor=DARK_BG)
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Navigation toolbar for zoom/pan
        self._nav_toolbar = NavigationToolbar(self._canvas, self)
        self._nav_toolbar.setStyleSheet(
            f"background-color: {PANEL_BG}; color: {TEXT}; border: none;"
        )
        layout.addWidget(self._nav_toolbar)
        layout.addWidget(self._canvas)

    # --- public API ---

    def load_ticker(self, ticker: str, period: Optional[str] = None):
        """Begin loading chart data for the given ticker."""
        self._current_ticker = ticker.upper()
        if period:
            self._current_period = period
        yf_period = data.CHART_PERIODS.get(
            self._current_period, self._current_period
        )
        self._worker = HistoryFetchWorker(ticker, yf_period, self)
        self._worker.finished.connect(self._on_data)
        self._worker.start()

    # --- callbacks ---

    def _on_period(self, label: str):
        for k, btn in self._period_buttons.items():
            btn.setChecked(k == label)
        self._current_period = label
        if self._current_ticker:
            self.load_ticker(self._current_ticker, label)

    def _on_toggle(self, flag_attr: str, btn: QPushButton):
        setattr(self, flag_attr, btn.isChecked())
        self._redraw()

    @pyqtSlot(str, str, object)
    def _on_data(self, ticker: str, period: str, df: pd.DataFrame):
        self._df = df
        self._redraw()

    # --- drawing ---

    def _redraw(self):
        self._figure.clear()
        if self._df is None or self._df.empty:
            ax = self._figure.add_subplot(111)
            ax.set_facecolor(DARK_BG)
            ax.text(0.5, 0.5, "No data available", transform=ax.transAxes,
                    ha="center", va="center", color=TEXT_DIM, fontsize=14)
            ax.set_xticks([]); ax.set_yticks([])
            self._canvas.draw_idle()
            return

        df = self._df
        show_rsi = self._show_rsi and "RSI" in df.columns
        show_macd = self._show_macd and "MACD" in df.columns

        # Determine subplot layout
        n_rows = 1
        ratios = [4]
        if self._show_volume:
            n_rows += 1; ratios.append(1)
        if show_rsi:
            n_rows += 1; ratios.append(1)
        if show_macd:
            n_rows += 1; ratios.append(1.2)

        axes = self._figure.subplots(
            n_rows, 1, sharex=True,
            gridspec_kw={"height_ratios": ratios, "hspace": 0.05},
        )
        if n_rows == 1:
            axes = [axes]

        ax_price = axes[0]
        ax_idx = 1
        dates = df.index

        # --- Price subplot ---
        ax_price.set_facecolor(DARK_BG)
        ax_price.plot(dates, df["Close"], color=ACCENT, linewidth=1.5, label="Close")

        if self._show_sma20 and "SMA_20" in df.columns:
            ax_price.plot(dates, df["SMA_20"], color="#f9e2af",
                          linewidth=1, alpha=0.8, label="SMA 20")
        if self._show_sma50 and "SMA_50" in df.columns:
            ax_price.plot(dates, df["SMA_50"], color="#f38ba8",
                          linewidth=1, alpha=0.8, label="SMA 50")
        if self._show_ema200 and "EMA_200" in df.columns:
            ax_price.plot(dates, df["EMA_200"], color="#fab387",
                          linewidth=1.2, alpha=0.9, label="EMA 200",
                          linestyle="--")
        if self._show_bollinger and "BB_Upper" in df.columns:
            ax_price.plot(dates, df["BB_Upper"], color="#94e2d5",
                          linewidth=0.8, alpha=0.6, label="BB Upper")
            ax_price.plot(dates, df["BB_Lower"], color="#94e2d5",
                          linewidth=0.8, alpha=0.6, label="BB Lower")
            ax_price.fill_between(dates, df["BB_Upper"], df["BB_Lower"],
                                  alpha=0.05, color="#94e2d5")

        ax_price.legend(loc="upper left", fontsize=7,
                        facecolor=CARD_BG, edgecolor=BORDER, labelcolor=TEXT)
        ax_price.set_ylabel("Price ($)", color=TEXT, fontsize=10)
        ax_price.set_title(
            f"{self._current_ticker} — {self._current_period}",
            color=TEXT, fontsize=13, fontweight="bold", pad=10,
        )
        ax_price.tick_params(colors=TEXT, labelsize=9)
        ax_price.grid(True, alpha=0.15, color=TEXT_DIM)
        for spine in ax_price.spines.values():
            spine.set_color(BORDER)

        # --- Volume subplot ---
        if self._show_volume and "Volume" in df.columns:
            ax_vol = axes[ax_idx]; ax_idx += 1
            ax_vol.set_facecolor(DARK_BG)
            colors = [GREEN if c >= o else RED
                      for c, o in zip(df["Close"], df["Open"])]
            ax_vol.bar(dates, df["Volume"], color=colors, alpha=0.6, width=0.8)
            ax_vol.set_ylabel("Volume", color=TEXT, fontsize=9)
            ax_vol.tick_params(colors=TEXT, labelsize=8)
            ax_vol.yaxis.set_major_formatter(
                mticker.FuncFormatter(lambda x, _: data.format_large_number(x)))
            ax_vol.grid(True, alpha=0.15, color=TEXT_DIM)
            for spine in ax_vol.spines.values():
                spine.set_color(BORDER)

        # --- RSI subplot ---
        if show_rsi:
            ax_rsi = axes[ax_idx]; ax_idx += 1
            ax_rsi.set_facecolor(DARK_BG)
            ax_rsi.plot(dates, df["RSI"], color="#cba6f7", linewidth=1.2)
            ax_rsi.axhline(70, color=RED, linewidth=0.8, linestyle="--", alpha=0.6)
            ax_rsi.axhline(30, color=GREEN, linewidth=0.8, linestyle="--", alpha=0.6)
            ax_rsi.fill_between(dates, 30, 70, alpha=0.05, color=TEXT)
            ax_rsi.set_ylim(0, 100)
            ax_rsi.set_ylabel("RSI", color=TEXT, fontsize=9)
            ax_rsi.tick_params(colors=TEXT, labelsize=8)
            ax_rsi.grid(True, alpha=0.15, color=TEXT_DIM)
            for spine in ax_rsi.spines.values():
                spine.set_color(BORDER)

        # --- MACD subplot ---
        if show_macd:
            ax_macd = axes[ax_idx]; ax_idx += 1
            ax_macd.set_facecolor(DARK_BG)
            ax_macd.plot(dates, df["MACD"], color="#89b4fa",
                         linewidth=1.0, label="MACD")
            ax_macd.plot(dates, df["MACD_Signal"], color="#f38ba8",
                         linewidth=1.0, label="Signal")
            hist_colors = [GREEN if v >= 0 else RED for v in df["MACD_Hist"]]
            ax_macd.bar(dates, df["MACD_Hist"], color=hist_colors,
                        alpha=0.5, width=0.8)
            ax_macd.axhline(0, color=TEXT_DIM, linewidth=0.5, linestyle="--")
            ax_macd.set_ylabel("MACD", color=TEXT, fontsize=9)
            ax_macd.legend(loc="upper left", fontsize=7,
                           facecolor=CARD_BG, edgecolor=BORDER, labelcolor=TEXT)
            ax_macd.tick_params(colors=TEXT, labelsize=8)
            ax_macd.grid(True, alpha=0.15, color=TEXT_DIM)
            for spine in ax_macd.spines.values():
                spine.set_color(BORDER)

        # Format x-axis dates
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        axes[-1].tick_params(axis="x", rotation=30)

        self._figure.tight_layout()
        self._canvas.draw_idle()


# ---------------------------------------------------------------------------
# Comparison chart widget
# ---------------------------------------------------------------------------

class CompareWidget(QWidget):
    """Compare normalised price performance of multiple stocks."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers: list[HistoryFetchWorker] = []
        self._data: dict[str, pd.DataFrame] = {}
        self._tickers: list[str] = []
        self._period = "1y"
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        top = QHBoxLayout()
        top.addWidget(QLabel("Tickers (comma-separated):"))
        self._input = QLineEdit()
        self._input.setPlaceholderText("e.g. AAPL, MSFT, GOOGL")
        self._input.returnPressed.connect(self._on_compare)
        top.addWidget(self._input)

        self._period_combo = QComboBox()
        self._period_combo.addItems(list(data.CHART_PERIODS.keys()))
        self._period_combo.setCurrentText("1Y")
        top.addWidget(self._period_combo)

        compare_btn = QPushButton("Compare")
        compare_btn.setObjectName("addBtn")
        compare_btn.clicked.connect(self._on_compare)
        top.addWidget(compare_btn)
        layout.addLayout(top)

        self._figure = Figure(facecolor=DARK_BG, edgecolor=DARK_BG)
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._nav = NavigationToolbar(self._canvas, self)
        self._nav.setStyleSheet(
            f"background-color: {PANEL_BG}; color: {TEXT}; border: none;")
        layout.addWidget(self._nav)
        layout.addWidget(self._canvas)
        self._status = QLabel("")
        layout.addWidget(self._status)

    def _on_compare(self):
        raw = self._input.text().strip()
        if not raw:
            return
        tickers = [t.strip().upper() for t in raw.split(",") if t.strip()]
        if len(tickers) < 2:
            self._status.setText("Enter at least 2 tickers separated by commas.")
            return
        if len(tickers) > 8:
            self._status.setText("Maximum 8 tickers for comparison.")
            return

        self._tickers = tickers
        self._data.clear()
        self._period = self._period_combo.currentText()
        yf_period = data.CHART_PERIODS.get(self._period, "1y")
        self._status.setText(f"Loading {len(tickers)} stocks...")

        for ticker in tickers:
            worker = HistoryFetchWorker(ticker, yf_period, self)
            worker.finished.connect(self._on_data_ready)
            self._workers.append(worker)
            worker.start()

    @pyqtSlot(str, str, object)
    def _on_data_ready(self, ticker: str, period: str, df: pd.DataFrame):
        if not df.empty:
            self._data[ticker.upper()] = df
        if len(self._data) + sum(
            1 for t in self._tickers if t not in self._data
            and not any(w.isRunning() for w in self._workers)
        ) >= len(self._tickers):
            self._draw()
            self._status.setText(
                f"Showing {len(self._data)} of {len(self._tickers)} stocks.")

    def _draw(self):
        self._figure.clear()
        if not self._data:
            ax = self._figure.add_subplot(111)
            ax.set_facecolor(DARK_BG)
            ax.text(0.5, 0.5, "No data to compare", transform=ax.transAxes,
                    ha="center", va="center", color=TEXT_DIM, fontsize=14)
            self._canvas.draw_idle()
            return

        ax = self._figure.add_subplot(111)
        ax.set_facecolor(DARK_BG)
        colours = ["#89b4fa", "#f9e2af", "#a6e3a1", "#f38ba8",
                    "#cba6f7", "#fab387", "#94e2d5", "#f5c2e7"]

        for i, (ticker, df) in enumerate(self._data.items()):
            if df.empty or "Close" not in df.columns:
                continue
            first = df["Close"].iloc[0]
            if first == 0:
                continue
            normalised = ((df["Close"] / first) - 1) * 100
            ax.plot(df.index, normalised, label=ticker,
                    color=colours[i % len(colours)], linewidth=1.5)

        ax.axhline(0, color=TEXT_DIM, linewidth=0.5, linestyle="--")
        ax.set_ylabel("Return (%)", color=TEXT, fontsize=10)
        ax.set_title(f"Performance Comparison — {self._period}",
                     color=TEXT, fontsize=13, fontweight="bold")
        ax.legend(loc="upper left", fontsize=9,
                  facecolor=CARD_BG, edgecolor=BORDER, labelcolor=TEXT)
        ax.tick_params(colors=TEXT, labelsize=9)
        ax.grid(True, alpha=0.15, color=TEXT_DIM)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        for spine in ax.spines.values():
            spine.set_color(BORDER)

        self._figure.tight_layout()
        self._canvas.draw_idle()


# ---------------------------------------------------------------------------
# Helper to build a metric card frame
# ---------------------------------------------------------------------------

def _make_metric_card(name: str, labels_dict: dict):
    """Create a styled metric card and register it in labels_dict."""
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
    labels_dict[name] = (lbl, val)
    return frame


# ---------------------------------------------------------------------------
# Metrics panel
# ---------------------------------------------------------------------------

class MetricsPanel(QWidget):
    """Displays key financial metrics as a card grid with 52-week range bar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        # Wrap everything in a scroll area so it fits smaller screens
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        self._layout = QVBoxLayout(inner)
        self._layout.setContentsMargins(8, 8, 8, 8)
        scroll.setWidget(inner)
        outer.addWidget(scroll)

        # Header — ticker + name
        header = QHBoxLayout()
        self._ticker_label = QLabel("")
        self._ticker_label.setObjectName("tickerLabel")
        header.addWidget(self._ticker_label)
        self._name_label = QLabel("")
        self._name_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 14px;")
        header.addWidget(self._name_label)
        header.addStretch()
        self._layout.addLayout(header)

        # Price + change
        price_row = QHBoxLayout()
        self._price_label = QLabel("—")
        self._price_label.setObjectName("priceLabel")
        price_row.addWidget(self._price_label)
        self._change_label = QLabel("")
        self._change_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        price_row.addWidget(self._change_label)
        price_row.addStretch()
        self._layout.addLayout(price_row)

        self._sector_label = QLabel("")
        self._sector_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        self._layout.addWidget(self._sector_label)

        # 52-Week Range bar
        range_label = QLabel("52-Week Range")
        range_label.setObjectName("metricLabel")
        self._layout.addWidget(range_label)
        self._range_bar = RangeBar()
        self._range_bar.setFixedHeight(65)
        self._layout.addWidget(self._range_bar)

        # Key metrics grid
        self._metric_labels: dict[str, tuple[QLabel, QLabel]] = {}
        grid1 = QGridLayout()
        grid1.setSpacing(12)
        metrics1 = [
            "Market Cap", "P/E Ratio", "EPS", "Dividend Yield",
            "Volume", "Avg Volume", "Open", "Prev Close",
            "Day High", "Day Low", "Revenue Growth", "Profit Margin",
            "Next Earnings", "", "", "",
        ]
        for i, name in enumerate(metrics1):
            if not name:
                continue
            row, col = divmod(i, 4)
            grid1.addWidget(_make_metric_card(name, self._metric_labels), row, col)
        self._layout.addLayout(grid1)

        # Valuation & Financial Health section
        val_header = QLabel("Valuation & Financial Health")
        val_header.setObjectName("sectionHeader")
        self._layout.addWidget(val_header)

        grid2 = QGridLayout()
        grid2.setSpacing(12)
        metrics2 = [
            "P/B Ratio", "PEG Ratio", "Price/Sales", "EV/EBITDA",
            "Debt/Equity", "Current Ratio", "Beta", "Free Cash Flow",
            "Book Value", "", "", "",
        ]
        for i, name in enumerate(metrics2):
            if not name:
                continue
            row, col = divmod(i, 4)
            grid2.addWidget(_make_metric_card(name, self._metric_labels), row, col)
        self._layout.addLayout(grid2)
        self._layout.addStretch()

    def update_quote(self, q: data.StockQuote):
        """Populate metrics from a StockQuote."""
        self._ticker_label.setText(q.ticker)
        self._name_label.setText(q.name)

        if q.error:
            self._price_label.setText("Error")
            self._change_label.setText(q.error)
            self._change_label.setStyleSheet(f"color: {RED}; font-size: 14px;")
            return

        self._price_label.setText(f"${q.price:,.2f}")
        sign = "+" if q.change >= 0 else ""
        color = GREEN if q.change >= 0 else RED
        self._change_label.setText(
            f"{sign}{q.change:.2f} ({sign}{q.change_pct:.2f}%)")
        self._change_label.setStyleSheet(
            f"color: {color}; font-size: 16px; font-weight: bold;")

        if q.sector or q.industry:
            self._sector_label.setText(f"{q.sector}  ·  {q.industry}")
        else:
            self._sector_label.setText("")

        # 52-week range bar
        if q.high_52w and q.low_52w and q.price:
            self._range_bar.set_values(q.low_52w, q.high_52w, q.price)

        def _set(name, val):
            if name in self._metric_labels:
                self._metric_labels[name][1].setText(str(val))

        _set("Market Cap", data.format_large_number(q.market_cap))
        _set("P/E Ratio", f"{q.pe_ratio:.2f}" if q.pe_ratio else "N/A")
        _set("EPS", f"${q.eps:.2f}" if q.eps else "N/A")
        _set("Dividend Yield",
             f"{q.dividend_yield * 100:.2f}%" if q.dividend_yield else "N/A")
        _set("Volume", data.format_large_number(q.volume))
        _set("Avg Volume", data.format_large_number(q.avg_volume))
        _set("Open", f"${q.open_price:,.2f}" if q.open_price else "N/A")
        _set("Prev Close", f"${q.prev_close:,.2f}" if q.prev_close else "N/A")
        _set("Day High", f"${q.day_high:,.2f}" if q.day_high else "N/A")
        _set("Day Low", f"${q.day_low:,.2f}" if q.day_low else "N/A")
        _set("Revenue Growth",
             f"{q.revenue_growth * 100:.1f}%" if q.revenue_growth else "N/A")
        _set("Profit Margin",
             f"{q.profit_margin * 100:.1f}%" if q.profit_margin else "N/A")
        _set("Next Earnings", q.next_earnings if q.next_earnings else "N/A")

        # Valuation metrics
        _set("P/B Ratio", f"{q.pb_ratio:.2f}" if q.pb_ratio else "N/A")
        _set("PEG Ratio", f"{q.peg_ratio:.2f}" if q.peg_ratio else "N/A")
        _set("Price/Sales",
             f"{q.price_to_sales:.2f}" if q.price_to_sales else "N/A")
        _set("EV/EBITDA",
             f"{q.ev_to_ebitda:.2f}" if q.ev_to_ebitda else "N/A")
        _set("Debt/Equity",
             f"{q.debt_to_equity:.1f}" if q.debt_to_equity is not None else "N/A")
        _set("Current Ratio",
             f"{q.current_ratio:.2f}" if q.current_ratio else "N/A")
        _set("Beta", f"{q.beta:.2f}" if q.beta else "N/A")
        _set("Free Cash Flow", data.format_large_number(q.free_cash_flow))
        _set("Book Value",
             f"${q.book_value:.2f}" if q.book_value else "N/A")


# ---------------------------------------------------------------------------
# Analyst panel
# ---------------------------------------------------------------------------

class AnalystPanel(QWidget):
    """Displays analyst ratings, price targets, and recommendation history."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[AnalystFetchWorker] = None
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(8, 8, 8, 8)
        scroll.setWidget(inner)
        outer.addWidget(scroll)

        # Consensus
        hdr = QLabel("Analyst Consensus")
        hdr.setObjectName("sectionHeader")
        layout.addWidget(hdr)

        consensus_row = QHBoxLayout()
        self._rec_label = QLabel("—")
        self._rec_label.setStyleSheet(
            f"font-size: 24px; font-weight: bold; color: {ACCENT};")
        consensus_row.addWidget(self._rec_label)
        self._analysts_label = QLabel("")
        self._analysts_label.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 12px;")
        consensus_row.addWidget(self._analysts_label)
        consensus_row.addStretch()
        layout.addLayout(consensus_row)

        # Price Target range bar
        target_hdr = QLabel("Price Target Range")
        target_hdr.setObjectName("sectionHeader")
        layout.addWidget(target_hdr)

        self._target_bar = RangeBar()
        self._target_bar.setFixedHeight(65)
        layout.addWidget(self._target_bar)

        # Target detail cards
        target_grid = QGridLayout()
        target_grid.setSpacing(12)
        self._target_labels: dict[str, QLabel] = {}
        for i, name in enumerate(
                ["Target Low", "Target Mean", "Target Median", "Target High"]):
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
            target_grid.addWidget(frame, 0, i)
            self._target_labels[name] = val
        layout.addLayout(target_grid)

        # Recent recommendations table
        rec_hdr = QLabel("Recent Rating Changes")
        rec_hdr.setObjectName("sectionHeader")
        layout.addWidget(rec_hdr)

        self._rec_table = QTableWidget()
        self._rec_table.setAlternatingRowColors(True)
        self._rec_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._rec_table.verticalHeader().setVisible(False)
        self._rec_table.setMaximumHeight(300)
        layout.addWidget(self._rec_table)

        self._status = QLabel("Select a stock to see analyst data.")
        self._status.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        layout.addWidget(self._status)
        layout.addStretch()

    def load_analyst(self, ticker: str):
        self._status.setText(f"Loading analyst data for {ticker}...")
        self._worker = AnalystFetchWorker(ticker, self)
        self._worker.finished.connect(self._on_data)
        self._worker.start()

    @pyqtSlot(object)
    def _on_data(self, ad: data.AnalystData):
        if ad.error:
            self._status.setText(f"Error: {ad.error}")
            return

        # Consensus
        rec_text = ad.recommendation.upper().replace("_", " ") if ad.recommendation else "N/A"
        rec_colors = {"BUY": GREEN, "STRONG BUY": GREEN, "HOLD": ACCENT,
                      "SELL": RED, "STRONG SELL": RED}
        color = rec_colors.get(rec_text, TEXT)
        self._rec_label.setText(rec_text)
        self._rec_label.setStyleSheet(
            f"font-size: 24px; font-weight: bold; color: {color};")
        self._analysts_label.setText(
            f"Based on {ad.num_analysts} analyst(s)" if ad.num_analysts else "")

        # Price target range bar
        if ad.target_low and ad.target_high and ad.current_price:
            self._target_bar.set_values(
                ad.target_low, ad.target_high, ad.current_price)

        for name, val in [
            ("Target Low", ad.target_low), ("Target Mean", ad.target_mean),
            ("Target Median", ad.target_median), ("Target High", ad.target_high),
        ]:
            self._target_labels[name].setText(
                f"${val:,.2f}" if val else "N/A")

        # Recommendations table
        if ad.recommendations is not None and not ad.recommendations.empty:
            df = ad.recommendations
            self._rec_table.setRowCount(len(df))
            self._rec_table.setColumnCount(len(df.columns))
            self._rec_table.setHorizontalHeaderLabels(
                [str(c) for c in df.columns])
            for r in range(len(df)):
                for c in range(len(df.columns)):
                    self._rec_table.setItem(
                        r, c, QTableWidgetItem(str(df.iloc[r, c])))
            self._rec_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.Stretch)
        else:
            self._rec_table.setRowCount(0)
            self._rec_table.setColumnCount(0)

        self._status.setText(f"Analyst data for {ad.ticker}")


# ---------------------------------------------------------------------------
# News panel
# ---------------------------------------------------------------------------

class NewsPanel(QWidget):
    """Shows recent news headlines for a stock."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[NewsFetchWorker] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        header = QLabel("News Headlines")
        header.setObjectName("sectionHeader")
        layout.addWidget(header)

        self._list = QListWidget()
        self._list.setWordWrap(True)
        self._list.itemDoubleClicked.connect(self._open_link)
        layout.addWidget(self._list)

        self._status = QLabel("Select a stock to see news.")
        self._status.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        layout.addWidget(self._status)

    def load_news(self, ticker: str):
        self._list.clear()
        self._status.setText(f"Loading news for {ticker}...")
        self._worker = NewsFetchWorker(ticker, self)
        self._worker.finished.connect(self._on_news)
        self._worker.start()

    @pyqtSlot(str, list)
    def _on_news(self, ticker: str, articles: list):
        self._list.clear()
        if not articles:
            self._status.setText(f"No news found for {ticker}.")
            return
        for art in articles:
            title = art.get("title", "")
            pub = art.get("publisher", "")
            link = art.get("link", "")
            text = f"{title}\n  — {pub}" if pub else title
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, link)
            item.setToolTip(link)
            self._list.addItem(item)
        self._status.setText(
            f"{len(articles)} headline(s) for {ticker}. Double-click to open.")

    def _open_link(self, item: QListWidgetItem):
        url = item.data(Qt.UserRole)
        if url:
            webbrowser.open(url)


# ---------------------------------------------------------------------------
# Portfolio panel
# ---------------------------------------------------------------------------

class PortfolioPanel(QWidget):
    """Portfolio tracker showing positions, values, and P&L."""

    stock_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._positions = storage.load_portfolio()
        self._workers: list[QThread] = []
        self._quotes: dict[str, data.StockQuote] = {}
        self._setup_ui()
        if self._positions:
            self._refresh_prices()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Summary header
        summary_frame = QFrame()
        summary_frame.setStyleSheet(
            f"background-color: {CARD_BG}; border-radius: 6px; padding: 12px;")
        summary_layout = QHBoxLayout(summary_frame)

        self._total_value_label = QLabel("Total Value: —")
        self._total_value_label.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {TEXT};")
        summary_layout.addWidget(self._total_value_label)

        self._total_pl_label = QLabel("Total P&L: —")
        self._total_pl_label.setStyleSheet(
            f"font-size: 16px; font-weight: bold;")
        summary_layout.addWidget(self._total_pl_label)
        summary_layout.addStretch()
        layout.addWidget(summary_frame)

        # Input row for adding positions
        input_row = QHBoxLayout()
        self._ticker_input = QLineEdit()
        self._ticker_input.setPlaceholderText("Ticker")
        self._ticker_input.setMaximumWidth(100)
        input_row.addWidget(self._ticker_input)

        self._shares_input = QLineEdit()
        self._shares_input.setPlaceholderText("Shares")
        self._shares_input.setMaximumWidth(100)
        input_row.addWidget(self._shares_input)

        self._cost_input = QLineEdit()
        self._cost_input.setPlaceholderText("Avg Cost ($)")
        self._cost_input.setMaximumWidth(120)
        input_row.addWidget(self._cost_input)

        add_btn = QPushButton("Add Position")
        add_btn.setObjectName("addBtn")
        add_btn.clicked.connect(self._add_position)
        input_row.addWidget(add_btn)

        remove_btn = QPushButton("Remove")
        remove_btn.setObjectName("removeBtn")
        remove_btn.clicked.connect(self._remove_position)
        input_row.addWidget(remove_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_prices)
        input_row.addWidget(refresh_btn)

        input_row.addStretch()
        layout.addLayout(input_row)

        # Portfolio table
        cols = ["Ticker", "Shares", "Cost Basis", "Current Price",
                "Market Value", "Gain/Loss ($)", "Gain/Loss (%)", "Allocation %"]
        self._table = QTableWidget(0, len(cols))
        self._table.setHorizontalHeaderLabels(cols)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSortingEnabled(True)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.itemSelectionChanged.connect(self._on_selection)
        layout.addWidget(self._table)

        self._status = QLabel("")
        self._status.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        layout.addWidget(self._status)

    def _add_position(self):
        ticker = self._ticker_input.text().strip().upper()
        try:
            shares = float(self._shares_input.text().strip())
            cost = float(self._cost_input.text().strip())
        except ValueError:
            self._status.setText("Enter valid numbers for shares and cost.")
            return
        if not ticker or shares <= 0 or cost <= 0:
            self._status.setText("Ticker, shares, and cost must be positive.")
            return

        self._positions = storage.add_position(
            ticker, shares, cost, self._positions)
        self._ticker_input.clear()
        self._shares_input.clear()
        self._cost_input.clear()
        self._status.setText(f"Added {shares} shares of {ticker} at ${cost:.2f}")
        self._refresh_prices()

    def _remove_position(self):
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            self._status.setText("Select a position to remove.")
            return
        ticker = self._table.item(rows[0].row(), 0).text()
        self._positions = storage.remove_position(ticker, self._positions)
        self._quotes.pop(ticker, None)
        self._status.setText(f"Removed {ticker} from portfolio.")
        self._rebuild_table()

    def _refresh_prices(self):
        tickers = [p["ticker"] for p in self._positions]
        if not tickers:
            self._table.setRowCount(0)
            self._update_summary()
            return
        self._status.setText("Refreshing prices...")
        worker = MultiFetchWorker(tickers, self)
        worker.quote_ready.connect(self._on_quote)
        worker.finished.connect(self._on_refresh_done)
        self._workers.append(worker)
        worker.start()

    @pyqtSlot(object)
    def _on_quote(self, q: data.StockQuote):
        if not q.error:
            self._quotes[q.ticker] = q

    @pyqtSlot()
    def _on_refresh_done(self):
        self._rebuild_table()
        self._status.setText(
            f"Portfolio updated at {datetime.now().strftime('%H:%M:%S')}")

    def _rebuild_table(self):
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)

        total_value = sum(
            p["shares"] * self._quotes[p["ticker"]].price
            for p in self._positions if p["ticker"] in self._quotes)

        for i, pos in enumerate(self._positions):
            ticker = pos["ticker"]
            shares = pos["shares"]
            cost = pos["cost_basis"]
            q = self._quotes.get(ticker)
            if not q:
                continue

            current = q.price
            market_val = shares * current
            cost_val = shares * cost
            gain = market_val - cost_val
            gain_pct = (gain / cost_val * 100) if cost_val > 0 else 0
            alloc = (market_val / total_value * 100) if total_value > 0 else 0

            self._table.insertRow(i)

            def _item(text, value=0.0):
                it = QTableWidgetItem(text)
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it.setData(Qt.UserRole, value)
                return it

            ticker_item = QTableWidgetItem(ticker)
            ticker_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self._table.setItem(i, 0, ticker_item)
            self._table.setItem(i, 1, _item(f"{shares:,.2f}", shares))
            self._table.setItem(i, 2, _item(f"${cost:,.2f}", cost))
            self._table.setItem(i, 3, _item(f"${current:,.2f}", current))
            self._table.setItem(i, 4, _item(f"${market_val:,.2f}", market_val))

            sign = "+" if gain >= 0 else ""
            gain_item = _item(f"{sign}${gain:,.2f}", gain)
            gain_item.setForeground(QColor(GREEN if gain >= 0 else RED))
            self._table.setItem(i, 5, gain_item)

            pct_item = _item(f"{sign}{gain_pct:.2f}%", gain_pct)
            pct_item.setForeground(QColor(GREEN if gain_pct >= 0 else RED))
            self._table.setItem(i, 6, pct_item)

            self._table.setItem(i, 7, _item(f"{alloc:.1f}%", alloc))

        self._table.setSortingEnabled(True)
        self._update_summary()

    def _update_summary(self):
        total_value = 0.0
        total_cost = 0.0
        for pos in self._positions:
            q = self._quotes.get(pos["ticker"])
            if q:
                total_value += pos["shares"] * q.price
                total_cost += pos["shares"] * pos["cost_basis"]

        self._total_value_label.setText(
            f"Total Value: ${total_value:,.2f}")
        total_pl = total_value - total_cost
        total_pl_pct = (total_pl / total_cost * 100) if total_cost > 0 else 0
        sign = "+" if total_pl >= 0 else ""
        color = GREEN if total_pl >= 0 else RED
        self._total_pl_label.setText(
            f"Total P&L: {sign}${total_pl:,.2f} ({sign}{total_pl_pct:.2f}%)")
        self._total_pl_label.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {color};")

    def _on_selection(self):
        rows = self._table.selectionModel().selectedRows()
        if rows:
            ticker_item = self._table.item(rows[0].row(), 0)
            if ticker_item:
                self.stock_selected.emit(ticker_item.text())


# ---------------------------------------------------------------------------
# Watchlist table
# ---------------------------------------------------------------------------

class WatchlistTable(QTableWidget):
    """Sortable table showing all stocks in the current watchlist."""

    stock_selected = pyqtSignal(str)

    COLUMNS = ["Ticker", "Name", "Price", "Change", "Change %",
                "Volume", "Mkt Cap", "P/E"]

    def __init__(self, parent=None):
        super().__init__(0, len(self.COLUMNS), parent)
        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSortingEnabled(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.verticalHeader().setVisible(False)
        self.itemSelectionChanged.connect(self._on_selection)
        self._quotes: dict[str, data.StockQuote] = {}

    def _on_selection(self):
        rows = self.selectionModel().selectedRows()
        if rows:
            ticker_item = self.item(rows[0].row(), 0)
            if ticker_item:
                self.stock_selected.emit(ticker_item.text())

    def upsert_quote(self, q: data.StockQuote):
        """Insert or update a row for the given quote."""
        self._quotes[q.ticker] = q
        row = None
        for r in range(self.rowCount()):
            if self.item(r, 0) and self.item(r, 0).text() == q.ticker:
                row = r
                break
        if row is None:
            row = self.rowCount()
            self.insertRow(row)

        def _item(text, align=Qt.AlignLeft):
            it = QTableWidgetItem(text)
            it.setTextAlignment(align | Qt.AlignVCenter)
            return it

        def _num_item(text, value=0.0):
            it = QTableWidgetItem(text)
            it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it.setData(Qt.UserRole, value)
            return it

        self.setItem(row, 0, _item(q.ticker))
        self.setItem(row, 1, _item(q.name))
        self.setItem(row, 2, _num_item(f"${q.price:,.2f}", q.price))

        change_item = _num_item(f"{q.change:+.2f}", q.change)
        change_item.setForeground(QColor(GREEN if q.change >= 0 else RED))
        self.setItem(row, 3, change_item)

        pct_item = _num_item(f"{q.change_pct:+.2f}%", q.change_pct)
        pct_item.setForeground(QColor(GREEN if q.change_pct >= 0 else RED))
        self.setItem(row, 4, pct_item)

        self.setItem(row, 5, _num_item(
            data.format_large_number(q.volume), q.volume))
        self.setItem(row, 6, _num_item(
            data.format_large_number(q.market_cap), q.market_cap))
        pe_text = f"{q.pe_ratio:.2f}" if q.pe_ratio else "N/A"
        self.setItem(row, 7, _num_item(pe_text, q.pe_ratio or 0))

    def remove_ticker(self, ticker: str):
        for r in range(self.rowCount()):
            if self.item(r, 0) and self.item(r, 0).text() == ticker:
                self.removeRow(r)
                self._quotes.pop(ticker, None)
                return

    def get_quotes(self) -> list[data.StockQuote]:
        return list(self._quotes.values())


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stock Analyzer")
        self.resize(1400, 900)

        self._watchlists = storage.load_watchlists()
        self._current_wl = list(self._watchlists.keys())[0]
        self._workers: list[QThread] = []

        # Auto-refresh timer
        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.timeout.connect(self._refresh_all)

        self._setup_ui()
        self._load_watchlist()

    # --- UI construction ---

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Left panel — watchlist controls + table
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Watchlist selector row
        wl_row = QHBoxLayout()
        wl_row.addWidget(QLabel("Watchlist:"))
        self._wl_combo = QComboBox()
        self._wl_combo.addItems(self._watchlists.keys())
        self._wl_combo.setCurrentText(self._current_wl)
        self._wl_combo.currentTextChanged.connect(self._on_wl_changed)
        wl_row.addWidget(self._wl_combo, 1)

        new_wl_btn = QPushButton("New")
        new_wl_btn.clicked.connect(self._new_watchlist)
        wl_row.addWidget(new_wl_btn)

        del_wl_btn = QPushButton("Delete")
        del_wl_btn.setObjectName("removeBtn")
        del_wl_btn.clicked.connect(self._delete_watchlist)
        wl_row.addWidget(del_wl_btn)
        left_layout.addLayout(wl_row)

        # Ticker input row
        input_row = QHBoxLayout()
        self._ticker_input = QLineEdit()
        self._ticker_input.setPlaceholderText("Enter ticker symbol (e.g. AAPL)")
        self._ticker_input.returnPressed.connect(self._add_ticker)
        input_row.addWidget(self._ticker_input, 1)

        add_btn = QPushButton("Add")
        add_btn.setObjectName("addBtn")
        add_btn.clicked.connect(self._add_ticker)
        input_row.addWidget(add_btn)

        remove_btn = QPushButton("Remove")
        remove_btn.setObjectName("removeBtn")
        remove_btn.clicked.connect(self._remove_ticker)
        input_row.addWidget(remove_btn)

        refresh_btn = QPushButton("Refresh All")
        refresh_btn.clicked.connect(self._refresh_all)
        input_row.addWidget(refresh_btn)

        # Auto-refresh dropdown
        input_row.addWidget(QLabel("Auto:"))
        self._auto_combo = QComboBox()
        self._auto_combo.addItems(["Off", "1 min", "5 min", "15 min"])
        self._auto_combo.currentTextChanged.connect(self._on_auto_refresh_changed)
        self._auto_combo.setMaximumWidth(90)
        input_row.addWidget(self._auto_combo)

        left_layout.addLayout(input_row)

        # Watchlist table
        self._table = WatchlistTable()
        self._table.stock_selected.connect(self._on_stock_selected)
        left_layout.addWidget(self._table)

        # Progress bar (hidden by default)
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        left_layout.addWidget(self._progress)

        # Export button
        export_row = QHBoxLayout()
        export_row.addStretch()
        export_btn = QPushButton("Export to CSV")
        export_btn.clicked.connect(self._export_csv)
        export_row.addWidget(export_btn)
        left_layout.addLayout(export_row)

        # Right panel — tabs
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()

        self._chart = ChartWidget()
        self._tabs.addTab(self._chart, "Chart")

        self._metrics = MetricsPanel()
        self._tabs.addTab(self._metrics, "Metrics")

        self._analyst = AnalystPanel()
        self._tabs.addTab(self._analyst, "Analyst")

        self._compare = CompareWidget()
        self._tabs.addTab(self._compare, "Compare")

        self._news = NewsPanel()
        self._tabs.addTab(self._news, "News")

        self._portfolio = PortfolioPanel()
        self._portfolio.stock_selected.connect(self._on_stock_selected)
        self._tabs.addTab(self._portfolio, "Portfolio")

        right_layout.addWidget(self._tabs)

        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([450, 950])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter)

        # Status bar
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("Ready — add a ticker to get started.")

    # --- Auto-refresh ---

    def _on_auto_refresh_changed(self, text: str):
        interval_map = {"Off": 0, "1 min": 60_000,
                        "5 min": 300_000, "15 min": 900_000}
        interval = interval_map.get(text, 0)
        if interval > 0:
            self._auto_refresh_timer.start(interval)
            self._statusbar.showMessage(f"Auto-refresh every {text}.")
        else:
            self._auto_refresh_timer.stop()
            self._statusbar.showMessage("Auto-refresh disabled.")

    # --- Watchlist management ---

    def _on_wl_changed(self, name: str):
        self._current_wl = name
        self._load_watchlist()

    def _load_watchlist(self):
        self._table.setRowCount(0)
        tickers = self._watchlists.get(self._current_wl, [])
        if tickers:
            self._fetch_multiple(tickers)
        else:
            self._statusbar.showMessage(
                "Watchlist is empty. Add a ticker symbol above.")

    def _new_watchlist(self):
        name, ok = QInputDialog.getText(self, "New Watchlist", "Watchlist name:")
        if ok and name.strip():
            name = name.strip()
            self._watchlists = storage.create_watchlist(name, self._watchlists)
            self._wl_combo.addItem(name)
            self._wl_combo.setCurrentText(name)

    def _delete_watchlist(self):
        if len(self._watchlists) <= 1:
            QMessageBox.information(
                self, "Cannot Delete",
                "You must keep at least one watchlist.")
            return
        reply = QMessageBox.question(
            self, "Delete Watchlist",
            f"Delete '{self._current_wl}' and all its tickers?",
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._watchlists = storage.delete_watchlist(
                self._current_wl, self._watchlists)
            self._wl_combo.clear()
            self._wl_combo.addItems(self._watchlists.keys())
            self._wl_combo.setCurrentIndex(0)

    # --- Ticker add / remove ---

    def _add_ticker(self):
        ticker = self._ticker_input.text().strip().upper()
        if not ticker:
            return
        self._ticker_input.clear()
        if ticker in self._watchlists.get(self._current_wl, []):
            self._statusbar.showMessage(f"{ticker} is already in the watchlist.")
            return
        self._statusbar.showMessage(f"Adding {ticker}...")
        self._watchlists = storage.add_ticker(
            self._current_wl, ticker, self._watchlists)
        worker = QuoteFetchWorker(ticker, self)
        worker.finished.connect(self._on_single_quote)
        self._workers.append(worker)
        worker.start()

    def _remove_ticker(self):
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            self._statusbar.showMessage("Select a stock to remove.")
            return
        ticker = self._table.item(rows[0].row(), 0).text()
        self._watchlists = storage.remove_ticker(
            self._current_wl, ticker, self._watchlists)
        self._table.remove_ticker(ticker)
        self._statusbar.showMessage(f"Removed {ticker}.")

    # --- Data fetching ---

    def _fetch_multiple(self, tickers: list[str]):
        self._progress.setVisible(True)
        self._progress.setMaximum(len(tickers))
        self._progress.setValue(0)
        self._statusbar.showMessage(f"Loading {len(tickers)} stocks...")
        worker = MultiFetchWorker(tickers, self)
        worker.quote_ready.connect(self._on_multi_quote)
        worker.progress.connect(self._on_progress)
        worker.finished.connect(self._on_multi_done)
        self._workers.append(worker)
        worker.start()

    @pyqtSlot(object)
    def _on_single_quote(self, q: data.StockQuote):
        if q.error:
            self._statusbar.showMessage(f"Error: {q.error}")
            self._watchlists = storage.remove_ticker(
                self._current_wl, q.ticker, self._watchlists)
            QMessageBox.warning(self, "Invalid Ticker", q.error)
            return
        self._table.upsert_quote(q)
        self._statusbar.showMessage(f"Added {q.ticker} — {q.name}")

    @pyqtSlot(object)
    def _on_multi_quote(self, q: data.StockQuote):
        if not q.error:
            self._table.upsert_quote(q)

    @pyqtSlot(int, int)
    def _on_progress(self, current: int, total: int):
        self._progress.setValue(current)

    @pyqtSlot()
    def _on_multi_done(self):
        self._progress.setVisible(False)
        ts = datetime.now().strftime("%H:%M:%S")
        auto = self._auto_combo.currentText()
        suffix = f" · next in {auto}" if auto != "Off" else ""
        self._statusbar.showMessage(f"Watchlist loaded at {ts}{suffix}")

    def _refresh_all(self):
        tickers = self._watchlists.get(self._current_wl, [])
        if tickers:
            self._fetch_multiple(tickers)
        else:
            self._statusbar.showMessage("Nothing to refresh.")

    # --- Stock selection ---

    def _on_stock_selected(self, ticker: str):
        self._statusbar.showMessage(f"Loading details for {ticker}...")
        self._chart.load_ticker(ticker)
        self._news.load_news(ticker)
        self._analyst.load_analyst(ticker)

        worker = QuoteFetchWorker(ticker, self)
        worker.finished.connect(self._on_detail_quote)
        self._workers.append(worker)
        worker.start()

    @pyqtSlot(object)
    def _on_detail_quote(self, q: data.StockQuote):
        self._metrics.update_quote(q)
        self._statusbar.showMessage(
            f"Showing {q.ticker}" + (f" — {q.name}" if q.name else ""))

    # --- CSV Export ---

    def _export_csv(self):
        quotes = self._table.get_quotes()
        if not quotes:
            self._statusbar.showMessage("No data to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", f"{self._current_wl}.csv", "CSV Files (*.csv)")
        if path:
            try:
                storage.export_to_csv(self._current_wl, path, quotes)
                self._statusbar.showMessage(f"Exported to {path}")
            except OSError as e:
                QMessageBox.warning(self, "Export Failed", str(e))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Stock Analyzer")
    app.setStyle("Fusion")
    app.setStyleSheet(_stylesheet())

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
