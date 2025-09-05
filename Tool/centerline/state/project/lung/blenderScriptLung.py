'''
blenderScriptLung.py
Latest : 25.05.21 (include 0429 patch)
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

import blenderArrangeObjects as arrange
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
        # for Territory
        '''
        "BlenderTerritory" : {
			"Segment" : {
				"DecimType" : "Fixed",
				"DecimFactor" : 2500,
				"UVMap" : "SmartUV"
			},
			"SubSegment" : {
				"DecimType" : "Fixed",
				"DecimFactor" : 1200,
				"UVMap" : "SmartUV"
			}
		}
        '''
        self.m_dicBlenderSegment = self.m_jsonData["Blender"]["BlenderTerritory"]["Segment"]
        self.m_dicBlenderSubSegment = self.m_jsonData["Blender"]["BlenderTerritory"]["SubSegment"]
        print(f"self.m_dicBlenderSegment : {self.m_dicBlenderSegment}")
        print(f"self.m_dicBlenderSubSegment : {self.m_dicBlenderSubSegment}")
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
    def Segment(self) :
        return self.m_dicBlenderSegment
    @property
    def SubSegment(self) :
        return self.m_dicBlenderSubSegment
    
class CBlenderScriptLung :
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
        # self.m_optionPath = os.path.join(tmpPath, "option.json")
        self.m_optionPath = os.path.join("option.json") #sally
        self.m_patientID = patientID
        self.m_terriStlPath = stlPath
        self.m_new = newFlag
        self.m_triOpt = triOpt
        self.m_outputRootPath = ""
        self.m_outputPatientPath = ""
        self.m_patientIdBlendPath = ""

        self.m_optionInfo = COptionInfo()
        self.m_saveAs = saveAs

        self.m_listStlName = []
        self.m_listStlNameCleanUp = []
    def process(self) -> bool :
        if self.m_optionInfo.process(self.m_optionPath) == False :
            return False
        
        dataRootName = os.path.basename(self.m_optionInfo.DataRootPath)
        # output path
        self.m_outputRootPath = os.path.join(tmpPath, dataRootName)
        self.m_outputPatientPath = os.path.dirname(os.path.dirname(self.m_terriStlPath)) # patientID 폴더 까지의 path
        self.m_patientIdBlendPath = os.path.join(self.m_outputPatientPath, f"{self.m_patientID}.blend") # patienID.blend 의 path
        
        print(f"terriStlPath : {self.m_terriStlPath}")
        print(f"blenderFullPath : {self.m_patientIdBlendPath}")
        print(f"m_outputPatientPath : {self.m_outputPatientPath}")
        
        
    def _arrange_object(self) :
        arrange.proc_arrange_lung_objects()
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
        objs = bpy.data.objects
        for obj in objs :
            if obj.name == "Camera" or obj.name == "Light" or obj.name == "Cube" :
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
            return
        # 1. blend_path의 모든 오브젝트의 이름을 가져오기
        object_names = CBlenderScriptLung.list_objects_in_blend(blenderPath)
            
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
        for cleanupName in listCleanup :
            if cleanupName in bpy.data.objects :
                self.m_listStlNameCleanUp.append([cleanupName, 0])
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
    
    def _save_blender_with_bak(self, baseName) :
        ## 기존 파일은 _old(n) 를 붙여 백업 후 원본 이름으로 최신내용을 저장함.
        if os.path.exists(self.m_patientIdBlendPath) :
            base_bak_name = f"{baseName}_old"
            new_bak_name = self._get_blendfilename_for_save_as(self.m_outputPatientPath, base_bak_name)  # ex) "path/to/huid_old(2).blend"
            new_bak_full_path = os.path.join(self.m_outputPatientPath, new_bak_name)
            print(f"new_bak_full_path : {new_bak_full_path}")
            os.rename(self.m_patientIdBlendPath, new_bak_full_path)
        # 최신파일 저장 
        blender_full_name = f"{baseName}.blend"
        self._save_blender_with_patientID(self.m_outputPatientPath, blender_full_name)
        
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
                    # print(f"completed clean-up : {objinfo[0]}")
                    objinfo[1] = 1
    
    
class CBlenderScriptLungCenterline(CBlenderScriptLung) :
    def __init__(self, patientID : str, stlPath : str, saveAs = "") :
        super().__init__(patientID, stlPath, saveAs)    

    def process(self) -> bool :
        # 센터라인을 추출하기 전, 수작업이 완료된 blender파일의 object들의 decimation과 mesh-clean을 수행한다.
        if super().process() == False :
            return False

        # patientID.blend 열기
        bpy.ops.wm.open_mainfile(filepath=self.m_patientIdBlendPath) 
        # _get_valid_object_list() 를 이용하여 꽃표 들어간 목록까지 다 비교해서 실제 적용할 object목록을 얻어온다.
        valid_clean_list = self._get_valid_object_list(self.m_optionInfo.CleanUp)
        valid_decim_dict = self._get_valid_object_dict(self.m_optionInfo.Decimation) 
        valid_decimRatio_dict = self._get_valid_object_dict(self.m_optionInfo.DecimationByRatio) 
        self._init_cleanup(valid_clean_list)
        self.triangulate_all_objects_no_ops()
        self._decimation(valid_decim_dict, False)
        self._decimation(valid_decimRatio_dict, True)
        self._cleanup()
        
        # # save
        # patientBlenderName = f"{self.m_patientID}.blend"
        # # patientBlenderNewName = self._get_blendfilename_for_save_as(self.m_outputPatientPath, patientBlenderName)
        # # self._save_blender_with_patientID(self.m_outputPatientPath, patientBlenderNewName)
        # self._save_blender_with_patientID(self.m_outputPatientPath, patientBlenderName)
        
        ## save as (self.m_saveAs = "patientid.blend")
        blender_name_no_ext = os.path.splitext(self.m_saveAs)[0]
        print(f"blender_name_no_ext : {blender_name_no_ext}")
        
        saveAsFullPath = self.m_patientIdBlendPath
        print(f"saveAsFullPath : {saveAsFullPath}")
        # 기존 파일 백업
        if os.path.exists(saveAsFullPath) :
            base_bak_name = f"{blender_name_no_ext}_old"
            new_bak_name = self._get_blendfilename_for_save_as(self.m_outputPatientPath, base_bak_name)  # ex) "path/to/huid_old(2).blend"
            new_bak_full_path = os.path.join(self.m_outputPatientPath, new_bak_name)
            print(f"new_bak_full_path : {new_bak_full_path}")
            os.rename(saveAsFullPath, new_bak_full_path)
        # 최신파일 저장 
        blender_full_name = f"{blender_name_no_ext}.blend"
        self._save_blender_with_patientID(self.m_outputPatientPath, blender_full_name)
        bpy.ops.wm.quit_blender()
        return True

class CBlenderScriptLungTerritory(CBlenderScriptLung) :
    def __init__(self, patientID : str, stlPath : str, saveAs = "") :
        super().__init__(patientID, stlPath, saveAs)
        self.m_terriBlendPath = ""
    def process(self) -> bool :
        if super().process() == False :
            return False
        ## rename TP to Lung_RS...
        self._rename_tp_to_lung(self.m_terriStlPath)
        self._delete_all_object()
        if self._import_stl(self.m_terriStlPath) == False : # Territory/out의 stl들을 import
            print("failed import stl")
            return False
        
        segment_list = []
        subsegment_list = []
        dic_decimFixed = {}
        dic_decimRatio = {}
        smartuv_list = []
        projectuv_list = []
        for stlname in self.m_listStlName : # no ext 
            # seg 인지 subseg인지 구분하기
            exclude_str = "Lung_"
            valid_str = stlname.replace(exclude_str, "")
            if self._find_lowercase(valid_str) != "" : #sub-seg
                subsegment_list.append(stlname)
                if self.m_optionInfo.SubSegment["DecimType"] == "Fixed" :
                    dic_decimFixed[stlname] = self.m_optionInfo.SubSegment["DecimFactor"]
                elif self.m_optionInfo.SubSegment["DecimType"] == "Ratio" :
                    dic_decimRatio[stlname] = self.m_optionInfo.SubSegment["DecimFactor"]
                if self.m_optionInfo.SubSegment["UVMap"] == "SmartUV" :
                    smartuv_list.append(stlname)
                elif self.m_optionInfo.SubSegment["UVMap"] == "ProjectUV" :    
                    projectuv_list.append(stlname)
            else :
                segment_list.append(stlname)
                if self.m_optionInfo.Segment["DecimType"] == "Fixed" :
                    dic_decimFixed[stlname] = self.m_optionInfo.Segment["DecimFactor"]
                elif self.m_optionInfo.Segment["DecimType"] == "Ratio" :
                    dic_decimRatio[stlname] = self.m_optionInfo.Segment["DecimFactor"]
                if self.m_optionInfo.Segment["UVMap"] == "SmartUV" :
                    smartuv_list.append(stlname)
                elif self.m_optionInfo.Segment["UVMap"] == "ProjectUV" :    
                    projectuv_list.append(stlname)  
        
        print(f"segment_list : {segment_list}")                      
        print(f"subsegment_list : {subsegment_list}")
        print(f"smartuv_list : {smartuv_list}")

        self._init_cleanup(self.m_listStlName)
        result1 = self._decimation(dic_decimFixed, False)
        result2 = self._decimation(dic_decimRatio, True)
        with open('decim_territory.csv', 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Name", "Src", "Target", "Result", "DIFF%", "Success"])
            if len(result1) > 0 :
                for item in result1 : 
                    writer.writerow(item)
            if len(result2) > 0 :
                for item in result2 : 
                    writer.writerow(item)
        
        self._cleanup()
        self._smartUV(smartuv_list)
        #self._projectUV(projectuv_list, view_axis="BACK") 

        self._arrange_object()

        ## 기존파일 존재시 넘버링하여 저장. Territory(n).blend
        # territoryBlenderBaseName = f"Territory"
        # territoryBlenderNewName = self._get_blendfilename_for_save_as(self.m_outputPatientPath, territoryBlenderBaseName)
        # self._save_blender_with_patientID(self.m_outputPatientPath, territoryBlenderNewName)

        territoryBlenderName = f"Territory.blend"
        self._save_blender_with_patientID(self.m_outputPatientPath, territoryBlenderName) 

        # bpy.ops.wm.quit_blender()
        return True
    
                
    def _rename_tp_to_lung(self, stl_folder) :
        # input_str = "D:/jys/git_Solution/Solution/UnitTestPrev/CommonPipeline_10_0319_lung/lung_patient/huid_103/TerriInfo/out"
        # stl_folder = input_str
        stl_name_list = os.listdir(stl_folder)
        print(f"stl_name_list = {stl_name_list}")

        #save 폴더에서 TP 들어간 stl만 가져오기
        for file_name in os.listdir(stl_folder):
            if "TP_" in file_name and file_name.endswith('.stl'):
                name, _ = os.path.splitext(file_name) # name without extension
                
                digit = self._extract_numbers2(name)
                new_name = f"Lung_{name[3]}S{digit}{self._find_lowercase_with_underbar(name)}_{name[4]}_{name[3]}.stl"
                print(f"in : {name} -> {new_name}")
                src = os.path.join(stl_folder, file_name)
                dst = os.path.join(stl_folder, new_name)
                if os.path.exists(dst) :
                    os.remove(dst)
                os.rename(src, dst)

class CBlenderScriptLungViewAll(CBlenderScriptLung) :
    def __init__(self, patientID : str, stlPath : str, saveAs = "") :
        super().__init__(patientID, stlPath, saveAs)

    def process(self) -> bool :
        # 사용자가 선택한 territory blender파일의 object들을 patientid.blend 파일에 import하고, Bronchus_P(sphere) 생성 후 arrange 수행.
        if super().process() == False :
            return False
        if self.m_terriBlendPath == "" : 
            return False
       
        # patientID.blend 열기
        bpy.ops.wm.open_mainfile(filepath=self.m_patientIdBlendPath) 
        # patientID.blend 에 Territory.blend의 object들을 import
        self._import_other_blend_objs(self.m_terriBlendPath)
        self._create_sphere(5, "TP_Bronchus")
        self._arrange_object()

        # save
        patientBlenderBaseName = f"{self.m_patientID}"
        # patientBlenderNewName = self._get_blendfilename_for_save_as(self.m_outputPatientPath, patientBlenderBaseName)
        # self._save_blender_with_patientID(self.m_outputPatientPath, patientBlenderNewName)

        self._save_blender_with_bak(patientBlenderBaseName)


        return True
    
    
        
    @property
    def TerriBlendPath(self) -> str:
        return self.m_terriBlendPath
    @TerriBlendPath.setter
    def TerriBlendPath(self, path : str) :
        self.m_terriBlendPath = path

class CBlenderScriptLungWrapUp(CBlenderScriptLung) :
    def __init__(self, patientID : str, stlPath : str, saveAs = "") :
        super().__init__(patientID, stlPath, saveAs)
        self.m_patientBlendPathCustom = ""

    def process(self) -> bool :
        if super().process() == False :
            return False
        if not os.path.exists(self.m_patientBlendPathCustom) :
            print(f"File Not Exist : {self.m_patientBlendPathCustom}")
            return False
        # patientID.blend 열기
        # bpy.ops.wm.open_mainfile(filepath=self.m_patientIdBlendPath) 
        bpy.ops.wm.open_mainfile(filepath=self.m_patientBlendPathCustom) 
        # _get_valid_object_list() 를 이용하여 꽃표 들어간 목록까지 다 비교해서 실제 적용할 object목록을 얻어온다.
        valid_clean_list = self._get_valid_object_list(self.m_optionInfo.CleanUp)
        valid_decim_dict = self._get_valid_object_dict(self.m_optionInfo.Decimation) 
        valid_decimRatio_dict = self._get_valid_object_dict(self.m_optionInfo.DecimationByRatio) 
        self._init_cleanup(valid_clean_list)
        decim_result1 = self._decimation(valid_decim_dict, False)
        decim_result2 = self._decimation(valid_decimRatio_dict, True)
        with open('decim_others.csv', 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Name", "Src", "Target", "Result", "DIFF%", "Success"])
            if len(decim_result1) > 0 :
                for item in decim_result1 : 
                    writer.writerow(item)
            if len(decim_result2) > 0 :
                for item in decim_result2 : 
                    writer.writerow(item)
        self._cleanup()
        all_objects = self._get_all_object_list()
        # self._recalc_normal(all_objects, toInside=False) # Outside로 해도 Inside로 뒤집어지는 문제가 있어서 일단 Outside 강제 셋팅은 생략.
        self._recalc_normal(["Wall_Inner", "Wall_Inside"], toInside=True) # wall_inner, wall_inside
        self._shade_auto_smooth(all_objects, angle=30) #
        valid_smartuv_list = self._get_valid_object_list(self.m_optionInfo.SmartUV)
        self._smartUV(valid_smartuv_list)
        
        # save
        # patientBlenderName = f"{self.m_patientID}"
        # patientBlenderNewName = self._get_blendfilename_for_save_as(self.m_outputPatientPath, patientBlenderName)
        # self._save_blender_with_patientID(self.m_outputPatientPath, patientBlenderNewName)
        
        # patientBlenderName = f"{self.m_patientID}.blend"
        # self._save_blender_with_patientID(self.m_outputPatientPath, patientBlenderName)

        patientBlenderName = os.path.basename(self.m_patientBlendPathCustom) #"patientID.blend"
        self._save_blender_with_patientID(self.m_outputPatientPath, patientBlenderName)  #이름 그대로 저장.
        bpy.ops.wm.quit_blender()

        return True
    @property
    def PatientBlendPath(self) -> str:
        return self.m_patientBlendPathCustom
    @PatientBlendPath.setter
    def PatientBlendPath(self, path : str) :
        self.m_patientBlendPathCustom = path

class CBlenderScriptLungWrapUpSecond(CBlenderScriptLung) :
    def __init__(self, patientID : str, stlPath : str, saveAs = "") :
        super().__init__(patientID, stlPath, saveAs)
        self.m_patientBlendPathCustom = ""

    def process(self) -> bool :
        if super().process() == False :
            return False
        if not os.path.exists(self.m_patientBlendPathCustom) :
            print(f"File Not Exist : {self.m_patientBlendPathCustom}")
            return False
        
        # patientID.blend 열기
        # bpy.ops.wm.open_mainfile(filepath=self.m_patientIdBlendPath) 
        bpy.ops.wm.open_mainfile(filepath=self.m_patientBlendPathCustom) 
        # valid_smartuv_list = self._get_valid_object_list(self.m_optionInfo.SmartUV)
        valid_projectuv_list = self._get_valid_object_list(self.m_optionInfo.ProjectUV)
        # self._smartUV(valid_smartuv_list)
        self._projectUV(valid_projectuv_list, view_axis="FRONT")
        
        self._delete_etc_objects()

        # save
        # patientBlenderBaseName = f"{self.m_patientID}"
        # patientBlenderNewName = self._get_blendfilename_for_save_as(self.m_outputPatientPath, patientBlenderBaseName)
        # self._save_blender_with_patientID(self.m_outputPatientPath, patientBlenderNewName)

        patientBlenderName = os.path.basename(self.m_patientBlendPathCustom)
        self._save_blender_with_patientID(self.m_outputPatientPath, patientBlenderName)  #이름 그대로 저장.
        bpy.ops.wm.quit_blender()

        # # DataRootPath의 해당 저장 폴더에 최종 파일 저장하기. => Vessel knife 에서 저장함.
        # save_folder = os.path.join(self.m_optionInfo.DataRootPath, self.m_patientID, "02_SAVE", "02_BLENDER_SAVE")
        # patientBlenderName = f"{self.m_patientID}.blend"
        # self._save_blender_with_patientID(save_folder, patientBlenderName) 



        return True
    @property
    def PatientBlendPath(self) -> str:
        return self.m_patientBlendPathCustom
    @PatientBlendPath.setter
    def PatientBlendPath(self, path : str) :
        self.m_patientBlendPathCustom = path

class CBlenderScriptCutVesselUVMapping :
    ## Cutting된 혈관들을 선택 후 Join
    ## Join된 Object를 원래의 이름으로 다시 Separate
    @staticmethod
    def _tag_objects_with_vertex_groups(objs):
        for obj in objs:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.object.vertex_group_add()
            obj.vertex_groups.active.name = obj.name
            bpy.ops.object.vertex_group_assign()
            bpy.ops.object.mode_set(mode='OBJECT')
    @staticmethod
    def _join_objects(objs):
        bpy.context.view_layer.objects.active = objs[0]
        for obj in objs:
            obj.select_set(True)
        bpy.ops.object.join()
        return bpy.context.active_object
    @staticmethod
    def separate_by_vertex_groups_and_rename(selectNameBase): # 에러남..
        bpy.ops.object.select_all(action='DESELECT')

        joined_obj = None
        selected_obj_name = ""
        # 모든 오브젝트 선택
        for obj in bpy.data.objects:
            if selectNameBase in obj.name :
                selected_obj_name = obj.name
                print(f"selected obj : {selected_obj_name}")
                break
        joined_obj = bpy.data.objects.get(selected_obj_name)
        if joined_obj and joined_obj.type == 'MESH':
            # 저장된 vertex group 이름들
            group_names = [vg.name for vg in joined_obj.vertex_groups]

            bpy.context.view_layer.objects.active = joined_obj
            joined_obj.select_set(True)
            bpy.ops.object.mode_set(mode='EDIT')

            for vg_name in group_names:
                bpy.ops.mesh.select_all(action='DESELECT')
                bpy.ops.object.vertex_group_set_active(group=vg_name)
                bpy.ops.object.vertex_group_select()
                bpy.ops.mesh.separate(type='SELECTED')

            bpy.ops.object.mode_set(mode='OBJECT')

            # 분리 후 새 오브젝트들 가져오기
            new_objs = [obj for obj in bpy.context.selected_objects if obj != joined_obj]

            # 새 오브젝트 이름 복원
            for idx, obj in enumerate(new_objs):
                obj.name = group_names[idx]  
                obj.data.name = group_names[idx] # mesh의 이름도 함께 변경
                obj.vertex_groups.clear()

            # Join된 오브젝트 삭제 (선택적)
            bpy.data.objects.remove(joined_obj, do_unlink=True)

            print("분리 및 이름 복원 완료!")
      
    # func : separate_by_vertex_groups_and_rename_preserve_data_no_ops
    # 기능1 : bpy.ops 없이 vertex group 기준 mesh 분리
    # 기능2 : custom split normals 유지
    # 기능3 : active UV map 유지
    # 기능4 : 오브젝트 및 메쉬 이름을 vertex group 이름과 동일하게 지정
    @staticmethod
    def separate_by_vertex_groups_and_rename_preserve_data_no_ops(selectNameBase):
        selected_obj_name = ""
        # 'Bronchus'가 들어간 이름의 오브젝트 선택(혈관조각들이 join된 상태의 Bronchusxxx object임)
        for obj in bpy.data.objects:
            if selectNameBase in obj.name :
                selected_obj_name = obj.name
                print(f"selected obj : {selected_obj_name}")
                break
        obj = bpy.data.objects.get(selected_obj_name)
        
        ##--------------------------------------------------------------------
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)

        # 원본 데이터
        src_verts = eval_mesh.vertices
        src_polys = eval_mesh.polygons
        src_loops = eval_mesh.loops
        src_uv_layer = eval_mesh.uv_layers.active.data if eval_mesh.uv_layers.active else None
        has_uv = src_uv_layer is not None
        custom_normals = [loop.normal.copy() for loop in src_loops]

        # vertex -> group 매핑
        group_map = {}
        for vg in obj.vertex_groups:
            group_map[vg.index] = {
                "name": vg.name,
                "verts": set()
            }

        for v in obj.data.vertices:
            for g in v.groups:
                if g.group in group_map:
                    group_map[g.group]["verts"].add(v.index)

        for group_index, data in group_map.items():
            vg_name = data["name"]
            vert_indices = data["verts"]

            if not vert_indices:
                continue

            vert_map = {}
            new_verts = []
            for idx in vert_indices:
                vert_map[idx] = len(new_verts)
                new_verts.append(src_verts[idx].co.copy())

            # faces
            new_faces = []
            loop_vert_indices = []
            loop_src_loop_indices = []
            for poly in src_polys:
                if all(v in vert_indices for v in poly.vertices):
                    new_face = [vert_map[v] for v in poly.vertices]
                    new_faces.append(new_face)
                    for li in range(poly.loop_start, poly.loop_start + poly.loop_total):
                        loop_vert_indices.append(vert_map[src_loops[li].vertex_index])
                        loop_src_loop_indices.append(li)

            # 메쉬 생성
            new_mesh = bpy.data.meshes.new(vg_name)
            new_mesh.from_pydata(new_verts, [], new_faces)
            new_mesh.validate()
            new_mesh.update()

            # UV 복사
            if has_uv:
                uv_layer = new_mesh.uv_layers.new(name="UVMap")
                for i, li in enumerate(loop_src_loop_indices):
                    uv_layer.data[i].uv = src_uv_layer[li].uv.copy()

            # Normal 복사
            new_mesh.use_auto_smooth = True
            new_mesh.create_normals_split()
            loop_normals = [custom_normals[li] for li in loop_src_loop_indices]
            new_mesh.normals_split_custom_set(loop_normals)

            # 오브젝트 생성 및 이름 설정
            new_obj = bpy.data.objects.new(vg_name, new_mesh)
            new_obj.name = vg_name
            new_obj.data.name = vg_name
            bpy.context.collection.objects.link(new_obj)

        # 메모리 해제 및 원본 오브젝트 삭제 (선택)
        eval_obj.to_mesh_clear()
        bpy.data.objects.remove(obj, do_unlink=True)

        print("✅ Bronchus Separate Done. (keep normal, UV)")

    @staticmethod
    def auto_join_for_uv_then_restore(selectNameBase : str):
        # 모든 오브젝트 선택 해제
        bpy.ops.object.select_all(action='DESELECT')

        # 모든 오브젝트 선택
        for obj in bpy.data.objects:
            if selectNameBase in obj.name :
                obj.select_set(True)

        # 필요시 하나를 활성 오브젝트로 설정 (첫 번째)
        if bpy.data.objects:
            bpy.context.view_layer.objects.active = bpy.data.objects[0]
            
        selected_objs = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
        if len(selected_objs) < 2:
            print("2개 이상의 Mesh Object 를 선택해주세요.")
            return

        CBlenderScriptCutVesselUVMapping._tag_objects_with_vertex_groups(selected_objs)
        joined_obj = CBlenderScriptCutVesselUVMapping._join_objects(selected_objs)

        print("이제 UV를 매핑하세요. 완료되면 저장 후 툴에서 Separate를 실행하세요!")
        
class CBlenderScriptCutVesselAutoMarkSharp :
    ## Cutting된 혈관들의 절단면을 선택한 후 Mark Sharp 수행
    THRESHOLD = 1e-2  #important factor : 이 값이 너무 작으면 절단면의 일부가 선택안될수 있음.
    MIN_FACES = 7 #important factor : 이 값이 너무 크면 선택안되는 절단면이 있을 수 있음.
    @staticmethod
    def mark_sharp_custom(objList) :
        for objName in objList:
            obj = bpy.data.objects.get(objName)
            if obj and obj.type == 'MESH':
                CBlenderScriptCutVesselAutoMarkSharp._select_cut_face_and_mark_sharp(obj, min_faces=7) 
              
        bpy.ops.object.mode_set(mode='OBJECT')
    @staticmethod    
    def _vector_almost_equal(v1: Vector, v2: Vector, tol=THRESHOLD):
        return (v1 - v2).length < tol
    @staticmethod
    def _get_connected_normal_groups(bm, tol=THRESHOLD, min_faces=10):
        visited = set()
        groups = []

        def dfs(start_face, normal, group):
            stack = [start_face]
            while stack:
                face = stack.pop()
                if face in visited:
                    continue
                if not CBlenderScriptCutVesselAutoMarkSharp._vector_almost_equal(face.normal, normal, tol):
                    continue
                visited.add(face)
                group.append(face)
                for edge in face.edges:
                    for linked_face in edge.link_faces:
                        if linked_face not in visited:
                            stack.append(linked_face)

        for face in bm.faces:
            if face in visited:
                continue
            group = []
            dfs(face, face.normal, group)
            if len(group) > min_faces:
                groups.append(group)

        return groups
    @staticmethod
    def _are_groups_adjacent(group1, group2):
        # 두 그룹의 face가 edge를 공유하면 인접
        group1_faces = set(group1)
        for face in group2:
            for edge in face.edges:
                for linked_face in edge.link_faces:
                    if linked_face in group1_faces:
                        return True
        return False
    @staticmethod
    def _find_largest_groups_among_adjacent(groups):
        group_graph = []
        for i, g1 in enumerate(groups):
            adj = set()
            for j, g2 in enumerate(groups):
                if i != j and CBlenderScriptCutVesselAutoMarkSharp._are_groups_adjacent(g1, g2):
                    adj.add(j)
            group_graph.append(adj)

        visited = set()
        result_groups = []

        for i in range(len(groups)):
            if i in visited:
                continue
            component = [i]
            visited.add(i)
            stack = [i]

            # 연결된 그룹 전체 탐색
            while stack:
                current = stack.pop()
                for neighbor in group_graph[current]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        component.append(neighbor)
                        stack.append(neighbor)

            # 해당 컴포넌트 내 가장 큰 그룹만 선택
            largest_group_index = max(component, key=lambda idx: len(groups[idx]))
            result_groups.append(groups[largest_group_index])

        return result_groups
    @staticmethod
    def _select_cut_face_and_mark_sharp(obj, min_faces=10, tol=THRESHOLD):
    #    bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.mode_set(mode='OBJECT')  # 안정적으로 OBJECT → EDIT 전환
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()

        # 전체 face 선택 해제
        for f in bm.faces:
            f.select = False
                
        # clear sharp 모든 엣지를 부드럽게 설정 (Sharp 해제)
        for edge in bm.edges:
            edge.smooth = True  # Sharp가 아닌 상태

        # 1. 노멀 기준 연결된 그룹들 찾기
        normal_groups = CBlenderScriptCutVesselAutoMarkSharp._get_connected_normal_groups(bm, tol, 7)

        # 2. 붙어있는 그룹들 중 가장 큰 것만 선택
        largest_groups = CBlenderScriptCutVesselAutoMarkSharp._find_largest_groups_among_adjacent(normal_groups)

        # 3. 조건 만족한 그룹만 선택
        for group in largest_groups:
            if len(group) >= min_faces:
                for f in group:
                    f.select = True
                    #set mark sharp
                    for edge in f.edges:
                        edge.smooth = False  # mark sharp 상태
                        # print("edge.smooth : false")

        bmesh.update_edit_mesh(obj.data)
class CBlenderScriptLungVesselProc(CBlenderScriptLung) :
    # 컷팅된 혈관의 절단경계면의 쉐이딩 제거 및 Bronchus UV mapping을 위한 Join과 Separate 수행
    # Mode : JOIN -> 컷팅된 혈관의 Rename, auto shading및 절단경계면 shading 제거, Bronchus Join
    # Mode : SEPARATE -> 수동 UV mapping된 Bronchus 를 다시 Separate 후 이름 복원
    def __init__(self, patientID : str, stlPath : str, saveAs = "") :
        super().__init__(patientID, stlPath, saveAs)
        self.m_vesselOutPath = ""
        self.m_mode = ""  # JOIN, SEPARATE, MERGE
        
    def process(self) -> bool :
        if super().process() == False :
            return False
        vesselBlenderName = f"Vessel.blend"
        if self.m_mode == "JOIN" :
            ## rename TP to Vessel name
            arteryPath = os.path.join(self.m_vesselOutPath, "Artery")
            bronchusPath = os.path.join(self.m_vesselOutPath, "Bronchus")
            veinPath = os.path.join(self.m_vesselOutPath, "Vein")
            self._rename_tp_to_vessel(arteryPath)
            self._rename_tp_to_vessel(bronchusPath)
            self._rename_tp_to_vessel(veinPath)

            self._delete_all_object()
            
            self._import_stl(arteryPath)
            self._import_stl(bronchusPath)
            self._import_stl(veinPath)
            
            #Triangulate  # TODO : 부작용 없는지 확인해야함. (vessel에만 적용하는 것이라서 괜찮을 것으로 예상됨)
            CBlenderScriptLungVesselProc.triangulate_all_objects_no_ops()

            all_objects = self._get_all_object_list()
            self._shade_auto_smooth(all_objects, angle=180) 
            CBlenderScriptCutVesselAutoMarkSharp.mark_sharp_custom(all_objects)
            CBlenderScriptCutVesselUVMapping.auto_join_for_uv_then_restore("Bronchus")
            
            self._save_blender_with_patientID(self.m_outputPatientPath, vesselBlenderName) 

            # bpy.ops.wm.quit_blender()
            return True
        elif self.m_mode == "SEPARATE" :
            ## join 상태에서 UV Mapping된 Bronchus를 다시 분리하고 각 segment들의 이름을 복원한다.
            blenderFullPath = os.path.join(self.m_outputPatientPath, vesselBlenderName)
            bpy.ops.wm.open_mainfile(filepath=blenderFullPath) 
            CBlenderScriptCutVesselUVMapping.separate_by_vertex_groups_and_rename_preserve_data_no_ops("Bronchus")
            self._save_blender_with_patientID(self.m_outputPatientPath, vesselBlenderName) 
            return True
        elif self.m_mode == "MERGE" :
            ## patientID.blend와 Vessel.blend를 merge 하고 arragne 수행
            blenderFullPath = os.path.join(self.m_outputPatientPath, vesselBlenderName)
            if blenderFullPath == "" : 
                return False
            vessel_obj_names = self.list_objects_in_blend(blenderFullPath)
            # vessel_obj_names = CBlenderScriptLungVesselProc.list_objects_in_blend(blenderFullPath)
            print(f"vessel_obj_names : {vessel_obj_names}")

            # patientID.blend 열기
            bpy.ops.wm.open_mainfile(filepath=self.m_patientIdBlendPath) 
            for mesh in bpy.data.meshes :
                for name in vessel_obj_names :
                    if name == mesh.name :
                        print(f"the same obj : {mesh.name}")
                        bpy.data.meshes.remove(mesh)
                        break

            # patientID.blend 에 Territory.blend의 object들을 import
            self._import_other_blend_objs(blenderFullPath)
            self._arrange_object()
            
            # save
            patientBlenderName = os.path.basename(self.m_patientIdBlendPath) #"patientID.blend"
            self._save_blender_with_patientID(self.m_outputPatientPath, patientBlenderName)  #이름 그대로 저장.
            
            # DataRootPath의 해당 저장 폴더에 최종 파일 저장하기.
            save_folder = os.path.join(self.m_optionInfo.DataRootPath, self.m_patientID, "02_SAVE", "02_BLENDER_SAVE")
            patientBlenderName = f"{self.m_patientID}.blend"
            self._save_blender_with_patientID(save_folder, patientBlenderName) 

            # bpy.ops.wm.quit_blender()
        return False        

    def _rename_tp_to_vessel(self, stl_folder : str) :
        if not os.path.exists(stl_folder) :
            return
        dicInitial = {"A":"Artery", "B":"Bronchus", "V":"Vein"}
        stl_name_list = os.listdir(stl_folder)
        print(f"stl_name_list = {stl_name_list}")

        #save 폴더에서 TP 들어간 stl만 가져오기
        currWholeVesselName = ""
        directionName = ""
        for file_name in stl_name_list:
            name, _ = os.path.splitext(file_name) # name without extension
            new_name = ""
            src = ""
            dst = ""
            do_flag = False
            if "TP_" in file_name and file_name.endswith('.stl'):            
                currWholeVesselName = dicInitial[name[4]]
                directionName = name[3]
                digit = self._extract_numbers2(name)
                new_name = f"{currWholeVesselName}_{directionName}{name[4]}{digit}{self._find_lowercase_with_underbar(name)}_{directionName}.stl"
                do_flag = True
            elif "Whole" in file_name :
                new_name = f"{currWholeVesselName}_{directionName}.stl"
                do_flag = True

            if do_flag :
                print(f"in : {name} -> {new_name}")
                src = os.path.join(stl_folder, file_name)
                dst = os.path.join(stl_folder, new_name)
                if os.path.exists(dst) :
                    os.remove(dst)
                os.rename(src, dst)

    

    @property
    def VesselOutPath(self) -> str:
        return self.m_vesselOutPath
    @VesselOutPath.setter
    def VesselOutPath(self, path : str) :
        self.m_vesselOutPath = path
    @property
    def Mode(self) -> str :
        return self.m_mode
    @Mode.setter
    def Mode(self, mode : str) :
        self.m_mode = mode


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
        saveAs = find_param(scriptArgs, "--saveAs")
        terriBlendPath = find_param(scriptArgs, "--terriBlendPath")
        patientBlendPath = find_param(scriptArgs, "--patientBlendPath")
        vesselOutPath = find_param(scriptArgs, "--vesselOutPath")
        vesselProcMode = find_param(scriptArgs, "--vesselProcMode")

        funcMode = find_param(scriptArgs, "--funcMode") # Territory, ViewAll, WrapUp


        # newFlag = exist_param(scriptArgs, "--new")
        # triOpt = exist_param(scriptArgs, "--triOpt")

        if patientID is None or stlPath is None or saveAs is None or funcMode is None:
            print(f"blender script : not found param")
        else :
            print("-" * 30)
            print(f"blender script : patientID -> {patientID}")
            print(f"blender script : stlPath -> {stlPath}")
            print(f"blender script : saveAs -> {saveAs}")
            print(f"blender script : funcMod -> {funcMode}")
            print("-" * 30)
            if funcMode == "CleanForCenterline" :
                inst = CBlenderScriptLungCenterline(patientID, stlPath, saveAs)
                inst.process()  
            elif funcMode == "Territory" :
                inst = CBlenderScriptLungTerritory(patientID, stlPath, saveAs)
                inst.process()
            elif funcMode == "ViewAll" :
                print(f"blender script : terriBlendPath -> {terriBlendPath}")
                inst = CBlenderScriptLungViewAll(patientID, stlPath, saveAs)
                inst.TerriBlendPath = terriBlendPath
                inst.process()                
            elif funcMode == "WrapUp" :
                print(f"blender script : patientBlendPath -> {patientBlendPath}")
                inst = CBlenderScriptLungWrapUp(patientID, stlPath, saveAs)
                inst.PatientBlendPath = patientBlendPath
                inst.process() 
            elif funcMode == "WrapUpSecond" : 
                print(f"blender script : patientBlendPath -> {patientBlendPath}")
                inst = CBlenderScriptLungWrapUpSecond(patientID, stlPath, saveAs)
                inst.PatientBlendPath = patientBlendPath
                inst.process() 
            elif funcMode == "VesselProc" :
                print(f"blender script : VesselOutPath -> {vesselOutPath}")
                inst = CBlenderScriptLungVesselProc(patientID, stlPath, saveAs)
                inst.VesselOutPath = vesselOutPath
                inst.Mode = vesselProcMode
                inst.process() 