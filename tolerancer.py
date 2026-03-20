import sys
import os
import io
from collections import defaultdict
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTabWidget, QFileDialog, QTableWidget, QTableWidgetItem,
    QLabel, QSplitter, QSpinBox, QComboBox, QHeaderView, QSizePolicy, QToolBar,
    QStatusBar, QAbstractItemView, QMessageBox
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor, QPalette, QBrush, QFont

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib as mpl
import numpy as np

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image as RLImage, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── register fonts ────────────────────────────────────────────────────────────
_FONT_PATHS = {
    'Carlito':            '/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf',
    'Carlito-Bold':       '/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf',
    'Carlito-Italic':     '/usr/share/fonts/truetype/crosextra/Carlito-Italic.ttf',
    'Carlito-BoldItalic': '/usr/share/fonts/truetype/crosextra/Carlito-BoldItalic.ttf',
    'LibMono':            '/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf',
    'LibMono-Bold':       '/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf',
}
for name, path in _FONT_PATHS.items():
    if os.path.exists(path):
        pdfmetrics.registerFont(TTFont(name, path))

# ── light palette ─────────────────────────────────────────────────────────────
C_BG        = "#f5f7fa"   # page/window background
C_SURFACE   = "#ffffff"   # widget surface
C_BORDER    = "#d0d7de"
C_TEXT      = "#1f2328"
C_TEXT_DIM  = "#57606a"
C_ACCENT    = "#0969da"   # blue
C_ACCENT2   = "#1a7f37"   # green
C_WARN      = "#9a6700"   # amber
C_ERR       = "#d1242f"
C_SEL       = "#dbeafe"   # light blue selection
C_ALT_ROW   = "#f0f4f8"   # alternate row
C_HDR_BG    = "#eaf0f8"   # table header background

TYPE_COLORS = {
    "TFRN": "#2563eb", "TIND": "#16a34a", "TABB": "#d97706",
    "TTHI": "#dc2626", "TSTY": "#7c3aed", "TSTX": "#db2777",
    "TRAD": "#0891b2", "TCUR": "#059669", "TCON": "#ca8a04",
    "TSDI": "#9333ea", "TSDX": "#e11d48", "TSDY": "#0284c7",
    "TEDX": "#f59e0b", "TEDY": "#10b981", "TETX": "#f43f5e",
    "TETY": "#a855f7", "TETZ": "#6366f1",
}
DEFAULT_COLOR = "#94a3b8"

# chart background / text colours (light)
CHART_BG    = "#f8fafc"
CHART_GRID  = "#e2e8f0"
CHART_TEXT  = "#1e293b"
CHART_DIM   = "#64748b"

OPERAND_CODES = {
    'ISOA','ISOB','ISOC','ISOD','TRAD','TCUR','TFRN','TTHI','TCON','TSDI',
    'TSDR','TSDX','TSDY','TSTX','TSTY','TIRX','TIRY','TIRR','TEXI','TEZI',
    'TPAI','TPAR','TIND','TABB','TCMU','TCIO','TCEO','TEDR','TEDX','TEDY',
    'TETX','TETY','TETZ','TARR','TARX','TARY','TRLR','TRLX','TRLY','TUDX',
    'TUDY','TUTX','TUTY','TUTZ','TNPS','TNPA','TMCO','CEDV','CMCO','COMM',
    'COMP','CPAR','SAVE','SEED','STAT','TWAV'
}

OPERAND_DESC = {
    'ISOA':'P-V Power','ISOB':'P-V Irregularity','ISOC':'P-V RSI','ISOD':'RMS Irregularity',
    'TRAD':'Radius (LU)','TCUR':'Curvature','TFRN':'Radius (fringes)',
    'TTHI':'Thickness/Position','TCON':'Conic Constant','TSDI':'Semi-Diameter',
    'TSDR':'Radial Decenter','TSDX':'X-Decenter (surf)','TSDY':'Y-Decenter (surf)',
    'TSTX':'Tilt X (surf, °)','TSTY':'Tilt Y (surf, °)',
    'TIRX':'Tilt X (surf, LU)','TIRY':'Tilt Y (surf, LU)','TIRR':'Irregularity',
    'TEXI':'Zernike Fringe Irreg','TEZI':'Zernike Std Irreg',
    'TPAI':'Param Inverse','TPAR':'Parameter','TIND':'Index of Refraction',
    'TABB':'Abbe Number','TCMU':'Coating Multiplier','TCIO':'Coating Index Offset',
    'TCEO':'Coating Extinction Offset','TEDR':'Element Radial Decenter',
    'TEDX':'Element X-Decenter','TEDY':'Element Y-Decenter',
    'TETX':'Element Tilt X (°)','TETY':'Element Tilt Y (°)','TETZ':'Element Tilt Z (°)',
    'TARR':'Radial Roll Angle','TARX':'Roll Angle X','TARY':'Roll Angle Y',
    'TRLR':'Radial Roll (TIR)','TRLX':'Roll X (TIR)','TRLY':'Roll Y (TIR)',
    'TUDX':'User X-Decenter','TUDY':'User Y-Decenter',
    'TUTX':'User Tilt X','TUTY':'User Tilt Y','TUTZ':'User Tilt Z',
    'TNPS':'NSC Position','TNPA':'NSC Parameter',
    'TMCO':'Multi-Config Value','CEDV':'Extra Data (depr.)','CMCO':'Multi-Config Comp.',
    'COMM':'Comment','COMP':'Compensator','CPAR':'Param Compensator',
    'SAVE':'Save File','SEED':'Random Seed','STAT':'MC Statistics','TWAV':'Test Wavelength',
}

TYPE_GROUPS = {
    "TFRN":     ["TFRN"],
    "TIND":     ["TIND"],
    "TABB":     ["TABB"],
    "TTHI":     ["TTHI"],
    "TSTY":     ["TSTY"],
    "TSTX":     ["TSTX"],
    "TRAD":     ["TRAD"],
    "TCON":     ["TCON"],
    "Decenter": ["TSDX","TSDY","TSDR","TEDX","TEDY","TEDR","TUDX","TUDY"],
    "ElemTilt": ["TETX","TETY","TETZ"],
    "Roll":     ["TARR","TARX","TARY","TRLR","TRLX","TRLY"],
    "UserDef":  ["TUTX","TUTY","TUTZ"],
    "SurfMisc": ["TSDI","TIRX","TIRY","TIRR","TEXI","TEZI","TPAI","TPAR"],
    "Coating":  ["TCMU","TCIO","TCEO"],
    "ISO":      ["ISOA","ISOB","ISOC","ISOD"],
    "NSC/MC":   ["TNPS","TNPA","TMCO","CMCO"],
}

GROUP_TOOLTIP = {
    "TFRN":"Surface Radius in Fringes","TIND":"Index of Refraction",
    "TABB":"Abbe Number","TTHI":"Thickness / Position",
    "TSTY":"Surface Tilt Y (deg)","TSTX":"Surface Tilt X (deg)",
    "TRAD":"Surface Radius (LU)","TCON":"Conic Constant",
    "Decenter":"All Decenter Operands","ElemTilt":"Element Tilts (TETX/Y/Z)",
    "Roll":"Roll / TIR Operands","UserDef":"User-Defined Tilts",
    "SurfMisc":"Surface Misc (semi-diam, irreg, Zernike…)",
    "Coating":"Coating Operands","ISO":"ISO Surface Operands","NSC/MC":"NSC / Multi-Config",
}


# ── parser ────────────────────────────────────────────────────────────────────

def parse_file(path):
    with open(path, 'rb') as f:
        raw = f.read()
    try:
        text = raw.decode('utf-16')
    except Exception:
        text = raw.decode('utf-8', errors='replace')

    lines = text.splitlines()
    info = {"criterion": "", "nominal": None, "operands": []}

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("Criterion"):
            info["criterion"] = stripped.split(":", 1)[-1].strip()
        elif stripped.startswith("Nominal Criterion"):
            try:
                val = stripped.split(":", 1)[-1].strip().replace(",", ".")
                info["nominal"] = float(val)
            except Exception:
                pass

        parts = line.split("\t")
        parts = [p.strip() for p in parts]
        # OPERAND | surface | '' | min_val | min_crit | min_change | max_val | max_crit | max_change
        if len(parts) >= 9 and parts[0] in OPERAND_CODES:
            operand = parts[0]
            surface = parts[1]
            try:
                min_val    = float(parts[3].replace(",", ".").replace("E", "e"))
                min_change = float(parts[5].replace(",", ".").replace("E", "e"))
                max_val    = float(parts[6].replace(",", ".").replace("E", "e"))
                max_change = float(parts[8].replace(",", ".").replace("E", "e"))
                contribution = abs(min_change) + abs(max_change)
                info["operands"].append({
                    "operand": operand, "surface": surface,
                    "min_val": min_val, "max_val": max_val,
                    "min_change": min_change, "max_change": max_change,
                    "contribution": contribution,
                    "label": f"{operand} s{surface}",
                })
            except Exception:
                pass

    return info


# ── chart canvas ──────────────────────────────────────────────────────────────

