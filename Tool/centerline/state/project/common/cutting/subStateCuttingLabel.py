import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import math
from scipy.spatial import KDTree

from PySide6.QtCore import Qt, QEvent, QObject, QPoint
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QMessageBox, QMenu
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

import com.componentSelectionCL as componentSelectionCL

import subStateCutting as subStateCutting 


class CSubStateCuttingLabel(subStateCutting.CSubStateCutting) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
    def clear(self) :
        # input your code
        super().clear()

    def process_init(self) :
        self.m_mediator.m_comDragSelCLTP.command_visible_label(True)
    def process(self) :
        pass
    def process_end(self) :
        self.m_mediator.m_comDragSelCLTP.command_visible_label(False)

    def clicked_mouse_rb(self, clickX, clickY) :
        listExceptKeyType = [
            data.CData.s_vesselType,
            data.CData.s_textType
        ]

        if self.m_mediator.m_comDragSelCLTP is None :
            return
        self.m_mediator.m_comDragSelCLTP.click(clickX, clickY, listExceptKeyType)
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        if self.m_mediator.m_comDragSelCLTP is None :
            return
        self.m_mediator.m_comDragSelCLTP.click_with_shift(clickX, clickY)
    def release_mouse_rb(self) :
        if self.m_mediator.m_comDragSelCLTP is not None : 
            self.m_mediator.m_comDragSelCLTP.release(0, 0)
        if self.m_mediator.m_comTreeVessel is not None :
            self.m_mediator.m_comTreeVessel.command_init_tree_vessel()
    def mouse_move(self, clickX, clickY) :
        pass
    def mouse_move_rb(self, clickX, clickY) :
        if self.m_mediator.m_comDragSelCLTP is None :
            return
        listExceptKeyType = [
            data.CData.s_vesselType,
            componentSelectionCL.CComDragSelCLTP.s_tpVesselKeyType,
            data.CData.s_textType
        ]
        self.m_mediator.m_comDragSelCLTP.move(clickX, clickY, listExceptKeyType)
    def key_press(self, keyCode : str) :
        if keyCode == "Escape" :
            if self.m_mediator.m_comDragSelCLTP is not None :
                self.m_mediator.m_comDragSelCLTP.command_reset_color()
            if self.m_mediator.m_comTreeVessel is not None :
                self.m_mediator.m_comTreeVessel.command_clear_selection()
        elif keyCode == "Delete" :
            self.m_mediator.m_editLabelName.setText("")
            if self.m_mediator.m_comDragSelCLTP is not None :
                self.m_mediator.m_comDragSelCLTP.command_label_name("")
            if self.m_mediator.m_comTreeVessel is not None :
                self.m_mediator.m_comTreeVessel.command_init_tree_vessel()
    def key_press_with_ctrl(self, keyCode : str) :
        if keyCode == "z" :
            pass


    # protected


    def slot_vessel_hierarchy(self, listCLID : list) :
        if self.m_mediator.m_comDragSelCLTP is not None :
            self.m_mediator.m_comDragSelCLTP.command_reset_color()

        clinfoInx = self._get_clinfo_index()
        for clID in listCLID :
            key = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, clID)
            self.m_mediator.m_opSelectionCL.add_selection_key(key)
        self.m_mediator.m_opSelectionCL.process()


if __name__ == '__main__' :
    pass


# print ("ok ..")

