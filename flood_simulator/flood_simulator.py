# -*- coding: utf-8 -*-
"""
flood_simulator.py — Classe principale del plugin QGIS
"""

import os
from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

from qgis.core import QgsApplication


class FloodSimulatorPlugin:

    def __init__(self, iface):
        self.iface  = iface
        self.dialog = None
        self.action = None

    def initGui(self):
        """Aggiunge il plugin al menu e alla toolbar di QGIS."""
        icon_path = os.path.join(os.path.dirname(__file__),
                                 "resources", "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        self.action = QAction(icon,
            "🌊  Flood Simulator — Innalzamento Livello Mare",
            self.iface.mainWindow())
        self.action.setToolTip(
            "Simulazione allagamento costiero da DSM GeoTIFF")
        self.action.triggered.connect(self.run)

        # Aggiunge al menu Raster e alla toolbar Plugins
        self.iface.addPluginToRasterMenu("Flood Simulator", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        """Rimuove il plugin dal menu e dalla toolbar."""
        self.iface.removePluginRasterMenu("Flood Simulator", self.action)
        self.iface.removeToolBarIcon(self.action)
        if self.dialog:
            self.dialog.close()
            self.dialog = None

    def run(self):
        """Apre la finestra del plugin."""
        from .flood_dialog import FloodDialog
        if self.dialog is None or not self.dialog.isVisible():
            self.dialog = FloodDialog(self.iface,
                                      self.iface.mainWindow())
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
