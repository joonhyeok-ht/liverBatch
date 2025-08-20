import sys
import os
import numpy as np
import json

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
solutionPath = os.path.dirname(fileAbsPath)
sys.path.append(fileAbsPath)
sys.path.append(solutionPath)

import AlgUtil.algMeshLib as algMeshLib

import optionInfo as optionInfo
   


class CMeshHealing() :
    def __init__(self) -> None:
        # input your code 
        self.m_inputPath = ""
        self.m_inputOptionInfo = None
    def clear(self) :
        # input your code
        self.m_inputPath = ""
        self.m_inputOptionInfo = None
    def process(self) :
        if self.InputPath == "" :
            print("Mesh Healing : not setting input path")
            return 
        if self.InputOptionInfo is None :
            print("Mesh Healing : not setting input option info")
            return 
        
        iHealingCnt = self.InputOptionInfo.get_mesh_healing_count()
        if iHealingCnt == 0 :
            print("not found mesh healing list")
            return
        
        for inx in range(0, iHealingCnt) :
            stlName = self.InputOptionInfo.get_mesh_healing(inx)
            stlFullPath = os.path.join(self.InputPath, f"{stlName}.stl")

            if os.path.exists(stlFullPath) == False :
                print(f"not found stl file : {stlName}")
                continue

            mesh = algMeshLib.CMeshLib.meshlib_load_stl(stlFullPath)
            mesh = algMeshLib.CMeshLib.meshlib_healing(mesh)
            algMeshLib.CMeshLib.meshlib_save_stl(stlFullPath, mesh)

            print(f"completed healing : {stlName}")


    @property
    def InputPath(self) -> str :
        return self.m_inputPath
    @InputPath.setter
    def InputPath(self, inputPath : str) :
        self.m_inputPath = inputPath
    @property
    def InputOptionInfo(self) -> optionInfo.COptionInfo :
        return self.m_inputOptionInfo
    @InputOptionInfo.setter
    def InputOptionInfo(self, optionInfo : optionInfo.COptionInfo) :
        self.m_inputOptionInfo = optionInfo




if __name__ == '__main__' :
    pass


# print ("ok ..")

