# -*- coding: utf-8 -*-

from datetime import date
from io import BytesIO

import matplotlib.pyplot as plt
import streamlit as st

# 既存ラジオゾンデ版
from emagram_ssi_web import draw_emagram_ssi
from emagram_convective_web import draw_emagram_convective

# ERA5版
from era5_convective_web import (
    STATIONS as ERA5_STATIONS,
    draw_era5_convective,
)


APP_VERSION = "2.0 Beta"


# ============================================================
# ページ設定
# ============================================================

st.set_page_config(
    page_title="エマグラム解析ツール",
    layout="wide",
)

st.title("エマグラム解析ツール")


# ============================================================
# ラジオゾンデ地点
# ============================================================

RADIOSONDE_STATIONS = [
    "稚内",
    "札幌",
    "釧路",
    "秋田",
    "輪島",
    "館野",
    "八丈島",
    "松江",
    "潮岬",
    "福岡",
    "鹿児島",
    "名瀬",
    "石垣島",
    "南大東島",
    "父島",
    "南鳥島",
]


# ============================================================
# サイドバー
# ============================================================

with st.sidebar:

    st.header("解析条件")

    source = st.radio(
        "データソース",
        [
            "ラジオゾンデ",
            "ERA5",
        ],
    )

    st.divider()

    # --------------------------------------------------------
    # ラジオゾンデ
    # --------------------------------------------------------

    if source == "ラジオゾンデ":

        station = st.selectbox(
            "地点",
            RADIOSONDE_STATIONS,
        )

        obs_date = st.date_input(
            "観測日",
        )

        hour = st.radio(
            "観測時刻",
            [9, 21],
            format_func=lambda x: f"{x} JST",
            horizontal=True,
        )

        mode = st.radio(
            "解析モード",
            [
                "SSI解析",
                "対流解析",
            ],
        )

    # --------------------------------------------------------
    # ERA5
    # --------------------------------------------------------

    else:

        location_mode = st.radio(
            "地点指定",
            [
                "登録地点",
                "緯度・経度",
            ],
        )

        if location_mode == "登録地点":

            station = st.selectbox(
                "地点",
                list(ERA5_STATIONS.keys()),
                index=(
                    list(ERA5_STATIONS.keys()).index("館野")
                    if "館野" in ERA5_STATIONS
                    else 0
                ),
            )

            lat, lon = ERA5_STATIONS[station]

            st.caption(
                f"{lat:.4f}°N, {lon:.4f}°E"
            )

        else:

            station = st.text_input(
                "地点名",
                value="湯沢",
            )

            lat = st.number_input(
                "緯度",
                min_value=-90.0,
                max_value=90.0,
                value=36.94,
                step=0.01,
                format="%.4f",
            )

            lon = st.number_input(
                "経度",
                min_value=-180.0,
                max_value=180.0,
                value=138.81,
                step=0.01,
                format="%.4f",
            )

        obs_date = st.date_input(
            "日時",
            value=date(2025, 8, 14),
        )

        hour = st.selectbox(
            "時刻（JST）",
            list(range(24)),
            index=9,
            format_func=lambda x: f"{x:02d}:00",
        )

        # 現在のERA5 Webエンジンは対流解析版。
        # SSIも同時に算出・表示される。
        mode = "対流解析"

        st.caption(
            "ERA5版は現在「対流解析」です。"
            "SSIも同時に計算します。"
        )

    draw_button = st.button(
        "描画",
        type="primary",
        use_container_width=True,
    )

    st.divider()

    st.caption("Emagram Analyzer")
    st.caption(f"Version {APP_VERSION}")
    st.caption("© Takuro Odagawa")


# ============================================================
# 初期表示
# ============================================================

if not draw_button:

    st.info(
        "サイドバーで解析条件を選び、"
        "「描画」を押してください。"
    )


# ============================================================
# 描画
# ============================================================

