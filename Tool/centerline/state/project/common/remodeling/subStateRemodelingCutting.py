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

class DeleteKeyFilter(QObject) :
    def __init__(self, callback) :
        super().__init__()
        self.callback = callback
    def eventFilter(self, obj, event) :
        if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Delete, Qt.Key_Backspace) :
            self.callback()
            return True
        return super().eventFilter(obj, event)


class CSubStateRemodelingCutting(subStateRemodeling.CSubStateRemodeling) :
    s_knifeKeyType = "knife"
    s_pickingDepth = 1000.0
    s_minDragDist = 10


    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_knifeKey = ""

        self.m_startX = 0
        self.m_startY = 0
        self.m_endX = 0
        self.m_endY = 0
        self.m_bDrag = False

        self.m_lvCuttedNodeDeleteKeyFilter = DeleteKeyFilter(self._on_lb_clicked_delete)
    def clear(self) :
        # input your code
        self.m_knifeKey = ""
        self.m_bDrag = False
        super().clear()

    def process_init(self) :
        self.m_knifeKey = ""

        self.m_mediator.m_lvCuttedNode.installEventFilter(self.m_lvCuttedNodeDeleteKeyFilter)
        self.m_mediator.m_lvCuttedNode.customContextMenuRequested.connect(self._on_lb_show_context_menu)

        self.m_bDrag = False
    def process(self) :
        pass
    def process_end(self) :
        self.App.remove_key_type(CSubStateRemodelingCutting.s_knifeKeyType)
        self.m_knifeKey = ""

        self.m_mediator.m_lvCuttedNode.removeEventFilter(self.m_lvCuttedNodeDeleteKeyFilter)
        self.m_mediator.m_lvCuttedNode.customContextMenuRequested.disconnect(self._on_lb_show_context_menu)

        self.m_bDrag = False

    def clicked_mouse_rb(self, clickX, clickY) :
        dataInst = self._get_data()
        if dataInst.Ready == False :
            return
        
        self.m_startX = clickX
        self.m_startY = clickY
        self.m_endX = clickX
        self.m_endY = clickY

        worldStart, pNearStart, pFarStart= self.App.get_world_from_mouse(self.m_startX, self.m_startY, CSubStateRemodelingCutting.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(self.m_endX, self.m_endY, CSubStateRemodelingCutting.s_pickingDepth)

        self.m_knifeKey = data.CData.make_key(CSubStateRemodelingCutting.s_knifeKeyType, 0, 0)
        inst = vtkObjLine.CVTKObjLine()
        inst.KeyType = CSubStateRemodelingCutting.s_knifeKeyType
        inst.Key = self.m_knifeKey
        inst.set_line_width(2.0)
        inst.set_pos(pFarStart, pFarEnd)
        inst.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        dataInst.add_vtk_obj(inst)

        self.App.ref_key_type(CSubStateRemodelingCutting.s_knifeKeyType)
        self.m_bDrag = True
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        pass
    def release_mouse_rb(self) :
        dataInst = self._get_data()
        if dataInst.Ready == False :
            return
        if self.m_bDrag == False :
            return False
        
        self.App.remove_key_type(CSubStateRemodelingCutting.s_knifeKeyType)

        # drag 영역이 너무 작을 경우 무시
        dx = self.m_endX - self.m_startX
        dy = self.m_endY - self.m_startY
        dist = math.hypot(dx, dy)
        if dist < CSubStateRemodelingCutting.s_minDragDist :
            return False
        
        self.m_mediator.command_cutting_mesh(self.m_startX, self.m_startY, self.m_endX, self.m_endY)
        self.m_bDrag = False
        
    def mouse_move(self, clickX, clickY) :
        pass
    def mouse_move_rb(self, clickX, clickY) :
        dataInst = self._get_data()
        if dataInst.Ready == False :
            return
        if self.m_bDrag == False :
            return False
        self.m_endX = clickX
        self.m_endY = clickY

        worldStart, pNearStart, pFarStart = self.App.get_world_from_mouse(self.m_startX, self.m_startY, CSubStateRemodelingCutting.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(self.m_endX, self.m_endY, CSubStateRemodelingCutting.s_pickingDepth)
        inst = dataInst.find_obj_by_key(self.m_knifeKey)
        inst.set_pos(pFarStart, pFarEnd)
    def key_press(self, keyCode : str) :
        if keyCode == "Escape" :
            pass
        elif keyCode == "Delete" :
            pass
    def key_press_with_ctrl(self, keyCode : str) :
        if keyCode == "z" :
            self.m_mediator.undo() 


    # protected
    def _on_lb_clicked_delete(self) :
        # mediator command call
        self.m_mediator.command_remove_node()
    def _on_lb_show_context_menu(self, pos) :
        item = self.m_mediator.m_lvCuttedNode.itemAt(pos)
        if item is None:
            return

        # 메뉴 생성
        menu = QMenu()
        action_delete = menu.addAction("Delete")
        
        # 액션 선택 처리
        action = menu.exec(self.m_mediator.m_lvCuttedNode.mapToGlobal(pos))
        if action == action_delete:
            self._on_lb_clicked_delete()  # 기존 delete 함수 호출
        # elif action == action_edit:
        #     self.edit_item_name(item)     # 새로운 이름 편집 함수

if __name__ == '__main__' :
    pass


# print ("ok ..")

