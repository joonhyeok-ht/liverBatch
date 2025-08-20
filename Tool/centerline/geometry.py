import sys
import os
import numpy as np
import vtk

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileToolPath = os.path.dirname(fileAbsPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algSkeletonGraph as algSkeletonGraph


class CGeometry :
    def __init__(self) :
        self.m_vertex = None
    def clear(self) :
        self.m_vertex = None


    def transform(self, mat : np.ndarray) :
        self.m_vertex = algLinearMath.CScoMath.mul_mat4_vec3(mat, self.m_vertex)

    
    @property
    def Vertex(self) -> np.ndarray :
        return self.m_vertex


class CCircle(CGeometry) :
    '''
    desc
    - 원점을 중심으로 -radius ~ +radius 만큼 circle 생성
    - x-y 평면으로 circle이 생성되며, z는 0.0이다.
    '''

    @staticmethod
    def generate_circle_vertices(radius, vertexCnt : int) -> np.array :
        npCirclePoints = []

        for i in range(vertexCnt):
            theta = 2 * np.pi * i / vertexCnt
            x = radius * np.cos(theta)
            y = radius * np.sin(theta)
            z = 0
            
            npCirclePoints.append([x, y, z])

        return np.array(npCirclePoints)


    def __init__(self, radius : float, vertexCnt : int) :
        super().__init__()
        self.m_vertex = CCircle.generate_circle_vertices(radius, vertexCnt)
        self.m_radius = radius
    def clear(self) :
        self.m_vertex = None
        self.m_radius = 0.0
        super().clear()

    
    @property
    def Radius(self) -> float :
        return self.m_radius



class CGrid(CGeometry) :
    '''
    desc
    - 원점을 중심으로 -radius ~ +radius 만큼 격자 생성
    - x-y 평면으로 격자가 생성되며, z는 0.0 이다.
    - 격자를 구성하는 vertex 갯수는 xCnt * yCnt 이다.
    '''
    def __init__(self, radius : float, xCnt : int, yCnt : int) :
        super().__init__()
        xCoord = np.linspace(-radius, radius, xCnt)
        yCoord = np.linspace(-radius, radius, yCnt)

        xv, yv = np.meshgrid(xCoord, yCoord)
        zv = np.zeros_like(xv)

        self.m_vertex = np.stack([xv.ravel(), yv.ravel(), zv.ravel()], axis=1)
        self.m_xCnt = xCnt
        self.m_yCnt = yCnt
        self.m_radius = radius
    def clear(self) :
        self.m_vertex = None
        self.m_xCnt = 0
        self.m_yCnt = 0
        self.m_radius = 0.0
        super().clear()

    
    @property
    def Radius(self) -> float :
        return self.m_radius
    @property
    def XCnt(self) -> int :
        return self.m_xCnt
    @property
    def YCnt(self) -> int :
        return self.m_yCnt



if __name__ == '__main__' :
    pass


# print ("ok ..")

