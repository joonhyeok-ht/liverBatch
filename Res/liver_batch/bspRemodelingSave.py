'''
'''
import bpy

import os, sys
import json
import re
import shutil
import math
import time

kidney_batchPath = os.path.abspath(os.path.dirname(__file__))
resPath = os.path.abspath(os.path.dirname(kidney_batchPath))
sys.path.append(kidney_batchPath)
sys.path.append(resPath)

import common.blenderOption as blenderOption


class CBSPRemodelingSave(blenderOption.CBlenderScriptBase) :
    '''
    param
        - "StlPath"    : remodeling된 stl 파일들이 저장되어 있는 folder path
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
        
        blenderOption.CBlenderScriptUtil._enable_add_on()
        # self.delete_overlap_sphere_objects()
        #blenderOption.CBlenderScriptUtil.delete_all_object()
        #blenderOption.CBlenderScriptUtil.delete_etc_objects()

        if self._import_stl() == False :
            print("failed import stl")
            return False
        
        iCnt = self.m_optionInfo.get_cleanup_meshname_count()
        for inx in range(0, iCnt) :
            meshname = self.m_optionInfo.get_cleanup_meshname(inx)
            blenderOption.CBlenderScriptUtil.cleanup(meshname)
        
        # self._init_cleanup(valid_clean_list)
        # self._cleanup()
        blenderOption.CBlenderScriptUtil.triangulate_all_objects_no_ops()
        blenderOption.CBlenderScriptUtil._apply_all_transforms_and_shade_smooth()
        
        
        # self.triangulate_all_objects_no_ops()
        
        # all_objects = self._get_all_object_list()
        # self._shade_auto_smooth(all_objects, angle=180) 
        
        # # decimation
        # retList = self.m_optionInfo.get_list_decimation_meshname()
        # for meshname in retList :
        #     triCnt = self.m_optionInfo.get_decimation(meshname)
        #     blenderOption.CBlenderScriptUtil.decimation_tri(meshname, triCnt)
        
        # # decimation ratio
        # retList = self.m_optionInfo.get_list_decimation_ratio_meshname()
        # for meshname in retList :
        #     ratio = self.m_optionInfo.get_decimation_ratio(meshname)
        #     blenderOption.CBlenderScriptUtil.decimation_ratio(meshname, ratio)

        # # cleanup
        # iCnt = self.m_optionInfo.get_cleanup_meshname_count()
        # for inx in range(0, iCnt) :
        #     meshname = self.m_optionInfo.get_cleanup_meshname(inx)
        #     blenderOption.CBlenderScriptUtil.cleanup(meshname)

        # # remesh
        # retList = self.m_optionInfo.get_list_remesh_meshname()
        # for meshname in retList :
        #     voxel = self.m_optionInfo.get_remesh_voxel(meshname)
        #     triCnt = self.m_optionInfo.get_remesh_voxel_facecnt(meshname)
        #     blenderOption.CBlenderScriptUtil.remesh(meshname, voxel, triCnt)
        
        # samrtuv
        # iCnt = self.m_optionInfo.get_smartuv_meshname_count()
        # for inx in range(0, iCnt) :
        #     meshname = self.m_optionInfo.get_smartuv_meshname(inx)
        #     blenderOption.CBlenderScriptUtil.smartuv(meshname)    

        # save 
        outputFullPath = self.OptionInfo.get_user_value("SaveFullPath")
        if outputFullPath is None or outputFullPath == "" :
            blenderOption.CBlenderScriptUtil.save_blender()
        else :
            blenderOption.CBlenderScriptUtil.save_as_blender(outputFullPath)
        # bpy.ops.wm.quit_blender()

        return True

    def delete_overlap_sphere_objects(self) :
        # Camera와 Light는 mesh가 아니므로 object로 검색해서 지워야함.
        objs = bpy.data.objects
        for obj in objs :
            if "zz" in obj.name:
                bpy.data.objects.remove(obj, do_unlink=True)
                
    # protected
    def _import_stl(self) -> bool:
        inputPath = self.OptionInfo.get_user_value("StlPath")
        if inputPath is None or inputPath == "":
            return False
        if os.path.exists(inputPath) == False:
            return False

        listStlName = os.listdir(inputPath)
        if len(listStlName) == 0:
            print("not found stl files")
            return False

        for stlName in listStlName:
            ext = stlName.split('.')[-1].lower()
            if ext != "stl":
                continue

            stlFullPath = os.path.join(inputPath, stlName)

            # 🔥 object 이름 (확장자 제거)
            objName = os.path.splitext(stlName)[0]
            
            if self.OptionInfo.get_user_value("OverWriteFlag") ==  "1":
                # 🔥 기존 object 삭제 (덮어쓰기)
                if objName in bpy.data.objects:
                    obj = bpy.data.objects[objName]

                    # 선택 후 삭제
                    bpy.ops.object.select_all(action='DESELECT')
                    obj.select_set(True)
                    bpy.context.view_layer.objects.active = obj
                    bpy.ops.object.delete()
                # 🔥 import
                blenderOption.CBlenderScriptUtil.import_stl(stlFullPath)
            else:
                if objName in bpy.data.objects:
                    continue
                else:
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
            inst = CBSPRemodelingSave(optionFullPath)
            inst.process()

