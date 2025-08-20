'''
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


class CBlenderScriptRecon :
    @staticmethod    
    def __get_decimation_ratio(srcVerticesCnt : int, targetVerticesCnt : int) :
        return targetVerticesCnt / srcVerticesCnt
    
    
    def __init__(self, optionFullPath : str, inputPath : str, outputPath : str, saveName : str) -> None :
        self.m_optionPath = optionFullPath
        self.m_inputPath = inputPath
        self.m_outputPath = outputPath
        self.m_saveName = saveName
        self.m_listStlNameCleanUp = []

        self.m_optionInfo = COptionInfo()
    def process(self) -> bool :
        if self.m_optionInfo.process(self.m_optionPath) == False :
            return False

        self._delete_all_object()
        if self._import_stl() == False :
            print("failed import stl")
            return False
        
        self._init_cleanup(self.m_optionInfo.CleanUp)
        self._decimation(self.m_optionInfo.Decimation, False)
        self._decimation(self.m_optionInfo.DecimationByRatio, True)
        self._remesh(self.m_optionInfo.Remesh)
        self._cleanup()
        self._save_blender_with_patientID(self.m_outputPath, self.m_saveName)
        # bpy.ops.wm.quit_blender()

        return True


    def _delete_all_object(self) :
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete()
    def _import_stl(self) -> bool :        
        listStlName = os.listdir(self.m_inputPath)
        if len(listStlName) == 0 :
            print("not found stl files")
            return False
        
        for stlName in listStlName :
            if stlName == ".DS_Store" : 
                continue

            ext = stlName.split('.')[-1]
            if ext != "stl" :
                 continue
            stlFullPath = os.path.join(self.m_inputPath, stlName)
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
                    targetVertexCnt = triValue
                    srcVertexCnt =len(bpy.context.active_object.data.vertices)
                    decimationRatio = self.__get_decimation_ratio(srcVertexCnt, targetVertexCnt / 2)
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
        cnt = 0
        print(f"mesh clean cnt : {count}")
        # for cnt in range(0, 10) :
        while count > 0 :
            self.__clean_up_mesh(self.m_listStlNameCleanUp) 
            print(f"mesh clean step : {cnt}, {count}")
            count = sum(1 for item in self.m_listStlNameCleanUp if item[1] == 0)
            cnt += 1
        print("passed mesh clean")
    def _save_blender_with_patientID(self, outputPath : str, saveName : str) :
        blenderFullPath = os.path.join(outputPath, saveName)
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
        inputPath = find_param(scriptArgs, "--inputPath")
        outputPath = find_param(scriptArgs, "--outputPath")
        saveName = find_param(scriptArgs, "--saveName")

        if inputPath is None or outputPath is None or saveName is None:
            print(f"blender script : not found param")
        else :
            print("-" * 30)
            print(f"blender script : optionFullPath -> {optionFullPath}")
            print(f"blender script : inputPath -> {inputPath}")
            print(f"blender script : outputPath -> {outputPath}")
            print(f"blender script : saveName -> {saveName}")
            print("-" * 30)
            inst = CBlenderScriptRecon(optionFullPath, inputPath, outputPath, saveName)
            inst.process()

