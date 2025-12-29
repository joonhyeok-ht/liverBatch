import sys
import os
import numpy as np
import json
import vtk
from vtkmodules.util import numpy_support

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
solutionPath = os.path.dirname(fileAbsPath)
sys.path.append(fileAbsPath)
sys.path.append(solutionPath)

import AlgUtil.algVTK as algVTK
import AlgUtil.algMeshLib as algMeshLib

import optionInfo as optionInfo
   


class CMeshBoolean() :
    @staticmethod
    def get_meshlib(vtkMeshInst : vtk.vtkPolyData) :
        npVertex = algVTK.CVTK.poly_data_get_vertex(vtkMeshInst)
        npIndex = algVTK.CVTK.poly_data_get_triangle_index(vtkMeshInst)
        meshLibInst = algMeshLib.CMeshLib.meshlib_create(npVertex, npIndex)
        return meshLibInst
    @staticmethod
    def get_vtkmesh(meshlibInst) -> vtk.vtkPolyData :
        npVertex = algMeshLib.CMeshLib.meshlib_get_vertex(meshlibInst)
        npIndex = algMeshLib.CMeshLib.meshlib_get_index(meshlibInst)
        vtkMesh = algVTK.CVTK.create_poly_data_triangle(npVertex, npIndex)
        return vtkMesh
    

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
            print("not found mesh boolean list")
            return
        
        for inx in range(0, iBooleanCnt) :
            operator, blenderName0, blenderName1, outBlenderName = self.InputOptionInfo.get_mesh_boolean(inx)

            stlFullPath0 = os.path.join(self.InputPath, f"{blenderName0}.stl")
            stlFullPath1 = os.path.join(self.InputPath, f"{blenderName1}.stl")
            outStlFullPath = os.path.join(self.InputPath, f"{outBlenderName}.stl")

            if os.path.exists(stlFullPath0) == False :
                print(f"not found stl file 0  : {blenderName0}")
                continue
            if os.path.exists(stlFullPath1) == False :
                print(f"not found stl file 1  : {blenderName0}")
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

            algMeshLib.CMeshLib.meshlib_save_stl(outStlFullPath, retMesh)
            print(f"completed boolean : {blenderName0} {operator} {blenderName1} --> {outBlenderName}")


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

