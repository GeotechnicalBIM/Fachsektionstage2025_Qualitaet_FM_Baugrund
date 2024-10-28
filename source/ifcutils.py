import ifcopenshell
import numpy as np


class IfcUtils:
    @staticmethod
    def transform_mat(x,y,z):
        mat = np.array(
        [
        [1,0,0,x],
        [0,1,0,y],
        [0,0,1,z],
        [0,0,0,1]
        ])
        return mat