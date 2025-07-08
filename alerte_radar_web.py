import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
import openrouteservice
from shapely.geometry import LineString, Point
from geopy.distance import geodesic
import folium
import streamlit.components.v1 as components
import numpy as np

def adresse_to_coordonnees(adresse):
    geolocator = Nominatim(user_agent="MonApplicationGeo")
    location = geolocator.geocode(adresse)
    if location:
        return (location.longitude, location.latitude)
    else:
        return None

def obtenir_trajet(depart, arrivee):
    client = openrouteservice.Client(key="5b3ce3597851110001cf624889dedb5eec2c4cbba48f64794bb8d139")
    route = client.directions(
        coordinates=[depart, arrivee],
        profile='driving-car',
        format='geojson'
    )
    coordinates = route['features'][0]['geometry']['coordinates']
    return coordinates

def is_radar_on_the_road(trajet, radar):
    if radar[1] is None or radar[0] is None:
        return False
    if not (42.33 <= radar[1] <= 51.09 and -5.14 <= radar[0] <= 9.56):
        return False
    line = LineString(trajet)
    point = Point(radar[0], radar[1])
    distance_deg = point.distance(line)
    nearest = line.interpolate(line.project(point))
    distance_m = geodesic((point.y, point.x), (nearest.y, nearest.x)).meters
    return distance_m < 10

def create_map(trajet, radars):
    start = trajet[0]
    end = trajet[-1]
    m = folium.Map(location=[start[1], start[0]], zoom_start=14)
    folium.PolyLine(locations=[(lat, lon) for lon, lat in trajet], color='blue').add_to(m)
    folium.Marker([start[1], start[0]], tooltip="Départ").add_to(m)
    folium.Marker([end[1], end[0]], tooltip="Arrivée").add_to(m)
    for radar in radars:
        if np.isnan(radar[2]):
            folium.Marker((radar[0],radar[1]),tooltip=f"Type de radar={radar[3]}").add_to(m)
        else:
            folium.Marker((radar[0],radar[1]),tooltip= f"VMA={int(radar[2])}km/h,Type de radar={radar[3]}").add_to(m)
    return m

st.title("🗺️ Détection de radars sur un trajet")

depart = st.text_input("Adresse de départ", "Toulouse")
arrivee = st.text_input("Adresse d’arrivée", "Montpellier")

if st.button("Calculer le trajet et afficher la carte"):
    coord_depart = adresse_to_coordonnees(depart)
    coord_arrivee = adresse_to_coordonnees(arrivee)

    if not coord_depart or not coord_arrivee:
        st.error("Une des adresses est invalide.")
    else:
        trajet = obtenir_trajet(coord_depart, coord_arrivee)
        url = "https://www.data.gouv.fr/fr/datasets/r/402aa4fe-86a9-4dcd-af88-23753e290a58"
        df = pd.read_csv(url, sep=';', encoding='ISO-8859-1')
        liste_radars = df.to_dict(orient='records')

        radar_on_the_road = [
            (radar["Latitude"], radar["Longitude"], radar["VMA"], radar["Type de radar "])
            for radar in liste_radars
            if is_radar_on_the_road(trajet, (radar["Longitude"], radar["Latitude"]))
        ]

        st.success(f"{len(radar_on_the_road)} radar(s) détecté(s) sur le trajet.")
        map_obj = create_map(trajet, radar_on_the_road)
        map_obj.save("map.html")
        with open("map.html", "r", encoding="utf-8") as f:
            html = f.read()
            components.html(html, height=600)