else:

    try:

        # ----------------------------------------------------
        # ラジオゾンデ
        # ----------------------------------------------------

        if source == "ラジオゾンデ":

            with st.spinner(
                "気象庁の高層観測データを取得しています..."
            ):

                if mode == "SSI解析":

                    fig, results = draw_emagram_ssi(
                        station,
                        obs_date,
                        hour,
                    )

                else:

                    fig, results = draw_emagram_convective(
                        station,
                        obs_date,
                        hour,
                    )

            profile_df = None

        # ----------------------------------------------------
        # ERA5
        # ----------------------------------------------------

        else:

            with st.spinner(
                "ERA5を取得・解析しています。"
                "初回は数十秒かかることがあります..."
            ):

                fig, results, profile_df = draw_era5_convective(
                    place_name=station,
                    lat=lat,
                    lon=lon,
                    date=obs_date.strftime("%Y-%m-%d"),
                    hour_jst=hour,
                )

        # ====================================================
        # エマグラム + 解析結果
        # ====================================================

        graph_col, result_col = st.columns(
            [3, 1],
            gap="large",
        )

        with graph_col:

            st.pyplot(
                fig,
                use_container_width=True,
            )

            image_buffer = BytesIO()

            fig.savefig(
                image_buffer,
                format="png",
                dpi=150,
                bbox_inches="tight",
            )

            image_buffer.seek(0)

            st.download_button(
                "PNGを保存",
                data=image_buffer,
                file_name=(
                    f"emagram_{source}_"
                    f"{obs_date:%Y%m%d}_"
                    f"{hour:02d}JST.png"
                ),
                mime="image/png",
            )

        with result_col:

            st.subheader("解析結果")

            # ------------------------------------------------
            # ラジオゾンデ SSI
            # ------------------------------------------------

            if (
                source == "ラジオゾンデ"
                and mode == "SSI解析"
            ):

                st.metric(
                    "SSI",
                    f"{results['SSI']:.2f}",
                )

                st.metric(
                    "850 hPa 気温",
                    f"{results['T850']:.1f} ℃",
                )

                st.metric(
                    "850 hPa 露点",
                    f"{results['Td850']:.1f} ℃",
                )

                st.metric(
                    "LCL",
                    f"{results['LCL']:.0f} hPa",
                )

                st.metric(
                    "500 hPa 実気温",
                    f"{results['T500']:.1f} ℃",
                )

                st.metric(
                    "500 hPa 空気塊",
                    f"{results['Parcel500']:.1f} ℃",
                )

            # ------------------------------------------------
            # 対流解析（ラジオゾンデ / ERA5）
            # ------------------------------------------------

            else:

                if results.get("SSI") is None:

                    st.metric(
                        "SSI",
                        "計算不可",
                    )

                else:

                    st.metric(
                        "SSI",
                        f"{results['SSI']:.2f}",
                    )

                st.metric(
                    "SBCAPE",
                    f"{results['SBCAPE']:.0f} J/kg",
                )

                st.metric(
                    "SBCIN",
                    f"{results['SBCIN']:.0f} J/kg",
                )

                st.metric(
                    "LCL",
                    f"{results['LCL']:.0f} hPa",
                )

                st.metric(
                    "LFC",
                    (
                        f"{results['LFC']:.0f} hPa"
                        if results["LFC"] is not None
                        else "なし"
                    ),
                )

                st.metric(
                    "EL",
                    (
                        f"{results['EL']:.0f} hPa"
                        if results["EL"] is not None
                        else "なし"
                    ),
                )

                # ERA5固有情報
                if source == "ERA5":

                    st.divider()
                    st.caption("ERA5 地上状態")

                    st.write(
                        f"地上気圧："
                        f"{results['SurfacePressure']:.1f} hPa"
                    )

                    st.write(
                        f"2 m気温："
                        f"{results['SurfaceTemperature']:.1f} ℃"
                    )

                    st.write(
                        f"2 m露点："
                        f"{results['SurfaceDewpoint']:.1f} ℃"
                    )

                    st.divider()
                    st.caption("使用ERA5格子")

                    st.write(
                        f"{results['GridLat']:.2f}°N, "
                        f"{results['GridLon']:.2f}°E"
                    )

                    if (
                        results["ProfileCached"]
                        and results["SurfaceCached"]
                    ):

                        st.success(
                            "保存済みERA5データを使用"
                        )

                    else:

                        st.success(
                            "ERA5データ取得完了"
                        )

        # ====================================================
        # ERA5鉛直プロファイル
        # ====================================================

        if (
            source == "ERA5"
            and profile_df is not None
        ):

            with st.expander(
                "ERA5鉛直プロファイルを見る"
            ):

                st.dataframe(
                    profile_df.style.format({
                        "気圧(hPa)": "{:.0f}",
                        "気温(℃)": "{:.1f}",
                        "露点(℃)": "{:.1f}",
                        "相対湿度(%)": "{:.1f}",
                        "風速(m/s)": "{:.1f}",
                        "風向(°)": "{:.0f}",
                    }),
                    use_container_width=True,
                )

        plt.close(fig)

    except Exception as exc:

        st.error(
            "解析中にエラーが発生しました。"
        )

        st.exception(exc)























st.sidebar.markdown("---")
st.sidebar.caption(
    """
**Data Sources**

• Japan Meteorological Agency (JMA)

• ERA5 Reanalysis (Copernicus Climate Change Service, C3S)

© European Union
"""
)