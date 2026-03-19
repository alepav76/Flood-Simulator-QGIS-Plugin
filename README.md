FLOOD SIMULATOR - QGIS PLUGIN

Authors: A. Pavan, P. Paganini, M. Potleca

Interactive coastal flood simulation using GeoTIFF DSM data.
Calculates flooded areas using the Priority Flood algorithm for 3 sea-level rise scenarios, displaying the results as separate layers within QGIS.

INSTALLATION

Copy the plugin to the QGIS folder

Copy the flood_simulator folder into your QGIS plugins directory.

For Windows: C:\Users<user>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\

For macOS: ~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/

For Linux: ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/

The final structure should include: init.py, flood_simulator.py, flood_dialog.py, flood_core.py, map_tool.py, metadata.txt, and the resources folder.

Enable the plugin in QGIS

Open QGIS and go to Plugins, then Manage and Install Plugins. Under the Installed tab, search for Flood Simulator and check the box. The wave button will appear in your toolbar.

Install the rasterio dependency

This plugin requires rasterio. Install it within the QGIS Python environment using the OSGeo4W Shell on Windows (python -m pip install rasterio) or via the QGIS Python Console using the following command: import subprocess, sys; subprocess.run([sys.executable, "-m", "pip", "install", "rasterio"]).

USAGE

Step 1 - Load the DSM
Click on Browse and select the GeoTIFF DSM file. The layer will be loaded automatically into QGIS.

Step 2 - Select the Seed Point
Click on Click on map to choose seed point. The cursor will turn into a crosshair. Click on a point that is definitely at sea level on the map. A red marker will appear showing the seed coordinates.

Step 3 - Configure Parameters
Set the Current Sea Level (usually 0) and define the three scenarios for sea-level rise in meters, such as 1.0, 1.5, and 2.0.

Step 4 - Run Simulation
Click on Run Simulation. The progress bar will track the process. Upon completion, 3 new layers are added to the QGIS project showing the flooded areas for each scenario along with the percentage and square kilometers affected.

HOW THE ALGORITHM WORKS

The plugin uses the Priority Flood algorithm with a priority queue (min-heap). It starts from the selected seed point and visits cells in ascending order of elevation. Water propagates only to cells lower than or equal to the water level that are physically reachable.

Unlike a simple threshold model, this approach respects levees and walls, does not flood closed depressions not connected to the sea, and handles narrow channels correctly.

OUTPUT FILE STRUCTURE

Output rasters are saved in a temporary system folder as flood_1.0m.tif, flood_1.5m.tif, and flood_2.0m.tif. These are GeoTIFFs with values 0 for dry and 1 for flooded, using the same projection as the original DSM.

REQUIREMENTS

QGIS version 3.0 or higher.
Python version 3.6 or higher.
rasterio library (requires separate installation).
numpy library (included with QGIS).

AUTHORS AND LICENSE

Authors: A. Pavan, P. Paganini, M. Potleca.
License: GNU GPL v3.

Developed with the assistance of Claude (Anthropic AI) to optimize code structure, performance, and GUI integration.
