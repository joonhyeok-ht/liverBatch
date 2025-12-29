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
import clMask as clMask

import commandInterface as commandInterface
import curveInfo as curveInfo
# import territory as territory


    
class CCommandKnifeCL(commandInterface.CCommand) :
    def __init__(self, mediator) :
        '''
        desc
            - world 좌표계의 A, B, C로 구성된 Plane을 교차하는 centerline 반환
            - 교차되는 centerline은 AB 선분위에 놓여있게 된다. 
        input
            - InputSkeleton
            - InputWorldA
            - InputWorldB
            - InputWorldC : 반드시 camera pos 또는 시점 pos가 되어야 한다.
        output
            - OutputKnifedCLID : knife로 절단 된 CLID 
            - OutputKnifedIndex : 절단 된 CLID의 시작 vertex index
            - OutputTangent : 절단 면의 노멀벡터, 즉 절단 면의 방향
            - OutputIntersectedPt : 정밀한 교차점 
            - OutputInfo : list
                - [(knifedCLID, knifedIndex, tangent, OutputIntersectedPt), ..]
        '''

        super().__init__(mediator)
        # input your code
        self.m_inputSkeleton = None
        self.m_inputWorldA = None
        self.m_inputWorldB = None
        self.m_inputWorldC = None

        self.m_outputKnifedCLID = -1
        self.m_outputKnifedIndex = -1
        self.m_outputTangent = None
        self.m_outputIntersectedPt = None

        self.m_outputInfo = None
    def clear(self) :
        # input your code
        self.m_inputSkeleton = None
        self.m_inputWorldA = None
        self.m_inputWorldB = None
        self.m_inputWorldC = None

        self.m_outputKnifedCLID = -1
        self.m_outputKnifedIndex = -1
        self.m_outputTangent = None
        self.m_outputIntersectedPt = None

        if self.m_outputInfo is not None :
            self.m_outputInfo.clear()

        super().clear()
    def process(self) :
        super().process()

        if self.InputSkeleton is None :
            return
        if self.InputWorldA is None :
            return
        if self.InputWorldB is None :
            return
        if self.InputWorldC is None :
            return
        
        self.m_outputInfo = self._find_intersected_clID_by_plane(self.InputWorldA, self.InputWorldB, self.InputWorldC)
        if self.m_outputInfo is None :
            return
        nearestInx = self._find_nearest_inx()
        if nearestInx == -1 :
            self.m_outputInfo = None
            return
        
        self.m_outputKnifedCLID = self.m_outputInfo[nearestInx][0]
        self.m_outputKnifedIndex = self.m_outputInfo[nearestInx][1]
        self.m_outputTangent = self.m_outputInfo[nearestInx][2]
        self.m_outputIntersectedPt = self.m_outputInfo[nearestInx][3]
        

    # protected
    def _find_nearest_inx(self) -> int :
        if self.m_outputInfo is None :
            return -1
        
        iCnt = len(self.m_outputInfo)
        if iCnt == 0 :
            return -1
        if iCnt == 1 :
            return 0
        
        pts = [t[3] for t in self.m_outputInfo]
        pts = np.concatenate(pts, axis=0)

        target = self.InputWorldC.reshape(1, 3)

        diff = pts - target
        dists = np.linalg.norm(diff, axis=1)
        nearestInx = np.argmin(dists)
        return nearestInx
    def _find_intersected_clID_by_plane(self, a : np.ndarray, b : np.ndarray, c : np.ndarray) -> list :
        '''
        ret : [(clID, knifeInx, tangent, intersectedPt), ..]
        '''
        epsilon = 1e-3
        skeleton = self.InputSkeleton

        plane = algLinearMath.CScoMath.create_plane(a, b, c)
        abc = plane[ : 3]
        d = plane[3]

        retList = []

        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            dist = np.dot(cl.Vertex, abc) + d

            abovePlaneIndices = np.where(dist >= 0)[0]
            belowPlaneIndices = np.where(dist < 0)[0]

            if abovePlaneIndices.size > 0 and belowPlaneIndices.size > 0 :
                # 첫번째 point가 평면상에 있다면 교차가 안된것으로 간주한다.
                if np.abs(dist[0]) < epsilon :
                    continue
                # 마지막 point가 평면상에 있다면 교차가 안된것으로 간주한다. 
                if np.abs(dist[-1]) < epsilon :
                    continue

                startInx = -1
                endInx= -1
                for ptInx in range(0, len(dist) - 1) :
                    # 부호가 다르므로 
                    if dist[ptInx] * dist[ptInx + 1] <= 0 :
                        startInx = ptInx
                        endInx = ptInx + 1
                        break
                # 무언가 잘못되었다. 
                if startInx == -1 :
                    continue

                p1 = cl.Vertex[startInx].reshape(-1, 3)
                p2 = cl.Vertex[endInx].reshape(-1, 3)

                d1 = algLinearMath.CScoMath.dot_plane_vec3(plane, p1)
                d2 = algLinearMath.CScoMath.dot_plane_vec3(plane, p2)
                if np.abs(d1 - d2) < epsilon :
                    continue

                t = d1 / (d1 - d2)
                pt = p1 + t * (p2 - p1)

                if self._is_point_in_triangle(pt, a, b, c, epsilon) == True :
                    retList.append((cl.ID, endInx, abc.reshape(-1, 3), pt.reshape(-1, 3)))
        
        if len(retList) == 0 :
            return None
        return retList
    
    def _is_point_in_triangle(self, p : np.ndarray, a : np.ndarray, b : np.ndarray, c : np.ndarray, epsilon=1e-6) -> bool :
        a = a.reshape(-1)
        b = b.reshape(-1)
        c = c.reshape(-1)
        p = p.reshape(-1)

        v0 = b - a
        v1 = c - a
        v2 = p - a

        d00 = np.dot(v0, v0)
        d01 = np.dot(v0, v1)
        d11 = np.dot(v1, v1)
        d20 = np.dot(v2, v0)
        d21 = np.dot(v2, v1)

        denom = d00 * d11 - d01 * d01
        if abs(denom) < epsilon :
            return False  # 삼각형이 면적이 거의 0

        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1 - v - w

        return (u >= -epsilon and v >= -epsilon and w >= -epsilon)


    @property
    def InputSkeleton(self) -> algSkeletonGraph.CSkeleton :
        return self.m_inputSkeleton
    @InputSkeleton.setter
    def InputSkeleton(self, skeleton : algSkeletonGraph.CSkeleton) :
        self.m_inputSkeleton = skeleton
    @property
    def InputWorldA(self) -> np.ndarray :
        return self.m_inputWorldA
    @InputWorldA.setter
    def InputWorldA(self, inputWorldA : np.ndarray) :
        self.m_inputWorldA = inputWorldA
    @property
    def InputWorldB(self) -> np.ndarray :
        return self.m_inputWorldB
    @InputWorldB.setter
    def InputWorldB(self, inputWorldB : np.ndarray) :
        self.m_inputWorldB = inputWorldB
    @property
    def InputWorldC(self) -> np.ndarray :
        return self.m_inputWorldC
    @InputWorldC.setter
    def InputWorldC(self, inputWorldC : np.ndarray) :
        self.m_inputWorldC = inputWorldC
    
    @property
    def OutputKnifedCLID(self) -> int :
        return self.m_outputKnifedCLID
    @property
    def OutputKnifedIndex(self) -> int :
        return self.m_outputKnifedIndex
    @property
    def OutputTangent(self) -> np.ndarray :
        return self.m_outputTangent
    @property
    def OutputIntersectedPt(self) -> np.ndarray :
        return self.m_outputIntersectedPt
    @property
    def OutputInfo(self) -> list :
        '''
        - OutputInfo : list
            - [(knifedCLID, knifedIndex, tangent, OutputIntersectedPt), ..]
        '''
        return self.m_outputInfo



