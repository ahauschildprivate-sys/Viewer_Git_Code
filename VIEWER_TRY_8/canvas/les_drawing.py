# -*- coding: utf-8 -*-
from __future__ import annotations
import math
from typing import List
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QPolygonF
from les_parser import Point

# LES-specific drawing helpers used by ViewerCanvas

LES_STEP_COLORS = [
    QColor(255, 0, 0), QColor(0, 255, 0), QColor(0, 0, 255),
    QColor(255, 255, 0), QColor(255, 0, 255), QColor(0, 255, 255)
]


def draw_outline(canvas, qp: QPainter):
    ld = canvas.les_data
    if not canvas.show_outline or not ld or not ld.outline_points:
        return
    qp.setPen(QPen(canvas.outline_color, 2))
    for seg in ld.outline_points:
        if len(seg) < 2:
            continue
        pts = [QPointF(*canvas.world_to_screen(x, y)) for x, y in seg]
        qp.drawPolyline(QPolygonF(pts))


def _draw_point(canvas, qp: QPainter, point: Point, is_stepped: bool = False):
    # Respect layer visibility for BASE points
    if not is_stepped and not canvas.show_layers.get(point.layer, False):
        return

    sx, sy = canvas.world_to_screen(point.x, point.y)
    if sx < -100 or sx > canvas._w + 100 or sy < -100 or sy > canvas._h + 100:
        return

    color = canvas.step_color if is_stepped else QColor(*point.fill_color)
    mode = point.aperture.mode.name

    if mode == 'T':
        r = max(0.5, point.aperture.radius * canvas.zoom_level)
        qp.setPen(Qt.NoPen)
        qp.setBrush(QBrush(color))
        qp.drawEllipse(QPointF(sx, sy), r, r)
        if canvas.selected_point is point and not is_stepped:
            qp.setBrush(Qt.NoBrush)
            qp.setPen(QPen(canvas.highlight_color, 2))
            qp.drawEllipse(QPointF(sx, sy), r + 2, r + 2)

    elif mode == 'O':
        w = max(1.0, point.aperture.width * canvas.zoom_level)
        h = max(1.0, point.aperture.height * canvas.zoom_level)
        ang = getattr(point.aperture, 'angle', 0.0)
        qp.save();
        qp.translate(sx, sy);
        qp.rotate(-ang)
        qp.setPen(Qt.NoPen);
        qp.setBrush(QBrush(color))
        qp.drawRect(QRectF(-w / 2, -h / 2, w, h))
        qp.restore()
        if canvas.selected_point is point and not is_stepped:
            qp.setPen(QPen(canvas.highlight_color, 2))
            qp.setBrush(Qt.NoBrush)
            qp.drawEllipse(QPointF(sx, sy), max(w, h) / 2 + 2, max(w, h) / 2 + 2)

    elif mode == 'K':
        orad = max(0.5, point.aperture.outer_radius * canvas.zoom_level)
        irad = max(0.5, point.aperture.inner_radius * canvas.zoom_level)
        qp.setPen(Qt.NoPen);
        qp.setBrush(QBrush(color))
        qp.drawEllipse(QPointF(sx, sy), orad, orad)
        qp.setBrush(QBrush(QColor(*point.background_color)))
        qp.drawEllipse(QPointF(sx, sy), irad, irad)

    elif mode == 'F':
        r = max(0.5, point.aperture.radius * canvas.zoom_level)
        qp.setPen(Qt.NoPen);
        qp.setBrush(QBrush(color))
        qp.drawEllipse(QPointF(sx, sy), r, r)
        if canvas.selected_point is point and not is_stepped:
            qp.setBrush(Qt.NoBrush)
            qp.setPen(QPen(canvas.highlight_color, 2))
            qp.drawEllipse(QPointF(sx, sy), r + 2, r + 2)


def draw_points(canvas, qp: QPainter):
    ld = canvas.les_data
    if not ld:
        return
    for pt in ld.points:
        _draw_point(canvas, qp, pt)


def _apply_ops_to_angle(angle_cw_deg: float, operations: str) -> float:
    a = angle_cw_deg % 360.0
    for op in operations:
        if op == 'D':
            a = (a + 90.0) % 360.0
        elif op == 'X':
            a = (360.0 - a) % 360.0
        elif op == 'Y':
            a = (180.0 - a) % 360.0
    return a


