import bpy
import bmesh
import json
import ifcopenshell
from ifcopenshell.api import run
import mathutils
import sys
import os
import numpy as np
import random
import ifcopenshell.api.pset_template

# local imports. looks a bit weird, but as the code is executed in blender we have to add the paths manually

dir_path = os.path.dirname(os.path.realpath(__file__))
parent_path = os.path.dirname(dir_path)
if dir_path not in sys.path:
    sys.path.append(dir_path)

from ifcutils import IfcUtils
from blenderutils import BlenderUtils
from geotmodelling import interpolate_rbf, create_cuboid, prepare_points_from_connections, prepare_grid_to_mesh, create_fake_topography, create_topography_with_influence


# Load project specific data
with open(parent_path+"/project_data/bh_data.json", encoding="Latin1") as f:
    bh_data = json.load(f) 


# Load Data from resources folder
with open(parent_path+"/resources/farbcode_DIN4023.json", "r", encoding="Latin1") as f:
    farbcode_DIN4023 = json.load(f)
with open(parent_path+"/resources/mapping_DIN4023.json", "r", encoding="Latin1") as f:
    mapping_DIN4023 = json.load(f)
with open(parent_path+"/resources/mapping_hg_to_materialname.json", "r", encoding="Latin1") as f:
    mapping_hg_to_materialname = json.load(f)


# Clear blender model from previous runs
for i in bpy.data.objects:
    bpy.data.objects.remove(i, do_unlink=True)
for i in bpy.data.collections:
    bpy.data.collections.remove(i, do_unlink=True)




# Create a blank model
model = ifcopenshell.file(schema="IFC4X3")

# All projects must have one IFC Project element
project = run("root.create_entity", model, ifc_class="IfcProject", name="Projekt_Fachsektionstage2025")
project.Description = "Ein akademisches Projekt, das Teil des Beitrags von Johannes Beck zu den Fachsektionstagen Geotechnik 2025 in Würzburg ist"

# Assigning without arguments defaults to metric units
length_unit = ifcopenshell.api.unit.add_si_unit(model, unit_type="LENGTHUNIT") # Note: Default is mm 
area_unit = ifcopenshell.api.unit.add_si_unit(model, unit_type="AREAUNIT")
money_unit = ifcopenshell.api.unit.add_monetary_unit(model, currency="EUR")
mass_unit =  ifcopenshell.api.unit.add_si_unit(model, unit_type="MASSUNIT")
run("unit.assign_unit", model, units=[length_unit, area_unit, money_unit])

# Create the 3D context - for body representations
context_3D = run("context.add_context", model, context_type="Model")
body = run("context.add_context", model, context_type="Model",
    context_identifier="Body", target_view="MODEL_VIEW", parent=context_3D)

# Create a site, building, and storey. 
site = run("root.create_entity", model, ifc_class="IfcSite", name="Baustelle_Fachsektionstage")
building = run("root.create_entity", model, ifc_class="IfcBuilding", name="Bauwerk1")
#storey = run("root.create_entity", model, ifc_class="IfcBuildingStorey", name="Aufschlussebene")
#storey2 = run("root.create_entity", model, ifc_class="IfcBuildingStorey", name="Schichtenebene")


# Assign according to IFC structure
run("aggregate.assign_object", file=model, products=[site], relating_object=project)
run("aggregate.assign_object", file=model, products=[building], relating_object=site)
#run("aggregate.assign_object", file=model, products = [storey, storey2], relating_object=building)

# Create Geomodel
baugrundschichtenmodell = run("root.create_entity", model, ifc_class="IfcGeomodel", name="Baugrundschichtenmodell")
baugrundaufschlussmodell = run("root.create_entity", model, ifc_class="IfcGeomodel", name="Baugrundaufschlussmodell")

#run("aggregate.assign_object", file=model, products=[baugrundschichtenmodell, baugrundaufschlussmodell], relating_object=site)
run("spatial.assign_container", file=model, products = [baugrundschichtenmodell, baugrundaufschlussmodell], relating_structure=site)



for i in ["Auffuellung", "Kies", "Sand"]:
    material = ifcopenshell.api.run("material.add_material", model, name=i)
    #style = ifcopenshell.api.style.add_style(model)
    style = run("style.add_style", model)
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
profile = model.create_entity("IfcCircleProfileDef", ProfileName="300C", ProfileType="AREA",Radius=0.300) # Note: Watch the choses IFCLENGHTUNIT


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
        # Note: The ifcopenshell.api.root.create entity handles the userdefined predefined type automatically
        layerelement = run("root.create_entity", model, ifc_class="IfcGeotechnicalStratum", name="{0}_{1}".format(bh_dict["Name"], layer_ind), predefined_type="ANSPRACHEBEREICH")
        
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
#run("spatial.assign_container", file=model, products = ifc_bhs, relating_structure=storey)
run("aggregate.assign_object", file=model, products = ifc_bhs, relating_object=baugrundaufschlussmodell)
        
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








