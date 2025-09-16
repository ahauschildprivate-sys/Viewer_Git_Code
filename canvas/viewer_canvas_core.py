# -*- coding: utf-8 -*-
"""
viewer_canvas_core.py
Core canvas: data/state, file I/O, transforms, fit, and stats.
Keeps public attributes and methods used by SidePanel and drawings.
"""
from __future__ import annotations

import os
import math
from typing import List, Optional, Tuple, Dict

from PySide6.QtCore import Qt, QPointF, QSize
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QWidget, QMessageBox, QSizePolicy

from .dialogs import TextDialog
from . import les_drawing
from . import xml_drawing

from les_parser import Point, Les
from xml_parser import Drawing, Step


class ViewerCanvasCore(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Data
        self.les_data: Optional[Les] = None
        self.xml_drawings: List[Drawing] = []
        self.current_xml_drawing_idx: int = -1
        self.current_xml_step: Optional[str] = None

        # View state
        self.zoom_level: float = 1.0
        self.pan_offset: QPointF = QPointF(0.0, 0.0)
        self.dragging: bool = False
        self.drag_button = None
        self.drag_start = None  # set in view mixin

        self.toolbar_height: int = 0
        self.xml_toolbar_height: int = 0

        # Layer visibility and modes
        self.show_layers: Dict[int, bool] = {}
        self.layer_mode: str = 'both'
        self.show_steps: bool = False
        self.show_outline: bool = False

        # XML toggles
        self.show_xml_edges: bool = True
        self.show_xml_repeats: bool = True
        self.show_xml_barcodes: bool = True

        # Selection
        self.selected_point: Optional[Point] = None

        # Appearance
        self.background_color = QColor(30, 30, 30)
        self.grid_color = QColor(50, 50, 50)
        self.text_color = QColor(220, 220, 220)
        self.highlight_color = QColor(255, 255, 0)
        self.step_color = QColor(0, 191, 255)
        self.outline_color = QColor(0, 255, 255)

        self.info_font = QFont('Arial', 10)
        self.title_font = QFont('Arial', 14, QFont.Weight.Bold)

        # Size
        self._w = 1200
        self._h = 800

    # ----------------------------------------------------------------------
    # File loading / unloading
    # ----------------------------------------------------------------------
    def load_file(self, file_path: str) -> bool:
        try:
            if file_path.lower().endswith('.xml'):
                self.load_xml_file(file_path, show_info=True)
                return True
            else:
                self.les_data = Les(file_path)
                self.show_layers.clear()
                for p in self.les_data.points:
                    self.show_layers[p.layer] = True
                self.init_layer_visibility()
                les_drawing.auto_zoom(self)
                self.update()
                return True
        except Exception as e:
            QMessageBox.critical(self, 'Load Error', str(e))
            return False

    def load_xml_file(self, file_path: str, show_info: bool = True):
        drawing = Drawing(file_path)
        self.xml_drawings.append(drawing)
        self.current_xml_drawing_idx = len(self.xml_drawings) - 1
        self.current_xml_step = (
            drawing.start_step
            or (next(iter(drawing.steps.keys())) if drawing.steps else None)
        )
        xml_drawing.reset_xml_view(self)
        if show_info:
            self.show_xml_info_window()
        self.update()

    def unload_les(self):
        self.les_data = None
        self.selected_point = None
        self.show_layers.clear()
        self.update()

    def unload_current_xml(self):
        if not self.xml_drawings:
            return
        idx = self.current_xml_drawing_idx
        if 0 <= idx < len(self.xml_drawings):
            del self.xml_drawings[idx]
        if not self.xml_drawings:
            self.current_xml_drawing_idx = -1
            self.current_xml_step = None
        else:
            self.current_xml_drawing_idx = min(idx, len(self.xml_drawings) - 1)
            cur = self.xml_drawings[self.current_xml_drawing_idx]
            self.current_xml_step = (
                cur.start_step
                or (next(iter(cur.steps.keys())) if cur.steps else None)
            )
        xml_drawing.reset_xml_view(self)
        self.update()

    # ----------------------------------------------------------------------
    # Coordinate transforms
    # ----------------------------------------------------------------------
    def world_to_screen(self, x: float, y: float) -> Tuple[float, float]:
        return (
            x * self.zoom_level + self.pan_offset.x(),
            y * self.zoom_level + self.pan_offset.y(),
        )

    def screen_to_world(self, sx: float, sy: float) -> Tuple[float, float]:
        return (
            (sx - self.pan_offset.x()) / self.zoom_level,
            (sy - self.pan_offset.y()) / self.zoom_level,
        )

    # ----------------------------------------------------------------------
    # Fitting / zoom
    # ----------------------------------------------------------------------
    def _fit_world_bounds(
        self, minx: float, miny: float, maxx: float, maxy: float, padding: int = 50
    ):
        if not (math.isfinite(minx) and math.isfinite(miny) and math.isfinite(maxx) and math.isfinite(maxy)):
            return
        bw, bh = maxx - minx, maxy - miny
        if bw <= 0 or bh <= 0:
            return

        avail_w = self._w - 2 * padding
        top_y = self.toolbar_height + self.xml_toolbar_height
        avail_h = self._h - top_y - 2 * padding
        if avail_w <= 0 or avail_h <= 0:
            return

        zx = avail_w / bw
        zy = avail_h / bh
        self.zoom_level = min(zx, zy)

        cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
        self.pan_offset.setX(self._w / 2 - cx * self.zoom_level)
        self.pan_offset.setY((top_y + (self._h - top_y) / 2) - cy * self.zoom_level)

    def fit_xml_step(self, include_repeats: bool):
        xml_drawing.fit_step(self, include_repeats)

    def fit_all(self):
        minx = float('inf'); miny = float('inf')
        maxx = float('-inf'); maxy = float('-inf')
        any_bounds = False

        # LES
        if self.les_data:
            xs: List[float] = []
            ys: List[float] = []
            visible = [p for p in self.les_data.points if self.show_layers.get(p.layer, False)]
            for p in visible:
                xs.append(p.x); ys.append(p.y)

            if self.show_steps:
                for st in self.les_data.steps:
                    for i in range(st.amount):
                        for p in visible:
                            if p.image != st.image:
                                continue
                            x, y, _ = st.apply_transformation(p, i)
                            xs.append(x); ys.append(y)

            if (self.show_outline and self.les_data.outline_points) or not xs:
                for seg in self.les_data.outline_points:
                    for (x, y) in seg:
                        xs.append(x); ys.append(y)

            if xs:
                minx = min(minx, min(xs)); maxx = max(maxx, max(xs))
                miny = min(miny, min(ys)); maxy = max(maxy, max(ys))
                any_bounds = True

        # XML
        if self.xml_drawings and self.current_xml_drawing_idx >= 0 and self.current_xml_step:
            drawing = self.xml_drawings[self.current_xml_drawing_idx]
            if self.current_xml_step in drawing.steps:
                step = drawing.steps[self.current_xml_step]
                bounds = [float('inf'), float('inf'), float('-inf'), float('-inf')]

                def add_bounds(b: Tuple[float, float, float, float]):
                    if b[0] != float('inf'):
                        bounds[0] = min(bounds[0], b[0])
                        bounds[1] = min(bounds[1], b[1])
                        bounds[2] = max(bounds[2], b[2])
                        bounds[3] = max(bounds[3], b[3])

                def arc_bounds(cx: float, cy: float, r: float, a0: float, a1: float, direction: str):
                    pts: List[Tuple[float, float]] = []
                    for ang in [a0, a1]:
                        rad = math.radians(ang)
                        pts.append((cx + r * math.cos(rad), cy - r * math.sin(rad)))
                    for ang in [0, 90, 180, 270]:
                        if xml_drawing._angle_in_sweep(ang, a0, a1, direction):
                            rad = math.radians(ang)
                            pts.append((cx + r * math.cos(rad), cy - r * math.sin(rad)))
                    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
                    return (min(xs), min(ys), max(xs), max(ys))

                def compute_step_bounds(st: Step, base_angle_deg: float, off_x: float, off_y: float, depth=0):
                    ang = -base_angle_deg * math.pi / 180.0

                    if self.show_xml_edges:
                        for e in st.edges:
                            if e.type == 'line':
                                sx, sy = xml_drawing.rotate_translate(e.xs, e.ys, ang, off_x, off_y)
                                ex, ey = xml_drawing.rotate_translate(e.xe, e.ye, ang, off_x, off_y)
                                add_bounds((min(sx, ex), min(sy, ey), max(sx, ex), max(sy, ey)))
                            elif e.type == 'arc':
                                sx, sy = xml_drawing.rotate_translate(e.xs, e.ys, ang, off_x, off_y)
                                ex, ey = xml_drawing.rotate_translate(e.xe, e.ye, ang, off_x, off_y)
                                cx, cy = xml_drawing.rotate_translate(e.xc, e.yc, ang, off_x, off_y)
                                r = math.hypot(sx - cx, sy - cy) or max(getattr(e, 'radius', 0.0), 0.0)
                                a0 = xml_drawing._angle_deg_math(cx, cy, sx, sy)
                                a1 = xml_drawing._angle_deg_math(cx, cy, ex, ey)
                                dir_math = xml_drawing._xml_dir_to_math(getattr(e, 'direction', 'ccw'))
                                ab = arc_bounds(cx, cy, r, a0, a1, dir_math)
                                add_bounds(ab)

                    if self.show_xml_barcodes:
                        for layer in st.layers:
                            for bc in layer.barcode_list:
                                bx, by = xml_drawing.rotate_translate(bc.x, bc.y, ang, off_x, off_y)
                                add_bounds((bx, by, bx + bc.width, by + bc.height))

                    if self.show_xml_repeats:
                        for rpt in st.repeats:
                            if rpt.step in drawing.steps:
                                sub = drawing.steps[rpt.step]
                                rx, ry = xml_drawing.rotate_translate(rpt.x, rpt.y, ang, off_x, off_y)
                                compute_step_bounds(sub, base_angle_deg + rpt.angle, rx, ry, depth + 1)

                compute_step_bounds(step, 0, -step.x, -step.y, 0)

                if bounds[0] != float('inf'):
                    minx = min(minx, bounds[0]); miny = min(miny, bounds[1])
                    maxx = max(maxx, bounds[2]); maxy = max(maxy, bounds[3])
                    any_bounds = True

        if any_bounds and (maxx > minx) and (maxy > miny):
            self._fit_world_bounds(minx, miny, maxx, maxy, padding=50)
            self.update()

    # ----------------------------------------------------------------------
    # Layer visibility
    # ----------------------------------------------------------------------
    def init_layer_visibility(self):
        if not self.les_data:
            return
        top_layer = 1
        bottom_layer = self.les_data.count_of_layer if self.les_data.count_of_layer else max(
            [p.layer for p in self.les_data.points] + [1]
        )
        if self.layer_mode == 'top':
            for layer in list(self.show_layers.keys()):
                self.show_layers[layer] = (layer == top_layer)
        elif self.layer_mode == 'bottom':
            for layer in list(self.show_layers.keys()):
                self.show_layers[layer] = (layer == bottom_layer)
        else:
            for layer in list(self.show_layers.keys()):
                self.show_layers[layer] = (layer in (top_layer, bottom_layer))
        self.update()

    # ----------------------------------------------------------------------
    # Stats & Info
    # ----------------------------------------------------------------------
    def show_stats_window(self):
        if not self.les_data:
            return
        text = self.generate_stats_text()
        dlg = TextDialog('LES File Statistics', text, self)
        dlg.exec()

    def generate_stats_text(self) -> str:
        if not self.les_data:
            return "No LES file loaded"
        ld = self.les_data
        lines = [
            "LES File Statistics",
            "=" * 50,
            "",
            f"File: {os.path.basename(getattr(ld, 'file_path', '') or 'Unknown')}",
            f"Test: {ld.test}",
            f"Layers: {ld.count_of_layer}",
            f"Unit: {ld.unit} (scale {ld.scale:.6f} mm/u)",
            f"Points: {len(ld.points)}",
            f"Nets: {len(ld.nets)}",
            f"Apertures: {len(ld.apertures)}",
            f"Steps: {len(ld.steps)}",
            f"Outline Segments: {len(ld.outline_points)}",
            f"View: {self.layer_mode.capitalize()}",
            "Top Layer: 1",
            f"Bottom Layer: {ld.count_of_layer}",
            "",
        ]
        if self.selected_point:
            p = self.selected_point
            status_yes_no = "Yes" if p.is_test else "No"
            lines += [
                "Selected Point:",
                "-" * 30,
                f"Type: {p.type.name}",
                f"Position: X{p.x:.3f}, Y{p.y:.3f}",
                f"Layer: {p.layer}",
                f"Net: {p.net.index}",
                f"Aperture: {p.aperture.mode.name}{p.aperture.index}",
                f"Test: {status_yes_no}",
                "",
            ]
        return "\n".join(lines)

    def show_xml_info_window(self):
        if not (self.xml_drawings and self.current_xml_drawing_idx >= 0):
            return
        drawing = self.xml_drawings[self.current_xml_drawing_idx]
        info = xml_drawing.xml_info_text(drawing)
        dlg = TextDialog('XML File Info', info, self)
        dlg.exec()

    # ----------------------------------------------------------------------
    # QWidget basics
    # ----------------------------------------------------------------------
    def sizeHint(self) -> QSize:
        return QSize(self._w, self._h)

    def resizeEvent(self, e):
        self._w = int(self.width())
        self._h = int(self.height())
        super().resizeEvent(e)

    # ----------------------------------------------------------------------
    # Utilities
    # ----------------------------------------------------------------------
    def save_screenshot(self):
        if self.xml_drawings and self.current_xml_drawing_idx >= 0:
            job = self.xml_drawings[self.current_xml_drawing_idx].job or 'pcb'
        elif self.les_data:
            job = self.les_data.test or 'les'
        else:
            job = 'unknown'
        from datetime import datetime
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        fname = f'{job}_{ts}.png'
        pix = self.grab()
        pix.save(fname)
        QMessageBox.information(self, 'Screenshot', f'Saved screenshot to\n{os.path.abspath(fname)}')
