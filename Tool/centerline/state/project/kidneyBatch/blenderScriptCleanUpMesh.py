import array
import bmesh
import bpy
import mathutils


def log_mesh_errors(objname) :
    nm, nm_len = check_non_manifold_edge(objname)
    i_f, i_f_len = check_intersect_face(objname)
    zf, zf_len, ze, ze_len = check_zero_faces_and_zero_edges(objname)
    nf, nf_len = check_non_flat_face(objname)
    vol, vert, face = get_stl_info(objname)
    return [vol, vert, face, nm_len, i_f_len, zf_len, ze_len, nf_len]

def clean_up_mesh(objname : str) -> bool : # 순서 중요함.
    # clean-up intersect faces 
    result = process_intersect_faces(objname)

    # clean-up non-manifold edges
    result = process_non_manifold_edges(objname)

    # clean-up zero faces
    result = process_zero_faces(objname)

    # clean-up non-flat faces
    result = process_non_flat_faces(objname)

    # triangulate
    # process_triangulate_all(objname)

    return True

def _sub_process_intersect_faces(objname, prev_numif : int) :
    # 1.2 make mani를 수행
    make_manifold_edge(objname)

    i_f3, i_f_len3 = check_intersect_face(objname)
    if i_f_len3 == 0 :
        return True
    if prev_numif == i_f_len3:
        # 1.3 intersect(knife)
        editmode_select_all(objname)##
        editmode_intersect_knife(objname)##
        i_f4, i_f_len4 = check_intersect_face(objname)
        if i_f_len4 == 0 :
            return True
        else :
            return False
    
def process_intersect_faces(objname) -> bool: 
    ''' i_f select -> dissolve face
        make manifold-edge
        all select -> intersect(knife)
    '''
    i_f, i_f_len = check_intersect_face(objname)
    if i_f_len == 0 : # intersect face 없음. 
        # print(f"{objname} intersected faces == 0")
        return True
    
    # 1.1 dissolve faces
    editmode_select_faces(objname, i_f)##
    editmode_dissolve_faces()

    i_f2, i_f_len2 = check_intersect_face(objname)
    
    if i_f_len2 == 0 :
        return True
    
    if i_f_len == i_f_len2 : #변화없음
        return _sub_process_intersect_faces(objname, i_f_len2)
    elif i_f_len2 < i_f_len : # 0개 아니지만 i_f보다 줄어듬
        # 1.1 dissolve faces again
        editmode_select_faces(objname, i_f2)##
        editmode_dissolve_faces()
        i_f3, i_f_len3 = check_intersect_face(objname)
        if i_f_len3 == 0 :
            return True
        return _sub_process_intersect_faces(objname, i_f_len3)

def process_non_manifold_edges(objname) -> bool: 
    ''' make manifold-edge
        non-mani select -> delete edge -> make manifold-edge 
    '''
    nm, nm_len = check_non_manifold_edge(objname)
    if nm_len == 0 : 
        return True
    
    make_manifold_edge(objname)

    nm2, nm_len2 = check_non_manifold_edge(objname)
    if nm_len2 == 0 : 
        return True
    
    editmode_select_edges(objname, nm2) ##
    editmode_delete_edges() 
    make_manifold_edge(objname)
    
    nm3, nm_len3 = check_non_manifold_edge(objname)
    if nm_len3 == 0 : 
        return True
    else :
        return False

def process_zero_faces(objname) -> bool: 
    ''' zero face select -> degenerate dissolve
        if non-mani > 0 -> make manifold-edge'''
    zf, zf_len, ze, ze_len = check_zero_faces_and_zero_edges(objname)

    if zf_len == 0 :
        return True

    editmode_select_faces(objname, zf)
    editmode_degenerate_dissolve(0.01)

    nm, nm_len = check_non_manifold_edge(objname)
    if nm_len > 0 :
        make_manifold_edge(objname)
        nm2, nm_len2 = check_non_manifold_edge(objname)
        if nm_len2 > 0:
            return False
    
    zf2, zf_len2, ze2, ze_len2 = check_zero_faces_and_zero_edges(objname)

    if zf_len2 > 0 :
        return False
    return True

def process_non_flat_faces(objname) -> bool: 
    ''' non-flat faces select -> triangulate face 
        if non-manifold edge > 0 -> make manifold edges
    '''
    nf, nf_len = check_non_flat_face(objname)
    if nf_len == 0 :
        return True
    editmode_select_faces(objname, nf)
    editmode_triangulate_faces()

    nm, nm_len = check_non_manifold_edge(objname)
    if nm_len > 0 :
        make_manifold_edge(objname)
        nm2, nm_len2 = check_non_manifold_edge(objname)
        if nm_len2 > 0:
            return False
        
    nf2, nf_len2 = check_non_flat_face(objname)
    if nf_len2 > 0 :
        return False
    return True

def process_triangulate_all(objname) : 
    editmode_select_all(objname)
    editmode_triangulate_faces()

