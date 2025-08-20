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


class CVTKObjInterface(vtkObj.CVTKObj) :
    def __init__(self) -> None:
        super().__init__()
        # input your code
        self.m_polyData = None
        self.m_bReady = False
    def clear(self) :
        # input your code
        # if self.m_polyData is not None :
        #     self.PolyData.Initialize()
        self.m_polyData = None
        self.m_bReady = False
        super().clear()

    
    @property
    def PolyData(self) -> vtk.vtkPolyData :
        return self.m_polyData
    @PolyData.setter
    def PolyData(self, polyData : vtk.vtkPolyData) :
        self.m_polyData = polyData
        self.m_mapper.SetInputData(self.m_polyData)
    @property
    def Ready(self) -> bool :
        return self.m_bReady
    @Ready.setter
    def Ready(self, bReady : bool) :
        self.m_bReady = bReady
    

if __name__ == '__main__' :
    pass


# print ("ok ..")

