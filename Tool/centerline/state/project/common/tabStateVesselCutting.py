import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

from scipy.spatial import KDTree

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTreeView, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QMessageBox
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


import data as data
import userDataCommon as userDataCommon

import operation as operation

import tabState as tabState

import treeVessel as treeVessel

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algMeshLib as algMeshLib
import AlgUtil.algVTK as algVTK
import AlgUtil.algSkeletonGraph as algSkeletonGraph

import vtkObjSTL as vtkObjSTL
import vtkObjInterface as vtkObjInterface
import vtkObjGuideMeshBound as vtkObjGuideMeshBound

import com.componentSelectionCL as componentSelectionCL
import com.componentTreeVessel as componentTreeVessel
import com.componentVesselCutting as componentVesselCutting

import cutting.subStateCutting as subStateCutting
import cutting.subStateCuttingLabel as subStateCuttingLabel
import cutting.subStateCuttingCutting as subStateCuttingCutting



class CTabStateVesselCutting(tabState.CTabState) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_opSelectionCL = operation.COperationDragSelectionCL(mediator)
        self.m_comDragSelCLTP = None
        self.m_comTreeVessel = None

        self.m_state = -1
        self.m_listSubState = []
        self.m_listSubState.append(subStateCuttingLabel.CSubStateCuttingLabel(self))
        self.m_listSubState.append(subStateCuttingCutting.CSubStateCuttingCutting(self))
    def clear(self) :
        # input your code
        self.m_listSubState.clear()
        self.m_state = -1

        if self.m_comDragSelCLTP is not None :
            self.m_comDragSelCLTP.clear()
            self.m_comDragSelCLTP = None
        if self.m_comTreeVessel is not None :
            self.m_comTreeVessel.clear()
            self.m_comTreeVessel = None
        self.m_opSelectionCL = None
        super().clear()

    def process_init(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        userData = self._get_userdata()
        if userData is None :
            return
        clinfoinx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoinx)
        if skeleton is None :
            return
        
        self.m_opSelectionCL.Skeleton = skeleton
        self.m_opSelectionCL.ChildSelectionMode = False

        self.m_comTreeVessel = componentTreeVessel.CComTreeVessel(self)
        self.m_comTreeVessel.InputUITVVessel = self.m_tvVessel
        self.m_comTreeVessel.signal_vessel_hierarchy = self.slot_vessel_hierarchy
        self.m_comTreeVessel.process_init()

        self.m_comDragSelCLTP = componentSelectionCL.CComDragSelCLTP(self)
        self.m_comDragSelCLTP.InputOPDragSelCL = self.m_opSelectionCL
        self.m_comDragSelCLTP.InputUILVTP = self.m_lvTP
        self.m_comDragSelCLTP.process_init()
        # tp test start
        rootCL = skeleton.RootCenterline
        pos = rootCL.get_vertex(0)
        self.m_comDragSelCLTP.add_tpinfo("root", pos)

        cl = skeleton.get_centerline(10)
        pos = cl.get_vertex(0)
        self.m_comDragSelCLTP.add_tpinfo("sub", pos)
        # tp test end
        
        self.m_comTreeVessel.command_init_tree_vessel()

        if self.m_state == -1 :
            self.m_state = 0
            self._get_substate(self.m_state).process_init()
        else :
            self.m_tabUI.setCurrentIndex(0)

        self.m_mediator.update_viewer()
    def process(self) :
        pass
    def process_end(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        userData = self._get_userdata()
        if userData is None :
            return
        clinfoinx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoinx)
        if skeleton is None :
            return

        self.m_tabUI.setCurrentIndex(0)

        if self.m_comTreeVessel is not None :
            self.m_comTreeVessel.process_end()
            self.m_comTreeVessel = None
        if self.m_comDragSelCLTP is not None :
            self.m_comDragSelCLTP.process_end()
            self.m_comDragSelCLTP = None
        
        self.m_opSelectionCL.process_reset()
        self.m_mediator.update_viewer()

    def init_ui(self) :
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        self.m_tvVessel = QTreeView()
        tabLayout.addWidget(self.m_tvVessel)

        self.m_tabUI = self.init_ui_tab()
        tabLayout.addWidget(self.m_tabUI)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        lastUI = line
        tabLayout.setAlignment(lastUI, Qt.AlignmentFlag.AlignTop)
    def init_ui_tab(self) -> QTabWidget :
        tabUI = QTabWidget()

        title = "Labeling"
        tab = QWidget()
        subTabLayout = QVBoxLayout(tab)

        label = QLabel("TP List")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        subTabLayout.addWidget(label)

        self.m_lvTP = QListWidget()
        subTabLayout.addWidget(self.m_lvTP)

        layout, self.m_editLabelName = self.m_mediator.create_layout_label_editbox("Label Name", False)
        self.m_editLabelName.returnPressed.connect(self._on_return_pressed_label_name)
        subTabLayout.addLayout(layout)

        btn = QPushButton("Labeling to Descendant")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_labeling_to_descendant)
        subTabLayout.addWidget(btn)

        subTabLayout.addStretch()
        tabUI.addTab(tab, title)


        title = "Cutting"
        tab = QWidget()
        subTabLayout = QVBoxLayout(tab)

        # input your code
        lvLayout = QHBoxLayout()
        self.m_lvInvalidNode = QListWidget()
        lvLayout.addWidget(self.m_lvInvalidNode)
        self.m_lvNode = QListWidget()
        lvLayout.addWidget(self.m_lvNode)
        lvLayout.addStretch()
        subTabLayout.addLayout(lvLayout)

        layout, self.m_editCuttingName = self.m_mediator.create_layout_label_editbox("Label Name", False)
        self.m_editCuttingName.returnPressed.connect(self._on_return_pressed_cutting_name)
        subTabLayout.addLayout(layout)

        btn = QPushButton("Save Cutting Mesh")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_save_cutting_mesh)
        subTabLayout.addWidget(btn)

        subTabLayout.addStretch()
        tabUI.addTab(tab, title)


        tabUI.currentChanged.connect(self._on_tab_changed)
        return tabUI


    def clicked_mouse_rb(self, clickX, clickY) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return

        self._get_substate(self.m_state).clicked_mouse_rb(clickX, clickY)
        self.m_mediator.update_viewer()
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        self._get_substate(self.m_state).clicked_mouse_rb_shift(clickX, clickY)
        self.m_mediator.update_viewer()
    def release_mouse_rb(self) :
        self._get_substate(self.m_state).release_mouse_rb()    
        self.m_mediator.update_viewer()
    def mouse_move_rb(self, clickX, clickY) :
        self._get_substate(self.m_state).mouse_move_rb(clickX, clickY)
        self.m_mediator.update_viewer()
    def key_press(self, keyCode : str) :
        self._get_substate(self.m_state).key_press(keyCode)
        self.m_mediator.update_viewer()
    def key_press_with_ctrl(self, keyCode : str) : 
        self._get_substate(self.m_state).key_press_with_ctrl(keyCode)
        self.m_mediator.update_viewer()

    
    def getui_tree_vessel_node(self) :
        selectedIndex = self.m_tvVessel.selectedIndexes()
        if not selectedIndex :
            return None
        if selectedIndex :
            index = selectedIndex[0]
            model = self.m_tvVessel.model()
            item = model.itemFromIndex(index)
            node = item.data(Qt.UserRole)
            if node :
                return node
        return None

    
    # protected
    def _get_userdata(self) -> userDataCommon.CUserDataCommon :
        return self.get_data().UserData
    def _get_substate(self, inx : int) -> subStateCutting.CSubStateCutting :
        return self.m_listSubState[inx]  
    
    
    # command
    def _command_save_cl(self) :
        dataInst = self.get_data()
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)
        if skeleton is None :
            return

        clOutPath = dataInst.get_cl_out_path()
        skelinfo = dataInst.get_skelinfo(clinfoInx)

        blenderName = skelinfo.BlenderName
        outputFileName = skelinfo.BlenderName
        outputFullPath = os.path.join(clOutPath, f"{outputFileName}.json")
        skeleton.save(outputFullPath, blenderName)


    # ui event 
    def _on_tab_changed(self, index) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        userData = self._get_userdata()
        if userData is None :
            return
        clinfoinx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoinx)
        if skeleton is None :
            return
        
        print(f"Tab changed: index={index}")
        if self.m_state >= 0 :
            self._get_substate(self.m_state).process_end()
        self.m_state = index
        if self.m_state >= 0 :
            self._get_substate(self.m_state).process_init()
        self.m_mediator.update_viewer()
    def _on_return_pressed_label_name(self) :
        labelName = self.m_editLabelName.text()
        self.m_editLabelName.setText("")
        if self.m_comDragSelCLTP is not None :
            self.m_comDragSelCLTP.command_label_name(labelName)
        if self.m_comTreeVessel is not None :
            self.m_comTreeVessel.command_init_tree_vessel()
        self.m_mediator.update_viewer()
    def _on_btn_labeling_to_descendant(self) :
        if self.m_comDragSelCLTP is not None :
            self.m_comDragSelCLTP.command_labeling_descendant()
        if self.m_comTreeVessel is not None :
            self.m_comTreeVessel.command_init_tree_vessel()
        self.m_mediator.update_viewer()
    def _on_return_pressed_cutting_name(self) :
        labelName = self.m_editCuttingName.text()
        self.m_editCuttingName.setText("")
        self._get_substate(self.m_state).on_return_pressed_cutting_name(labelName)
    def _on_btn_save_cutting_mesh(self) :
        self._get_substate(self.m_state).on_btn_save_cutting_mesh()

    # private


    # slot 
    def slot_vessel_hierarchy(self, listCLID : list) :
        self._get_substate(self.m_state).slot_vessel_hierarchy(listCLID)
        self.m_mediator.update_viewer()
    def slot_invalid_node(self, node : treeVessel.CNodeVesselHier) :
        self.m_mediator.update_viewer()


if __name__ == '__main__' :
    pass


# print ("ok ..")

