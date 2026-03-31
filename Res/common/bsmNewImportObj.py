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



class CBSMNewImportObj(blenderOption.CBlenderScriptBase) :
    '''
    param
        - "ObjPath"         : obj 파일들이 저장되어 있는 folder path, 없다면 "" 또는 None을 입력 
        - "ListObjFullPath  : obj파일들의 전체 경로를 저장한 list, 없다면 None을 입력 
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
        
        objPath = self.OptionInfo.get_user_value("ObjPath")
        listObjFullPath = self.OptionInfo.get_user_value("ListObjFullPath")
        if listObjFullPath is None :
            listObjFullPath = []

        if objPath and os.path.exists(objPath) == True :
            retList = [
                os.path.join(objPath, f) for f in os.listdir(objPath)
                if f.lower().endswith(".obj") and os.path.isfile(os.path.join(objPath, f))
            ]
            if len(retList) != 0 :
                listObjFullPath += retList
        
        for objFullPath in listObjFullPath :
            blenderOption.CBlenderScriptUtil.import_obj(objFullPath)
        
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

            inst = CBSMNewImportObj(optionFullPath)
            inst.process()

