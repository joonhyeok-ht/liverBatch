import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileCommonPath = os.path.dirname(fileAbsPath)
fileStateProjectPath = os.path.dirname(fileCommonPath)
fileStatePath = os.path.dirname(fileStateProjectPath)
fileAppPath = os.path.dirname(fileStatePath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileCommonPath)
sys.path.append(fileStateProjectPath)
sys.path.append(fileStatePath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algVTK as algVTK
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algMeshLib as algMeshLib


import data as data

import operation as operation

import tabState as tabState

import VtkObj.vtkObjLine as vtkObjLine
import vtkObjInterface as vtkObjInterface

import command.commandVesselKnife as commandVesselKnife


class CRemodelingNode :
    def __init__(self) :
        self.m_name = ""
        self.m_key = ""
        self.m_skelKey = ""
        self.m_skelEnKey = ""
        self.m_skeleton = None
        self.m_skeletonEn = None
        self.m_rootEntity = None
    def clear(self) :
        self.m_name = ""
        self.m_key = ""
        self.m_skelKey = ""
        self.m_skelEnKey = ""
        self.m_skeleton = None
        self.m_skeletonEn = None
        if self.m_rootEntity is not None :
            self.m_rootEntity.clear()
        self.m_rootEntity = None
    

    @property
    def Name(self) -> str :
        return self.m_name
    @Name.setter
    def Name(self, name : str) :
        self.m_name = name
    @property
    def Key(self) -> str :
        return self.m_key
    @Key.setter
    def Key(self, key : str) :
        self.m_key = key
    @property
    def SkelKey(self) -> str :
        return self.m_skelKey
    @SkelKey.setter
    def SkelKey(self, skelKey : str) :
        self.m_skelKey = skelKey
    @property
    def SkelEnKey(self) -> str :
        return self.m_skelEnKey
    @SkelEnKey.setter
    def SkelEnKey(self, skelEnKey : str) :
        self.m_skelEnKey = skelEnKey
    @property
    def Skeleton(self) -> algSkeletonGraph.CSkeleton :
        return self.m_skeleton
    @Skeleton.setter
    def Skeleton(self, skeleton : algSkeletonGraph.CSkeleton) :
        self.m_skeleton = skeleton
    @property
    def SkeletonEn(self) -> algSkeletonGraph.CSkeleton :
        return self.m_skeletonEn
    @SkeletonEn.setter
    def SkeletonEn(self, skeleton : algSkeletonGraph.CSkeleton) :
        self.m_skeletonEn = skeleton
    @property
    def RootEntity(self) -> tabState.CRenderEntity :
        return self.m_rootEntity
    @RootEntity.setter
    def RootEntity(self, rootEntity : tabState.CRenderEntity) :
        self.m_rootEntity = rootEntity
    


if __name__ == '__main__' :
    pass


# print ("ok ..")

