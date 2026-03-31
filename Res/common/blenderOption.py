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

tmpPath = os.path.abspath(os.path.dirname(__file__))
sys.path.append(tmpPath)

import blenderScriptCleanUpMesh as clmsh



class CBlenderScriptUtil :
    @staticmethod
    def parse_array_token(inputArrayStr : str) :
        '''
        inputStr : ex)a[1,10], A[1,10], ..

        ret :
            - a[1,10] -> [a1, a2, .. , a10]
        '''
        match = re.search(r'([a-zA-Z0-9_]+)\[(\d+),(\d+)\]', inputArrayStr)
        if match :
            prefix = match.group(1)         # 문자 부분 추출
            start = int(match.group(2))     # 시작 숫자
            end = int(match.group(3))       # 끝 숫자
            result = [f"{prefix}{num}" for num in range(start, end + 1)]
            return result
        else :
            return None
    @staticmethod
    def parse_star_token(inputStarStr : str, listStr : list) -> list :
        '''
        inputStarStr : ex) a*, A*, test*

        ret :
            - a* -> listStr 중 a로 시작하는 모든 문자열
        '''

        match = re.search(r'^([a-zA-Z0-9_]+)\*$', inputStarStr)
        if match :
            prefix = match.group(1)
            result = [s for s in listStr if s.startswith(prefix)]
            return result
        else :
            return None
    @staticmethod
    def parse_star_meshname(meshname : str) -> list :
        retList = []

        if '*' in meshname :
            retList = [obj.name for obj in bpy.data.objects if obj.type == 'MESH']
            retList = CBlenderScriptUtil.parse_star_token(meshname, retList)
        else :
            retList.append(meshname)
        return retList
    @staticmethod
    def mesh_volume(obj) -> float :
        """
        Object Mode에서 mesh volume 계산
        열린 메쉬 / 퇴화 메쉬면 0에 가까운 값 반환
        """
        if obj.type != 'MESH':
            return 0.0
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        # triangulate 안 돼 있어도 calc_volume 가능
        volume = abs(bm.calc_volume())
        bm.free()
        return volume
    
    @staticmethod
    def _enable_add_on() :
    # kidney,stomach 공통
        bpy.ops.preferences.addon_enable(module='object_print3d_utils')  

    @staticmethod
    def delete_all_object() :
        for mesh in bpy.data.meshes :
            bpy.data.meshes.remove(mesh)
    @staticmethod
    def delete_etc_objects() :
        # Camera와 Light는 mesh가 아니므로 object로 검색해서 지워야함.
        objs = bpy.data.objects
        for obj in objs :
            if "Camera" in obj.name or "Light" in obj.name or "Cube" in obj.name :
                bpy.data.objects.remove(obj, do_unlink=True)
    @staticmethod
    def delete_object(meshname : str) :
        if meshname in bpy.data.objects:
            obj = bpy.data.objects[meshname]
            mesh_name = obj.data.name
            bpy.data.objects.remove(obj, do_unlink=True)
            print(f"Delete obj: '{meshname}'")
                    
            if mesh_name in bpy.data.meshes :
                mesh = bpy.data.meshes[mesh_name]
                bpy.data.meshes.remove(mesh)
                print(f"Delete mesh data: '{mesh_name}'") 
    @staticmethod
    def import_stl(stlFullPath : str) :
        if os.path.exists(stlFullPath) == False :
            print(f"failed import {stlFullPath}")
            return
        bpy.ops.import_mesh.stl(filepath=f"{stlFullPath}")
        print(f"imported {stlFullPath}")
    @staticmethod
    def import_obj(objFullPath : str) :
        if os.path.exists(objFullPath) == False :
            print(f"failed import {objFullPath}")
            return
        
        bpy.ops.import_scene.obj(filepath=f"{objFullPath}", axis_forward='Y', axis_up='Z')
        print(f"imported {objFullPath}")

        # import된 obj는 context에 추가됨
        obj = bpy.context.selected_objects[0]
        # Object 모드로 전환
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='OBJECT')
        mesh = obj.data

        # 기존 vertex normal 제거
        mesh.use_auto_smooth = False
        try:
            mesh.normals_split_custom_set_from_vertices([])
        except Exception:
            pass

        mesh.calc_normals()
        if mesh.uv_layers :
            mesh.calc_tangents()
    @staticmethod
    def _apply_all_transforms_and_shade_smooth() :
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

                # Shade Smooth 적용
                obj.data.use_auto_smooth = True  # Auto Smooth 활성화 (옵션)
                bpy.ops.object.shade_smooth()

                # 선택 해제
                obj.select_set(False)
    @staticmethod
    def triangulate_all_objects_no_ops():
        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue
            mesh = obj.data
            # bmesh로 변환
            bm = bmesh.new()
            bm.from_mesh(mesh)
            # Triangulate faces
            bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')

            # 결과를 메시에 다시 반영
            bm.to_mesh(mesh)
            bm.free()

            print(f"'{obj.name}' Triangulate Done.")
    @staticmethod
    def decimation_tri(meshname : str, targetTriCnt : int) :
        retListValidMeshName = CBlenderScriptUtil.parse_star_meshname(meshname)

        for meshname in retListValidMeshName :
            if meshname not in bpy.data.objects :
                print(f"skipped decimation : {meshname}")
                continue
            
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            # 해당 object에 대해서면 selection을 on 시킨다.
            obj = bpy.data.objects[meshname]
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            
            srcTriangleCnt = len(obj.data.polygons)
            decimationRatio = targetTriCnt / srcTriangleCnt

            # decimation을 수행한다. 
            decimate_modifier = obj.modifiers.new(name="DecimateMod", type='DECIMATE')
            decimate_modifier.ratio = decimationRatio
            
            # blender v3.6~4.1.1 까지 호환되는 함수
            bpy.ops.object.modifier_apply(modifier=decimate_modifier.name, single_user=True) 
            print(f"succeeded decimation : {meshname} : {targetTriCnt} : {decimationRatio}")
    @staticmethod
    def decimation_ratio(meshname : str, ratio : int) :
        retListValidMeshName = CBlenderScriptUtil.parse_star_meshname(meshname)

        for meshname in retListValidMeshName :
            if meshname not in bpy.data.objects :
                print(f"skipped decimation ratio : {meshname}")
                continue
            
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            # 해당 object에 대해서면 selection을 on 시킨다.
            obj = bpy.data.objects[meshname]
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

            decimationRatio = ratio / 100.0

            # decimation을 수행한다. 
            decimate_modifier = obj.modifiers.new(name="DecimateMod", type='DECIMATE')
            decimate_modifier.ratio = decimationRatio
            
            # blender v3.6~4.1.1 까지 호환되는 함수
            bpy.ops.object.modifier_apply(modifier=decimate_modifier.name, single_user=True) 
            print(f"succeeded decimation ratio : {meshname} : {decimationRatio}")
    @staticmethod
    def remesh(meshname : str, voxelSize : float, targetFaceCnt : int) :
        retListValidMeshName = CBlenderScriptUtil.parse_star_meshname(meshname)

        for meshname in retListValidMeshName :
            if meshname not in bpy.data.objects :
                print(f"skipped remesh : {meshname}")
                continue
            
            bpy.ops.object.select_all(action='DESELECT')
            obj = bpy.data.objects[meshname]
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            # voxel remesh
            bpy.context.object.data.remesh_voxel_size = voxelSize
            bpy.ops.object.voxel_remesh()
            # quadric remesh
            bpy.context.object.data.remesh_mode = 'QUAD'
            bpy.ops.object.quadriflow_remesh(target_faces=int(targetFaceCnt / 2))
            bpy.ops.object.select_all(action='DESELECT')

            print(f"succeeded remesh : {meshname}")
    @staticmethod
    def cleanup(meshname : str) :
        retListValidMeshName = CBlenderScriptUtil.parse_star_meshname(meshname)

        for meshname in retListValidMeshName :
            if meshname not in bpy.data.objects :
                print(f"skipped cleanup : {meshname}")
                continue
            
            ret = False 
            for cnt in range(0, 10) :
                if bpy.context.mode == 'EDIT_MESH':
                    bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.select_all(action='SELECT')

                if ret == False :
                    clmsh.clean_up_mesh(meshname)
                    meshErrStatus = clmsh.log_mesh_errors(meshname)
                    # [vol, vert, face, nm_len, i_f_len, zf_len, ze_len, nf_len]
                    if meshErrStatus[3] == 0 and meshErrStatus[4] == 0 and meshErrStatus[5] == 0 and meshErrStatus[7] == 0 :
                        ret = True
            
            print(f"succeeded cleanup : {meshname}")
    @staticmethod
    def smartuv(meshname : str) :
        retListValidMeshName = CBlenderScriptUtil.parse_star_meshname(meshname)

        for meshname in retListValidMeshName :
            if meshname not in bpy.data.objects :
                print(f"skipped smartuv : {meshname}")
                continue

            if bpy.context.mode != 'OBJECT' :
                bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')

            obj = bpy.data.objects[meshname]
            if obj.type != 'MESH':
                print(f"skipped smartuv : {meshname}")
                continue
            
            vol = CBlenderScriptUtil.mesh_volume(obj)
            EPS = 1e-8 
            if vol < EPS:
                print(f"- skipped smartuv : {meshname} (volume = {vol})")
                continue
            
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.reveal()
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(scale_to_bounds=True)
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')

            print(f"succeeded smartuv : {meshname}")

    @staticmethod
    def triangulate_all() :
        for obj in bpy.data.objects :
            if obj.type != 'MESH' :
                continue
            mesh = obj.data
            # bmesh로 변환
            bm = bmesh.new()
            bm.from_mesh(mesh)
            # Triangulate faces
            bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')

            # 결과를 메시에 다시 반영
            bm.to_mesh(mesh)
            bm.free()

    @staticmethod
    def recalc_normal(objName : str, toInside=False) :
        if objName not in bpy.data.objects :
            print(f"recalc_normal() : {objName} is not in Mesh Objects. Skip.")
            return
        
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')
        
        obj = bpy.data.objects.get(objName)
        if obj and obj.type != 'MESH' :
            print(f"recalc_normal() : {objName} is not in Mesh Objects. Skip.")
            return
        
        # 오브젝트를 활성화하고 선택
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        # edit-mode set        
        bpy.ops.object.mode_set(mode='EDIT')
        # 모든 면 선택
        bpy.ops.mesh.select_all(action='SELECT')
        # 노멀을 Outside/Inside로 재계산
        bpy.ops.mesh.normals_make_consistent(inside=toInside)
        # 객체 모드로 돌아가기
        bpy.ops.object.mode_set(mode='OBJECT')
        print(f"succeeded recalc normal() : {objName}")
    @staticmethod
    def rotation_all_x(deg : float) :
        for obj in bpy.context.scene.objects:
            rotate_x = math.radians(deg)
            obj.rotation_euler.rotate_axis('X', rotate_x)
    @staticmethod
    def rotation_all_y(deg : float) :
        for obj in bpy.context.scene.objects:
            rotate_y = math.radians(deg)
            obj.rotation_euler.rotate_axis('Y', rotate_y)
    @staticmethod
    def rotation_all_z(deg : float) :
        for obj in bpy.context.scene.objects:
            rotate_z = math.radians(deg)
            obj.rotation_euler.rotate_axis('Z', rotate_z)

    @staticmethod
    def match_mesh_data_name() :
        bpy.ops.object.select_all(action='DESELECT')
        objs = bpy.data.objects
        for obj in objs :
            obj = bpy.data.objects[obj.name]
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            obj.data.name = obj.name
        print("checked match mesh data name")
    @staticmethod
    def rename_mesh(objname : str, renamed : str) :
        if objname in bpy.data.objects :
            bpy.ops.object.select_all(action='DESELECT')
            obj = bpy.data.objects[objname]
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            obj.data.name = renamed
            obj.name = renamed
            print(f"renamed {objname} -> {renamed}")
    @staticmethod
    def join_objects(meshnameToken : str, joinedName : str) :
        ## keyword가 들어있는 object들을 join하여 keyword 이름으로 생성.
        # 모든 오브젝트 선택 해제
        bpy.ops.object.select_all(action='DESELECT')
        # keyword(=Cyst) 가 들어가는 object를 리스트에 저장
        objects_to_join = [obj for obj in bpy.context.scene.objects if meshnameToken in obj.name]
        if len(objects_to_join) >= 2 :
                
            bpy.context.view_layer.objects.active = objects_to_join[0]
            for obj in objects_to_join:
                obj.select_set(True)
            bpy.ops.object.join()
            
            joined_obj = bpy.context.active_object
            joined_obj.name = joinedName
            joined_obj.data.name = joinedName
        elif len(objects_to_join) == 1 : 
            objects_to_join[0].name = joinedName
            objects_to_join[0].data.name = joinedName
        else :
            print("join_objects() : No cyst objects available to join. Skip")
    
    @staticmethod
    def save_blender() :
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.wm.save_mainfile()
        bpy.ops.object.select_all(action='DESELECT')
        print(f"Saved current blend file")
    @staticmethod
    def save_as_blender(blenderFullPath : str) :
        if os.path.exists(blenderFullPath) :
            os.remove(blenderFullPath)
            
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.wm.save_as_mainfile(filepath=blenderFullPath)
        bpy.ops.object.select_all(action='DESELECT')
        print(f"Save Path : {blenderFullPath}")


    def __init__(self) :
        pass
    def clear(self) :
        pass



