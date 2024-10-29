import numpy as np
from scipy.interpolate import RBFInterpolator, griddata
import mathutils
import math

def create_fake_topography(xmin, xmax, ymin, ymax, grid_size=1, x_scale=0.1, y_scale=0.1, z_scale = 10):
    # Calculate the number of vertices in the x and y directions
    x_size = xmax - xmin
    y_size = ymax - ymin
    x_verts = int(x_size / grid_size) + 1
    y_verts = int(y_size / grid_size) + 1

    vertices, faces = [], []
    for y in range(y_verts):
        for x in range(x_verts):
            # Calculate the vertex position in 3D space
            x_coord = x * grid_size
            y_coord = y * grid_size
            # Generate height using Perlin noise or fractal noise
            height = mathutils.noise.noise(mathutils.Vector((x_coord * x_scale, y_coord * y_scale, 1))) * z_scale
            # Create the vertex and add it to the row list
            vertices.append([x_coord, y_coord, height])
    
    for y in range(y_verts - 1):
        for x in range(x_verts - 1):
            # Calculate indices of the four vertices that make up each face
            v1 = y * x_verts + x
            v2 = y * x_verts + (x + 1)
            v3 = (y + 1) * x_verts + (x + 1)
            v4 = (y + 1) * x_verts + x
            faces.append([v1, v2, v3, v4])

    return vertices, faces

def create_topography_with_influence(xmin, xmax, ymin, ymax, grid_size, z_base, points, influence_radius = 10, z_scale=1):
    # Calculate the number of vertices in the x and y directions
    x_size = xmax - xmin
    y_size = ymax - ymin
    x_verts = int(x_size / grid_size) + 1
    y_verts = int(y_size / grid_size) + 1

    vertices = []  # List to store 2D vertex positions with heights
    faces = []     # List to store face indices

    # Create a heightmap with Perlin noise
    heightmap = {}
    for y in range(y_verts):
        for x in range(x_verts):
            x_coord = x * grid_size
            y_coord = y * grid_size
            # Generate base height using Perlin noise
            height = mathutils.noise.noise(mathutils.Vector((x_coord * 0.1, y_coord * 0.1, z_base))) * z_scale  # Adjust scaling and amplitude
            heightmap[(x, y)] = height

    # Smoothly interpolate heights to go through control points
    for px, py, p_height in points:
        # Convert world coordinates to grid indices
        gx = int(px / grid_size)
        gy = int(py / grid_size)

        # Apply a radial influence from each control point
         # Radius around the control point to influence, adjust as needed
        for y in range(max(gy - influence_radius, 0), min(gy + influence_radius, y_verts - 1)):
            for x in range(max(gx - influence_radius, 0), min(gx + influence_radius, x_verts - 1)):
                # Distance from the control point
                distance = math.sqrt((gx - x) ** 2 + (gy - y) ** 2)
                if distance < influence_radius:
                    # Smooth interpolation using inverse distance weighting
                    weight = (1 - (distance / influence_radius)) ** 2
                    # Blend noise height and target height smoothly
                    heightmap[(x, y)] = (1 - weight) * heightmap[(x, y)] + weight * p_height

    # Generate vertices with the adjusted heights
    for y in range(y_verts):
        for x in range(x_verts):
            x_coord = x * grid_size
            y_coord = y * grid_size
            height = heightmap[(x, y)]
            vertices.append((x_coord, y_coord, height))

    # Generate faces based on vertex indices
    for y in range(y_verts - 1):
        for x in range(x_verts - 1):
            # Calculate indices of the four vertices that make up each face
            v1 = y * x_verts + x
            v2 = y * x_verts + (x + 1)
            v3 = (y + 1) * x_verts + (x + 1)
            v4 = (y + 1) * x_verts + x
            faces.append([v1, v2, v3, v4])

    return vertices, faces

