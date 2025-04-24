import streamlit as st
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Test Map", layout="wide")
st.title("Test Map with Red Dot")

m = folium.Map(location=(54.5742, -1.2345), zoom_start=17)

folium.Marker(
    location=(54.5742, -1.2345),
    popup="Home",
    icon=folium.Icon(color="green", icon="home")
).add_to(m)

folium.CircleMarker(
    location=(54.5749, -1.2349),
    radius=7,
    color='red',
    fill=True,
    fill_color='red',
    fill_opacity=1.0,
    tooltip="Red Dot"
).add_to(m)

st_folium(m, width=1000, height=450)
