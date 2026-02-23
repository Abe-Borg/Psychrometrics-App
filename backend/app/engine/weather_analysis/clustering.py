"""
K-means clustering of hourly psychrometric states.

Groups 8,760 hourly weather data points into clusters representing distinct
HVAC operating regimes, then extracts per-cluster metadata (hour counts,
centroids, worst-case points).
"""

import numpy as np
import psychrolib
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from app.models.weather_analysis import HourlyPsychroState

DEFAULT_K = 5


def cluster_weather_data(
    states: list[HourlyPsychroState],
    n_clusters: int = DEFAULT_K,
    random_state: int = 42,
) -> dict:
    """
    Cluster hourly psychrometric states using k-means on (Tdb, W).

    Args:
        states: List of HourlyPsychroState (SI units).
        n_clusters: Number of clusters (default 5).
        random_state: Random seed for reproducibility.

    Returns:
        dict with:
            labels: list[int] — cluster assignment per hour (length = len(states))
            cluster_infos: list[dict] — per-cluster info with keys:
                cluster_id, hour_count, fraction_of_year,
                centroid_tdb_c, centroid_w, centroid_state (HourlyPsychroState),
                worst_case_state (HourlyPsychroState), label (str)
    """
    n = len(states)
    if n < n_clusters:
        n_clusters = max(1, n)

    # Build feature matrix: (Tdb_c, humidity_ratio)
    X = np.array([[s.dry_bulb_c, s.humidity_ratio] for s in states])

    # Normalize so both axes contribute equally to distance
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=random_state,
        n_init=10,
        max_iter=300,
    )
    kmeans.fit(X_scaled)

    labels = kmeans.labels_.tolist()

    # Transform centroids back to original scale
    centroids_original = scaler.inverse_transform(kmeans.cluster_centers_)

    # Compute mean pressure across all states for centroid state resolution
    mean_pressure = np.mean([s.pressure_pa for s in states])

    cluster_infos = []
    for cid in range(n_clusters):
        mask = [i for i, lbl in enumerate(labels) if lbl == cid]
        hour_count = len(mask)
        cluster_states = [states[i] for i in mask]

        # Centroid in original coordinates
        centroid_tdb_c = float(centroids_original[cid, 0])
        centroid_w = float(centroids_original[cid, 1])

        # Resolve full psychrometric state at centroid
        centroid_state = _resolve_state_from_tdb_w(
            centroid_tdb_c, centroid_w, mean_pressure
        )

        # Worst-case: highest enthalpy in this cluster
        worst_case = max(cluster_states, key=lambda s: s.enthalpy_j_per_kg)

        # Descriptive label based on centroid conditions
        label = label_cluster(centroid_tdb_c, centroid_state.relative_humidity)

        cluster_infos.append({
            "cluster_id": cid,
            "hour_count": hour_count,
            "fraction_of_year": round(hour_count / n, 4),
            "centroid_tdb_c": centroid_tdb_c,
            "centroid_w": centroid_w,
            "centroid_state": centroid_state,
            "worst_case_state": worst_case,
            "label": label,
        })

    return {
        "labels": labels,
        "cluster_infos": cluster_infos,
    }


def label_cluster(centroid_tdb_c: float, centroid_rh: float) -> str:
    """
    Assign a descriptive label based on centroid conditions.

    Args:
        centroid_tdb_c: Dry-bulb temperature in °C.
        centroid_rh: Relative humidity as fraction (0-1).

    Returns:
        Label like "Warm Humid", "Cool Dry", etc.
    """
    # Convert to °F for labeling thresholds (per IMPLEMENTATION_PLAN.md)
    tdb_f = centroid_tdb_c * 9.0 / 5.0 + 32.0

    if tdb_f >= 90:
        temp_label = "Hot"
    elif tdb_f >= 75:
        temp_label = "Warm"
    elif tdb_f >= 60:
        temp_label = "Mild"
    elif tdb_f >= 45:
        temp_label = "Cool"
    else:
        temp_label = "Cold"

    if centroid_rh >= 0.65:
        moisture_label = "Humid"
    elif centroid_rh >= 0.35:
        moisture_label = "Moderate"
    else:
        moisture_label = "Dry"

    return f"{temp_label} {moisture_label}"


def _resolve_state_from_tdb_w(
    tdb_c: float, w: float, pressure_pa: float
) -> HourlyPsychroState:
    """
    Compute full psychrometric state from Tdb and humidity ratio (SI).
    Used for centroid state resolution.
    """
    psychrolib.SetUnitSystem(psychrolib.SI)

    twb = psychrolib.GetTWetBulbFromHumRatio(tdb_c, w, pressure_pa)
    tdp = psychrolib.GetTDewPointFromHumRatio(tdb_c, w, pressure_pa)
    rh = psychrolib.GetRelHumFromHumRatio(tdb_c, w, pressure_pa)
    h = psychrolib.GetMoistAirEnthalpy(tdb_c, w)
    v = psychrolib.GetMoistAirVolume(tdb_c, w, pressure_pa)

    return HourlyPsychroState(
        month=0,
        day=0,
        hour=0,
        dry_bulb_c=tdb_c,
        wet_bulb_c=twb,
        dewpoint_c=tdp,
        humidity_ratio=w,
        relative_humidity=rh,
        enthalpy_j_per_kg=h,
        specific_volume=v,
        pressure_pa=pressure_pa,
    )
