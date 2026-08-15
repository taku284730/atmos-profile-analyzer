# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import metpy.calc as mpcalc
from metpy.plots import SkewT
from metpy.units import units


# ============================================================
# 日本語フォント（Mac）
# ============================================================

plt.rcParams["font.family"] = "Hiragino Sans"


# ============================================================
# 高層気象観測所
# ============================================================

stations = {
    "稚内": 47401,
    "札幌": 47412,
    "釧路": 47418,
    "秋田": 47582,
    "輪島": 47600,
    "館野": 47646,
    "八丈島": 47678,
    "松江": 47741,
    "潮岬": 47778,
    "福岡": 47807,
    "鹿児島": 47827,
    "名瀬": 47909,
    "本茶峠": 47909,
    "石垣島": 47918,
    "南大東島": 47945,
    "父島": 47971,
    "南鳥島": 47991,
}


# ============================================================
# 対流解析エマグラム
# ============================================================

def draw_emagram_convective(station, date, hour):

    # --------------------------------------------------------
    # 入力
    # --------------------------------------------------------

    if station not in stations:
        raise ValueError(
            f"『{station}』は登録されていない地点名です。"
        )

    if hour not in [9, 21]:
        raise ValueError(
            "観測時刻は9または21を指定してください。"
        )

    # Streamlitのdate_input対策
    if hasattr(date, "strftime"):
        date = date.strftime("%Y-%m-%d")

    year, month, day = map(
        int,
        date.split("-")
    )

    point = stations[station]


    # ========================================================
    # 気象庁から取得
    # ========================================================

    url = (
        "https://www.data.jma.go.jp/stats/etrn/upper/view/hourly_usp.php"
        f"?year={year}"
        f"&month={month}"
        f"&day={day}"
        f"&hour={hour}"
        f"&atm="
        f"&point={point}"
        f"&view="
    )

    tables = pd.read_html(url)

    # 0：地上
    # 1：指定気圧面
    ground = tables[0].copy()
    upper = tables[1].copy()


    # ========================================================
    # 数値化
    # ========================================================

    for col in [
        "気温(℃)",
        "相対湿度(%)",
        "風速(m/s)",
        "風向(°)"
    ]:
        upper[col] = pd.to_numeric(
            upper[col],
            errors="coerce"
        )

    for col in [
        "気圧(hPa)",
        "気温(℃)",
        "相対湿度(%)",
        "風速(m/s)",
        "風向(°)"
    ]:
        ground[col] = pd.to_numeric(
            ground[col],
            errors="coerce"
        )


    # ========================================================
    # 上空データ
    # ========================================================

    prss = (
        upper["気圧(hPa)"].to_numpy()
        * units.hPa
    )

    tmpr = (
        upper["気温(℃)"].to_numpy()
        * units.degC
    )

    rhmd = (
        upper["相対湿度(%)"].to_numpy()
    )

    wndsp = (
        upper["風速(m/s)"].to_numpy()
        * units("m/s")
    )

    wnddr = (
        upper["風向(°)"].to_numpy()
        * units.degrees
    )


    # ========================================================
    # 露点・風
    # ========================================================

    dewp = mpcalc.dewpoint_from_relative_humidity(
        tmpr,
        rhmd / 100.0
    )

    uwnd, vwnd = mpcalc.wind_components(
        wndsp,
        wnddr
    )


    # ========================================================
    # SSI（数値だけ）
    # ========================================================

    ssi = mpcalc.showalter_index(
        prss,
        tmpr,
        dewp
    )[0]


    # ========================================================
    # 地上観測値
    # ========================================================

    p0 = (
        ground["気圧(hPa)"].iloc[0]
        * units.hPa
    )

    T0 = (
        ground["気温(℃)"].iloc[0]
        * units.degC
    )

    RH0 = (
        ground["相対湿度(%)"].iloc[0]
    )

    Td0 = mpcalc.dewpoint_from_relative_humidity(
        T0,
        RH0 / 100.0
    )


    # ========================================================
    # Surface-based解析用プロファイル
    # ========================================================

    valid = (
        ~np.isnan(tmpr.magnitude)
        & ~np.isnan(dewp.magnitude)
    )

    p_valid = prss[valid]
    T_valid = tmpr[valid]
    Td_valid = dewp[valid]


    # 地上を追加
    p_sb = np.concatenate([
        [p0.magnitude],
        p_valid.magnitude
    ]) * units.hPa

    T_sb = np.concatenate([
        [T0.magnitude],
        T_valid.magnitude
    ]) * units.degC

    Td_sb = np.concatenate([
        [Td0.to("degC").magnitude],
        Td_valid.to("degC").magnitude
    ]) * units.degC


    # 地上より高圧の点を除外
    mask = (
        p_sb <= p0
    )

    p_sb = p_sb[mask]
    T_sb = T_sb[mask]
    Td_sb = Td_sb[mask]


    # 高圧 → 低圧
    order = np.argsort(
        -p_sb.magnitude
    )

    p_sb = p_sb[order]
    T_sb = T_sb[order]
    Td_sb = Td_sb[order]


    # ========================================================
    # Surface Parcel
    # ========================================================

    parcel_sb = mpcalc.parcel_profile(
        p_sb,
        T_sb[0],
        Td_sb[0]
    )


    # ========================================================
    # SBCAPE / SBCIN
    # ========================================================

    sbcape, sbcin = mpcalc.surface_based_cape_cin(
        p_sb,
        T_sb,
        Td_sb
    )


    # ========================================================
    # LCL
    # ========================================================

    p_lcl, t_lcl = mpcalc.lcl(
        p_sb[0],
        T_sb[0],
        Td_sb[0]
    )


    # ========================================================
    # LFC
    # ========================================================

    p_lfc, t_lfc = mpcalc.lfc(
        p_sb,
        T_sb,
        Td_sb,
        parcel_temperature_profile=parcel_sb
    )


    # ========================================================
    # EL
    # ========================================================

    p_el, t_el = mpcalc.el(
        p_sb,
        T_sb,
        Td_sb,
        parcel_temperature_profile=parcel_sb
    )


    # ========================================================
    # エマグラム
    # ========================================================

    xmin = -90
    xmax = 40

    ymin = 100
    ymax = 1020

    fig = plt.figure(
        figsize=(210 / 25.4, 294 / 25.4),
        dpi=100
    )

    skew = SkewT(
        fig,
        rotation=0,
        aspect=150
    )

    skew.ax.set_xlim(
        xmin,
        xmax
    )

    skew.ax.set_ylim(
        ymax,
        ymin
    )

    skew.ax.set_xlabel(
        "Temperature (℃)"
    )

    skew.ax.set_ylabel(
        "Pressure (hPa)"
    )


    # ========================================================
    # タイトル
    # ========================================================

    skew.ax.set_title(
        f"{station}  {year}/{month}/{day}  {hour} JST",
        loc="left"
    )

    skew.ax.set_title(
        (
            f"SSI={ssi.magnitude:.2f}   "
            f"SBCAPE={sbcape.magnitude:.0f} J/kg   "
            f"SBCIN={sbcin.magnitude:.0f} J/kg"
        ),
        loc="right",
        fontsize=9
    )


    # ========================================================
    # 気温・露点・風
    # ========================================================

    skew.plot(
        prss,
        tmpr,
        "red",
        linewidth=2,
        label="Temperature"
    )

    skew.plot(
        prss,
        dewp,
        "blue",
        linewidth=2,
        label="Dew Point"
    )

    skew.plot_barbs(
        prss,
        uwnd,
        vwnd
    )


    # ========================================================
    # Surface Parcel
    # ========================================================

    skew.plot(
        p_sb,
        parcel_sb,
        color="darkorange",
        linestyle="--",
        linewidth=2,
        label="Surface Parcel"
    )


    # ========================================================
    # CAPE / CIN
    # ========================================================

    skew.shade_cape(
        p_sb,
        T_sb,
        parcel_sb,
        color="red",
        alpha=0.35
    )

    skew.shade_cin(
        p_sb,
        T_sb,
        parcel_sb,
        Td_sb,
        color="royalblue",
        alpha=0.30
    )


    # ========================================================
    # 乾燥断熱線
    # ========================================================

    dry_t0 = (
        np.arange(
            200,
            360,
            10
        )
        * units.K
    )

    skew.plot_dry_adiabats(
        t0=dry_t0,
        lw=0.5,
        colors="red"
    )

    for t in dry_t0:

        p1 = 350 * units.hPa

        t1 = mpcalc.dry_lapse(
            p1,
            t,
            1000 * units.hPa
        )

        if t1 < xmin * units.degC:
            continue

        skew.ax.text(
            t1,
            p1,
            f"{t.magnitude}",
            fontsize=9,
            horizontalalignment="center",
            color="red"
        )


    # ========================================================
    # 湿潤断熱線
    # ========================================================

    moist_t0 = (
        np.arange(
            245,
            320,
            5
        )
        * units.K
    )

    skew.plot_moist_adiabats(
        t0=moist_t0,
        lw=0.5,
        colors="green"
    )

    for t in moist_t0:

        p1 = 250 * units.hPa

        t1 = mpcalc.moist_lapse(
            p1,
            t,
            1000 * units.hPa
        )

        if t1 < xmin * units.degC:
            continue

        skew.ax.text(
            t1,
            p1,
            f"{t.magnitude}",
            fontsize=9,
            horizontalalignment="center",
            color="green"
        )


    # ========================================================
    # 等飽和混合比線
    # ========================================================

    mixing_ratio = np.array([
        0.2,
        0.4,
        0.6,
        1,
        2,
        4,
        5,
        10,
        15,
        20,
        25,
        30,
        35
    ]).reshape(-1, 1) * units("g/kg")

    pressure = (
        np.arange(
            1000,
            10,
            -50
        )
        * units.hPa
    )

    skew.plot_mixing_lines(
        mixing_ratio=mixing_ratio,
        pressure=pressure,
        lw=0.5,
        colors="blue"
    )


    # ========================================================
    # 混合比ラベル
    # ========================================================

    for mr in mixing_ratio.flatten():

        p1 = 110 * units.hPa

        dewpt_label = mpcalc.dewpoint(
            mpcalc.vapor_pressure(
                p1,
                mr
            )
        )

        x = dewpt_label.to(
            "degC"
        ).magnitude

        if xmin <= x <= xmax:

            skew.ax.text(
                x,
                p1.magnitude,
                f"{mr.magnitude:g}",
                fontsize=8,
                horizontalalignment="center",
                color="blue"
            )


    # ========================================================
    # LCL
    # ========================================================

    skew.ax.plot(
        t_lcl.to("degC").magnitude,
        p_lcl.magnitude,
        "o",
        color="darkorange",
        markersize=7,
        zorder=10
    )

    skew.ax.annotate(
        f"LCL {p_lcl.magnitude:.0f}",
        xy=(
            t_lcl.to("degC").magnitude,
            p_lcl.magnitude
        ),
        xytext=(8, -15),
        textcoords="offset points",
        color="darkorange",
        fontsize=8
    )


    # ========================================================
    # LFC
    # ========================================================

    if not np.isnan(p_lfc.magnitude):

        skew.ax.plot(
            t_lfc.to("degC").magnitude,
            p_lfc.magnitude,
            "o",
            color="purple",
            markersize=7,
            zorder=10
        )

        skew.ax.annotate(
            f"LFC {p_lfc.magnitude:.0f}",
            xy=(
                t_lfc.to("degC").magnitude,
                p_lfc.magnitude
            ),
            xytext=(-45, 8),
            textcoords="offset points",
            color="purple",
            fontsize=8
        )


    # ========================================================
    # EL
    # ========================================================

    if not np.isnan(p_el.magnitude):

        skew.ax.plot(
            t_el.to("degC").magnitude,
            p_el.magnitude,
            "o",
            color="green",
            markersize=7,
            zorder=10
        )

        skew.ax.annotate(
            f"EL {p_el.magnitude:.0f}",
            xy=(
                t_el.to("degC").magnitude,
                p_el.magnitude
            ),
            xytext=(-40, 8),
            textcoords="offset points",
            color="green",
            fontsize=8
        )


    # ========================================================
    # 凡例
    # ========================================================

    skew.ax.legend(
        loc="lower left"
    )
  
    # ========================================================
    # Webへ返す
    # ========================================================

    results = {
        "SSI": ssi.magnitude,
        "SBCAPE": sbcape.magnitude,
        "SBCIN": sbcin.magnitude,
        "LCL": p_lcl.magnitude,
        "LFC": (
            None
            if np.isnan(p_lfc.magnitude)
            else p_lfc.magnitude
        ),
        "EL": (
            None
            if np.isnan(p_el.magnitude)
            else p_el.magnitude
        ),
    }

    return fig, results