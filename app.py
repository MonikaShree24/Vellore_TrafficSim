import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from modules.traffic_simulation import (
    find_connected_roads,
    find_roads_within_hops
)

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Vellore TrafficSim",
    page_icon="🚦",
    layout="wide"
)

# --------------------------------------------------
# TITLE
# --------------------------------------------------

st.title("🚦 Vellore TrafficSim")
st.subheader("Traffic Congestion Visualization System")

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

traffic = pd.read_csv("data/traffic.csv")
roads = pd.read_csv("data/roads.csv")
nodes = pd.read_csv("data/nodes.csv")

# --------------------------------------------------
# COMBINE TRAFFIC AND ROAD DATA
# --------------------------------------------------

data = traffic.merge(
    roads[
        [
            "road_id",
            "road_name",
            "capacity",
            "speed_limit",
            "start_node",
            "end_node"
        ]
    ],
    on="road_id"
)

# --------------------------------------------------
# ORIGINAL CONGESTION
# --------------------------------------------------

data["congestion"] = (
    data["vehicle_count"] / data["capacity"]
)

# --------------------------------------------------
# CONGESTION CLASSIFICATION FUNCTION
# --------------------------------------------------

def congestion_level(value):

    if value < 0.40:
        return "Low"

    elif value < 0.70:
        return "Moderate"

    elif value < 0.90:
        return "High"

    else:
        return "Severe"


# Original congestion level

data["congestion_level"] = data[
    "congestion"
].apply(congestion_level)

# --------------------------------------------------
# TIME SELECTOR
# --------------------------------------------------

st.header("⏰ Select Traffic Time")

selected_time = st.selectbox(
    "Choose a time to analyze traffic:",
    sorted(data["time"].unique())
)

# --------------------------------------------------
# WHAT-IF SIMULATION
# --------------------------------------------------

st.header("🔄 What-If Traffic Simulation")

vehicle_multiplier = st.slider(
    "Change Vehicle Volume",
    min_value=50,
    max_value=150,
    value=100,
    step=10,
    help="100% represents the original traffic volume."
)

# --------------------------------------------------
# CREATE SIMULATION DATA
# --------------------------------------------------

simulation_data = data.copy()

simulation_data["simulated_vehicle_count"] = (
    simulation_data["vehicle_count"]
    * vehicle_multiplier
    / 100
)

simulation_data["simulated_congestion"] = (
    simulation_data["simulated_vehicle_count"]
    / simulation_data["capacity"]
)

simulation_data["simulated_level"] = (
    simulation_data["simulated_congestion"]
    .apply(congestion_level)
)

# --------------------------------------------------
# FILTER SELECTED TIME
# --------------------------------------------------

selected_data = simulation_data[
    simulation_data["time"] == selected_time
].copy()

# --------------------------------------------------
# TRAFFIC JAM PROPAGATION
# --------------------------------------------------

# --------------------------------------------------
# TRAFFIC JAM SPREAD STAGE
# --------------------------------------------------

st.subheader("🚧 Traffic Jam Spread Stage")

stage_name = st.radio(
    "Select propagation stage:",
    [
        "Stage 0 - Initial Jam",
        "Stage 1 - Directly Connected Roads",
        "Stage 2 - Extended Propagation"
    ],
    index=1
)

# Convert selected stage to number

if stage_name.startswith("Stage 0"):
    propagation_stage = 0

elif stage_name.startswith("Stage 1"):
    propagation_stage = 1

else:
    propagation_stage = 2


# Display explanation

if propagation_stage == 0:

    st.info(
        "Stage 0: Only the selected road is affected by the traffic jam."
    )

elif propagation_stage == 1:

    st.warning(
        "Stage 1: The traffic jam spreads to directly connected roads."
    )

else:

    st.error(
        "Stage 2: The traffic jam spreads farther through the road network."
    )
selected_road = st.selectbox(
    "Select a road to simulate a traffic jam:",
    selected_data["road_id"],
    format_func=lambda x: selected_data[
        selected_data["road_id"] == x
    ]["road_name"].iloc[0]
)

# Find connected roads

connected_roads = find_connected_roads(
    roads,
    selected_road
)

# Get selected road name

selected_road_name = selected_data[
    selected_data["road_id"] == selected_road
]["road_name"].iloc[0]

st.write(
    f"**🚧 Traffic Jam Source:** {selected_road_name}"
)

