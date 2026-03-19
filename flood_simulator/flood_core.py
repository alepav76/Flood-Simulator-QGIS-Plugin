# -*- coding: utf-8 -*-
"""
flood_core.py — Algoritmo Priority Flood
Logica di simulazione indipendente da QGIS.
"""

import heapq
import numpy as np


def priority_flood(dem: np.ndarray, water_level: float,
                   seed_row: int, seed_col: int) -> np.ndarray:
    """
    Priority Flood: propaga l'acqua dal seed rispettando gli ostacoli.

    Parametri:
        dem         : array 2D delle quote (float32, NaN = nodata)
        water_level : livello assoluto dell'acqua in metri
        seed_row    : riga pixel del seed (punto mare)
        seed_col    : colonna pixel del seed (punto mare)

    Restituisce:
        maschera booleana (uint8) True = cella allagata
    """
    rows, cols = dem.shape
    flooded  = np.zeros((rows, cols), dtype=np.uint8)
    in_queue = np.zeros((rows, cols), dtype=bool)

    # Verifica seed valido
    if not (0 <= seed_row < rows and 0 <= seed_col < cols):
        raise ValueError(f"Seed ({seed_row}, {seed_col}) fuori dai limiti del DSM ({rows}x{cols})")

    seed_elev = float(dem[seed_row, seed_col])
    if np.isnan(seed_elev):
        raise ValueError("Il seed cade su un pixel NoData. Scegli un punto valido.")

    if seed_elev > water_level:
        # Il seed è già più alto del livello acqua: nessun allagamento possibile
        return flooded

    heap = [(seed_elev, seed_row, seed_col)]
    in_queue[seed_row, seed_col] = True

    # 8 direzioni
    neighbors = [(-1,-1),(-1,0),(-1,1),
                 ( 0,-1),       ( 0,1),
                 ( 1,-1),( 1,0),( 1,1)]

    while heap:
        elev, r, c = heapq.heappop(heap)

        if flooded[r, c]:
            continue
        flooded[r, c] = 1

        for dr, dc in neighbors:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue
            if flooded[nr, nc] or in_queue[nr, nc]:
                continue
            n_elev = dem[nr, nc]
            if np.isnan(n_elev):
                continue
            if n_elev <= water_level:
                heapq.heappush(heap, (float(n_elev), nr, nc))
                in_queue[nr, nc] = True

    return flooded


def compute_flood_stats(flood_mask: np.ndarray, pixel_size_m: float, rise: float) -> dict:
    """Calcola statistiche di allagamento."""
    n = int(flood_mask.sum())
    area_m2  = n * pixel_size_m ** 2
    area_km2 = area_m2 / 1_000_000
    pct      = 100.0 * n / flood_mask.size if flood_mask.size > 0 else 0.0
    return {
        "rise_m":   rise,
        "n_pixels": n,
        "pct":      pct,
        "area_m2":  area_m2,
        "area_km2": area_km2,
    }
