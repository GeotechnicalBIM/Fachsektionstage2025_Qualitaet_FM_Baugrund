import numpy as np
from shapely.geometry import Polygon, Point
import matplotlib.pyplot as plt
from shapely.geometry import LineString
import timeit
import time
import multiprocessing

    


def test_function():
    # Function to generate a simple polygon with no self-intersections
    def generate_non_intersecting_polygon(num_points=100, radius=10):
        # Generate random angles and sort them to ensure a non-intersecting shape
        angles = np.sort(np.random.uniform(0, 2 * np.pi, num_points))
        
        # Generate points on a circle using the sorted angles
        points = [(radius * np.cos(angle), radius * np.sin(angle)) for angle in angles]
        
        # Create a shapely Polygon
        polygon = Polygon(points)
        return polygon




    # Function to generate a random line that intersects the polygon

    def generate_intersecting_line(polygon, length=20):

        # Get the bounding box of the polygon to define line start and end points

        minx, miny, maxx, maxy = polygon.bounds
        # Generate a line that is likely to intersect the polygon by choosing points across the bounding box
        start_point = (minx - 5, np.random.uniform(miny, maxy))
        end_point = (maxx + 5, np.random.uniform(miny, maxy))
        # Create the line
        line = LineString([start_point, end_point])
        return line


    # Generate a polygon with 100 points
    print(f"Running in process {multiprocessing.current_process().name}")
    polygon = generate_non_intersecting_polygon(num_points=100)
    intersecting_line = generate_intersecting_line(polygon)
    intersection = polygon.intersection(intersecting_line)
    time.sleep(1)
    print("Done")


# Multiprocessing 
# Main block to run the function in parallel

# Number of parallel runs
num_runs = 10


# Create a pool of worker processes
with multiprocessing.Pool(processes=num_runs) as pool:
    # Run the function 10 times in parallel

    results = pool.map(test_function, range(num_runs))