# 🌊 Flood Simulator — Plugin QGIS

Simulazione interattiva di allagamento costiero da DSM GeoTIFF.
Calcola le zone inondate con l'algoritmo **Priority Flood** per 3 scenari
di innalzamento del livello del mare, visualizzando i risultati come layer separati in QGIS.

---

## 📦 Installazione

### 1. Copia il plugin nella cartella QGIS

Copia la cartella `flood_simulator/` nella directory dei plugin di QGIS:

| Sistema operativo | Percorso |
|---|---|
| **Windows** | `C:\Users\<utente>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\` |
| **macOS** | `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/` |
| **Linux** | `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/` |

La struttura finale deve essere:
```
plugins/
  flood_simulator/
    __init__.py
    flood_simulator.py
    flood_dialog.py
    flood_core.py
    map_tool.py
    metadata.txt
    resources/
      icon.png
```

### 2. Abilita il plugin in QGIS

1. Apri QGIS
2. Vai su **Plugin → Gestisci e installa plugin**
3. Scheda **Installati** → cerca `Flood Simulator` → ✅ spunta la casella
4. Il bottone 🌊 appare nella toolbar

### 3. Installa la dipendenza `rasterio`

Il plugin richiede `rasterio`. Installalo nell'ambiente Python di QGIS:

**Windows (OSGeo4W Shell):**
```
python -m pip install rasterio
```

**macOS / Linux:**
```bash
# Trova il Python di QGIS
python3 -m pip install rasterio
# oppure, se usi QGIS da conda:
conda install -c conda-forge rasterio
```

**Da QGIS Python Console** (Plugin → Console Python):
```python
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "rasterio"])
```

---

## 🚀 Utilizzo

### Passo 1 — Carica il DSM
- Clicca su **"📂 Sfoglia…"**
- Seleziona il file GeoTIFF del DSM (es. `DSM_0.5m.tif`)
- Il layer viene caricato automaticamente in QGIS

### Passo 2 — Seleziona il seed (punto mare)
- Clicca **"🖱️ Clicca sulla mappa per scegliere il seed"**
- Il cursore diventa un mirino (+)
- Clicca su un punto **certamente in mare** nella mappa
- Viene mostrato un marcatore rosso e le coordinate del seed

### Passo 3 — Imposta i parametri
- **Livello mare attuale**: quota 0 per la maggior parte dei casi
- **Scenario 1, 2, 3**: innalzamento in metri (es. 1.0, 1.5, 2.0)

### Passo 4 — Esegui la simulazione
- Clicca **"🌊 Esegui Simulazione"**
- La progress bar mostra l'avanzamento
- Al termine, 3 nuovi layer vengono aggiunti al progetto QGIS:
  - `🌊 Allagamento +1.0 m  (XX%  YY km²)` — blu chiaro
  - `🌊 Allagamento +1.5 m  (XX%  YY km²)` — blu medio
  - `🌊 Allagamento +2.0 m  (XX%  YY km²)` — blu scuro

---

## ⚙️ Come funziona l'algoritmo

**Priority Flood** con coda di priorità (min-heap):

1. Parte dal seed (punto mare selezionato)
2. Visita le celle in ordine crescente di quota
3. Propaga l'acqua solo alle celle ≤ livello_acqua **fisicamente raggiungibili**
4. Si blocca dove trova barriere più alte del livello attuale

A differenza di un semplice threshold, questo approccio:
- ✅ Rispetta argini e muri (anche 1 pixel)
- ✅ Non allaga depressioni chiuse non connesse al mare
- ✅ Gestisce canali stretti e passaggi

---

## 🗂️ Struttura file output

I raster di output vengono salvati in una cartella temporanea del sistema
(es. `/tmp/flood_sim_XXXXX/`) come:
- `flood_1.0m.tif`
- `flood_1.5m.tif`  
- `flood_2.0m.tif`

Sono GeoTIFF con valori `0 = asciutto`, `1 = allagato`,
nella stessa proiezione del DSM originale.

---

## 🛠️ Requisiti

- QGIS ≥ 3.0
- Python ≥ 3.6 (incluso in QGIS)
- `rasterio` (installazione separata — vedi sopra)
- `numpy` (già incluso in QGIS)
