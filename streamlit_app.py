import streamlit as st
import pandas as pd
import pydeck as pdk
from pyproj import Transformer
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# -----------------
# 1. Sample Data Setup
# -----------------

# Simulate LOCA (location) table
loca_data = [
    {'LOCA_ID': 'BH01', 'LOCA_GL': 50.0, 'EASTING': 551000, 'NORTHING': 180000},
    {'LOCA_ID': 'BH02', 'LOCA_GL': 48.5, 'EASTING': 552000, 'NORTHING': 180500},
    {'LOCA_ID': 'BH03', 'LOCA_GL': 46.0, 'EASTING': 551500, 'NORTHING': 181000},
]
loca_df = pd.DataFrame(loca_data)

# Simulate Lithology log
litho_data = [
    # BH01
    {'LOCA_ID': 'BH01', 'TOP_BG': 0, 'BASE_BG': 1, 'GEOL_CODE': 'HWH_CLAY', 'GEOL_DESC': 'Harwich Formation silty clay'},
    {'LOCA_ID': 'BH01', 'TOP_BG': 1, 'BASE_BG': 3, 'GEOL_CODE': 'HWH_SILTSTONE', 'GEOL_DESC': 'Harwich siltstone'},
    {'LOCA_ID': 'BH01', 'TOP_BG': 3, 'BASE_BG': 5, 'GEOL_CODE': 'LONDON_CLAY', 'GEOL_DESC': 'London Clay very stiff'},
    # BH02
    {'LOCA_ID': 'BH02', 'TOP_BG': 0, 'BASE_BG': 2, 'GEOL_CODE': 'HWH_CLAY', 'GEOL_DESC': 'Harwich Formation silty clay'},
    {'LOCA_ID': 'BH02', 'TOP_BG': 2, 'BASE_BG': 3.5, 'GEOL_CODE': 'LONDON_CLAY', 'GEOL_DESC': 'London Clay sandy'},
    # BH03
    {'LOCA_ID': 'BH03', 'TOP_BG': 0, 'BASE_BG': 1.2, 'GEOL_CODE': 'HWH_CLAY', 'GEOL_DESC': 'Harwich Formation silty clay'},
    {'LOCA_ID': 'BH03', 'TOP_BG': 1.2, 'BASE_BG': 4.0, 'GEOL_CODE': 'LONDON_CLAY', 'GEOL_DESC': 'London Clay laminated'},
]
litho_df = pd.DataFrame(litho_data)

# -----------------
# 2. Color Mapping for Formations
# -----------------
formation_colors = {
    'HWH_CLAY': '#e377c2',         # pink/magenta
    'HWH_SILTSTONE': '#17becf',    # teal
    'LONDON_CLAY': '#bcbd22',      # olive
}
default_color = '#cccccc'

# -----------------
# 3. Coordinate Transformation (OSGB36 to WGS84)
# -----------------
transformer = Transformer.from_crs("epsg:27700", "epsg:4326", always_xy=True)
def grid_to_latlon(easting, northing):
    lon, lat = transformer.transform(easting, northing)
    return lat, lon

loca_df[['LAT', 'LON']] = loca_df.apply(lambda row: pd.Series(grid_to_latlon(row['EASTING'], row['NORTHING'])), axis=1)

# -----------------
# 4. Streamlit Layout
# -----------------
st.set_page_config(layout="wide")
st.title('Harwich Formation Lithological Analysis')

left, right = st.columns([1, 2])

with right:
    st.subheader("Borehole Locations (click to select)")
    # Prepare pydeck data
    view_state = pdk.ViewState(
        longitude=loca_df['LON'].mean(),
        latitude=loca_df['LAT'].mean(),
        zoom=13,
        pitch=0,
    )
    # Scatterplot layer for boreholes
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=loca_df,
        pickable=True,
        get_position='[LON, LAT]',
        get_radius=25,
        get_fill_color='[200, 30, 0, 180]',
        get_line_color='[0, 0, 0]',
        line_width_min_pixels=2,
    )
    # Add tooltips to display LOCA_ID
    tooltip={"text": "LOCA_ID: {LOCA_ID}"}

    # Render
    r = pdk.Deck(map_style="mapbox://styles/mapbox/satellite-v9",
                 initial_view_state=view_state,
                 layers=[layer],
                 tooltip=tooltip)
    selected_point = st.pydeck_chart(r)
    st.markdown("*Map auto-zooms to all available boreholes.*")

    # Streamlit/pydeck can't directly capture point click, so workaround below.

# --------------
# 5. Selection workaround: dropdown selection
# (Pydeck click selection not supported natively in streamlit yet, so we provide a dropdown next to the map)
# --------------

with left:
    st.subheader("Borehole Lithology")
    selected_id = st.selectbox(
        "Select a borehole for lithology detail (or click marker label on map):",
        [''] + loca_df['LOCA_ID'].tolist(),
        index=0
    )
    if selected_id:
        borehole = loca_df[loca_df['LOCA_ID'] == selected_id].iloc[0]
        intervals = litho_df[litho_df['LOCA_ID'] == selected_id].sort_values(by='TOP_BG')
        if not intervals.empty:
            ground_level = borehole['LOCA_GL']
            fig, ax = plt.subplots(figsize=(2, 6))
            for _, row in intervals.iterrows():
                top_m_od = ground_level - row['TOP_BG']
                base_m_od = ground_level - row['BASE_BG']
                color = formation_colors.get(row['GEOL_CODE'], default_color)
                ax.add_patch(
                    patches.Rectangle(
                        (0.05, base_m_od),   # x, y
                        0.9,                 # width
                        top_m_od - base_m_od, # height
                        facecolor=color,
                        edgecolor='black'
                    )
                )
                # Text label
                ax.text(0.5, (top_m_od+base_m_od)/2, row['GEOL_CODE'],
                        ha='center', va='center', fontsize=8, color='black', rotation=90)
            ax.set_ylim(
                intervals.apply(lambda r: ground_level - r['BASE_BG'], axis=1).min() - 0.5,
                ground_level + 0.5
            )
            ax.set_xlim(0, 1)
            ax.invert_yaxis()
            ax.set_xticks([])
            ax.set_ylabel('Elevation (m OD)')
            st.pyplot(fig)
            st.markdown("**Interval Table:**")
            # Elevation columns based on OD
            intervals = intervals.copy()
            intervals['Top_elev_OD'] = ground_level - intervals['TOP_BG']
            intervals['Base_elev_OD'] = ground_level - intervals['BASE_BG']
            st.dataframe(
                intervals[['Top_elev_OD', 'Base_elev_OD', 'GEOL_CODE', 'GEOL_DESC']],
                hide_index=True
            )
        else:
            st.info("No lithology data available for this location.")
    else:
        st.markdown("_Select a point on the map or choose from the dropdown to see lithology details._")

# -----
# Notes:
# - Replace simulated DataFrames with your real AGS data for production use.
# - If you implement in a pure Streamlit Cloud environment, `pydeck` and map style keys may require setup.
# -----