# --------------------------------------------------
# CREATE PROPAGATION DATA
# --------------------------------------------------

propagation_data = selected_data.copy()

# Create column to identify propagation

propagation_data["propagation_status"] = "Normal"

# --------------------------------------------------
# INCREASE TRAFFIC ON SELECTED ROAD
# --------------------------------------------------

propagation_data.loc[
    propagation_data["road_id"] == selected_road,
    "simulated_vehicle_count"
] *= 1.30

propagation_data.loc[
    propagation_data["road_id"] == selected_road,
    "propagation_status"
] = "Jam Source"

# --------------------------------------------------
# DETERMINE AFFECTED ROADS BASED ON PROPAGATION STAGE
# --------------------------------------------------

if propagation_stage == 0:

    affected_road_ids = []

elif propagation_stage == 1:

    affected_road_ids = find_roads_within_hops(
        roads,
        selected_road,
        1
    )

else:

    affected_road_ids = find_roads_within_hops(
        roads,
        selected_road,
        2
    )


# --------------------------------------------------
# APPLY PROPAGATION
# --------------------------------------------------

for road_id in affected_road_ids:

    if road_id in propagation_data["road_id"].values:

        # Stage 1 roads receive 15% additional traffic
        # Stage 2 roads receive 10% additional traffic

        if propagation_stage == 1:

            multiplier = 1.15

        else:

            multiplier = 1.10

        propagation_data.loc[
            propagation_data["road_id"] == road_id,
            "simulated_vehicle_count"
        ] *= multiplier

        propagation_data.loc[
            propagation_data["road_id"] == road_id,
            "propagation_status"
        ] = "Affected"
# --------------------------------------------------
# RECALCULATE PROPAGATED CONGESTION
# --------------------------------------------------

propagation_data["propagated_congestion"] = (
    propagation_data["simulated_vehicle_count"]
    / propagation_data["capacity"]
)

# --------------------------------------------------
# RECALCULATE PROPAGATED CONGESTION LEVEL
# --------------------------------------------------

propagation_data["propagated_level"] = (
    propagation_data["propagated_congestion"]
    .apply(congestion_level)
)

# --------------------------------------------------
# PROPAGATION INFORMATION
# --------------------------------------------------

st.info(
    f"🚧 {selected_road_name} receives 30% additional traffic. "
    f"Connected roads receive 15% additional traffic."
)

# --------------------------------------------------
# DISPLAY AFFECTED ROADS
# --------------------------------------------------

if len(connected_roads) > 0:

    st.write("### Roads affected by the traffic jam:")

    affected_count = 0

    for _, road in connected_roads.iterrows():

        road_id = road["road_id"]

        if road_id in propagation_data["road_id"].values:

            st.write(
                f"➡️ {road['road_name']} "
                f"({road['road_id']})"
            )

            affected_count += 1

    if affected_count == 0:

        st.info(
            "No connected roads have traffic data for the selected time."
        )

else:

    st.info(
        "No directly connected roads found."
    )

# --------------------------------------------------
# CONGESTION SUMMARY
# --------------------------------------------------

st.header("🚦 Congestion Summary")

low = (
    propagation_data["propagated_level"] == "Low"
).sum()

moderate = (
    propagation_data["propagated_level"] == "Moderate"
).sum()

high = (
    propagation_data["propagated_level"] == "High"
).sum()

severe = (
    propagation_data["propagated_level"] == "Severe"
).sum()

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "🟢 Low",
    low
)

col2.metric(
    "🟡 Moderate",
    moderate
)

col3.metric(
    "🟠 High",
    high
)

col4.metric(
    "🔴 Severe",
    severe
)

# --------------------------------------------------
# SIMULATION INFORMATION
# --------------------------------------------------

st.info(
    f"Traffic volume is currently set to "
    f"{vehicle_multiplier}% of the original volume."
)

# --------------------------------------------------
# TRAFFIC MAP
# --------------------------------------------------

st.header("🗺️ Vellore Traffic Map")

# Center of map

vellore_center = [
    nodes["latitude"].mean(),
    nodes["longitude"].mean()
]

traffic_map = folium.Map(
    location=vellore_center,
    zoom_start=13
)

# --------------------------------------------------
# DRAW ROAD SEGMENTS
# --------------------------------------------------

