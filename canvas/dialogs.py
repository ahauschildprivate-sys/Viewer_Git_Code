
# -*- coding: utf-8 -*-
from __future__ import annotations
from PySide6.QtWidgets import QDialog, QVBoxLayout, QPlainTextEdit

class TextDialog(QDialog):
    def __init__(self, title: str, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(720, 520)
        layout = QVBoxLayout(self)
        edit = QPlainTextEdit(self)
        edit.setReadOnly(True)
        edit.setPlainText(text)
        layout.addWidget(edit)
