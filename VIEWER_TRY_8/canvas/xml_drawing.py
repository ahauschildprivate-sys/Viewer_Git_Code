# -*- coding: utf-8 -*-
from __future__ import annotations
import math
from typing import List, Tuple
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QPolygonF

from xml_parser import Drawing, Step

OUTLINE_COLORS = [
    QColor(0, 255, 255), QColor(255, 215, 0), QColor(50, 205, 50), QColor(255, 99, 71),
    QColor(65, 105, 225), QColor(255, 105, 180), QColor(138, 43, 226), QColor(32, 178, 170)
]
STEP_TYPE_COLORS = {
    'panel': QColor(255, 215, 0),
    'set':   QColor(65, 105, 225),
    'pcs':   QColor(50, 205, 50),
    'kb':    QColor(255, 99, 71),
    'edit':  QColor(138, 43, 226),
}


def _normalize_deg(a: float) -> float:
    a = a % 360.0
    if a < 0:
        a += 360.0
    return a


def _angle_in_sweep(a: float, a0: float, a1: float, direction: str) -> bool:
    norm = _normalize_deg
    a, a0, a1 = norm(a), norm(a0), norm(a1)
    if direction.lower() == 'cw':
        a0, a1 = a1, a0
    span = (a1 - a0) % 360.0
    rel = (a - a0) % 360.0
    return rel <= span + 1e-9


def _angle_deg_math(cx: float, cy: float, x: float, y: float) -> float:
    return math.degrees(math.atan2(cy - y, x - cx)) % 360.0


def _xml_dir_to_math(d: str) -> str:
    d = (d or '').lower()
    return 'ccw' if d == 'cw' else 'cw'


def rotate_translate(x: float, y: float, angle_rad: float, off_x: float, off_y: float) -> Tuple[float, float]:
    xr = x * math.cos(angle_rad) - y * math.sin(angle_rad) + off_x
    yr = y * math.cos(angle_rad) + x * math.sin(angle_rad) + off_y
    return xr, yr


def arc_polyline_world_points(canvas, cx: float, cy: float, r: float,
                              start_deg_math: float, end_deg_math: float, direction: str) -> List[Tuple[float, float]]:
    if direction.lower() == 'ccw':
        delta_deg = (end_deg_math - start_deg_math) % 360.0
    else:
        delta_deg = -((start_deg_math - end_deg_math) % 360.0)
    arc_len_px = abs(math.radians(delta_deg)) * max(r * canvas.zoom_level, 1.0)
    num_segments = max(12, min(512, int(arc_len_px / 3)))
    if num_segments < 2:
        num_segments = 2
    step_rad = math.radians(delta_deg) / num_segments
    start_rad = math.radians(start_deg_math)
    pts: List[Tuple[float, float]] = []
    for i in range(num_segments + 1):
        a = start_rad + i * step_rad
        x = cx + r * math.cos(a)
        y = cy - r * math.sin(a)
        pts.append((x, y))
    return pts


def draw_xml(canvas, qp: QPainter):
    if not (canvas.xml_drawings and canvas.current_xml_drawing_idx >= 0 and canvas.current_xml_step):
        return
    drawing = canvas.xml_drawings[canvas.current_xml_drawing_idx]
    if canvas.current_xml_step not in drawing.steps:
        return
    step = drawing.steps[canvas.current_xml_step]
    step_color = STEP_TYPE_COLORS.get(step.type, OUTLINE_COLORS[0])

    # Draw board rectangle
    qp.setPen(QPen(QColor(80, 80, 100), 2))
    qp.setBrush(Qt.NoBrush)
    x0, y0 = canvas.world_to_screen(0, 0)
    qp.drawRect(QRectF(x0, y0, drawing.width * canvas.zoom_level, drawing.height * canvas.zoom_level))

    _draw_xml_step_recursive(canvas, qp, step, 0, -step.x, -step.y, 0)


