'''
blenderScriptKidney.py
Latest : 25.07.10
'''
import bpy
import csv
import os, sys
import json
import re
import shutil
import math
import time
import bmesh
from mathutils import Vector

tmpPath = os.path.abspath(os.path.dirname(__file__))
sys.path.append(tmpPath)

import blenderScriptCleanUpMesh as clmsh
import blenderScriptUVUtils as projectuv

class COptionInfo :
    @staticmethod
    def generate_strings(input_str) :
        # 정규식을 사용하여 숫자 범위와 문자 부분 추출
        match = re.search(r'([a-zA-Z0-9_]+)\[(\d+),(\d+)\]', input_str)
        if match:
            prefix = match.group(1)  # 문자 부분 추출
            start = int(match.group(2))  # 시작 숫자
            end = int(match.group(3))    # 끝 숫자
            
            # 숫자 범위에 따른 문자열 생성
            result = [f"{prefix}{num}" for num in range(start, end + 1)]
            return result
        else:
            return None
        

    def __init__(self):
        self.m_jsonData = None
        self.m_dataRootPath = ""
        self.m_dicDecimation = {}
        self.m_dicDecimationByRatio = {}
        self.m_dicRemesh = {}
        self.m_listMeshCleanup = []
        self.m_listMeshHealing = []
        self.m_listSamrtUV = []
        self.m_listProjectUV = []
        
    def process(self, fullPath : str) -> bool :
        if os.path.exists(fullPath) == False: 
            print(f"not valid Option_Path : {fullPath}")
            return False
        # json initialize 
        with open(fullPath, 'r') as fp :
            self.m_jsonData = json.load(fp)

        self.m_dataRootPath = self.m_jsonData["DataRootPath"]
        self.m_decimation = self.m_jsonData["Blender"]["Decimation"]
        self.m_decimationByRatio = self.m_jsonData["Blender"]["DecimationByRatio"]
        self.m_remesh = self.m_jsonData["Blender"]["Remesh"]
        self.m_meshCleanup = self.m_jsonData["Blender"]["MeshCleanUp"]
        self.m_meshHealing = self.m_jsonData["Blender"]["MeshHealing"]
        self.m_smartUV = self.m_jsonData["Blender"]["SmartUV"]
        self.m_projectUV = self.m_jsonData["Blender"]["ProjectUV"]
        self.m_centerlineInfo = self.m_jsonData["CenterlineInfo"]
        self.m_voxelSize = self.m_remesh["VoxelSize"]
        self.m_remeshList = self.m_remesh["RemeshList"]
        self.m_separateList = self.m_jsonData["Blender"]["SeparatedSTLNameList"]

        return True
    
    @property
    def DataRootPath(self) -> str :
        return self.m_dataRootPath
    @property
    def Decimation(self) -> dict :
        return self.m_decimation
    @property
    def DecimationByRatio(self) -> dict :
        return self.m_decimationByRatio
    @property
    def CleanUp(self) -> list :
        return self.m_meshCleanup
    @property
    def Healing(self) -> list :
        return self.m_meshHealing
    @property
    def SmartUV(self) -> list :
        return self.m_smartUV
    @property
    def ProjectUV(self) -> list :
        return self.m_projectUV
    @property
    def CenterlineInfo(self) -> list :
        return self.m_centerlineInfo
    @property
    def VoxelSize(self) :
        return self.m_voxelSize
    @property
    def Remesh(self):
        return self.m_remeshList
    @property
    def Separate(self) -> list:
        return self.m_separateList
    
