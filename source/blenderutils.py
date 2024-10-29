import bpy
import bmesh
import math
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri

class BlenderUtils:
    def __init__(self) -> None:
        pass

    
    @staticmethod
    def intersection_check(obj_name_list, scene=bpy.context.scene):
        #check every object for intersection with every other object
        for obj_now in obj_name_list:
            for obj_next in obj_name_list:
                if obj_now == obj_next:
                    continue

                #create bmesh objects
                bm1 = bmesh.new()
                bm2 = bmesh.new()

                #fill bmesh data from objects
                bm1.from_mesh(scene.objects[obj_now].data)
                bm2.from_mesh(scene.objects[obj_next].data)            

                bm1.transform(scene.objects[obj_now].matrix_world)
                bm2.transform(scene.objects[obj_next].matrix_world) 

                #make BVH tree from BMesh of objects
                obj_now_BVHtree = BVHTree.FromBMesh(bm1)
                obj_next_BVHtree = BVHTree.FromBMesh(bm2)           

                #get intersecting pairs
                inter = obj_now_BVHtree.overlap(obj_next_BVHtree)

                #if list is empty, no objects are touching
                if inter != []:
                    return True
                else:
                    return False



    @staticmethod
    def compute_xy_distances(test_pt, pts):
        """
        Compute the distance of a point ([x,y,z]) to each point in the list pts.
        works with points [x,y] as well.
        """
        distances = []
        for pt in pts:
            dist = math.sqrt((pt[0] - test_pt[0])**2 + (pt[1] - test_pt[1])**2)
            distances.append(dist)
        return distances


    @staticmethod
    def add_testmesh(vertices, faces, name="testmesh"):
        """Quick util function for development. Adds a mesh to the scene"""
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        scene = bpy.context.scene
        scene.collection.objects.link(obj)
        return obj, mesh

    @staticmethod
    def detectByFaces():
        """
        Find isolated parts of a mesh by faces from the current object from the edit context
        """
        raw, island, visited  = [], [], []
        mesh=bmesh.from_edit_mesh(bpy.context.object.data)
        bpy.ops.mesh.select_mode(type="FACE")
        bpy.ops.mesh.select_all(action='DESELECT')
        for f in mesh.faces:
            if f.index not in raw:
                f.select = True
                bpy.ops.mesh.select_linked()
                for fs in mesh.faces:
                    if fs.select:
                        island.append(fs.index)
                        raw.append(fs.index)
                bpy.ops.mesh.select_all(action='DESELECT')
                if island not in visited:
                    visited.append(island[:])
                    island.clear()
        return visited
    
    @staticmethod
    def split_with_surface(mesh_name, surface_name, keep_original_mesh=True, keep_original_surface=True):
        """
        This method is used to split one closed mesh with one surface like open mesh into
        two closed meshes.

        Note that there are several assumption made. Ensure that the split will return two meshes.

        Returns two objects with the names mesh_name+_1 and mesh_name+_2

        # Example
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        name_object1 = "mesh1"
        name_object2 = "surface1"

        # Add test models
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        obj1 = bpy.context.object
        obj1.name=name_object1

        bpy.ops.mesh.primitive_plane_add(location=(0, 0, 0))
        obj2 = bpy.context.object
        obj2.name = name_object2
        obj2.scale = (2, 2, 1)  # Scale on X axis
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        m1, m2, org = BlenderUtils.split_with_surface(mesh_name=name_object1, surface_name=name_object2, keep_original_mesh=False)
        
        """
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        
       
        if keep_original_mesh:
            src_obj = bpy.data.objects[mesh_name]
            C = bpy.context  
            new_obj = src_obj.copy()
            new_obj.data = src_obj.data.copy()
            new_obj.name = mesh_name + "_org"
            new_obj.animation_data_clear()
            C.collection.objects.link(new_obj)

        if keep_original_surface:
            src_obj = bpy.data.objects[surface_name]
            C = bpy.context  
            new_obj = src_obj.copy()
            new_obj.data = src_obj.data.copy()
            new_obj.name = surface_name + "_org"
            new_obj.animation_data_clear()
            C.collection.objects.link(new_obj)

        # get both objects

        obj1 = bpy.data.objects[mesh_name]
        obj2 = bpy.data.objects[surface_name]

        # Join operation - select both objects, set one as the active one

        obj1.select_set(True)
        obj2.select_set(True)
        bpy.context.view_layer.objects.active = obj1
        bpy.ops.object.join()
        
        # Duplicate the joined object   
        joined_object = bpy.context.object  # This is now the joined object
        joined_object.name = joined_object.name +"_1"

        bpy.ops.object.duplicate()
        copy = bpy.context.object
        copy.name = joined_object.name[:-1] +"2"

        joined_object = bpy.data.objects[joined_object.name]
        joined_object.select_set(True)    
        bpy.context.view_layer.objects.active = joined_object

        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")

        bpy.ops.mesh.select_mode(type="VERT")
        bm = bmesh.from_edit_mesh(joined_object.data)
        for v in bm.verts:
            v.select = True
            break
        bmesh.update_edit_mesh(joined_object.data) 
        bpy.ops.mesh.select_linked(delimit={'SEAM'})

        bpy.ops.mesh.intersect(mode='SELECT_UNSELECT', separate_mode='ALL', threshold=1e-06, solver='EXACT')
        

        faces = BlenderUtils.detectByFaces()

        for i in[0,3]:
            bm = bmesh.from_edit_mesh(bpy.context.edit_object.data)
            bm.faces.ensure_lookup_table()
            bm.faces[faces[i][0]].select = True  # select by index
            bmesh.update_edit_mesh(bpy.context.edit_object.data)
            bm.free()
            bpy.ops.mesh.select_linked(delimit={'SEAM'})

        bpy.ops.mesh.remove_doubles(threshold=0.0001, use_unselected=False, use_sharp_edge_from_normals=False)

        # INVERT SELCETION
        mesh = bmesh.from_edit_mesh(bpy.context.edit_object.data)
        for elem in mesh.verts if mesh.select_mode & {'VERT'} else (mesh.edges if mesh.select_mode & {'EDGE'} else mesh.faces):
            elem.select = not elem.select
        bmesh.update_edit_mesh(bpy.context.edit_object.data)
        # DELETE SELECTION
        bpy.ops.mesh.delete(type='VERT')




        # NOW FOR THE SECOND PART
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")

        copy = bpy.data.objects[copy.name]
        copy.select_set(True)    
        bpy.context.view_layer.objects.active = copy

        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.mesh.select_mode(type="VERT")

        bm = bmesh.from_edit_mesh(copy.data)
        for v in bm.verts:
            v.select = True
            break
        bmesh.update_edit_mesh(copy.data) 
        bpy.ops.mesh.select_linked(delimit={'SEAM'})
        bpy.ops.mesh.intersect(mode='SELECT_UNSELECT', separate_mode='ALL', threshold=1e-06, solver='EXACT')
        faces = BlenderUtils.detectByFaces()
        for i in[1,3]:
            bm = bmesh.from_edit_mesh(bpy.context.edit_object.data)
            bm.faces.ensure_lookup_table()
            bm.faces[faces[i][0]].select = True  # select by index
            bmesh.update_edit_mesh(bpy.context.edit_object.data)
            bm.free()
            bpy.ops.mesh.select_linked(delimit={'SEAM'})
        bpy.ops.mesh.remove_doubles(threshold=0.0001, use_unselected=False, use_sharp_edge_from_normals=False)
        # INVERT SELCETION
        mesh = bmesh.from_edit_mesh(bpy.context.edit_object.data)
        for elem in mesh.verts if mesh.select_mode & {'VERT'} else (mesh.edges if mesh.select_mode & {'EDGE'} else mesh.faces):
            elem.select = not elem.select
        bmesh.update_edit_mesh(bpy.context.edit_object.data)
        # DELETE SELECTION
        bpy.ops.mesh.delete(type='VERT')


        # FINISH SECOND PART.

        bpy.ops.object.mode_set(mode="OBJECT")


        if keep_original_mesh:
            org_mesh = bpy.data.objects[mesh_name+"_org"]
        else:
            org_mesh = None
        
        if keep_original_surface:
            org_surface = bpy.data.objects[surface_name+"_org"]
        else: 
            org_surface = None

        
        return bpy.data.objects[mesh_name+"_1"], bpy.data.objects[mesh_name+"_2"], org_mesh, org_surface




