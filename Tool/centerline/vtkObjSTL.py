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

import Block.optionInfo as optionInfo

import VtkObj.vtkObj as vtkObj
import VtkObj.vtkObjLine as vtkObjLine
import VtkObj.vtkObjSphere as vtkObjSphere
import VtkObj.vtkObjPolyData as vtkObjPolyData

import VtkUI.vtkUI as vtkUI
import vtkObjInterface as vtkObjInterface


class CVTKObjSTL(vtkObjInterface.CVTKObjInterface) :
    def __init__(self, optionInfoInst : optionInfo.COptionInfo, stlFullPath : str) -> None:
        super().__init__()
        # input your code
        self.m_keyType = "stl"
        self.m_optionInfo = optionInfoInst

        if os.path.exists(stlFullPath) == False :
            print(f"failed to stl : {stlFullPath}")
            return
        
        self.m_fileName = os.path.splitext(os.path.basename(stlFullPath))[0]

        self.PolyData = algVTK.CVTK.load_poly_data_stl(stlFullPath)
        self.Ready = True

        if self.m_optionInfo is None :
            return
        
    def clear(self) :
        # input your code
        self.m_optionInfo = None
        self.m_fileName = ""
        super().clear()

    
    @property
    def FileName(self) -> str :
        return self.m_fileName
    @property
    def OptionInfo(self) -> optionInfo.COptionInfo :
        return self.m_optionInfo




if __name__ == '__main__' :
    pass


# print ("ok ..")

