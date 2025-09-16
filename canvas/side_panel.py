# -*- coding: utf-8 -*-
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QToolButton, QFrame, QSizePolicy,
    QButtonGroup, QHBoxLayout
)

MM_PER_INCH = 25.4


def mm_to_px(mm: float) -> int:
    screen = QGuiApplication.primaryScreen()
    dpi_x = screen.physicalDotsPerInchX() if screen else 96.0
    return max(24, int(round(dpi_x * (mm / MM_PER_INCH))))


OUTLINED_BTN_STYLE = """
QToolButton {
    border: 1px solid #666;
    border-radius: 4px;
    padding: 4px 6px;
    background-color: #f5f5f5;
    color: #000;
}
QToolButton:hover {
    border-color: #1a73e8;
    background-color: #fafafa;
}
QToolButton:pressed {
    background-color: #e6f0ff;
}
QToolButton:checked {
    background-color: #dbe8ff;
    border-color: #1a73e8;
    color: #000;
}
QToolButton:disabled {
    color: #888;
    background-color: #f0f0f0;
    border-color: #bbb;
}
"""


class SidePanel(QWidget):
    """
    Slim (~60 mm) view control panel with outlined text buttons and compact info.
    """
    fitAllRequested = Signal()
    layerModeChanged = Signal(str)
    lesStepsToggled = Signal(bool)
    outlineToggled = Signal(bool)
    edgesToggled = Signal(bool)
    xmlStepsToggled = Signal(bool)
    barcodesToggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedWidth(mm_to_px(60))
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # Fit All button at the top
        self._btn_fit_all = self._mk_btn("Fit All", "Fit all content")
        self._btn_fit_all.clicked.connect(self.fitAllRequested.emit)
        root.addWidget(self._btn_fit_all)

        # LES Section
        self._les_label = self._mk_header("LES VIEW")
        root.addWidget(self._les_label)

        row = QHBoxLayout()
        row.setSpacing(6)
        self._btn_top = self._mk_btn("Top", "Show top layer only", check=True)
        self._btn_bot = self._mk_btn("Bot", "Show bottom layer only", check=True)
        self._btn_both = self._mk_btn("Both", "Show both layers", check=True)
        row.addWidget(self._btn_top)
        row.addWidget(self._btn_bot)
        row.addWidget(self._btn_both)
        root.addLayout(row)

        self._layer_group = QButtonGroup(self)
        self._layer_group.addButton(self._btn_top, 1)
        self._layer_group.addButton(self._btn_bot, 2)
        self._layer_group.addButton(self._btn_both, 3)
        self._btn_both.setChecked(True)

        self._btn_les_steps = self._mk_btn("Steps", "Toggle LES Steps", check=True)
        self._btn_outline = self._mk_btn("Outline", "Toggle LES Outline", check=True)
        root.addWidget(self._btn_les_steps)
        root.addWidget(self._btn_outline)

        self._les_info = self._mk_info_label()
        root.addWidget(self._les_info)

        root.addWidget(self._mk_div())

        # XML Section
        self._xml_label = self._mk_header("XML VIEW")
        root.addWidget(self._xml_label)

        self._btn_edges = self._mk_btn("Edges", "Toggle XML Edges", check=True)
        self._btn_xml_steps = self._mk_btn("Steps", "Toggle XML repeated steps", check=True)
        self._btn_barcodes = self._mk_btn("Barcodes", "Toggle XML barcodes", check=True)
        root.addWidget(self._btn_edges)
        root.addWidget(self._btn_xml_steps)
        root.addWidget(self._btn_barcodes)

        self._xml_info = self._mk_info_label()
        root.addWidget(self._xml_info)

        root.addStretch(1)

        # Wiring
        self._layer_group.idClicked.connect(self._emit_layer_mode)
        self._btn_les_steps.toggled.connect(self.lesStepsToggled.emit)
        self._btn_outline.toggled.connect(self.outlineToggled.emit)
        self._btn_edges.toggled.connect(self.edgesToggled.emit)
        self._btn_xml_steps.toggled.connect(self.xmlStepsToggled.emit)
        self._btn_barcodes.toggled.connect(self.barcodesToggled.emit)

    # ---------- UI helpers ----------
    def _mk_btn(self, text: str, tip: str, check: bool = False) -> QToolButton:
        btn = QToolButton(self)
        btn.setText(text)
        btn.setToolTip(tip)
        btn.setCheckable(check)
        btn.setAutoRaise(False)  # keep outline visible
        btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        btn.setMinimumHeight(28)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.setStyleSheet(OUTLINED_BTN_STYLE)
        return btn

    def _mk_div(self) -> QFrame:
        div = QFrame(self)
        div.setFrameShape(QFrame.HLine)
        div.setFrameShadow(QFrame.Sunken)
        return div

    def _mk_header(self, text: str) -> QLabel:
        lbl = QLabel(text, self)
        lbl.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        lbl.setStyleSheet("font-weight: 700; color: #000;")
        return lbl

    def _mk_info_label(self) -> QLabel:
        lbl = QLabel("—", self)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color:#000; font: 11px 'Courier New', monospace;")
        lbl.setMaximumHeight(mm_to_px(35))  # cap height to avoid pushing buttons
        return lbl

    # ---------- signals ----------
    def _emit_layer_mode(self, idx: int):
        mode = {1: "top", 2: "bottom", 3: "both"}.get(idx, "both")
        self.layerModeChanged.emit(mode)

    # ---------- public API ----------
    def set_les_enabled(self, on: bool):
        for w in (self._les_label, self._btn_top, self._btn_bot, self._btn_both,
                  self._btn_les_steps, self._btn_outline, self._les_info):
            w.setEnabled(on)

    def set_xml_enabled(self, on: bool):
        for w in (self._xml_label, self._btn_edges, self._btn_xml_steps,
                  self._btn_barcodes, self._xml_info):
            w.setEnabled(on)

    def sync_from_canvas(self, canvas):
        # LES
        mode = getattr(canvas, "layer_mode", "both")
        if mode == "top":
            self._btn_top.setChecked(True)
        elif mode == "bottom":
            self._btn_bot.setChecked(True)
        else:
            self._btn_both.setChecked(True)

        self._btn_les_steps.setChecked(bool(getattr(canvas, "show_steps", False)))
        self._btn_outline.setChecked(bool(getattr(canvas, "show_outline", False)))

        has_les = bool(getattr(canvas, "les_data", None))
        self.set_les_enabled(has_les)
        self._update_les_info(canvas if has_les else None)

        # XML
        self._btn_edges.setChecked(bool(getattr(canvas, "show_xml_edges", True)))
        self._btn_xml_steps.setChecked(bool(getattr(canvas, "show_xml_repeats", True)))
        self._btn_barcodes.setChecked(bool(getattr(canvas, "show_xml_barcodes", True)))

        has_xml = bool(getattr(canvas, "xml_drawings", []))
        self.set_xml_enabled(has_xml)
        self._update_xml_info(canvas if has_xml else None)

    def _update_les_info(self, canvas):
        if not canvas or not canvas.les_data:
            self._les_info.setText("—")
            return
        ld = canvas.les_data
        txt = (
            f"Test: {ld.test or '—'}\n"
            f"Layers: {ld.count_of_layer or 0}\n"
            f"Points: {len(ld.points)}  Nets: {len(ld.nets)}\n"
            f"Apertures: {len(ld.apertures)}\n"
            f"Steps: {len(ld.steps)}  Outline: {len(ld.outline_points)}"
        )
        self._les_info.setText(txt)

    def _update_xml_info(self, canvas):
        if not canvas or not canvas.xml_drawings or canvas.current_xml_drawing_idx < 0:
            self._xml_info.setText("—")
            return
        drawing = canvas.xml_drawings[canvas.current_xml_drawing_idx]
        cur_step = canvas.current_xml_step or "—"
        txt = (
            f"Job: {drawing.job or '—'}\n"
            f"Size: {drawing.width:g} × {drawing.height:g}\n"
            f"Step: {cur_step}\n"
            f"Steps: {len(drawing.steps)}"
        )
        self._xml_info.setText(txt)
