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


class CBSMExport(blenderOption.CBlenderScriptBase) :
    '''
    param
        - "ListObjName"     : blender obj name
        - "ExportPath"      : export 할 folder path를 지정
    
    desc 
        - ExportPath 경로에 obj name에 해당되는 mesh를 stl로 저장 
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
        
        listObjName = self.OptionInfo.get_user_value("ListObjName")
        exportPath = self.OptionInfo.get_user_value("ExportPath")

        if listObjName is None :
            return False
        if exportPath is None or exportPath == "" :
            return False
        
        objs = bpy.data.objects
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = objs[0]
        objs[0].select_set(True)
        
        os.makedirs(exportPath, exist_ok=True)

        for objName in listObjName :
            if objName in bpy.data.objects :
                bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.select_all(action='DESELECT')
                bpy.data.objects[objName].select_set(True)
                bpy.context.view_layer.objects.active = bpy.data.objects[objName]
                bpy.ops.export_mesh.stl(filepath=os.path.join(exportPath, objName + '.stl'), use_selection=True)
    


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

            inst = CBSMExport(optionFullPath)
            inst.process()



