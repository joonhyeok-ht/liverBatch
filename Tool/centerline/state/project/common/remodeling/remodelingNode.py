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
        self.m_skelGroupID = -1
        self.m_skeletonEn = None
    def clear(self) :
        self.m_name = ""
        self.m_key = ""
        self.m_skelGroupID = -1
        self.m_skeletonEn = None
    

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
    def SkelGroupID(self) -> int :
        return self.m_skelGroupID
    @SkelGroupID.setter
    def SkelGroupID(self, skelGroupID : int) :
        self.m_skelGroupID = skelGroupID
    @property
    def SkeletonEn(self) -> algSkeletonGraph.CSkeleton :
        return self.m_skeletonEn
    @SkeletonEn.setter
    def SkeletonEn(self, skeleton : algSkeletonGraph.CSkeleton) :
        self.m_skeletonEn = skeleton



class CSkelNode :
    def __init__(self) :
        self.m_remodelingNode = None
        self.m_name = ""
        self.m_listCLID = []
    def clear(self) :
        self.m_remodelingNode = None
        self.m_name = ""
        self.m_listCLID.clear()


    def clear_clid(self) :
        self.m_listCLID.clear()
    def add_clid(self, clid : int) :
        self.m_listCLID.append(clid)
    def add_clid_list(self, listCLID : list) :
        self.m_listCLID += listCLID
    def get_clid_count(self) -> int :
        return len(self.m_listCLID)
    def get_clid(self, inx : int) -> int :
        return self.m_listCLID[inx]

    
    @property
    def RemodelingNode(self) -> CRemodelingNode :
        return self.m_remodelingNode
    @RemodelingNode.setter
    def RemodelingNode(self, remodelingNode : CRemodelingNode) :
        self.m_remodelingNode = remodelingNode
    @property
    def Name(self) -> str :
        return self.m_name
    @Name.setter
    def Name(self, name : str) :
        self.m_name = name



if __name__ == '__main__' :
    pass


# print ("ok ..")

