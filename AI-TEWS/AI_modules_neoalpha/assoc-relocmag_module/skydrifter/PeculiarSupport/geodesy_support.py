from itertools import combinations
from shapely.geometry import LineString, Point, MultiPoint
from shapely.ops import unary_union
from math import radians, cos, sin, sqrt, atan2, degrees, asin

def calculate_distance(lat1, lat2, lon1, lon2):
    lon1 = radians(lon1)
    lon2 = radians(lon2)
    lat1 = radians(lat1)
    lat2 = radians(lat2)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * asin(sqrt(a))
    return(c * 6371)
    
def calculate_coordinate(lat1, lon1, distance_km, azimuth_deg):
    lat1 = radians(lat1)
    lon1 = radians(lon1)
    azimuth_rad = radians(azimuth_deg)
    R = 6371.0
    angular_distance = distance_km / R
    lat2 = atan2(sin(lat1) * cos(angular_distance) + cos(lat1) * sin(angular_distance) * cos(azimuth_rad),
                 sqrt(sin(azimuth_rad) ** 2 + (sin(lat1) * sin(angular_distance) - cos(lat1) * cos(angular_distance) * cos(azimuth_rad)) ** 2))
    lon2 = lon1 + atan2(sin(azimuth_rad) * sin(angular_distance) * cos(lat1),
                        cos(angular_distance) - sin(lat1) * sin(lat2))
    lat2 = degrees(lat2)
    lon2 = degrees(lon2)
    return lon2, lat2

def intersection(line1_coords,line2_coords):
    line1 = LineString(line1_coords)
    line2 = LineString(line2_coords)
    if line1.intersects(line2):
        intersection_point = line1.intersection(line2)
        try:
            if isinstance(intersection_point, MultiPoint):
                output_list = [(point.x,point.y) for point in intersection_point.geoms]
            elif isinstance(intersection_point, Point):
                output_list = [(intersection_point.x,intersection_point.y)]
            return output_list
        except:
            return []
    else:
        return []