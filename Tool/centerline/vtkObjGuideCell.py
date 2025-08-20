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


class CVTKObjGuideCell(vtkObjInterface.CVTKObjInterface) :
    def __init__(self) -> None:
        super().__init__()
        # input your code
        self.m_keyType = "branch"

        self.PolyData = None
        self.Ready = False
    def clear(self) :
        # input your code
        super().clear()

    def set_cellid(self, polyData : vtk.vtkPolyData, cellID : int) :
        if polyData is None or cellID == -1 :
            self.PolyData = None
            self.Ready = False 
            return

        cell = polyData.GetCell(cellID)
        points = cell.GetPoints()

        newPoints = vtk.vtkPoints()
        dicPointID = {}
        for i in range(points.GetNumberOfPoints()):
            point = points.GetPoint(i)
            newID = newPoints.InsertNextPoint(point)
            dicPointID[i] = newID

        arrCell = vtk.vtkCellArray()
        newCell = vtk.vtkIdList()

        for i in range(cell.GetNumberOfPoints()):
            newCell.InsertNextId(dicPointID[i])
        
        arrCell.InsertNextCell(newCell)
        newPolyData = vtk.vtkPolyData()
        newPolyData.SetPoints(newPoints)
        newPolyData.SetPolys(arrCell)
        self.PolyData = newPolyData

        self.Ready = True



    




if __name__ == '__main__' :
    pass


# print ("ok ..")

