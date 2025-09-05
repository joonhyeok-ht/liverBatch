import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileStatePath = os.path.dirname(fileAbsPath)
fileAppPath = os.path.dirname(fileStatePath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileStatePath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algSkeletonGraph as algSkeletonGraph

import VtkObj.vtkObjLine as vtkObjLine
import VtkObj.vtkObjSphere as vtkObjSphere

import vtkObjGuideCL as vtkObjGuideCL

import data as data

import operation as operation


class CCLMask :
    def __init__(self, polyData : vtk.vtkPolyData):
        self.m_polyData = polyData
        self.m_dicTable = {}

        self.m_selEnPt = vtk.vtkSelectEnclosedPoints()
        self.m_selEnPt.SetSurfaceData(polyData)
    def clear(self) :
        self.m_polyData = None
        self.m_dicTable.clear()
    def attach_cl(self, cl : algSkeletonGraph.CSkeletonCenterline) :
        retList = []
        testPt = vtk.vtkPoints()

        iCnt = cl.get_vertex_count()
        for inx in range(0, iCnt) :
            vertex = cl.get_vertex(inx)
            testPt.InsertNextPoint(vertex[0, 0], vertex[0, 1], vertex[0, 2])
        testPolyData = vtk.vtkPolyData()
        testPolyData.SetPoints(testPt)
        
        self.m_selEnPt.SetInputData(testPolyData)
        self.m_selEnPt.Update()

        for i in range(testPt.GetNumberOfPoints()) :
            bInside = self.m_selEnPt.IsInside(i)
            # retList.append(bInside == 1)
            retList.append(cl.Name != '' and bInside == 1)  #sally: labeling이 안돼 있거나 lobe의 바깥쪽에 있는 centerline point는 territory 계산에서 제외하기 위한 전처리. 화면에서 빨간점으로 표시됨.
        self.m_dicTable[cl.ID] = retList
    def get_flag(self, cl : algSkeletonGraph.CSkeletonCenterline, inx : int) -> bool :
        if cl.ID in self.m_dicTable :
            return self.m_dicTable[cl.ID][inx]
        return False

if __name__ == '__main__' :
    pass


# print ("ok ..")

