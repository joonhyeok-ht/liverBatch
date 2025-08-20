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


class CVTKObjGuideEP(vtkObjInterface.CVTKObjInterface) :
    def __init__(self, cl : algSkeletonGraph.CSkeletonCenterline, epSize : float) -> None:
        super().__init__()
        # input your code
        self.m_keyType = "branch"
        self.m_cl = cl

        self.PolyData = algVTK.CVTK.create_poly_data_sphere(algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0]), epSize)
        self.Pos = cl.get_end_point()
        self.Ready = True

    def clear(self) :
        # input your code
        self.m_cl = None
        super().clear()
    

    @property
    def CL(self) -> algSkeletonGraph.CSkeletonCenterline :
        return self.m_cl

    




if __name__ == '__main__' :
    pass


# print ("ok ..")

