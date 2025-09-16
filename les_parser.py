# -*- coding: utf-8 -*-
"""
les_parser.py
Parses LES files into Python objects usable by viewer.py
"""
from __future__ import annotations
import re
import math
from les_parser_panel_image import assign_panel_image_names
from dataclasses import dataclass
from typing import List, Optional

# ---------- Data classes ----------
@dataclass(init=False)
class Aperture:
    from enum import Enum
    class ApertureMode(Enum):
        T = 0  # round
        O = 1  # rectangular
        K = 2  # annular
        U = 3  # special
        F = 4  # Tooling Hole

    index: int
    mode: 'Aperture.ApertureMode'
    radius: float
    inner_radius: float
    outer_radius: float
    width: float
    height: float
    angle: float

    def __init__(self, content: str = None):
        self.index = 0
        self.mode = Aperture.ApertureMode.T
        self.radius = 10.0
        self.inner_radius = 0.0
        self.outer_radius = 0.0
        self.width = 0.0
        self.height = 0.0
        self.angle = 0.0
        if content:
            head = content[0]
            try:
                self.mode = Aperture.ApertureMode[head]
            except KeyError:
                self.mode = Aperture.ApertureMode.T
            parts = content.split(':')
            self.index = int(parts[0][1:]) if len(parts[0]) > 1 else 0
            if self.mode == Aperture.ApertureMode.T:
                self.radius = float(parts[1]) / 2.0 if len(parts) > 1 else 10.0
            elif self.mode == Aperture.ApertureMode.O:
                if len(parts) >= 3:
                    self.width = float(parts[1])
                    self.height = float(parts[2])
                if len(parts) >= 4:
                    try:
                        self.angle = float(parts[3])
                    except ValueError:
                        self.angle = 0.0
            elif self.mode == Aperture.ApertureMode.K:
                if len(parts) >= 3:
                    self.inner_radius = float(parts[1]) / 2.0
                    self.outer_radius = float(parts[2]) / 2.0

@dataclass(init=False)
class Net:
    index: int
    image: int
    points: List['Point']
    is_plain: bool

    def __init__(self, content: str = None):
        self.points = []
        self.is_plain = False
        self.index = 0
        self.image = 1
        if content:
            if 'P' in content:
                self.is_plain = True
                content = content.replace('P', '')
            parts = content.split('C')
            idx_part = parts[0].replace('@', '').strip()
            digits = ''
            for ch in idx_part:
                if ch.isdigit():
                    digits += ch
                else:
                    break
            self.index = int(digits) if digits else 0
            self.image = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1

@dataclass(init=False)
class LesStep:
    amount: int
    operations: str
    offset_x: float
    offset_y: float
    distance_x: float
    distance_y: float
    image: int
    tooltip: str

    def __init__(self, content: str):
        self.amount = 0
        self.operations = ""
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.distance_x = 0.0
        self.distance_y = 0.0
        self.image = 1
        self.tooltip = content
        parts = content.split(':')
        if len(parts) < 5:
            return
        try:
            self.amount = int(parts[1])
        except Exception:
            self.amount = 0
        self.operations = parts[2]
        off = parts[3].split(',')
        if len(off) >= 2:
            self.offset_x = float(off[0])
            self.offset_y = float(off[1])
        dist = parts[4].split(',')
        if len(dist) >= 2:
            self.distance_x = float(dist[0])
            self.distance_y = float(dist[1])
        if len(parts) > 5 and 'I' in parts[5]:
            try:
                self.image = int(parts[5].replace('I', ''))
            except Exception:
                self.image = 1

    def scale_values(self, s: float):
        self.offset_x *= s
        self.offset_y *= s
        self.distance_x *= s
        self.distance_y *= s

    def apply_transformation(self, point, step_index):
        x, y = point.x, point.y
        layer = point.layer
        for op in self.operations:
            if op == 'D':
                x, y = y, -x
            elif op == 'X':
                y = -y
                if hasattr(point, 'layer') and hasattr(point, 'count_of_layer'):
                    layer = (1 - point.layer) + point.count_of_layer
            elif op == 'Y':
                x = -x
                if hasattr(point, 'layer') and hasattr(point, 'count_of_layer'):
                    layer = (1 - point.layer) + point.count_of_layer
        x += self.offset_x + step_index * self.distance_x
        y += self.offset_y + step_index * self.distance_y
        return x, y, layer

