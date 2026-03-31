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



class CBSMClean(blenderOption.CBlenderScriptBase) :
    '''
    param
        - "ListMeshName"    : clean-up 할 mesh name, None or 원소가 없다면 전체를 clean-up 한다.
        - "SaveFullPath"    : 저장 할 blend 파일명의 전체 경로, None or "" 라면 덮어쓴다. 
    '''
    def __init__(self, optionFullPath : str) -> None :
        super().__init__(optionFullPath)
        # input your code
    def clear(self) :
        # input your code
        super().clear()
    def process(self) -> bool :
        if self.Ready == False :
            return False
        
        retList = self.OptionInfo.get_user_value("ListMeshName")

        # 특별히 지정한 mesh name이 없다면 전체를 clean-up 한다.
        if retList is None or len(retList) == 0 :
            iCnt = self.m_optionInfo.get_cleanup_meshname_count()
            for inx in range(0, iCnt) :
                meshname = self.m_optionInfo.get_cleanup_meshname(inx)
                blenderOption.CBlenderScriptUtil.cleanup(meshname)
        else :
            for meshname in retList :
                blenderOption.CBlenderScriptUtil.cleanup(meshname)
        
        outputFullPath = self.OptionInfo.get_user_value("SaveFullPath")
        if outputFullPath is None or outputFullPath == "" :
            blenderOption.CBlenderScriptUtil.save_blender()
        else :
            blenderOption.CBlenderScriptUtil.save_as_blender(outputFullPath)



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

            inst = CBSMClean(optionFullPath)
            inst.process()

