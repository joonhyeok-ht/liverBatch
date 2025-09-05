'''
blenderScriptCommonPipeline.py
latest : 25.05.21 (include 0429 patch(mesh clean))
'''
import bpy

import os, sys
import json
import re
import shutil
import math
import time

tmpPath = os.path.abspath(os.path.dirname(__file__))
sys.path.append(tmpPath)

import blenderScriptCleanUpMesh as clmsh


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

        self.m_centerlineInfo = self.m_jsonData["CenterlineInfo"]

        self.m_voxelSize = self.m_remesh["VoxelSize"]

        self._update_dictionary_type(self.m_dicDecimation, self.m_decimation)
        self._update_dictionary_type(self.m_dicDecimationByRatio, self.m_decimationByRatio)
        self._update_dictionary_type(self.m_dicRemesh, self.m_remesh["RemeshList"])
        self._update_list_type(self.m_listMeshCleanup, self.m_meshCleanup)
        self._update_list_type(self.m_listMeshHealing, self.m_meshHealing)
        self._update_list_type(self.m_listSamrtUV, self.m_smartUV)
        
        return True
    
    def _update_dictionary_type(self, outputDic : dict, srcDict : dict) :
        for key, value in srcDict.items() :
            listRet = COptionInfo.generate_strings(key)
            if listRet is None :
                outputDic[key] = value
            else :
                for subKey in listRet :
                    outputDic[subKey] = value
    def _update_list_type(self, outList : list, srcList : list) :
        for key in srcList :
            listRet = COptionInfo.generate_strings(key)
            if listRet is None :
                outList.append(key)
            else :
                for subKey in listRet :
                    outList.append(subKey)
    
    @property
    def DataRootPath(self) -> str :
        return self.m_dataRootPath
    @property
    def Decimation(self) -> dict :
        return self.m_dicDecimation
    @property
    def DecimationByRatio(self) -> dict :
        return self.m_dicDecimationByRatio
    @property
    def Remesh(self) -> dict :
        return self.m_dicRemesh
    @property
    def CleanUp(self) -> list :
        return self.m_listMeshCleanup
    @property
    def Healing(self) -> list :
        return self.m_listMeshHealing
    @property
    def SmartUV(self) -> list :
        return self.m_listSamrtUV
    @property
    def CenterlineInfo(self) -> list :
        return self.m_centerlineInfo
    @property
    def VoxelSize(self) :
        return self.m_voxelSize


