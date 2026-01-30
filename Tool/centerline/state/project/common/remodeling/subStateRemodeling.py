import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
from scipy.spatial import KDTree

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QMessageBox
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


import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algSkeletonGraph as algSkeletonGraph

import VtkObj.vtkObjLine as vtkObjLine
import VtkObj.vtkObjSphere as vtkObjSphere

import vtkObjGuideCL as vtkObjGuideCL

import data as data

import operation as operation

import remodelingNode as remodelingNode


class CSubStateRemodeling() :
    s_cuttingMeshType = "cuttedMesh"
    '''
    - groupID : 0 고정
    - ID : 0 ~ 무한대 (cuttedMeshID)
    '''
    s_subRemodelingKey = "subRemodeling"
    '''
    - groupID : 0 고정
    - ID : cuttedMeshID
    '''
    s_dilationPass = 5


    def __init__(self, mediator) :
        # input your code
        self.m_mediator = mediator      # CTabStateVesselRemodeling
    def clear(self) :
        # input your code
        self.m_mediator = None

    def process_init(self) :
        pass
    def process(self) :
        pass
    def process_end(self) :
        pass

    def clicked_mouse_rb(self, clickX, clickY) :
        pass
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        pass
    def release_mouse_rb(self) :
        pass
    def mouse_move(self, clickX, clickY) :
        pass
    def mouse_move_rb(self, clickX, clickY) :
        pass
    def key_press(self, keyCode : str) :
        pass
    def key_press_with_ctrl(self, keyCode : str) :
        pass

    def changed_cutting_mesh(self, prevNode : remodelingNode.CRemodelingNode, nowNode : remodelingNode.CRemodelingNode) :
        pass
    def checked_sel_cell(self, bChecked : bool) :
        pass
    def btn_attach_centerline(self) :
        pass
    def btn_refresh_centerline(self) :
        pass
    def btn_select_minor(self):
        pass


    # protected
    def _get_data(self) -> data.CData :
        return self.m_mediator.get_data()
    def _get_clinfo_index(self) -> int :
        dataInst = self._get_data()
        return dataInst.CLInfoIndex
    def _get_skeleton(self) -> algSkeletonGraph.CSkeleton :
        dataInst = self._get_data()
        clinfoinx = self._get_clinfo_index()
        return dataInst.get_skeleton(clinfoinx)


    @property
    def App(self) : 
        return self.m_mediator.m_mediator

if __name__ == '__main__' :
    pass


# print ("ok ..")

