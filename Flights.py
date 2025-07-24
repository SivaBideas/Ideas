# flights.py
import requests
from geopy.distance import geodesic
from datetime import datetime

# Credentials for OpenSky
USERNAME = "Your username"
PASSWORD = "Your password"

# Your location
MY_LAT = 3.1063
MY_LON = 101.6070
RADIUS_KM = 100

model_cache = {}
route_cache = {}

# Airline fallback icons and model guess
model_fallbacks = {
    "AXM": "Airbus A320",
    "MAS": "Boeing 737-800",
    "MXD": "ATR 72",
    "SIA": "Airbus A350",
    "UAE": "Boeing 777-300ER",
    "QTR": "Airbus A350",
    "BAW": "Boeing 787",
    "THA": "Airbus A330",
    "JAL": "Boeing 787",
    "TGW": "Airbus A320",
    "CPA": "Airbus A330",
    "AIC": "Boeing 787"
}

route_fallbacks = {
    "MAS319": ("KUL", "BKI"),
    "SIA318": ("SIN", "LHR"),
    "AXM883": ("KUL", "LGK"),
    "UAE342": ("DXB", "SYD"),
    "QTR846": ("DOH", "MEL"),
    "BAW34": ("LHR", "SIN")
}

def get_radius():
    return RADIUS_KM

def fetch_opensky_flights():
    try:
        r = requests.get("https://opensky-network.org/api/states/all", auth=(USERNAME, PASSWORD), timeout=10)
        if "Too many requests" in r.text or r.status_code != 200:
            return []
        return r.json().get("states", [])
    except:
        return []

def fetch_adsb_lol_flights():
    try:
        nm = int(RADIUS_KM * 0.539957)
        url = f"https://api.adsb.lol/v2/lat/{MY_LAT}/lon/{MY_LON}/dist/{nm}"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return []
        return r.json().get("ac", [])
    except:
        return []

def get_aircraft_model(icao24, callsign):
    if icao24 in model_cache:
        return model_cache[icao24]

    try:
        r = requests.get(f"https://opensky-network.org/api/metadata/aircraft/icao24/{icao24}", auth=(USERNAME, PASSWORD), timeout=5)
        if r.status_code == 200:
            model = r.json().get("model", "").strip()
            if model:
                model_cache[icao24] = model
                return model
    except:
        pass

    if callsign:
        prefix = callsign[:3].upper()
        if prefix in model_fallbacks:
            model_cache[icao24] = model_fallbacks[prefix]
            return model_fallbacks[prefix]

    model_cache[icao24] = "Unavailable"
    return "Unavailable"

def get_flight_route(callsign):
    callsign = callsign.strip().upper()
    if not callsign:
        return ("Unavailable", "Unavailable")
    if callsign in route_cache:
        return route_cache[callsign]
    if callsign in route_fallbacks:
        return route_fallbacks[callsign]
    route_cache[callsign] = ("Unavailable", "Unavailable")
    return ("Unavailable", "Unavailable")

def get_nearby_flights():
    states = fetch_opensky_flights()
    use_adsb = False
    if not states:
        use_adsb = True

    flights = []

    if not use_adsb:
        for state in states:
            icao24 = state[0]
            callsign = state[1] or "Unknown"
            origin_country = state[2]
            lon = state[5]
            lat = state[6]
            alt = state[7]
            if lat is None or lon is None:
                continue
            distance_km = geodesic((MY_LAT, MY_LON), (lat, lon)).km
            if distance_km > RADIUS_KM:
                continue
            cs = callsign.strip()
            model = get_aircraft_model(icao24, cs)
            origin, destination = get_flight_route(cs)
            flights.append({
                "callsign": cs,
                "country": origin_country,
                "distance_km": round(distance_km, 1),
                "altitude_m": int(alt) if alt else 0,
                "model": model,
                "origin": origin,
                "destination": destination
            })
    else:
        adsb = fetch_adsb_lol_flights()
        for ac in adsb:
            lat = ac.get("lat")
            lon = ac.get("lon")
            if lat is None or lon is None:
                continue
            cs = ac.get("flight", "Unknown").strip()
            alt = ac.get("alt_baro", 0)
            icao24 = ac.get("hex", "Unknown")
            distance_km = geodesic((MY_LAT, MY_LON), (lat, lon)).km
            model = get_aircraft_model(icao24, cs)
            origin, destination = get_flight_route(cs)
            flights.append({
                "callsign": cs,
                "country": ac.get("r", "Unknown"),
                "distance_km": round(distance_km, 1),
                "altitude_m": int(alt),
                "model": model,
                "origin": origin,
                "destination": destination
            })

    flights.sort(key=lambda x: x["distance_km"])
    return flights, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), use_adsb
