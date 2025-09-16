# -*- coding: utf-8 -*-
"""
xml_parser.py
Parses XML eMAP drawings into Python objects usable by viewer.py
"""
from __future__ import annotations
import os
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional

class Edge:
    def __init__(self, edge_element):
        self.id = edge_element.get('id')
        self.type = edge_element.get('type')  # 'line' or 'arc'
        self.xs = float(edge_element.get('xs', 0))
        self.ys = float(edge_element.get('ys', 0))
        self.xe = float(edge_element.get('xe', 0))
        self.ye = float(edge_element.get('ye', 0))
        self.xc = float(edge_element.get('xc', 0))
        self.yc = float(edge_element.get('yc', 0))
        self.radius = float(edge_element.get('radius', 0))
        self.direction = edge_element.get('direction', 'cw')

class Repeat:
    def __init__(self, repeat_element):
        self.id = repeat_element.get('id')
        self.pos_num = repeat_element.get('pos_num')  # e.g., A3
        self.step = repeat_element.get('step')
        self.x = float(repeat_element.get('x', 0))
        self.y = float(repeat_element.get('y', 0))
        self.angle = float(repeat_element.get('angle', 0))
        self.number = repeat_element.get('number', '')

class Layer:
    def __init__(self, layer_element):
        self.name = layer_element.get('name')
        self.barcode_list: List[Barcode] = []  # type: ignore[name-defined]
        for barcode_element in layer_element.findall('barcode'):
            self.barcode_list.append(Barcode(barcode_element))  # type: ignore[name-defined]

class Barcode:
    def __init__(self, barcode_element):
        self.num = barcode_element.get('num')
        self.layercode = barcode_element.get('layercode')
        self.layerface = barcode_element.get('layerface')
        self.content = barcode_element.get('content')
        self.polarity = barcode_element.get('polarity')
        self.id = barcode_element.get('id')
        self.x = float(barcode_element.get('x', 0))
        self.y = float(barcode_element.get('y', 0))
        self.width = float(barcode_element.get('width', 0))
        self.height = float(barcode_element.get('height', 0))

class Step:
    def __init__(self, step_element):
        self.name = step_element.get('name')
        self.type = step_element.get('type')
        self.x = float(step_element.get('x', 0))
        self.y = float(step_element.get('y', 0))
        self.width = float(step_element.get('width', 0))
        self.height = float(step_element.get('height', 0))
        self.edges: List[Edge] = []
        self.repeats: List[Repeat] = []
        self.layers: List[Layer] = []
        for edge_element in step_element.findall('edge'):
            self.edges.append(Edge(edge_element))
        for repeat_element in step_element.findall('repeat'):
            self.repeats.append(Repeat(repeat_element))
        for layer_element in step_element.findall('layer'):
            self.layers.append(Layer(layer_element))

class Drawing:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.job: str = ""
        self.width: float = 0
        self.height: float = 0
        self.start_step: Optional[str] = ""
        self.steps: Dict[str, Step] = {}
        self.parse_xml(file_path)

    def parse_xml(self, file_path: str):
        tree = ET.parse(file_path)
        root = tree.getroot()
        self.job = root.get('job') or os.path.basename(file_path)
        self.width = float(root.get('width', 0))
        self.height = float(root.get('height', 0))
        start_elem = root.find('start')
        if start_elem is not None:
            self.start_step = start_elem.get('step')
        for step_element in root.findall('step'):
            st = Step(step_element)
            self.steps[st.name] = st
        if not self.start_step and self.steps:
            self.start_step = next(iter(self.steps.keys()))
