# -*- coding: utf-8 -*-
"""
viewer_canvas_view.py
Painting & user interactions (mixin).
Relies on attributes and methods provided by ViewerCanvasCore.
"""
from __future__ import annotations

import math
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush
from PySide6.QtGui import QCursor

from . import les_drawing
from . import xml_drawing


class CanvasPaintingMixin:
    # -------------------------- helpers --------------------------
    def _draw_grid(self, p: QPainter):
        if self.zoom_level <= 0.1:
            return
        grid = 10 * self.zoom_level
        if grid <= 5:
            return
        p.setPen(QPen(self.grid_color, 1))
        sx0, sy0 = self.world_to_screen(0, 0)

        x = sx0 % grid
        while x < self._w:
            p.drawLine(int(x), 0, int(x), self._h)
            x += grid

        y = sy0 % grid
        while y < self._h:
            p.drawLine(0, int(y), self._w, int(y))
            y += grid

    def _draw_origin(self, p: QPainter):
        ox, oy = self.world_to_screen(0, 0)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(255, 0, 0)))
        r = 5
        p.drawEllipse(QPointF(ox, oy), r, r)

        axis_len = 50 / self.zoom_level
        x_end, _ = self.world_to_screen(axis_len, 0)
        p.setPen(QPen(QColor(255, 0, 0), 2))
        p.drawLine(QPointF(ox, oy), QPointF(x_end, oy))

        _, y_end = self.world_to_screen(0, axis_len)
        p.setPen(QPen(QColor(0, 255, 0), 2))
        p.drawLine(QPointF(ox, oy), QPointF(ox, y_end))

    # viewer_canvas_view.py - Update the _draw_point_info method

    def _draw_point_info(self, p: QPainter):
        pt = self.selected_point
        if pt is None:
            return

        # ---- Type mapping (code -> human meaning) ----
        # S = Signal Point, D = Drill Point, B = Bridge Point,
        # P = Power Point, E = Edge/Ext. Ref. Point
        type_map = {
            'S': 'Signal Point',
            'D': 'Drill Point',
            'B': 'Bridge Point',
            'P': 'Power Point',
            'E': 'Edge/Ext. Ref. Point',
        }
        t_code = getattr(getattr(pt, "type", None), "name", "NONE")
        t_desc = type_map.get(t_code, t_code)
        type_line = f"Type: {t_code} = {t_desc}"

        # ---- Aperture description (human-friendly with size) ----
        ap = getattr(pt, "aperture", None)
        apt_mode = getattr(ap, "mode", None)
        apt_desc = "—"
        apt_code = "—"

        if ap is not None and apt_mode is not None:
            mode_name = apt_mode.name  # 'T', 'O', 'K', 'F', 'U'
            idx = getattr(ap, "index", 0)
            apt_code = f"{mode_name}{idx}"

            # Compose readable size text by aperture type
            if mode_name == 'T':
                # Round: ap.radius is radius; show diameter
                d = 2 * float(getattr(ap, "radius", 0.0))
                apt_desc = f"Round Ø{d:.3f}"
            elif mode_name == 'O':
                w = float(getattr(ap, "width", 0.0))
                h = float(getattr(ap, "height", 0.0))
                ang = float(getattr(ap, "angle", 0.0))
                apt_desc = f"Rect {w:.3f} × {h:.3f}" + (f" @ {ang:g}°" if abs(ang) > 1e-9 else "")
            elif mode_name == 'K':
                # Annular: inner/outer are radii; show diameters
                do = 2 * float(getattr(ap, "outer_radius", 0.0))
                di = 2 * float(getattr(ap, "inner_radius", 0.0))
                apt_desc = f"Annular Ø{do:.3f} / Ø{di:.3f}"
            elif mode_name == 'F':
                # Tooling hole: radius; show diameter
                d = 2 * float(getattr(ap, "radius", 0.0))
                apt_desc = f"Tooling Ø{d:.3f}"
            else:
                # Unknown / special
                apt_desc = mode_name

        status = "Test" if getattr(pt, "is_test", False) else "Not Test"

        # Get panel image name if available
        panel_info = getattr(pt, "panel_image_name", "—")

        # ---- Compose overlay lines (now with Panel info) ----
        lines = [
            "Point Info",
            type_line,  # e.g., "Type: S = Signal Point"
            f"X: {pt.x:.3f}",
            f"Y: {pt.y:.3f}",
            f"Layer: {pt.layer}",
            f"Panel: {panel_info}",  # New line for panel info
            f"Image: {pt.image}",
            f"Net: {pt.net.index}",
            f"Aperture: {apt_desc} ({apt_code})",
            f"Status: {status}",
        ]

        # ---- Draw the info panel ----
        pad = 10
        p.setFont(self.info_font)
        max_w = max(p.fontMetrics().horizontalAdvance(t) for t in lines)
        line_h = p.fontMetrics().height() + 2
        box_w = max_w + pad * 2
        box_h = len(lines) * line_h + pad * 2 + 6

        top_y = self.toolbar_height + self.xml_toolbar_height
        x0, y0 = 15, top_y + 15

        # Background
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 190)))
        p.drawRect(QRectF(x0, y0, box_w, box_h))

        # Header strip
        p.setBrush(QBrush(QColor(100, 200, 255, 220)))
        p.drawRect(QRectF(x0, y0, box_w, p.fontMetrics().height() + pad))

        # Text
        y = y0 + pad - 2
        for i, t in enumerate(lines):
            col = QColor(20, 20, 20) if i == 0 else QColor(230, 230, 230)
            p.setPen(QPen(col))
            p.drawText(QPointF(x0 + pad, y + p.fontMetrics().ascent()), t)
            y += line_h

        # Outline
        p.setPen(QPen(QColor(180, 180, 180, 230), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(QRectF(x0, y0, box_w, box_h))

    def _draw_no_file_loaded(self, p: QPainter):
        p.setFont(self.title_font)
        p.setPen(QPen(self.text_color))
        text = 'No file loaded'
        tw = p.fontMetrics().horizontalAdvance(text)
        th = p.fontMetrics().height()
        p.drawText(QPointF((self._w - tw) / 2, (self._h - th) / 2), text)

        p.setFont(self.info_font)
        note = 'Use File > Open to load a LES or XML file'
        nw = p.fontMetrics().horizontalAdvance(note)
        p.drawText(QPointF((self._w - nw) / 2, (self._h - th) / 2 + 40), note)

    # -------------------------- painting -------------------------
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillRect(self.rect(), self.background_color)

        top_y = self.toolbar_height + self.xml_toolbar_height
        p.save(); p.setClipRect(0, top_y, self._w, self._h - top_y)

        self._draw_grid(p)
        self._draw_origin(p)

        data_drawn = False  # show "No file loaded" when nothing drawn

        if self.les_data:
            les_drawing.draw_points(self, p)
            les_drawing.draw_outline(self, p)
            les_drawing.draw_stepped_data(self, p)
            data_drawn = True

        if self.xml_drawings and self.current_xml_drawing_idx >= 0 and self.current_xml_step:
            xml_drawing.draw_xml(self, p)
            data_drawn = True
        p.restore()

        if self.selected_point is not None:
            self._draw_point_info(p)

        if not data_drawn:
            self._draw_no_file_loaded(p)

    # -------------------------- interaction ----------------------
    def wheelEvent(self, e):
        angle_delta = e.angleDelta().y()
        if angle_delta == 0:
            return
        mx = e.position().x(); my = e.position().y()
        wx, wy = self.screen_to_world(mx, my)
        factor = 1.1 if angle_delta > 0 else 1 / 1.1
        self.zoom_level *= factor
        self.pan_offset.setX(mx - wx * self.zoom_level)
        self.pan_offset.setY(my - wy * self.zoom_level)
        self.update()

    def mousePressEvent(self, e):
        """Handle mouse press events for panning with right button"""
        if e.button() in (Qt.MiddleButton, Qt.RightButton):
            self.dragging = True
            self.drag_button = e.button()
            self.drag_start = e.pos().toPoint()
            self.setCursor(Qt.ClosedHandCursor)  # Show grabbing hand cursor
            e.accept()  # Prevent event from being handled by other widgets
        elif e.button() == Qt.LeftButton:
            # Keep the existing left-click selection code
            if self.les_data:
                mx, my = e.position().x(), e.position().y()
                wx, wy = self.screen_to_world(mx, my)
                mind = float('inf');
                hit = None
                for p in self.les_data.points:
                    if not self.show_layers.get(p.layer, False):
                        continue
                    d = math.hypot(p.x - wx, p.y - wy)
                    if d < (5 / self.zoom_level) and d < mind:
                        mind = d;
                        hit = p
                self.selected_point = hit
                self.update()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self.dragging and self.drag_button in (Qt.MiddleButton, Qt.RightButton):
            mx, my = e.pos().x(), e.pos().y()
            dx = mx - self.drag_start.x()
            dy = my - self.drag_start.y()
            self.pan_offset += QPointF(dx, dy)
            self.drag_start = e.pos().toPoint()
            self.update()
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() in (Qt.MiddleButton, Qt.RightButton):
            self.dragging = False
            self.drag_button = None
        super().mouseReleaseEvent(e)
