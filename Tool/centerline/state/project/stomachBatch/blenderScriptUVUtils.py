# blenderScriptUVUtils.py

import bpy
import bmesh
from mathutils import Vector

def project_from_view_bounds(obj_name: str, projection: str = "FRONT"):
    """
    지정한 이름의 Mesh 오브젝트에 대해 UV를 생성하고 'UVMap'으로 설정합니다.
    
    Parameters:
    - obj_name (str): 대상 오브젝트 이름
    - projection (str): 투영 방향 - "BACK", "BOTTOM", "SIDE" 중 하나
    """
    print(f"[UV] Project from view(bounds): {obj_name} | projection={projection}")

    obj = bpy.data.objects.get(obj_name)
    if not obj or obj.type != 'MESH':
        print(f"'{obj_name}' is not a mesh or doesn't exist.")
        return

    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()

    # UV 레이어 생성 또는 선택
    uv_layer = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")

    # 투영 방향 설정
    projection_axis = {
        "FRONT": Vector((0, 1, -1)),     
        "BACK": Vector((0, -1, 1)),      
        "BOTTOM": Vector((0, 0, -1))      
    }.get(projection.upper(), Vector((0, 0, -1)))  # 기본값: BACK

    world_matrix = obj.matrix_world
    uvs = []

    for face in bm.faces:
        for loop in face.loops:
            world_co = world_matrix @ loop.vert.co
            projected = world_co - projection_axis * world_co.dot(projection_axis)
            uv = Vector((projected.x, projected.y))
            loop[uv_layer].uv = uv
            uvs.append(uv)

    # UV 정규화 (scale_to_bounds)
    if uvs:
        min_uv = Vector((min(uv.x for uv in uvs), min(uv.y for uv in uvs)))
        max_uv = Vector((max(uv.x for uv in uvs), max(uv.y for uv in uvs)))
        size_uv = max_uv - min_uv
        for face in bm.faces:
            for loop in face.loops:
                uv = loop[uv_layer].uv
                uv.x = (uv.x - min_uv.x) / size_uv.x if size_uv.x != 0 else 0
                uv.y = (uv.y - min_uv.y) / size_uv.y if size_uv.y != 0 else 0

    bm.to_mesh(mesh)
    bm.free()

    # UVMap 이름 설정
    uv_layers = mesh.uv_layers
    if uv_layers:
        uv_layers.active.name = "UVMap"
        uv_layers.active_index = 0
        print(f"✅ UVMap '{uv_layers.active.name}' set on object '{obj_name}' with projection '{projection}'")

# import sys
# if __name__ == "__main__" :

#     sys.path.append("C:/your/path/to/scripts")  # blenderScriptUVUtils.py 위치 경로로 수정

#     from blenderScriptUVUtils import project_from_view_bounds

#     project_from_view_bounds("Chest", projection="BACK")
#     project_from_view_bounds("Rib", projection="SIDE")
