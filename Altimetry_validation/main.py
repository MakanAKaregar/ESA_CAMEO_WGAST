#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Altimetry Validation Workflow
Sentinel-3 / Sentinel-6 SSH Extraction & Validation

Main features:
- SSH extraction from Sentinel products
- River or coastal mask filtering
- Dam exclusion zone handling for inland water
- SWORD-based slope correction for inland water
- GNSS-IR / in-situ validation ready output
- Robust aggregation (median + MAD)
"""
# =============================================================================
# IMPORTS
# =============================================================================

import os
import glob
import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd
from shapely.geometry import Point
from shapely.ops import unary_union, transform as shp_transform
from math import radians, sin, cos, sqrt, atan2
from google.colab import drive
import warnings
import pyproj

warnings.filterwarnings("ignore", category=FutureWarning)

# =============================================================================
# 0️⃣ GOOGLE DRIVE SETUP + PATHS
# =============================================================================

from google.colab import drive
import os
import yaml

drive.mount('/content/drive', force_remount=True)

# -------------------------------------------------------------
# Project root (ONLY place where Drive is defined)
# -------------------------------------------------------------
project_root_drive = "/content/drive/MyDrive/Altimetry/FFSAR_product"

# -------------------------------------------------------------
# Load configuration (GitHub-style structure)
# -------------------------------------------------------------
config_path = "config/config.yaml"

with open(config_path, "r") as f:
    cfg = yaml.safe_load(f)

# -------------------------------------------------------------
# Sentinel datasets
# -------------------------------------------------------------
sentinel6_path = os.path.join(project_root_drive, "Sentinel-6_part2")

# -------------------------------------------------------------
# Outputs
# -------------------------------------------------------------
output_path = os.path.join(project_root_drive, "results_S6_river_part2")
os.makedirs(output_path, exist_ok=True)

# -------------------------------------------------------------
# Auxiliary datasets
# -------------------------------------------------------------
river_mask_path = os.path.join(project_root_drive, "Sanaga_mask", "Sanaga.shp")
stations_file = os.path.join(project_root_drive, "RPR_stations.xls")

# -------------------------------------------------------------
# SWORD dataset (optional slope correction)
# -------------------------------------------------------------
sword_reaches_path = os.path.join(project_root_drive, "Sanaga_SWORD.gpkg")

# =============================================================================
# 🚧 DAM LOCATION (EXCLUSION ZONE)
# =============================================================================

lat_dam = 4.078300
lon_dam = 10.464673
dam_exclusion_m = 700  # 0.7 km exclusion radius

# =============================================================================
# 1️⃣ LOAD RIVER or COASTAL STATIONS (GNSS-IR OR HYDROMETRIC OR TIDE GAUGE STATION)
# =============================================================================

stations_df = pd.read_excel(stations_file)

# Keep only river stations
stations_df = stations_df[stations_df["type"].str.lower() == "river"].reset_index(drop=True)

print(f"River stations loaded: {len(stations_df)}")
print(stations_df[["name", "lat", "lon"]].to_string(index=False))

# =============================================================================
# 2️⃣ LOAD RIVER OR COASTAL MASK
# =============================================================================

river_gdf = gpd.read_file(river_mask_path)

# Ensure CRS = WGS84
if river_gdf.crs is None:
    river_gdf = river_gdf.set_crs(epsg=4326)
elif getattr(river_gdf.crs, "to_epsg", lambda: None)() != 4326:
    river_gdf = river_gdf.to_crs(epsg=4326)

river_union = unary_union(river_gdf.geometry)
print("River mask loaded")

# =============================================================================
# 2️⃣b LOAD SWORD (OPTIONAL)
# =============================================================================

sword_gdf = None
sword_slope_col = None

if os.path.exists(sword_reaches_path):

    print(f"Loading SWORD dataset: {sword_reaches_path}")
    sword_gdf = gpd.read_file(sword_reaches_path)

    # CRS fix
    if sword_gdf.crs is None:
        sword_gdf = sword_gdf.set_crs(epsg=4326)
    elif getattr(sword_gdf.crs, "to_epsg", lambda: None)() != 4326:
        sword_gdf = sword_gdf.to_crs(epsg=4326)

    # Detect slope column automatically
    for c in ("slope", "slope_mkm", "slope_m_per_km", "Slope", "SLOPE"):
        if c in sword_gdf.columns:
            sword_slope_col = c
            break

    if sword_slope_col:
        print(f"SWORD slope column: {sword_slope_col}")
    else:
        print("⚠️ No slope column detected in SWORD")

else:
    print("⚠️ SWORD not found -> slope correction disabled")

# =============================================================================
# 3️⃣ PARAMETERS
# =============================================================================

search_radius_deg = 0.12
buffer_radius_km = 1
buffer_radius_m = int(buffer_radius_km * 1000)

misfit_threshold = 6.0

w_station = 0.3
w_center = 0.7

# =============================================================================
# 4️⃣ UTILITY FUNCTIONS
# =============================================================================

def print_var_info(da, name):
    """Print NetCDF variable metadata."""
    if da is None:
        print(f"{name}: missing")
        return
    print(f"{name}: shape={da.shape}, dtype={da.dtype}")

def to_numpy_nan(da):
    """Convert xarray variable to numpy and replace fill values."""
    if da is None:
        return None
    arr = da.values.astype(float)
    fv = da.attrs.get("_FillValue", da.attrs.get("missing_value", None))
    if fv is not None:
        arr[arr == fv] = np.nan
    return arr

def haversine_km(lat1, lon1, lat2, lon2):
    """Compute distance in km."""
    R = 6371.0
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi/2)**2 + cos(phi1)*cos(phi2)*sin(dlambda/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))

def local_projector(lat, lon):
    """Return local UTM projection centered on location."""
    utm_zone = int((lon + 180) / 6) + 1
    epsg = 32600 + utm_zone if lat >= 0 else 32700 + utm_zone

    to_m = pyproj.Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True).transform
    to_ll = pyproj.Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True).transform

    return to_m, to_ll, epsg

# =============================================================================
# TRACTS SELECTION
# =============================================================================

tracts_all = [d for d in os.listdir(sentinel6_path)
              if os.path.isdir(os.path.join(sentinel6_path, d))]

print("Available tracts:", tracts_all)

user_input = input("Tracts to process: ").strip()

if user_input:
    tracts = [t.strip() for t in user_input.split(",") if t in tracts_all]
else:
    tracts = tracts_all

print("Selected tracts:", tracts)

# =============================================================================
# 5️⃣ MAIN LOOP
# =============================================================================

for tract in tracts:
    print(f"\n🛰️ Processing tract {tract} ...")

    # data_dir = os.path.join(sentinel3_path, tract, "80Hz", "l2")
    data_dir = os.path.join(sentinel6_path, tract, "140Hz", "l2")

    nc_files = sorted(glob.glob(os.path.join(data_dir, "*.nc")))
    if not nc_files:
        print(f"⚠️ No .nc files found in {data_dir}. Skipping.")
        continue

    print(f"  → {len(nc_files)} .nc files found")

    for _, station in stations_df.iterrows():
        station_name = station["name"]
        lat_station = float(station["lat"])
        lon_station = float(station["lon"])

        dfs_station = []

        for file in nc_files:
            ds_main = ds_geo = None
            try:
                # --- Open main dataset ---
                try:
                    ds_main = xr.open_dataset(file, group="data/ku")
                    group_used = "data/ku"
                except Exception:
                    ds_main = xr.open_dataset(file)
                    group_used = "root"

                # --- Open geophysical corrections dataset ---
                try:
                    ds_geo = xr.open_dataset(file, group="data_01")
                except Exception:
                    try:
                        ds_geo = xr.open_dataset(file, group="geo")
                    except Exception:
                        ds_geo = None

                # --- Inspect time / altitude / range / lat-lon variables ---
                t_da = ds_main.get("time", None)
                lat_da = ds_main.get("latitude", None)
                lon_da = ds_main.get("longitude", None)
                alt_da = ds_main.get("altitude", None)
                range_da = ds_main.get("range_samp", ds_main.get("range", None))

                print_var_info(t_da, "time")
                print_var_info(lat_da, "latitude")
                print_var_info(lon_da, "longitude")
                print_var_info(alt_da, "altitude")
                print_var_info(range_da, "range_samp")

                # --- Robust time decoding ---
                time_dt = robust_decode_time(t_da)
                if time_dt is None or np.all(pd.isna(time_dt)):
                    print("⚠️ Unable to decode time correctly. Skipping file.")
                    continue

                # --- Convert variables to numpy arrays (FillValue → NaN) ---
                lat = to_numpy_nan(lat_da)
                lon = to_numpy_nan(lon_da)
                altitude = to_numpy_nan(alt_da)
                range_samp = to_numpy_nan(range_da)

                # --- Check required variables ---
                if lat is None or lon is None or altitude is None or range_samp is None:
                    print("⚠️ Missing required variables (lat/lon/altitude/range). Skipping file.")
                    continue

                # --- Quality mask removed: keep all points ---
                quality_mask = np.ones_like(lat, dtype=bool)
                print("  → surface_flag IGNORED: keeping all points (spatial + misfit filtering applied later).")

                # --- Detect misfit variable (misfit_samp preferred) ---
                if "misfit_samp" in ds_main:
                    misfit_var_name = "misfit_samp"
                elif "misfit_ptr" in ds_main:
                    misfit_var_name = "misfit_ptr"
                else:
                    misfit_var_name = None

                misfit_all = None
                if misfit_var_name:
                    misfit_all = to_numpy_nan(ds_main[misfit_var_name])
                    try:
                        print(f"  → misfit variable used: {misfit_var_name}; "
                              f"min/max: {np.nanmin(misfit_all):.3f}/{np.nanmax(misfit_all):.3f}")
                    except Exception:
                        pass
                else:
                    print("  → No misfit_samp/ptr variable found in ds_main.")

                # --- Prepare geophysical corrections ---
                corrections_candidates = [
                    "iono_cor_gim",
                    "model_wet_tropo_cor_zero_altitude",
                    "model_dry_tropo_cor_zero_altitude",
                    "solid_earth_tide",
                    "pole_tide",
                ]# for coastal application use corrections_candidates = ["iono_cor_gim","model_wet_tropo_cor_zero_altitude",  "model_dry_tropo_cor_zero_altitude","solid_earth_tide", "pole_tide", "dac","longperiod_tide", "equi_tide", "load_tide"]# add                   

                present_corr = []
                if ds_geo is not None:
                    for c in corrections_candidates:
                        if c in ds_geo:
                            present_corr.append(c)

                def interp_geo(varname):
                    if ds_geo is None or varname not in ds_geo:
                        return np.zeros(len(time_dt))

                    tgeo = ds_geo["time"]
                    tgeo_dt = robust_decode_time(tgeo)
                    vals = to_numpy_nan(ds_geo[varname])

                    try:
                        x_geo = tgeo_dt.astype("int64") / 1e9
                        x_main = pd.to_datetime(time_dt).astype("int64") / 1e9

                        if np.all(np.isnan(vals)):
                            return np.zeros_like(x_main)

                        vals_interp = np.interp(x_main, x_geo, vals, left=np.nan, right=np.nan)

                        outside_mask = np.isnan(vals_interp)
                        if np.any(outside_mask):
                            pct_out = 100.0 * np.sum(outside_mask) / len(outside_mask)
                            if pct_out > 5:
                                print(f"    ⚠️ interpolation {varname}: {pct_out:.1f}% out of range → set to 0")
                            vals_interp[outside_mask] = 0.0

                        return vals_interp

                    except Exception as e:
                        print(f"    ⚠️ Interpolation error {varname}: {e}")
                        return np.zeros(len(time_dt))

                # --- Apply geophysical corrections ---
                total_correction = np.zeros(len(time_dt))
                used_corr = []

                for c in corrections_candidates:
                    if ds_geo is not None and c in ds_geo:
                        comp = interp_geo(c)
                        if np.nanstd(comp) > 0:
                            total_correction += np.nan_to_num(comp)
                            used_corr.append(c)

                print(f"  → Corrections used: {used_corr}")

                # --- Compute raw SSH ---
                ssh_raw = altitude - range_samp - total_correction
                ssh = np.where(quality_mask, ssh_raw, np.nan)

                # --- Station spatial window (approx degrees) ---
                mask_station = (
                    (np.abs(lat - lat_station) <= search_radius_deg)
                    & (np.abs(lon - lon_station) <= search_radius_deg)
                )

                if np.sum(mask_station) == 0:
                    continue

                # --- Build initial dataframe ---
                df = pd.DataFrame({
                    "date": pd.to_datetime(time_dt)[mask_station],
                    "lat": lat[mask_station],
                    "lon": lon[mask_station],
                    "ssh": ssh[mask_station],
                    "misfit": misfit_all[mask_station] if misfit_all is not None else np.nan,
                }).dropna(subset=["lat", "lon"])

                gdf_points = gpd.GeoDataFrame(
                    df,
                    geometry=gpd.points_from_xy(df["lon"], df["lat"]),
                    crs="EPSG:4326"
                )

                # --- Keep only river pixels ---
                gdf_points_in_river = gdf_points[gdf_points.geometry.intersects(river_union)].copy()
                print(f"  → Window points: {len(df)} ; river points: {len(gdf_points_in_river)}")

                if gdf_points_in_river.empty:
                    continue

                # --- Exclude dam buffer only for RPR1 station ---
                try:
                    if station_name == "Song_Mbenguè":
                        before_excl = len(gdf_points_in_river)
                        gdf_points_in_river = gdf_points_in_river[
                            ~gdf_points_in_river.geometry.within(dam_buffer)
                        ]
                        after_excl = len(gdf_points_in_river)
                        print(f"  → Dam exclusion ({dam_exclusion_m} m): {before_excl} → {after_excl}")

                        if gdf_points_in_river.empty:
                            continue
                except Exception as e:
                    print(f"⚠️ Dam exclusion error: {e}")

                # --- Misfit filtering ---
                if "misfit" in gdf_points_in_river.columns and not np.all(np.isnan(gdf_points_in_river["misfit"])):
                    before_count = len(gdf_points_in_river)
                    gdf_points_in_river = gdf_points_in_river[
                        gdf_points_in_river["misfit"] < misfit_threshold
                    ]
                    print(f"  → After misfit filtering < {misfit_threshold}: {before_count} → {len(gdf_points_in_river)}")

                    if gdf_points_in_river.empty:
                        continue

                # ============================================================
                # 🔹 Robust virtual point selection
                # ============================================================
                try:
                    s6_in_river = gdf_points_in_river.copy()
                    if s6_in_river.empty:
                        print("⚠️ No river points after filtering.")
                        continue

                    pts_union = s6_in_river.unary_union
                    pts_union_buffer = pts_union.buffer(0.0001)
                    river_cross_section = river_union.intersection(pts_union_buffer)

                    if river_cross_section.is_empty:
                        station_point = Point(lon_station, lat_station)
                        station_buf2km = buffer_point_meters(station_point, 2000, lat_station, lon_station)

                        if station_buf2km is not None:
                            try:
                                local_piece = river_union.intersection(station_buf2km)
                                if not local_piece.is_empty:
                                    river_cross_section = local_piece
                                    print("    → Fallback: station buffer used.")
                            except Exception:
                                pass

                    if river_cross_section.is_empty:
                        s6_in_river["dist_station_km"] = s6_in_river.apply(
                            lambda r: haversine_km(lat_station, lon_station, r["lat"], r["lon"]),
                            axis=1
                        )
                        virtual_idx = s6_in_river["dist_station_km"].idxmin()
                        virtual_point = s6_in_river.loc[virtual_idx, "geometry"]
                    else:
                        river_cross_center = river_cross_section.centroid

                        s6_in_river["dist_station_km"] = s6_in_river.apply(
                            lambda r: haversine_km(lat_station, lon_station, r["lat"], r["lon"]),
                            axis=1
                        )

                        s6_in_river["dist_center_km"] = s6_in_river.apply(
                            lambda r: haversine_km(river_cross_center.y, river_cross_center.x, r["lat"], r["lon"]),
                            axis=1
                        )

                        s6_in_river["score"] = (
                            w_station * s6_in_river["dist_station_km"] +
                            w_center * s6_in_river["dist_center_km"]
                        )

                        virtual_idx = s6_in_river["score"].idxmin()
                        virtual_point = s6_in_river.loc[virtual_idx, "geometry"]

                except Exception as e:
                    print(f"❌ Virtual point selection error: {type(e).__name__}: {e}")
                    continue

                # --- Metric buffer around virtual point ---
                if virtual_point is None:
                    continue

                buffer_poly = buffer_point_meters(
                    virtual_point,
                    buffer_radius_m,
                    lat_station,
                    lon_station
                )

                if buffer_poly is None or buffer_poly.is_empty:
                    continue

                river_zone = buffer_poly.intersection(river_union)

                if river_zone.is_empty:
                    continue

                gdf_buffer = s6_in_river[
                    s6_in_river.geometry.intersects(river_zone)
                ].copy()

                print(f"  → Buffer points selected: {len(gdf_buffer)}")

                if gdf_buffer.empty:
                    continue

            # -----------------------------------------------------------
            #  SWORD-based slope correction
            # -----------------------------------------------------------
            from shapely.geometry import LineString
            
            slope_m_per_km = 0.0
            slope_source = "none"
            VS_method = "undefined"
            
            if sword_gdf is None or len(sword_gdf) == 0:
                print("⚠️ SWORD not loaded → no SSH correction.")
                gdf_buffer["ssh_uncorr"] = gdf_buffer["ssh"]
                gdf_buffer["ssh_corr"] = gdf_buffer["ssh"]
            else:
                try:
                    # -----------------------------------------------------------
                    # 0) Local metric CRS (cluster centroid)
                    # -----------------------------------------------------------
                    cluster_centroid_ll = gdf_buffer.unary_union.centroid
                    to_m, to_ll, epsg_loc = local_projector(cluster_centroid_ll.y, cluster_centroid_ll.x)
                    cluster_centroid_m = shp_transform(to_m, cluster_centroid_ll)
                    cluster_buffer_m = cluster_centroid_m.buffer(500)
            
                    print(f"INFO: Approximate local EPSG = {epsg_loc}")
            
                    # -----------------------------------------------------------
                    # 0b) Fix SWORD CRS: ensure CRS then project to epsg_loc (meters)
                    # -----------------------------------------------------------
                    if sword_gdf.crs is None:
                        sword_gdf = sword_gdf.set_crs(epsg=4326)
                    elif getattr(sword_gdf.crs, "to_epsg", lambda: None)() != 4326:
                        sword_gdf = sword_gdf.to_crs(epsg=4326)
            
                    sword_gdf_m = sword_gdf.to_crs(epsg_loc)
                    cand = sword_gdf_m.copy()
            
                    # -----------------------------------------------------------
                    # 1) Filter SWORD for Sanaga (heuristics)
                    # -----------------------------------------------------------
                    if "river_name" in cand.columns:
                        cand = cand[cand["river_name"].str.contains("Sanaga", case=False, na=False)]
                    else:
                        print("⚠️ No 'river_name' field found in SWORD — keeping all reaches for now.")
            
                    if "strm_order" in cand.columns:
                        cand = cand[cand["strm_order"] >= 4]
            
                    if "facc" in cand.columns:
                        cand = cand[cand["facc"] > 1e5]
            
                    if len(cand) == 0:
                        raise RuntimeError("No Sanaga reaches found in SWORD after filtering.")
            
                    # -----------------------------------------------------------
                    # 2) Build reach_center_m (use X,Y if available)
                    # -----------------------------------------------------------
                    def build_reach_center(row):
                        if ("X" in row.index and "Y" in row.index and
                            not pd.isna(row["X"]) and not pd.isna(row["Y"])):
                            try:
                                pt_ll = Point(float(row["X"]), float(row["Y"]))
                                return shp_transform(to_m, pt_ll)
                            except Exception:
                                return row["geometry"].centroid
                        else:
                            return row["geometry"].centroid
            
                    cand = cand.copy()
                    cand["geometry_m"] = cand["geometry"]  # already projected (meters)
                    cand["reach_center_m"] = cand.apply(build_reach_center, axis=1)
            
                    example_geom = cand["geometry_m"].iloc[0]
                    print("Example geometry_m (first):", example_geom.geom_type)
                    print("Example reach_center_m (first coords):",
                          cand["reach_center_m"].iloc[0].x,
                          cand["reach_center_m"].iloc[0].y)
            
                    # -----------------------------------------------------------
                    # 3) Compute cluster median point (meters)
                    # -----------------------------------------------------------
                    pts_m = [shp_transform(to_m, Point(r["lon"], r["lat"]))
                             for _, r in gdf_buffer.sort_values("date").iterrows()]
            
                    if len(pts_m) == 0:
                        raise RuntimeError("Empty cluster.")
            
                    # -----------------------------------------------------------
                    # Geometric median function (Weiszfeld)
                    # -----------------------------------------------------------
                    def geometric_median(points, eps=1e-6, max_iter=1000):
                        pts = np.asarray(points)
                        guess = pts.mean(axis=0)
            
                        for _ in range(max_iter):
                            dist = np.linalg.norm(pts - guess, axis=1)
                            nonzero = dist > eps
            
                            if not np.any(nonzero):
                                return guess
            
                            w = 1 / np.maximum(dist, eps)
                            new_guess = np.sum(pts[nonzero] * w[nonzero, None], axis=0) / np.sum(w[nonzero])
            
                            if np.linalg.norm(new_guess - guess) < eps:
                                return new_guess
            
                            guess = new_guess
            
                        return guess
            
                    pts_arr = np.array([[p.x, p.y] for p in pts_m])
                    median_xy = geometric_median(pts_arr)
                    median_point_m = Point(median_xy[0], median_xy[1])
                    print(f"INFO: true spatial median (m) = ({median_point_m.x:.1f}, {median_point_m.y:.1f})")
            
                    median_point_ll = shp_transform(to_ll, median_point_m)
                    print(f"INFO: true spatial median (lat, lon) = ({median_point_ll.y:.6f}, {median_point_ll.x:.6f})")
            
                    # -----------------------------------------------------------
                    # 4) Robust reach selection from median point
                    # -----------------------------------------------------------
                    cand["dist_median_to_geom"] = cand["geometry_m"].apply(
                        lambda g: g.distance(median_point_m)
                    )
                    sword_reach = cand.loc[cand["dist_median_to_geom"].idxmin()]
            
                    river_line_m = sword_reach["geometry_m"]
                    if river_line_m.is_empty:
                        raise RuntimeError("Selected reach geometry is empty.")
            
                    # ensure LineString
                    if not isinstance(river_line_m, LineString):
                        try:
                            parts = list(river_line_m)
                            river_line_m = max(parts, key=lambda p: p.length)
                        except Exception:
                            raise RuntimeError("Selected reach geometry is not usable as LineString.")
            
                    # -----------------------------------------------------------
                    # 5) VS = projection of median point onto reach centerline
                    # -----------------------------------------------------------
                    proj_dist_on_reach = river_line_m.project(median_point_m)
                    VS_m = river_line_m.interpolate(proj_dist_on_reach)
                    VS_method = "median_projection_on_selected_reach"
            
                    Dist_VS_km = proj_dist_on_reach / 1000.0
                    reach_id_col = next((c for c in ["reach_id", "rch_id_dn", "reach_id_dn"]
                                         if c in sword_reach.index), None)
                    reach_id_val = sword_reach.get(reach_id_col)
            
                    print(f" → Selected reach: {reach_id_col} = {reach_id_val}")
                    print(f"   VS_method = {VS_method} | Dist_VS = {Dist_VS_km:.3f} km")
            
                    # -----------------------------------------------------------
                    # 6) VS consistency check → fallback if needed
                    # -----------------------------------------------------------
                    dist_candidate_to_proj = median_point_m.distance(VS_m)
                    MAX_ACCEPT_DIST_M = 2000
                    print(f"DEBUG: median → projected VS distance = {dist_candidate_to_proj:.1f} m")
            
                    if dist_candidate_to_proj > MAX_ACCEPT_DIST_M:
                        print("⚠️ VS projection too far from median (> MAX_ACCEPT_DIST_M). Using fallback reach selection.")
                        cand["dist_center_to_median"] = cand["reach_center_m"].apply(
                            lambda c: c.distance(median_point_m)
                        )
                        sword_reach = cand.loc[cand["dist_center_to_median"].idxmin()]
            
                        river_line_m = sword_reach["geometry_m"]
                        proj_dist_on_reach = river_line_m.project(median_point_m)
                        VS_m = river_line_m.interpolate(proj_dist_on_reach)
                        VS_method = "fallback_center_selection"
            
                        Dist_VS_km = proj_dist_on_reach / 1000.0
                        reach_id_col = next((c for c in ["reach_id", "rch_id_dn", "reach_id_dn"]
                                             if c in sword_reach.index), None)
                        reach_id_val = sword_reach.get(reach_id_col)
            
                        print(f" → Fallback selected reach: {reach_id_col} = {reach_id_val}")
                        print(f"   VS_method = {VS_method} | Dist_VS = {Dist_VS_km:.3f} km")
            
                    # -----------------------------------------------------------
                    # 7) Retrieve SWORD slope
                    # -----------------------------------------------------------
                    slope_col = None
                    for cand_col in [sword_slope_col, "slope", "slope_m_per_km", "slope_mkm"]:
                        if cand_col is not None and cand_col in sword_reach.index:
                            slope_col = cand_col
                            break
            
                    if slope_col is None:
                        raise RuntimeError("Slope column not found in SWORD after reach selection.")
            
                    slope_m_per_km = float(sword_reach[slope_col])
                    slope_source = f"SWORD ({slope_col})"
                    print(f"   → slope = {slope_m_per_km:.5f} m/km")
            
                    # -----------------------------------------------------------
                    # 8) SSH correction: project points onto centerline and correct
                    # -----------------------------------------------------------
                    gdf_buffer["ssh_uncorr"] = gdf_buffer["ssh"]
            
                    Dist_km = []
                    pts_idx = []
                    SSH_list = []
            
                    for _, row in gdf_buffer.iterrows():
                        p = shp_transform(to_m, Point(row["lon"], row["lat"]))
                        D = river_line_m.project(p) / 1000.0
                        Dist_km.append(D)
                        pts_idx.append(p)
                        SSH_list.append(row["ssh"])
            
                    Dist_km = np.array(Dist_km)
                    SSH_arr = np.array(SSH_list, dtype=float)
            
                    valid_mask = ~np.isnan(SSH_arr) & ~np.isnan(Dist_km)
            
                    if np.sum(valid_mask) < 3:
                        print("⚠️ Too few valid points to estimate orientation/slope → no SWORD correction.")
                        gdf_buffer["ssh_corr"] = gdf_buffer["ssh"]
                    else:
                        try:
                            fit = np.polyfit(Dist_km[valid_mask], SSH_arr[valid_mask], 1)
                            fit_slope = fit[0]
                        except Exception:
                            fit_slope = np.nan
            
                        geometry_length_km = river_line_m.length / 1000.0
                        flipped = False
            
                        if not np.isnan(fit_slope) and slope_m_per_km != 0.0:
                            if (fit_slope * slope_m_per_km) > 0:
                                print("INFO: geometry orientation likely reversed → flipping D")
                                Dist_km = geometry_length_km - Dist_km
                                Dist_VS_km = (river_line_m.length / 1000.0) - Dist_VS_km
                                flipped = True
            
                        d_km = Dist_km - Dist_VS_km
                        SSHcorr = SSH_arr - slope_m_per_km * d_km
            
                        gdf_buffer["Dist_km"] = Dist_km.tolist()
                        gdf_buffer["Dist_VS_km"] = Dist_VS_km
                        gdf_buffer["d_km"] = d_km.tolist()
                        gdf_buffer["ssh_corr"] = SSHcorr.tolist()
                        gdf_buffer["VS_method"] = VS_method + ("|flipped" if flipped else "")
                        gdf_buffer["slope_source"] = slope_source
                        gdf_buffer["slope_m_per_km"] = slope_m_per_km
            
                    debug_cols = [c for c in ["reach_id", "rch_id_dn", "reach_len", "slope", "facc", "dist_out"]
                                  if c in sword_reach.index]
                    print("DEBUG reach:", {c: sword_reach[c] for c in debug_cols})
            
                except Exception as e:
                    print(f"⚠️ SWORD correction error: {e}")
                    gdf_buffer["ssh_corr"] = gdf_buffer["ssh"]
        
    # 6) Robust aggregation (median + MAD)
    ssh_values = gdf_buffer["ssh_corr"].values
    n_valid = np.sum(~np.isnan(ssh_values))
    print(f"    - total SSH points in buffer: {len(ssh_values)} ; valid: {n_valid}")
    
    if n_valid > 0:
        ssh_median = np.nanmedian(ssh_values)
        mad = np.nanmedian(np.abs(ssh_values - ssh_median))
        sigma_approx = 1.4826 * mad if not np.isnan(mad) else 0.0
        date_median = pd.to_datetime(gdf_buffer["date"]).median()
    
        dfs_station.append({
            "date": pd.to_datetime(date_median),
            "lat": float(np.nanmedian(gdf_buffer["lat"])),
            "lon": float(np.nanmedian(gdf_buffer["lon"])),
            "ssh": float(ssh_median),
            "ssh_sigma_mad": float(sigma_approx),
            "n_points": int(len(gdf_buffer)),
            "n_valid": int(n_valid),
            "slope_sword_m_per_km": float(slope_m_per_km),
            "slope_source": slope_source,
            "tract_file": os.path.basename(file),
        })
    
    except Exception as e:
        print(f"❌ Error with {os.path.basename(file)} → {type(e).__name__}: {e}")
        continue
    finally:
        try:
            if ds_main is not None:
                ds_main.close()
        except Exception:
            pass
        try:
            if ds_geo is not None:
                ds_geo.close()
        except Exception:
            pass
    
    # --- Save results ---
    if dfs_station:
        df_all = pd.DataFrame(dfs_station).sort_values("date").reset_index(drop=True)
        station_output = os.path.join(output_path, station_name, tract)
        os.makedirs(station_output, exist_ok=True)
        output_file = os.path.join(station_output, f"{station_name}_{tract}_ssh.csv")
        df_all.to_csv(output_file, index=False)
    
        print(f"✅ SSH time series saved: {station_name} ({tract}) — {len(df_all)} passes")
    
        # Summary diagnostics
        print("  ▶ Summary diagnostics (excerpts):")
        print(f"    - first/last dates: {df_all['date'].iloc[0]} → {df_all['date'].iloc[-1]}")
        print(f"    - global median SSH: {df_all['ssh'].median():.3f} m ; median MAD sigma: {df_all['ssh_sigma_mad'].median():.3f} m")
        print(f"    - average cluster size (n_points): {int(df_all['n_points'].median())}")
    else:
        print(f"⚠️ No valid points for {station_name} ({tract}).")
    
    print("\nProcessing completed.")
