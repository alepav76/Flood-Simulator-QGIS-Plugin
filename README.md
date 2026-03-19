🌊 Flood Simulator — QGIS PluginInteractive coastal flood simulation using GeoTIFF DSM data.Calculates flooded areas using the Priority Flood algorithm for 3 sea-level rise scenarios, displaying the results as separate layers within QGIS.

📦 Installation
1. Copy the plugin to the QGIS folderCopy the flood_simulator/ folder into your QGIS plugins directory:Operating SystemPathWindowsC:\Users\<user>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\macOS~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/Linux~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/The final structure should look like this:

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
      
2. Enable the plugin in QGISOpen QGIS.Go to Plugins → Manage and Install Plugins.Under the Installed tab → search for Flood Simulator → ✅ check the box. The 🌊 button will appear in your toolbar.
3. Install the rasterio dependency. This plugin requires rasterio. Install it within the QGIS Python environment:
   
   Windows (OSGeo4W Shell):
   python -m pip install rasterio
   
   macOS / Linux:
   # Find the QGIS Python path
   python3 -m pip install rasterio
   # Or if using QGIS via Conda:
   conda install -c conda-forge rasterio

   From the QGIS Python Console (Plugins → Python Console):
   import subprocess, sys
   subprocess.run([sys.executable, "-m", "pip", "install", "rasterio"])

🚀 Usage
Step 1 — Load the DSMClick on "📂 Browse…". Select the GeoTIFF DSM file (e.g., DSM_0.5m.tif).The layer will be loaded automatically into QGIS.
Step 2 — Select the Seed Point (Sea Level Reference)Click "🖱️ Click on map to choose seed point". The cursor will turn into a crosshair (+). Click on a point that is definitely at sea level on the map.A red marker will appear, showing the seed coordinates.
Step 3 — Configure ParametersCurrent Sea Level: elevation 0 for most cases.Scenario 1, 2, 3: sea-level rise in meters (e.g., 1.0, 1.5, 2.0).
Step 4 — Run SimulationClick "🌊 Run Simulation".The progress bar will track the process.Upon completion, 3 new layers are added to the QGIS project:
🌊 Flood +1.0 m  (XX%  YY km²) — Light blue.
🌊 Flood +1.5 m  (XX%  YY km²) — Medium blue.
🌊 Flood +2.0 m  (XX%  YY km²) — Dark blue.

⚙️ How the Algorithm Works
Priority Flood with a priority queue (min-heap):
Starts from the seed point (selected sea point).
Visits cells in ascending order of elevation.
Propagates water only to cells ≤ water_level that are physically reachable.
Stops when it encounters barriers higher than the current water level.

Unlike a simple threshold (bathtub model), this approach:✅ Respects levees and walls (even 1 pixel wide).✅ Does not flood closed depressions not connected to the sea.✅ Handles narrow channels and passages correctly.

🗂️ Output File Structure
Output rasters are saved in a temporary system folder (e.g., /tmp/flood_sim_XXXXX/) as:
flood_1.0m.tif
flood_1.5m.tif
flood_2.0m.tif

These are GeoTIFFs with values 0 = dry, 1 = flooded, using the same projection as the original DSM.

🛠️ Requirements
QGIS ≥ 3.0.
Python ≥ 3.6 (included with QGIS).
rasterio (requires separate installation — see above).
numpy (already included with QGIS).
