# -*- coding: utf-8 -*-
from __future__ import annotations
import os
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QToolBar, QMessageBox, QDockWidget, QWidget
)

from canvas.viewer_canvas import ViewerCanvas
from canvas.side_panel import SidePanel
from config import ConfigManager


class MainWindow(QMainWindow):
    """Main window with SidePanel-based view controls."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle('LES and XML Utility V. 20250914 by Andreas Hauschild aka Fei Long')

        # Config manager
        self.config = ConfigManager()

        # Restore window geometry if available
        geometry, state = self.config.get_window_geometry()
        if geometry and not geometry.isEmpty() and state and not state.isEmpty():
            self.restoreGeometry(geometry)
            self.restoreState(state)
        else:
            # Default size if no saved geometry
            self.resize(1200, 800)

        # ---- Central canvas -------------------------------------------------
        self.canvas = ViewerCanvas(self)
        self.setCentralWidget(self.canvas)

        # ---- Side Panel (left dock) ----------------------------------------
        self.side_panel = SidePanel(self)
        self._dock_panel = QDockWidget('', self)
        self._dock_panel.setObjectName("SidePanelDock")
        self._dock_panel.setWidget(self.side_panel)
        self._dock_panel.setFeatures(QDockWidget.NoDockWidgetFeatures)

        # Hide the dock title bar for a clean, slim look
        empty = QWidget(self)
        empty.setFixedHeight(1)
        self._dock_panel.setTitleBarWidget(empty)

        self.addDockWidget(Qt.LeftDockWidgetArea, self._dock_panel)

        # Wire panel signals -> canvas actions
        self._wire_side_panel_signals()
        # Initial sync
        self.side_panel.sync_from_canvas(self.canvas)

        # ---- Toolbar (no actions; hidden—Fit All is in side panel) ---------
        self.main_tb = QToolBar('Main', self)
        self.main_tb.setMovable(True)
        self.addToolBar(Qt.TopToolBarArea, self.main_tb)
        self.main_tb.setVisible(False)

        # No XML toolbar; ensure canvas clip offset treats it as 0
        self.canvas.xml_toolbar_height = 0

        # ---- Menubar: File / Info / SavePng / About ------------------------
        self._build_menubar_clean()
        self._sync_toolbar_heights()

    def closeEvent(self, event):
        """Save window geometry when closing"""
        # Only save if window is not minimized
        if not self.isMinimized():
            self.config.set_window_geometry(self.saveGeometry(), self.saveState())
        super().closeEvent(event)

    # ======================================================================
    # Wiring to Side Panel
    # ======================================================================
    def _wire_side_panel_signals(self):
        # Panel-wide action
        self.side_panel.fitAllRequested.connect(self.canvas.fit_all)

        # LES
        self.side_panel.layerModeChanged.connect(self._set_layer_mode)
        self.side_panel.lesStepsToggled.connect(self._toggle_steps)
        self.side_panel.outlineToggled.connect(self._toggle_outline)

        # XML
        self.side_panel.edgesToggled.connect(
            lambda on: self._set_xml_flag('edges', on)
        )
        # "XML Steps" in panel == include repeats in drawing
        self.side_panel.xmlStepsToggled.connect(
            lambda on: self._set_xml_flag('repeats', on)
        )
        # "Barcodes" toggle
        self.side_panel.barcodesToggled.connect(
            lambda on: self._set_xml_flag('barcodes', on)
        )

    # ======================================================================
    # Toolbar height handling (toolbar is hidden => height 0)
    # ======================================================================
    def _sync_toolbar_heights(self):
        self.canvas.toolbar_height = self.main_tb.sizeHint().height() if self.main_tb.isVisible() else 0
        self.canvas.xml_toolbar_height = 0
        self.canvas.update()

    # ======================================================================
    # Menubar (File, Info, SavePng, About ONLY)
    # ======================================================================
    def _build_menubar_clean(self):
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu('&File')

        act_load_les = QAction('Load LES', self)
        act_load_les.triggered.connect(self.open_les_file_dialog)
        file_menu.addAction(act_load_les)

        act_load_xml = QAction('Load XML', self)
        act_load_xml.triggered.connect(self.open_xml_file_dialog)
        file_menu.addAction(act_load_xml)

        file_menu.addSeparator()

        act_unload_les = QAction('Unload LES', self)
        act_unload_les.triggered.connect(self.unload_les)
        file_menu.addAction(act_unload_les)

        act_unload_xml = QAction('Unload XML', self)
        act_unload_xml.triggered.connect(self.unload_xml)
        file_menu.addAction(act_unload_xml)

        # Info
        info_menu = mb.addMenu('&Info')

        act_stats = QAction('LES Stats', self)
        act_stats.triggered.connect(self.canvas.show_stats_window)
        info_menu.addAction(act_stats)

        act_xml_info = QAction('XML Info', self)
        act_xml_info.triggered.connect(self.canvas.show_xml_info_window)
        info_menu.addAction(act_xml_info)

        # Top-level quick actions
        act_save = QAction('&SavePng', self)
        act_save.triggered.connect(self.canvas.save_screenshot)
        mb.addAction(act_save)

        act_about = QAction('&About', self)
        act_about.triggered.connect(self.show_about_dialog)
        mb.addAction(act_about)

    # ======================================================================
    # Actions (called by panel/menu)
    # ======================================================================
    def _set_layer_mode(self, mode: str):
        self.canvas.layer_mode = mode
        self.canvas.init_layer_visibility()  # triggers self.update() inside
        self.side_panel.sync_from_canvas(self.canvas)

    def _toggle_steps(self, checked: bool):
        # No auto-zoom; just redraw with new flag
        self.canvas.show_steps = checked
        self.canvas.update()
        self.side_panel.sync_from_canvas(self.canvas)

    def _toggle_outline(self, checked: bool):
        # No auto-zoom; just redraw with new flag
        self.canvas.show_outline = checked
        self.canvas.update()
        self.side_panel.sync_from_canvas(self.canvas)

    def _set_xml_flag(self, which: str, checked: bool):
        if which == 'edges':
            self.canvas.show_xml_edges = checked
        elif which == 'repeats':
            self.canvas.show_xml_repeats = checked
        elif which == 'barcodes':
            self.canvas.show_xml_barcodes = checked
        self.canvas.update()
        self.side_panel.sync_from_canvas(self.canvas)

    # ======================================================================
    # File ops
    # ======================================================================
    def load_path_smart(self, path: str, silent_xml: bool = False):
        if not path:
            return
        if path.lower().endswith('.xml'):
            self._load_xml_silent_and_zoom(path)
            # Save to config
            self.config.set_last_files(xml_file=path)
        else:
            self.canvas.load_file(path)
            # Save to config
            self.config.set_last_files(les_file=path)

        self._sync_toolbar_heights()
        self._sync_panel_enable_state()

    def open_les_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Open LES File', '',
            'LES files (*.les *.les.txt *.txt);;All files (*.*)'
        )
        if path:
            self.canvas.load_file(path)
            # Save to config
            self.config.set_last_files(les_file=path)
            self._sync_toolbar_heights()
            self._sync_panel_enable_state()

    def open_xml_file_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, 'Open XML Files', '',
            'XML files (*.xml *.xmlstep);;All files (*)'
        )
        if not paths:
            return
        for p in paths:
            self._load_xml_silent_and_zoom(p)
            # Save to config (only the last one)
            self.config.set_last_files(xml_file=p)
        self._sync_toolbar_heights()
        self._sync_panel_enable_state()

    def _load_xml_silent_and_zoom(self, path: str):
        original = self.canvas.show_xml_info_window
        try:
            # suppress info popup during batch/silent loads
            self.canvas.show_xml_info_window = lambda: None
            self.canvas.load_xml_file(path, show_info=False)
        finally:
            self.canvas.show_xml_info_window = original

        try:
            self.canvas.fit_all()
        except Exception:
            pass

    def unload_les(self):
        self.canvas.unload_les()
        # Clear from config
        self.config.clear_files('les')
        self._sync_toolbar_heights()
        self._sync_panel_enable_state()

    def unload_xml(self):
        self.canvas.unload_current_xml()
        # Clear from config
        self.config.clear_files('xml')
        self._sync_toolbar_heights()
        self._sync_panel_enable_state()

    def _sync_panel_enable_state(self):
        self.side_panel.sync_from_canvas(self.canvas)

    # ======================================================================
    # Misc
    # ======================================================================
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._sync_toolbar_heights()

    def show_about_dialog(self):
        QMessageBox.about(
            self,
            "About",
            """LES & XML Viewer (PySide6)
File / Info / SavePng / About.
View controls live in the left Side Panel.
© Your Team"""
        )