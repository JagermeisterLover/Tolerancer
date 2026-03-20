import sys
import os
import io
from collections import defaultdict
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTabWidget, QFileDialog, QTableWidget, QTableWidgetItem,
    QLabel, QSplitter, QSpinBox, QHeaderView, QSizePolicy, QToolBar,
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


def fill_table(table, rows, highlight_top=3):
    table.setSortingEnabled(False)
    table.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            item = QTableWidgetItem()
            if isinstance(val, float):
                item.setData(Qt.DisplayRole, val)
                item.setText(f"{val:.6e}")
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


# ── MainWindow ────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Zemax Tolerance Analyzer")
        self.resize(1440, 880)
        self.setStyleSheet(STYLESHEET)
        self._files = {}
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

    def close_current(self):
        idx = self.file_tabs.currentIndex()
        if idx >= 0:
            self.close_tab(idx)

    def close_tab(self, idx):
        tip = self.file_tabs.tabToolTip(idx)
        if tip in self._files:
            del self._files[tip]
        self.file_tabs.removeTab(idx)
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