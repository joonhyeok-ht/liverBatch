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

import subStateRemodeling as subStateRemodeling 


class CSubStateRemodelingRemodeling(subStateRemodeling.CSubStateRemodeling) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
    def clear(self) :
        # input your code
        super().clear()

    def process_init(self) :
        self.m_mediator.m_lvCuttedNode.customContextMenuRequested.connect(self._on_lb_show_context_menu)
        self.m_mediator.setui_edit_anchor_name("")
        self.m_mediator.setui_lv_subnode_remove_all()
    def process(self) :
        pass
    def process_end(self) :
        self.m_mediator.m_lvCuttedNode.customContextMenuRequested.disconnect(self._on_lb_show_context_menu)
        self.m_mediator.setui_edit_anchor_name("")
        self.m_mediator.setui_lv_subnode_remove_all()

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


    # protected
    def _on_lb_show_context_menu(self, pos) :
        item = self.m_mediator.m_lvCuttedNode.itemAt(pos)
        if item is None :
            return

        # 메뉴 생성
        menu = QMenu()
        action_attachAnchor = menu.addAction("Attach Anchor")
        action_attachSub = menu.addAction("Attach Sub")
        action_addCL = menu.addAction("Add Centerline")
        
        # 액션 선택 처리
        action = menu.exec(self.m_mediator.m_lvCuttedNode.mapToGlobal(pos))
        if action == action_attachAnchor :
            self.m_mediator.command_attach_anchor()
        elif action == action_attachSub :
            self.m_mediator.command_attach_sub()
        elif action == action_addCL :
            self.m_mediator.command_add_skelinfo()

if __name__ == '__main__' :
    pass


# print ("ok ..")

