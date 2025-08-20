import sys
import os
import numpy as np
import vtk

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget
from PySide6.QtCore import Qt
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileToolPath = os.path.dirname(fileAbsPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algSkeletonGraph as algSkeletonGraph

import VtkObj.vtkObj as vtkObj
import VtkObj.vtkObjLine as vtkObjLine
import VtkObj.vtkObjSphere as vtkObjSphere
import VtkObj.vtkObjPolyData as vtkObjPolyData

import VtkUI.vtkUI as vtkUI
import vtkObjInterface as vtkObjInterface


class CVTKObjGuideCLBound(vtkObjInterface.CVTKObjInterface) :
    def __init__(self, skeleton : algSkeletonGraph.CSkeleton, margin : float = 1.0, targetCLName : str = "") -> None:
        super().__init__()
        # input your code
        self.m_keyType = "branch"
        self.m_skeleton = skeleton
        self.m_margin = margin
        self.m_targetCLName = targetCLName
        self.m_min = None
        self.m_max = None
        self.m_size = None

        self._update_polydata(margin)
    def clear(self) :
        # input your code
        self.m_min = None
        self.m_max = None
        self.m_size = None
        self.m_targetPolyData = None
        self.m_margin = 0.0
        super().clear()


    def _update_polydata(self, newMargin) :
        vertex = None

        iCnt = self.Skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = self.Skeleton.get_centerline(inx)
            if cl.Name == self.TargetCLName :
                if vertex is None :
                    vertex = cl.Vertex.copy()
                else :
                    vertex = np.concatenate((vertex, cl.Vertex), axis=0)
        if vertex is None :
            self.Ready = False
            return
        
        minV = algLinearMath.CScoMath.get_min_vec3(vertex)
        maxV = algLinearMath.CScoMath.get_max_vec3(vertex)
        minV -= newMargin
        maxV += newMargin

        cubeSource = vtk.vtkCubeSource()
        centerX = (minV[0, 0] + maxV[0, 0]) / 2.0
        centerY = (minV[0, 1] + maxV[0, 1]) / 2.0
        centerZ = (minV[0, 2] + maxV[0, 2]) / 2.0
        cubeSource.SetCenter(centerX, centerY, centerZ)

        xSize = maxV[0, 0] - minV[0, 0]
        ySize = maxV[0, 1] - minV[0, 1]
        zSize = maxV[0, 2] - minV[0, 2]
        cubeSource.SetXLength(xSize)
        cubeSource.SetYLength(ySize)
        cubeSource.SetZLength(zSize)

        cubeSource.Update()
        self.PolyData = cubeSource.GetOutput()

        self.m_min = minV
        self.m_max = maxV
        self.m_size = [xSize, ySize, zSize]

        self.Ready = True
    

    @property
    def Skeleton(self) -> algSkeletonGraph.CSkeleton :
        return self.m_skeleton
    @property
    def Margin(self) -> float :
        return self.m_margin
    @Margin.setter
    def Margin(self, margin : float) :
        self.m_margin = margin
        self._update_polydata(margin)
    @property
    def TargetCLName(self) -> float :
        return self.m_targetCLName
    @TargetCLName.setter
    def TargetCLName(self, clName : str) :
        self.m_targetCLName = clName
        self._update_polydata(self.m_margin)
    @property
    def Min(self) -> np.ndarray :
        return self.m_min
    @property
    def Max(self) -> np.ndarray :
        return self.m_max
    @property
    def Size(self) -> list :
        return self.m_size



if __name__ == '__main__' :
    pass


# print ("ok ..")

