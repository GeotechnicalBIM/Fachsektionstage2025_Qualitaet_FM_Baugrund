import numpy as np
from scipy.interpolate import RBFInterpolator, griddata

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