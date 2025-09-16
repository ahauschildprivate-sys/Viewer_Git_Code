# -*- coding: utf-8 -*-
import os
import configparser
from pathlib import Path
from PySide6.QtCore import QByteArray


class ConfigManager:
    def __init__(self):
        self.config_file = Path(__file__).parent / "config.ini"
        self.config = configparser.ConfigParser()
        self.load_config()

    def load_config(self):
        # Ensure we have the required sections
        if not self.config.has_section('FILES'):
            self.config['FILES'] = {}
        if not self.config.has_section('WINDOW'):
            self.config['WINDOW'] = {}

        if self.config_file.exists():
            self.config.read(self.config_file)

    def save_config(self):
        # Ensure we have the required sections before saving
        if not self.config.has_section('FILES'):
            self.config['FILES'] = {}
        if not self.config.has_section('WINDOW'):
            self.config['WINDOW'] = {}

        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def get_last_files(self):
        """Get the last loaded files from config"""
        if not self.config.has_section('FILES'):
            return '', ''

        les_file = self.config.get('FILES', 'les_file', fallback='')
        xml_file = self.config.get('FILES', 'xml_file', fallback='')
        return les_file, xml_file

    def set_last_files(self, les_file=None, xml_file=None):
        """Set the last loaded files in config"""
        if not self.config.has_section('FILES'):
            self.config['FILES'] = {}

        if les_file is not None:
            self.config['FILES']['les_file'] = les_file
        if xml_file is not None:
            self.config['FILES']['xml_file'] = xml_file
        self.save_config()

    def clear_files(self, file_type=None):
        """Clear file references from config"""
        if not self.config.has_section('FILES'):
            return

        if file_type == 'les' or file_type is None:
            if 'les_file' in self.config['FILES']:
                del self.config['FILES']['les_file']
        if file_type == 'xml' or file_type is None:
            if 'xml_file' in self.config['FILES']:
                del self.config['FILES']['xml_file']
        self.save_config()

    def get_window_geometry(self):
        """Get window geometry from config"""
        if not self.config.has_section('WINDOW'):
            return QByteArray(), QByteArray()

        geometry_str = self.config.get('WINDOW', 'geometry', fallback='')
        state_str = self.config.get('WINDOW', 'state', fallback='')

        geometry = QByteArray.fromBase64(geometry_str.encode()) if geometry_str else QByteArray()
        state = QByteArray.fromBase64(state_str.encode()) if state_str else QByteArray()

        return geometry, state

    def set_window_geometry(self, geometry, state):
        """Set window geometry in config"""
        if not self.config.has_section('WINDOW'):
            self.config['WINDOW'] = {}

        self.config['WINDOW']['geometry'] = geometry.toBase64().data().decode()
        self.config['WINDOW']['state'] = state.toBase64().data().decode()
        self.save_config()