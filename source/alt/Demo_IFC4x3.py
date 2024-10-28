#
#
# This file is used to create a simple geotechnical BIM model using ifcopenshell
# It runs in Blender and assumes the add-on bonsai (former blenderbim) is installed.
#
#


import ifcopenshell
from ifcopenshell.api import run
import bpy
import mathutils
import bonsai
import bonsai.tool as tool
import scipy
import numpy as np
from scipy.interpolate import RBFInterpolator, griddata
 

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
            print("Above not Found")
            continue
        ind = len(hgs) - 1 - hgs[::-1].index(above)
        if ind == len(hgs)-1:
            continue
        
        hauptgruppe_below = hgs[ind+1]
        print("\t", hauptgruppe_below)
        if hauptgruppe_below in below:
            x_data.append(bh["x"])
            y_data.append(bh["y"])
            z_data.append(bh["OK"]-bh["Layerdata"]["UKs"][ind])
    
    return x_data, y_data, z_data

def add_testmesh(vertices, faces, name="testmesh"):
    """Quick util function for development. Adds a mesh to the scene"""
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    scene = bpy.context.scene
    scene.collection.objects.link(obj)
    
    return obj, mesh
    
    
def create_cuboid(xmin, ymin, zmin, xmax, ymax, zmax):
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

def split_closed_mesh(closed_mesh_name, surface_mesh_name):
    # Retrieve the closed mesh and the surface mesh by name
    closed_mesh = bpy.data.objects[closed_mesh_name]
    surface_mesh = bpy.data.objects[surface_mesh_name]
    
    if closed_mesh is None or surface_mesh is None:
        print(f"Mesh '{closed_mesh_name}' or surface '{surface_mesh_name}' not found!")
        return
    
    # Step 1: Duplicate the closed mesh for the second part
    bpy.ops.object.select_all(action='DESELECT')  # Deselect everything
    closed_mesh.select_set(True)  # Select the closed mesh
    bpy.context.view_layer.objects.active = closed_mesh  # Set it active
    bpy.ops.object.duplicate(linked=False)  # Duplicate the object
    
    closed_mesh_part2 = bpy.context.active_object  # The duplicate
    closed_mesh_part2.name = f"{closed_mesh_name}_part2"  # Rename the duplicate

    # Step 2: Add a boolean modifier to the original closed mesh for the first part (Difference)
    boolean_diff = closed_mesh.modifiers.new(name="BooleanDifference", type='BOOLEAN')
    boolean_diff.operation = 'DIFFERENCE'  # Keep the part outside the surface mesh
    boolean_diff.object = surface_mesh
    
    # Apply the modifier to the first part
    bpy.context.view_layer.objects.active = closed_mesh  # Make sure it's active
    bpy.ops.object.modifier_apply(modifier=boolean_diff.name)
    
    # Step 3: On the duplicate, apply the reverse boolean operation to get the second part (Intersect)
    boolean_intersect = closed_mesh_part2.modifiers.new(name="BooleanIntersect", type='BOOLEAN')
    boolean_intersect.operation = 'INTERSECT'  # Keep the part intersecting with the surface
    boolean_intersect.object = surface_mesh
    
    # Apply the modifier to the duplicated mesh
    bpy.context.view_layer.objects.active = closed_mesh_part2
    bpy.ops.object.modifier_apply(modifier=boolean_intersect.name)
    
    print(f"Mesh '{closed_mesh_name}' successfully split into two parts using '{surface_mesh_name}'.")



farbcode_DIN4023 = {
    "oliv" : (105, 99, 62),
    "gelb" : (219, 171, 6),
    "gelblichbraun" : (165, 105, 58),
    "rosa" : (195, 114, 128),
    "orange" : (198, 84, 47),
    "dunkelbraun" : (93, 71, 64),
    "rot" : (190, 77, 88),
    "lila" : (135, 70, 128),
    "violett" : (103, 81, 129),
    "violettblau" : (65, 73, 108),
    "dunkelblau" : (42, 76, 103),
    "hellblau" : (47, 125, 183),
    "gelbgrün" : (97, 154, 70),
    "türkis" : (98, 213, 196),
    "grün" : (45, 128, 74),
    "grau" : (127, 127, 127),
    "schwarz" : (0, 0, 0)
}  


