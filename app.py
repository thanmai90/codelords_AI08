import json
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from shapely.geometry import shape, Point
from apscheduler.schedulers.background import BackgroundScheduler
from geopy.distance import geodesic

app = Flask(__name__)
CORS(app)

# Predefined evacuation zones (for demonstration purposes)
evacuation_zones = [
    {"name": "Zone A", "lat": 19.0760, "lon": 72.8777, "services": "Food, Shelter, Aid"},
    {"name": "Zone B", "lat": 28.7041, "lon": 77.1025, "services": "Shelter, Aid"},
    {"name": "Zone C", "lat": 13.0827, "lon": 80.2707, "services": "Food, Shelter"}
]

# URL for GeoJSON evacuation zones (replace with actual URL)
EVACUATION_ZONES_URL = "https://example.com/evacuation-zones.geojson"  # Replace with actual GeoJSON URL

# Global variable to store evacuation zones
geojson_evacuations_zones = []

# Fetch GeoJSON evacuation zones with error handling and logging
def fetch_evacuations_zones():
    global geojson_evacuations_zones
    try:
        response = requests.get(EVACUATION_ZONES_URL)
        response.raise_for_status()  # Check if the request was successful (status code 200)
        
        # Parse the JSON response
        data = response.json()
        
        # Check if GeoJSON has the correct structure
        if 'features' in data:
            geojson_evacuations_zones = data['features']
            print("Evacuation zones updated.")
        else:
            print("Error: GeoJSON structure is missing 'features'")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching evacuation zones: {e}")
    except ValueError as e:
        print(f"Error parsing GeoJSON: {e}")

# Check if a given point (latitude, longitude) is inside an evacuation zone
def check_if_in_zone(lat, lon):
    point = Point(lon, lat)  # Create a Point object using the user's coordinates
    
    for zone in geojson_evacuations_zones:
        try:
            zone_polygon = shape(zone['geometry'])  # Convert GeoJSON polygon to shapely object
            if zone_polygon.contains(point):
                return zone['properties']
        except Exception as e:
            print(f"Error processing zone: {e}")
    
    return None  # Return None if the point is not in any zone

# Calculate the distance between two points in kilometers using geopy
def calculate_distance(lat1, lon1, lat2, lon2):
    return geodesic((lat1, lon1), (lat2, lon2)).km

# Find nearby safe zones (zones with low alert level) given a high alert zone
def find_nearby_safe_zones(lat, lon, high_alert_zone):
    safe_zones = []
    for zone in geojson_evacuations_zones:
        zone_properties = zone['properties']
        
        # Check if the zone is safe and if it's not the high alert zone
        if zone_properties.get('alert_level') == 'low' and zone != high_alert_zone:
            zone_polygon = shape(zone['geometry'])
            zone_center = zone_polygon.centroid  # Get the center of the zone for simplicity
            
            # Calculate distance to the high alert zone's centroid (or to the user's location)
            distance = calculate_distance(lat, lon, zone_center.y, zone_center.x)
            safe_zones.append({
                'name': zone_properties['name'],
                'distance_km': distance,
                'center': {'lat': zone_center.y, 'lon': zone_center.x},
                'properties': zone_properties
            })
    
    # Sort safe zones by distance
    safe_zones.sort(key=lambda x: x['distance_km'])
    return safe_zones

# Route to check if the user's location is inside an evacuation zone and fetch nearby safe zones
@app.route('/check_location', methods=['POST'])
def check_location():
    try:
        data = request.get_json()
        latitude = data.get("latitude")
        longitude = data.get("longitude")

        if latitude is None or longitude is None:
            return jsonify({"error": "Invalid coordinates"}), 400

        # Dummy logic for determining risk (high risk if coordinates are greater than a threshold)
        if latitude > 35 and longitude > 140:
            risk_level = "High Risk"
            evacuation_needed = True
        else:
            risk_level = "Safe Zone"
            evacuation_needed = False

        # Check if the user's location is within a GeoJSON evacuation zone
        zone_properties = check_if_in_zone(latitude, longitude)
        if zone_properties:
            if zone_properties.get('alert_level') == 'high':
                nearby_safe_zones = find_nearby_safe_zones(latitude, longitude, zone_properties)
                return jsonify({
                    "status": "high_alert",
                    "message": "You are in a high alert zone.",
                    "safe_zones": nearby_safe_zones
                })
            else:
                return jsonify({
                    "status": "safe",
                    "message": "You are in a safe zone."
                })

        # Respond with risk level and evacuation zones if high risk
        response = {"riskLevel": risk_level, "evacuationNeeded": evacuation_needed}
        
        if evacuation_needed:
            response["evacuationZones"] = evacuation_zones

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Periodically fetch evacuation zones
def scheduled_fetch_zones():
    fetch_evacuations_zones()  # Regularly fetch evacuation zones (e.g., every hour)

# Initialize and start the scheduler to fetch zones periodically
scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_fetch_zones, 'interval', hours=1)  # Fetch zones every hour
scheduler.start()

# Start the Flask application
if __name__ == '__main__':
    # Fetch zones initially when the server starts
    fetch_evacuations_zones()
    
    # Start the Flask app
    app.run(debug=True, use_reloader=False)  # use_reloader=False to avoid starting scheduler twice
