# -*- coding: utf-8 -*-
"""
viewer_canvas.py
Public entrypoint that keeps the original import path stable.

Usage elsewhere remains:
    from canvas.viewer_canvas import ViewerCanvas
"""
from __future__ import annotations

import math
from typing import List, Optional, Tuple, Dict

from PySide6.QtCore import Qt, QPoint, QPointF, QSize
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QCursor
from PySide6.QtWidgets import QWidget, QMessageBox, QSizePolicy

from .viewer_canvas_core import ViewerCanvasCore
from .viewer_canvas_view import CanvasPaintingMixin


class ViewerCanvas(CanvasPaintingMixin, ViewerCanvasCore):
    """Concrete canvas composed from core logic and view mixin."""

    def __init__(self, parent=None):
        # Initialize both parent classes
        super().__init__(parent)

        # Set context menu policy to prevent interference with right-click panning
        self.setContextMenuPolicy(Qt.NoContextMenu)

        # Initialize panning variables
        self.dragging = False
        self.drag_button = None
        self.drag_start = QPoint()
        self.pan_offset = QPointF(0, 0)

    def mousePressEvent(self, e):
        """Handle mouse press events for panning with right button"""
        if e.button() in (Qt.MiddleButton, Qt.RightButton):
            self.dragging = True
            self.drag_button = e.button()
            self.drag_start = e.pos()
            self.setCursor(Qt.ClosedHandCursor)  # Show grabbing hand cursor
            e.accept()  # Prevent event from being handled by other widgets
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        """Handle mouse move events for panning"""
        if self.dragging and self.drag_button in (Qt.MiddleButton, Qt.RightButton):
            mx, my = e.pos().x(), e.pos().y()
            dx = mx - self.drag_start.x()
            dy = my - self.drag_start.y()
            self.pan_offset += QPointF(dx, dy)
            self.drag_start = e.pos()
            self.update()
            e.accept()
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        """Handle mouse release events"""
        if e.button() in (Qt.MiddleButton, Qt.RightButton):
            self.dragging = False
            self.drag_button = None
            self.setCursor(Qt.ArrowCursor)  # Reset to normal cursor
            e.accept()
        else:
            super().mouseReleaseEvent(e)

    def wheelEvent(self, e):
        """Handle zoom with mouse wheel"""
        angle_delta = e.angleDelta().y()
        if angle_delta == 0:
            return
        mx = e.position().x()
        my = e.position().y()
        wx, wy = self.screen_to_world(mx, my)
        factor = 1.1 if angle_delta > 0 else 1 / 1.1
        self.zoom_level *= factor
        self.pan_offset.setX(mx - wx * self.zoom_level)
        self.pan_offset.setY(my - wy * self.zoom_level)
        self.update()
        e.accept()

    def screen_to_world(self, sx: float, sy: float) -> Tuple[float, float]:
        """Convert screen coordinates to world coordinates"""
        wx = (sx - self.pan_offset.x()) / self.zoom_level
        wy = (sy - self.pan_offset.y()) / self.zoom_level
        return wx, wy

    def world_to_screen(self, wx: float, wy: float) -> Tuple[float, float]:
        """Convert world coordinates to screen coordinates"""
        sx = wx * self.zoom_level + self.pan_offset.x()
        sy = wy * self.zoom_level + self.pan_offset.y()
        return sx, sy