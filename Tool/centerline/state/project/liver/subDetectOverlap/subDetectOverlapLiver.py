# -*- coding: utf-8 -*-
'''
File : subDetectOverlap.py (based by processDetectingOverlapWin.py)
Version : 2025_06_05
'''
import os
import sys

tmpPath = os.path.abspath(os.path.dirname(__file__))
algPath = os.path.join(tmpPath, "Algorithm")

sys.path.append(algPath)

from Algorithm.DetectingOverlap import detectingOverlap

class CSubDetectOverlap :
    # s_jsonFileName = "option.json"
    def __init__(self) -> None:
        self.m_stlPath = ""
        self.m_logPath = ""
    
    def process(self) -> bool :
        if not os.path.exists(self.m_stlPath) :
            print(f"not found STL Path : {self.m_stlPath}")
            return False
        if not os.path.exists(self.m_logPath) :
            print(f"not found Log Path (Skip) : {self.m_logPath}")
            # return False
        
        filelist = os.listdir(self.m_stlPath)
        for ff in filelist:
            if "zz_" in ff:
                fullpath = os.path.join(self.m_stlPath, ff)
                os.remove(fullpath)
                
                
        outputOverlapJson0 = os.path.join(self.m_logPath, "Artery.json")
        outputOverlapJson1 = os.path.join(self.m_logPath, "Vein.json")
        outputOverlapJson2 = os.path.join(self.m_logPath, "Portal.json")
        
        
        # DetectingOverlapBlock_0
        detectingOverlapBlock = detectingOverlap.CDetectingOverlap()
        detectingOverlapBlock.InputPath = self.m_stlPath
        detectingOverlapBlock.OutputPath = self.m_stlPath
        detectingOverlapBlock.OutputJsonPath = outputOverlapJson0
        detectingOverlapBlock.add_src_stl_filename("Vein.stl")
        detectingOverlapBlock.add_src_stl_filename("Portal.stl")
        detectingOverlapBlock.add_src_stl_filename("Duct.stl")
        detectingOverlapBlock.TargetStlFile = "Artery.stl"
        detectingOverlapBlock.process()
        
        # DetectingOverlapBlock_1
        detectingOverlapBlock_1 = detectingOverlap.CDetectingOverlap()
        detectingOverlapBlock_1.InputPath = self.m_stlPath
        detectingOverlapBlock_1.OutputPath = self.m_stlPath
        detectingOverlapBlock_1.OutputJsonPath = outputOverlapJson1
        detectingOverlapBlock_1.add_src_stl_filename("Portal.stl")
        detectingOverlapBlock_1.add_src_stl_filename("Duct.stl")
        detectingOverlapBlock_1.TargetStlFile = "Vein.stl"
        detectingOverlapBlock_1.process()

        # DetectingOverlapBlock_2
        detectingOverlapBlock_2 = detectingOverlap.CDetectingOverlap()
        detectingOverlapBlock_2.InputPath = self.m_stlPath
        detectingOverlapBlock_2.OutputPath = self.m_stlPath
        detectingOverlapBlock_2.OutputJsonPath = outputOverlapJson2
        detectingOverlapBlock_2.add_src_stl_filename("Duct.stl")
        detectingOverlapBlock_2.TargetStlFile = "Portal.stl"
        detectingOverlapBlock_2.process()
               
        return True
   
    @property
    def StlPath(self) -> str :
        return self.m_stlPath
    @StlPath.setter
    def StlPath(self, path : str) :
        self.m_stlPath = path
    @property
    def LogPath(self) -> str :
        return self.m_logPath
    @LogPath.setter
    def LogPath(self, path : str) :
        self.m_logPath = path

if __name__ == '__main__' :

    inst = CSubDetectOverlap()
    inst.StlPath = ""
    inst.LogPath = ""
    result = inst.process()
    if result :
        print("CSubDetectOverlap -> PASS")
    else : 
        print("CSubDetectOverlap -> FAIL")