@dataclass
class ViewImage:
    min_x: float = 0.0
    min_y: float = 0.0
    max_x: float = 0.0
    max_y: float = 0.0
    initial: bool = True

    @property
    def width(self) -> float:
        return max(self.max_x - self.min_x, 100)

    @property
    def height(self) -> float:
        return max(self.max_y - self.min_y, 100)

    def set_size(self, point: 'Point'):
        if self.initial:
            self.min_x = self.max_x = point.x
            self.min_y = self.max_y = point.y
            self.initial = False
        else:
            self.min_x = min(point.x, self.min_x)
            self.max_x = max(point.x, self.max_x)
            self.min_y = min(point.y, self.min_y)
            self.max_y = max(point.y, self.max_y)

@dataclass(init=False)
class Point:
    from enum import Enum
    class PointType(Enum):
        NONE = 0
        S = 1
        D = 2
        B = 3
        P = 4
        E = 5

    class PointStyle(Enum):
        NORMAL = 0
        GLOBAL = 1
        LOCAL = 2

    original: str
    identifier: int
    x: float
    y: float
    type: 'Point.PointType'
    style: 'Point.PointStyle'
    aperture: Aperture
    index_of_map: list
    content: str
    net: Net
    layer: int
    count_of_layer: int
    fill_color: tuple
    background_color: tuple
    default_opacity: float
    opacity: float
    logic_mode: bool
    is_enable: bool
    is_test: bool
    is_selected: bool
    is_visible: bool
    image: int

    def __init__(self, content: str = None, count_of_layer: int = 1, apertures: List[Aperture] = None,
                 net: Net = None, style: 'Point.PointStyle' = None):
        self.original = content or ""
        self.identifier = 0
        self.x = 0.0
        self.y = 0.0
        self.type = Point.PointType.NONE
        self.style = style or Point.PointStyle.NORMAL
        self.aperture = Aperture()
        self.index_of_map = []
        self.content = ""
        self.net = net or Net()
        self.layer = 1
        self.count_of_layer = count_of_layer
        self.fill_color = (255, 215, 0)
        self.background_color = (0, 100, 0)
        self.default_opacity = 0.6
        self.opacity = 0.6
        self.logic_mode = False
        self.is_enable = True
        self.is_test = True
        self.is_selected = False
        self.is_visible = True
        self.image = 1
        apertures = apertures or []
        if content:
            if style is not None and style in (Point.PointStyle.GLOBAL, Point.PointStyle.LOCAL):
                self._init_tooling_hole(content, apertures, style)
            else:
                self._init_regular_point(content, count_of_layer, apertures, net)

    def _init_tooling_hole(self, content: str, apertures: List[Aperture], style: 'Point.PointStyle'):
        self.original = content
        lead = self.original.split(',', 1)[0].strip() if self.original else ''
        if lead == 'F':
            self.aperture.mode = Aperture.ApertureMode.F
        else:
            self.aperture.mode = Aperture.ApertureMode.K
        clean = (content.replace('[', '').replace(']', '').replace('*', '').replace('/', '')
                 .replace('~', '').replace('&M', '').replace('&S', '')
                 .replace(' ', '').replace(',', ''))
        i_parts = clean.split('I')
        self.content = i_parts[0]
        self.style = style
        self.image = 0 if style == Point.PointStyle.GLOBAL else (
            int(i_parts[1]) if len(i_parts) > 1 and i_parts[1].isdigit() else 1)
        self.net = Net()
        self.is_test = False
        self.is_enable = False
        self.layer = 1
        self.type = Point.PointType.NONE
        if 'X' in self.content and 'Y' in self.content:
            x_start = self.content.find('X') + 1
            x_end = self.content.find('Y')
            try:
                self.x = float(self.content[x_start:x_end])
            except ValueError:
                self.x = 0.0
            y_start = x_end + 1
            t_pos = self.content.find('T', y_start)
            if t_pos > 0:
                try:
                    self.y = float(self.content[y_start:t_pos])
                except ValueError:
                    self.y = 0.0
                try:
                    ap_idx = int(self.content[t_pos + 1:])
                except ValueError:
                    ap_idx = None
                if ap_idx is not None:
                    for ap in apertures:
                        if ap.index == ap_idx:
                            if self.aperture.mode == Aperture.ApertureMode.F:
                                self.aperture.radius = getattr(ap, 'radius', ap.outer_radius or 10.0)
                            else:
                                self.aperture.radius = ap.outer_radius or ap.radius
                            break
            else:
                try:
                    self.y = float(self.content[y_start:])
                except ValueError:
                    self.y = 0.0
                self.aperture.radius = self.aperture.radius or 10.0
        else:
            self.x = self.y = 0.0
            self.aperture.radius = 10.0
        self.aperture.inner_radius = getattr(self.aperture, 'inner_radius', self.aperture.radius)
        self.aperture.outer_radius = getattr(self.aperture, 'outer_radius', self.aperture.radius + 4)
        self.fill_color = (148, 0, 211)  # tooling purple
        self.background_color = (0, 100, 0)

    def _init_regular_point(self, content: str, count_of_layer: int, apertures: List[Aperture], net: Net):
        self.original = content
        self.style = Point.PointStyle.NORMAL
        self.net = net or Net()
        self.image = self.net.image
        self.count_of_layer = count_of_layer
        self.content = (content.replace('[', '').replace(']', '').replace('*', '').replace('/', '')
                        .replace('~', '').replace('&M', '').replace('&S', '')
                        .replace(' ', '').replace(',', ''))
        if self.content.startswith('I') and 'X' in self.content:
            id_part = self.content.split('X')[0].lstrip('I')
            if id_part:
                try:
                    self.identifier = int(id_part)
                except Exception:
                    self.identifier = 0
        if 'X' in self.content and 'Y' in self.content:
            x_part = self.content.split('Y')[0].split('X')
            if len(x_part) > 1:
                try:
                    self.x = float(x_part[1])
                except Exception:
                    self.x = 0.0
            y_part = self.content.split('A')[0].split('Y')
            if len(y_part) > 1:
                try:
                    self.y = float(y_part[1])
                except Exception:
                    self.y = 0.0
            if 'A' in self.content:
                a_parts = self.content.split('A')
                if len(a_parts) > 1:
                    ap_part = a_parts[1].split('Z')[0].split('V')[0].split('M')[0]
                    self.logic_mode = 'L' in ap_part
                    try:
                        if self.logic_mode:
                            ap_index = int(ap_part[3:])
                            type_char = ap_part[1]
                        else:
                            ap_index = int(ap_part[2:])
                            type_char = ap_part[0]
                        for ap in apertures:
                            if ap.index == ap_index:
                                self.aperture = ap
                                break
                        try:
                            self.type = Point.PointType[type_char]
                        except Exception:
                            self.type = Point.PointType.NONE
                    except Exception:
                        pass
            if 'V' in self.content:
                v_parts = self.content.split('V')
                if len(v_parts) > 1:
                    layer_part = v_parts[1].split('N')[0] if 'N' in v_parts[1] else v_parts[1]
                    if layer_part:
                        try:
                            self.layer = int(layer_part)
                        except Exception:
                            self.layer = 1
            self.is_enable = (self.layer == 1 or self.layer == count_of_layer)
            self.is_test = ('*' not in content)
            # Colors by layer/test
            if self.layer == 1:
                self.fill_color = (255, 215, 0) if self.is_test else (184, 134, 11)
            elif self.layer == count_of_layer and count_of_layer > 1:
                self.fill_color = (0, 255, 0) if self.is_test else (0, 128, 0)
            else:
                self.fill_color = (0, 255, 255) if self.is_test else (70, 130, 180)
            self.background_color = (0, 100, 0)

