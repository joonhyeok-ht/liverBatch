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


class CBSPRecon(blenderOption.CBlenderScriptBase) :
    '''
    param
        - "InputPath"       : import 할 mesh file들이 있는 folder  
        - "SaveFullPath"    : 저장 할 blend 파일명의 전체 경로
    '''
    def __init__(self, optionFullPath : str) -> None :
        super().__init__(optionFullPath)
        # input your code
    def clear(self) :
        # input your code
        super().clear()
    def process(self) -> bool :
        if self.Ready == False :
            print("blender script Recon error : not found option")
            return False
        
        blenderOption.CBlenderScriptUtil.delete_all_object()
        blenderOption.CBlenderScriptUtil.delete_etc_objects()

        if self._import_stl() == False :
            print("failed import stl")
            return False
        
        # decimation
        retList = self.m_optionInfo.get_list_decimation_meshname()
        for meshname in retList :
            triCnt = self.m_optionInfo.get_decimation(meshname)
            blenderOption.CBlenderScriptUtil.decimation_tri(meshname, triCnt)
        
        # decimation ratio
        retList = self.m_optionInfo.get_list_decimation_ratio_meshname()
        for meshname in retList :
            ratio = self.m_optionInfo.get_decimation_ratio(meshname)
            blenderOption.CBlenderScriptUtil.decimation_ratio(meshname, ratio)

        # cleanup
        iCnt = self.m_optionInfo.get_cleanup_meshname_count()
        for inx in range(0, iCnt) :
            meshname = self.m_optionInfo.get_cleanup_meshname(inx)
            blenderOption.CBlenderScriptUtil.cleanup(meshname)

        # remesh
        retList = self.m_optionInfo.get_list_remesh_meshname()
        for meshname in retList :
            voxel = self.m_optionInfo.get_remesh_voxel(meshname)
            triCnt = self.m_optionInfo.get_remesh_voxel_facecnt(meshname)
            blenderOption.CBlenderScriptUtil.remesh(meshname, voxel, triCnt)
        
        # samrtuv
        iCnt = self.m_optionInfo.get_smartuv_meshname_count()
        for inx in range(0, iCnt) :
            meshname = self.m_optionInfo.get_smartuv_meshname(inx)
            blenderOption.CBlenderScriptUtil.smartuv(meshname)
            
        
        blenderOption.CBlenderScriptUtil.match_mesh_data_name()

        # save 
        outputFullPath = self.OptionInfo.get_user_value("SaveFullPath")
        if outputFullPath is None or outputFullPath == "" :
            blenderOption.CBlenderScriptUtil.save_blender()
        else :
            blenderOption.CBlenderScriptUtil.save_as_blender(outputFullPath)

        return True


    # protected
    def _import_stl(self) -> bool :
        inputPath = self.OptionInfo.get_user_value("InputPath")
        if inputPath is None or inputPath == "" :
            return False
        if os.path.exists(inputPath) == False : 
            return False

        listStlName = os.listdir(inputPath)
        if len(listStlName) == 0 :
            print("not found stl files")
            return False
        
        for stlName in listStlName :
            ext = stlName.split('.')[-1]
            if ext != "stl" :
                 continue
            
            stlFullPath = os.path.join(inputPath, stlName)
            blenderOption.CBlenderScriptUtil.import_stl(stlFullPath)
        return True
    


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
            inst = CBSPRecon(optionFullPath)
            inst.process()

