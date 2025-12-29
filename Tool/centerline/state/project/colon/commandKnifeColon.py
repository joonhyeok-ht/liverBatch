import sys
import os
import numpy as np
import shutil
import glob
import vtk
import subprocess
import copy
import SimpleITK as sitk
import math
from collections import Counter

from PySide6.QtCore import Qt, QItemSelection, QItemSelectionModel
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTreeView, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QListWidgetItem, QMessageBox, QAbstractItemView
from PySide6.QtGui import QStandardItemModel, QStandardItem
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileStateProjectPath = os.path.dirname(fileAbsPath)
fileStatePath = os.path.dirname(fileStateProjectPath)
fileAppPath = os.path.dirname(fileStatePath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileStateProjectPath)
sys.path.append(fileStatePath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algVTK as algVTK
import AlgUtil.algSkeletonGraph as algSkeletonGraph

import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer
import Block.originOffset as originOffset
import Block.removeStricture as removeStricture
import Block.registration as registration
import Block.resampling as resamplingB
import Block.reconstruction as reconstruction
import Block.meshHealing as meshHealing
import Block.meshBoolean as meshBoolean

import vtkObjInterface as vtkObjInterface

import data as data

import userData as userData

import command.commandRecon as commandRecon
import command.commandKnife as commandKnife



class CCommandKnifeColon(commandKnife.CCommandKnifeCL) :
    def __init__(self, mediator) :
        '''
        desc
            - world 좌표계의 A, B, C로 구성된 Plane을 교차하는 centerline 반환
            - 교차되는 centerline은 AB 선분위에 놓여있게 된다. 
        input
            - InputSkeleton
            - InputWorldA
            - InputWorldB
            - InputWorldC
        output
            - OutputKnifedCLID : knife로 절단 된 CLID 
            - OutputKnifedIndex : 절단 된 CLID의 시작 vertex index
            - OutputTangent : 절단 면의 노멀벡터, 즉 절단 면의 방향
        '''

        super().__init__(mediator)
        # input your code
    def clear(self) :
        # input your code
        super().clear()
    def process(self) :
        if self.InputData is None :
            return
        if self.InputSkeleton is None :
            return
        if self.InputWorldA is None :
            return
        if self.InputWorldB is None :
            return
        if self.InputWorldC is None :
            return
        
        iCLCnt = self.InputSkeleton.get_centerline_count()
        for inx in range(0, iCLCnt) :
            cl = self.InputSkeleton.get_centerline(inx)
            retList = self._find_intersected_colon_clID_by_plane(cl, self.InputWorldA, self.InputWorldB, self.InputWorldC)
            if retList is not None :
                if len(retList) == 1 :
                    self.m_outputKnifedCLID = retList[0][0]
                    self.m_outputKnifedIndex = retList[0][1]
                    self.m_outputTangent = retList[0][2]
                    self.m_outputIntersectedPt = retList[0][3]
        

    # protected
    def _find_intersected_colon_clID_by_plane(
            self, 
            cl : algSkeletonGraph.CSkeletonCenterline, 
            a : np.ndarray, b : np.ndarray, c : np.ndarray
            ) -> list :
        '''
        ret : [(clID, knifeInx, tangent, intersectedPt), ..]
        '''
        epsilon = 1e-3
        plane = algLinearMath.CScoMath.create_plane(a, b, c)
        abc = plane[ : 3]
        d = plane[3]
        dist = np.dot(cl.Vertex, abc) + d

        retList = []
        abovePlaneIndices = np.where(dist >= 0)[0]
        belowPlaneIndices = np.where(dist < 0)[0]

        if abovePlaneIndices.size > 0 and belowPlaneIndices.size > 0 :
            # 첫번째 point가 평면상에 있다면 교차가 안된것으로 간주한다.
            if np.abs(dist[0]) < epsilon :
                return None
            # 마지막 point가 평면상에 있다면 교차가 안된것으로 간주한다. 
            if np.abs(dist[-1]) < epsilon :
                return None

            for ptInx in range(0, len(dist) - 1) :
                # 부호가 다르므로 
                if dist[ptInx] * dist[ptInx + 1] <= 0 :
                    startInx = ptInx
                    endInx = ptInx + 1

                    p1 = cl.Vertex[startInx].reshape(-1, 3)
                    p2 = cl.Vertex[endInx].reshape(-1, 3)

                    # 이 부분은 고찰해봐야 함 
                    d1 = algLinearMath.CScoMath.dot_plane_vec3(plane, p1)
                    d2 = algLinearMath.CScoMath.dot_plane_vec3(plane, p2)
                    if np.abs(d1 - d2) < epsilon :
                        continue

                    t = d1 / (d1 - d2)
                    pt = p1 + t * (p2 - p1)

                    if self._is_point_in_triangle(pt, a, b, c, epsilon) == True :
                        retList.append((cl.ID, endInx, abc.reshape(-1, 3), pt.reshape(-1, 3)))
                    else :
                        i = 0
        if len(retList) == 0 :
            return None
        return retList

if __name__ == '__main__' :
    pass


# print ("ok ..")

