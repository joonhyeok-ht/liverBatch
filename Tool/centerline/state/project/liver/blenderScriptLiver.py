'''
blenderScriptStomach.py
Latest : 25.07.29  based CommonPipeline_10_0509_x
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

import blenderCleanUpMesh as clmsh

class COptionInfo :
    def __init__(self):
        self.m_jsonData = None
        self.m_dataRootPath = ""
        self.m_dicDecimation = {}
        self.m_dicDecimationByRatio = {}
        self.m_listMeshCleanup = []
        self.m_listSamrtUV = []
        self.m_dicNiftiSTLPair =  {}
        
    def process(self, fullPath : str) -> bool :
        if type(fullPath) != str:
            fullPath = str(fullPath)
        
        if os.path.exists(fullPath) == False: 
            print(f"not valid Option_Path : {fullPath}")
            return False
        # json initialize 
        with open(fullPath, 'r') as fp :
            self.m_jsonData = json.load(fp)

        self.m_dataRootPath = self.m_jsonData["DataRootPath"]
        self.m_decimation = self.m_jsonData["Blender"]["Decimation"]
        self.m_decimationByRatio = self.m_jsonData["Blender"]["DecimationByRatio"]["List"]        
        self.m_meshCleanup = self.m_jsonData["Blender"]["MeshCleanUp"]
        self.m_smartUVIncludedList = self.m_jsonData["Blender"]["SmartUV"]["IncludedList"]
        self.m_notImportList = self.m_jsonData["Blender"]["NotImport"]
        
        maskKey = "MaskList"
        m_listMask = []
        if maskKey in self.m_jsonData :
            m_listMask = self.m_jsonData[maskKey]
            for index, maskInfo in enumerate(m_listMask):
                nameExceptExt = maskInfo['name'].split(".")[0]
                self.m_dicNiftiSTLPair[nameExceptExt] = maskInfo['stl_name'].split(".")[0]
        

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
    def SmartUV(self) -> list :
        return self.m_smartUVIncludedList
    @property
    def NotImport(self) -> list :
        return self.m_notImportList
    @property
    def NiftiStlPair(self) -> dict :
        return self.m_dicNiftiSTLPair
    
class CBlenderScriptLiver :
    @staticmethod
    def list_objects_in_blend(blend_path):
        with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
            return data_from.objects 
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
    def __init__(self, patientID : str, optionPath : str, stlPath : str, outputPath = "") -> None :
        self.m_optionFullPath = optionPath
        self.m_patientID = patientID
        self.m_stlPath = stlPath        # "" 가능
        self.m_optionInfo = COptionInfo()
        self.m_outPath = outputPath

        self.m_outputRootPath = ""
        self.m_outputPatientPath = ""

        self.m_auto01Path = ""
        self.m_auto02Path = ""
        self.m_auto03Path = ""

        self.m_listStlName = []
        self.m_listStlNameCleanUp = []
        
        self.m_mappingMaskDict = {
            "maskName":"stlName"
        }

    def process(self) -> bool:
        if self.m_optionInfo.process(self.m_optionFullPath) == False :
            return False   
        if not os.path.exists(self.m_outPath) : 
            print(f"outPath not extist : {self.m_outPath}. Return.")
            return False
        
        self.m_auto01Path = os.path.join(self.m_outPath, "Auto01_Recon")
        self.m_auto02Path = os.path.join(self.m_outPath, "Auto02_Overlap")
        self.m_auto03Path = os.path.join(self.m_outPath, "Auto03_MeshClean")        
        os.makedirs(self.m_auto01Path, exist_ok=True)
        os.makedirs(self.m_auto02Path, exist_ok=True)
        os.makedirs(self.m_auto03Path, exist_ok=True)
        
        return True
    
    def _enable_add_on(self) :
        # kidney,stomach 공통
        bpy.ops.preferences.addon_enable(module='object_print3d_utils')  
        
    def _mapping_mask_stl(self, maskName : str, mesh_objects : list) -> str:
        
        if maskName in self.m_mappingMaskDict.keys():
            maskName = self.m_mappingMaskDict[maskName]
        
        filtered = [s for s in mesh_objects if str(maskName).lower() in s.lower()]
        
        if filtered:
            return filtered[0]
        else:
            return maskName
        
    def _get_valid_object_list(self, in_list : list) -> list:
        # 꽃표 들어간 목록까지 다 비교해서 실제 적용할 object목록을 리턴한다.
        mesh_objects = [obj.name for obj in bpy.data.objects if obj.type == 'MESH']
        flattened = []
        print(f"mesh_objects : {mesh_objects}")
        valid_list = []
        for maskName in in_list : 
            validname = maskName
            if '*' in maskName :
                validname = maskName.replace("*", "")
                
            if validname in self.m_mappingMaskDict.keys():
                validname = self.m_mappingMaskDict[validname]
                    
            filtered = [s for s in mesh_objects if validname.lower() in s.lower() and not "zz" in s.lower()]
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
                valid_dict[self._mapping_mask_stl(validname, mesh_objects)] = factor
        print(f"valid_dict : {valid_dict}")    
        return valid_dict
    def _delete_all_object(self) :
        self.m_listStlName = []
        # kidney,stomach 공통
        for mesh in bpy.data.meshes :
            bpy.data.meshes.remove(mesh)   
    def _delete_etc_objects(self) :
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
            
            if stlNameExceptExt in self.m_optionInfo.NotImport :
                print(f"{stlNameExceptExt} Not Imported.")
                continue
            
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
        object_names = CBlenderScriptLiver.list_objects_in_blend(blenderPath)
            
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
        
    def _decimation(self, dicDeci : dict, bRatio : bool) :
        if bRatio :
            mode = "Ratio"
        else : 
            mode = "Fixed"
        
        result_list = []        
        for deciName, triValue in dicDeci.items() : 
            bpy.ops.object.select_all(action='DESELECT')

            if deciName in bpy.data.objects :
                obj = bpy.data.objects[deciName]
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                srcTriangleCnt = len(obj.data.polygons)
                targetTriangleCnt = 0
                if bRatio == False :
                    targetTriangleCnt = triValue                    
                    decimationRatio = targetTriangleCnt / srcTriangleCnt
                    if decimationRatio == 1.0 :
                        #print(f"- Decimation : {deciName} Skipped. (dedimationRatio=1.0)")

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
                    #print(f"- Decimation : {deciName} Applied. (Triangles : ({srcTriangleCnt}) -> ({dstTriangleCnt}))")
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
    def _rename_blender_name(self) :
        if len(self.m_optionInfo.NiftiStlPair) == 0 :     
            print(f"_rename_blender_name() - ERROR : NiftiStlPair is Empty.")
        bpy.ops.object.select_all(action='DESELECT')
        objs = bpy.data.objects
        for obj in objs :
            curr_name = obj.name
            if curr_name in self.m_optionInfo.NiftiStlPair :
                obj = bpy.data.objects[curr_name]
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                obj.data.name = self.m_optionInfo.NiftiStlPair[curr_name]
                obj.name = self.m_optionInfo.NiftiStlPair[curr_name]
                print(f"Rename {curr_name} to {obj.name}")
            
        print("Rename Done.")
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
        print(f"mesh clean cnt : {count}")
        for cnt in range(0, 10) :
            self.__clean_up_mesh(self.m_listStlNameCleanUp) 
        print("Mesh-Clean All Done. ")
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
    def _extract_numbers2(self, string):
        # 숫자인 문자만 필터링하여 리스트로 만들고, 이를 합침
        return ''.join(char for char in string if char.isdigit())

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
                    
    def _shade_smooth_all(self) :
        # Object Mode로 전환 (필수)
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        # 모든 메시 오브젝트에 대해 처리
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                # 활성화 및 선택
                bpy.context.view_layer.objects.active = obj
                obj.select_set(True)

                # Shade Smooth 적용
                obj.data.use_auto_smooth = True  # Auto Smooth 활성화 (옵션)
                bpy.ops.object.shade_smooth()

                # 선택 해제
                obj.select_set(False)
                
    def _apply_all_transforms_and_shade_smooth(self) :
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
    
class CBlenderScriptStomachBasic(CBlenderScriptLiver) :
    def __init__(self, patientID : str, optionPath : str, stlPath : str, outputPath = "") :
        super().__init__(patientID, optionPath, stlPath, outputPath)    

    def process(self) -> bool :
        ## Reconstruction이 완료된 STL 파일의 decimation, Remesh 등을 수행한다.
        if super().process() == False :
            return False
        self._enable_add_on()
        self._delete_all_object()
        self._delete_etc_objects()

        if self._import_stl(self.m_stlPath) == False : 
            print("failed import stl")
            return False

        valid_decim_dict = self._get_valid_object_dict(self.m_optionInfo.Decimation) 
        valid_decimRatio_dict = self._get_valid_object_dict(self.m_optionInfo.DecimationByRatio) 
        self._decimation(valid_decim_dict, False)
        self._decimation(valid_decimRatio_dict, True)

        #smartuv 넣기?? 마지막에 넣어야할듯
        self._rename_mesh()
        
        # save
        # DataRootPath의 해당 저장 폴더에 최종 파일 저장하기.
        patientBlenderName = f"{self.m_patientID}.blend"
        self._save_blender_with_patientID(self.m_auto01Path, patientBlenderName) 
        # self._save_blender_with_bak(self.m_auto01Path, self.m_patientID)
        #bpy.ops.wm.quit_blender()

        # delete STL path
        # if os.path.exists(self.m_stlPath) :
        #     shutil.rmtree(self.m_stlPath)
        #     print(f"delete {self.m_stlPath} folder")

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
            
class CBlenderScriptStomachExport() :
    def __init__(self, patientID : str, inBlendPath : str, exportPath : str ) :
        self.m_patientID = patientID
        self.m_inputBlendPath = inBlendPath
        self.m_exportPath = exportPath

    def process(self) -> bool :
        if self.m_patientID == "" :
            print(f"patientID is Null")
            return False
        if not os.path.exists(self.m_inputBlendPath) :
            print(f"Not Exist : {self.m_inputBlendPath}")
            return False
        if not os.path.exists(self.m_exportPath) :
            print(f"Not Exitst : {self.m_exportPath}")
            return False
        
        patientBlenderName = os.path.join(self.m_inputBlendPath, f"{self.m_patientID}.blend")
        bpy.ops.wm.open_mainfile(filepath=patientBlenderName) 
        export_path = self.m_exportPath
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
        
class CBlenderScriptStomachImportSave(CBlenderScriptLiver) :
    
    def __init__(self, patientID : str, optionPath : str, stlPath : str, outputPath = "" ) :
        super().__init__(patientID, optionPath, stlPath, outputPath)    

    def process(self) -> bool :
        if super().process() == False :
            return False
        
        self._delete_all_object()
        self._delete_etc_objects()
        
        if self._import_stl(self.m_stlPath) == False :
            print("failed import stl")
            return False
        
        # DataRootPath의 해당 저장 폴더에 최종 파일 저장하기.
        patientBlenderName = f"{self.m_patientID}.blend"
        self._save_blender_with_patientID(self.m_auto02Path, patientBlenderName) 
        # self._save_blender_with_bak(self.m_auto02Path, self.m_patientID)
        # bpy.ops.wm.quit_blender()

        # delete export stl path
        # if os.path.exists(self.m_stlPath) :
        #     shutil.rmtree(self.m_stlPath)
        #     print(f"delete {self.m_stlPath} folder")
        return True
    
class CBlenderScriptLiverOpen(CBlenderScriptLiver) :
    def __init__(self, patientID : str, optionPath : str, stlPath : str, outputPath = "") :
        super().__init__(patientID, optionPath, stlPath, outputPath)    
        self.m_openPath = ""
    def process(self) -> bool :
        
        if super().process() == False :
            return False
        if os.path.exists(self.m_openPath) == False:
            print(f"ERROR : openPath Not Exist. ")
            return False

        patientBlenderName = self.m_openPath
        bpy.ops.wm.open_mainfile(filepath=patientBlenderName) 
    @property
    def OpenPath(self) :
        return self.m_openPath
    @OpenPath.setter
    def OpenPath(self, path) :
        self.m_openPath = path
    
    
class CBlenderScriptStomachMeshClean(CBlenderScriptLiver) :
    def __init__(self, patientID : str, optionPath : str, stlPath : str, outputPath = "", overlapPath = "") :
        super().__init__(patientID, optionPath, stlPath, outputPath)    

    def process(self) -> bool :
        if super().process() == False :
            return False
        #patientBlenderName = os.path.join(self.m_auto02Path, f"{self.m_patientID}.blend")
        overlapBlenderPath = overlapPath
        if not os.path.exists(overlapBlenderPath) :
            print(f"Error - not exist blender file : patientBeldnerName . Return.")
            return False
        bpy.ops.wm.open_mainfile(filepath=overlapBlenderPath) 
        
        self._recalc_normal(["Diaphragm"], toInside=True)
        self._make_flat("Diaphragm")

        valid_clean_list = self._get_valid_object_list(self.m_optionInfo.CleanUp)
        self._init_cleanup(valid_clean_list)
        
        self.triangulate_all_objects_no_ops()
        
        self._cleanup()
        #self._shade_smooth_all()
        self._apply_all_transforms_and_shade_smooth()

        valid_smartuv_list = self._get_valid_object_list(self.m_optionInfo.SmartUV)
        self._smartUV(valid_smartuv_list)
        
        self._rename_mesh()
        self._rename_blender_name()
        self._delete_etc_objects()
        
        # DataRootPath의 해당 저장 폴더에 최종 파일 저장하기.
        patientBlenderName = f"{self.m_patientID}.blend"
        self._save_blender_with_patientID(self.m_auto03Path, patientBlenderName) 
        # self._save_blender_with_bak(self.m_auto03Path, self.m_patientID)
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
    def _make_flat(self, object_name) :
        # 해당 오브젝트가 있는지 체크
        namelist = []
        objs = bpy.data.objects
        for obj in objs : 
            namelist.append(obj.name)
        if object_name not in namelist :
            print(f"_make_flat() : {object_name} is not in Mesh Objects. Return.")
            return
        
        # 오브젝트 가져오기
        obj = bpy.data.objects.get(object_name)
        if obj is None:
            raise ValueError(f"not found {object_name}'")
        if obj.type != 'MESH':
            raise TypeError(f"'{object_name}' not a mesh")

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

        print(f"'{object_name}' make flat done : faces dissolve + triangulate .")
    @property
    def InputBlendPath(self) :
        return self.m_inputBlendPath
    @InputBlendPath.setter
    def InputBlendPath(self, path : str) :
        self.m_inputBlendPath = path

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
        
        funcMode = find_param(scriptArgs, "--func_mode") 
        print(f"blender script : func_mode -> {funcMode}")
        patientID = find_param(scriptArgs, "--patient_id")

        if patientID is None or funcMode is None:
            print(f"blender script : not found param")
        else :
            if funcMode == "Basic" :
                optionPath = find_param(scriptArgs, "--option_path")
                stlPath = find_param(scriptArgs, "--stl_path")
                outputPath = find_param(scriptArgs, "--out_path")
                inst = CBlenderScriptStomachBasic(patientID, optionPath, stlPath, outputPath)
                inst.process()  
            elif funcMode == "Export" :
                inputBlendPath = find_param(scriptArgs, "--input_blend_path")
                exportPath = find_param(scriptArgs, "--export_path")
                inst = CBlenderScriptStomachExport(patientID, inputBlendPath, exportPath)
                inst.process()
            elif funcMode == "ImportSave" :
                optionPath = find_param(scriptArgs, "--option_path")
                stlPath = find_param(scriptArgs, "--stl_path")
                outputPath = find_param(scriptArgs, "--out_path")
                inst = CBlenderScriptStomachImportSave(patientID, optionPath, stlPath, outputPath)
                inst.process()             
            elif funcMode == "MeshClean" :
                optionPath = find_param(scriptArgs, "--option_path")
                stlPath = find_param(scriptArgs, "--stl_path")
                outputPath = find_param(scriptArgs, "--out_path")
                overlapPath = find_param(scriptArgs, "--overlap_path")
                inst = CBlenderScriptStomachMeshClean(patientID, optionPath, stlPath, outputPath)
                inst.process() 
            elif funcMode == "OpenBlend" :
                openPath = find_param(scriptArgs, "--open_path")
                stlPath = find_param(scriptArgs, "--stl_path")
                optionPath = find_param(scriptArgs, "--option_path")
                outputPath = find_param(scriptArgs, "--out_path")
                
                inst = CBlenderScriptLiverOpen(patientID, optionPath, stlPath, outputPath)
                inst.OpenPath = openPath
                inst.process()
    