class COptionInfo :
    @staticmethod
    def parse_dictionary_type(outputDic : dict, srcDict : dict) :
        for key, value in srcDict.items() :
            listRet = CBlenderScriptUtil.parse_array_token(key)
            if listRet is None :
                outputDic[key] = value
            else :
                for subKey in listRet :
                    outputDic[subKey] = value
    @staticmethod
    def parse_list_type(outList : list, srcList : list) :
        for key in srcList :
            listRet = CBlenderScriptUtil.parse_array_token(key)
            if listRet is None :
                outList.append(key)
            else :
                for subKey in listRet :
                    outList.append(subKey)


    def __init__(self) :
        self.m_jsonData = None
        self.m_dataRootPath = ""
        self.m_dicDecimation = {}
        self.m_dicDecimationByRatio = {}
        self.m_dicRemesh = {}
        self.m_listMeshCleanup = []
        self.m_listSamrtUV = []
    def process(self, fullPath : str) -> bool :
        if os.path.exists(fullPath) == False :
            print(f"not valid Option_Path : {fullPath}")
            return False
        # json initialize 
        with open(fullPath, 'r') as fp :
            self.m_jsonData = json.load(fp)
        
        self.m_dataRootPath = self.m_jsonData["DataRootPath"]

        if self._exist_blender_key("Decimation") == True :
            COptionInfo.parse_dictionary_type(self.m_dicDecimation, self._get_blender_value("Decimation"))
        if self._exist_blender_key("DecimationByRatio") == True :
            COptionInfo.parse_dictionary_type(self.m_dicDecimationByRatio, self._get_blender_value("DecimationByRatio"))
        if self._exist_blender_key("Remesh") == True :
            COptionInfo.parse_dictionary_type(self.m_dicRemesh, self._get_blender_value("Remesh"))
        
        if self._exist_blender_key("MeshCleanUp") == True :
            COptionInfo.parse_list_type(self.m_listMeshCleanup, self._get_blender_value("MeshCleanUp"))
        if self._exist_blender_key("SmartUV") == True :
            COptionInfo.parse_list_type(self.m_listSamrtUV, self._get_blender_value("SmartUV"))
        
        return True
    
    def exist_meshname_decimation(self, meshname : str) -> bool :
        if meshname in self.m_dicDecimation :
            return True
        return False
    def get_list_decimation_meshname(self) -> list :
        return list(self.m_dicDecimation.keys())
    def get_decimation(self, meshname : str) -> int :
        return self.m_dicDecimation[meshname]
    
    def exist_meshname_decimation_ratio(self, meshname : str) -> bool :
        if meshname in self.m_dicDecimationByRatio :
            return True
        return False
    def get_list_decimation_ratio_meshname(self) -> list :
        return list(self.m_dicDecimationByRatio.keys())
    def get_decimation_ratio(self, meshname : str) -> int :
        return self.m_dicDecimationByRatio[meshname]
    
    def exist_meshname_remesh(self, meshname : str) -> bool :
        if meshname in self.m_dicRemesh :
            return True
        return False
    def get_list_remesh_meshname(self) -> list :
        return list(self.m_dicRemesh.keys())
    def get_remesh_voxel(self, meshname : str) -> int :
        return self.m_dicRemesh[meshname][0]
    
    def get_remesh_voxel_facecnt(self, meshname : str) -> int :
        return self.m_dicRemesh[meshname][1]
    
    def exist_meshname_cleanup(self, meshname : str) -> bool :
        if meshname in self.m_listMeshCleanup :
            return True
        return False
    def get_cleanup_meshname_count(self) -> int :
        return len(self.m_listMeshCleanup)
    def get_cleanup_meshname(self, inx : int) -> str :
        return self.m_listMeshCleanup[inx]
    
    def exist_meshname_smartuv(self, meshname : str) -> bool :
        if meshname in self.m_listSamrtUV :
            return True
        return False
    def get_smartuv_meshname_count(self) -> int :
        return len(self.m_listSamrtUV)
    def get_smartuv_meshname(self, inx : int) -> str :
        return self.m_listSamrtUV[inx]
    
    # user key-value 
    def get_user_value(self, key : str) :
        if key in self.m_jsonData :
            return self.m_jsonData[key]
        else :
            return None

    # protected
    def _exist_blender_key(self, blenderKey : str) -> bool :
        if blenderKey in self.m_jsonData["Blender"] :
            return True
        return False
    def _get_blender_value(self, blenderKey : str) : 
        return self.m_jsonData["Blender"][blenderKey]
    

    @property
    def DataRootPath(self) -> str :
        return self.m_dataRootPath
    
    


class CBlenderScriptBase :
    def __init__(self, optionFullPath : str) :
        self.m_bReady = False
        self.m_optionPath = optionFullPath
        self.m_optionInfo = COptionInfo()
        self.m_bReady = self.m_optionInfo.process(self.m_optionPath)
    def clear(self) :
        self.m_bReady = False
        self.m_optionPath = ""
        self.m_optionInfo = None


    @property
    def Ready(self) -> bool :
        return self.m_bReady
    @property
    def OptionInfo(self) -> COptionInfo :
        return self.m_optionInfo

