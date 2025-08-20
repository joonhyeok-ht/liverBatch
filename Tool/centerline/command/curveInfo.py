import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget
from PySide6.QtCore import Qt
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAppPath = os.path.dirname(fileAbsPath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algSegment as algSegment

import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer
import Block.reconstruction as reconstruction

import data as data
import geometry as geometry

import commandInterface as commandInterface
# import territory as territory



class CCLCurve : 
    @staticmethod
    def compute_curvature_3d(points : np.ndarray) :
        """
        3D 곡선에서 곡률을 계산하는 함수
        :param points: N x 3 형태의 numpy 배열 (x, y, z 좌표)
        :return: 곡률 값 배열
        """
        dr = np.gradient(points, axis=0)
        d2r = np.gradient(dr, axis=0)

        cross_product = np.cross(dr, d2r)
        numerator = np.linalg.norm(cross_product, axis=1)
        denominator = np.linalg.norm(dr, axis=1) ** 3

        curvature = np.zeros(len(points))
        mask = denominator > 1e-8
        curvature[mask] = numerator[mask] / denominator[mask]

        return curvature
    @staticmethod
    def calc_coord_by_tangent(tangent : np.ndarray, prevUp : np.ndarray) -> tuple :
        '''
        ret : (xCoord, yCoord, zCoord), type : np.ndarray
        '''
        tangent = tangent.reshape(-1)
        prevUp = prevUp.reshape(-1)
        if np.abs(np.dot(tangent, prevUp)) > 0.99 :
            prevUp = np.array([0.0, 0.0, 1.0])
        
        binormal = np.cross(prevUp, tangent)
        binormal = binormal / np.linalg.norm(binormal)
        up = np.cross(tangent, binormal)

        return (binormal.reshape(-1, 3), up.reshape(-1, 3), tangent.reshape(-1, 3))
    @staticmethod
    def calc_mat(xCoord : np.ndarray, yCoord : np.ndarray, zCoord : np.ndarray, pos : np.ndarray) -> np.ndarray :
        mat = algLinearMath.CScoMath.rot_mat3_from_axis(xCoord, yCoord, zCoord)
        rotMat = algLinearMath.CScoMath.from_mat3_to_mat4(mat)
        transMat = algLinearMath.CScoMath.translation_mat4(pos)
        return algLinearMath.CScoMath.mul_mat4_mat4(transMat, rotMat)
    @staticmethod
    def calc_curve_coord(npVertexCurve : np.ndarray) -> tuple :
        '''
        ret : (xCoord, yCoord, zCoord)
        '''

        tangents = []
        normals = []
        binormals = []

        prevUp = np.array([0.0, 1.0, 0.0])

        for inx in range(0, len(npVertexCurve) - 1) :
            if inx == 0 :
                tangentV = (npVertexCurve[inx + 1] - npVertexCurve[inx])
                tangentV = tangentV / np.linalg.norm(tangentV)
                if np.abs(np.dot(tangentV, prevUp)) > 0.99 :
                    prevUp = np.array([0.0, 0.0, 1.0])
            else :
                tangentV = (npVertexCurve[inx + 1] - npVertexCurve[inx - 1])
                tangentV = tangentV / np.linalg.norm(tangentV)

            binormalV = np.cross(prevUp, tangentV)
            binormalV = binormalV / np.linalg.norm(binormalV)
            upV = np.cross(tangentV, binormalV)

            tangents.append(tangentV)
            binormals.append(binormalV)
            normals.append(upV)

            prevUp = upV.copy()
        
        tangents.append(tangents[-1])
        normals.append(normals[-1])
        binormals.append(binormals[-1])
        
        return (np.array(binormals), np.array(normals), np.array(tangents))
    

    def __init__(self, cl : algSkeletonGraph.CSkeletonCenterline) :
        self.m_cl = cl
        # self.m_npCurvature = CCLCurve.compute_curvature_3d(self.m_npVertexCurve)
        self.m_npXCoord, self.m_npYCoord, self.m_npZCoord = CCLCurve.calc_curve_coord(self.m_cl.Vertex)
    def clear(self) :
        self.m_cl = None
        self.m_npXCoord = None
        self.m_npYCoord = None
        self.m_npZCoord = None

    def get_transform(self, clPtInx : int) :
        mat = algLinearMath.CScoMath.rot_mat3_from_axis(
            self.m_npXCoord[clPtInx].reshape(-1, 3),
            self.m_npYCoord[clPtInx].reshape(-1, 3),
            self.m_npZCoord[clPtInx].reshape(-1, 3)
            )
        rotMat = algLinearMath.CScoMath.from_mat3_to_mat4(mat)
        transMat = algLinearMath.CScoMath.translation_mat4(self.m_cl.get_vertex(clPtInx))
        return algLinearMath.CScoMath.mul_mat4_mat4(transMat, rotMat)
    

    @property
    def CL(self) -> algSkeletonGraph.CSkeletonCenterline :
        return self.m_cl



class CCLCircle :
    def __init__(self, clCurve : CCLCurve, circleVertexCnt : int) :
        self.m_clCurve = clCurve
        self.m_listCircle = []

        cl = clCurve.CL

        for inx in range(0, cl.get_vertex_count()) :
            circle = geometry.CCircle(cl.get_radius(inx), circleVertexCnt)
            mat = clCurve.get_transform(inx)
            circle.transform(mat)
            self.m_listCircle.append(circle)
    def clear(self) :
        for circle in self.m_listCircle :
            circle.clear()
        self.m_listCircle.clear()
        self.m_clCurve = None

    def get_circle_count(self) -> int :
        return len(self.m_listCircle)
    def get_circle(self, inx : int) -> geometry.CCircle :
        return self.m_listCircle[inx]
    def get_range_circle_vertex(self, startInx : int, endInx : int) :
        retVertex = None 

        for inx in range(startInx, endInx + 1) :
            circle = self.get_circle(inx)
            if retVertex is None :
                retVertex = circle.m_vertex.copy()
            else :
                retVertex = np.concatenate((retVertex, circle.m_vertex), axis=0)
        return retVertex


    @property
    def Vertex(self) -> np.ndarray :
        retVertex = None 

        iCnt = self.get_circle_count()
        for inx in range(0, iCnt) :
            circle = self.get_circle(inx)
            if retVertex is None :
                retVertex = circle.m_vertex.copy()
            else :
                retVertex = np.concatenate((retVertex, circle.m_vertex), axis=0)
        return retVertex

    

class CSkelCircle :
    def __init__(self, skeleton : algSkeletonGraph.CSkeleton, circleVertexCnt : int) :
        self.m_listCurve = []
        self.m_listCircle = []

        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            clCurve = CCLCurve(cl)
            clCircle = CCLCircle(clCurve, circleVertexCnt)
            self.m_listCurve.append(clCurve)
            self.m_listCircle.append(clCircle)
    def clear(self) :
        self.m_listCircle.clear()
        self.m_listCircle.clear()

    
    def get_clinfo_count(self) -> int :
        return len(self.m_listCurve)
    def get_cl_curve(self, clID : int) -> CCLCurve :
        return self.m_listCurve[clID]
    def get_cl_circle(self, clID : int) -> CCLCircle :
        return self.m_listCircle[clID]





if __name__ == '__main__' :
    pass


# print ("ok ..")

