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

import blenderOption as blenderOption
import blenderScriptCleanUpMesh as clmsh



class CBlenderScriptIndRecon :
    @staticmethod    
    def __get_decimation_ratio(srcVerticesCnt : int, targetVerticesCnt : int) :
        return targetVerticesCnt / srcVerticesCnt
    
    
    def __init__(self, optionFullPath : str, inputPath : str, outputPath : str, saveName : str) -> None :
        self.m_optionPath = optionFullPath
        self.m_inputPath = inputPath
        self.m_outputPath = outputPath
        self.m_saveName = saveName
        self.m_listStlName = []
        self.m_listStlNameCleanUp = []

        self.m_optionInfo = blenderOption.COptionInfo()
    def process(self) -> bool :
        if self.m_optionInfo.process(self.m_optionPath) == False :
            return False

        if self._import_stl() == False :
            print("failed import stl")
            return False
        
        self._init_cleanup(self.m_optionInfo.CleanUp)
        self._decimation(self.m_optionInfo.Decimation, False)
        self._decimation(self.m_optionInfo.DecimationByRatio, True)
        self._remesh(self.m_optionInfo.Remesh)
        self._cleanup()
        self._save_blender_with_patientID(self.m_outputPath, self.m_saveName)

        return True


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

            self.m_listStlName.append(stlName.split('.')[0])
            bpy.ops.import_mesh.stl(filepath=f"{stlFullPath}")
            print(f"imported {stlFullPath}")
        return True
    def _init_cleanup(self, listCleanup : list) :
        for cleanupName in listCleanup :
            if cleanupName not in self.m_listStlName :
                continue
            if cleanupName not in bpy.data.objects :
                continue
            self.m_listStlNameCleanUp.append([cleanupName, 0])
    def _decimation(self, dicDeci : dict, bRatio : bool) :
        for deciName, triValue in dicDeci.items() : 
            if deciName not in self.m_listStlName :
                continue
            if deciName not in bpy.data.objects :
                continue
            
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')

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
            if remeshName not in self.m_listStlName :
                continue
            if remeshName not in bpy.data.objects :
                continue

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
            inst = CBlenderScriptIndRecon(optionFullPath, inputPath, outputPath, saveName)
            inst.process()

