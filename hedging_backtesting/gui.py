"""
CHF Hedging Backtester — Dark-themed Finance GUI

Launch with: python gui.py
"""

import threading
import tkinter as tk
from tkinter import ttk

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from hedging_backtest_msci_chf import (
    run_backtest, compute_metrics, plot_cumulative_returns,
    plot_rolling_volatility, START_DATE, END_DATE, ETF_TICKERS,
)
from cache import clear_cache

# =============================================================================
# Color palette (Catppuccin Mocha-inspired dark finance theme)
# =============================================================================
C = {
    "bg": "#1e1e2e",
    "surface": "#313244",
    "surface2": "#45475a",
    "overlay": "#585b70",
    "text": "#cdd6f4",
    "subtext": "#a6adc8",
    "accent": "#89b4fa",
    "green": "#a6e3a1",
    "red": "#f38ba8",
    "yellow": "#f9e2af",
    "teal": "#94e2d5",
}

MPL_DARK = {
    "figure.facecolor": C["bg"],
    "axes.facecolor": C["surface"],
    "axes.edgecolor": C["overlay"],
    "axes.labelcolor": C["subtext"],
    "text.color": C["text"],
    "xtick.color": C["subtext"],
    "ytick.color": C["subtext"],
    "grid.color": C["surface2"],
    "legend.facecolor": C["surface"],
    "legend.edgecolor": C["overlay"],
}


def apply_dark_style(style):
    """Configure ttk dark theme."""
    style.theme_use("clam")

    style.configure(".", background=C["bg"], foreground=C["text"],
                    fieldbackground=C["surface"], borderwidth=0,
                    font=("Segoe UI", 10))
    style.configure("TFrame", background=C["bg"])
    style.configure("TLabel", background=C["bg"], foreground=C["text"])
    style.configure("TEntry", fieldbackground=C["surface"], foreground=C["text"],
                    insertcolor=C["text"])
    style.configure("TCheckbutton", background=C["bg"], foreground=C["text"])
    style.map("TCheckbutton",
              background=[("active", C["surface"])],
              foreground=[("active", C["accent"])])
    style.configure("TNotebook", background=C["bg"], borderwidth=0)
    style.configure("TNotebook.Tab", background=C["surface"], foreground=C["subtext"],
                    padding=[14, 6])
    style.map("TNotebook.Tab",
              background=[("selected", C["bg"])],
              foreground=[("selected", C["accent"])])

    # Accent button
    style.configure("Accent.TButton", background=C["accent"], foreground=C["bg"],
                    font=("Segoe UI", 11, "bold"), padding=[20, 10])
    style.map("Accent.TButton",
              background=[("active", C["teal"]), ("disabled", C["overlay"])],
              foreground=[("disabled", C["subtext"])])

    # Secondary button
    style.configure("Secondary.TButton", background=C["surface"], foreground=C["text"],
                    padding=[12, 6])
    style.map("Secondary.TButton", background=[("active", C["surface2"])])

    # Treeview
    style.configure("Treeview", background=C["surface"], foreground=C["text"],
                    fieldbackground=C["surface"], rowheight=28,
                    font=("Consolas", 10))
    style.configure("Treeview.Heading", background=C["surface2"], foreground=C["accent"],
                    font=("Segoe UI", 10, "bold"))
    style.map("Treeview", background=[("selected", C["surface2"])],
              foreground=[("selected", C["accent"])])

    # Progress bar
    style.configure("TProgressbar", background=C["accent"], troughcolor=C["surface"],
                    thickness=6)

    # Horizontal separator
    style.configure("TSeparator", background=C["surface2"])


class BacktesterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CHF Hedging Backtester")
        self.root.configure(bg=C["bg"])
        self.root.geometry("1280x860")
        self.root.minsize(900, 600)

        self.style = ttk.Style()
        apply_dark_style(self.style)
        plt.rcParams.update(MPL_DARK)

        self.results = None
        self._build_ui()

    # -----------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------
    def _build_ui(self):
        # Header
        header = ttk.Frame(self.root)
        header.pack(fill="x", padx=20, pady=(16, 0))
        ttk.Label(header, text="CHF Hedging Backtester",
                  font=("Segoe UI", 18, "bold"), foreground=C["accent"]).pack(side="left")
        ttk.Label(header, text="MSCI Index Funds",
                  font=("Segoe UI", 12), foreground=C["subtext"]).pack(side="left", padx=(12, 0))

        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=20, pady=10)

        # Control panel
        ctrl = ttk.Frame(self.root)
        ctrl.pack(fill="x", padx=20, pady=(0, 8))

        # Row 1: dates + indices
        row1 = ttk.Frame(ctrl)
        row1.pack(fill="x")

        ttk.Label(row1, text="Start Date", foreground=C["subtext"]).pack(side="left")
        self.start_var = tk.StringVar(value=START_DATE)
        e1 = ttk.Entry(row1, textvariable=self.start_var, width=13)
        e1.pack(side="left", padx=(6, 20))

        ttk.Label(row1, text="End Date", foreground=C["subtext"]).pack(side="left")
        self.end_var = tk.StringVar(value=END_DATE)
        e2 = ttk.Entry(row1, textvariable=self.end_var, width=13)
        e2.pack(side="left", padx=(6, 30))

        # Index checkboxes
        self.index_vars = {}
        for name in ETF_TICKERS:
            var = tk.BooleanVar(value=True)
            self.index_vars[name] = var
            ttk.Checkbutton(row1, text=name, variable=var).pack(side="left", padx=(0, 12))

        # Row 2: buttons + progress
        row2 = ttk.Frame(ctrl)
        row2.pack(fill="x", pady=(10, 0))

        self.run_btn = ttk.Button(row2, text="Run Backtest", style="Accent.TButton",
                                  command=self._on_run)
        self.run_btn.pack(side="left")

        ttk.Button(row2, text="Clear Cache", style="Secondary.TButton",
                   command=self._on_clear_cache).pack(side="left", padx=(10, 0))

        ttk.Button(row2, text="Export CSV", style="Secondary.TButton",
                   command=self._on_export).pack(side="left", padx=(10, 0))

        self.progress = ttk.Progressbar(row2, mode="indeterminate", length=200)
        self.progress.pack(side="left", padx=(20, 0))

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(row2, textvariable=self.status_var, foreground=C["subtext"],
                  font=("Segoe UI", 9)).pack(side="left", padx=(12, 0))

        # Tabbed content area
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=(4, 16))

        # Tab 1: cumulative returns chart
        self.cum_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.cum_frame, text="  Cumulative Returns  ")
        self.cum_fig = Figure(figsize=(12, 7), dpi=100)
        self.cum_canvas = FigureCanvasTkAgg(self.cum_fig, self.cum_frame)
        self.cum_canvas.get_tk_widget().pack(fill="both", expand=True)
        self._add_toolbar(self.cum_canvas, self.cum_frame)

        # Tab 2: rolling volatility chart
        self.vol_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.vol_frame, text="  Rolling Volatility  ")
        self.vol_fig = Figure(figsize=(12, 7), dpi=100)
        self.vol_canvas = FigureCanvasTkAgg(self.vol_fig, self.vol_frame)
        self.vol_canvas.get_tk_widget().pack(fill="both", expand=True)
        self._add_toolbar(self.vol_canvas, self.vol_frame)

        # Tab 3: summary table
        self.table_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.table_frame, text="  Summary Table  ")
        self._build_table()

        # Log tab
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text="  Log  ")
        self.log_text = tk.Text(self.log_frame, bg=C["surface"], fg=C["text"],
                                font=("Consolas", 10), bd=0, insertbackground=C["text"],
                                state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)

    def _add_toolbar(self, canvas, parent):
        """Add matplotlib navigation toolbar styled for dark theme."""
        tb_frame = ttk.Frame(parent)
        tb_frame.pack(fill="x")
        toolbar = NavigationToolbar2Tk(canvas, tb_frame)
        toolbar.config(background=C["bg"])
        for child in toolbar.winfo_children():
            try:
                child.config(background=C["bg"], foreground=C["text"])
            except tk.TclError:
                pass
        toolbar.update()

    def _build_table(self):
        cols = ("Index", "Strategy", "Ann. Return", "Ann. Vol", "Sharpe",
                "Max Drawdown", "Total Return", "Months")
        self.tree = ttk.Treeview(self.table_frame, columns=cols, show="headings", height=20)
        for col in cols:
            w = 130 if col in ("Index", "Strategy") else 100
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center" if col not in ("Index", "Strategy") else "w")
        self.tree.pack(fill="both", expand=True, padx=4, pady=4)

    # -----------------------------------------------------------------
    # Logging
    # -----------------------------------------------------------------
    def _log(self, msg):
        """Thread-safe log to both status bar and log tab."""
        def _update():
            self.status_var.set(msg)
            self.log_text.configure(state="normal")
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.root.after(0, _update)

    # -----------------------------------------------------------------
    # Actions
    # -----------------------------------------------------------------
    def _on_run(self):
        self.run_btn.configure(state="disabled")
        self.progress.start(12)
        self._log("Starting backtest...")
        threading.Thread(target=self._run_backtest, daemon=True).start()

    def _run_backtest(self):
        try:
            results = run_backtest(
                start_date=self.start_var.get().strip(),
                end_date=self.end_var.get().strip(),
                log=self._log,
            )
            # Filter to selected indices
            if results:
                selected = {name for name, var in self.index_vars.items() if var.get()}
                results = {k: v for k, v in results.items() if k in selected}

            self.root.after(0, lambda: self._display_results(results))
        except Exception as e:
            self._log(f"ERROR: {e}")
            self.root.after(0, lambda: self._finish())

    def _display_results(self, results):
        self.results = results
        if not results:
            self._log("No results to display.")
            self._finish()
            return

        # Charts (must be on main thread for matplotlib)
        self._log("Rendering charts...")
        plot_cumulative_returns(results, fig=self.cum_fig, save_path=None)
        self.cum_canvas.draw()

        plot_rolling_volatility(results, fig=self.vol_fig, save_path=None)
        self.vol_canvas.draw()

        # Summary table
        for row in self.tree.get_children():
            self.tree.delete(row)
        for index_name, df in results.items():
            for col in df.columns:
                m = compute_metrics(df[col])
                self.tree.insert("", "end", values=(
                    index_name, col,
                    f"{m['Ann. Return']:.1%}", f"{m['Ann. Vol']:.1%}",
                    f"{m['Sharpe']:.2f}", f"{m['Max Drawdown']:.1%}",
                    f"{m['Total Return']:.1%}", m['Months'],
                ))

        first = next(iter(results.values()))
        period = f"{first.index[0].strftime('%Y-%m')} to {first.index[-1].strftime('%Y-%m')}"
        self._log(f"Done — {len(results)} indices, {period}")
        self.notebook.select(0)
        self._finish()

    def _finish(self):
        self.progress.stop()
        self.run_btn.configure(state="normal")

    def _on_clear_cache(self):
        clear_cache()
        self._log("Cache cleared.")

    def _on_export(self):
        if not self.results:
            self._log("No results to export. Run backtest first.")
            return
        import os
        os.makedirs("work", exist_ok=True)
        for index_name, df in self.results.items():
            safe_name = index_name.replace(" ", "_").lower()
            path = f"work/hedging_{safe_name}_monthly_returns.csv"
            df.to_csv(path)
            self._log(f"Saved: {path}")

        plot_cumulative_returns(self.results, save_path="work/hedging_cumulative_returns.png")
        plot_rolling_volatility(self.results, save_path="work/hedging_rolling_volatility.png")
        self._log("Export complete.")


def main():
    root = tk.Tk()
    BacktesterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
