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
                
                
        outputOverlapJson0 = os.path.join(self.m_logPath, "artery_vein.json")
        outputOverlapJson1 = os.path.join(self.m_logPath, "extraArtery_vein.json")
        outputOverlapJson2 = os.path.join(self.m_logPath, "extraVein_artery.json")
        outputOverlapJson3 = os.path.join(self.m_logPath, "spleen.json")
        outputOverlapJson4 = os.path.join(self.m_logPath, "stomach.json")
        outputOverlapJson5 = os.path.join(self.m_logPath, "liver.json")
        outputOverlapJson6 = os.path.join(self.m_logPath, "gb.json")
        outputOverlapJson7 = os.path.join(self.m_logPath, "pancreas.json")
        
        
        
        # DetectingOverlapBlock_0
        detectingOverlapBlock = detectingOverlap.CDetectingOverlap()
        detectingOverlapBlock.InputPath = self.m_stlPath
        detectingOverlapBlock.OutputPath = self.m_stlPath
        detectingOverlapBlock.OutputJsonPath = outputOverlapJson0
        detectingOverlapBlock.add_src_stl_filename("anatomy_all_allartery.stl")
        detectingOverlapBlock.TargetStlFile = "anatomy_all_allvein.stl"
        detectingOverlapBlock.process()
        
        # DetectingOverlapBlock_1
        detectingOverlapBlock_1 = detectingOverlap.CDetectingOverlap()
        detectingOverlapBlock_1.InputPath = self.m_stlPath
        detectingOverlapBlock_1.OutputPath = self.m_stlPath
        detectingOverlapBlock_1.OutputJsonPath = outputOverlapJson1
        detectingOverlapBlock_1.add_src_stl_filename("anatomy_artery_00_EXTRA_ARTERY.stl")
        detectingOverlapBlock_1.TargetStlFile = "anatomy_all_allvein.stl"
        detectingOverlapBlock_1.process()

        # DetectingOverlapBlock_2
        detectingOverlapBlock_2 = detectingOverlap.CDetectingOverlap()
        detectingOverlapBlock_2.InputPath = self.m_stlPath
        detectingOverlapBlock_2.OutputPath = self.m_stlPath
        detectingOverlapBlock_2.OutputJsonPath = outputOverlapJson2
        detectingOverlapBlock_2.add_src_stl_filename("anatomy_vein_01_EXTRA_VEIN.stl")
        detectingOverlapBlock_2.TargetStlFile = "anatomy_all_allartery.stl"
        detectingOverlapBlock_2.process()
               

        # DetectingOverlapBlock_3
        detectingOverlapBlock_3 = detectingOverlap.CDetectingOverlap()
        detectingOverlapBlock_3.InputPath = self.m_stlPath
        detectingOverlapBlock_3.OutputPath = self.m_stlPath
        detectingOverlapBlock_3.OutputJsonPath = outputOverlapJson3
        detectingOverlapBlock_3.add_src_stl_filename("anatomy_artery_15_SGA.stl")
        detectingOverlapBlock_3.add_src_stl_filename("anatomy_artery_27_PGA.stl")
        detectingOverlapBlock_3.add_src_stl_filename("anatomy_artery_08_LGEA.stl")
        detectingOverlapBlock_3.add_src_stl_filename("anatomy_vein_07_LGEV.stl")
        detectingOverlapBlock_3.add_src_stl_filename("anatomy_artery_36_OmentalBr.stl")
        detectingOverlapBlock_3.add_src_stl_filename("anatomy_artery_00_EXTRA_ARTERY.stl")
        detectingOverlapBlock_3.add_src_stl_filename("anatomy_vein_01_EXTRA_VEIN.stl")
        detectingOverlapBlock_3.TargetStlFile = "anatomy_spleen.stl"
        detectingOverlapBlock_3.process()

        # DetectingOverlapBlock_4
        detectingOverlapBlock_4 = detectingOverlap.CDetectingOverlap()
        detectingOverlapBlock_4.InputPath = self.m_stlPath
        detectingOverlapBlock_4.OutputPath = self.m_stlPath
        detectingOverlapBlock_4.OutputJsonPath = outputOverlapJson4
        detectingOverlapBlock_4.add_src_stl_filename("anatomy_all_allartery.stl")
        detectingOverlapBlock_4.add_src_stl_filename("anatomy_all_allvein.stl")
        detectingOverlapBlock_4.add_src_stl_filename("anatomy_artery_00_EXTRA_ARTERY.stl")
        detectingOverlapBlock_4.add_src_stl_filename("anatomy_vein_01_EXTRA_VEIN.stl")
        detectingOverlapBlock_4.TargetStlFile = "anatomy_stomach.stl"
        detectingOverlapBlock_4.process()

        # DetectingOverlapBlock_5
        detectingOverlapBlock_5 = detectingOverlap.CDetectingOverlap()
        detectingOverlapBlock_5.InputPath = self.m_stlPath
        detectingOverlapBlock_5.OutputPath = self.m_stlPath
        detectingOverlapBlock_5.OutputJsonPath = outputOverlapJson5
        detectingOverlapBlock_5.add_src_stl_filename("anatomy_artery_07_LGA.stl")
        detectingOverlapBlock_5.add_src_stl_filename("anatomy_vein_08_LGV.stl")
        detectingOverlapBlock_5.add_src_stl_filename("anatomy_artery_11_RGA.stl")
        detectingOverlapBlock_5.add_src_stl_filename("anatomy_vein_17_RGV.stl")
        detectingOverlapBlock_5.TargetStlFile = "anatomy_liver.stl"
        detectingOverlapBlock_5.process()

        # DetectingOverlapBlock_6
        detectingOverlapBlock_6 = detectingOverlap.CDetectingOverlap()
        detectingOverlapBlock_6.InputPath = self.m_stlPath
        detectingOverlapBlock_6.OutputPath = self.m_stlPath
        detectingOverlapBlock_6.OutputJsonPath = outputOverlapJson6
        detectingOverlapBlock_6.add_src_stl_filename("anatomy_all_allartery.stl")
        detectingOverlapBlock_6.add_src_stl_filename("anatomy_all_allvein.stl")
        detectingOverlapBlock_6.add_src_stl_filename("anatomy_artery_00_EXTRA_ARTERY.stl")
        detectingOverlapBlock_6.add_src_stl_filename("anatomy_vein_01_EXTRA_VEIN.stl")
        detectingOverlapBlock_6.TargetStlFile = "anatomy_gallbladder.stl"
        detectingOverlapBlock_6.process()

        # DetectingOverlapBlock_7
        detectingOverlapBlock_7 = detectingOverlap.CDetectingOverlap()
        detectingOverlapBlock_7.InputPath = self.m_stlPath
        detectingOverlapBlock_7.OutputPath = self.m_stlPath
        detectingOverlapBlock_7.OutputJsonPath = outputOverlapJson7
        detectingOverlapBlock_7.add_src_stl_filename("anatomy_artery_00_EXTRA_ARTERY.stl")
        detectingOverlapBlock_7.TargetStlFile = "anatomy_pancreas.stl"
        detectingOverlapBlock_7.process()
               
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




