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


class CVTKObjGuideRange(vtkObjInterface.CVTKObjInterface) :
    def __init__(self, pt : np.ndarray, range : float = 2.0) -> None:
        super().__init__()
        # input your code
        self.m_keyType = "branch"
        self.m_range = range

        self.PolyData = algVTK.CVTK.create_poly_data_sphere(algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0]), range)
        self.Pos = pt.copy()
        self.Ready = True

    def clear(self) :
        # input your code
        self.m_range = 2.0
        super().clear()
    

    @property
    def Range(self) -> float :
        return self.m_range
    @Range.setter
    def Range(self, range : float) :
        self.m_range = range
        self.PolyData = algVTK.CVTK.create_poly_data_sphere(algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0]), range)


    




if __name__ == '__main__' :
    pass


# print ("ok ..")