def check_intersect_face(objname : str):
    obj = bpy.data.objects[objname]
    bpy.context.view_layer.objects.active = obj # active object

    bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(True)
    faces_intersect = _bmesh_check_self_intersect_object(obj)

    print("intersect face : " + str(len(faces_intersect)))
    return faces_intersect, len(faces_intersect)

def check_non_flat_face(objname : str) :
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj = bpy.data.objects[objname]
    obj.select_set(True)
    
    scene = bpy.context.scene
    print_3d = scene.print_3d
    angle_distort = print_3d.angle_distort

    bm = _bmesh_copy_from_object(obj, transform=True, triangulate=False)
    bm.normal_update()

    faces_distort = array.array(
            'i',
            (i for i, ele in enumerate(bm.faces) if _face_is_distorted(ele, angle_distort))
        )

    bm.free()
    
    print("non-flat face : " + str(len(faces_distort)))
    
    return faces_distort, len(faces_distort)

def check_non_manifold_edge(objname : str) :
    if bpy.context.mode == 'EDIT_MESH':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj = bpy.data.objects[objname]
    obj.select_set(True)
    
    bm = _bmesh_copy_from_object(obj, transform=False, triangulate=False)  #new code 0514

    edges_non_manifold = array.array('i', (i for i, ele in enumerate(bm.edges) if not ele.is_manifold))            

    bm.free()

    print("non-manifold edge : " + str(len(edges_non_manifold)))
    return edges_non_manifold, len(edges_non_manifold)

def check_zero_faces_and_zero_edges(objname : str) :
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj = bpy.data.objects[objname]
    obj.select_set(True)

    bm = _bmesh_copy_from_object(obj, transform=False, triangulate=False) #new code 0514
    
    scene = bpy.context.scene
    print_3d = scene.print_3d
    threshold = print_3d.threshold_zero
    faces_zero = array.array('i', (i for i, ele in enumerate(bm.faces) if ele.calc_area() <= threshold))
    edges_zero = array.array('i', (i for i, ele in enumerate(bm.edges) if ele.calc_length() <= threshold))

    bm.free()
    print("zero face : " + str(len(faces_zero)))
    print("zero edge : " + str(len(edges_zero)))
    return faces_zero, len(faces_zero), edges_zero, len(edges_zero)

def get_stl_info(stlname : str) :
    stlNameExceptExt = stlname
    
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj = bpy.data.objects[stlNameExceptExt]
    obj.select_set(True)
    # bpy.context.view_layer.objects.active = obj

    #volume
    bm = _bmesh_copy_from_object(obj, apply_modifiers=True)
    volume = bm.calc_volume()
    ## Verts, Faces
    verts = len(bm.verts)
    faces = len(bm.faces)
    

    bm.free()
    # return volume, verts, faces, tris
    return volume, verts, faces

