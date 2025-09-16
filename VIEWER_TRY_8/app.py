# -*- coding: utf-8 -*-
"""
app.py – Entry point that wires the modularized viewer together.
"""
from __future__ import annotations
import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from gui.main_window import MainWindow
from config import ConfigManager


def main(argv):
    app = QApplication(argv)
    w = MainWindow()

    # Check for config and prompt to reload last files
    config = ConfigManager()
    les_file, xml_file = config.get_last_files()

    # Only prompt if no files were passed via command line
    if len(argv) <= 1 and (les_file or xml_file):
        msg = "Do you want to reload the last files?\n\n"
        if les_file:
            msg += f"LES: {les_file}\n"
        if xml_file:
            msg += f"XML: {xml_file}\n"

        reply = QMessageBox.question(
            w, 'Reload Files', msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply == QMessageBox.Yes:
            if les_file:
                w.load_path_smart(les_file, silent_xml=True)
            if xml_file:
                w.load_path_smart(xml_file, silent_xml=True)
            try:
                w.canvas.fit_all()
            except Exception:
                pass

    # Batch-load any paths passed on the command line; XML loads are silent + Zoom All
    args = argv[1:]
    if args:
        for a in args:
            w.load_path_smart(a, silent_xml=True)
        try:
            w.canvas.fit_all()
        except Exception:
            pass

    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main(sys.argv)