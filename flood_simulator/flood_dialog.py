# -*- coding: utf-8 -*-
"""
flood_dialog.py — Finestra principale del plugin Flood Simulator
"""

import os
import tempfile
import numpy as np

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QDoubleSpinBox, QGroupBox, QProgressBar,
    QTextEdit, QSizePolicy, QFrame, QGridLayout, QSpinBox,
    QMessageBox, QApplication
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QColor, QPalette

from qgis.core import (
    QgsRasterLayer, QgsProject, QgsColorRampShader,
    QgsRasterShader, QgsSingleBandPseudoColorRenderer,
    QgsRasterBandStats, QgsMessageLog, Qgis,
    QgsCoordinateReferenceSystem, QgsPointXY
)
from qgis.gui import QgsMapCanvas

try:
    import rasterio
    from rasterio.transform import rowcol
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

from .flood_core import priority_flood, compute_flood_stats
from .map_tool import SeedPickerTool


# ──────────────────────────────────────────────────────────────
# Worker thread — esegue il calcolo senza bloccare l'UI
# ──────────────────────────────────────────────────────────────

class FloodWorker(QObject):
    finished  = pyqtSignal(dict)   # {livello: path_tif}
    progress  = pyqtSignal(int, str)
    error     = pyqtSignal(str)

    def __init__(self, dsm_path, seed_row, seed_col,
                 sea_level, flood_levels, output_dir):
        super().__init__()
        self.dsm_path    = dsm_path
        self.seed_row    = seed_row
        self.seed_col    = seed_col
        self.sea_level   = sea_level
        self.flood_levels = flood_levels
        self.output_dir  = output_dir

    def run(self):
        try:
            import rasterio
            from rasterio.transform import from_bounds
            import numpy as np

            self.progress.emit(5, "Caricamento DSM…")

            with rasterio.open(self.dsm_path) as src:
                dem       = src.read(1).astype(np.float32)
                nodata    = src.nodata
                transform = src.transform
                crs       = src.crs
                profile   = src.profile.copy()

            if nodata is not None:
                dem[dem == nodata] = np.nan

            results = {}
            n = len(self.flood_levels)

            for i, rise in enumerate(self.flood_levels):
                pct_start = 10 + int(i * 80 / n)
                self.progress.emit(pct_start,
                    f"Calcolo scenario +{rise:.1f} m…")

                water_level = self.sea_level + rise
                mask = priority_flood(dem, water_level,
                                      self.seed_row, self.seed_col)

                # Salva il raster di output come GeoTIFF
                out_profile = profile.copy()
                out_profile.update(dtype=rasterio.uint8, count=1, nodata=0)
                fname = os.path.join(
                    self.output_dir, f"flood_{rise:.1f}m.tif")

                with rasterio.open(fname, "w", **out_profile) as dst:
                    dst.write(mask.astype(np.uint8), 1)

                stats = compute_flood_stats(
                    mask, abs(transform.a), rise)
                results[rise] = {"path": fname, "stats": stats}

                self.progress.emit(pct_start + int(80 / n),
                    f"Scenario +{rise:.1f} m completato")

            self.progress.emit(100, "Completato!")
            self.finished.emit(results)

        except Exception as e:
            self.error.emit(str(e))


# ──────────────────────────────────────────────────────────────
# Finestra principale
# ──────────────────────────────────────────────────────────────

FLOOD_COLORS = [
    (1, "#5bc8f5", "#3399FF"),   # blu chiaro
    (2, "#1a6bbf", "#0055CC"),   # blu medio
    (3, "#00215e", "#002080"),   # blu scuro
]