class CCommandKnifeCLMask(commandInterface.CCommand) :
    def __init__(self, mediator) :
        '''
        desc
            - world 좌표계의 A, B, C로 구성된 Plane을 통해 해당 clMask를 False로 만듬
        input
            - InputCLMask
        output
        '''

        super().__init__(mediator)
        # input your code
        self.m_inputSkeleton = None
        self.m_inputKnifedCLID = -1
        self.m_inputKnifedIndex = -1
        self.m_inputCLMask = None
        # [(clID, vertexInx)]
        self.m_undoListInfo = []
    def clear(self) :
        # input your code
        self.m_inputSkeleton = None
        self.m_inputKnifedCLID = -1
        self.m_inputKnifedIndex = -1
        self.m_inputCLMask = None
        self.m_undoListInfo.clear()

        super().clear()
    def process(self) :
        super().process()

        if self.InputSkeleton is None :
            return
        if self.InputKnifedCLID == -1 :
            return
        if self.InputKnifedIndex == -1 :
            return
        if self.InputCLMask is None :
            return
        
        retList = self.InputSkeleton.find_descendant_centerline_by_centerline_id(self.InputKnifedCLID)
        if retList is None :
            return
        
        cl = retList[0]
        iCnt = cl.get_vertex_count()
        for inx in range(self.InputKnifedIndex, iCnt) :
            bRet = self.InputCLMask.get_flag(cl, inx)
            if bRet == True :
                self.InputCLMask.set_flag(cl, inx, False)
                self.m_undoListInfo.append((cl.ID, inx))
        
        del retList[0]
        for cl in retList : 
            iCnt = cl.get_vertex_count()
            for inx in range(0, iCnt) :
                bRet = self.InputCLMask.get_flag(cl, inx)
                if bRet == True :
                    self.InputCLMask.set_flag(cl, inx, False)
                    self.m_undoListInfo.append((cl.ID, inx))
        self.m_mediator.remove_key_type(data.CData.s_outsideKeyType)
        self.m_mediator.load_outside_key(self.InputCLMask)
        self.m_mediator.ref_key_type(data.CData.s_outsideKeyType)    
    def process_undo(self):
        super().process_undo()

        for undoInfo in self.m_undoListInfo :
            clID = undoInfo[0]
            inx = undoInfo[1]
            self.InputCLMask.set_flag(self.InputSkeleton.get_centerline(clID), inx, True)
        self.m_mediator.remove_key_type(data.CData.s_outsideKeyType)
        self.m_mediator.load_outside_key(self.InputCLMask)
        self.m_mediator.ref_key_type(data.CData.s_outsideKeyType)
        

    @property
    def InputSkeleton(self) -> algSkeletonGraph.CSkeleton :
        return self.m_inputSkeleton
    @InputSkeleton.setter
    def InputSkeleton(self, skeleton : algSkeletonGraph.CSkeleton) :
        self.m_inputSkeleton = skeleton
    @property
    def InputKnifedCLID(self) -> int :
        return self.m_inputKnifedCLID
    @InputKnifedCLID.setter
    def InputKnifedCLID(self, inputKnifedCLID : int) :
        self.m_inputKnifedCLID = inputKnifedCLID
    @property
    def InputKnifedIndex(self) -> int :
        return self.m_inputKnifedIndex
    @InputKnifedIndex.setter
    def InputKnifedIndex(self, inputKnifedIndex : int) :
        self.m_inputKnifedIndex = inputKnifedIndex
    @property
    def InputCLMask(self) -> clMask.CCLMask :
        return self.m_inputCLMask
    @InputCLMask.setter
    def InputCLMask(self, clMaskInst : clMask.CCLMask) :
        self.m_inputCLMask = clMaskInst


if __name__ == '__main__' :
    pass


# print ("ok ..")