# CREATE THE SUBSOIL VOLUMES
# USING THE STACKED SURFACE APPROACH

# Create a collections for structuring the model / surface
main_coll_name = "GeologicalModelling"
srf_coll_name, base_coll_name, topo_coll_name, vol_coll_name = "GeologicalSurfaces", "Base", "Topography", "GeologicalVolumes"

main_coll = bpy.data.collections.new(main_coll_name)
bpy.context.scene.collection.children.link(main_coll)
srf_collection = bpy.data.collections.new(srf_coll_name)
base_collection = bpy.data.collections.new(base_coll_name)
topo_collection = bpy.data.collections.new(topo_coll_name)
vol_collection = bpy.data.collections.new(vol_coll_name)
for i in [srf_coll_name, base_coll_name, topo_coll_name, vol_coll_name]:
    bpy.data.collections[main_coll_name].children.link(bpy.data.collections[i])

# Create the meshes for soil volumes
# Set model extents.
x_min, x_max = min([i["x"] for i in bh_data])-2, max([i["x"] for i in bh_data])+3
y_min, y_max = min([i["y"] for i in bh_data])-2, max([i["y"] for i in bh_data])+3
z_min, z_max = min([i["OK"] - i["Layerdata"]["UKs"][-1] for i in bh_data]) - 1,  max([i["OK"] for i in bh_data])+1

# create base model
base_v, base_f = create_cuboid(x_min+1, y_min+1, z_min-1, x_max-2, y_max-2, z_max+2) # reduce size so intersection is granted
base_obj, cuboid_mesh = BlenderUtils.add_testmesh(base_v, base_f, name="Main")
bpy.data.collections[base_coll_name].objects.link(base_obj)
for collection in base_obj.users_collection:
    if collection.name!=base_coll_name:
        collection.objects.unlink(base_obj)

# Topography
x_data = [i["x"] for i in bh_data]
y_data = [i["y"] for i in bh_data]
z_data = [i["OK"] for i in bh_data]
xyz_data = list(zip(x_data, y_data, z_data))
x_rbf, y_rbf, z_rbf = interpolate_rbf(xyz_data, xmin = x_min, ymin = y_min, xmax = x_max, ymax = y_max)
vertices, faces = prepare_grid_to_mesh(x_rbf, y_rbf, z_rbf)             

for v_ind, v in enumerate(vertices): # this would be much prettier with perlin noise or something like that
    if min(BlenderUtils.compute_xy_distances(v, xyz_data)) < 0.1: # keep the points from the boreholes.
        continue
    elif v[2]<min(z_data):
        vertices[v_ind] = [v[0], v[1], min(z_data) + 0.1* random.random()]
    else:
        vertices[v_ind] = [v[0], v[1], v[2] + 0.1* random.random() - 0.1*random.random()]

topo_obj, topo_mesh = BlenderUtils.add_testmesh(vertices, faces, name="Topo")
bpy.data.collections[topo_coll_name].objects.link(topo_obj)
for collection in topo_obj.users_collection:
    if collection.name!=topo_coll_name:
        collection.objects.unlink(topo_obj)  

# Contact points from Fill to all other points.
x_data, y_data, z_data = prepare_points_from_connections(bh_data, "A", ["S", "G"])    
xyz_data = list(zip(x_data, y_data, z_data))
x_rbf, y_rbf, z_rbf = interpolate_rbf(xyz_data, xmin = x_min, ymin = y_min, xmax = x_max, ymax = y_max)
vertices, faces = prepare_grid_to_mesh(x_rbf, y_rbf, z_rbf)             
srf_a, msh_a = BlenderUtils.add_testmesh(vertices, faces, "A_GS")
bpy.data.collections[srf_coll_name].objects.link(srf_a)
for collection in srf_a.users_collection:
    if collection.name!=srf_coll_name:
        collection.objects.unlink(srf_a)  

# Contact points from S to G.
x_data, y_data, z_data = prepare_points_from_connections(bh_data, "G", ["S"])    
xyz_data = list(zip(x_data, y_data, z_data))

#ADD CUSTOM CONSTRAINTS
xyz_data.append((0,100, 3))


x_rbf, y_rbf, z_rbf = interpolate_rbf(xyz_data, xmin = x_min, ymin = y_min, xmax = x_max, ymax = y_max)
vertices, faces = prepare_grid_to_mesh(x_rbf, y_rbf, z_rbf)             
srf_b, msh_b = BlenderUtils.add_testmesh(vertices, faces, name="G_S")
bpy.data.collections[srf_coll_name].objects.link(srf_b)
for collection in srf_b.users_collection:
    if collection.name!=srf_coll_name:
        collection.objects.unlink(srf_b)  