class Les:
    def __init__(self, file_path: str = None):
        self.test = ""
        self.count_of_layer = 0
        self.unit = ""
        self.scale = 1.0
        self.nets: List[Net] = []
        self.points: List[Point] = []
        self.apertures: List[Aperture] = []
        self.steps: List[LesStep] = []
        self.content: List[str] = []
        self.outline_points: List[List[tuple]] = []
        self.images: List[Optional[ViewImage]] = [None, ViewImage()]  # 1-based images
        # Regex
        self.layer_pattern = re.compile(r"^L\s*(\d+)\s*\*?$")
        self.aperture_pattern = re.compile(r"^[FTOKU][0-9]+:")
        self.step_pattern = re.compile(r"^STEP:.*$")
        self.tooling_pattern = re.compile(r"^F,X.*$")
        self.outline_pattern = re.compile(r"^K,X-?\d+Y-?\d+(?:,)?(?:T\d+)?(?:,)?$")
        self.point_pattern = re.compile(r"^I\d+X-?\d+Y-?\d+A.+$")
        if file_path:
            self.load_file(file_path)

    def _apply_scale_to_aperture(self, ap: Aperture):
        ap.radius *= self.scale
        ap.inner_radius *= self.scale
        ap.outer_radius *= self.scale
        ap.width *= self.scale
        ap.height *= self.scale

    def load_file(self, file_path: str):
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            self.content = [line.rstrip('\n') for line in f]
        index_of_step = float('inf')
        current_outline_segment: List[tuple] = []
        for i, raw in enumerate(self.content):
            line = raw.strip()
            if not line:
                continue
            if "#ATFH" in line:
                parts = line.split(':')
                if len(parts) > 1:
                    self.test = parts[1]
                continue
            m_layer = self.layer_pattern.match(line)
            if m_layer:
                self.count_of_layer = int(m_layer.group(1))
                if len(self.images) < 2:
                    self.images = [None, ViewImage()]
                continue
            if line.startswith('UNIT'):
                parts = line.split(':')
                if len(parts) >= 3:
                    self.unit = parts[1].strip().upper()
                    try:
                        res = float(parts[2])
                    except Exception:
                        res = 1.0
                    if self.unit == 'INCH':
                        self.scale = 25.4 / res if res else 1.0
                    elif self.unit == 'MM':
                        self.scale = 1.0 / res if res else 1.0
                    else:
                        self.scale = 1.0
                continue
            # Outline
            if self.outline_pattern.match(line):
                has_comma = line.endswith(',')
                work = line[2:].rstrip(',')
                coord = work.split('T', 1)[0]
                xs, ys = coord.split('Y', 1)
                try:
                    x = float(xs.replace('X', '')) * self.scale
                    y = float(ys) * self.scale
                except Exception:
                    x = y = 0.0
                current_outline_segment.append((x, y))
                if not has_comma and current_outline_segment:
                    self.outline_points.append(current_outline_segment)
                    current_outline_segment = []
                continue
            # Tooling
            if self.tooling_pattern.match(line):
                style = Point.PointStyle.GLOBAL if i < index_of_step else Point.PointStyle.LOCAL
                p = Point(line, apertures=self.apertures, style=style)
                p.x *= self.scale
                p.y *= self.scale
                self.points.append(p)
                continue
            if self.aperture_pattern.match(line):
                ap = Aperture(line)
                self._apply_scale_to_aperture(ap)
                self.apertures.append(ap)
                continue
            if self.step_pattern.match(line):
                st = LesStep(line)
                st.scale_values(self.scale)
                self.steps.append(st)
                index_of_step = i
                continue
            if line.startswith('@') and '!' not in line:
                net = Net(line)
                self.nets.append(net)
                while net.image > len(self.images) - 1:
                    self.images.append(ViewImage())
                continue
            stripped = line.strip('[]').strip()
            if self.point_pattern.match(stripped):
                net = self.nets[-1] if self.nets else Net()
                pt = Point(stripped, self.count_of_layer, self.apertures, net)
                pt.x *= self.scale
                pt.y *= self.scale
                self.points.append(pt)
                if self.nets:
                    self.nets[-1].points.append(pt)
                while pt.image > len(self.images) - 1:
                    self.images.append(ViewImage())
                if pt.image < len(self.images) and self.images[pt.image]:
                    self.images[pt.image].set_size(pt)
                continue
        if current_outline_segment:
            self.outline_points.append(current_outline_segment)
            assign_panel_image_names(self.steps, self.points)  # Assign Panel/Image names