def _style_ax_light(ax, fig):
    fig.patch.set_facecolor(CHART_BG)
    ax.set_facecolor(CHART_BG)
    ax.tick_params(colors=CHART_DIM, labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor(CHART_GRID)
    ax.grid(axis='x', color=CHART_GRID, linewidth=0.6, alpha=0.9)


class ChartCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(facecolor=CHART_BG)  # no global tight_layout; set per plot
        super().__init__(self.fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def plot_bar(self, labels, values, chart_colors, title, xlabel="Contribution"):
        self.fig.clf()
        ax = self.fig.add_subplot(111)
        _style_ax_light(ax, self.fig)
        if not labels:
            ax.text(0.5, 0.5, "No data", ha='center', va='center',
                    color=CHART_DIM, fontsize=12)
            self.draw(); return

        n = len(labels)
        y_pos = np.arange(n)
        # Bar height as fraction of slot — keep generous gap between bars
        bar_h = 0.55
        ax.barh(y_pos, values, color=chart_colors, height=bar_h,
                edgecolor='white', linewidth=0.5)
        max_v = max(values) if values else 1
        # Labels: always inside bars, dark background text for readability
        # Use a contrasting box behind the value text
        for i, val in enumerate(values):
            frac = val / max_v if max_v else 0
            label_str = f"{val:.3e}"
            if frac > 0.25:
                # inside bar — white bold text, large enough to read when printed
                ax.text(val * 0.97, i, label_str,
                        va='center', ha='right', color='white', fontsize=8,
                        fontfamily='monospace', fontweight='bold')
            else:
                # outside short bar — dark text with slight offset
                ax.text(val + max_v * 0.005, i, label_str,
                        va='center', ha='left', color=CHART_TEXT, fontsize=8,
                        fontfamily='monospace', fontweight='bold')
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, color=CHART_TEXT, fontsize=9)
        ax.set_xlabel(xlabel, color=CHART_DIM, fontsize=9)
        ax.set_title(title, color=CHART_TEXT, fontsize=11, pad=10, fontweight='bold')
        ax.xaxis.label.set_color(CHART_DIM)
        ax.set_xlim(0, max_v * 1.05)
        # Expand y-axis so bars have breathing room
        ax.set_ylim(-0.7, n - 0.3)
        ax.invert_yaxis()
        try:
            self.fig.tight_layout()
        except Exception:
            pass
        self.draw()

    def plot_pie(self, labels, values, pie_colors, title):
        self.fig.clf()
        self.fig.patch.set_facecolor(CHART_BG)
        # Use constrained_layout=False and manual subplot rect to keep pie circular
        ax = self.fig.add_axes([0.0, 0.05, 0.62, 0.88])  # left portion for pie
        ax.set_facecolor(CHART_BG)
        if not labels:
            ax.text(0.5, 0.5, "No data", ha='center', va='center', color=CHART_DIM)
            self.draw(); return
        wedges, _, autotexts = ax.pie(
            values, labels=None, colors=pie_colors,
            autopct=lambda p: f'{p:.1f}%' if p > 3 else '',
            startangle=140, pctdistance=0.75,
            wedgeprops=dict(width=0.52, edgecolor='white', linewidth=1.5)
        )
        for t in autotexts:
            t.set_color('white'); t.set_fontsize(10); t.set_fontweight('bold')
        ax.set_aspect('equal')
        ax.set_title(title, color=CHART_TEXT, fontsize=10, fontweight='bold', pad=8)
        ax.legend(wedges, labels, loc='center left',
                  bbox_to_anchor=(1.08, 0.5), bbox_transform=ax.transAxes,
                  frameon=False, labelcolor=CHART_TEXT, fontsize=8)
        self.draw()

    def to_rl_image(self, width_mm, height_mm, dpi=150, tight=True):
        """Render to ReportLab Image.
        tight=True: use bbox_inches='tight' (good for bars, may resize).
        tight=False: honour exact figure dimensions (required for pie).
        """
        w_in = width_mm / 25.4
        h_in = height_mm / 25.4
        orig_size = self.fig.get_size_inches()
        self.fig.set_size_inches(w_in, h_in)
        buf = io.BytesIO()
        if tight:
            self.fig.savefig(buf, format='png', dpi=dpi,
                             facecolor=CHART_BG, bbox_inches='tight',
                             pad_inches=0.1)
        else:
            self.fig.savefig(buf, format='png', dpi=dpi,
                             facecolor=CHART_BG)
        self.fig.set_size_inches(orig_size)
        buf.seek(0)
        return RLImage(buf, width=width_mm * mm, height=height_mm * mm, kind='direct')


def render_pie_image(labels, values, pie_colors, title, side_mm=130, dpi=150):
    """Render a circular pie/donut chart to RLImage using Agg (no Qt needed).
    side_mm: both width and height — always square so pie is never elliptical.
    """
    from matplotlib.figure import Figure as _Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg as _Agg
    side_in = side_mm / 25.4
    fig = _Figure(figsize=(side_in, side_in), facecolor=CHART_BG)
    _Agg(fig)
    # Pie axes in left 60% of figure, legend in right 40%
    ax = fig.add_axes([0.0, 0.05, 0.60, 0.90])
    ax.set_facecolor(CHART_BG)
    if not labels:
        ax.text(0.5, 0.5, 'No data', ha='center', va='center', color=CHART_DIM)
    else:
        wedges, _, autotexts = ax.pie(
            values, labels=None, colors=pie_colors,
            autopct=lambda p: f'{p:.1f}%' if p > 3 else '',
            startangle=140, pctdistance=0.75,
            wedgeprops=dict(width=0.52, edgecolor='white', linewidth=1.5)
        )
        for t in autotexts:
            t.set_color('white'); t.set_fontsize(11); t.set_fontweight('bold')
        ax.set_aspect('equal')
        ax.set_title(title, color=CHART_TEXT, fontsize=10, fontweight='bold', pad=8)
        ax.legend(wedges, labels, loc='center left',
                  bbox_to_anchor=(1.05, 0.5), bbox_transform=ax.transAxes,
                  frameon=False, labelcolor=CHART_TEXT, fontsize=8)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, facecolor=CHART_BG)
    buf.seek(0)
    return RLImage(buf, width=side_mm * mm, height=side_mm * mm, kind='direct')


def render_bar_slices(labels, values, chart_colors, title,
                      width_mm, max_page_h_mm, bars_per_slice=None,
                      xlabel="Contribution", dpi=150):
    """Split a bar chart into page-height slices.  Returns list of RLImage."""
    from matplotlib.figure import Figure as _Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg as _Agg
    n = len(labels)
    if n == 0:
        return []

    # How many bars fit on one page at 9 mm each (with some margin for axes)?
    # axes overhead ~ 20mm (title + x-axis + padding)
    AXIS_OVERHEAD_MM = 20  # title + x-axis + padding
    bar_h_mm = 9   # physical height per bar on paper
    if bars_per_slice is None:
        bars_per_slice = max(1, int((max_page_h_mm - AXIS_OVERHEAD_MM) / bar_h_mm))

    images = []
    for start in range(0, n, bars_per_slice):
        end = min(start + bars_per_slice, n)
        sl_labels = labels[start:end]
        sl_values = values[start:end]
        sl_colors = chart_colors[start:end]
        sl_n = end - start

        h_mm = sl_n * bar_h_mm + AXIS_OVERHEAD_MM
        w_in = width_mm / 25.4
        h_in = h_mm / 25.4

        fig = _Figure(figsize=(w_in, h_in), facecolor=CHART_BG)
        _Agg(fig)
        ax = fig.add_subplot(111)
        ax.set_facecolor(CHART_BG)
        ax.tick_params(colors=CHART_DIM, labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor(CHART_GRID)
        ax.grid(axis='x', color=CHART_GRID, linewidth=0.6, alpha=0.9)

        y_pos = np.arange(sl_n)
        ax.barh(y_pos, sl_values, color=sl_colors, height=0.55,
                edgecolor='white', linewidth=0.5)
        max_v = max(values)  # global max — consistent scale across slices
        for i, val in enumerate(sl_values):
            frac = val / max_v if max_v else 0
            label_str = f"{val:.3e}"
            if frac > 0.25:
                ax.text(val * 0.97, i, label_str, va='center', ha='right',
                        color='white', fontsize=8, fontfamily='monospace',
                        fontweight='bold')
            else:
                ax.text(val + max_v * 0.005, i, label_str, va='center', ha='left',
                        color=CHART_TEXT, fontsize=8, fontfamily='monospace',
                        fontweight='bold')
        ax.set_yticks(y_pos)
        ax.set_yticklabels(sl_labels, color=CHART_TEXT, fontsize=9)
        ax.set_xlabel(xlabel, color=CHART_DIM, fontsize=9)
        if start == 0:
            ax.set_title(title, color=CHART_TEXT, fontsize=11, pad=8, fontweight='bold')
        else:
            ax.set_title(f"{title}  (cont.)", color=CHART_DIM, fontsize=9, pad=5)
        ax.set_xlim(0, max_v * 1.05)
        ax.set_ylim(-0.6, sl_n - 0.4)
        ax.invert_yaxis()

        # Fixed inch margins — large enough for labels regardless of chart height
        fig.subplots_adjust(
            left   = 0.90 / w_in,          # ~22mm: fits longest y-tick label
            right  = 1.0 - 0.05 / w_in,    # 1.3mm right pad
            top    = 1.0 - 0.38 / h_in,    # ~9.7mm: title + pad
            bottom = 0.30 / h_in,           # ~7.6mm: x-label + ticks
        )
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=dpi, facecolor=CHART_BG)
        buf.seek(0)
        images.append(RLImage(buf, width=width_mm * mm, height=h_mm * mm, kind='direct'))

    return images


# ── table helpers ─────────────────────────────────────────────────────────────

