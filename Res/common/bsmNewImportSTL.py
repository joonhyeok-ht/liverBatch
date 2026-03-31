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



class CBSMNewImportSTL(blenderOption.CBlenderScriptBase) :
    '''
    param
        - "StlPath"         : stl 파일들이 저장되어 있는 folder path, 없다면 "" 또는 None을 입력 
        - "ListStlFullPath  : stl파일들의 전체 경로를 저장한 list, 없다면 None을 입력 
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
        
        blenderOption.CBlenderScriptUtil.delete_all_object()
        blenderOption.CBlenderScriptUtil.delete_etc_objects()
        
        stlPath = self.OptionInfo.get_user_value("StlPath")
        listStlFullPath = self.OptionInfo.get_user_value("ListStlFullPath")
        if listStlFullPath is None :
            listStlFullPath = []

        if stlPath and os.path.exists(stlPath) == True :
            retList = [
                os.path.join(stlPath, f) for f in os.listdir(stlPath)
                if f.lower().endswith(".stl") and os.path.isfile(os.path.join(stlPath, f))
            ]
            if len(retList) != 0 :
                listStlFullPath += retList
        
        for stlFullPath in listStlFullPath :
            blenderOption.CBlenderScriptUtil.import_stl(stlFullPath)
        
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

            inst = CBSMNewImportSTL(optionFullPath)
            inst.process()

