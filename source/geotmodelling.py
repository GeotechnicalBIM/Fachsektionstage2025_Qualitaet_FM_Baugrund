import numpy as np
from scipy.interpolate import RBFInterpolator, griddata

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