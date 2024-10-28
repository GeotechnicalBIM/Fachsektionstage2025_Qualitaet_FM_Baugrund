import bpy
import bmesh

class BlenderUtils:
    def __init__(self) -> None:
        pass

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
    def split_with_surface(mesh_name, surface_name, keep_original_mesh=True):
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


        if not keep_original_mesh:
            return bpy.data.objects[mesh_name+"_1"], bpy.data.objects[mesh_name+"_2"], None
        else:
            return bpy.data.objects[mesh_name+"_1"], bpy.data.objects[mesh_name+"_2"], bpy.data.objects[mesh_name+"_2"]