def make_table(headers):
    t = QTableWidget()
    t.setColumnCount(len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.verticalHeader().setVisible(False)
    t.verticalHeader().setDefaultSectionSize(22)
    t.setAlternatingRowColors(True)
    t.setSortingEnabled(True)
    t.setShowGrid(True)
    t.setStyleSheet(f"""
        QTableWidget {{
            background-color: {C_SURFACE}; color: {C_TEXT};
            gridline-color: {C_BORDER}; border: 1px solid {C_BORDER};
            font-size: 12px; font-family: 'Consolas','Courier New',monospace;
        }}
        QTableWidget::item:selected {{
            background-color: {C_SEL}; color: {C_TEXT};
        }}
        QTableWidget::item:alternate {{ background-color: {C_ALT_ROW}; }}
        QHeaderView::section {{
            background-color: {C_HDR_BG}; color: {C_ACCENT};
            border: 1px solid {C_BORDER}; padding: 4px 6px;
            font-size: 11px; font-weight: bold;
        }}
    """)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    t.horizontalHeader().setStretchLastSection(True)
    return t


def _fmt_float(val):
    """Format a float without unnecessary scientific notation.
    Percentages/scores (0.01–9999): plain decimal.
    Small contributions/changes/wavelengths: scientific.
    """
    if val != val:  # NaN
        return "—"
    abs_v = abs(val)
    if abs_v == 0.0:
        return "0"
    if abs_v >= 0.01 and abs_v < 10000:
        if abs_v >= 100:
            return f"{val:.2f}"
        elif abs_v >= 10:
            return f"{val:.3f}"
        else:
            return f"{val:.4f}"
    return f"{val:.4e}"


def fill_table(table, rows, highlight_top=3):
    table.setSortingEnabled(False)
    table.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            item = QTableWidgetItem()
            if isinstance(val, float):
                item.setData(Qt.DisplayRole, val)
                item.setText(_fmt_float(val))
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
            else:
                item.setText(str(val))
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            if r < highlight_top and c == len(row) - 1:
                item.setForeground(QBrush(QColor(C_WARN)))
            table.setItem(r, c, item)
    table.setSortingEnabled(True)


# ── Qt stylesheet ─────────────────────────────────────────────────────────────

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {C_BG}; color: {C_TEXT};
    font-family: 'Segoe UI','Arial',sans-serif; font-size: 13px;
}}
QTabWidget::pane {{
    border: 1px solid {C_BORDER}; background: {C_SURFACE};
}}
QTabBar::tab {{
    background: {C_BG}; color: {C_TEXT_DIM};
    border: 1px solid {C_BORDER}; border-bottom: none;
    padding: 5px 12px; font-size: 11px; min-width: 0px;
}}
QTabBar::tab:selected {{
    background: {C_SURFACE}; color: {C_ACCENT};
    border-bottom: 2px solid {C_ACCENT}; font-weight: bold;
}}
QTabBar::tab:hover {{ color: {C_TEXT}; background: {C_ALT_ROW}; }}
QPushButton {{
    background-color: {C_SURFACE}; color: {C_ACCENT};
    border: 1px solid {C_BORDER}; border-radius: 5px;
    padding: 5px 14px; font-size: 12px; font-weight: 500;
}}
QPushButton:hover {{
    background-color: {C_SEL}; border-color: {C_ACCENT};
}}
QPushButton:pressed {{ background-color: #bfdbfe; }}
QSpinBox {{
    background: {C_SURFACE}; color: {C_TEXT};
    border: 1px solid {C_BORDER}; padding: 2px 6px; border-radius: 3px;
}}
QLabel {{ color: {C_TEXT}; }}
QSplitter::handle {{ background: {C_BORDER}; width: 1px; height: 1px; }}
QStatusBar {{
    background: {C_SURFACE}; color: {C_TEXT_DIM};
    border-top: 1px solid {C_BORDER};
}}
QScrollBar:vertical {{ background: {C_BG}; width: 8px; border: none; }}
QScrollBar::handle:vertical {{
    background: {C_BORDER}; border-radius: 4px; min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QToolBar {{
    background: {C_SURFACE}; border-bottom: 1px solid {C_BORDER};
    spacing: 4px; padding: 3px 8px;
}}
"""


# ── PDF builder ───────────────────────────────────────────────────────────────

PDF_WHITE   = colors.white
PDF_BG      = colors.HexColor("#f8fafc")
PDF_SURF    = colors.white
PDF_HDR     = colors.HexColor("#e8f0fb")   # light blue header
PDF_HDR2    = colors.HexColor("#f0fdf4")   # light green header
PDF_ACCENT  = colors.HexColor("#1d4ed8")
PDF_ACCENT2 = colors.HexColor("#15803d")
PDF_WARN    = colors.HexColor("#92400e")
PDF_TEXT    = colors.HexColor("#1e293b")
PDF_DIM     = colors.HexColor("#64748b")
PDF_GRID    = colors.HexColor("#e2e8f0")
PDF_ALT     = colors.HexColor("#f1f5f9")
PDF_RANK1   = colors.HexColor("#fef3c7")   # amber tint for top rows
PDF_RANK2   = colors.HexColor("#fff7ed")
PDF_RANK3   = colors.HexColor("#fefce8")
PDF_BORDER  = colors.HexColor("#cbd5e1")

FONT_BODY   = 'Carlito'
FONT_BOLD   = 'Carlito-Bold'
FONT_ITALIC = 'Carlito-Italic'
FONT_MONO   = 'LibMono'
FONT_MONO_B = 'LibMono-Bold'

# Fallback to Helvetica if Carlito not registered
try:
    pdfmetrics.getFont(FONT_BODY)
except Exception:
    FONT_BODY = 'Helvetica'
    FONT_BOLD = 'Helvetica-Bold'
    FONT_ITALIC = 'Helvetica-Oblique'
try:
    pdfmetrics.getFont(FONT_MONO)
except Exception:
    FONT_MONO = 'Courier'
    FONT_MONO_B = 'Courier-Bold'


def _pdf_styles():
    base = getSampleStyleSheet()
    return {
        'title': ParagraphStyle('ZTitle',
            fontName=FONT_BOLD, fontSize=20, leading=24,
            textColor=PDF_ACCENT, spaceAfter=2),
        'subtitle': ParagraphStyle('ZSub',
            fontName=FONT_ITALIC, fontSize=10, leading=13,
            textColor=PDF_DIM, spaceAfter=8),
        'h1': ParagraphStyle('ZH1',
            fontName=FONT_BOLD, fontSize=12, leading=15,
            textColor=PDF_ACCENT, spaceBefore=10, spaceAfter=4),
        'h2': ParagraphStyle('ZH2',
            fontName=FONT_BOLD, fontSize=10, leading=13,
            textColor=PDF_ACCENT2, spaceBefore=6, spaceAfter=3),
        'meta': ParagraphStyle('ZMeta',
            fontName=FONT_BODY, fontSize=9, leading=12,
            textColor=PDF_TEXT, spaceAfter=2),
        'small': ParagraphStyle('ZSmall',
            fontName=FONT_BODY, fontSize=7.5, leading=10,
            textColor=PDF_DIM),
    }


def _rank_color(i):
    if i == 0: return PDF_RANK1
    if i == 1: return PDF_RANK2
    if i == 2: return PDF_RANK3
    return None


def _tbl_style_all(n_data_rows, highlight_top=3):
    cmds = [
        # Header
        ('BACKGROUND',    (0,0), (-1, 0),  PDF_HDR),
        ('TEXTCOLOR',     (0,0), (-1, 0),  PDF_ACCENT),
        ('FONTNAME',      (0,0), (-1, 0),  FONT_BOLD),
        ('FONTSIZE',      (0,0), (-1, 0),  8),
        ('ALIGN',         (0,0), (-1, 0),  'CENTER'),
        ('VALIGN',        (0,0), (-1,-1),  'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1, 0),  5),
        ('TOPPADDING',    (0,0), (-1, 0),  5),
        # Body
        ('FONTNAME',      (0,1), (-1,-1),  FONT_BODY),
        ('FONTSIZE',      (0,1), (-1,-1),  7.5),
        ('TEXTCOLOR',     (0,1), (-1,-1),  PDF_TEXT),
        ('ALIGN',         (0,1), (-1,-1),  'RIGHT'),
        ('ALIGN',         (0,1), ( 0,-1),  'CENTER'),  # rank
        ('ALIGN',         (1,1), ( 3,-1),  'LEFT'),    # operand, surf, desc
        ('ROWBACKGROUNDS',(0,1), (-1,-1),  [PDF_SURF, PDF_ALT]),
        ('LINEBELOW',     (0,0), (-1, 0),  0.8, PDF_ACCENT),
        ('GRID',          (0,0), (-1,-1),  0.3, PDF_GRID),
        ('BOTTOMPADDING', (0,1), (-1,-1),  3),
        ('TOPPADDING',    (0,1), (-1,-1),  3),
        ('LEFTPADDING',   (0,0), (-1,-1),  4),
        ('RIGHTPADDING',  (0,0), (-1,-1),  4),
    ]
    # Top-N row highlights + bold contribution
    for i in range(min(highlight_top, n_data_rows)):
        rc = _rank_color(i)
        if rc:
            cmds.append(('BACKGROUND', (0, i+1), (-1, i+1), rc))
        cmds.append(('FONTNAME', (-1, i+1), (-1, i+1), FONT_BOLD))
        cmds.append(('TEXTCOLOR', (-1, i+1), (-1, i+1), PDF_ACCENT))
    return TableStyle(cmds)


def _tbl_style_group(n_data_rows, highlight_top=3):
    cmds = [
        ('BACKGROUND',    (0,0), (-1, 0),  PDF_HDR2),
        ('TEXTCOLOR',     (0,0), (-1, 0),  PDF_ACCENT2),
        ('FONTNAME',      (0,0), (-1, 0),  FONT_BOLD),
        ('FONTSIZE',      (0,0), (-1, 0),  8),
        ('ALIGN',         (0,0), (-1, 0),  'CENTER'),
        ('VALIGN',        (0,0), (-1,-1),  'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1, 0),  5),
        ('TOPPADDING',    (0,0), (-1, 0),  5),
        ('FONTNAME',      (0,1), (-1,-1),  FONT_BODY),
        ('FONTSIZE',      (0,1), (-1,-1),  7.5),
        ('TEXTCOLOR',     (0,1), (-1,-1),  PDF_TEXT),
        ('ALIGN',         (0,1), (-1,-1),  'RIGHT'),
        ('ALIGN',         (0,1), ( 2,-1),  'LEFT'),
        ('ROWBACKGROUNDS',(0,1), (-1,-1),  [PDF_SURF, PDF_ALT]),
        ('LINEBELOW',     (0,0), (-1, 0),  0.8, PDF_ACCENT2),
        ('GRID',          (0,0), (-1,-1),  0.3, PDF_GRID),
        ('BOTTOMPADDING', (0,1), (-1,-1),  3),
        ('TOPPADDING',    (0,1), (-1,-1),  3),
        ('LEFTPADDING',   (0,0), (-1,-1),  4),
        ('RIGHTPADDING',  (0,0), (-1,-1),  4),
    ]
    for i in range(min(highlight_top, n_data_rows)):
        rc = _rank_color(i)
        if rc:
            cmds.append(('BACKGROUND', (0, i+1), (-1, i+1), rc))
        cmds.append(('FONTNAME', (-1, i+1), (-1, i+1), FONT_BOLD))
        cmds.append(('TEXTCOLOR', (-1, i+1), (-1, i+1), PDF_ACCENT2))
    return TableStyle(cmds)


def _tbl_style_summary(n_data_rows):
    cmds = [
        ('BACKGROUND',    (0,0), (-1, 0),  PDF_HDR),
        ('TEXTCOLOR',     (0,0), (-1, 0),  PDF_ACCENT),
        ('FONTNAME',      (0,0), (-1, 0),  FONT_BOLD),
        ('FONTSIZE',      (0,0), (-1, 0),  8),
        ('ALIGN',         (0,0), (-1, 0),  'CENTER'),
        ('VALIGN',        (0,0), (-1,-1),  'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1, 0),  5),
        ('TOPPADDING',    (0,0), (-1, 0),  5),
        ('FONTNAME',      (0,1), (-1,-1),  FONT_BODY),
        ('FONTSIZE',      (0,1), (-1,-1),  8),
        ('TEXTCOLOR',     (0,1), (-1,-1),  PDF_TEXT),
        ('ALIGN',         (0,1), (-1,-1),  'RIGHT'),
        ('ALIGN',         (0,1), ( 1,-1),  'LEFT'),
        ('ROWBACKGROUNDS',(0,1), (-1,-1),  [PDF_SURF, PDF_ALT]),
        ('LINEBELOW',     (0,0), (-1, 0),  0.8, PDF_ACCENT),
        ('GRID',          (0,0), (-1,-1),  0.3, PDF_GRID),
        ('BOTTOMPADDING', (0,1), (-1,-1),  3),
        ('TOPPADDING',    (0,1), (-1,-1),  3),
        ('LEFTPADDING',   (0,0), (-1,-1),  4),
        ('RIGHTPADDING',  (0,0), (-1,-1),  4),
    ]
    for i in range(min(3, n_data_rows)):
        rc = _rank_color(i)
        if rc:
            cmds.append(('BACKGROUND', (0, i+1), (-1, i+1), rc))
        cmds.append(('FONTNAME', (0, i+1), (0, i+1), FONT_BOLD))
        cmds.append(('TEXTCOLOR', (-1, i+1), (-1, i+1), PDF_ACCENT))
    return TableStyle(cmds)


def build_pdf(path, data, filename, all_chart, summary_chart, group_charts):
    sty = _pdf_styles()
    PW, PH = landscape(A4)
    USABLE_W = 262*mm  # from actual frame: 750.5pt/72*25.4=264.8mm minus 2mm margin

    def bg_page(canvas, doc):
        canvas.setFillColor(PDF_BG)
        canvas.rect(0, 0, PW, PH, fill=1, stroke=0)
        # thin header stripe
        canvas.setFillColor(PDF_ACCENT)
        canvas.rect(0, PH - 8*mm, PW, 8*mm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont(FONT_BOLD, 8)
        canvas.drawString(14*mm, PH - 5.5*mm, f"Zemax Tolerance Report  ·  {filename}")
        canvas.setFont(FONT_BODY, 7.5)
        canvas.drawRightString(PW - 14*mm, PH - 5.5*mm,
            datetime.now().strftime("%Y-%m-%d"))
        # page number at bottom
        canvas.setFillColor(PDF_DIM)
        canvas.setFont(FONT_BODY, 7)
        canvas.drawCentredString(PW/2, 5*mm, f"Page {doc.page}")

    doc = SimpleDocTemplate(
        path, pagesize=landscape(A4),
        leftMargin=14*mm, rightMargin=14*mm,
        topMargin=14*mm, bottomMargin=10*mm,
        title=f"Tolerance Analysis — {filename}",
    )
    story = []

    # ── Title block ──────────────────────────────────────────────────────────
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph("Sensitivity Analysis Report", sty['title']))
    nom = f"{data['nominal']:.8f}" if data['nominal'] is not None else "N/A"
    story.append(Paragraph(
        f"Criterion: <b>{data['criterion']}</b>   ·   "
        f"Nominal: <b>{nom}</b>   ·   "
        f"Operands: <b>{len(data['operands'])}</b>   ·   "
        f"File: {filename}", sty['meta']))
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=PDF_BORDER, spaceAfter=6))

    # ── All operands table ────────────────────────────────────────────────────
    story.append(Paragraph("All Operands — Ranked by Contribution", sty['h1']))

    ops_sorted = sorted(data["operands"], key=lambda x: -x["contribution"])
    hdr = ["#", "Operand", "Surf", "Description",
           "Min Val", "Max Val", "Min Δ", "Max Δ", "Contribution"]
    rows = [hdr]
    for i, op in enumerate(ops_sorted):
        rows.append([
            str(i+1), op["operand"], op["surface"],
            OPERAND_DESC.get(op["operand"], ""),
            f"{op['min_val']:.4e}", f"{op['max_val']:.4e}",
            f"{op['min_change']:+.4e}", f"{op['max_change']:+.4e}",
            f"{op['contribution']:.4e}",
        ])
    # #(7) Op(14) Surf(10) Desc(38) MinVal(26) MaxVal(26) MinΔ(28) MaxΔ(28) Contrib; fills to USABLE_W
    _cw_fixed = [7*mm, 14*mm, 10*mm, 38*mm, 26*mm, 26*mm, 28*mm, 28*mm, 28*mm]
    cw = _cw_fixed[:]
    cw[-1] += max(0, USABLE_W - sum(_cw_fixed))
    tbl = Table(rows, colWidths=cw, repeatRows=1)
    tbl.setStyle(_tbl_style_all(len(rows)-1))
    story.append(tbl)

    if all_chart is not None:
        story.append(PageBreak())
        n_bars = len(ops_sorted)
        labels_all  = [f"{op['operand']} s{op['surface']}" for op in ops_sorted]
        values_all  = [op['contribution'] for op in ops_sorted]
        colors_all  = [TYPE_COLORS.get(op['operand'], DEFAULT_COLOR) for op in ops_sorted]
        for img_slice in render_bar_slices(
                labels_all, values_all, colors_all,
                f"Top {n_bars} Contributors",
                USABLE_W / mm, 178):
            story.append(img_slice)

    story.append(PageBreak())

    # ── Summary by type ───────────────────────────────────────────────────────
    story.append(Paragraph("Summary by Operand Type", sty['h1']))

    by_type = defaultdict(list)
    for op in data["operands"]:
        by_type[op["operand"]].append(op["contribution"])
    type_rows = sorted(by_type.items(), key=lambda x: -sum(x[1]))

    shdr = ["Operand", "Description", "Count", "Total Contribution", "Max Single"]
    srows = [shdr]
    for code, c in type_rows:
        srows.append([code, OPERAND_DESC.get(code,""), str(len(c)),
                      f"{sum(c):.4e}", f"{max(c):.4e}"])

    # Summary table - explicit safe column widths, pie below
    # Cols: Operand(16) Desc(62) Count(14) TotalContrib(32) MaxSingle(32)
    scw = [16*mm, 62*mm, 14*mm, 32*mm, 32*mm]
    stbl = Table(srows, colWidths=scw, repeatRows=1)
    stbl.setStyle(_tbl_style_summary(len(srows)-1))
    story.append(stbl)

    story.append(PageBreak())

    # Pie on its own page — guaranteed to fit, no overflow possible
    if summary_chart is not None:
        story.append(Paragraph("Contribution by Operand Type", sty['h1']))
        by_type2 = defaultdict(list)
        for op in data["operands"]:
            by_type2[op["operand"]].append(op["contribution"])
        pie_rows2 = sorted(by_type2.items(), key=lambda x: -sum(x[1]))
        pie_labels2 = [r[0] for r in pie_rows2]
        pie_values2 = [sum(r[1]) for r in pie_rows2]
        pie_colors2 = [TYPE_COLORS.get(l, DEFAULT_COLOR) for l in pie_labels2]
        story.append(render_pie_image(pie_labels2, pie_values2, pie_colors2,
                                      "Share of Total Contribution", side_mm=160))
    story.append(PageBreak())

    # ── Per-group pages ───────────────────────────────────────────────────────
    for group_name, (ops, chart_widget) in group_charts.items():
        if not ops:
            continue

        story.append(Paragraph(f"Operand Group: {group_name}  —  "
                                f"{GROUP_TOOLTIP.get(group_name, '')}", sty['h1']))

        g_ops = sorted(ops, key=lambda x: -x["contribution"])
        ghdr = ["#", "Operand", "Surf", "Min Val", "Max Val",
                "Min Δ", "Max Δ", "Contribution"]
        grows = [ghdr]
        for i, op in enumerate(g_ops):
            grows.append([
                str(i+1), op["operand"], op["surface"],
                f"{op['min_val']:.4e}", f"{op['max_val']:.4e}",
                f"{op['min_change']:+.4e}", f"{op['max_change']:+.4e}",
                f"{op['contribution']:.4e}",
            ])
        # Fixed widths totalling USABLE_W (~269mm landscape)
        # #(8) Op(16) Surf(12) MinVal(32) MaxVal(32) MinΔ(34) MaxΔ(34) Contrib(36) = 204
        # remainder goes to Contrib
        gcw_fixed = [8*mm, 16*mm, 12*mm, 32*mm, 32*mm, 34*mm, 34*mm, 36*mm]
        remainder = USABLE_W - sum(gcw_fixed)
        gcw = gcw_fixed[:]
        gcw[-1] += max(0, remainder)

        gtbl = Table(grows, colWidths=gcw, repeatRows=1)
        gtbl.setStyle(_tbl_style_group(len(grows)-1))

        # Always: full-width table, then chart below — side-by-side destroyed column widths
        story.append(gtbl)

        if chart_widget is not None:
            story.append(PageBreak())
            g_labels = [f"{op['operand']} s{op['surface']}" for op in g_ops]
            g_values = [op['contribution'] for op in g_ops]
            g_colors = [TYPE_COLORS.get(op['operand'], DEFAULT_COLOR) for op in g_ops]
            for img_slice in render_bar_slices(
                    g_labels, g_values, g_colors,
                    f"{group_name} — Contributions",
                    USABLE_W / mm, 178):
                story.append(img_slice)

        story.append(PageBreak())

    doc.build(story, onFirstPage=bg_page, onLaterPages=bg_page)


# ── FileTab ───────────────────────────────────────────────────────────────────

class FileTab(QWidget):
    def __init__(self, data, filename, parent=None):
        super().__init__(parent)
        self.data = data
        self.filename = filename
        self._all_chart     = None
        self._summary_chart = None
        self._group_charts  = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        nom = f"{self.data['nominal']:.6f}" if self.data['nominal'] is not None else "N/A"
        bar = QLabel(
            f"  Criterion: <b style='color:{C_ACCENT}'>{self.data['criterion']}</b>"
            f"   ·   Nominal: <b style='color:{C_ACCENT2}'>{nom}</b>"
            f"   ·   Operands: <b>{len(self.data['operands'])}</b>"
        )
        bar.setTextFormat(Qt.RichText)
        bar.setStyleSheet(
            f"background:{C_SURFACE}; padding:6px 10px;"
            f" border-bottom:1px solid {C_BORDER}; font-size:12px;")
        layout.addWidget(bar)

        self.inner_tabs = QTabWidget()
        self.inner_tabs.setUsesScrollButtons(True)
        self.inner_tabs.setElideMode(Qt.ElideNone)
        self.inner_tabs.tabBar().setExpanding(False)
        self.inner_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {C_BORDER}; background: {C_SURFACE};
            }}
            QTabBar {{
                background: {C_BG};
            }}
            QTabBar::tab {{
                background: {C_BG}; color: {C_TEXT_DIM};
                border: 1px solid {C_BORDER}; border-bottom: none;
                padding: 4px 10px; font-size: 11px; min-width: 0px;
                margin-right: 1px;
            }}
            QTabBar::tab:selected {{
                background: {C_SURFACE}; color: {C_ACCENT};
                border-bottom: 2px solid {C_ACCENT}; font-weight: bold;
            }}
            QTabBar::tab:hover {{ color: {C_TEXT}; background: {C_ALT_ROW}; }}
            QTabBar::scroller {{ width: 20px; }}
        """)
        layout.addWidget(self.inner_tabs)

        self._add_all_tab()
        self._add_summary_tab()
        self._add_group_tabs()

    def _color(self, operand):
        return TYPE_COLORS.get(operand, DEFAULT_COLOR)

    def _add_all_tab(self):
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(4, 4, 4, 4)

        ctl = QHBoxLayout()
        ctl.addWidget(QLabel("Top N:"))
        spin = QSpinBox()
        n_total = len(self.data["operands"])
        spin.setRange(1, max(500, n_total))
        spin.setValue(n_total)
        spin.setFixedWidth(70)
        ctl.addWidget(spin)
        ctl.addStretch()
        vl.addLayout(ctl)

        splitter = QSplitter(Qt.Horizontal)
        tbl = make_table(["#", "Operand", "Surf", "Description",
                          "Min Val", "Max Val", "Min Δ", "Max Δ", "Contribution"])
        splitter.addWidget(tbl)
        chart = ChartCanvas()
        self._all_chart = chart
        splitter.addWidget(chart)
        splitter.setSizes([620, 540])
        vl.addWidget(splitter)

        idx = self.inner_tabs.addTab(w, "All")
        self.inner_tabs.setTabToolTip(idx, "All operands ranked by contribution")

        def refresh():
            n = spin.value()
            ops = sorted(self.data["operands"], key=lambda x: -x["contribution"])[:n]
            rows = [(i+1, op["operand"], op["surface"],
                     OPERAND_DESC.get(op["operand"], ""),
                     op["min_val"], op["max_val"],
                     op["min_change"], op["max_change"], op["contribution"])
                    for i, op in enumerate(ops)]
            fill_table(tbl, rows)
            labels = [f"{op['operand']} s{op['surface']}" for op in ops]
            values = [op["contribution"] for op in ops]
            clrs   = [self._color(op["operand"]) for op in ops]
            chart.plot_bar(labels, values, clrs, f"Top {n} Contributors")

        spin.valueChanged.connect(refresh)
        refresh()

    def _add_summary_tab(self):
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(4, 4, 4, 4)

        splitter = QSplitter(Qt.Horizontal)
        tbl = make_table(["Operand", "Description", "Count",
                          "Total Contrib.", "Max Single"])
        splitter.addWidget(tbl)
        pie = ChartCanvas()
        self._summary_chart = pie
        splitter.addWidget(pie)
        splitter.setSizes([420, 740])
        vl.addWidget(splitter)

        idx = self.inner_tabs.addTab(w, "Summary")
        self.inner_tabs.setTabToolTip(idx, "Contribution totalled per operand type")

        by_type = defaultdict(list)
        for op in self.data["operands"]:
            by_type[op["operand"]].append(op["contribution"])
        rows_sorted = sorted(by_type.items(), key=lambda x: -sum(x[1]))
        tbl_rows = [(code, OPERAND_DESC.get(code,""), len(c), sum(c), max(c))
                    for code, c in rows_sorted]
        fill_table(tbl, tbl_rows, highlight_top=3)

        labels     = [r[0] for r in tbl_rows[:16]]
        values     = [r[3] for r in tbl_rows[:16]]
        pie_colors = [self._color(l) for l in labels]
        pie.plot_pie(labels, values, pie_colors, "Contribution by Operand Type")

    def _add_group_tabs(self):
        for group_name, codes in TYPE_GROUPS.items():
            ops = [o for o in self.data["operands"] if o["operand"] in codes]
            if not ops:
                continue

            w = QWidget()
            vl = QVBoxLayout(w)
            vl.setContentsMargins(4, 4, 4, 4)

            splitter = QSplitter(Qt.Horizontal)
            tbl = make_table(["#", "Operand", "Surf",
                               "Min Val", "Max Val", "Min Δ", "Max Δ", "Contribution"])
            splitter.addWidget(tbl)
            chart = ChartCanvas()
            splitter.addWidget(chart)
            splitter.setSizes([460, 700])
            vl.addWidget(splitter)

            idx = self.inner_tabs.addTab(w, group_name)
            self.inner_tabs.setTabToolTip(idx, GROUP_TOOLTIP.get(group_name, group_name))

            ops_sorted = sorted(ops, key=lambda x: -x["contribution"])
            rows = [(i+1, op["operand"], op["surface"],
                     op["min_val"], op["max_val"],
                     op["min_change"], op["max_change"], op["contribution"])
                    for i, op in enumerate(ops_sorted)]
            fill_table(tbl, rows)
            labels = [f"{op['operand']} s{op['surface']}" for op in ops_sorted]
            values = [op["contribution"] for op in ops_sorted]
            clrs   = [self._color(op["operand"]) for op in ops_sorted]
            chart.plot_bar(labels, values, clrs, f"{group_name} — Contributions")

            self._group_charts[group_name] = (ops, chart)

    def export_pdf(self, path):
        build_pdf(path, self.data, self.filename,
                  self._all_chart, self._summary_chart, self._group_charts)



# ── CompareTab ────────────────────────────────────────────────────────────────

def _val_match(va, vb, rel_tol=1e-4):
    """True if two float values are within rel_tol of each other (or both zero)."""
    if va == 0.0 and vb == 0.0:
        return True
    ref = max(abs(va), abs(vb))
    return ref == 0 or abs(va - vb) / ref <= rel_tol


def _build_compare_data(data_a, data_b, label_a, label_b):
    """Merge two datasets by (operand, surface) key.
    Returns (rows, mismatches) where:
      rows      — list of dicts per operand
      mismatches — list of (operand, surface, min_a, max_a, min_b, max_b) for value conflicts
    """
    total_a = sum(op["contribution"] for op in data_a["operands"]) or 1.0
    total_b = sum(op["contribution"] for op in data_b["operands"]) or 1.0

    map_a = {(op["operand"], op["surface"]): op for op in data_a["operands"]}
    map_b = {(op["operand"], op["surface"]): op for op in data_b["operands"]}

    sorted_a = sorted(data_a["operands"], key=lambda x: -x["contribution"])
    sorted_b = sorted(data_b["operands"], key=lambda x: -x["contribution"])
    rank_a = {(op["operand"], op["surface"]): i+1 for i, op in enumerate(sorted_a)}
    rank_b = {(op["operand"], op["surface"]): i+1 for i, op in enumerate(sorted_b)}

    all_keys = set(map_a.keys()) | set(map_b.keys())
    rows = []
    mismatches = []
    contrib_max_a = max((op["contribution"] for op in data_a["operands"]), default=1) or 1
    contrib_max_b = max((op["contribution"] for op in data_b["operands"]), default=1) or 1

    for key in sorted(all_keys):
        operand, surface = key
        op_a = map_a.get(key)
        op_b = map_b.get(key)

        ca = op_a["contribution"] if op_a else 0.0
        cb = op_b["contribution"] if op_b else 0.0

        # operand tolerance bounds (renamed to avoid shadowing contrib_max_a/b)
        tol_min_a = op_a["min_val"] if op_a else None
        tol_max_a = op_a["max_val"] if op_a else None
        tol_min_b = op_b["min_val"] if op_b else None
        tol_max_b = op_b["max_val"] if op_b else None

        # Check for value mismatch (only when both files have the operand)
        value_ok = True
        if op_a and op_b:
            if not (_val_match(tol_min_a, tol_min_b) and _val_match(tol_max_a, tol_max_b)):
                value_ok = False
                mismatches.append((operand, surface, tol_min_a, tol_max_a, tol_min_b, tol_max_b))

        # Display value: use A if available, else B
        disp_min = tol_min_a if tol_min_a is not None else tol_min_b
        disp_max = tol_max_a if tol_max_a is not None else tol_max_b

        pct_a = ca / total_a * 100
        pct_b = cb / total_b * 100
        norm_a = ca / contrib_max_a
        norm_b = cb / contrib_max_b
        combined = (norm_a * norm_b) ** 0.5

        rows.append({
            "operand": operand, "surface": surface,
            "min_val": disp_min, "max_val": disp_max,
            "value_ok": value_ok,
            "only_in": None if (op_a and op_b) else ("a" if op_a else "b"),
            "contrib_a": ca, "contrib_b": cb,
            "pct_a": pct_a, "pct_b": pct_b,
            "norm_a": norm_a, "norm_b": norm_b,
            "rank_a": rank_a.get(key, 9999),
            "rank_b": rank_b.get(key, 9999),
            "combined": combined,
            "label": f"{operand} s{surface}",
        })
    return rows, mismatches


class CompareChart(FigureCanvas):
    """Grouped horizontal bar chart for two criteria."""
    def __init__(self, parent=None):
        self.fig = Figure(facecolor=CHART_BG)
        super().__init__(self.fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def plot_compare(self, rows, label_a, label_b, sort_by="combined", top_n=20):
        self.fig.clf()
        ax = self.fig.add_subplot(111)
        ax.set_facecolor(CHART_BG)
        self.fig.patch.set_facecolor(CHART_BG)

        if not rows:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", color=CHART_DIM)
            self.draw(); return

        # Sort and slice
        key_fn = {
            "combined": lambda r: -r["combined"],
            "a":        lambda r: -r["norm_a"],
            "b":        lambda r: -r["norm_b"],
        }.get(sort_by, lambda r: -r["combined"])
        top = sorted(rows, key=key_fn)[:top_n]
        top = list(reversed(top))  # bottom-to-top for barh

        labels  = [r["label"] for r in top]
        vals_a  = [r["norm_a"] * 100 for r in top]
        vals_b  = [r["norm_b"] * 100 for r in top]
        n = len(top)
        y = np.arange(n)
        bar_h = 0.40

        COLOR_A = C_ACCENT   # blue
        COLOR_B = C_ACCENT2  # green

        bars_a = ax.barh(y + bar_h/2, vals_a, height=bar_h,
                         color=COLOR_A, alpha=0.88, edgecolor="white", linewidth=0.4,
                         label=label_a)
        bars_b = ax.barh(y - bar_h/2, vals_b, height=bar_h,
                         color=COLOR_B, alpha=0.88, edgecolor="white", linewidth=0.4,
                         label=label_b)

        max_v = max(max(vals_a, default=0), max(vals_b, default=0)) or 1
        for bar, val in zip(bars_a, vals_a):
            if val > max_v * 0.15:
                ax.text(val * 0.97, bar.get_y() + bar.get_height()/2,
                        f"{val:.1f}%", va="center", ha="right",
                        color="white", fontsize=8, fontweight="bold",
                        fontfamily="monospace")
        for bar, val in zip(bars_b, vals_b):
            if val > max_v * 0.15:
                ax.text(val * 0.97, bar.get_y() + bar.get_height()/2,
                        f"{val:.1f}%", va="center", ha="right",
                        color="white", fontsize=8, fontweight="bold",
                        fontfamily="monospace")

        ax.set_yticks(y)
        ax.set_yticklabels(labels, color=CHART_TEXT, fontsize=8.5)
        ax.set_xlabel("Normalised Contribution (%)", color=CHART_DIM, fontsize=9)
        ax.set_title(f"{label_a}  vs  {label_b}",
                     color=CHART_TEXT, fontsize=10, fontweight="bold", pad=8)
        ax.set_xlim(0, max_v * 1.08)
        # Give each operand pair enough vertical space — 1 slot = 2 bars + gap
        ax.set_ylim(-0.8, n - 0.2)
        ax.tick_params(colors=CHART_DIM, labelsize=8)
        for sp in ax.spines.values():
            sp.set_edgecolor(CHART_GRID)
        ax.grid(axis="x", color=CHART_GRID, linewidth=0.5)
        # Legend outside plot area at bottom-right
        ax.legend(frameon=False, labelcolor=CHART_TEXT, fontsize=8,
                  loc="lower right")
        try:
            self.fig.tight_layout()
        except Exception:
            pass
        self.draw()

    def plot_combined_score(self, rows, label_a, label_b, title="Combined Score",
                            sort_by="combined", top_n=20):
        """Single bar per operand showing geometric-mean combined score."""
        self.fig.clf()
        ax = self.fig.add_subplot(111)
        ax.set_facecolor(CHART_BG)
        self.fig.patch.set_facecolor(CHART_BG)
        if not rows:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", color=CHART_DIM)
            self.draw(); return

        key_fn = {"combined": lambda r: -r["combined"],
                  "a": lambda r: -r["norm_a"],
                  "b": lambda r: -r["norm_b"]}.get(sort_by, lambda r: -r["combined"])
        top = list(reversed(sorted(rows, key=key_fn)[:top_n]))

        labels = [r["label"] for r in top]
        scores = [r["combined"] * 100 for r in top]
        clrs   = [TYPE_COLORS.get(r["operand"], DEFAULT_COLOR) for r in top]
        n = len(top)
        y = np.arange(n)

        ax.barh(y, scores, color=clrs, height=0.55, edgecolor="white", linewidth=0.4)
        max_v = max(scores) if scores else 1
        for i, val in enumerate(scores):
            if val > max_v * 0.25:
                ax.text(val * 0.97, i, f"{val:.1f}%", va="center", ha="right",
                        color="white", fontsize=8, fontweight="bold",
                        fontfamily="monospace")
            else:
                ax.text(val + max_v * 0.005, i, f"{val:.1f}%", va="center", ha="left",
                        color=CHART_TEXT, fontsize=8, fontfamily="monospace")
        ax.set_yticks(y)
        ax.set_yticklabels(labels, color=CHART_TEXT, fontsize=8.5)
        ax.set_xlabel("Combined Score (geom. mean of norm. contributions, %)",
                      color=CHART_DIM, fontsize=9)
        ax.set_title(title, color=CHART_TEXT, fontsize=10, fontweight="bold", pad=8)
        ax.set_xlim(0, max_v * 1.08)
        ax.set_ylim(-0.7, n - 0.3)
        ax.tick_params(colors=CHART_DIM, labelsize=8)
        for sp in ax.spines.values():
            sp.set_edgecolor(CHART_GRID)
        ax.grid(axis="x", color=CHART_GRID, linewidth=0.5)
        try:
            self.fig.tight_layout()
        except Exception:
            pass
        self.draw()


class CompareResultTab(QWidget):
    """A result tab produced by pressing Compare.
    Inner tabs mirror FileTab structure: All, Summary, per-type groups.
    Each group shows A vs B side-by-side AND a combined score bar.
    """
    def __init__(self, rows, data_a, data_b, label_a, label_b,
                 sort_key="combined", top_n=20, parent=None):
        super().__init__(parent)
        self._rows    = rows
        self._label_a = label_a
        self._label_b = label_b
        self._sort_key = sort_key
        self._top_n   = top_n
        self._crit_a  = data_a.get("criterion", "")
        self._crit_b  = data_b.get("criterion", "")
        self._n_a     = len(data_a["operands"])
        self._n_b     = len(data_b["operands"])
        self._build_ui()

    # ── helpers ──────────────────────────────────────────────────────────────
    def _filter_rows(self, codes=None):
        """Return rows filtered to operand codes (None = all)."""
        if codes is None:
            return self._rows
        return [r for r in self._rows if r["operand"] in codes]

    def _make_table(self):
        return make_table(["#", "Operand", "Surf", "Description",
                           "Min Val", "Max Val",
                           "Contrib A", "% A (norm)",
                           "Contrib B", "% B (norm)",
                           "Rank A", "Rank B", "Combined Score"])

    def _fill(self, tbl, rows, sort_key, top_n):
        key_fn = {"combined": lambda r: -r["combined"],
                  "a":        lambda r: -r["norm_a"],
                  "b":        lambda r: -r["norm_b"]}.get(sort_key, lambda r: -r["combined"])
        top = sorted(rows, key=key_fn)[:top_n]
        tbl.setSortingEnabled(False)
        tbl.setRowCount(len(top))
        for i, r in enumerate(top):
            vals = (i+1, r["operand"], r["surface"],
                    OPERAND_DESC.get(r["operand"], ""),
                    r["min_val"] if r["min_val"] is not None else float("nan"),
                    r["max_val"] if r["max_val"] is not None else float("nan"),
                    r["contrib_a"], r["pct_a"],
                    r["contrib_b"], r["pct_b"],
                    r["rank_a"], r["rank_b"],
                    r["combined"] * 100)
            for c, val in enumerate(vals):
                item = QTableWidgetItem()
                if isinstance(val, float):
                    item.setData(Qt.DisplayRole, val)
                    item.setText(_fmt_float(val))
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
                else:
                    item.setText(str(val))
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                # Highlight last col (combined) for top 3
                if i < 3 and c == len(vals) - 1:
                    item.setForeground(QBrush(QColor(C_WARN)))
                # Flag value mismatch: orange background on min/max val cols
                if not r.get("value_ok", True) and c in (4, 5):
                    item.setBackground(QBrush(QColor("#fff3cd")))
                    item.setForeground(QBrush(QColor("#92400e")))
                    item.setToolTip("⚠ Tolerance value differs between the two files")
                # Flag operand only in one file
                if r.get("only_in") and c in (4, 5):
                    item.setBackground(QBrush(QColor("#fce8e8")))
                    item.setForeground(QBrush(QColor(C_ERR)))
                    item.setToolTip(f"Operand only present in file {'A' if r['only_in']=='a' else 'B'}")
                tbl.setItem(i, c, item)
        tbl.setSortingEnabled(True)

    def _make_split_tab(self, rows_subset, tab_title, group_label=None):
        """Create one inner-tab widget with table | A-vs-B chart | combined chart."""
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(4, 4, 4, 4)
        vl.setSpacing(4)

        # controls
        ctl = QHBoxLayout()
        ctl.addWidget(QLabel("Sort by:"))
        combo_sort = QComboBox()
        combo_sort.addItems(["Combined", "File A", "File B"])
        combo_sort.setCurrentIndex(["combined","a","b"].index(self._sort_key))
        combo_sort.setFixedWidth(140)
        ctl.addWidget(combo_sort)
        ctl.addWidget(QLabel("  Top N:"))
        spin = QSpinBox(); spin.setRange(1, 500); spin.setValue(self._top_n)
        spin.setFixedWidth(60)
        ctl.addWidget(spin)
        ctl.addStretch()
        vl.addLayout(ctl)

        # horizontal splitter: table | charts (vertical: side-by-side top, combined bottom)
        h_split = QSplitter(Qt.Horizontal)

        tbl = self._make_table()
        h_split.addWidget(tbl)

        # right side: two charts stacked
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(2)

        chart_ab  = CompareChart()   # A vs B grouped bars
        chart_comb = CompareChart()  # combined score single bars
        rv.addWidget(chart_ab,   stretch=3)
        rv.addWidget(chart_comb, stretch=2)
        h_split.addWidget(right)
        h_split.setSizes([480, 680])
        vl.addWidget(h_split)

        title_ab   = f"{self._label_a}  vs  {self._label_b}"
        if group_label:
            title_ab = f"{group_label} — {title_ab}"
        title_comb = f"{group_label or 'All'} — Combined Score"

        def refresh():
            sk = ["combined","a","b"][combo_sort.currentIndex()]
            n  = spin.value()
            rs = self._filter_rows(None) if rows_subset is None else rows_subset
            self._fill(tbl, rs, sk, n)
            chart_ab.plot_compare(rs, self._label_a, self._label_b,
                                  sort_by=sk, top_n=n)
            chart_comb.plot_combined_score(rs, self._label_a, self._label_b,
                                           title=title_comb, sort_by=sk, top_n=n)

        combo_sort.currentIndexChanged.connect(refresh)
        spin.valueChanged.connect(refresh)
        refresh()
        return w

    def _make_summary_tab(self):
        """Summary by operand type — totals for A, B, combined."""
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(4, 4, 4, 4)

        # Build per-type aggregate
        from collections import defaultdict
        type_a = defaultdict(float); type_b = defaultdict(float)
        type_comb = defaultdict(float); type_cnt = defaultdict(int)
        for r in self._rows:
            op = r["operand"]
            type_a[op]    += r["contrib_a"]
            type_b[op]    += r["contrib_b"]
            type_comb[op] += r["combined"]
            type_cnt[op]  += 1

        codes = sorted(type_comb.keys(), key=lambda c: -type_comb[c])

        # Count mismatches per type
        type_mm = defaultdict(int)
        for r in self._rows:
            if not r.get("value_ok", True):
                type_mm[r["operand"]] += 1

        tbl = make_table(["Operand", "Description", "Count",
                          "Val Mismatches",
                          "Total Contrib A", "Total Contrib B", "Combined Score"])
        tbl_rows = [(c, OPERAND_DESC.get(c,""), type_cnt[c],
                     type_mm.get(c, 0),
                     type_a[c], type_b[c], type_comb[c] * 100)
                    for c in codes]
        fill_table(tbl, tbl_rows, highlight_top=3)

        # pie showing combined score share by type
        pie = ChartCanvas()
        pie_labels = codes[:12]
        pie_vals   = [type_comb[c] for c in pie_labels]
        pie_colors = [TYPE_COLORS.get(c, DEFAULT_COLOR) for c in pie_labels]
        pie.plot_pie(pie_labels, pie_vals, pie_colors, "Combined Score by Operand Type")

        h_split = QSplitter(Qt.Horizontal)
        h_split.addWidget(tbl)
        h_split.addWidget(pie)
        h_split.setSizes([420, 740])
        vl.addWidget(h_split)
        return w

    # ── build UI ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # info bar
        info = QLabel(
            f"  A: <b style='color:{C_ACCENT}'>{self._label_a}</b>"
            f"  [{self._crit_a}]  ·  Operands: {self._n_a}"
            f"   &nbsp;&nbsp;|&nbsp;&nbsp;  "
            f"B: <b style='color:{C_ACCENT2}'>{self._label_b}</b>"
            f"  [{self._crit_b}]  ·  Operands: {self._n_b}"
        )
        info.setTextFormat(Qt.RichText)
        info.setStyleSheet(
            f"background:{C_SURFACE}; padding:6px 10px;"
            f" border-bottom:1px solid {C_BORDER}; font-size:12px;")
        info.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        vl.addWidget(info)

        # inner tab widget
        inner = QTabWidget()
        inner.setUsesScrollButtons(True)
        inner.setElideMode(Qt.ElideNone)
        inner.tabBar().setExpanding(False)
        inner.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {C_BORDER}; background: {C_SURFACE}; }}
            QTabBar {{ background: {C_BG}; }}
            QTabBar::tab {{
                background: {C_BG}; color: {C_TEXT_DIM};
                border: 1px solid {C_BORDER}; border-bottom: none;
                padding: 4px 10px; font-size: 11px; min-width: 0px; margin-right: 1px;
            }}
            QTabBar::tab:selected {{
                background: {C_SURFACE}; color: {C_ACCENT};
                border-bottom: 2px solid {C_ACCENT}; font-weight: bold;
            }}
            QTabBar::tab:hover {{ color: {C_TEXT}; background: {C_ALT_ROW}; }}
            QTabBar::scroller {{ width: 20px; }}
        """)
        vl.addWidget(inner)

        # All tab
        all_tab = self._make_split_tab(None, "All")
        inner.addTab(all_tab, "All")
        inner.setTabToolTip(0, "All operands ranked by combined score")

        # Summary tab
        sum_tab = self._make_summary_tab()
        inner.addTab(sum_tab, "Summary")
        inner.setTabToolTip(1, "Contribution totalled per operand type")

        # Per-type tabs — only types present in rows
        present_types = set(r["operand"] for r in self._rows)
        for group_name, codes in TYPE_GROUPS.items():
            codes_set = set(codes)
            subset = [r for r in self._rows if r["operand"] in codes_set]
            if not subset:
                continue
            gt = self._make_split_tab(subset, group_name, group_label=group_name)
            idx = inner.addTab(gt, group_name)
            inner.setTabToolTip(idx, GROUP_TOOLTIP.get(group_name, group_name))


class CompareTab(QWidget):
    """Control panel tab for launching comparisons. Each compare spawns a result tab."""
    def __init__(self, files_dict, file_tabs_widget, parent=None):
        super().__init__(parent)
        self._files = files_dict
        self._file_tabs = file_tabs_widget
        self._build_ui()

    def _build_ui(self):
        vl = QVBoxLayout(self)
        vl.setContentsMargins(6, 6, 6, 6)

        # ── selector bar ──
        sel = QHBoxLayout()
        sel.addWidget(QLabel("File A:"))
        self.combo_a = QComboBox(); self.combo_a.setMinimumWidth(260)
        sel.addWidget(self.combo_a)

        sel.addWidget(QLabel("  File B:"))
        self.combo_b = QComboBox(); self.combo_b.setMinimumWidth(260)
        sel.addWidget(self.combo_b)

        sel.addWidget(QLabel("  Sort by:"))
        self.combo_sort = QComboBox()
        self.combo_sort.addItems(["Combined (geom. mean)", "File A contrib", "File B contrib"])
        self.combo_sort.setFixedWidth(200)
        sel.addWidget(self.combo_sort)

        sel.addWidget(QLabel("  Top N:"))
        self.spin = QSpinBox(); self.spin.setRange(1, 500); self.spin.setValue(20)
        self.spin.setFixedWidth(65)
        sel.addWidget(self.spin)

        btn = QPushButton("⟳  Compare")
        btn.clicked.connect(self.run_compare)
        sel.addWidget(btn)
        sel.addStretch()
        vl.addLayout(sel)

        hint = QLabel(
            "Select two files and click  ⟳ Compare  to create a new result tab.")
        hint.setStyleSheet(
            f"color:{C_TEXT_DIM}; font-size:12px; padding:10px;")
        vl.addWidget(hint)

        self.refresh_combos()

    def refresh_combos(self):
        """Reload file lists from the live _files dict."""
        paths = list(self._files.keys())
        for combo in (self.combo_a, self.combo_b):
            cur = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            for p in paths:
                combo.addItem(os.path.basename(p), p)
            # restore selection if still present
            idx = combo.findText(cur)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            combo.blockSignals(False)
        # default: A=0, B=1
        if self.combo_a.count() >= 1:
            self.combo_a.setCurrentIndex(0)
        if self.combo_b.count() >= 2:
            self.combo_b.setCurrentIndex(1)

    def run_compare(self):
        path_a = self.combo_a.currentData()
        path_b = self.combo_b.currentData()
        if not path_a or not path_b:
            return
        if path_a == path_b:
            QMessageBox.warning(self, "Same File", "Select two different files.")
            return

        data_a = self._files.get(path_a)
        data_b = self._files.get(path_b)
        if not data_a or not data_b:
            return

        label_a = os.path.basename(path_a)
        label_b = os.path.basename(path_b)
        si = self.combo_sort.currentIndex()
        sort_key = ["combined", "a", "b"][si]
        top_n = self.spin.value()

        rows, mismatches = _build_compare_data(data_a, data_b, label_a, label_b)

        # Show mismatch warning if needed
        if mismatches:
            lines = [f"  {op} s{surf}:  A=[{mn_a:.4e}, {mx_a:.4e}]  B=[{mn_b:.4e}, {mx_b:.4e}]"
                     for op, surf, mn_a, mx_a, mn_b, mx_b in mismatches[:20]]
            suffix = f"\n  … and {len(mismatches)-20} more" if len(mismatches) > 20 else ""
            QMessageBox.warning(self, "Tolerance Value Mismatch",
                f"{len(mismatches)} operand(s) have different tolerance values in the two files:\n\n"
                + "\n".join(lines) + suffix +
                "\n\nThese are highlighted in the result table.")

        # Create a new result tab and insert it into the parent file_tabs
        result = CompareResultTab(rows, data_a, data_b, label_a, label_b,
                                  sort_key=sort_key, top_n=top_n)
        short_a = label_a[:14] + "…" if len(label_a) > 14 else label_a
        short_b = label_b[:14] + "…" if len(label_b) > 14 else label_b
        tab_label = f"⇄ {short_a} vs {short_b}"
        if self._file_tabs is not None:
            idx = self._file_tabs.addTab(result, tab_label)
            self._file_tabs.setCurrentIndex(idx)

    def on_files_changed(self):
        """Called by MainWindow when files are loaded/closed."""
        self.refresh_combos()


# ── MainWindow ────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Zemax Tolerance Analyzer")
        self.resize(1440, 880)
        self.setStyleSheet(STYLESHEET)
        self._files = {}
        self._compare_tab = None
        self._build_ui()

    def _build_ui(self):
        tb = QToolBar()
        tb.setMovable(False)
        tb.setIconSize(QSize(16, 16))
        self.addToolBar(tb)

        btn_open = QPushButton("⊕  Open File(s)")
        btn_open.clicked.connect(self.open_files)
        tb.addWidget(btn_open)

        btn_close = QPushButton("✕  Close Tab")
        btn_close.clicked.connect(self.close_current)
        tb.addWidget(btn_close)

        btn_pdf = QPushButton("⬇  Save Report PDF")
        btn_pdf.clicked.connect(self.save_pdf)
        tb.addWidget(btn_pdf)

        btn_compare = QPushButton("⇄  Compare Files")
        btn_compare.clicked.connect(self._open_compare_tab)
        tb.addWidget(btn_compare)

        self.file_tabs = QTabWidget()
        self.file_tabs.setTabsClosable(True)
        self.file_tabs.setUsesScrollButtons(True)
        self.file_tabs.setElideMode(Qt.ElideNone)
        self.file_tabs.tabBar().setExpanding(False)
        self.file_tabs.tabCloseRequested.connect(self.close_tab)
        self.file_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {C_BORDER}; background: {C_BG};
            }}
            QTabBar::tab {{
                background: {C_ALT_ROW}; color: {C_TEXT_DIM};
                border: 1px solid {C_BORDER}; border-bottom: none;
                padding: 6px 16px; font-size: 12px; min-width: 0px;
                margin-right: 1px;
            }}
            QTabBar::tab:selected {{
                background: {C_SURFACE}; color: {C_ACCENT};
                border-bottom: 2px solid {C_ACCENT}; font-weight: bold;
            }}
            QTabBar::tab:hover {{ color: {C_TEXT}; }}
            QTabBar::scroller {{ width: 20px; }}
        """)

        self._show_welcome()
        self.setCentralWidget(self.file_tabs)

        self.status = QStatusBar()
        self.status.setStyleSheet(
            f"background:{C_SURFACE}; color:{C_TEXT_DIM}; font-size:11px;")
        self.setStatusBar(self.status)
        self.status.showMessage("Ready — open a Zemax tolerancing file to begin.")

    def _show_welcome(self):
        lbl = QLabel(
            "Open a Zemax tolerancing output file to begin.\n\n"
            "Click  ⊕ Open File(s)  in the toolbar above.")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f"color:{C_TEXT_DIM}; font-size:15px; background:{C_BG};")
        self.file_tabs.addTab(lbl, "Welcome")
        self.file_tabs.tabBar().setTabButton(0, self.file_tabs.tabBar().RightSide, None)

    def open_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Zemax Tolerance File(s)", "",
            "Text Files (*.txt);;All Files (*)"
        )
        for path in paths:
            self._load_file(path)

    def _load_file(self, path):
        if path in self._files:
            for i in range(self.file_tabs.count()):
                if self.file_tabs.tabToolTip(i) == path:
                    self.file_tabs.setCurrentIndex(i); return

        self.status.showMessage(f"Parsing {os.path.basename(path)} …")
        QApplication.processEvents()
        try:
            data = parse_file(path)
        except Exception as e:
            QMessageBox.critical(self, "Parse Error", str(e))
            self.status.showMessage("Error loading file."); return

        if not data["operands"]:
            QMessageBox.warning(self, "No Data",
                "No sensitivity analysis operands found.\n"
                "Ensure the file is a Zemax tolerancing output in Sensitivities mode.")
            self.status.showMessage("No operands found."); return

        self._files[path] = data
        if self._compare_tab is not None:
            self._compare_tab.on_files_changed()
        if self.file_tabs.count() == 1 and self.file_tabs.tabText(0) == "Welcome":
            self.file_tabs.removeTab(0)

        tab = FileTab(data, os.path.basename(path))
        short = os.path.basename(path)
        if len(short) > 30:
            short = short[:27] + "…"
        idx = self.file_tabs.addTab(tab, short)
        self.file_tabs.setTabToolTip(idx, path)
        self.file_tabs.setCurrentIndex(idx)
        self.status.showMessage(
            f"Loaded: {os.path.basename(path)}  ·  {len(data['operands'])} operands  ·  "
            f"Nominal: {data['nominal']:.6f}"
        )

    def save_pdf(self):
        idx = self.file_tabs.currentIndex()
        widget = self.file_tabs.widget(idx)
        if not isinstance(widget, FileTab):
            QMessageBox.information(self, "No file", "Open a tolerance file first.")
            return
        default = os.path.splitext(widget.filename)[0] + "_report.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF Report", default, "PDF Files (*.pdf);;All Files (*)"
        )
        if not path:
            return
        self.status.showMessage("Generating PDF…")
        QApplication.processEvents()
        try:
            widget.export_pdf(path)
            self.status.showMessage(f"PDF saved: {path}")
        except Exception as e:
            QMessageBox.critical(self, "PDF Error", str(e))
            self.status.showMessage("PDF export failed.")

    def _open_compare_tab(self):
        if len(self._files) < 2:
            QMessageBox.information(self, "Need 2 files",
                "Load at least two tolerance files before comparing.")
            return
        # Reuse existing compare tab if present
        if self._compare_tab is not None:
            for i in range(self.file_tabs.count()):
                if self.file_tabs.widget(i) is self._compare_tab:
                    self._compare_tab.refresh_combos()
                    self.file_tabs.setCurrentIndex(i)
                    return
        self._compare_tab = CompareTab(self._files, self.file_tabs)
        idx = self.file_tabs.addTab(self._compare_tab, "⇄ Compare")
        self.file_tabs.setCurrentIndex(idx)

    def close_current(self):
        idx = self.file_tabs.currentIndex()
        if idx >= 0:
            self.close_tab(idx)

    def close_tab(self, idx):
        tip = self.file_tabs.tabToolTip(idx)
        if tip in self._files:
            del self._files[tip]
        self.file_tabs.removeTab(idx)
        if self._compare_tab is not None:
            self._compare_tab.on_files_changed()
        if self.file_tabs.count() == 0:
            self._show_welcome()
            self.status.showMessage("Ready.")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.Window,          QColor(C_BG))
    pal.setColor(QPalette.WindowText,      QColor(C_TEXT))
    pal.setColor(QPalette.Base,            QColor(C_SURFACE))
    pal.setColor(QPalette.AlternateBase,   QColor(C_ALT_ROW))
    pal.setColor(QPalette.ToolTipBase,     QColor(C_SURFACE))
    pal.setColor(QPalette.ToolTipText,     QColor(C_TEXT))
    pal.setColor(QPalette.Text,            QColor(C_TEXT))
    pal.setColor(QPalette.Button,          QColor(C_SURFACE))
    pal.setColor(QPalette.ButtonText,      QColor(C_TEXT))
    pal.setColor(QPalette.Highlight,       QColor(C_SEL))
    pal.setColor(QPalette.HighlightedText, QColor(C_ACCENT))
    pal.setColor(QPalette.Mid,             QColor(C_BORDER))
    pal.setColor(QPalette.Dark,            QColor(C_BORDER))
    app.setPalette(pal)

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()