class CBlenderScriptCommonPipeline :
    @staticmethod    
    def __get_decimation_ratio(srcVerticesCnt : int, targetVerticesCnt : int) :
        return targetVerticesCnt / srcVerticesCnt
    

    def __init__(self, patientID : str, stlPath : str, saveAs = "", newFlag = True, triOpt = True) -> None :
        self.m_optionPath = "" #os.path.join(self.fileAbsPath, "option.json")
        self.m_patientID = patientID
        self.m_stlPath = stlPath
        self.m_new = newFlag
        self.m_triOpt = triOpt
        self.m_intermediateDataPath = ""
        self.m_outputPatientPath = ""

        self.m_optionInfo = COptionInfo()
        self.m_saveAs = saveAs

        self.m_listStlNameCleanUp = []
    def process(self) -> bool :
        if self.m_optionInfo.process(self.m_optionPath) == False :
            return False
        
        # dataRootName = os.path.basename(self.m_optionInfo.DataRootPath)
        # self.m_intermediateDataPath = os.path.join(tmpPath, dataRootName)
        self.m_outputPatientPath = os.path.join(self.m_intermediateDataPath, self.m_patientID)
        self.m_stlPath = os.path.join(self.m_outputPatientPath, self.m_stlPath)

        if self.m_new == True :
            self._delete_all_object()
        if self._import_stl() == False :
            print("failed import stl")
            return False
        if self.m_triOpt == True :
            self._init_cleanup(self.m_optionInfo.CleanUp)
            self._decimation(self.m_optionInfo.Decimation, False)
            self._decimation(self.m_optionInfo.DecimationByRatio, True)
            self._remesh(self.m_optionInfo.Remesh)
            self._cleanup()
            self._healing(self.m_optionInfo.Healing)
            self._smartUV(self.m_optionInfo.SmartUV)

        ## save as (self.m_saveAs = "patientid.blend")
        blender_name_no_ext = os.path.splitext(self.m_saveAs)[0]
        print(f"blender_name_no_ext : {blender_name_no_ext}")
        
        saveAsFullPath = os.path.join(self.m_outputPatientPath, self.m_saveAs)
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


    def _delete_all_object(self) :
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete()
    def _import_stl(self) -> bool :        
        listStlName = os.listdir(self.m_stlPath)
        if len(listStlName) == 0 :
            print("not found stl files")
            return False
        
        for stlName in listStlName :
            if stlName == ".DS_Store" : 
                continue

            ext = stlName.split('.')[-1]
            if ext != "stl" :
                 continue
            stlFullPath = os.path.join(self.m_stlPath, stlName)
            if os.path.isdir(stlFullPath) == True :
                continue

            bpy.ops.import_mesh.stl(filepath=f"{stlFullPath}")
            print(f"imported {stlFullPath}")
        return True
    def _init_cleanup(self, listCleanup : list) :
        for cleanupName in listCleanup :
            if cleanupName in bpy.data.objects :
                self.m_listStlNameCleanUp.append([cleanupName, 0])
    def _decimation(self, dicDeci : dict, bRatio : bool) :
        for deciName, triValue in dicDeci.items() : 
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')

            if deciName in bpy.data.objects :
                obj = bpy.data.objects[deciName]
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj

                if bRatio == False :
                    # targetVertexCnt = triValue
                    # srcVertexCnt =len(bpy.context.active_object.data.vertices)
                    # decimationRatio = self.__get_decimation_ratio(srcVertexCnt, targetVertexCnt / 2)
                    # triangle 개수를 읽어와서 그 기준으로 계산하도록 변경 - sally
                    targetTriangleCnt = triValue
                    srcTriangleCnt = len(obj.data.polygons)
                    decimationRatio = targetTriangleCnt / srcTriangleCnt
                else :
                    decimationRatio = triValue / 100.0
                
                decimate_modifier = obj.modifiers.new(name="Decimate", type='DECIMATE')
                decimate_modifier.ratio = decimationRatio
                bpy.ops.object.modifier_apply(modifier=decimate_modifier.name)

                print(f"passed decimation : {deciName} : {triValue} : {decimationRatio}")
        print("passed decimation")
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
        print("passed mesh clean")
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
        print("passed smartUV")
    def _save_blender_with_patientID(self, outputPath : str, saveAs : str) :
        blenderPath = os.path.join(outputPath)
        blenderFullPath = os.path.join(blenderPath, saveAs)
        if os.path.exists(blenderFullPath):
            os.remove(blenderFullPath)
            
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.wm.save_as_mainfile(filepath=blenderFullPath)
        bpy.ops.object.select_all(action='DESELECT')
        print(f"Save Path : {blenderFullPath}")


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
    def _extract_numbers2(self, string):
        # 숫자인 문자만 필터링하여 리스트로 만들고, 이를 합침
        return ''.join(char for char in string if char.isdigit())
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
    
    @property
    def OptionPath(self) -> str:
        return self.m_optionPath
    @OptionPath.setter
    def OptionPath(self, path : str) :
        self.m_optionPath = path
    @property
    def IntermediateDataPath(self) -> str:
        return self.m_intermediateDataPath
    @IntermediateDataPath.setter
    def IntermediateDataPath(self, path : str) :
        self.m_intermediateDataPath = path
        

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
        newFlag = exist_param(scriptArgs, "--new")
        triOpt = exist_param(scriptArgs, "--triOpt")
        optionPath = find_param(scriptArgs, "--optionPath")
        intermediatePath = find_param(scriptArgs, "--intermediatePath")

        if patientID is None or stlPath is None or saveAs is None or optionPath is None or intermediatePath is None:
            print(f"blender script : not found param")
        else :
            print("-" * 30)
            print(f"blender script : patientID -> {patientID}")
            print(f"blender script : stlPath -> {stlPath}")
            print(f"blender script : saveAs -> {saveAs}")
            print(f"blender script : new -> {newFlag}")
            print(f"blender script : triOpt -> {triOpt}")
            print(f"blender script : optionPath -> {optionPath}")
            print(f"blender script : intermediatePath -> {intermediatePath}")
            print("-" * 30)

            inst = CBlenderScriptCommonPipeline(patientID, stlPath, saveAs, newFlag, triOpt)
            inst.OptionPath = optionPath
            inst.IntermediateDataPath = intermediatePath
            inst.process()