for _, road in propagation_data.iterrows():

    start = nodes[
        nodes["node_id"] == road["start_node"]
    ].iloc[0]

    end = nodes[
        nodes["node_id"] == road["end_node"]
    ].iloc[0]

    # Use propagated congestion

    level = road["propagated_level"]

    # --------------------------------------------------
    # ROAD COLOR
    # --------------------------------------------------

    if level == "Low":

        road_color = "green"

    elif level == "Moderate":

        road_color = "orange"

    elif level == "High":

        road_color = "red"

    else:

        road_color = "darkred"

    # --------------------------------------------------
    # SPECIAL STYLING FOR JAM SOURCE
    # --------------------------------------------------

    road_weight = 7

    if road["propagation_status"] == "Jam Source":

        road_weight = 11

    # --------------------------------------------------
    # ROAD TOOLTIP
    # --------------------------------------------------

    tooltip_text = (
        f"Road: {road['road_name']} | "
        f"Vehicles: {road['simulated_vehicle_count']:.0f} | "
        f"Congestion: {road['propagated_congestion']:.2f} | "
        f"Level: {level} | "
        f"Status: {road['propagation_status']}"
    )

    # --------------------------------------------------
    # DRAW ROAD
    # --------------------------------------------------

    folium.PolyLine(
        locations=[
            [
                start["latitude"],
                start["longitude"]
            ],
            [
                end["latitude"],
                end["longitude"]
            ]
        ],
        color=road_color,
        weight=road_weight,
        tooltip=tooltip_text
    ).add_to(traffic_map)

# --------------------------------------------------
# ADD ROAD NODE MARKERS
# --------------------------------------------------

for _, node in nodes.iterrows():

    folium.CircleMarker(
        location=[
            node["latitude"],
            node["longitude"]
        ],
        radius=5,
        popup=f"Node: {node['node_id']}",
        color="blue",
        fill=True
    ).add_to(traffic_map)

# --------------------------------------------------
# MAP LEGEND
# --------------------------------------------------

st.markdown("""
### 🚦 Traffic Map Legend

🟢 **Low** — Congestion below 40%

🟠 **Moderate** — Congestion between 40% and 70%

🔴 **High** — Congestion between 70% and 90%

🔴 **Severe** — Congestion above 90%

**Jam Source** — Selected road where the traffic jam starts

**Affected** — Connected road receiving additional traffic
""")

# --------------------------------------------------
# DISPLAY MAP
# --------------------------------------------------

st_folium(
    traffic_map,
    width=1200,
    height=600
)

# --------------------------------------------------
# TRAFFIC DATA TABLE
# --------------------------------------------------

st.header("📋 Traffic Data")

display_data = propagation_data[
    [
        "road_id",
        "road_name",
        "time",
        "vehicle_count",
        "simulated_vehicle_count",
        "capacity",
        "propagated_congestion",
        "propagated_level",
        "propagation_status",
        "avg_speed"
    ]
].copy()

# Rename columns

display_data.columns = [
    "Road ID",
    "Road Name",
    "Time",
    "Original Vehicles",
    "Simulated Vehicles",
    "Capacity",
    "Congestion",
    "Level",
    "Propagation Status",
    "Average Speed"
]

st.dataframe(
    display_data,
    use_container_width=True
)

# --------------------------------------------------
# CONGESTION BAR CHART
# --------------------------------------------------

st.header("📊 Congestion by Road")

st.bar_chart(
    propagation_data.set_index(
        "road_name"
    )["propagated_congestion"]
)

# --------------------------------------------------
# VEHICLE COUNT CHART
# --------------------------------------------------

st.header("🚗 Vehicle Count by Road")

st.bar_chart(
    propagation_data.set_index(
        "road_name"
    )["simulated_vehicle_count"]
)

# --------------------------------------------------
# AVERAGE SPEED CHART
# --------------------------------------------------

st.header("🏎️ Average Speed by Road")

st.bar_chart(
    propagation_data.set_index(
        "road_name"
    )["avg_speed"]
)

# --------------------------------------------------
# SIMULATION COMPARISON
# --------------------------------------------------

st.header("📈 Original vs Simulated Traffic")

comparison = propagation_data[
    [
        "road_name",
        "vehicle_count",
        "simulated_vehicle_count"
    ]
].copy()

comparison = comparison.set_index(
    "road_name"
)

comparison.columns = [
    "Original Vehicles",
    "Simulated Vehicles"
]

st.bar_chart(comparison)