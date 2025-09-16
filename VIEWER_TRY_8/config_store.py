# -*- coding: utf-8 -*-
"""
config_store.py
Simple INI-backed persistence for last session and view options.
"""
from __future__ import annotations
import json
from pathlib import Path
from configparser import ConfigParser


class ConfigStore:
    def __init__(self, path: str | None = None):
        # Default location: ~/.les_xml_viewer/config.ini
        default_path = Path.home() / ".les_xml_viewer" / "config.ini"
        self.path = Path(path) if path else default_path
        self.cfg = ConfigParser()
        self._load_or_init()

    # ---------- Core I/O ----------
    def _load_or_init(self):
        if self.path.exists():
            self.cfg.read(self.path, encoding="utf-8")
        else:
            self.cfg["General"] = {"ask_on_start": "true"}
            self.cfg["Recent"] = {"les_file": "", "xml_files": "[]"}
            self.cfg["Window"] = {
                "x": "100", "y": "100", "width": "1200", "height": "800", "maximized": "false"
            }
            self.cfg["View"] = {
                "layer_mode": "both",
                "show_steps": "false",
                "show_outline": "false",
                "show_xml_edges": "true",
                "show_xml_repeats": "true",
                "show_xml_barcodes": "true",
            }
            self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            self.cfg.write(f)

    # ---------- General ----------
    def get_ask_on_start(self) -> bool:
        return self.cfg.getboolean("General", "ask_on_start", fallback=True)

    def set_ask_on_start(self, value: bool):
        self.cfg.setdefault("General", {})
        self.cfg["General"]["ask_on_start"] = "true" if value else "false"
        self.save()

    # ---------- Recent files ----------
    def set_recent_files(self, les_file: str | None, xml_files: list[str]):
        self.cfg.setdefault("Recent", {})
        self.cfg["Recent"]["les_file"] = les_file or ""
        self.cfg["Recent"]["xml_files"] = json.dumps(xml_files or [])
        self.save()

    def get_recent_files(self) -> tuple[str | None, list[str]]:
        les_file = self.cfg.get("Recent", "les_file", fallback="").strip() or None
        try:
            xml_files = json.loads(self.cfg.get("Recent", "xml_files", fallback="[]"))
            if not isinstance(xml_files, list):
                xml_files = []
        except Exception:
            xml_files = []
        return les_file, xml_files

    # ---------- Window ----------
    def set_window(self, x: int, y: int, w: int, h: int, maximized: bool):
        self.cfg.setdefault("Window", {})
        self.cfg["Window"]["x"] = str(int(x))
        self.cfg["Window"]["y"] = str(int(y))
        self.cfg["Window"]["width"] = str(int(w))
        self.cfg["Window"]["height"] = str(int(h))
        self.cfg["Window"]["maximized"] = "true" if maximized else "false"
        self.save()

    def get_window(self) -> tuple[int, int, int, int, bool]:
        x = self.cfg.getint("Window", "x", fallback=100)
        y = self.cfg.getint("Window", "y", fallback=100)
        w = self.cfg.getint("Window", "width", fallback=1200)
        h = self.cfg.getint("Window", "height", fallback=800)
        maximized = self.cfg.getboolean("Window", "maximized", fallback=False)
        return x, y, w, h, maximized

    # ---------- View options ----------
    def set_view_options(
        self,
        layer_mode: str,
        show_steps: bool,
        show_outline: bool,
        show_xml_edges: bool,
        show_xml_repeats: bool,
        show_xml_barcodes: bool,
    ):
        self.cfg.setdefault("View", {})
        v = self.cfg["View"]
        v["layer_mode"] = layer_mode
        v["show_steps"] = "true" if show_steps else "false"
        v["show_outline"] = "true" if show_outline else "false"
        v["show_xml_edges"] = "true" if show_xml_edges else "false"
        v["show_xml_repeats"] = "true" if show_xml_repeats else "false"
        v["show_xml_barcodes"] = "true" if show_xml_barcodes else "false"
        self.save()

    def get_view_options(self) -> dict:
        v = self.cfg["View"]
        return {
            "layer_mode": v.get("layer_mode", "both"),
            "show_steps": v.get("show_steps", "false").lower() == "true",
            "show_outline": v.get("show_outline", "false").lower() == "true",
            "show_xml_edges": v.get("show_xml_edges", "true").lower() == "true",
            "show_xml_repeats": v.get("show_xml_repeats", "true").lower() == "true",
            "show_xml_barcodes": v.get("show_xml_barcodes", "true").lower() == "true",
        }