class CBlenderScriptKidney :
    @staticmethod    
    def __get_decimation_ratio(srcVerticesCnt : int, targetVerticesCnt : int) :
        return targetVerticesCnt / srcVerticesCnt
    @staticmethod
    def list_objects_in_blend(blend_path):
        with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
            return data_from.objects  # object name 리스트 반환
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

    def __init__(self, patientID : str, stlPath : str, saveAs = "", newFlag = True, triOpt = True) -> None :
        #self.m_optionPath = os.path.join(tmpPath, "option.json")
        self.m_optionPath = os.path.join("option.json") #sally
        
        self.m_patientID = patientID
        self.m_stlPath = stlPath
        self.m_new = newFlag
        self.m_triOpt = triOpt
        self.m_outputRootPath = ""
        self.m_outputPatientPath = ""
        # self.m_patientIdBlendPath = ""
        self.m_auto01Path = ""
        self.m_auto02Path = ""
        self.m_auto03Path = ""

        self.m_optionInfo = COptionInfo()
        self.m_saveAs = saveAs

        self.m_listStlName = []
        self.m_listStlNameCleanUp = []
    def process(self) -> bool:
        if self.m_optionInfo.process(self.m_optionPath) == False :
            return False        
        # dataRootName = os.path.basename(self.m_optionInfo.DataRootPath)
        # output path
        # self.m_outputRootPath = os.path.join(tmpPath, dataRootName)
        self.m_outputPatientPath = os.path.dirname(self.m_stlPath) # OutTemp/patientid/ 의 full path
        # self.m_patientIdBlendPath = os.path.join(self.m_outputPatientPath, f"{self.m_patientID}.blend") # patienID.blend 의 path
        saveFolder = self.m_saveAs #os.path.join(self.m_optionInfo.DataRootPath, self.m_patientID, "02_SAVE", "02_BLENDER_SAVE")
        self.m_auto01Path = os.path.join(saveFolder, "Auto01_Recon")
        self.m_auto02Path = os.path.join(saveFolder, "Auto02_Overlap")
        self.m_auto03Path = os.path.join(saveFolder, "Auto03_Separate_Cleanup")        
        
        print(f"StlPath : {self.m_stlPath}")
        print(f"SaveFolder : {saveFolder}")
        # print(f"outputRootPath : {self.m_outputRootPath}")
        # print(f"blenderFullPath(OutTemp) : {self.m_patientIdBlendPath}")
        print(f"outputPatientPath : {self.m_outputPatientPath}")
        
    
        return True
    
    def _enable_add_on(self) :
        # kidney,stomach 공통
        bpy.ops.preferences.addon_enable(module='object_print3d_utils')  
          
    def _get_all_object_list(self) -> list :
        mesh_objects = [obj.name for obj in bpy.data.objects if obj.type == 'MESH']
        return mesh_objects
    def _get_valid_object_list(self, in_list : list) -> list:
        # 꽃표 들어간 목록까지 다 비교해서 실제 적용할 object목록을 리턴한다.
        mesh_objects = [obj.name for obj in bpy.data.objects if obj.type == 'MESH']
        flattened = []
        print(f"mesh_objects : {mesh_objects}")
        valid_list = []
        for stlname in in_list : 
            validname = stlname
            if '*' in stlname :
                validname = stlname.replace("*", "")
            filtered = [s for s in mesh_objects if validname in s]
            valid_list.append(filtered)
            flattened = [item for sublist in valid_list for item in sublist]
        
        resultlist = list(set(flattened))
        print(f"valid_list : {resultlist}")    
        return resultlist
    def _get_valid_object_dict(self, in_dict : dict) -> dict:
        # 꽃표 들어간 목록까지 다 비교해서 실제 적용할 object목록을 factor와 함께 리턴한다.
        mesh_objects = [obj.name for obj in bpy.data.objects if obj.type == 'MESH']
        valid_dict = {}
        for stlname, factor in in_dict.items() : 
            validname = stlname
            if '*' in stlname :
                validname = stlname.replace("*", "")
                filtered = [s for s in mesh_objects if validname in s]

                for validname in filtered :
                    valid_dict[validname] = factor
            else :
                valid_dict[validname] = factor
        print(f"valid_dict : {valid_dict}")    
        return valid_dict
    def _delete_all_object(self) :
        self.m_listStlName = []
        # bpy.ops.object.select_all(action="SELECT")
        # bpy.ops.object.delete()
        
        # Cube 의 mesh 및 기타 mesh잔여물들을 없애기 위해 아래 코드 추가.(0724)
        # kidney,stomach 공통
        for mesh in bpy.data.meshes :
            bpy.data.meshes.remove(mesh)   
    def _delete_etc_objects(self) :
        # for mesh in bpy.data.meshes :
        #     if mesh.name == "Camera" or mesh.name == "Light" or mesh.name == "Cube":
        #         bpy.data.meshes.remove(mesh) 
        # Camera와 Light는 mesh가 아니므로 object로 검색해서 지워야함.
        objs = bpy.data.objects
        for obj in objs :
            if "Camera" in obj.name or "Light" in obj.name or "Cube" in obj.name :
                bpy.data.objects.remove(obj, do_unlink=True)
                
    def _import_stl(self, path : str) -> bool : 
        if not os.path.exists(path) :
            print(f"Not found stl path({path}). Return.")
            return False
        listStlName = os.listdir(path)
        if len(listStlName) == 0 :
            print("Not found stl files. Return.")
            return False
        
        for stlName in listStlName :
            if stlName == ".DS_Store" : 
                continue
            
            stlNameExceptExt = stlName.split('.')[0]
            
            ext = stlName.split('.')[-1]
            if ext != "stl" :
                 continue
            stlFullPath = os.path.join(path, stlName)
            if os.path.isdir(stlFullPath) == True :
                continue

            self.m_listStlName.append(stlNameExceptExt)
            
            # kidney,stomach 공통
            if (4,1,0) < bpy.app.version : 
                bpy.ops.wm.stl_import(filepath=f"{stlFullPath}")
            else :
                bpy.ops.import_mesh.stl(filepath=f"{stlFullPath}")

            print(f"imported {stlFullPath}")
        
        return True
    def _import_other_blend_objs(self, blenderPath : str) -> bool :
        ## 현재 .blend 에 다른 .blend의 오브젝트를 import한다. 중복되는 object는 삭제 후 다른 .blend의 object로 대체함.
        if not os.path.exists(blenderPath):
            print(f"Not Found : {blenderPath}")
            return False
        # 1. blend_path의 모든 오브젝트의 이름을 가져오기
        object_names = CBlenderScriptKidney.list_objects_in_blend(blenderPath)
            
        # 2. 중복 오브젝트가 있다면 현재 .blend에서 삭제
        for mesh in bpy.data.meshes :
            for name in object_names:         
                if mesh.name == name :
                    bpy.data.meshes.remove(mesh)
                    break

        # 3. blend_path 에서 object 불러오기
        with bpy.data.libraries.load(blenderPath, link=False) as (data_from, data_to):
            available = data_from.objects
            to_load = [name for name in object_names if name in available]
            data_to.objects = to_load
        
        # 4. import한 object들이 Collection바깥에 있을수도 있으므로 Collection 안으로 옮기는(연결하는) 코드임
        # Collection을 찾거나 없으면 새로 생성
        collection_name = "Collection"
        target_collection = bpy.data.collections.get(collection_name)
        if not target_collection:
            target_collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(target_collection)
        # 가져온 오브젝트들을 Collection에 추가
        for obj in data_to.objects:
            if obj is not None:
                # bpy.context.scene.collection.objects.link(obj)  # 씬에 연결
                target_collection.objects.link(obj)             # 컬렉션에도 연결
                print(f"Imported: {obj.name} to Collection: {collection_name}")
        return True
    def _import_other_blend_objs_as(self, blenderPath : str) -> bool :
        ## 현재 .blend 에 다른 .blend의 오브젝트를 import한다. 중복되는 object는 넘버링되어 import됨.
        # 1. 불러올 blend 파일 경로
        selected_blend_path = blenderPath
        # 2. 파일이 존재하는지 확인
        if not os.path.exists(selected_blend_path):
            print("Error - Not Exist :", selected_blend_path)
            return False
        
        # 3. 블렌드 파일 내의 오브젝트 리스트 확인
        with bpy.data.libraries.load(selected_blend_path, link=False) as (data_from, data_to):
            print("가져올 오브젝트들:", data_from.objects)            
            data_to.objects = data_from.objects  # 모든 오브젝트 가져오기
        
            
        # 4. import한 object들이 Collection바깥에 있을수도 있으므로 Collection 안으로 옮기는(연결하는) 코드임
        # Collection을 찾거나 없으면 새로 생성
        collection_name = "Collection"
        target_collection = bpy.data.collections.get(collection_name)
        if not target_collection:
            target_collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(target_collection)
        # 가져온 오브젝트들을 Collection에 추가
        for obj in data_to.objects:
            if obj is not None:
                # bpy.context.scene.collection.objects.link(obj)  # 씬에 연결
                target_collection.objects.link(obj)             # 컬렉션에도 연결
                print(f"Imported: {obj.name} to Collection: {collection_name}")
        return True
    def _init_cleanup(self, listCleanup : list) :
        self.m_listStlNameCleanUp.clear()
        for cleanupName in listCleanup :
            if cleanupName in bpy.data.objects :
                self.m_listStlNameCleanUp.append([cleanupName, 0])
                print(f"CleanUp Name : {cleanupName}")
        # def _switch_to_collection(self) :
    #     context = bpy.context
    #     layer = context.view_layer
    #     scene_collection = context.layer_collection.collection
    #     objects = scene_collection.objects # 이 코드를 아래 코드로 수정.
    #     # objects = bpy.data.objects

    #     for object in objects:
    #         print("-----", object.name)
    #     # print(objects[0].name)
    #     if len(objects) > 0 :
    #         bpy.ops.object.select_all(action='DESELECT')
    #         obj = bpy.data.objects[objects[0].name]
    #         obj.select_set(True)
    #         bpy.context.view_layer.objects.active = obj

    #         layer.update()
    #     print("_switch_to_collection done")
    def _decimation(self, dicDeci : dict, bRatio : bool) : #sally 250408 updated
        # 아래 루틴은 background 모드에서 돌아야 에러가 안남.
        if bRatio :
            mode = "Ratio"
        else : 
            mode = "Fixed"
        
        result_list = []        
        for deciName, triValue in dicDeci.items() : 
            # bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
            bpy.ops.object.select_all(action='DESELECT')

            if deciName in bpy.data.objects :
                obj = bpy.data.objects[deciName]
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                srcTriangleCnt = len(obj.data.polygons)
                targetTriangleCnt = 0
                if bRatio == False :
                    # targetVertexCnt = triValue
                    # srcVertexCnt =len(bpy.context.active_object.data.vertices)
                    # decimationRatio = self.__get_decimation_ratio(srcVertexCnt, targetVertexCnt / 2)
                    # triangle 개수를 읽어와서 그 기준으로 계산하도록 변경 - sally
                    targetTriangleCnt = triValue                    
                    decimationRatio = targetTriangleCnt / srcTriangleCnt
                    if decimationRatio == 1.0 :
                        print(f"- Decimation : {deciName} Skipped. (dedimationRatio=1.0)")

                        result_list.append([deciName, srcTriangleCnt, targetTriangleCnt, srcTriangleCnt, "0.0", "OK"])
                        continue
                else :
                    decimationRatio = triValue / 100.0
                    targetTriangleCnt = srcTriangleCnt * triValue
                
                decimate_modifier = obj.modifiers.new(name="Decimate", type='DECIMATE')
                if decimate_modifier:
                    decimate_modifier.ratio = decimationRatio
                    bpy.ops.object.modifier_apply(modifier=decimate_modifier.name, single_user=True)
                    dstTriangleCnt = len(obj.data.polygons)
                    print(f"- Decimation : {deciName} Applied. (Triangles : ({srcTriangleCnt}) -> ({dstTriangleCnt}))")
                    diff = abs(targetTriangleCnt - dstTriangleCnt)
                    diff_ratio = diff * 100.0 / targetTriangleCnt
                    result = "OK"
                    if diff_ratio > 5.0 : 
                        result = "FAIL"
                    result_list.append([deciName, srcTriangleCnt, targetTriangleCnt, dstTriangleCnt, diff_ratio, result])
                else:
                    print(f"- Decimation : {deciName} ERROR : decimate_modifier.new() Fail.")
               
        print(f"Decimation({mode}) All Done.")
        return result_list

    def _remesh(self, dicRemesh : dict) :
        voxelSize = self.m_optionInfo.VoxelSize
        for remeshName, triCnt in dicRemesh.items() :
            if remeshName in bpy.data.objects :
                self.__remesh_stl(remeshName, voxelSize, triCnt)
                print(f"remeshed {remeshName} : {triCnt}")
        print("passed remesh")
    def _rename_mesh(self) :
        bpy.ops.object.select_all(action='DESELECT')
        objs = bpy.data.objects
        for obj in objs :
            obj = bpy.data.objects[obj.name]
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            obj.data.name = obj.name
        print("passed rename_mesh")
    def _cleanup(self) :
        count = sum(1 for item in self.m_listStlNameCleanUp if item[1] == 0)
        #cnt = 0
        print(f"mesh clean cnt : {count}")
        for cnt in range(0, 10) :
        #while count > 0 :
            self.__clean_up_mesh(self.m_listStlNameCleanUp) 
            #print(f"mesh clean step : {cnt}, {count}")
            #count = sum(1 for item in self.m_listStlNameCleanUp if item[1] == 0)
            #cnt += 1
        print("Mesh-Clean All Done. ")
    def _healing(self, listHealing : list) :
        for healingName in listHealing :
            if healingName in bpy.data.objects :
                bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.select_all(action='DESELECT')
                # input healing code
                print(f"mesh healing : {healingName}")
        print("passed mesh healing")
    def _smartUV(self, listSmartUV : list) :
        bpy.ops.object.select_all(action='DESELECT')
        for smartUVName in listSmartUV :
            if smartUVName in bpy.data.objects :                
                obj = bpy.data.objects[smartUVName]
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj

                bpy.ops.object.editmode_toggle()
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.uv.smart_project(scale_to_bounds=True)
                bpy.ops.mesh.select_all(action='DESELECT')
                bpy.ops.object.editmode_toggle()
                bpy.ops.object.select_all(action='DESELECT')
                print(f"- SmartUV : {smartUVName} processed.")
        print("SmartUV All Done.")
    def _projectUV(self, listProjectUV : list, view_axis="FRONT") :
        for objname in listProjectUV :
            projectuv.project_from_view_bounds(objname, view_axis)
    def _shade_auto_smooth(self, objNameList : list, angle=30) :
        for objName in objNameList :
            radian = math.radians(angle)

            obj = bpy.data.objects.get(objName)
            if obj and obj.type == 'MESH':
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)

                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.shade_smooth()
                obj.data.use_auto_smooth = True
                obj.data.auto_smooth_angle = radian 
    # _shade_auto_smooth() 를 ops를 사용하지 않고 구현한 코드임. (.001이 생기는 문제가 있는듯함.)
    def _shade_auto_smooth_by_bmesh(self, objNameList : list, angle=30) : #TODO : 동작되는지 테스트해야함.
        smooth_angle_rad = math.radians(angle)

        for objName in objNameList :
            obj = bpy.data.objects.get(objName)
            if obj.type != "MESH" : 
                continue
            mesh = obj.data
            # shade smooth 설정 (vertex normals)
            for poly in mesh.polygons : 
                poly.use_smooth = True
            mesh.use_auto_smooth = True
            mesh.auto_smooth_angle = smooth_angle_rad

            # Clear Sharp (마크된 Sharp 엣지 제거)
            # 메쉬가 이미 편집 상태가 아니라면 편집용 BMesh로 로드
            bm = bmesh.new()
            bm.from_mesh(mesh)

            for edge in bm.edges:
                edge.smooth = True  # Sharp 마크 제거

            # BMesh 내용을 원래 메시에 반영하고 종료
            bm.to_mesh(mesh)
            bm.free()
                    
    def _recalc_normal(self, objNameList : list, toInside=False) :
        namelist = []
        objs = bpy.data.objects
        for obj in objs : 
            namelist.append(obj.name)

        for objName in objNameList :
            if objName in namelist:
                if bpy.ops.object.mode_set.poll():
                    bpy.ops.object.mode_set(mode='OBJECT')

                obj = bpy.data.objects.get(objName)

                if obj and obj.type == 'MESH':
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
            else :
                print(f"_recalc_normal() : {objName} is not in Mesh Objects. Skip.")

    def _save_blender_with_patientID(self, outputPath : str, saveAs : str) :
        blenderPath = os.path.join(outputPath)
        blenderFullPath = os.path.join(blenderPath, saveAs)
        if os.path.exists(blenderFullPath):
            os.remove(blenderFullPath)
            
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.wm.save_as_mainfile(filepath=blenderFullPath)
        bpy.ops.object.select_all(action='DESELECT')
        print(f"Save Path : {blenderFullPath}")
        
    def _save_blender_with_bak(self, savePath, baseName) :
        ## 기존 파일은 _old(n) 를 붙여 백업 후 원본 이름으로 최신내용을 저장함.
        savePathFull = os.path.join(savePath, f"{baseName}.blend")
        if os.path.exists(savePathFull) :
            base_bak_name = f"{baseName}_old"
            new_bak_name = self._get_blendfilename_for_save_as(savePath, base_bak_name)  # ex) "path/to/huid_old(2).blend"
            new_bak_full_path = os.path.join(savePath, new_bak_name)
            print(f"new_bak_full_path : {new_bak_full_path}")
            os.rename(savePathFull, new_bak_full_path)
        
        # 최신파일 저장 
        blender_full_name = f"{baseName}.blend"
        self._save_blender_with_patientID(savePath, blender_full_name)
        
    def _get_blendfilename_for_save_as(self, in_blenderPath, in_basename) :
        #중복 파일 존재시 넘버링하여 저장.
        #Lung에서는 PatientID(#).blend or PatientID_Terri(#).blend 를 사용.
        newName = in_basename
        listBlendName = os.listdir(in_blenderPath)
        max_no = 0
        num_of_blend = 0
        curr_no = 0
        for name in listBlendName:
            filename,ext = os.path.splitext(name)            
            if ext == '.blend':                                      
                if in_basename in name: #in_basename 가 파일명에 있나?(기존에 저장돼 있는 .blend가 있나)
                    num_of_blend = num_of_blend + 1
                    valid_str = filename.replace(in_basename, "")
                    # sp1 = filename
                    # if in_mode == "Territory" :
                    #     #파일명에서 _Terri 에 붙은 넘버를 찾기. 없으면 0
                    #     sp1 = filename.split('_')[-1]
                    digit = self._extract_numbers2(valid_str)
                    if digit.isdigit() :
                        curr_no = int(digit)
                    if max_no < curr_no: #기존파일들중 최고 넘버를 찾기
                        max_no = curr_no

        if num_of_blend == 0:
            newName = in_basename
        else:
            newName = f"{in_basename}({max_no+1})"

        return f"{newName}.blend"    
    def _find_lowercase(self, string) -> str:
        # 소문자가 포함되었는지 여부와 첫 소문자를 반환
        lowercase_letters = [char for char in string if char.islower()]
        # print(f"lowercase_letters : {lowercase_letters}")
        contains_lowercase = bool(lowercase_letters)
        if contains_lowercase :
            return f"{lowercase_letters[0]}"
        else :
            return ""
    def _find_lowercase_with_underbar(self, string) -> str:
        # 소문자가 포함되었으면 첫 소문자를 언더바와 함께 리턴
        lowercase_letters = [char for char in string if char.islower()]
        contains_lowercase = bool(lowercase_letters)
        if contains_lowercase :
            return f"_{lowercase_letters[0]}"
        else :
            return ""
        # return contains_lowercase, lowercase_letters
    def _create_sphere(self, inRadius, objName) :
        # remove an existing object
        obj = bpy.data.objects.get(objName)
        rmmesh = bpy.data.meshes.get(objName)
        if obj :
            bpy.data.objects.remove(obj, do_unlink=True)
        if rmmesh : 
            bpy.data.meshes.remove(rmmesh) 
            
        # Sphere 생성
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=inRadius,  
            location=(0, 0, 0) 
        )

        sphere = bpy.data.objects.get("Sphere") #bpy.context.active_object
        sphere.name = objName
        sphere.data.name = objName

        # Scene Collection에 생성되었다면 제거
        if sphere.name in bpy.context.scene.collection.objects:
            print("*** unusual case")
            bpy.context.scene.collection.objects.unlink(sphere)
        
        # Collection에 연결하기
        collection_name = "Collection"
        target_collection = bpy.data.collections.get(collection_name)
        if sphere.name not in target_collection.objects:
            print("*** unusual case")
            target_collection.objects.link(sphere)

        bpy.ops.object.select_all(action='DESELECT')        

    def _extract_numbers2(self, string):
        # 숫자인 문자만 필터링하여 리스트로 만들고, 이를 합침
        return ''.join(char for char in string if char.isdigit())


    def __remesh_stl(self, stlNameExceptExt : str, voxelSize : float, targetFaceCnt : int) :
        bpy.ops.object.select_all(action='DESELECT')
        obj = bpy.data.objects[stlNameExceptExt]
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        # voxel remesh
        bpy.context.object.data.remesh_voxel_size = voxelSize
        bpy.ops.object.voxel_remesh()
        # quadric remesh
        bpy.context.object.data.remesh_mode = 'QUAD'
        bpy.ops.object.quadriflow_remesh(target_faces=int(targetFaceCnt / 2))
        bpy.ops.object.select_all(action='DESELECT')
    def __clean_up_mesh(self, name_and_flag_list) :
        if bpy.context.mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='SELECT')
        
        for objinfo in name_and_flag_list :
            if objinfo[1] == 0: #해당 obj의 mesh error가 미해결 상태라면 clean-up 수행
                clmsh.clean_up_mesh(objinfo[0])
                meshErrStatus = clmsh.log_mesh_errors(objinfo[0])
                print(f"error : {meshErrStatus}")
                # [vol, vert, face, nm_len, i_f_len, zf_len, ze_len, nf_len]
                if meshErrStatus[3] == 0 and meshErrStatus[4] == 0 and meshErrStatus[5] == 0 and meshErrStatus[7] == 0 :
                    print(f"completed clean-up : {objinfo[0]}")
                    objinfo[1] = 1
    
    
