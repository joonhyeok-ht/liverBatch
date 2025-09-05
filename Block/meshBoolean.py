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
   


class CMeshBoolean() :
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
            print("Mesh Boolean : not setting input path")
            return 
        if self.InputOptionInfo is None :
            print("Mesh Boolean : not setting input option info")
            return 
        
        iBooleanCnt = self.InputOptionInfo.get_mesh_boolean_count()
        if iBooleanCnt == 0 :
            #print("not found mesh boolean list")
            return
        
        for inx in range(0, iBooleanCnt) :
            meshBoolean = self.InputOptionInfo.get_mesh_boolean(inx)
            operator = meshBoolean.Operator
            blenderName0 = meshBoolean.BlenderName0
            blenderName1 = meshBoolean.BlenderName1
            fillHole = meshBoolean.FillHole
            blenderName = meshBoolean.BlenderName

            stlFullPath0 = os.path.join(self.InputPath, f"{blenderName0}.stl")
            stlFullPath1 = os.path.join(self.InputPath, f"{blenderName1}.stl")
            stlFullPath = os.path.join(self.InputPath, f"{blenderName}.stl")

            if os.path.exists(stlFullPath0) == False :
                #print(f"not found stl file 0  : {blenderName0}")
                continue
            if os.path.exists(stlFullPath1) == False :
                #print(f"not found stl file 1  : {blenderName0}")
                continue

            mesh0 = algMeshLib.CMeshLib.meshlib_load_stl(stlFullPath0)
            mesh1 = algMeshLib.CMeshLib.meshlib_load_stl(stlFullPath1)
            retMesh = None

            if operator == "subtraction" :
                retMesh = algMeshLib.CMeshLib.meshlib_boolean_subtraction(mesh0, mesh1)
            elif operator == "intersection" :
                retMesh = algMeshLib.CMeshLib.meshlib_boolean_intersection(mesh0, mesh1)
            elif operator == "union" :
                retMesh = algMeshLib.CMeshLib.meshlib_boolean_union(mesh0, mesh1)
            elif operator == "inside" :
                retMesh = algMeshLib.CMeshLib.meshlib_boolean_inside(mesh0, mesh1)
            elif operator == "outside" :
                retMesh = algMeshLib.CMeshLib.meshlib_boolean_outside(mesh0, mesh1)
            else :
                print(f"Invalide Operator : {operator}")
                continue

            if fillHole == 1 :
                retMesh = algMeshLib.CMeshLib.meshlib_fill_hole(retMesh)

            algMeshLib.CMeshLib.meshlib_save_stl(stlFullPath, retMesh)
            print(f"completed boolean : {blenderName0} {operator} {blenderName1} --> {blenderName}")


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