def _draw_xml_step_recursive(canvas, qp: QPainter, step: Step, base_angle_deg: float, world_off_x: float, world_off_y: float,
                             color: QColor, depth=0):
    if depth > 50:
        return
    color = STEP_TYPE_COLORS.get(step.type, OUTLINE_COLORS[depth % len(OUTLINE_COLORS)])
    angle_rad = -base_angle_deg * math.pi / 180.0

    if canvas.show_xml_edges:
        qp.setPen(QPen(color, 2))
        for e in step.edges:
            if e.type == 'line':
                sx, sy = rotate_translate(e.xs, e.ys, angle_rad, world_off_x, world_off_y)
                ex, ey = rotate_translate(e.xe, e.ye, angle_rad, world_off_x, world_off_y)
                qp.drawLine(QPointF(*canvas.world_to_screen(sx, sy)), QPointF(*canvas.world_to_screen(ex, ey)))
            elif e.type == 'arc':
                sx, sy = rotate_translate(e.xs, e.ys, angle_rad, world_off_x, world_off_y)
                ex, ey = rotate_translate(e.xe, e.ye, angle_rad, world_off_x, world_off_y)
                cx, cy = rotate_translate(e.xc, e.yc, angle_rad, world_off_x, world_off_y)
                r = math.hypot(sx - cx, sy - cy) or max(getattr(e, 'radius', 0.0), 0.0)
                a0 = _angle_deg_math(cx, cy, sx, sy)
                a1 = _angle_deg_math(cx, cy, ex, ey)
                direction_math = _xml_dir_to_math(getattr(e, 'direction', 'ccw'))
                pts_world = arc_polyline_world_points(canvas, cx, cy, r, a0, a1, direction_math)
                if len(pts_world) > 1:
                    pts_screen = [QPointF(*canvas.world_to_screen(x, y)) for (x, y) in pts_world]
                    qp.drawPolyline(QPolygonF(pts_screen))

    if canvas.show_xml_barcodes:
        qp.setPen(QPen(QColor(200, 200, 200), 1))
        for layer in step.layers:
            for bc in layer.barcode_list:
                bx, by = rotate_translate(bc.x, bc.y, angle_rad, world_off_x, world_off_y)
                x, y = canvas.world_to_screen(bx, by)
                w = bc.width * canvas.zoom_level
                h = bc.height * canvas.zoom_level
                qp.drawRect(QRectF(x, y, w, h))
                if bc.content:
                    qp.setFont(canvas.info_font)
                    qp.setPen(QPen(QColor(150, 150, 150), 1))
                    qp.drawText(QPointF(x, y - 4), str(bc.content))

    if canvas.show_xml_repeats:
        for rpt in step.repeats:
            drawing = canvas.xml_drawings[canvas.current_xml_drawing_idx]
            if rpt.step in drawing.steps:
                sub = drawing.steps[rpt.step]
                rx, ry = rotate_translate(rpt.x, rpt.y, angle_rad, world_off_x, world_off_y)
                _draw_xml_step_recursive(canvas, qp, sub, base_angle_deg + rpt.angle, rx, ry, depth + 1)


def reset_xml_view(canvas):
    if not (canvas.xml_drawings and canvas.current_xml_drawing_idx >= 0):
        return
    drawing = canvas.xml_drawings[canvas.current_xml_drawing_idx]
    w = canvas._w
    h = canvas._h - (canvas.toolbar_height + canvas.xml_toolbar_height)
    if drawing.width <= 0 or drawing.height <= 0:
        canvas.zoom_level = 1.0
        canvas.pan_offset.setX((w - 400) / 2)
        canvas.pan_offset.setY((h - 300) / 2 + (canvas.toolbar_height + canvas.xml_toolbar_height))
        return
    canvas.zoom_level = min(w / drawing.width, h / drawing.height) * 0.8
    canvas.pan_offset.setX((w - drawing.width * canvas.zoom_level) / 2)
    canvas.pan_offset.setY((h - drawing.height * canvas.zoom_level) / 2 + (canvas.toolbar_height + canvas.xml_toolbar_height))
    canvas.update()


