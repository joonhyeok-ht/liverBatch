'''
'''
import bpy
import bmesh

import os, sys
import json
import re
import shutil
import math
import time

kidney_batchPath = os.path.abspath(os.path.dirname(__file__))
resPath = os.path.abspath(os.path.dirname(kidney_batchPath))
sys.path.append(kidney_batchPath)
sys.path.append(resPath)

import common.blenderOption as blenderOption



class CBSPSepClean(blenderOption.CBlenderScriptBase) :
    '''
    warning : must be executed background mode

    param
        - 없음 
    '''
    def __init__(self, optionFullPath : str) -> None :
        super().__init__(optionFullPath)
        # input your code
    def clear(self) :
        # input your code
        super().clear()
    def process(self) -> bool :
        ## in/out separate를 수행하고, mesh clean, rotate 등의 마무리 작업 수행
        if self.Ready == False :
            print("blender script Recon error : not found option")
            return False
        
        # 이미 원하는 blend 파일을 로딩한 상황이라고 가정 
        
        # patientBlenderName = os.path.join(self.m_auto02Path, f"{self.m_patientID}.blend")
        # bpy.ops.wm.open_mainfile(filepath=patientBlenderName) 
        
        # #separate stl 수행전에 해당 오브젝트들의 mesh error를 제거한다.
        # #centerline을 추출할 오브젝트도 함께 cleanup
        # valid_clean_list = self._get_valid_object_list(["Kidney", "Renal_artery", "Renal_vein", "Ureter", "Rectus_*"])
        # self._init_cleanup(valid_clean_list) 
        # self._cleanup()

        if "SeparatedSTLNameList" in self.m_optionInfo.m_jsonData["Blender"] :
            listSepInfo = self.m_optionInfo.m_jsonData["Blender"]["SeparatedSTLNameList"]
            self._separation_stl(listSepInfo)
        
        self._switch_to_collection()

        listRecalcNormal = ["Diaphragm"]
        for objname in listRecalcNormal :
            blenderOption.CBlenderScriptUtil.recalc_normal(objname, toInside=False)
        
        self._make_flat("Diaphragm")  # 이게 뭘까? 

        # cleanup
        iCnt = self.m_optionInfo.get_cleanup_meshname_count()
        for inx in range(0, iCnt) :
            meshname = self.m_optionInfo.get_cleanup_meshname(inx)
            blenderOption.CBlenderScriptUtil.cleanup(meshname)
        
        # rotation z, 90 degree
        blenderOption.CBlenderScriptUtil.rotation_all_z(90.0)

        # # shade smooth and All Transforms 적용
        self._apply_all_transforms()


        # smartUV
        iCnt = self.m_optionInfo.get_smartuv_meshname_count()
        for inx in range(0, iCnt) :
            meshname = self.m_optionInfo.get_smartuv_meshname(inx)
            blenderOption.CBlenderScriptUtil.smartuv(meshname)
        
        # rename mesh check
        blenderOption.CBlenderScriptUtil.match_mesh_data_name()
        blenderOption.CBlenderScriptUtil.delete_etc_objects()

        ## Renal_artery island 개수 체크(작은조각제외), island 2개 이상이라면, Renal_artery blender 자동 separate
        len_islands = self.split_object_by_mesh_islands("Renal_artery", "RA_")
        ## island 2개 이상이라면, ARA자동생성 : Aorta와 Renal_artery UNION (blender union modifier이용)
        if len_islands > 1 :
            blenderOption.CBlenderScriptUtil.delete_object("ARA")
            self.boolean_union("Aorta", "Renal_artery", "ARA")

        # DataRootPath의 해당 저장 폴더에 최종 파일 저장하기.
        blenderOption.CBlenderScriptUtil.save_blender()
        # self._save_blender_with_bak(self.m_auto03Path, self.m_patientID)

        # must be background mode 
        bpy.ops.wm.quit_blender()
        return True 
    

    # kidney,stomach 공통
    def _switch_to_collection(self) :
        context = bpy.context
        layer = context.view_layer
        scene_collection = context.layer_collection.collection
        objects = scene_collection.objects

        if len(objects) > 0 :
            bpy.ops.object.select_all(action='DESELECT')
            obj = bpy.data.objects[objects[0].name]
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

            layer.update()
    def _remove_uvmap_and_material_index(self, obj_name) :
        # 24.07.26
        # Attributes 창에서 수동으로 material_index 와 UVMap을 삭제하던것을 코드화함.
        # in, out 붙은 object로 테스트 하면 됨.(ureter_in, ureter_out)

        mesh = bpy.data.meshes[obj_name]

        obj = bpy.data.objects[obj_name]
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        #uv개수 보지 않고 그냥 지우면 에러남
        print(f"{obj_name}'s uv_layers length : ", len(mesh.uv_layers))
        if len(mesh.uv_layers) > 0:
            uv_layer = mesh.uv_layers.active.data
            obj.data.uv_layers.remove(obj.data.uv_layers[obj.data.uv_layers.active_index])
            print(f"remove {obj_name}'s uv_layer")

        obj.data.materials.clear() #ok
        print(f"remove {obj_name}'s material")
        bpy.ops.object.select_all(action='DESELECT')
        
    def _separation_stl(self, separateList) : #Version : HuBlenderKidInOutSep_v1.1.0
        #bpy.ops.object.mode_set(mode='OBJECT')
        for stlNameExceptExt in separateList :
            if stlNameExceptExt in bpy.data.objects :
                self.__separation_object(stlNameExceptExt)
                print(f"separated {stlNameExceptExt}")
                self._remove_uvmap_and_material_index(f"{stlNameExceptExt}_in")
                self._remove_uvmap_and_material_index(f"{stlNameExceptExt}_out")
        print("passed separated stl")     
    def __separation_object(self, stlNameExceptExt: str):
        kidney_obj = bpy.data.objects.get("Kidney")
        if kidney_obj is None:
            print("Error: Kidney object not found.")
            return

        original = bpy.data.objects.get(stlNameExceptExt)
        if original is None:
            print(f"Error: Object '{stlNameExceptExt}' not found.")
            return

        stlNameExceptExtIn = f"{stlNameExceptExt}_in"
        stlNameExceptExtOut = f"{stlNameExceptExt}_out"

        # 1. 복사본 2개 생성
        obj_out = original.copy()
        obj_out.data = original.data.copy()
        bpy.context.collection.objects.link(obj_out)

        obj_in = original.copy()
        obj_in.data = original.data.copy()
        bpy.context.collection.objects.link(obj_in)

        # 2. 기존 오브젝트 이름 변경 (원본 그대로 유지)
        original.name = stlNameExceptExt
        original.data.name = stlNameExceptExt

        # 3. 복사본 이름 변경
        obj_out.name = stlNameExceptExtOut
        obj_out.data.name = stlNameExceptExtOut
        obj_in.name = stlNameExceptExtIn
        obj_in.data.name = stlNameExceptExtIn

        # 4. Boolean 연산 설정 및 적용 (데이터 API로 직접 적용)
        for obj, operation in [
            (obj_out, 'DIFFERENCE'),
            (obj_in, 'INTERSECT')
        ]:
            boolean_modifier = obj.modifiers.new(name="Boolean", type='BOOLEAN')
            boolean_modifier.object = kidney_obj
            boolean_modifier.operation = operation
            boolean_modifier.solver = "FAST"

            # Boolean 적용 후 메쉬 교체 (안전하게)
            depsgraph = bpy.context.evaluated_depsgraph_get()
            obj_eval = obj.evaluated_get(depsgraph)

            new_mesh = bpy.data.meshes.new_from_object(
                obj_eval,
                preserve_all_data_layers=True,
                depsgraph=depsgraph
            )

            obj.data = new_mesh
            obj.modifiers.clear()

        print("Boolean separation completed.")
    def _make_flat(self, object_name) :
        # 해당 오브젝트가 있는지 체크
        namelist = []
        objs = bpy.data.objects
        for obj in objs : 
            namelist.append(obj.name)
        if object_name not in namelist :
            print(f"_make_flat() : {object_name} is not in Mesh Objects. Skip.")
            return
        
        # 오브젝트 가져오기
        obj = bpy.data.objects.get(object_name)
        if obj is None:
            raise ValueError(f"'{object_name}' 을(를) 찾을 수 없습니다.")
        if obj.type != 'MESH':
            raise TypeError(f"'{object_name}' 는 메쉬가 아닙니다.")

        # 메쉬 데이터 접근
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)

        # 1. 모든 face dissolve
        bmesh.ops.dissolve_faces(bm, faces=bm.faces[:], use_verts=False)

        # 2. triangulate faces
        bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')

        # 결과 반영
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

        print(f"'{object_name}' 처리 완료: faces dissolve + triangulate .")

    def _join_object_a_and_b(self, objNameA, objNameB, joinedName):
        ## objNameA 와 objNameB를 join하여 joinedName 으로 생성.
        # 모든 오브젝트 선택 해제
        bpy.ops.object.select_all(action='DESELECT')
        # keyword(=Cyst) 가 들어가는 object를 리스트에 저장
        objects_to_join = [obj for obj in bpy.context.scene.objects if objNameA in obj.name or objNameB in obj.name]
        print(f"objects_to_join[] : {objects_to_join}")
        if len(objects_to_join) >= 2 :
                
            bpy.context.view_layer.objects.active = objects_to_join[0]
            for obj in objects_to_join:
                obj.select_set(True)
            bpy.ops.object.join()
            
            joined_obj = bpy.context.active_object

            joined_obj.name = joinedName
            joined_obj.data.name = joinedName
    def split_object_by_mesh_islands(self, obj_name: str, prefix: str):
        ## obj_name 이 2개 이상의 분리된 mesh로 이뤄져 있다면 각각 분리한 후 prefix에 넘버를 붙여 생성한다.
        src_obj = bpy.data.objects.get(obj_name)
        if not src_obj or src_obj.type != 'MESH':
            print(f"Object '{obj_name}' not found or not a mesh.")
            return

        # 메쉬 데이터 접근
        src_mesh = src_obj.data

        # BMesh로 로드
        bm = bmesh.new()
        bm.from_mesh(src_mesh)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        # 루즈 파트(연결된 요소) 찾기
        islands = []
        visited = set()
        for v in bm.verts:
            if v.index in visited:
                continue
            stack = [v]
            connected = set()
            while stack:
                cur = stack.pop()
                if cur.index in visited:
                    continue
                visited.add(cur.index)
                connected.add(cur)
                for e in cur.link_edges:
                    other = e.other_vert(cur)
                    if other.index not in visited:
                        stack.append(other)
            islands.append(list(connected))

        print(f"Found {len(islands)} separate mesh islands in '{obj_name}'")

        len_islands = len(islands)
        if len_islands == 1 :
            bm.free()
            return len_islands

        # 각 island별로 새로운 mesh 생성
        for i, verts in enumerate(islands, start=1):
            bm_new = bmesh.new()
            vert_map = {}

            # 새로운 bm에 verts 복제
            for v in verts:
                vert_map[v] = bm_new.verts.new(v.co)

            # edges/faces 복제
            for f in bm.faces:
                if all(v in verts for v in f.verts):
                    bm_new.faces.new([vert_map[v] for v in f.verts])

            bm_new.normal_update()

            # 새로운 mesh 데이터 생성
            new_mesh = bpy.data.meshes.new(f"{prefix}{i:d}")
            bm_new.to_mesh(new_mesh)
            bm_new.free()

            # 새로운 object 생성 및 링크
            new_obj = bpy.data.objects.new(new_mesh.name, new_mesh)
            new_obj.matrix_world = src_obj.matrix_world.copy()
            bpy.context.collection.objects.link(new_obj)

            print(f"Created: {new_obj.name}")

        bm.free()
        print(f"Done. Original '{obj_name}' kept intact.")
        return len_islands
    def boolean_union(self, a_name: str, b_name: str, c_name: str):
        # 오브젝트 참조
        obj_a = bpy.data.objects.get(a_name)
        obj_b = bpy.data.objects.get(b_name)
        if obj_a is None or obj_b is None:
            print(f"⚠️ Object not found: {a_name if obj_a is None else b_name}")
            return None

        # A 복제 → 새 Object C 생성 (mesh data도 완전히 분리)
        obj_c = obj_a.copy()
        obj_c.data = obj_a.data.copy()
        obj_c.name = c_name
        bpy.context.collection.objects.link(obj_c)

        # Boolean Modifier 추가
        bool_mod = obj_c.modifiers.new(name="UnionBoolean", type='BOOLEAN')
        bool_mod.operation = 'UNION'
        bool_mod.object = obj_b
        bool_mod.solver = 'EXACT'  # 정확한 연산 ('FAST'도 가능)

        # Modifier 적용
        bpy.context.view_layer.objects.active = obj_c
        bpy.ops.object.select_all(action='DESELECT')
        obj_c.select_set(True)
        bpy.ops.object.modifier_apply(modifier=bool_mod.name)

        # 이름 정리
        obj_c.data.name = c_name

        print(f" Boolean Union complete: {a_name} + {b_name} → {c_name}")
        print(f"   Original '{a_name}', '{b_name}' kept intact.")
        return obj_c
    def _apply_all_transforms(self) :
        # Object Mode로 전환 (필수)
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        # 모든 메시 오브젝트에 대해 처리
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                # 활성화 및 선택
                bpy.context.view_layer.objects.active = obj
                obj.select_set(True)

                # All Transforms 적용 (Location, Rotation, Scale)
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

                # 선택 해제
                obj.select_set(False)



def find_param(args : list, paramName : str) :
    try:
        inx = args.index(paramName)
        return args[inx + 1]
    except ValueError:
        print(f"not found param : {paramName}")
    return None
def exist_param(args : list, paramName : str) -> bool :
    try:
        inx = args.index(paramName)
        return True
    except ValueError:
        print(f"not found param : {paramName}")
    return False

if __name__=='__main__' :
    args = sys.argv

    if "--" in args :
        inx = args.index("--")
        scriptArgs = args[inx + 1 : ]

        optionFullPath = find_param(scriptArgs, "--optionFullPath")

        if optionFullPath is None :
            print(f"blender script : not found param")
        else :
            print("-" * 30)
            print(f"blender script : optionFullPath -> {optionFullPath}")
            print("-" * 30)
            inst = CBSPSepClean(optionFullPath)
            inst.process()

