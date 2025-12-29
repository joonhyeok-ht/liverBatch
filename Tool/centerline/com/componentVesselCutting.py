import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import math

from PySide6.QtCore import Qt, QItemSelection, QItemSelectionModel
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTreeView, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QListWidgetItem, QMessageBox, QAbstractItemView
from PySide6.QtGui import QStandardItemModel, QStandardItem
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAppPath = os.path.dirname(fileAbsPath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algMeshLib as algMeshLib

import data as data
import operation as operation
import component as component
import componentSelectionCL as componentSelectionCL
import treeVessel as treeVessel

import VtkObj.vtkObjLine as vtkObjLine

import command.commandKnife as commandKnife
import command.commandVesselKnife as commandVesselKnife


class CVesselSeparator :
    def __init__(self, mediator, dataInst : data.CData) :
        self.m_mediator = mediator
        self.m_dataInst = dataInst
        self.m_listInvalidNode = []
    def clear(self) :
        self.m_mediator = None
        self.m_dataInst = None
        self.m_listInvalidNode.clear()
    def process(self, treeVessel : treeVessel.CTreeVessel, firstNodeVessel : vtk.vtkPolyData) :
        self.m_treeVessel = treeVessel
        firstRootNode = self.m_treeVessel.get_first_root_node()
        if firstRootNode is None :
            return
        firstRootNode.clear_vessel()
        firstRootNode.Vessel = firstNodeVessel

        iCnt = firstRootNode.get_child_node_count()
        for inx in range(0, iCnt) :
            node = firstRootNode.get_child_node(inx)
            self._process_sub(node)
    

    # protected
    def _process_sub(self, node : treeVessel.CNodeVesselHier) :
        wholeVessel = node.get_whole_vessel()
        if wholeVessel is None :
            print("not found whole vessel mesh")
        
        # meshLibVessel = commandVesselKnife.CCommandSepVessel.get_meshlib(wholeVessel)
        # meshLibVessel = algMeshLib.CMeshLib.meshlib_healing(meshLibVessel)
        clID = node.get_clID(0)

        # cmd = commandVesselKnife.CCommandSepVesselPick(self.m_mediator)
        cmd = commandVesselKnife.CCommandSepVesselKMTreeVessel(self.m_mediator)
        cmd.m_inputData = self.m_dataInst
        cmd.m_inputSkeleton = self.m_treeVessel.Skeleton
        cmd.m_inputWholeVessel = wholeVessel
        # cmd.m_inputMeshLibWholeVessel = meshLibVessel
        cmd.m_inputCLID = clID
        cmd.process()

        if cmd.OutputWhole is None or cmd.OutputSub is None :
            self.m_listInvalidNode.append(node)
        else :
            node.set_whole_vessel(cmd.OutputWhole)
            node.Vessel = cmd.OutputSub

        iCnt = node.get_child_node_count()
        for inx in range(0, iCnt) :
            childNode = node.get_child_node(inx)
            self._process_sub(childNode)
    

    @property
    def ListInvalidNode(self) -> list :
        return self.m_listInvalidNode


class CComVesselCutting(componentSelectionCL.CComDrag) :
    s_knifeKeyType = "knife"
    s_pickingDepth = 1000.0
    s_minDragDist = 10


    def __init__(self, mediator) :
        super().__init__(mediator)
        self.m_inputTreeVessel = None
        self.m_inputUILVInvalidVessel = None

        self.signal_invalid_node = None     # (self, node : treeVessel.CNodeVesselHier)
        self.signal_finished_knife = None   # (self, node : treeVessel.CNodeVesselHier)

        self.m_knifeKey = ""
    def clear(self) :
        self.m_inputTreeVessel = None
        self.m_inputUILVInvalidVessel = None

        self.signal_invalid_node = None
        self.signal_finished_knife = None

        self.m_knifeKey = ""
        super().clear()

    
    # override 
    def ready(self) -> bool :
        if self.InputTreeVessel is None :
            return False
        if self.InputUILVInvalidVessel is None :
            return False
        return True
    def process_init(self) :
        super().process_init()
        # input your code
        if self.ready() == False :
            return
        self.InputUILVInvalidVessel.itemClicked.connect(self._on_lb_invalid_node)
        self.m_knifeKey = ""
    def process_end(self) :
        # input your code
        if self.ready() == False :
            return
        
        self.m_knifeKey = ""
        self.App.remove_key_type(CComVesselCutting.s_knifeKeyType)
        self.InputUILVInvalidVessel.clear()

        self.signal_invalid_node = None
        self.signal_finished_knife = None
        
        super().process_end()
    
    def click(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        
        super().click(clickX, clickY)
        
        dataInst = self._get_data()
        worldStart, pNearStart, pFarStart= self.App.get_world_from_mouse(self.m_startX, self.m_startY, CComVesselCutting.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(self.m_endX, self.m_endY, CComVesselCutting.s_pickingDepth)

        self.m_knifeKey = data.CData.make_key(CComVesselCutting.s_knifeKeyType, 0, 0)
        inst = vtkObjLine.CVTKObjLine()
        inst.KeyType = CComVesselCutting.s_knifeKeyType
        inst.Key = self.m_knifeKey
        inst.set_line_width(2.0)
        inst.set_pos(pFarStart, pFarEnd)
        inst.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        dataInst.add_vtk_obj(inst)

        self.App.ref_key_type(CComVesselCutting.s_knifeKeyType)

        self.m_bDrag = True
        return True
    def click_with_shift(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        return True
    def release(self, clickX : int, clickY : int) :
        if self.ready() == False :
            return False
        if self.Drag == False :
            return False
        
        self.App.remove_key_type(CComVesselCutting.s_knifeKeyType)

        # drag 영역이 너무 작을 경우 무시
        dx = self.m_endX - self.m_startX
        dy = self.m_endY - self.m_startY
        dist = math.hypot(dx, dy)
        if dist < CComVesselCutting.s_minDragDist :
            return False

        self.command_knife_vessel(self.m_startX, self.m_startY, self.m_endX, self.m_endY)

        self.m_bDrag = False
        return True
    def move(self, clickX : int, clickY : int, listExceptKeyType=None) :
        if self.ready() == False :
            return
        if self.Drag == False :
            return False
        
        super().move(clickX, clickY, listExceptKeyType)

        dataInst = self._get_data()
        worldStart, pNearStart, pFarStart = self.App.get_world_from_mouse(self.m_startX, self.m_startY, CComVesselCutting.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(self.m_endX, self.m_endY, CComVesselCutting.s_pickingDepth)
        inst = dataInst.find_obj_by_key(self.m_knifeKey)
        inst.set_pos(pFarStart, pFarEnd)
 
        return True


    # command
    def command_clear_selection(self) -> bool :
        if self.ready() == False :
            return False
        self.InputUILVInvalidVessel.clearSelection()
        return True
    def command_separate_vessel(self, vesselPolyData : vtk.vtkPolyData) :
        dataInst = self._get_data()

        cmd = CVesselSeparator(self.App, dataInst)
        cmd.process(self.InputTreeVessel, vesselPolyData)
        if len(cmd.ListInvalidNode) > 0 :
            self._setui_list_add_listnode(cmd.ListInvalidNode)
        cmd.clear()
    def command_knife_vessel(self, startMx, startMy, endMx, endMy) :
        dataInst = self._get_data()
        clinfoInx = self._get_clinfoinx()
        skeleton = self._get_skeleton()

        worldStart, pNearStart, pFarStart = self.App.get_world_from_mouse(startMx, startMy, CComVesselCutting.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(endMx, endMy, CComVesselCutting.s_pickingDepth)
        cameraInfo = self.App.get_active_camerainfo()
        cameraPos = cameraInfo[3]

        knifeCL = commandKnife.CCommandKnifeCL(self.App)
        knifeCL.InputData = dataInst
        knifeCL.InputSkeleton = skeleton
        knifeCL.InputWorldA = worldStart
        knifeCL.InputWorldB = worldEnd
        knifeCL.InputWorldC = cameraPos
        knifeCL.process()

        if knifeCL.OutputKnifedCLID == -1 :
            print("not intersected cl")
            return
        
        node = self._getui_list_selected_node()
        if node is None :
            print("not selected invalid node")
            return
        
        # 현재는 혈관의 root cl만 가능하게 한다.
        selectedCLID = node.get_clID(0)
        if selectedCLID != knifeCL.OutputKnifedCLID :
            print("not selected invalid node")
            return 
        

        wholeVessel = node.get_whole_vessel()
        if wholeVessel is None :
            print("not found whole vessel mesh")
            return
        
        # meshLibVessel = commandVesselKnife.CCommandSepVessel.get_meshlib(wholeVessel)
        # meshLibVessel = algMeshLib.CMeshLib.meshlib_healing(meshLibVessel)

        knifeCL.InputWorldA = worldStart
        knifeCL.InputWorldB = worldEnd
        knifeCL.InputWorldC = cameraPos

        # cmd = commandVesselKnife.CCommandSepVesselKnife(self.App)
        cmd = commandVesselKnife.CCommandSepVesselKMTreeVesselKnife(self.App)
        cmd.m_inputData = dataInst
        cmd.m_inputSkeleton = skeleton
        # cmd.m_inputMeshLibWholeVessel = meshLibVessel
        cmd.m_inputWholeVessel = wholeVessel
        cmd.m_inputWorldA = worldStart
        cmd.m_inputWorldB = worldEnd
        cmd.m_inputWorldC = cameraPos
        cmd.process()

        if cmd.OutputWhole is None or cmd.OutputSub is None :
            print("failed to vessel knife")
            return
        else :
            node.set_whole_vessel(cmd.OutputWhole)
            node.Vessel = cmd.OutputSub
        self._setui_list_remove_node(node)

        if self.signal_finished_knife is not None :
            self.signal_finished_knife(node)

    
    # ui setting
    def _getui_list_selected_node(self) -> treeVessel.CNodeVesselHier :
        selectedItems = self.InputUILVInvalidVessel.selectedItems()
        if not selectedItems :
            return None
        
        item = selectedItems[0]
        text = item.text()
        node = item.data(Qt.UserRole) 
        
        return node
    
    def _setui_list_add_node(self, node : treeVessel.CNodeVesselHier) :
        self.InputUILVInvalidVessel.blockSignals(True)

        clLabel = self.InputTreeVessel.get_cl_label(node)
        item = QListWidgetItem(f"{clLabel}")
        item.setData(Qt.UserRole, node)
        self.InputUILVInvalidVessel.addItem(item)

        self.InputUILVInvalidVessel.blockSignals(False)
    def _setui_list_add_listnode(self, listNode : list) :
        self.InputUILVInvalidVessel.blockSignals(True)
        self.InputUILVInvalidVessel.clear()

        for node in listNode :
            clLabel = self.InputTreeVessel.get_cl_label(node)
            item = QListWidgetItem(f"{clLabel}")
            item.setData(Qt.UserRole, node)
            self.InputUILVInvalidVessel.addItem(item)

        self.InputUILVInvalidVessel.blockSignals(False)
    def _setui_list_remove_node(self, targetNode : treeVessel.CNodeVesselHier) :
        self.InputUILVInvalidVessel.blockSignals(True)

        self.InputUILVInvalidVessel.setCurrentItem(None)
        self.InputUILVInvalidVessel.clearSelection()

        count = self.InputUILVInvalidVessel.count()
        for i in reversed(range(count)):
            item = self.InputUILVInvalidVessel.item(i)
            node = item.data(Qt.UserRole)
            if node == targetNode :
                self.InputUILVInvalidVessel.takeItem(i)
                del item
                break
        
        self.InputUILVInvalidVessel.blockSignals(False)


    # event
    def _on_lb_invalid_node(self, item) :
        node = item.data(Qt.UserRole)
        if node is None :
            print("not found node")
            return
        if self.signal_invalid_node is not None :
            self.signal_invalid_node(node)


    @property
    def InputTreeVessel(self) -> treeVessel.CTreeVessel :
        return self.m_inputTreeVessel
    @InputTreeVessel.setter
    def InputTreeVessel(self, treeVesselInst : treeVessel.CTreeVessel) :
        self.m_inputTreeVessel = treeVesselInst
    @property
    def InputUILVInvalidVessel(self) :
        return self.m_inputUILVInvalidVessel
    @InputUILVInvalidVessel.setter
    def InputUILVInvalidVessel(self, inputUILVInvalidVessel) :
        self.m_inputUILVInvalidVessel = inputUILVInvalidVessel




if __name__ == '__main__' :
    pass


# print ("ok ..")