mapping_DIN4023 = {
    "Kies" : "gelb",
    "Sand" : "orange",
    "Auffuellung" : "grau",
}  

    
bh_data = [
    {
        "Name" : "bh01",
        "x" : 0,
        "y" : 0,
        "OK" : 5,
        "Layerdata" : {
            "UKs" : [1, 2 ,7],
            "Hauptgruppen" : ["A", "G", "S"]        
        }
    },
    {
        "Name" : "bh02",
        "x" : 10,
        "y" : 0,
        "OK" : 3,
        "Layerdata" : {
            "UKs" : [1, 3 ,7],
            "Hauptgruppen" : ["A", "G", "S"]        
        }
    },
    {
        "Name" : "bh03",
        "x" : 5,
        "y" : 10,
        "OK" : 6,
        "Layerdata" : {
            "UKs" : [1, 3 ,7],
            "Hauptgruppen" : ["A", "G", "S"]        
        }
    },
    {
        "Name" : "bh04",
        "x" : 15,
        "y" : 20,
        "OK" : 6,
        "Layerdata" : {
            "UKs" : [1, 7],
            "Hauptgruppen" : ["A", "S"]        
        }
    },
    {
        "Name" : "bh05",
        "x" : 1,
        "y" : 20,
        "OK" : 6,
        "Layerdata" : {
            "UKs" : [1, 4],
            "Hauptgruppen" : ["A", "S"]        
        }
    },
]

# Get the currently opened ifc-file
#model = tool.Ifc.get()

# toggle blender console (for logging etc.)
#bpy.ops.wm.console_toggle()


# Clear blender model from previous runs
for i in bpy.data.objects:
    bpy.data.objects.remove(i, do_unlink=True)
for i in bpy.data.collections:
    bpy.data.collections.remove(i, do_unlink=True)
    
    
# Create a blank model
model = ifcopenshell.file(schema="IFC4x3")


# All projects must have one IFC Project element
project = run("root.create_entity", model, ifc_class="IfcProject", name="Projekt_Fachsektionstage2025")


# Assigning without arguments defaults to metric units
run("unit.assign_unit", model)


# Create the 3D context
context_3D = run("context.add_context", model, context_type="Model")
# Create conext for the body representations
body = run("context.add_context", model, context_type="Model",
    context_identifier="Body", target_view="MODEL_VIEW", parent=context_3D)


# Create a site, building, and storey. 
site = run("root.create_entity", model, ifc_class="IfcSite", name="Baustelle_Fachsektionstage")
building = run("root.create_entity", model, ifc_class="IfcBuilding", name="Bauwerk1")
storey = run("root.create_entity", model, ifc_class="IfcBuildingStorey", name="Ebene0")


# Assign according to IFC structure
run("aggregate.assign_object", file=model, products=[site], relating_object=project)
run("aggregate.assign_object", file=model, products=[building], relating_object=site)
run("aggregate.assign_object", file=model, products = [storey], relating_object=building)


# Create IFCMaterials and add styling
mapping_hg_to_materialname = {"A": "Auffuellung", "G": "Kies", "S": "Sand"}
for i in ["Auffuellung", "Kies", "Sand"]:
    material = ifcopenshell.api.run("material.add_material", model, name=i)
    style = ifcopenshell.api.style.add_style(model)
    ifcopenshell.api.style.add_surface_style(model,
        style=style, ifc_class="IfcSurfaceStyleShading", attributes={
        "SurfaceColour": { 
            "Name": "{}Style".format(i), 
            "Red": farbcode_DIN4023[mapping_DIN4023[i]][0]/255, 
            "Green": farbcode_DIN4023[mapping_DIN4023[i]][1]/255, 
            "Blue": farbcode_DIN4023[mapping_DIN4023[i]][2]/255,
            },
        "Transparency": 0., # 0 is opaque, 1 is transparent
        })
    # Note: Material can be assigned to both object and materials. If directly assigned, it is used to overwrite    
    ifcopenshell.api.run("style.assign_material_style", model, material=material, style=style, context=context_3D)


# Create the profile used to construct boreholes
profile = model.create_entity("IfcCircleProfileDef", ProfileName="300C", ProfileType="AREA",Radius=300)


