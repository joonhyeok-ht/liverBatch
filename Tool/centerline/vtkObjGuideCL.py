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


class CVTKObjGuideCL(vtkObjInterface.CVTKObjInterface) :
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
        
    #     points = self.m_polyData.GetPoints()
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

    #     points = self.m_polyData.GetPoints()
    #     for i, vertex in enumerate(self.m_vertex):
    #         points.SetPoint(i, vertex)
    #     points.Modified()
    def process(self, newEndPoint : np.ndarray, weightDecay=0.9) :
        npRet = np.diff(self.m_vertex, axis=0)
        npRet = np.linalg.norm(npRet, axis=1)
        npRet = npRet[ : : -1]
        npRet = np.cumsum(npRet)
        npRet = np.concatenate(([0], npRet))
        
        curveLen = npRet[-1]
        distFromEnd = curveLen - npRet
        maxDistFromEnd = distFromEnd.max()
        weights = 1.0 - (distFromEnd / maxDistFromEnd)

        movingVec = newEndPoint - self.m_vertex[-1].reshape(-1, 3)
        for i in range(len(self.m_vertex)):
            npTmp = (movingVec * weights[i]).reshape(-1)
            self.m_modifiedVertex[i] = self.m_vertex[i] + npTmp
        
        points = self.m_polyData.GetPoints()
        for i, vertex in enumerate(self.m_modifiedVertex):
            points.SetPoint(i, vertex)
        points.Modified()
        
    def set_line_width(self, width : float) :
        self.m_actor.GetProperty().SetLineWidth(width)
        self.m_width = width


    # protected
    def _update_range(self) :
        npVertex = None 
        # 끝점이 이동되어야 한다. 
        if self.m_cl.find_vertex_inx_by_vertex(self.m_anchorPt) == 0 :
            self.m_bReverse = True
            npVertex = self.m_cl.Vertex[ : : -1].copy()
        else :
            npVertex = self.m_cl.Vertex.copy()

        self.m_minInx = self._find_first_vertex_outside_radius(npVertex, self.m_anchorPt, self.m_range)
        # all point in radius
        if self.m_minInx == -1 :
            self.m_minInx = 1
        else :
            self.m_minInx += 1

        self.m_vertex = npVertex[self.m_minInx : ].copy()
        self.m_modifiedVertex = self.m_vertex.copy()
        self.m_index = algVTK.CVTK.make_line_strip_index(self.m_vertex.shape[0])
        self.PolyData = algVTK.CVTK.create_poly_data_line(self.m_vertex, self.m_index)
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