def editmode_select_all(objname : str) -> None :
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj = bpy.data.objects[objname]
    bpy.ops.object.mode_set(mode = "EDIT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.mesh.select_all(action='SELECT')

def editmode_select_edges(objname : str, bm_array) -> None :
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj = bpy.data.objects[objname]
    bpy.ops.object.mode_set(mode = "EDIT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_mode(type='EDGE')

    bm = bmesh.from_edit_mesh(obj.data)
    elems = getattr(bm, "edges")[:]

    for i in bm_array:
        elems[i].select_set(True)
        
def editmode_select_faces(objname : str, bm_array) -> None :
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj = bpy.data.objects[objname]
    bpy.ops.object.mode_set(mode = "EDIT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_mode(type='FACE')

    bm = bmesh.from_edit_mesh(obj.data)
    elems = getattr(bm, "faces")[:]

    for i in bm_array:
        elems[i].select_set(True)

def editmode_dissolve_edges() :
    bpy.ops.mesh.dissolve_edges(use_verts=True, use_face_split=True)

def editmode_delete_edges() :
    bpy.ops.mesh.delete(type='EDGE')

def editmode_dissolve_faces() :
    bpy.ops.mesh.dissolve_faces(use_verts=True)

def editmode_degenerate_dissolve(thresh) :
    bpy.ops.mesh.dissolve_degenerate(threshold=thresh)

def editmode_intersect_knife(objname : str) :
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj = bpy.data.objects[objname]
    bpy.ops.object.mode_set(mode = "EDIT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.select_mode(type='FACE')
    bpy.ops.mesh.intersect(mode='SELECT', separate_mode='NONE', solver='EXACT')

def make_manifold_edge(objname : str) -> None :
    threshold = 0.0001
    sides = 0
    
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj = bpy.data.objects[objname]
    bpy.ops.object.mode_set(mode = "EDIT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    __setup_environment()
    bm_key_orig = __elem_count(obj)

    __delete_loose()
    __delete_interior()
    __remove_doubles(threshold)
    __dissolve_degenerate(threshold)
    __fix_non_manifold(obj, sides)  # may take a while
    __make_normals_consistently_outwards()

    bm_key = __elem_count(obj)

    verts = bm_key[0] - bm_key_orig[0]
    edges = bm_key[1] - bm_key_orig[1]
    faces = bm_key[2] - bm_key_orig[2]
    print(("Modified: {:+} vertices, {:+} edges, {:+} faces").format(verts, edges, faces))

def editmode_triangulate_faces() : 
    bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')

#===========================================================================
def _bmesh_check_self_intersect_object(obj):
    """
    Check if any faces self intersect
    returns an array of edge index values.
    """

    if not obj.data.polygons:
        return array.array('i', ())

    bm = _bmesh_copy_from_object(obj, transform=False, triangulate=False)
    tree = mathutils.bvhtree.BVHTree.FromBMesh(bm, epsilon=0.00001)

    overlap = tree.overlap(tree)
    faces_error = {i for i_pair in overlap for i in i_pair}

#    print(f"len of intersect faces = {len(faces_error)}")
#    
#    if len(faces_error) > 0: 
#        ret = bmesh.ops.dissolve_faces(bm, faces_error, use_verts=True)
#        print(f"after len of intersect faces = {len(faces_error)}")
    # jys add
    bm.free()

    return array.array('i', faces_error)

def _bmesh_copy_from_object(obj, transform=True, triangulate=True, apply_modifiers=False):
    """
    Returns a transformed, triangulated copy of the mesh
    """

    assert(obj.type == 'MESH')

    if apply_modifiers and obj.modifiers:
        
        me = obj.to_mesh(bpy.context.scene, True, 'PREVIEW', calc_tessface=False)
        bm = bmesh.new()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
        del bpy
    else:
        me = obj.data
        if obj.mode == 'EDIT':
            bm_orig = bmesh.from_edit_mesh(me)
            bm = bm_orig.copy()
        else:
            bm = bmesh.new()
            bm.from_mesh(me)

    if transform:
        bm.transform(obj.matrix_world)

    if triangulate:
        bmesh.ops.triangulate(bm, faces=bm.faces)

    return bm

def _face_is_distorted(ele, angle_distort):
    no = ele.normal
    angle_fn = no.angle

    for loop in ele.loops:
        loopno = loop.calc_normal()

        if loopno.dot(no) < 0.0:
            loopno.negate()

        if angle_fn(loopno, 1000.0) > angle_distort:
            return True

    return False
#===========================================================================

def __setup_environment():
    """set the mode as edit, select mode as vertices, and reveal hidden vertices"""
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(type='VERT')
    bpy.ops.mesh.reveal()

def __remove_doubles(threshold):
    """remove duplicate vertices"""
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=threshold)

def __delete_loose():
    """delete loose vertices/edges/faces"""
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=True)

def __delete_interior():
    """delete interior faces"""
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_interior_faces()
    bpy.ops.mesh.delete(type='FACE')

def __dissolve_degenerate(threshold):
    """dissolve zero area faces and zero length edges"""
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.dissolve_degenerate(threshold=threshold)

def __make_normals_consistently_outwards():
    """have all normals face outwards"""
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent()


def __select_non_manifold_verts(use_wire=False, 
                            use_boundary=False,
                            use_multi_face=False,
                            use_non_contiguous=False,
                            use_verts=False
                            ):
    """select non-manifold vertices"""
    bpy.ops.mesh.select_non_manifold(
        extend=False,
        use_wire=use_wire,
        use_boundary=use_boundary,
        use_multi_face=use_multi_face,
        use_non_contiguous=use_non_contiguous,
        use_verts=use_verts,
    )

def __count_non_manifold_verts(obj):
    """return a set of coordinates of non-manifold vertices"""
    __select_non_manifold_verts(use_wire=True, use_boundary=True, use_verts=True)

    bm = bmesh.from_edit_mesh(obj.data)
    return sum((1 for v in bm.verts if v.select))

def __elem_count(obj):
        bm = bmesh.from_edit_mesh(obj.data)
        return len(bm.verts), len(bm.edges), len(bm.faces)

def __fill_non_manifold(sides):
    """fill in any remnant non-manifolds"""
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.fill_holes(sides=sides)

def __delete_newly_generated_non_manifold_verts():
    """delete any newly generated vertices from the filling repair"""
    __select_non_manifold_verts(use_wire=True, use_verts=True)
    bpy.ops.mesh.delete(type='VERT')    

def __fix_non_manifold(obj, sides):
    """naive iterate-until-no-more approach for fixing manifolds"""

    total_non_manifold = __count_non_manifold_verts(obj)

    if not total_non_manifold:
        return

    bm_states = set()
    bm_key = __elem_count(obj)
    bm_states.add(bm_key)

    while True:
        __fill_non_manifold(sides)
        __delete_newly_generated_non_manifold_verts()

        bm_key = __elem_count(obj)
        if bm_key in bm_states:
            break
        else:
            bm_states.add(bm_key)