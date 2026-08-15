# -*- coding: utf-8 -*-

import os
import warnings
from datetime import datetime, timedelta

import cdsapi
import cfgrib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import metpy.calc as mpcalc
from metpy.plots import SkewT
from metpy.units import units


warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
)

plt.rcParams["font.family"] = "Hiragino Sans"


PRESSURE_LEVELS = [
    "1000", "975", "950", "925", "900", "875", "850", "825", "800",
    "775", "750", "700", "650", "600", "550", "500", "450", "400",
    "350", "300", "250", "225", "200", "175", "150", "125", "100",
    "70", "50", "30", "20", "10", "7", "5", "3", "2", "1",
]

LABEL_PRESSURE_LEVELS = {900, 850, 700, 500, 300, 200, 100}


STATIONS = {
    "稚内": (45 + 24.9 / 60, 141 + 40.7 / 60),
    "札幌": (43 + 3.6 / 60, 141 + 19.7 / 60),
    "釧路": (42 + 57.2 / 60, 144 + 26.3 / 60),
    "秋田": (39 + 43.1 / 60, 140 + 6.0 / 60),
    "輪島": (37 + 23.5 / 60, 136 + 53.7 / 60),
    "館野": (36 + 3.5 / 60, 140 + 7.5 / 60),
    "八丈島": (33 + 7.3 / 60, 139 + 46.7 / 60),
    "松江": (35 + 27.5 / 60, 133 + 4.0 / 60),
    "潮岬": (33 + 27.1 / 60, 135 + 45.7 / 60),
    "福岡": (33 + 35.0 / 60, 130 + 23.0 / 60),
    "鹿児島": (31 + 33.3 / 60, 130 + 32.9 / 60),
    "名瀬": (28 + 23.6 / 60, 129 + 33.2 / 60),
    "石垣島": (24 + 20.2 / 60, 124 + 9.8 / 60),
    "南大東島": (25 + 49.8 / 60, 131 + 13.7 / 60),
    "父島": (27 + 5.7 / 60, 142 + 11.1 / 60),
    "南鳥島": (24 + 17.4 / 60, 153 + 59.0 / 60),
}


def coordinate_tag(value):
    return f"{value:.2f}".replace("-", "m").replace(".", "p")


def select_nearest_grid(ds, target_lat, target_lon):
    """複数格子が含まれている場合、指定地点に最も近い1格子を選ぶ。"""

    indexers = {}

    if "latitude" in ds.dims:
        indexers["latitude"] = target_lat

    if "longitude" in ds.dims:
        indexers["longitude"] = target_lon

    if indexers:
        ds = ds.sel(
            indexers,
            method="nearest",
        )

    return ds


def download_era5_profile(
    lat,
    lon,
    date,
    hour_jst,
    cache_dir="era5_cache",
):
    """ERA5気圧面37層のT/RH/U/Vを取得する。"""

    os.makedirs(cache_dir, exist_ok=True)

    dt_jst = datetime.strptime(
        f"{date} {hour_jst:02d}:00",
        "%Y-%m-%d %H:%M",
    )
    dt_utc = dt_jst - timedelta(hours=9)

    lat_tag = coordinate_tag(lat)
    lon_tag = coordinate_tag(lon)

    output_file = os.path.join(
        cache_dir,
        (
            f"era5_profile_{lat_tag}_{lon_tag}_"
            f"{dt_jst:%Y%m%d_%H}JST.grib"
        ),
    )

    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        return output_file, dt_jst, dt_utc, True

    north = lat + 0.125
    west = lon - 0.125
    south = lat - 0.125
    east = lon + 0.125

    request = {
        "product_type": ["reanalysis"],
        "variable": [
            "temperature",
            "relative_humidity",
            "u_component_of_wind",
            "v_component_of_wind",
        ],
        "year": [f"{dt_utc.year:04d}"],
        "month": [f"{dt_utc.month:02d}"],
        "day": [f"{dt_utc.day:02d}"],
        "time": [f"{dt_utc.hour:02d}:00"],
        "pressure_level": PRESSURE_LEVELS,
        "data_format": "grib",
        "download_format": "unarchived",
        "area": [north, west, south, east],
    }

    client = cdsapi.Client()
    client.retrieve(
        "reanalysis-era5-pressure-levels",
        request,
    ).download(output_file)

    return output_file, dt_jst, dt_utc, False


