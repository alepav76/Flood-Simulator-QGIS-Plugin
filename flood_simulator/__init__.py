# -*- coding: utf-8 -*-
"""
Flood Simulator — Plugin QGIS
Simulazione allagamento costiero da DSM GeoTIFF
"""

def classFactory(iface):
    from .flood_simulator import FloodSimulatorPlugin
    return FloodSimulatorPlugin(iface)