# Create the boreholes from the dict containing the data
ifc_bhs = []
ifc_subelements = []
for bh_ind, bh_dict in enumerate(bh_data):
    bh = run("root.create_entity", model, ifc_class="IfcBorehole", name=bh_dict["Name"])
    transformation = IfcUtils.transform_mat(bh_dict["x"], bh_dict["y"], bh_dict["OK"])
    #transformation = IfcUtils.transform_mat(0, 0, 0)
    ifcopenshell.api.geometry.edit_object_placement(model, product=bh, matrix=transformation)    
    ifc_bhs.append(bh)
    
    bh_layer_sublist = []
    for layer_ind in range(len(bh_dict["Layerdata"]["UKs"])):
        hg = bh_dict["Layerdata"]["Hauptgruppen"][layer_ind]
        uk = bh_dict["Layerdata"]["UKs"][layer_ind]
        layerelement = run("root.create_entity", model, ifc_class="IfcGeotechnicalStratum", name="{0}_{1}".format(bh_dict["Name"], layer_ind))
        
        if layer_ind == 0:
            layer_thickness = uk
        else:
            layer_thickness = uk - bh_dict["Layerdata"]["UKs"][layer_ind-1]
         
        representation = ifcopenshell.api.geometry.add_profile_representation(model, context=body, profile=profile, depth=layer_thickness, 
        placement_zx_axes = (mathutils.Vector((0.0, 0.0, 1.0)), mathutils.Vector((1.0, 0.0, 0.0))))
        
        if layer_ind == 0:
            transformation = IfcUtils.transform_mat(bh_dict["x"], bh_dict["y"], bh_dict["OK"] - layer_thickness)
        else:
            transformation = IfcUtils.transform_mat(bh_dict["x"], bh_dict["y"], bh_dict["OK"] - bh_dict["Layerdata"]["UKs"][layer_ind-1] -layer_thickness)
        ifcopenshell.api.geometry.edit_object_placement(model, product=layerelement, matrix=transformation)  
        ifcopenshell.api.geometry.assign_representation(model, product=layerelement, representation=representation)

        bh_layer_sublist.append(layerelement)  
    run("aggregate.assign_object", model, products=bh_layer_sublist, relating_object=bh)
    ifc_subelements.append(bh_layer_sublist)        
#run("aggregate.assign_object", file=model, products = ifc_bhs, relating_object=storey)
run("spatial.assign_container", file=model, products = ifc_bhs, relating_structure=storey)


# Assign materials by Hauptgruppe. Note: Hauptgruppen have been mapped to material names prior      
layer_elems = [i for j in ifc_subelements for i in j]
hgs = []
for i in bh_data:
    hgs.extend(i["Layerdata"]["Hauptgruppen"]) 
for k, v in mapping_hg_to_materialname.items():
    element_collector = []
    for object_ind, hg in enumerate(hgs):
        if hg == k:
            element_collector.append(layer_elems[object_ind])
    material = [i for i in model.by_type('IfcMaterial') if i.Name == v][0]   
    ifcopenshell.api.material.assign_material(model, products=element_collector, material=material)    
        





# Create the meshes for soil volumes
# Set model extents.
x_min, x_max = min([i["x"] for i in bh_data])-2, max([i["x"] for i in bh_data])+3
y_min, y_max = min([i["y"] for i in bh_data])-2, max([i["y"] for i in bh_data])+3
z_min, z_max = min([i["OK"] - i["Layerdata"]["UKs"][-1] for i in bh_data]) - 1,  max([i["OK"] for i in bh_data])+1

# create base model
base_v, base_f = create_cuboid(x_min+1, y_min+1, z_min-1, x_max-2, y_max-2, z_max+2) # reduce size so intersection is granted
_, cuboid_mesh = add_testmesh(base_v, base_f, name="Main")

# Using the stacked surface apporach.

x_data = [i["x"] for i in bh_data]
y_data = [i["y"] for i in bh_data]
z_data = [i["OK"] for i in bh_data]
# Topography
xyz_data = list(zip(x_data, y_data, z_data))
x_rbf, y_rbf, z_rbf = interpolate_rbf(xyz_data, xmin = x_min, ymin = y_min, xmax = x_max, ymax = y_max)
vertices, faces = prepare_grid_to_mesh(x_rbf, y_rbf, z_rbf)             
_, topo_mesh = add_testmesh(vertices, faces, name="Topo")

#split_closed_mesh("Main", "Topo")

# Contact points from Fill to all other points.
x_data, y_data, z_data = prepare_points_from_connections(bh_data, "A", ["S", "G"])    
xyz_data = list(zip(x_data, y_data, z_data))
x_rbf, y_rbf, z_rbf = interpolate_rbf(xyz_data, xmin = x_min, ymin = y_min, xmax = x_max, ymax = y_max)
vertices, faces = prepare_grid_to_mesh(x_rbf, y_rbf, z_rbf)             
add_testmesh(vertices, faces)

# Contact points from S to G.
x_data, y_data, z_data = prepare_points_from_connections(bh_data, "G", ["S"])    
xyz_data = list(zip(x_data, y_data, z_data))
x_rbf, y_rbf, z_rbf = interpolate_rbf(xyz_data, xmin = x_min, ymin = y_min, xmax = x_max, ymax = y_max)
vertices, faces = prepare_grid_to_mesh(x_rbf, y_rbf, z_rbf)             
add_testmesh(vertices, faces)
    

# Save file and load the project
fp = "Y:/institut/Publikationen/01_Eigene Publikationen/2025/unveröffentlicht/2025_jb_sh_Fachsektionstage/code/ifc_test_export_4x3.ifc"
model.write(fp)

proj = bpy.ops.bim.load_project(filepath=fp, use_relative_path=False, should_start_fresh_session=False)


print(len(x_data), z_data)