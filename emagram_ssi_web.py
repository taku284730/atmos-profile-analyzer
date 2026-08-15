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
# SSIエマグラム描画
# ============================================================

def draw_emagram_ssi(station, date, hour):

    # --------------------------------------------------------
    # 入力値を整える
    # --------------------------------------------------------

    if station not in stations:
        raise ValueError(
            f"『{station}』は登録されていない地点名です。"
        )

    if hour not in [9, 21]:
        raise ValueError(
            "観測時刻は9または21を指定してください。"
        )

    # Streamlitのdate_inputはdatetime.dateを返すので文字列へ変換
    if hasattr(date, "strftime"):
        date = date.strftime("%Y-%m-%d")

    year, month, day = map(
        int,
        date.split("-")
    )

    point = stations[station]


    # ========================================================
    # 気象庁から高層観測データ取得
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

    # 0番目：地上
    # 1番目：指定気圧面
    df = tables[1].copy()


    # ========================================================
    # 数値化
    # ========================================================

    cols = [
        "気温(℃)",
        "相対湿度(%)",
        "風速(m/s)",
        "風向(°)"
    ]

    for col in cols:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )


    # ========================================================
    # MetPy用単位
    # ========================================================

    prss = (
        df["気圧(hPa)"].to_numpy()
        * units.hPa
    )

    tmpr = (
        df["気温(℃)"].to_numpy()
        * units.degC
    )

    rhmd = (
        df["相対湿度(%)"].to_numpy()
    )

    wndsp = (
        df["風速(m/s)"].to_numpy()
        * units("m/s")
    )

    wnddr = (
        df["風向(°)"].to_numpy()
        * units.degrees
    )


    # ========================================================
    # 露点・風成分
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
    # SSI
    # ========================================================

    ssi = mpcalc.showalter_index(
        prss,
        tmpr,
        dewp
    )[0]


    # ========================================================
    # 850 hPa / 500 hPa
    # ========================================================

    i850 = np.where(
        prss.magnitude == 850
    )[0][0]

    i500 = np.where(
        prss.magnitude == 500
    )[0][0]

    T850 = tmpr[i850]
    Td850 = dewp[i850]

    T500 = tmpr[i500]


    # ========================================================
    # SSI用LCL
    # ========================================================

    p_lcl, t_lcl = mpcalc.lcl(
        850 * units.hPa,
        T850,
        Td850
    )


    # ========================================================
    # 850 hPa気塊を500 hPaまで持ち上げる
    # ========================================================

    p_parcel = (
        np.linspace(
            850,
            500,
            200
        )
        * units.hPa
    )

    parcel_temp = mpcalc.parcel_profile(
        p_parcel,
        T850,
        Td850
    )

    Tparcel500 = parcel_temp[-1].to(
        "degC"
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
        f"SSI = {ssi.magnitude:.2f}",
        loc="right"
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
    # 850 hPa Parcel
    # ========================================================

    skew.plot(
        p_parcel,
        parcel_temp,
        color="black",
        linewidth=2.5,
        label="850 hPa Parcel"
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
    # 850 hPa露点（LCL導出用）
    # ========================================================

    skew.ax.plot(
        Td850.magnitude,
        850,
        marker="o",
        color="gray",
        markersize=6,
        zorder=10
    )

    skew.ax.annotate(
        "850 hPa\nDew Point",
        xy=(
            Td850.magnitude,
            850
        ),
        xytext=(
            Td850.magnitude - 18,
            905
        ),
        fontsize=8,
        color="gray",
        arrowprops=dict(
            arrowstyle="->",
            color="gray"
        )
    )


    # ========================================================
    # LCL
    # ========================================================

    skew.ax.plot(
        t_lcl.to("degC").magnitude,
        p_lcl.magnitude,
        marker="o",
        color="green",
        markersize=8,
        zorder=10
    )

    skew.ax.annotate(
        (
            "LCL\n"
            f"{p_lcl.magnitude:.0f} hPa"
        ),
        xy=(
            t_lcl.to("degC").magnitude,
            p_lcl.magnitude
        ),
        xytext=(
            t_lcl.to("degC").magnitude - 18,
            p_lcl.magnitude + 55
        ),
        arrowprops=dict(
            arrowstyle="->",
            color="green"
        ),
        fontsize=9,
        bbox=dict(
            boxstyle="round",
            facecolor="white",
            edgecolor="green",
            alpha=0.85
        )
    )


    # ========================================================
    # 500 hPa 実気温
    # ========================================================

    skew.ax.plot(
        T500.magnitude,
        500,
        "ro",
        markersize=7,
        zorder=10
    )

    skew.ax.annotate(
        (
            "500 hPa 実気温\n"
            f"{T500.magnitude:.1f} ℃"
        ),
        xy=(
            T500.magnitude,
            500
        ),
        xytext=(
            T500.magnitude + 8,
            450
        ),
        fontsize=9,
        color="red",
        arrowprops=dict(
            arrowstyle="->",
            color="red"
        ),
        bbox=dict(
            boxstyle="round",
            facecolor="white",
            alpha=0.85
        )
    )


    # ========================================================
    # 500 hPa Parcel温度
    # ========================================================

    skew.ax.plot(
        Tparcel500.magnitude,
        500,
        "ko",
        markersize=7,
        zorder=10
    )

    skew.ax.annotate(
        (
            "500 hPa 空気塊\n"
            f"{Tparcel500.magnitude:.1f} ℃"
        ),
        xy=(
            Tparcel500.magnitude,
            500
        ),
        xytext=(
            Tparcel500.magnitude - 25,
            570
        ),
        fontsize=9,
        color="black",
        arrowprops=dict(
            arrowstyle="->",
            color="black"
        ),
        bbox=dict(
            boxstyle="round",
            facecolor="white",
            alpha=0.85
        )
    )


    # ========================================================
    # SSIを図示
    # ========================================================

    skew.ax.plot(
        [
            Tparcel500.magnitude,
            T500.magnitude
        ],
        [
            500,
            500
        ],
        color="black",
        linestyle="--",
        linewidth=1.4
    )

    ssi_x = (
        Tparcel500.magnitude
        + T500.magnitude
    ) / 2

    skew.ax.annotate(
        f"SSI = {ssi.magnitude:.2f} ℃",
        xy=(
            ssi_x,
            500
        ),
        xytext=(
            ssi_x,
            565
        ),
        ha="center",
        fontsize=10,
        bbox=dict(
            boxstyle="round",
            facecolor="white",
            edgecolor="black",
            alpha=0.9
        ),
        arrowprops=dict(
            arrowstyle="-",
            color="black"
        )
    )


    # ========================================================
    # 凡例
    # ========================================================

    skew.ax.legend(
        loc="lower left"
    )


    # ========================================================
    # Web側へ返す
    # ========================================================

    results = {
        "SSI": ssi.magnitude,
        "T850": T850.magnitude,
        "Td850": Td850.magnitude,
        "LCL": p_lcl.magnitude,
        "T500": T500.magnitude,
        "Parcel500": Tparcel500.magnitude,
    }

    return fig, results