def create_cuboid(xmin, ymin, zmin, xmax, ymax, zmax):
    """
    Compute vertices and faces for a world alligned cuboid given its min and max points
    """
    # Define the 8 vertices of the cuboid
    vertices = [
        (xmin, ymin, zmin),  # Bottom face (4 vertices)
        (xmax, ymin, zmin),
        (xmax, ymax, zmin),
        (xmin, ymax, zmin),
        (xmin, ymin, zmax),  # Top face (4 vertices)
        (xmax, ymin, zmax),
        (xmax, ymax, zmax),
        (xmin, ymax, zmax)
    ]
    
    # Define the faces of the cuboid, using the vertices
    faces = [
        (0, 1, 2, 3),  # Bottom face
        (4, 5, 6, 7),  # Top face
        (0, 1, 5, 4),  # Side face 1
        (1, 2, 6, 5),  # Side face 2
        (2, 3, 7, 6),  # Side face 3
        (3, 0, 4, 7)   # Side face 4
    ]
    return vertices, faces


def interpolate_rbf(data_xyz, xmin=None, xmax=None, ymin=None, ymax=None, grid_x=1, grid_y=1): 
    """
    data_xyz:list -> [xpos of borehole, ypos of borehole, z-value used for interpolation]
    """
    xmin = xmin if xmin else min([i[0] for i in data_xyz])
    xmax = xmax if xmax else max([i[0] for i in data_xyz])
    ymin = ymin if ymin else min([i[1] for i in data_xyz])
    ymax = ymax if ymax else max([i[1] for i in data_xyz])

    # https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.RBFInterpolator.html#scipy.interpolate.RBFInterpolator
    interpolator = RBFInterpolator(
        y = np.array([
            [i[0] for i in data_xyz],
            [i[1] for i in data_xyz]
            ]).T,
        d = [i[2] for i in data_xyz],
        neighbors = len(data_xyz),
        smoothing = 0.0,
        kernel = "cubic",
        epsilon = None,
        degree = None
    )

    xgrid = np.mgrid[xmin:xmax:grid_x, ymin:ymax:grid_y]
    xflat = xgrid.reshape(2, -1).T
    yflat = interpolator(xflat)
    ygrid = yflat.reshape(xgrid.shape[1], xgrid.shape[2])

    return *xgrid, ygrid


def prepare_points_from_connections(bh_data, above, below):
    """
    Find the contact points of a Hauptgruppe above with all Hauptgruppen specified below.
    
    Similar to defining contact points in leapfrog works.
    above-str
    below-[str]
    """
    x_data, y_data, z_data = [], [], []
    for bh in bh_data:
        hgs = bh["Layerdata"]["Hauptgruppen"]
        if above not in hgs:
            #print("Above not Found")
            continue
        ind = len(hgs) - 1 - hgs[::-1].index(above)
        if ind == len(hgs)-1:
            continue
        
        hauptgruppe_below = hgs[ind+1]
        #print("\t", hauptgruppe_below)
        if hauptgruppe_below in below:
            x_data.append(bh["x"])
            y_data.append(bh["y"])
            z_data.append(bh["OK"]-bh["Layerdata"]["UKs"][ind])
    
    return x_data, y_data, z_data


def prepare_grid_to_mesh(x_arr, y_arr, z_arr, mode="triangle"):
    """
    Given three 2d arrays containing x, y, and z coordinates
    prepare list of vertices and faces
    """
    # Regular grid to triangluar mesh
    vertices = []
    for i in range(x_arr.shape[0]):
        for j in range(x_arr.shape[1]):
            vertices.append((x_arr[i, j], y_arr[i, j], z_arr[i, j]))
    faces = []
    for i in range(x_arr.shape[0] - 1):
        for j in range(x_arr.shape[1] - 1):
            # Define 2 triangles for each quad on the grid
            v1 = i * x_arr.shape[1] + j
            v2 = (i + 1) * x_arr.shape[1] + j
            v3 = (i + 1) * x_arr.shape[1] + (j + 1)
            v4 = i * x_arr.shape[1] + (j + 1)
            if mode=="triangle":
                faces.append((v1, v2, v3))
                faces.append((v1, v3, v4))
            else:
                faces.append((v1,v2,v3,v4))
    return vertices, faces