# PERFORM THE CUTTING. KEEP THE SURFACES IN THEIR COLLECETION

# SORT THE SURFACES. Note: They are passed in an ordered list later on. This is just for visualtization 
# Note: Blender sorts them by alphabetical order by default. Hence, we just add prefixes.
collection = bpy.data.collections.get(srf_coll_name)
srf_b.name = "0_" + srf_b.name
    

# START WITH THE TOPOLOGY. The part above the topology is dropped.
m1, m2, org_mesh, org_surface = BlenderUtils.split_with_surface(mesh_name="Main", surface_name="Topo", keep_original_mesh=True, keep_original_surface=True)

# Sort the results of the intersection in the corresponding collections
bpy.data.collections[vol_coll_name].objects.link(m1)
for collection in m1.users_collection:
    if collection.name!=vol_coll_name:
        collection.objects.unlink(m1)  

bpy.data.objects.remove(m2, do_unlink=True)

bpy.data.collections[topo_coll_name].objects.link(org_surface)
for collection in org_surface.users_collection:
    if collection.name!=topo_coll_name:
        collection.objects.unlink(org_surface)  

bpy.data.collections[base_coll_name].objects.link(org_mesh)
for collection in org_mesh.users_collection:
    if collection.name!=base_coll_name:
        collection.objects.unlink(org_mesh)

# Hide the main body
org_mesh.hide_viewport = True

# Cut all volume meshes with the next surfaces. THIS HAS THE BE A CLEAN CUT THROUGH!!


for srf in [srf_b, srf_a]:
    for mesh in bpy.data.collections[vol_coll_name].all_objects:
        if not BlenderUtils.intersection_check([mesh.name, srf.name]):
            continue

        m1, m2, org_mesh, org_surface = BlenderUtils.split_with_surface(mesh_name=mesh.name, surface_name=srf.name, keep_original_mesh=False, keep_original_surface=True)


        if m1.name not in [i.name for i in bpy.data.collections[vol_coll_name].objects]:
            bpy.data.collections[vol_coll_name].objects.link(m1)
            for collection in m1.users_collection:
                if collection.name!=vol_coll_name:
                    collection.objects.unlink(m1)
            
        if m2.name not in [i.name for i in bpy.data.collections[vol_coll_name].objects]:        
            bpy.data.collections[vol_coll_name].objects.link(m2)
            for collection in m1.users_collection:
                if collection.name!=vol_coll_name:
                    collection.objects.unlink(m2)  

        if org_surface.name not in [i.name for i in bpy.data.collections[srf_coll_name].objects]:     
            bpy.data.collections[srf_coll_name].objects.link(org_surface)
            for collection in org_surface.users_collection:
                if collection.name!=srf_coll_name:
                    collection.objects.unlink(org_surface)  
    

# Hide the blender collections
bpy.data.collections[topo_coll_name].hide_viewport = True  
bpy.data.collections[srf_coll_name].hide_viewport = True  
bpy.data.collections[vol_coll_name].hide_viewport = True  


# Lazy identification of subsoil volumes as we know the order to be A-G-S.
z_max_collector = []
for m in bpy.data.collections[vol_coll_name].objects:
    bm = bmesh.new()
    bm.from_mesh(m.data)
    zmax = max([i.co.z for i in bm.verts])
    z_max_collector.append(zmax)
    bm.free()

names = [i.name for i in bpy.data.collections[vol_coll_name].objects]
names = [x for _, x in sorted(zip(z_max_collector, names), key=lambda x: x[0], reverse=True)]

layernames = ["A", "G", "S"]
for name_ind, name in enumerate(names):
    obj = bpy.data.collections[vol_coll_name].objects[name]
    obj.name = layernames[name_ind]


# ADD SOIL LAYERS TO IFC FILE
ifc_volumes = []
for obj in bpy.data.collections[vol_coll_name].objects:
    # Create entities
    vol_element = run("root.create_entity", model, ifc_class="IfcGeotechnicalStratum", predefined_type="SOLID", name=obj.name)
    # Create their geometries based on the meshes
    # Assign representations
    # Assign material (Materials with styles have already been created for the boreholes)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    vertices, faces = [], []
    for f in bm.faces:
        faces.append([v.index for v in f.verts])
    for v in bm.verts:
        vertices.append(v.co.to_tuple())
    vertices = [vertices]
    faces = [faces]
    bm.free()
    #vertices = [[(0.,0.,0.), (0.,2.,0.), (2.,2.,0.), (2.,0.,0.), (1.,1.,1.)]]
    #faces = [[(0,1,2,3), (0,4,1), (1,4,2), (2,4,3), (3,4,0)]]
    representation = ifcopenshell.api.geometry.add_mesh_representation(model, context=body, vertices=vertices, faces=faces)
    
    ifcopenshell.api.geometry.assign_representation(model, product=vol_element, representation=representation)
    run("aggregate.assign_object", model, products=[vol_element], relating_object=baugrundschichtenmodell)
    #run("spatial.assign_container", file=model, products = [vol_element], relating_structure=site)
    
    #run("spatial.assign_container", file=model, products = [vol_element], relating_structure=storey2)


    # Assign materials by Hauptgruppe. Note: Hauptgruppen have been mapped to material names prior      

    for k, v in mapping_hg_to_materialname.items():
        element_collector = []

        if obj.name == k:
            element_collector.append(vol_element)
            material = [i for i in model.by_type('IfcMaterial') if i.Name == v][0]   
            ifcopenshell.api.material.assign_material(model, products=element_collector, material=material)    
            break

    ifc_volumes.append(vol_element)