class CBlenderScriptKidneyBasic(CBlenderScriptKidney) :
    def __init__(self, patientID : str, stlPath : str, saveAs = "" ) :
        super().__init__(patientID, stlPath, saveAs)    

    def process(self) -> bool :
        ## Reconstruction이 완료된 STL 파일의 decimation, Remesh 등을 수행한다.
        if super().process() == False :
            return False
        self._enable_add_on()
        self._delete_all_object()

        if self._import_stl(self.m_stlPath) == False : 
            print("failed import stl")
            return False

        # _get_valid_object_list() 를 이용하여 꽃표 들어간 목록까지 다 비교해서 실제 적용할 object목록을 얻어온다.
        # valid_clean_list = self._get_valid_object_list(self.m_optionInfo.CleanUp)
        valid_decim_dict = self._get_valid_object_dict(self.m_optionInfo.Decimation) 
        valid_decimRatio_dict = self._get_valid_object_dict(self.m_optionInfo.DecimationByRatio) 
        self._init_cleanup(self.m_optionInfo.Remesh.keys()) # remesh 할 organ들을 cleanup 하기 위함.
        self._decimation(valid_decim_dict, False)
        self._decimation(valid_decimRatio_dict, True)
        self._cleanup()
        self._remesh(self.m_optionInfo.Remesh) # remesh 후에 Aorta와 IVC는 mesh error가 생김. 최종 단계에서 cleanup을 해야함.
        # valid_smartuv_list = self._get_valid_object_list(self.m_optionInfo.SmartUV)
        # self._smartUV(valid_smartuv_list)
        
        self._rename_mesh()
        self._rename_one_mesh("Tumor_exo", "Tumor")
        self._rename_one_mesh("Tumor_endo", "Tumor")
        self._join_objects("Cyst")
        
        self._delete_etc_objects()
        
        # save
        # patientBlenderName = os.path.basename(self.m_patientIdBlendPath) #"patientID.blend"
        # self._save_blender_with_patientID(self.m_outputPatientPath, patientBlenderName)  #이름 그대로 저장.
        
        # DataRootPath의 해당 저장 폴더에 최종 파일 저장하기.
        # patientBlenderName = f"{self.m_patientID}.blend"
        # self._save_blender_with_patientID(self.m_auto01Path, patientBlenderName) 
        self._save_blender_with_bak(self.m_auto01Path, self.m_patientID)
        # bpy.ops.wm.quit_blender()
        return True
        
    def _join_objects(self, keyword):
        ## keyword가 들어있는 object들을 join하여 keyword 이름으로 생성.
        # 모든 오브젝트 선택 해제
        bpy.ops.object.select_all(action='DESELECT')
        # keyword(=Cyst) 가 들어가는 object를 리스트에 저장
        objects_to_join = [obj for obj in bpy.context.scene.objects if keyword in obj.name]
        if len(objects_to_join) >= 2 :
                
            bpy.context.view_layer.objects.active = objects_to_join[0]
            for obj in objects_to_join:
                obj.select_set(True)
            bpy.ops.object.join()
            
            joined_obj = bpy.context.active_object

            joined_obj.name = keyword
            joined_obj.data.name = keyword
        elif len(objects_to_join) == 1 : # Cyst 가 Cyst_exo 또는 Cyst_endo 하나인 경우 Cyst로 rename한다.
            objects_to_join[0].name = keyword
            objects_to_join[0].data.name = keyword
        else :
            print("join_objects() : No cyst objects available to join. Skip")
    
    def _rename_one_mesh(self, objname, renamed) :
        if objname in bpy.data.objects :
            bpy.ops.object.select_all(action='DESELECT')
            obj = bpy.data.objects[objname]
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            obj.data.name = renamed  #rename mesh data
            obj.name = renamed  #rename obj
            print(f"renamed {objname} -> {renamed}")
            
