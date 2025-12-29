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


class CVTKObjGuideMeshBound(vtkObjInterface.CVTKObjInterface) :
    def __init__(self, polyData : vtk.vtkPolyData, margin : float = 1.0, limitMin : np.ndarray = None, limitMax : np.ndarray = None) -> None:
        super().__init__()
        # input your code
        self.m_keyType = "branch"
        self.m_margin = margin
        self.m_targetPolyData = polyData
        self.m_min = None
        self.m_max = None
        self.m_size = None
        self.m_limitMin = limitMin
        self.m_limitMax = limitMax

        self._update_polydata(margin)

        self.Ready = True
    def clear(self) :
        # input your code
        self.m_min = None
        self.m_max = None
        self.m_size = None
        self.m_targetPolyData = None
        self.m_margin = 0.0
        self.m_limitMin = None
        self.m_limitMax = None
        super().clear()


    def _update_polydata(self, newMargin) :
        xMin, xMax, yMin, yMax, zMin, zMax = self.m_targetPolyData.GetBounds()
        xMin -= newMargin
        xMax += newMargin
        yMin -= newMargin
        yMax += newMargin
        zMin -= newMargin
        zMax += newMargin

        if self.m_limitMin is not None :
            if xMin < self.m_limitMin[0, 0] : 
                xMin = self.m_limitMin[0, 0]
            if yMin < self.m_limitMin[0, 1] : 
                yMin = self.m_limitMin[0, 1]
            if zMin < self.m_limitMin[0, 2] : 
                zMin = self.m_limitMin[0, 2]
        if self.m_limitMax is not None :
            if xMax > self.m_limitMax[0, 0] : 
                xMax = self.m_limitMax[0, 0]
            if yMax > self.m_limitMax[0, 1] : 
                yMax = self.m_limitMax[0, 1]
            if zMax > self.m_limitMax[0, 2] : 
                zMax = self.m_limitMax[0, 2]

        cubeSource = vtk.vtkCubeSource()
        centerX = (xMin + xMax) / 2.0
        centerY = (yMin + yMax) / 2.0
        centerZ = (zMin + zMax) / 2.0
        cubeSource.SetCenter(centerX, centerY, centerZ)

        xSize = xMax - xMin
        ySize = yMax - yMin
        zSize = zMax - zMin
        cubeSource.SetXLength(xSize)
        cubeSource.SetYLength(ySize)
        cubeSource.SetZLength(zSize)

        cubeSource.Update()
        self.PolyData = cubeSource.GetOutput()

        self.m_min = algLinearMath.CScoMath.to_vec3([xMin, yMin, zMin])
        self.m_max = algLinearMath.CScoMath.to_vec3([xMax, yMax, zMax])
        self.m_size = [xSize, ySize, zSize]
    

    @property
    def Margin(self) -> float :
        return self.m_margin
    @Margin.setter
    def Margin(self, margin : float) :
        self.m_margin = margin
        self._update_polydata(margin)
    @property
    def TargetPolyData(self) -> vtk.vtkPolyData :
        return self.m_targetPolyData
    @TargetPolyData.setter
    def TargetPolyData(self, targetPolyData : vtk.vtkPolyData) :
        self.m_targetPolyData = targetPolyData
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