# Set attributes
for i in ifc_volumes:
    i.Description = "A volume representing a subsoil layer."


# Assign properties to the elements in ifc_bhs and ifc_volumnes

# Add a Pset for which a standard template is provided. See: https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/Pset_SolidStratumCapacity.htm
# Other ones are e.g. https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/Pset_SolidStratumComposition.htm
p = [i for i in ifc_volumes if i.Name=="S"][0]
Pset_SolidStratumCapacity = ifcopenshell.api.pset.add_pset(model, product=p, name="Pset_SolidStratumCapacity")
ifcopenshell.api.pset.edit_pset(model, pset=Pset_SolidStratumCapacity, properties={"CohesionBehaviour": 0, "FrictionAngle": 32.5, "PoisonsRatio":None}, should_purge=False)

p = [i for i in ifc_volumes if i.Name=="A"][0]
Pset_SolidStratumCapacity = ifcopenshell.api.pset.add_pset(model, product=p, name="Pset_SolidStratumCapacity")
ifcopenshell.api.pset.edit_pset(model, pset=Pset_SolidStratumCapacity, properties={"CohesionBehaviour": 5, "FrictionAngle": 15, "PoisonsRatio":0.2}, should_purge=False)

p = [i for i in ifc_volumes if i.Name=="G"][0]
Pset_SolidStratumCapacity = ifcopenshell.api.pset.add_pset(model, product=p, name="Pset_SolidStratumCapacity")
ifcopenshell.api.pset.edit_pset(model, pset=Pset_SolidStratumCapacity, properties={"CohesionBehaviour": 10_000, "FrictionAngle": 40, "PoisonsRatio":0.2}, should_purge=False)


for bh in ifc_bhs:
    Pset_BoreholeCommon = ifcopenshell.api.pset.add_pset(model, product=bh, name="Pset_BoreholeCommon")
    ifcopenshell.api.pset.edit_pset(model, pset=Pset_BoreholeCommon, properties={"BoreholeState": "INSTALLED", "GroundwaterDepth":None}, should_purge=False)


# Add custom properties using a custom property template
template = ifcopenshell.api.pset_template.add_pset_template(model, name="Fachsektionstage2025_template")
prop1 = ifcopenshell.api.pset_template.add_prop_template(model, pset_template=template, name="Wichte", description="Feuchtwichte des Bodens", template_type="P_SINGLEVALUE", primary_measure_type="IfcMassDensityMeasure") #kg/m3
prop1 = ifcopenshell.api.pset_template.add_prop_template(model, pset_template=template, name="WichteBounded", description="Feuchtwichte des Bodens", template_type="P_BOUNDEDVALUE", primary_measure_type="IfcMassDensityMeasure") #kg/m3

for p in ifc_volumes:
    pset = ifcopenshell.api.pset.add_pset(model, product=p, name="Fachsektionstage2025")
    ifcopenshell.api.pset.edit_pset(model, pset=pset, properties={"Wichte": 19_000, "IsFun": True}, pset_template=template)

# Save file and load the project
fp = parent_path+"/project_data/script_output_4x3.ifc"
model.write(fp)

# Add some issues for showing how the tests work
incorrect_layerelement = run("root.create_entity", model, ifc_class="IfcGeotechnicalStratum", name="wrong_borehole_name_xy", predefined_type="KEIN_ANSPRACHEBEREICH")
incorrect_layerelement2 = run("root.create_entity", model, ifc_class="IfcGeotechnicalStratum", name="wrong_borehole_name_xy", predefined_type="ANSPRACHEBEREICH")
incorrect_borehole = run("root.create_entity", model, ifc_class="IfcBorehole", name="wrong_borehole_name")
incorrect_borehole1 = run("root.create_entity", model, ifc_class="IfcBorehole", name="wrong_borehole_name")

fp = parent_path+"/project_data/script_output_4x3_with_errors.ifc"
model.write(fp)



proj = bpy.ops.bim.load_project(filepath=fp, use_relative_path=False, should_start_fresh_session=False)
print("Done.")