def _fit_world_bounds(canvas, minx: float, miny: float, maxx: float, maxy: float, padding: int = 50):
    if not (math.isfinite(minx) and math.isfinite(miny) and math.isfinite(maxx) and math.isfinite(maxy)):
        return
    bw, bh = maxx - minx, maxy - miny
    if bw <= 0 or bh <= 0:
        return
    avail_w = canvas._w - 2 * padding
    avail_h = canvas._h - (canvas.toolbar_height + canvas.xml_toolbar_height) - 2 * padding
    if avail_w <= 0 or avail_h <= 0:
        return
    zx = avail_w / bw
    zy = avail_h / bh
    canvas.zoom_level = min(zx, zy)
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    top_y = canvas.toolbar_height + canvas.xml_toolbar_height
    canvas.pan_offset.setX(canvas._w / 2 - cx * self.zoom_level)
    canvas.pan_offset.setY((top_y + (canvas._h - top_y) / 2) - cy * canvas.zoom_level)


def fit_step(canvas, include_repeats: bool):
    if not (canvas.xml_drawings and canvas.current_xml_drawing_idx >= 0 and canvas.current_xml_step):
        return
    drawing = canvas.xml_drawings[canvas.current_xml_drawing_idx]
    if canvas.current_xml_step not in drawing.steps:
        return
    step = drawing.steps[canvas.current_xml_step]

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
            if _angle_in_sweep(ang, a0, a1, direction):
                rad = math.radians(ang)
                pts.append((cx + r * math.cos(rad), cy - r * math.sin(rad)))
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        return (min(xs), min(ys), max(xs), max(ys))

    def compute_step_bounds(st: Step, base_angle_deg: float, off_x: float, off_y: float, depth=0):
        ang = -base_angle_deg * math.pi / 180.0
        if canvas.show_xml_edges:
            for e in st.edges:
                if e.type == 'line':
                    sx, sy = rotate_translate(e.xs, e.ys, ang, off_x, off_y)
                    ex, ey = rotate_translate(e.xe, e.ye, ang, off_x, off_y)
                    add_bounds((min(sx, ex), min(sy, ey), max(sx, ex), max(sy, ey)))
                elif e.type == 'arc':
                    sx, sy = rotate_translate(e.xs, e.ys, ang, off_x, off_y)
                    ex, ey = rotate_translate(e.xe, e.ye, ang, off_x, off_y)
                    cx, cy = rotate_translate(e.xc, e.yc, ang, off_x, off_y)
                    r = math.hypot(sx - cx, sy - cy) or max(getattr(e, 'radius', 0.0), 0.0)
                    a0 = _angle_deg_math(cx, cy, sx, sy)
                    a1 = _angle_deg_math(cx, cy, ex, ey)
                    dir_math = _xml_dir_to_math(getattr(e, 'direction', 'ccw'))
                    ab = arc_bounds(cx, cy, r, a0, a1, dir_math)
                    add_bounds(ab)
        if canvas.show_xml_barcodes:
            for layer in st.layers:
                for bc in layer.barcode_list:
                    bx, by = rotate_translate(bc.x, bc.y, ang, off_x, off_y)
                    add_bounds((bx, by, bx + bc.width, by + bc.height))
        if include_repeats and canvas.show_xml_repeats:
            for rpt in st.repeats:
                if rpt.step in drawing.steps:
                    sub = drawing.steps[rpt.step]
                    rx, ry = rotate_translate(rpt.x, rpt.y, ang, off_x, off_y)
                    compute_step_bounds(sub, base_angle_deg + rpt.angle, rx, ry, depth + 1)

    compute_step_bounds(step, 0, -step.x, -step.y, 0)
    if bounds[0] == float('inf'):
        reset_xml_view(canvas)
        return
    _fit_world_bounds(canvas, *bounds, padding=50)
    canvas.update()


def xml_info_text(drawing: Drawing) -> str:
    import os
    lines = [
        f"File: {os.path.basename(drawing.file_path)}",
        f"Job: {drawing.job}",
        f"Dimensions: {drawing.width} x {drawing.height}",
        f"Start Step: {drawing.start_step}",
        "Steps:",
    ]
    for step_name, step in drawing.steps.items():
        lines.append(f"  - {step_name} ({step.type}): {step.width} x {step.height} at ({step.x}, {step.y})")
    return "\n".join(lines)