class CBlenderScriptKidneyExport(CBlenderScriptKidney) :
    def __init__(self, patientID : str, stlPath : str, saveAs = "" ) :
        super().__init__(patientID, stlPath, saveAs)    

    def process(self) -> bool :
        ## Auto01_Recon 의 .blend 의 object들을 stl export한다.
        if super().process() == False :
            return False
        
        patientBlenderName = os.path.join(self.m_auto01Path, f"{self.m_patientID}.blend")
        bpy.ops.wm.open_mainfile(filepath=patientBlenderName) 
        export_path = os.path.join(self.m_outputPatientPath, "ExportStl")
        self._do_export(export_path)
        bpy.ops.wm.quit_blender()
        
        return True
    
    def _export_stl2(self, out_path) :
        # selection = bpy.context.selected_objects
        objects = bpy.data.objects
        # Export each object.
        for object in objects:
            if object.type != 'MESH':
                continue
            bpy.ops.object.select_all(action='DESELECT')
            obj = bpy.data.objects[object.name]
            object.select_set(True)
            bpy.context.view_layer.objects.active = object
            print('Exporting {}'.format(object.name))
            fpath = os.path.join(out_path, f"{object.name}.stl")
            bpy.ops.export_mesh.stl(filepath=fpath,
                                use_selection=True)
        # Reset the selection to original.
        bpy.ops.object.select_all(action='DESELECT')
        
    def _do_export(self, out_path) :
        print(f"export out_path = {out_path}")
        if not os.path.exists(out_path) :
            # print(f"export_stl-ERROR) - Not found STL Path : {out_path}")
            os.makedirs(out_path)
        else :
            filelist = os.listdir(out_path)
            for ff in filelist:
                ext = os.path.splitext(ff)[1] 
                if ext == '.stl':
                    fullpath = os.path.join(out_path, ff)
                    os.remove(fullpath)
                    print(f"removed {ff}")
            
        # _export_stl(out_path) # for blender v4.1.1
        self._export_stl2(out_path) # for blender v3.6 ~ v4.1.1
        
