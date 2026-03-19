# -*- coding: utf-8 -*-
"""
map_tool.py — Tool mappa QGIS per la selezione interattiva del seed point
"""

from qgis.gui import QgsMapTool
from qgis.core import QgsPointXY
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QCursor, QPixmap, QColor
from PyQt5.QtCore import Qt


class SeedPickerTool(QgsMapTool):
    """
    Tool mappa che intercetta un click sinistro dell'utente
    e restituisce le coordinate geografiche del punto selezionato.
    """
    pointSelected = pyqtSignal(QgsPointXY)   # emesso quando l'utente clicca

    def __init__(self, canvas):
        super().__init__(canvas)
        # Cursore a mirino
        self.setCursor(Qt.CrossCursor)

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            point = self.toMapCoordinates(event.pos())
            self.pointSelected.emit(point)