def _draw_point_with_color(
        canvas, qp: QPainter, x: float, y: float, point: Point, color: QColor,
        angle_override: float | None = None
):
    sx, sy = canvas.world_to_screen(x, y)
    if sx < -100 or sx > canvas._w + 100 or sy < -100 or sy > canvas._h + 100:
        return

    mode = point.aperture.mode.name

    if mode == 'T':
        r = max(0.5, point.aperture.radius * canvas.zoom_level)
        qp.setPen(Qt.NoPen);
        qp.setBrush(QBrush(color))
        qp.drawEllipse(QPointF(sx, sy), r, r)

    elif mode == 'O':
        w = max(1.0, point.aperture.width * canvas.zoom_level)
        h = max(1.0, point.aperture.height * canvas.zoom_level)
        ang = angle_override if angle_override is not None else getattr(point.aperture, 'angle', 0.0)
        qp.save();
        qp.translate(sx, sy);
        qp.rotate(-ang)
        qp.setPen(Qt.NoPen);
        qp.setBrush(QBrush(color))
        qp.drawRect(QRectF(-w / 2, -h / 2, w, h))
        qp.restore()

    elif mode == 'K':
        orad = max(0.5, point.aperture.outer_radius * canvas.zoom_level)
        irad = max(0.5, point.aperture.inner_radius * canvas.zoom_level)
        qp.setPen(Qt.NoPen);
        qp.setBrush(QBrush(color))
        qp.drawEllipse(QPointF(sx, sy), orad, orad)
        qp.setBrush(QBrush(QColor(*point.background_color)))
        qp.drawEllipse(QPointF(sx, sy), irad, irad)

    elif mode == 'F':
        r = max(0.5, point.aperture.radius * canvas.zoom_level)
        qp.setPen(Qt.NoPen);
        qp.setBrush(QBrush(color))
        qp.drawEllipse(QPointF(sx, sy), r, r)


def draw_stepped_data(canvas, qp: QPainter):
    """
    Draw LES step replications.

    Behavior:
      - Stepped points RESPECT layer mode (Top/Bot/Both).
      - Base points (drawn in draw_points) also respect layer mode.
      - Outline is independent.
      - No auto-zoom is triggered externally; this function only draws.
      - Steps are only applied to points with matching image numbers.
    """
    ld = canvas.les_data
    if not canvas.show_steps or not ld or not ld.steps:
        return

    for s_idx, st in enumerate(ld.steps):
        c = LES_STEP_COLORS[s_idx % len(LES_STEP_COLORS)]
        qp.setPen(QPen(c, 2))

        for i in range(st.amount):
            # Step instance marker
            cx = st.offset_x + i * st.distance_x
            cy = st.offset_y + i * st.distance_y
            tx, ty = cx, cy
            for op in st.operations:
                if op == 'D':
                    tx, ty = ty, -tx
                elif op == 'X':
                    ty = -ty
                elif op == 'Y':
                    tx = -tx
            sx, sy = canvas.world_to_screen(tx, ty)
            # qp.setPen(QPen(c, 2)); # Dont Draw the Step Instance marker
            # qp.setBrush(QBrush(c))
            # qp.drawEllipse(QPointF(sx, sy), 5, 5)

            # Draw stepped points that pass current layer visibility AND image matching
            for pt in ld.points:
                # Skip points that don't match the step's image
                if pt.image != st.image:
                    continue

                if not canvas.show_layers.get(pt.layer, False):
                    continue
                x, y, layer = st.apply_transformation(pt, i)
                if not canvas.show_layers.get(layer, False):
                    continue

                angle_override = None
                if pt.aperture.mode.name == 'O':
                    base_ang = getattr(pt.aperture, 'angle', 0.0)
                    angle_override = _apply_ops_to_angle(base_ang, st.operations)

                _draw_point_with_color(canvas, qp, x, y, pt, c, angle_override)


def auto_zoom(canvas):
    ld = canvas.les_data
    if not ld:
        return

    xs: List[float] = []
    ys: List[float] = []

    # Consider only visible BASE points for layer mode in fit logic
    visible = [p for p in ld.points if canvas.show_layers.get(p.layer, False)]
    for p in visible:
        xs.append(p.x);
        ys.append(p.y)

    if canvas.show_steps:
        for st in ld.steps:
            for i in range(st.amount):
                for p in visible:
                    # Skip points that don't match the step's image
                    if p.image != st.image:
                        continue
                    x, y, _ = st.apply_transformation(p, i)
                    xs.append(x);
                    ys.append(y)

    if (canvas.show_outline and ld.outline_points) or not xs:
        for seg in ld.outline_points:
            for (x, y) in seg:
                xs.append(x);
                ys.append(y)

    if not xs:
        return

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    bw, bh = max_x - min_x, max_y - min_y
    if bw == 0 or bh == 0:
        return

    zx = (canvas._w - 100) / bw
    zy = (canvas._h - 100 - (canvas.toolbar_height + canvas.xml_toolbar_height)) / bh
    canvas.zoom_level = min(zx, zy) * 0.9

    cx, cy = (min_x + max_x) / 2, (min_y + max_y) / 2
    top_y = canvas.toolbar_height + canvas.xml_toolbar_height
    canvas.pan_offset.setX(canvas._w / 2 - cx * canvas.zoom_level)
    canvas.pan_offset.setY((top_y + (canvas._h - top_y) / 2) - cy * canvas.zoom_level)
    canvas.update()