class CBlenderScriptKidneyImportSave(CBlenderScriptKidney) :
    def __init__(self, patientID : str, stlPath : str, saveAs = "" ) :
        super().__init__(patientID, stlPath, saveAs)    

    def process(self) -> bool :
        if super().process() == False :
            return False
        
        self._delete_all_object()
        self._delete_etc_objects()
        
        if self._import_stl(self.m_stlPath) == False :
            print("failed import stl")
            return False
        
        # DataRootPath의 해당 저장 폴더에 최종 파일 저장하기.
        # patientBlenderName = f"{self.m_patientID}.blend"
        # self._save_blender_with_patientID(self.m_auto02Path, patientBlenderName) 
        self._save_blender_with_bak(self.m_auto02Path, self.m_patientID)
        # bpy.ops.wm.quit_blender()
        return True
class CBlenderScriptKidneySeparateClean(CBlenderScriptKidney) :
    def __init__(self, patientID : str, stlPath : str, saveAs = "" ) :
        super().__init__(patientID, stlPath, saveAs)    

    def process(self) -> bool :
        ## in/out separate를 수행하고, mesh clean, rotate 등의 마무리 작업 수행
        if super().process() == False :
            return False
        patientBlenderName = os.path.join(self.m_auto02Path, f"{self.m_patientID}.blend")
        bpy.ops.wm.open_mainfile(filepath=patientBlenderName) 
        
        #separate stl 수행전에 해당 오브젝트들의 mesh error를 제거한다.
        self._init_cleanup(["Kidney", "Renal_artery", "Renal_vein", "Ureter"]) 
        self._cleanup()

        self._separation_stl(self.m_optionInfo.Separate)
        
        self._switch_to_collection()
        
        self._recalc_normal(["Diaphragm"], toInside=False)
        self._make_flat("Diaphragm")  ##기존루틴
        
        # self._join_object_a_and_b("Diaphragm", "Abdominal_wall", "Abdominal_wall") ##기존루틴

        # _get_valid_object_list() 를 이용하여 꽃표 들어간 목록까지 다 비교해서 실제 적용할 object목록을 얻어온다.
        valid_clean_list = self._get_valid_object_list(self.m_optionInfo.CleanUp)
        self._init_cleanup(valid_clean_list) # remesh 할 organ들을 cleanup 하기 위함.
        self._cleanup()
        valid_smartuv_list = self._get_valid_object_list(self.m_optionInfo.SmartUV)
        self._smartUV(valid_smartuv_list)
        valid_projectuv_list = self._get_valid_object_list(self.m_optionInfo.ProjectUV) ##기존루틴
        self._smartUV(valid_smartuv_list)
        # self._projectUV(valid_projectuv_list, view_axis="BOTTOM") ##기존루틴
        
        self._rename_mesh()
        self._delete_etc_objects()
        self._rotation()        
        
        # DataRootPath의 해당 저장 폴더에 최종 파일 저장하기.
        # patientBlenderName = f"{self.m_patientID}.blend"
        # self._save_blender_with_patientID(self.m_auto03Path, patientBlenderName) 
        self._save_blender_with_bak(self.m_auto03Path, self.m_patientID)
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
    def _rotation(self) :
        for obj in bpy.context.scene.objects:
            rotate_z = math.radians(90)
            obj.rotation_euler.rotate_axis('Z', rotate_z)
        print("passed rotation")
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
class CBlenderScriptKidneyOpen(CBlenderScriptKidney) :
    def __init__(self, patientID : str, stlPath : str, saveAs = "" ) :
        super().__init__(patientID, stlPath, saveAs)    

    def process(self) -> bool :
        ## in/out separate를 수행하고, mesh clean, rotate 등의 마무리 작업 수행
        if super().process() == False :
            return False
        patientBlenderName = os.path.join(self.m_auto03Path, f"{self.m_patientID}.blend")
        bpy.ops.wm.open_mainfile(filepath=patientBlenderName) 
        

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

        patientID = find_param(scriptArgs, "--patientID")
        stlPath = find_param(scriptArgs, "--path")
        funcMode = find_param(scriptArgs, "--funcMode") # Territory, ViewAll, WrapUp

        saveAs = find_param(scriptArgs, "--saveAs")
        patientBlendPath = find_param(scriptArgs, "--patientBlendPath")

        if patientID is None or stlPath is None or funcMode is None:
            print(f"blender script : not found param")
        else :
            print("-" * 30)
            print(f"blender script : patientID -> {patientID}")
            print(f"blender script : stlPath -> {stlPath}")
            print(f"blender script : saveAs -> {saveAs}")
            print(f"blender script : funcMod -> {funcMode}")
            print("-" * 30)
            if funcMode == "Basic" :
                inst = CBlenderScriptKidneyBasic(patientID, stlPath, saveAs)
                inst.process()  
            elif funcMode == "Export" :
                inst = CBlenderScriptKidneyExport(patientID, stlPath, saveAs)
                inst.process()
            elif funcMode == "ImportSave" :
                inst = CBlenderScriptKidneyImportSave(patientID, stlPath, saveAs)
                inst.process()             
            elif funcMode == "SeparateClean" :
                inst = CBlenderScriptKidneySeparateClean(patientID, stlPath, saveAs)
                inst.process() 
            elif funcMode == "OpenBlend" :
                inst = CBlenderScriptKidneyOpen(patientID, stlPath, saveAs)
                inst.process()       
            # elif funcMode == "WrapUpSecond" : 
            #     print(f"blender script : patientBlendPath -> {patientBlendPath}")
            #     inst = CBlenderScriptKidneyWrapUpSecond(patientID, stlPath, saveAs)
            #     inst.PatientBlendPath = patientBlendPath
            #     inst.process() 
            # elif funcMode == "VesselProc" :
            #     print(f"blender script : VesselOutPath -> {vesselOutPath}")
            #     inst = CBlenderScriptKidneyVesselProc(patientID, stlPath, saveAs)
            #     inst.VesselOutPath = vesselOutPath
            #     inst.Mode = vesselProcMode
            #     inst.process() 