class FloodDialog(QDialog):

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface       = iface
        self.canvas      = iface.mapCanvas()
        self.dsm_path    = None
        self.seed_point  = None   # QgsPointXY in coordinate mappa
        self.seed_row    = None
        self.seed_col    = None
        self.map_tool    = None
        self.prev_tool   = None
        self.worker      = None
        self.thread      = None
        self.output_dir  = tempfile.mkdtemp(prefix="flood_sim_")

        self.setWindowTitle("🌊  Flood Simulator — Innalzamento Livello Mare")
        self.setMinimumWidth(480)
        self.setModal(False)
        self._build_ui()

    # ── Costruzione UI ─────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)

        # ── Titolo ──
        title = QLabel("Simulazione Allagamento Costiero")
        title.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        title.setFont(font)
        title.setStyleSheet("color: #1a4a7a; padding: 6px;")
        root.addWidget(title)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #cccccc;")
        root.addWidget(sep)

        # ── Sezione 1: DSM ──
        grp1 = QGroupBox("① Carica DSM (GeoTIFF)")
        grp1.setStyleSheet("QGroupBox { font-weight: bold; }")
        g1 = QVBoxLayout(grp1)

        row_dsm = QHBoxLayout()
        self.lbl_dsm = QLabel("Nessun file selezionato")
        self.lbl_dsm.setStyleSheet("color: #888; font-style: italic;")
        self.lbl_dsm.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.btn_load = QPushButton("📂  Sfoglia…")
        self.btn_load.clicked.connect(self.load_dsm)
        self.btn_load.setFixedWidth(110)
        row_dsm.addWidget(self.lbl_dsm)
        row_dsm.addWidget(self.btn_load)
        g1.addLayout(row_dsm)

        self.lbl_dsm_info = QLabel("")
        self.lbl_dsm_info.setStyleSheet("color: #2d6a4f; font-size: 10px;")
        g1.addWidget(self.lbl_dsm_info)
        root.addWidget(grp1)

        # ── Sezione 2: Seed ──
        grp2 = QGroupBox("② Seleziona punto mare (seed)")
        grp2.setStyleSheet("QGroupBox { font-weight: bold; }")
        g2 = QVBoxLayout(grp2)

        hint = QLabel("Clicca sul bottone, poi clicca sulla mappa "
                      "in corrispondenza del mare.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #555; font-size: 10px;")
        g2.addWidget(hint)

        row_seed = QHBoxLayout()
        self.btn_pick = QPushButton("🖱️  Clicca sulla mappa per scegliere il seed")
        self.btn_pick.setEnabled(False)
        self.btn_pick.setCheckable(True)
        self.btn_pick.setStyleSheet(
            "QPushButton:checked { background: #d4edda; border: 2px solid #28a745; }"
            "QPushButton:!checked { background: #f8f9fa; }"
        )
        self.btn_pick.clicked.connect(self.toggle_seed_picker)
        row_seed.addWidget(self.btn_pick)
        g2.addLayout(row_seed)

        self.lbl_seed = QLabel("Seed: non impostato")
        self.lbl_seed.setStyleSheet("color: #888; font-style: italic;")
        g2.addWidget(self.lbl_seed)
        root.addWidget(grp2)

        # ── Sezione 3: Parametri ──
        grp3 = QGroupBox("③ Parametri di simulazione")
        grp3.setStyleSheet("QGroupBox { font-weight: bold; }")
        g3 = QGridLayout(grp3)

        g3.addWidget(QLabel("Livello mare attuale (m):"), 0, 0)
        self.spin_sea = QDoubleSpinBox()
        self.spin_sea.setRange(-10, 20)
        self.spin_sea.setValue(0.0)
        self.spin_sea.setSingleStep(0.1)
        self.spin_sea.setDecimals(2)
        g3.addWidget(self.spin_sea, 0, 1)

        g3.addWidget(QLabel("Scenario 1 — innalzamento (m):"), 1, 0)
        self.spin_l1 = QDoubleSpinBox()
        self.spin_l1.setRange(0.1, 20); self.spin_l1.setValue(1.0)
        self.spin_l1.setSingleStep(0.5); self.spin_l1.setDecimals(2)
        g3.addWidget(self.spin_l1, 1, 1)

        g3.addWidget(QLabel("Scenario 2 — innalzamento (m):"), 2, 0)
        self.spin_l2 = QDoubleSpinBox()
        self.spin_l2.setRange(0.1, 20); self.spin_l2.setValue(1.5)
        self.spin_l2.setSingleStep(0.5); self.spin_l2.setDecimals(2)
        g3.addWidget(self.spin_l2, 2, 1)

        g3.addWidget(QLabel("Scenario 3 — innalzamento (m):"), 3, 0)
        self.spin_l3 = QDoubleSpinBox()
        self.spin_l3.setRange(0.1, 20); self.spin_l3.setValue(2.0)
        self.spin_l3.setSingleStep(0.5); self.spin_l3.setDecimals(2)
        g3.addWidget(self.spin_l3, 3, 1)

        root.addWidget(grp3)

        # ── Bottone Run ──
        self.btn_run = QPushButton("🌊  Esegui Simulazione")
        self.btn_run.setEnabled(False)
        self.btn_run.setMinimumHeight(42)
        self.btn_run.setStyleSheet(
            "QPushButton { background: #1a6bbf; color: white; "
            "font-weight: bold; font-size: 13px; border-radius: 6px; }"
            "QPushButton:hover { background: #155a9e; }"
            "QPushButton:disabled { background: #aaa; color: #ddd; }"
        )
        self.btn_run.clicked.connect(self.run_simulation)
        root.addWidget(self.btn_run)

        # ── Progress bar ──
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        root.addWidget(self.progress)

        # ── Log ──
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(130)
        self.log.setStyleSheet(
            "background: #1e1e2e; color: #a6e3a1; "
            "font-family: monospace; font-size: 10px;"
        )
        root.addWidget(self.log)

        # ── Bottone chiudi ──
        btn_close = QPushButton("Chiudi")
        btn_close.clicked.connect(self.close)
        btn_close.setStyleSheet(
            "QPushButton { background: #f8f9fa; border: 1px solid #ccc; "
            "padding: 5px 20px; border-radius: 4px; }"
            "QPushButton:hover { background: #e2e6ea; }"
        )
        row_close = QHBoxLayout()
        row_close.addStretch()
        row_close.addWidget(btn_close)
        root.addLayout(row_close)

    # ── Logica ─────────────────────────────────────────────────

    def _log(self, msg: str, color: str = "#a6e3a1"):
        self.log.append(f'<span style="color:{color}">{msg}</span>')

    def load_dsm(self):
        if not HAS_RASTERIO:
            QMessageBox.critical(self, "Dipendenza mancante",
                "Il modulo 'rasterio' non è installato nell'ambiente Python di QGIS.\n\n"
                "Apri la Python Console di QGIS ed esegui:\n"
                "    import pip; pip.main(['install','rasterio'])\n"
                "oppure installa rasterio nell'ambiente conda/osgeo4w.")
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "Apri file DSM GeoTIFF", "",
            "GeoTIFF (*.tif *.tiff);;Tutti i file (*.*)")
        if not path:
            return

        try:
            import rasterio
            with rasterio.open(path) as src:
                dem    = src.read(1).astype("float32")
                nodata = src.nodata
                tr     = src.transform
                crs    = src.crs

            if nodata is not None:
                dem[dem == nodata] = float("nan")

            self.dsm_path      = path
            self.dsm_dem       = dem
            self.dsm_transform = tr
            self.dsm_crs       = crs

            pxsize = abs(tr.a)
            zmin   = float(np.nanmin(dem))
            zmax   = float(np.nanmax(dem))
            name   = os.path.basename(path)
            self.lbl_dsm.setText(name)
            self.lbl_dsm.setStyleSheet("color: #1a4a7a; font-style: normal;")
            self.lbl_dsm_info.setText(
                f"Dimensioni: {dem.shape[1]}×{dem.shape[0]} px  |  "
                f"Risoluzione: {pxsize:.2f} m  |  Z: [{zmin:.1f}, {zmax:.1f}] m")
            self._log(f"✅ DSM caricato: {name}")
            self._log(f"   {dem.shape[1]}×{dem.shape[0]} px  |  Z [{zmin:.1f} – {zmax:.1f}] m")

            # Carica il DSM come layer QGIS per visualizzarlo
            layer = QgsRasterLayer(path, f"DSM — {name}")
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                self.iface.setActiveLayer(layer)
                self.canvas.zoomToFullExtent()
                self._log("   Layer DSM aggiunto a QGIS")

            self.btn_pick.setEnabled(True)
            self._check_ready()

        except Exception as e:
            self._log(f"❌ Errore caricamento: {e}", "#f38ba8")
            QMessageBox.critical(self, "Errore", str(e))

    def toggle_seed_picker(self):
        if self.btn_pick.isChecked():
            # Attiva il tool di selezione
            self.prev_tool = self.canvas.mapTool()
            self.map_tool  = SeedPickerTool(self.canvas)
            self.map_tool.pointSelected.connect(self.on_seed_selected)
            self.canvas.setMapTool(self.map_tool)
            self.btn_pick.setText("⏳  Clicca sul mare nella mappa…")
            self._log("🖱️  Tool attivo — clicca sul mare nella mappa")
        else:
            self._deactivate_seed_tool()

    def _deactivate_seed_tool(self):
        if self.map_tool:
            self.canvas.unsetMapTool(self.map_tool)
            self.map_tool = None
        if self.prev_tool:
            self.canvas.setMapTool(self.prev_tool)
        self.btn_pick.setChecked(False)
        self.btn_pick.setText("🖱️  Clicca sulla mappa per scegliere il seed")

    def on_seed_selected(self, point: QgsPointXY):
        """Riceve il click dalla mappa e converte in pixel DSM."""
        self._deactivate_seed_tool()
        try:
            from rasterio.transform import rowcol
            tr = self.dsm_transform

            # Coordinate geografiche → pixel raster
            row, col = rowcol(tr, point.x(), point.y())
            row, col = int(row), int(col)

            dem = self.dsm_dem
            if not (0 <= row < dem.shape[0] and 0 <= col < dem.shape[1]):
                self._log("⚠️  Punto fuori dall'estensione del DSM. Riprova.", "#fab387")
                return

            z = dem[row, col]
            if np.isnan(z):
                self._log("⚠️  Punto su NoData. Scegli un altro punto.", "#fab387")
                return

            self.seed_point = point
            self.seed_row   = row
            self.seed_col   = col

            self.lbl_seed.setText(
                f"Seed: riga={row}, col={col}  |  "
                f"X={point.x():.2f}  Y={point.y():.2f}  |  Z={z:.2f} m")
            self.lbl_seed.setStyleSheet("color: #1a6bbf; font-style: normal;")
            self._log(f"📌 Seed impostato: ({row}, {col})  Z={z:.2f} m")

            # Aggiungi marcatore visivo sulla mappa
            self._add_seed_marker(point)
            self._check_ready()

        except Exception as e:
            self._log(f"❌ Errore selezione seed: {e}", "#f38ba8")

    def _add_seed_marker(self, point: QgsPointXY):
        """Aggiunge un piccolo layer punto per mostrare la posizione del seed."""
        try:
            from qgis.core import (QgsVectorLayer, QgsFeature,
                                   QgsGeometry, QgsPointXY)
            vl = QgsVectorLayer(
                f"Point?crs={self.dsm_crs.authid() if self.dsm_crs else 'EPSG:4326'}",
                "🔵 Seed Point", "memory")
            pr = vl.dataProvider()
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPointXY(point))
            pr.addFeature(feat)
            vl.updateExtents()

            # Stile: cerchio rosso
            from qgis.core import QgsMarkerSymbol
            symbol = QgsMarkerSymbol.createSimple({
                "name": "circle", "color": "red",
                "size": "10", "outline_color": "white", "outline_width": "1"
            })
            vl.renderer().setSymbol(symbol)

            # Rimuovi seed precedente se esiste
            for lyr in QgsProject.instance().mapLayersByName("🔵 Seed Point"):
                QgsProject.instance().removeMapLayer(lyr.id())

            QgsProject.instance().addMapLayer(vl)
        except Exception:
            pass  # il marker è opzionale

    def _check_ready(self):
        ready = (self.dsm_path is not None and
                 self.seed_row is not None)
        self.btn_run.setEnabled(ready)

    def run_simulation(self):
        if self.thread and self.thread.isRunning():
            return

        sea   = self.spin_sea.value()
        lvls  = sorted([self.spin_l1.value(),
                        self.spin_l2.value(),
                        self.spin_l3.value()])

        self._log(f"\n▶ Avvio simulazione  |  Livello mare: {sea:.2f} m")
        self._log(f"  Scenari: +{lvls[0]:.1f} m, +{lvls[1]:.1f} m, +{lvls[2]:.1f} m")

        self.btn_run.setEnabled(False)
        self.progress.setValue(0)

        self.worker = FloodWorker(
            self.dsm_path, self.seed_row, self.seed_col,
            sea, lvls, self.output_dir)
        self.thread = QThread()
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_simulation_done)
        self.worker.progress.connect(self.on_progress)
        self.worker.error.connect(self.on_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.thread.finished.connect(lambda: self.btn_run.setEnabled(True))

        self.thread.start()

    def on_progress(self, value: int, msg: str):
        self.progress.setValue(value)
        self.progress.setFormat(f"{msg}  ({value}%)")
        self._log(f"  {msg}")

    def on_error(self, msg: str):
        self._log(f"❌ Errore: {msg}", "#f38ba8")
        QMessageBox.critical(self, "Errore simulazione", msg)
        self.btn_run.setEnabled(True)

    def on_simulation_done(self, results: dict):
        self._log("\n✅ Simulazione completata!")

        COLORS = [
            (0, "#5bc8f5", "#3399ff"),
            (1, "#1a6bbf", "#0055cc"),
            (2, "#00215e", "#002080"),
        ]

        for i, (rise, data) in enumerate(sorted(results.items())):
            path  = data["path"]
            stats = data["stats"]
            color_low, color_high = COLORS[i % len(COLORS)][1], COLORS[i % len(COLORS)][2]

            area_str = (f"{stats['area_km2']:.3f} km²"
                        if stats['area_km2'] >= 0.01
                        else f"{stats['area_m2']:,.0f} m²")

            layer_name = (f"🌊 Allagamento +{rise:.1f} m  "
                          f"({stats['pct']:.1f}%  {area_str})")

            layer = QgsRasterLayer(path, layer_name)
            if not layer.isValid():
                self._log(f"  ⚠️  Layer +{rise:.1f} m non valido", "#fab387")
                continue

            # Stile: trasparenza 0 = asciutto, colore = allagato
            shader = QgsRasterShader()
            color_ramp = QgsColorRampShader()
            color_ramp.setColorRampType(QgsColorRampShader.Discrete)

            items = [
                QgsColorRampShader.ColorRampItem(0, QColor(0, 0, 0, 0),   "Asciutto"),
                QgsColorRampShader.ColorRampItem(1, QColor(color_high).lighter(130), f"+{rise:.1f} m"),
            ]
            color_ramp.setColorRampItemList(items)
            shader.setRasterShaderFunction(color_ramp)

            renderer = QgsSingleBandPseudoColorRenderer(
                layer.dataProvider(), 1, shader)
            renderer.setOpacity(0.72)
            layer.setRenderer(renderer)

            QgsProject.instance().addMapLayer(layer)
            self._log(
                f"  ✅ Layer +{rise:.1f} m → {stats['pct']:.1f}%  "
                f"({area_str})")

        self.canvas.refreshAllLayers()
        self._log("\n🗺️  Layer aggiornati in QGIS. Simulazione completata.")

    def closeEvent(self, event):
        self._deactivate_seed_tool()
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait(3000)
        super().closeEvent(event)
