import httpx

async def geocode(place_name: str) -> dict:
    """
    Converts a place name to lat/lon using Nominatim (OpenStreetMap).
    Completely free, no API key needed.
    Example: "Saket Delhi" → { lat: 28.52, lon: 77.21 }
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q":              place_name,
        "format":         "json",
        "limit":          1,
        "addressdetails": 1,
        "countrycodes":   "in"   # restrict to India for better accuracy
    }
    # Nominatim requires a User-Agent header — use your app name
    headers = {"User-Agent": "your-app-name/1.0"}

    async with httpx.AsyncClient() as client:
        res  = await client.get(url, params=params, headers=headers)
        data = res.json()

    if not data:
        raise ValueError(f"Location not found: {place_name}")

    result = data[0]
    return {
        "lat":        float(result["lat"]),
        "lon":        float(result["lon"]),
        "place_name": result["display_name"]
    }




# # Python library for making HTTP requests with API or Website 
# import httpx
# import os
# from dotenv import load_dotenv

# load_dotenv()

# async def geocode(place_name: str) -> dict:
#     """
#     Converts a place name to lat/lon using MapTiler.
#     Example: "Saket Delhi" → { lat: 28.52, lon: 77.21 }
#     """
#     url    = f"https://api.maptiler.com/geocoding/{place_name}.json"
#     params = {"key": os.getenv("MAPTILER_API_KEY"), "limit": 1}
    
#     #  opens an HTTP connection
#     async with httpx.AsyncClient() as client:
#         res  = await client.get(url, params=params)
#         data = res.json()
        
# #it will return the data in this format {
# #  "features":[
# #    {
# #      "place_name":"Saket, Delhi, India",
# #      "geometry":{
# #         "coordinates":[77.215,28.524]
# #      }
# #    }
# #  ]
# # }

#     if not data.get("features"):
#         raise ValueError(f"Location not found: {place_name}")

#     feature = data["features"][0]
#     lon, lat = feature["geometry"]["coordinates"]

#     return {
#         "lat":        lat,
#         "lon":        lon,
#         "place_name": feature["place_name"]
#     }



