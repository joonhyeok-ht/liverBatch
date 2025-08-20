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


class CVTKObjRadius(vtkObjInterface.CVTKObjInterface) :
    def __init__(self) -> None:
        super().__init__()
        # input your code
        self.m_keyType = "radius"
        self.PolyData = None
        self.Ready = False
    def clear(self) :
        # input your code
        self.m_cl = None
        self.m_vertexIndex = -1
        self.Ready = False
        super().clear()
    
    def set_cl(self, cl : algSkeletonGraph.CSkeletonCenterline, vertexIndex : int, color : np.ndarray) :
        self.m_cl = cl
        self.m_vertexIndex = vertexIndex
        self.PolyData = algVTK.CVTK.create_poly_data_sphere(self.m_cl.get_vertex(self.m_vertexIndex), self.m_cl.get_radius(self.m_vertexIndex))
        self.Color = color
        self.Ready = True

if __name__ == '__main__' :
    pass


# print ("ok ..")

