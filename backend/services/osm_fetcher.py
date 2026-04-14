import requests
import time
import random

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://z.overpass-api.de/api/interpreter"
]

HEADERS = {
    "User-Agent": "GIS-Analyzer/1.0 (your_email@example.com)"
}


def safe_overpass_request(query: str, max_retries: int = 4) -> dict:
    for attempt in range(max_retries):
        url = random.choice(OVERPASS_URLS)

        try:
            response = requests.post(
                url,
                data    = {"data": query},
                headers = HEADERS,
                timeout = 180
            )

            if response.status_code == 200:
# JSON (string from API) → Python Dictionary (usable object)
                data = response.json()

                if "error" in data:
                    raise Exception(data["error"])

                return data

            else:
                print(f"🔴 Overpass HTTP {response.status_code} "
                      f"(attempt {attempt+1}/{max_retries})")

        except requests.exceptions.Timeout:
            print(f"⏱ Overpass timeout (attempt {attempt+1}/{max_retries})")

        except requests.exceptions.ConnectionError:
            print(f"🌐 Overpass connection error (attempt {attempt+1}/{max_retries})")

        except Exception as e:
            print(f"🔴 Overpass error: {e}")

        wait_time = 5 * (attempt + 1)
        time.sleep(wait_time)

    raise Exception("❌ Overpass API failed after multiple retries")


def fetch_pois(lat: float, lon: float, radius_km: float) -> dict:
    radius_m = radius_km * 1000
    
# JSON (string from API) → Python Dictionary (usable object)

    query = f"""
    [out:json][timeout:180];
    (
      node["amenity"="hospital"](around:{radius_m},{lat},{lon});
      node["amenity"="clinic"](around:{radius_m},{lat},{lon});
      node["amenity"="veterinary"](around:{radius_m},{lat},{lon});

      node["highway"="bus_stop"](around:{radius_m},{lat},{lon});
      node["amenity"="fuel"](around:{radius_m},{lat},{lon});
      node["amenity"="school"](around:{radius_m},{lat},{lon});
      node["amenity"="restaurant"](around:{radius_m},{lat},{lon});
      node["amenity"="pharmacy"](around:{radius_m},{lat},{lon});

      way["building"](around:{radius_m},{lat},{lon});
    );
    out center;
    """

    data = safe_overpass_request(query)

    human_hospitals, vet_hospitals = [], []
    bus_stops, fuel_stations       = [], []
    schools, restaurants, pharmacies, buildings = [], [], [], []

    for element in data.get("elements", []):
        tags    = element.get("tags", {})
        amenity = tags.get("amenity", "")
        highway = tags.get("highway", "")

        if element["type"] == "node":
            el_lat = element.get("lat")
            el_lon = element.get("lon")
        elif element["type"] == "way":
            center = element.get("center", {})
            el_lat = center.get("lat")
            el_lon = center.get("lon")
        else:
            continue

        if not el_lat or not el_lon:
            continue

        item = {
            "name": tags.get("name", "Unknown"),
            "lat":  el_lat,
            "lon":  el_lon
        }

        if amenity in ["hospital", "clinic"]:
            human_hospitals.append(item)
        elif amenity == "veterinary":
            vet_hospitals.append(item)
        elif highway == "bus_stop":
            bus_stops.append(item)
        elif amenity == "fuel":
            fuel_stations.append(item)
        elif amenity == "school":
            schools.append(item)
        elif amenity == "restaurant":
            restaurants.append(item)
        elif amenity == "pharmacy":
            pharmacies.append(item)
        elif element["type"] == "way" and tags.get("building"):
            buildings.append(item)

    return {
        "human_hospitals": human_hospitals,
        "vet_hospitals":   vet_hospitals,
        "bus_stops":       bus_stops,
        "fuel_stations":   fuel_stations,
        "schools":         schools,
        "restaurants":     restaurants,
        "pharmacies":      pharmacies,
        "buildings":       buildings,
        "summary": {
            "human_hospitals": len(human_hospitals),
            "vet_hospitals":   len(vet_hospitals),
            "bus_stops":       len(bus_stops),
            "fuel_stations":   len(fuel_stations),
            "schools":         len(schools),
            "restaurants":     len(restaurants),
            "pharmacies":      len(pharmacies),
            "buildings":       len(buildings),
        }
    }












# import json

# def convert_to_geojson(poi_data):
#     features = []

#     def add_features(category, items):
#         for item in items:
#             features.append({
#                 "type": "Feature",
#                 "properties": {
#                     "name": item["name"],
#                     "category": category
#                 },
#                 "geometry": {
#                     "type": "Point",
#                     "coordinates": [item["lon"], item["lat"]]
#                 }
#             })

#     # Add all categories
#     add_features("human_hospitals", poi_data["human_hospitals"])
#     add_features("vet_hospitals", poi_data["vet_hospitals"])
#     add_features("bus_stops", poi_data["bus_stops"])
#     add_features("fuel_stations", poi_data["fuel_stations"])
#     add_features("schools", poi_data["schools"])
#     add_features("restaurants", poi_data["restaurants"])
#     add_features("pharmacies", poi_data["pharmacies"])
#     add_features("buildings", poi_data["buildings"])

#     geojson = {
#         "type": "FeatureCollection",
#         "features": features
#     }

#     return geojson


# if __name__ == "__main__":
#     LAT = 23.1828
#     LON = 75.7680
#     RADIUS_KM = 1

#     print("📡 Fetching OSM data for Mahakal (1 km radius)...")

#     poi_data = fetch_pois(LAT, LON, RADIUS_KM)

#     print("✅ Summary:")
#     print(json.dumps(poi_data["summary"], indent=2))

#     geojson_data = convert_to_geojson(poi_data)

#     output_file = "mahakal_pois.geojson"

#     with open(output_file, "w", encoding="utf-8") as f:
#         json.dump(geojson_data, f, indent=2)

#     print(f"📁 GeoJSON saved: {output_file}")