def download_era5_surface_state(
    lat,
    lon,
    dt_jst,
    dt_utc,
    cache_dir="era5_cache",
):
    """ERA5のsurface pressure + 2m T + 2m Tdを取得する。"""

    os.makedirs(cache_dir, exist_ok=True)

    lat_tag = coordinate_tag(lat)
    lon_tag = coordinate_tag(lon)

    output_file = os.path.join(
        cache_dir,
        (
            f"era5_surface_state_{lat_tag}_{lon_tag}_"
            f"{dt_jst:%Y%m%d_%H}JST.grib"
        ),
    )

    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        return output_file, True

    north = lat + 0.125
    west = lon - 0.125
    south = lat - 0.125
    east = lon + 0.125

    request = {
        "product_type": ["reanalysis"],
        "variable": [
            "surface_pressure",
            "2m_temperature",
            "2m_dewpoint_temperature",
        ],
        "year": [f"{dt_utc.year:04d}"],
        "month": [f"{dt_utc.month:02d}"],
        "day": [f"{dt_utc.day:02d}"],
        "time": [f"{dt_utc.hour:02d}:00"],
        "data_format": "grib",
        "download_format": "unarchived",
        "area": [north, west, south, east],
    }

    client = cdsapi.Client()
    client.retrieve(
        "reanalysis-era5-single-levels",
        request,
    ).download(output_file)

    return output_file, False


def get_era5_profile(
    grib_file,
    target_lat,
    target_lon,
):
    """気圧面GRIBをMetPy用プロファイルへ変換する。"""

    datasets = cfgrib.open_datasets(grib_file)

    required = {"t", "r", "u", "v"}
    ds = None

    for candidate in datasets:
        if required.issubset(set(candidate.data_vars)):
            ds = candidate
            break

    if ds is None:
        raise ValueError(
            "GRIB内に気温・相対湿度・風成分がそろった"
            "気圧面Datasetが見つかりません。"
        )

    ds = select_nearest_grid(
        ds,
        target_lat=target_lat,
        target_lon=target_lon,
    )

    prss = ds["isobaricInhPa"].values * units.hPa

    tmpr = (
        ds["t"].values
        * units.kelvin
    ).to("degC")

    rhmd = ds["r"].values

    dewp = mpcalc.dewpoint_from_relative_humidity(
        tmpr,
        rhmd / 100.0,
    )

    uwnd = ds["u"].values * units("m/s")
    vwnd = ds["v"].values * units("m/s")

    latitude = float(
        np.asarray(ds["latitude"].values).squeeze()
    )
    longitude = float(
        np.asarray(ds["longitude"].values).squeeze()
    )
    valid_time = ds["valid_time"].values

    order = np.argsort(prss.magnitude)[::-1]

    return (
        prss[order],
        tmpr[order],
        dewp[order],
        rhmd[order],
        uwnd[order],
        vwnd[order],
        latitude,
        longitude,
        valid_time,
    )


def _find_variable(datasets, candidate_names):
    for ds in datasets:
        for name in candidate_names:
            if name in ds.data_vars:
                return ds, name

    return None, None


