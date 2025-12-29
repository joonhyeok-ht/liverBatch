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


class CVTKObjGuideVertex(vtkObjInterface.CVTKObjInterface) :
    def __init__(self, cl : algSkeletonGraph.CSkeletonCenterline, anchorPt : np.ndarray, range : int) -> None:
        super().__init__()
        # input your code
        self.m_cl = cl
        self.m_anchorPt = anchorPt.copy()
        self.m_range = range
        self.m_bReverse = False
        
        self.m_vertex = None
        self.m_modifiedVertex = None
        self.m_index = None
        self.m_minInx = -1
        
        # self.m_index = algVTK.CVTK.make_line_strip_index(self.m_vertex.shape[0])
        # self.PolyData = algVTK.CVTK.create_poly_data_line(self.m_vertex, self.m_index)
        
        self._update_range()
    def clear(self) :
        # input your code
        self.m_cl = None
        self.m_anchorPt = None
        self.m_range = 0
        self.m_bReverse = False

        self.m_vertex = None
        self.m_modifiedVertex = None
        self.m_index = None
        self.m_minInx = -1
        super().clear()
    # def process(self, moveVec : np.ndarray, weightDecay = 0.5) : 
    #     self.m_anchorPt = moveVec.copy()
    #     endPointMove = moveVec - self.m_vertex[-1]
    #     iCnt = self.m_vertex.shape[0]
    #     endPointMove = endPointMove.reshape(-1)

    #     for inx in range(0, iCnt) :
    #         weight = weightDecay ** (iCnt - inx - 1)
    #         self.m_vertex[inx] += endPointMove * weight
        
    #     points = self.PolyData.GetPoints()
    #     for i, vertex in enumerate(self.m_vertex) :
    #         points.SetPoint(i, vertex)
    #     points.Modified()
    '''
    # 이게 가장 나아 보임 
    '''
    # def process(self, moveVec: np.ndarray, weightDecay=0.9) :
    #     self.m_anchorPt = moveVec.copy()
    #     endPointMove = moveVec - self.m_vertex[-1]
    #     iCnt = self.m_vertex.shape[0]
    #     # iCnt = self.m_vertex.shape[0] - 1
    #     endPointMove = endPointMove.reshape(-1)

    #     for inx in range(iCnt):
    #         # weight = (inx / (iCnt - 1)) ** 2
    #         weight = (inx / (iCnt - 1))
    #         self.m_vertex[inx] += endPointMove * weight * weightDecay
    #     # 마지막 원소는 branch point를 세팅한다. 
    #     self.m_vertex[-1] = moveVec.reshape(-1).copy()

    #     points = self.PolyData.GetPoints()
    #     for i, vertex in enumerate(self.m_vertex):
    #         points.SetPoint(i, vertex)
    #     points.Modified()
    def process(self, newEndPoint : np.ndarray) :
        
        
        if self.m_vertex is None or len(self.m_vertex) < 2:
            return

        # 선분(2점)만 있는 경우: 시작점 고정(0), 끝점만 이동(1)
        if len(self.m_vertex) == 2:
            weights = np.array([0.0, 1.0], dtype=np.float64)

        movingVec = (newEndPoint.reshape(1, 3) - self.m_vertex[-1].reshape(1, 3))
        self.m_modifiedVertex = self.m_vertex.copy()

        for i in range(len(self.m_vertex)):
            self.m_modifiedVertex[i] = self.m_vertex[i] + (movingVec * weights[i]).reshape(-1)

        # PolyData 좌표 갱신
        points = self.PolyData.GetPoints()
        for i, vertex in enumerate(self.m_modifiedVertex):
            points.SetPoint(i, vertex.reshape(-1))
        points.Modified()
        self.PolyData.Modified()
    
        
    def set_line_width(self, width : float) :
        self.m_actor.GetProperty().SetLineWidth(width)
        self.m_width = width


    # protected
    def _update_range(self) :
        self.m_vertex = np.array([self.m_anchorPt, self.m_anchorPt], dtype=np.float64)
        self.m_modifiedVertex = self.m_vertex.copy()

        points = vtk.vtkPoints()
        points.SetNumberOfPoints(2)
        points.SetPoint(0, *self.m_vertex[0])
        points.SetPoint(1, *self.m_vertex[1])

        line = vtk.vtkLine()
        line.GetPointIds().SetId(0, 0)
        line.GetPointIds().SetId(1, 1)

        cells = vtk.vtkCellArray()
        cells.InsertNextCell(line)
        
        self.PolyData = vtk.vtkPolyData()

        self.PolyData.SetPoints(points)
        self.PolyData.SetLines(cells)
        self.PolyData.Modified()
    
    def _find_first_vertex_outside_radius(self, npVertex : np.ndarray, anchorPt : np.ndarray, radius : int) -> int :
        for i in range(len(npVertex) - 1, -1, -1) :
            dist = np.linalg.norm(npVertex[i].reshape(-1, 3) - anchorPt, axis=1)
            if dist > radius:
                return i
        return -1


    @property
    def CL(self) -> algSkeletonGraph.CSkeletonCenterline :
        return self.m_cl
    @property
    def Reverse(self) -> bool :
        return self.m_bReverse 
    @property
    def ModifiedVertex(self) -> np.ndarray :
        return self.m_modifiedVertex
    @property
    def MinInx(self) -> int :
        return self.m_minInx
    @property
    def Range(self) -> int :
        return self.m_range
    @Range.setter
    def Range(self, range : int) :
        self.m_range = range
        self._update_range()

    




if __name__ == '__main__' :
    pass


# print ("ok ..")

