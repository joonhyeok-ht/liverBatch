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
            #print(f"not found STL Path : {self.m_stlPath}")
            return False
        if not os.path.exists(self.m_logPath) :
            print(f"not found Log Path (Skip) : {self.m_logPath}")
            # return False
        
        filelist = os.listdir(self.m_stlPath)
        for ff in filelist:
            if "zz_" in ff:
                fullpath = os.path.join(self.m_stlPath, ff)
                os.remove(fullpath)
        
        outputOverlapJson0 = os.path.join(self.m_logPath, "artery_ureter.json")
        outputOverlapJson1 = os.path.join(self.m_logPath, "vein_ureter.json")
        outputOverlapJson2 = os.path.join(self.m_logPath, "artery_vein.json")
        outputOverlapJson3 = os.path.join(self.m_logPath, "wall_ureter.json")
        outputOverlapJson4 = os.path.join(self.m_logPath, "wall_gonadal_vein.json")
        
        # DetectingOverlapBlock_0
        detectingOverlapBlock = detectingOverlap.CDetectingOverlap()
        detectingOverlapBlock.InputPath = self.m_stlPath
        detectingOverlapBlock.OutputPath = self.m_stlPath
        detectingOverlapBlock.OutputJsonPath = outputOverlapJson0
        detectingOverlapBlock.add_src_stl_filename("Renal_artery.stl")
        detectingOverlapBlock.TargetStlFile = "Ureter.stl"
        detectingOverlapBlock.process()

        # DetectingOverlapBlock_1
        detectingOverlapBlock_1 = detectingOverlap.CDetectingOverlap()
        detectingOverlapBlock_1.InputPath = self.m_stlPath
        detectingOverlapBlock_1.OutputPath = self.m_stlPath
        detectingOverlapBlock_1.OutputJsonPath = outputOverlapJson1
        detectingOverlapBlock_1.add_src_stl_filename("Renal_vein.stl")
        detectingOverlapBlock_1.TargetStlFile = "Ureter.stl"
        detectingOverlapBlock_1.process()

        # DetectingOverlapBlock_2
        detectingOverlapBlock_2 = detectingOverlap.CDetectingOverlap()
        detectingOverlapBlock_2.InputPath = self.m_stlPath
        detectingOverlapBlock_2.OutputPath = self.m_stlPath
        detectingOverlapBlock_2.OutputJsonPath = outputOverlapJson2
        detectingOverlapBlock_2.add_src_stl_filename("Renal_artery.stl")
        detectingOverlapBlock_2.TargetStlFile = "Renal_vein.stl"
        detectingOverlapBlock_2.process()

        # DetectingOverlapBlock_2
        detectingOverlapBlock_3 = detectingOverlap.CDetectingOverlap()
        detectingOverlapBlock_3.InputPath = self.m_stlPath
        detectingOverlapBlock_3.OutputPath = self.m_stlPath
        detectingOverlapBlock_3.OutputJsonPath = outputOverlapJson3
        detectingOverlapBlock_3.add_src_stl_filename("Abdominal_wall.stl")
        detectingOverlapBlock_3.TargetStlFile = "Ureter.stl"
        detectingOverlapBlock_3.process()

        detectingOverlapBlock_4 = detectingOverlap.CDetectingOverlap()
        detectingOverlapBlock_4.InputPath = self.m_stlPath
        detectingOverlapBlock_4.OutputPath = self.m_stlPath
        detectingOverlapBlock_4.OutputJsonPath = outputOverlapJson4
        detectingOverlapBlock_4.add_src_stl_filename("Abdominal_wall.stl")
        detectingOverlapBlock_4.TargetStlFile = "Gonadal_vein.stl"
        detectingOverlapBlock_4.process()

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