def get_era5_surface_state(
    grib_file,
    target_lat,
    target_lon,
):
    """ERA5地上状態を読み込む。"""

    datasets = cfgrib.open_datasets(grib_file)

    ds_sp, key_sp = _find_variable(datasets, ["sp"])
    ds_t2m, key_t2m = _find_variable(datasets, ["t2m", "2t"])
    ds_d2m, key_d2m = _find_variable(datasets, ["d2m", "2d"])

    if ds_sp is None or ds_t2m is None or ds_d2m is None:
        raise ValueError(
            "ERA5地上状態GRIBから必要な変数を読み込めませんでした。"
        )

    ds_sp = select_nearest_grid(
        ds_sp,
        target_lat,
        target_lon,
    )
    ds_t2m = select_nearest_grid(
        ds_t2m,
        target_lat,
        target_lon,
    )
    ds_d2m = select_nearest_grid(
        ds_d2m,
        target_lat,
        target_lon,
    )

    surface_pressure_hpa = (
        float(np.asarray(ds_sp[key_sp].values).squeeze())
        / 100.0
    )

    surface_temperature = (
        float(np.asarray(ds_t2m[key_t2m].values).squeeze())
        * units.kelvin
    ).to("degC")

    surface_dewpoint = (
        float(np.asarray(ds_d2m[key_d2m].values).squeeze())
        * units.kelvin
    ).to("degC")

    surface_latitude = float(
        np.asarray(ds_sp["latitude"].values).squeeze()
    )
    surface_longitude = float(
        np.asarray(ds_sp["longitude"].values).squeeze()
    )

    return (
        surface_pressure_hpa,
        surface_temperature,
        surface_dewpoint,
        surface_latitude,
        surface_longitude,
    )


