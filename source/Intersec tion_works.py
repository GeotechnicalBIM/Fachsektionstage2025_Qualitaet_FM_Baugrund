import bpy
import bmesh
"""

Das doppelte stück bekommen wir über:
    intersect boolean difference
        - first select the cube
Die beiden einzelnen Teile bekommen wir über
    intersect knife, ALL

"""


if bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')


name_object1 = "Testcube"
name_object2 = "Testplane"

# Delete old versions.
obj = bpy.data.objects.get(name_object1)
bpy.ops.object.delete()
obj = bpy.data.objects.get(name_object2)
bpy.ops.object.delete()

# Add test models
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
obj1 = bpy.context.object
obj1.name=name_object1

bpy.ops.mesh.primitive_plane_add(location=(0, 0, 0))
obj2 = bpy.context.object
obj2.name = name_object2
obj2.scale = (2, 2, 1)  # Scale on X axis
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)



# Join operation - select both objects, set one as the active one
obj1.select_set(True)
obj2.select_set(True)
bpy.context.view_layer.objects.active = obj1
bpy.ops.object.join()


# Duplicate the joined object
joined_object = bpy.context.object  # This is now the joined object
#bpy.ops.object.duplicate()

bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="DESELECT")
#bpy.ops.mesh.select_linked(delimit={'SEAM'})

#joined_object.data.vertices[0].select = True
bpy.ops.mesh.select_mode(type="VERT")
bm = bmesh.from_edit_mesh(joined_object.data)
for v in bm.verts:
    v.select = True
    break
bmesh.update_edit_mesh(joined_object.data) 
bpy.ops.mesh.select_linked(delimit={'SEAM'})

bpy.ops.mesh.intersect(mode='SELECT_UNSELECT', separate_mode='ALL', threshold=1e-06, solver='EXACT')





def detectByFaces():
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
    #print("islands (faces): ", visited)
    #print("total islands: ", len(visited))
    return visited
    

faces = detectByFaces()
print(faces)



#ob_dup = bpy.context.edit_object.copy()
#ob_dup.data = bpy.context.edit_object.data.copy()




for i in[0,3]:
    bm = bmesh.from_edit_mesh(bpy.context.edit_object.data)
    bm.faces.ensure_lookup_table()
    bm.faces[faces[i][0]].select = True  # select by index
    bmesh.update_edit_mesh(bpy.context.edit_object.data)
    bm.free()

    bpy.ops.mesh.select_linked(delimit={'SEAM'})


bpy.ops.mesh.remove_doubles(threshold=0.0001, use_unselected=False, use_sharp_edge_from_normals=False)

#for i in [1,2]:
#    bmesh.ops.delete( bm, geom = faces, context = 'FACES_ONLY' )

# INVERT SELCETION
# DELETE