def draw_era5_convective(
    place_name,
    lat,
    lon,
    date,
    hour_jst,
    cache_dir="era5_cache",
):
    """
    ERA5を取得し、対流解析エマグラムを描く。

    Returns
    -------
    fig : matplotlib.figure.Figure
    results : dict
    profile_df : pandas.DataFrame
    """

    profile_file, dt_jst, dt_utc, profile_cached = download_era5_profile(
        lat=lat,
        lon=lon,
        date=date,
        hour_jst=hour_jst,
        cache_dir=cache_dir,
    )

    (
        prss,
        tmpr,
        dewp,
        rhmd,
        uwnd,
        vwnd,
        latitude,
        longitude,
        valid_time,
    ) = get_era5_profile(
        profile_file,
        target_lat=lat,
        target_lon=lon,
    )

    surface_file, surface_cached = download_era5_surface_state(
        lat=lat,
        lon=lon,
        dt_jst=dt_jst,
        dt_utc=dt_utc,
        cache_dir=cache_dir,
    )

    (
        surface_pressure_hpa,
        T0,
        Td0,
        surface_latitude,
        surface_longitude,
    ) = get_era5_surface_state(
        surface_file,
        target_lat=lat,
        target_lon=lon,
    )

    p0 = surface_pressure_hpa * units.hPa

    # 地下気圧面を除外
    above_ground = prss.magnitude <= surface_pressure_hpa

    prss = prss[above_ground]
    tmpr = tmpr[above_ground]
    dewp = dewp[above_ground]
    rhmd = rhmd[above_ground]
    uwnd = uwnd[above_ground]
    vwnd = vwnd[above_ground]

    # SSI
    if 850 in prss.magnitude and 500 in prss.magnitude:
        ssi = mpcalc.showalter_index(
            prss,
            tmpr,
            dewp,
        )[0]
        ssi_value = float(ssi.magnitude)
    else:
        ssi = None
        ssi_value = None

    # Surface based profile
    valid = (
        ~np.isnan(tmpr.magnitude)
        & ~np.isnan(dewp.magnitude)
    )

    p_valid = prss[valid]
    T_valid = tmpr[valid]
    Td_valid = dewp[valid]

    p_sb = np.concatenate([
        [p0.magnitude],
        p_valid.magnitude,
    ]) * units.hPa

    T_sb = np.concatenate([
        [T0.magnitude],
        T_valid.to("degC").magnitude,
    ]) * units.degC

    Td_sb = np.concatenate([
        [Td0.magnitude],
        Td_valid.to("degC").magnitude,
    ]) * units.degC

    mask = p_sb <= p0
    p_sb = p_sb[mask]
    T_sb = T_sb[mask]
    Td_sb = Td_sb[mask]

    order = np.argsort(-p_sb.magnitude)
    p_sb = p_sb[order]
    T_sb = T_sb[order]
    Td_sb = Td_sb[order]

    parcel_sb = mpcalc.parcel_profile(
        p_sb,
        T_sb[0],
        Td_sb[0],
    )

    sbcape, sbcin = mpcalc.surface_based_cape_cin(
        p_sb,
        T_sb,
        Td_sb,
    )

    p_lcl, t_lcl = mpcalc.lcl(
        p_sb[0],
        T_sb[0],
        Td_sb[0],
    )

    p_lfc, t_lfc = mpcalc.lfc(
        p_sb,
        T_sb,
        Td_sb,
        parcel_temperature_profile=parcel_sb,
    )

    p_el, t_el = mpcalc.el(
        p_sb,
        T_sb,
        Td_sb,
        parcel_temperature_profile=parcel_sb,
    )

    # ========================================================
    # Figure
    # ========================================================

    xmin = -90
    xmax = 40
    ymin = 100
    ymax = 1020

    fig = plt.figure(
        figsize=(210 / 25.4, 294 / 25.4),
        dpi=100,
    )

    skew = SkewT(
        fig,
        rotation=0,
        aspect=150,
    )

    skew.ax.set_xlim(xmin, xmax)
    skew.ax.set_ylim(ymax, ymin)

    skew.ax.set_xlabel("Temperature (℃)")
    skew.ax.set_ylabel("Pressure (hPa)")

    skew.ax.set_title(
        f"ERA5 {place_name}  {dt_jst:%Y/%m/%d %H} JST",
        loc="left",
    )

    ssi_text = (
        f"{ssi_value:.2f}"
        if ssi_value is not None
        else "N/A"
    )

    skew.ax.set_title(
        (
            f"SSI={ssi_text}   "
            f"SBCAPE={sbcape.magnitude:.0f} J/kg   "
            f"SBCIN={sbcin.magnitude:.0f} J/kg"
        ),
        loc="right",
        fontsize=9,
    )

    # Surface pressure
    if ymin <= surface_pressure_hpa <= ymax:
        skew.ax.axhline(
            surface_pressure_hpa,
            color="gray",
            linestyle=":",
            linewidth=1.2,
            zorder=1,
        )

        skew.ax.text(
            xmin + 3,
            surface_pressure_hpa,
            f" Surface {surface_pressure_hpa:.0f} hPa",
            fontsize=8,
            color="gray",
            va="bottom",
            ha="left",
        )

    # T / Td / wind
    skew.plot(
        prss,
        tmpr,
        color="red",
        linewidth=2,
        marker="o",
        label="Temperature",
    )

    skew.plot(
        prss,
        dewp,
        color="blue",
        linewidth=2,
        marker="o",
        label="Dew Point",
    )

    skew.plot_barbs(
        prss,
        uwnd,
        vwnd,
    )

    # Surface parcel
    skew.plot(
        p_sb,
        parcel_sb,
        color="darkorange",
        linestyle="--",
        linewidth=2,
        label="Surface Parcel",
    )

    skew.ax.plot(
        T_sb[0].magnitude,
        p_sb[0].magnitude,
        marker="o",
        color="darkorange",
        markersize=7,
        zorder=10,
    )

    # CAPE/CIN
    skew.shade_cape(
        p_sb,
        T_sb,
        parcel_sb,
        color="red",
        alpha=0.35,
    )

    skew.shade_cin(
        p_sb,
        T_sb,
        parcel_sb,
        Td_sb,
        color="royalblue",
        alpha=0.30,
    )

    # Background
    dry_t0 = np.arange(200, 360, 10) * units.K
    skew.plot_dry_adiabats(
        t0=dry_t0,
        lw=0.5,
        colors="red",
    )

    moist_t0 = np.arange(245, 320, 5) * units.K
    skew.plot_moist_adiabats(
        t0=moist_t0,
        lw=0.5,
        colors="green",
    )

    mixing_ratio = np.array([
        0.2, 0.4, 0.6, 1, 2, 4, 5,
        10, 15, 20, 25, 30, 35,
    ]).reshape(-1, 1) * units("g/kg")

    mixing_pressure = (
        np.arange(1000, 10, -50)
        * units.hPa
    )

    skew.plot_mixing_lines(
        mixing_ratio=mixing_ratio,
        pressure=mixing_pressure,
        lw=0.5,
        colors="blue",
    )

    # Mixing ratio labels
    for mr in mixing_ratio.flatten():
        p1 = 110 * units.hPa

        dewpt_label = mpcalc.dewpoint(
            mpcalc.vapor_pressure(
                p1,
                mr,
            )
        )

        x = dewpt_label.to("degC").magnitude

        if xmin <= x <= xmax:
            skew.ax.text(
                x,
                p1.magnitude,
                f"{mr.magnitude:g}",
                fontsize=8,
                horizontalalignment="center",
                color="blue",
            )

    # LCL
    skew.ax.plot(
        t_lcl.to("degC").magnitude,
        p_lcl.magnitude,
        "o",
        color="darkorange",
        markersize=7,
        zorder=10,
    )

    skew.ax.annotate(
        f"LCL {p_lcl.magnitude:.0f}",
        xy=(
            t_lcl.to("degC").magnitude,
            p_lcl.magnitude,
        ),
        xytext=(8, -15),
        textcoords="offset points",
        color="darkorange",
        fontsize=8,
    )

    # LFC
    if not np.isnan(p_lfc.magnitude):
        skew.ax.plot(
            t_lfc.to("degC").magnitude,
            p_lfc.magnitude,
            "o",
            color="purple",
            markersize=7,
            zorder=10,
        )

        skew.ax.annotate(
            f"LFC {p_lfc.magnitude:.0f}",
            xy=(
                t_lfc.to("degC").magnitude,
                p_lfc.magnitude,
            ),
            xytext=(-45, 8),
            textcoords="offset points",
            color="purple",
            fontsize=8,
        )

    # EL
    if not np.isnan(p_el.magnitude):
        skew.ax.plot(
            t_el.to("degC").magnitude,
            p_el.magnitude,
            "o",
            color="green",
            markersize=7,
            zorder=10,
        )

        skew.ax.annotate(
            f"EL {p_el.magnitude:.0f}",
            xy=(
                t_el.to("degC").magnitude,
                p_el.magnitude,
            ),
            xytext=(-40, 8),
            textcoords="offset points",
            color="green",
            fontsize=8,
        )

    # Major pressure labels
    for p, t in zip(prss, tmpr):
        p_value = int(round(p.magnitude))

        if p_value not in LABEL_PRESSURE_LEVELS:
            continue

        skew.ax.annotate(
            f"{p_value}",
            xy=(
                t.magnitude,
                p.magnitude,
            ),
            xytext=(6, 0),
            textcoords="offset points",
            fontsize=7,
            color="red",
        )

    skew.ax.legend(
        loc="lower left",
    )

    # Profile table
    wind_speed = mpcalc.wind_speed(
        uwnd,
        vwnd,
    )

    wind_direction = mpcalc.wind_direction(
        uwnd,
        vwnd,
    )

    profile_df = pd.DataFrame({
        "気圧(hPa)": prss.magnitude,
        "気温(℃)": tmpr.magnitude,
        "露点(℃)": dewp.to("degC").magnitude,
        "相対湿度(%)": rhmd,
        "風速(m/s)": wind_speed.magnitude,
        "風向(°)": wind_direction.magnitude,
    })

    def _nullable_pressure(value):
        if np.isnan(value.magnitude):
            return None
        return float(value.magnitude)

    results = {
        "SSI": ssi_value,
        "SBCAPE": float(sbcape.magnitude),
        "SBCIN": float(sbcin.magnitude),
        "LCL": float(p_lcl.magnitude),
        "LFC": _nullable_pressure(p_lfc),
        "EL": _nullable_pressure(p_el),
        "SurfacePressure": float(surface_pressure_hpa),
        "SurfaceTemperature": float(T0.magnitude),
        "SurfaceDewpoint": float(Td0.magnitude),
        "RequestedLat": float(lat),
        "RequestedLon": float(lon),
        "GridLat": float(latitude),
        "GridLon": float(longitude),
        "SurfaceGridLat": float(surface_latitude),
        "SurfaceGridLon": float(surface_longitude),
        "ValidTimeUTC": str(valid_time),
        "ProfileCached": bool(profile_cached),
        "SurfaceCached": bool(surface_cached),
    }

    return fig, results, profile_df
