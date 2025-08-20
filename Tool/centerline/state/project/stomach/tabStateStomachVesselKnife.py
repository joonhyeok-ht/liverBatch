import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import math

from scipy.spatial import KDTree
# from scipy.spatial import cKDTree

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTreeView, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QListWidgetItem, QMessageBox
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

import operation as operation

import tabState as tabState

import treeVessel as treeVessel
import userDataStomach as userDataStomach

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algMeshLib as algMeshLib
import AlgUtil.algVTK as algVTK

import VtkObj.vtkObjVertex as vtkObjVertex
import VtkObj.vtkObjText as vtkObjText
import VtkObj.vtkObjLine as vtkObjLine
import vtkObjSTL as vtkObjSTL
import vtkObjInterface as vtkObjInterface
import vtkObjGuideMeshBound as vtkObjGuideMeshBound

import command.commandTerritory as commandTerritory
import command.commandKnife as commandKnife
import command.commandVesselKnife as commandVesselKnife

import com.componentSelectionCL as componentSelectionCL
import com.componentTreeVessel as componentTreeVessel
import com.componentVesselCutting as componentVesselCutting



class CTabStateStomachVesselKnife(tabState.CTabState) :
    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_opSelectionCL = operation.COperationSelectionCL(mediator)
        self.m_comTreeVessel = None
        self.m_comVesselCutting = None
    def clear(self) :
        # input your code
        self.m_opSelectionCL = None
        if self.m_comTreeVessel is not None :
            self.m_comTreeVessel.clear()
        if self.m_comVesselCutting is not None :
            self.m_comVesselCutting.clear()
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
        self.m_opSelectionCL.ParentSelectionMode = False
        self.m_opSelectionCL.process_reset()

        self._init_cl_label()
        self.__init_vessel_territory()

        self.m_comTreeVessel = componentTreeVessel.CComTreeVessel(self)
        self.m_comTreeVessel.InputUITVVessel = self.m_tvVessel
        self.m_comTreeVessel.signal_vessel_hierarchy_node = self.slot_vessel_hierarchy_node
        self.m_comTreeVessel.process_init()

        self.m_comVesselCutting = componentVesselCutting.CComVesselCutting(self)
        self.m_comVesselCutting.InputTreeVessel = self.m_comTreeVessel.TreeVessel
        self.m_comVesselCutting.InputUILVInvalidVessel = self.m_lvInvalidNode
        self.m_comVesselCutting.signal_invalid_node = self.slot_invalid_node
        self.m_comVesselCutting.signal_finished_knife = self.slot_finished_knife
        self.m_comVesselCutting.process_init()
        
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
        
        if self.m_comTreeVessel is not None :
            self.m_comTreeVessel.process_end()
        if self.m_comVesselCutting is not None :
            self.m_comVesselCutting.process_end()
        
        self.m_opSelectionCL.process_reset()
        self._clear_cl_label()
        self.__clear_vessel_territory()
        self.m_mediator.update_viewer()

    def init_ui(self) :
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        label = QLabel("-- Stomach Vessel Hierarchy Test --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        self.m_tvVessel = QTreeView()
        tabLayout.addWidget(self.m_tvVessel)

        self.m_lvInvalidNode = QListWidget()
        tabLayout.addWidget(self.m_lvInvalidNode)

        btn = QPushButton("View Separated Vessel")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_view_separated_vessel)
        tabLayout.addWidget(btn)

        btn = QPushButton("Save Vessel")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_save_vessel)
        tabLayout.addWidget(btn)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        lastUI = line
        tabLayout.setAlignment(lastUI, Qt.AlignmentFlag.AlignTop)


    def clicked_mouse_rb(self, clickX, clickY) :
        if self.m_comVesselCutting is not None :
            self.m_comVesselCutting.click(clickX, clickY)
        self.m_mediator.update_viewer()
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        self.m_mediator.update_viewer()
    def release_mouse_rb(self) :
        if self.m_comVesselCutting is not None :
            self.m_comVesselCutting.release(0, 0)
        self.m_mediator.update_viewer()
    def mouse_move_rb(self, clickX, clickY) :
        if self.m_comVesselCutting is not None :
            self.m_comVesselCutting.move(clickX, clickY)
        self.m_mediator.update_viewer()
    def key_press(self, keyCode : str) :
        if keyCode == "Escape" :
            self.m_opSelectionCL.process_reset()
            self.__clear_vessel_territory()
            if self.m_comTreeVessel is not None :
                self.m_comTreeVessel.command_clear_selection()
            if self.m_comVesselCutting is not None :
                self.m_comVesselCutting.command_clear_selection()
            self.m_mediator.update_viewer()
        elif keyCode == "m" :
            pass


    # protected
    def _get_userdata(self) -> userDataStomach.CUserDataStomach :
        return self.get_data().find_userdata(userDataStomach.CUserDataStomach.s_userDataKey)
    
    # ui setting
    
    
    # command
    def _command_save_vessel(self) :
        if self.m_comTreeVessel is None :
            return 
        
        dataInst = self.get_data()
        patientPath = dataInst.DataInfo.PatientPath
        tpinfoPath = os.path.join(patientPath, userDataStomach.CUserDataStomach.s_tpInfoPath)
        tpinfoOutPath = os.path.join(tpinfoPath, "out")
        
        if os.path.exists(tpinfoOutPath) == False :
            os.makedirs(tpinfoOutPath)
        # else : 
        #     for filename in os.listdir(tpinfoOutPath):
        #         fullPath = os.path.join(tpinfoOutPath, filename)
        #         try:
        #             if os.path.isfile(fullPath) or os.path.islink(fullPath):
        #                 os.remove(fullPath)
        #             elif os.path.isdir(fullPath):
        #                 shutil.rmtree(fullPath)
        #         except Exception as e:
        #             print(f'파일 삭제 중 오류 발생: {fullPath} -> {e}')
        
        mergeCmd = treeVessel.CMergePolyData()
        mergeCmd.process(self.m_comTreeVessel.TreeVessel)

        for label, polyData in mergeCmd.OutDicPolyData.items() :
            fullPath = os.path.join(tpinfoOutPath, f"{label}.stl")
            algVTK.CVTK.save_poly_data_stl(fullPath, polyData)


    # ui event 
    def _on_btn_view_separated_vessel(self) :
        if self.m_comVesselCutting is None :
            return
        dataInst = self.get_data()
        clinfoInx = self.get_clinfo_index()
        vesselKey = data.CData.make_key(data.CData.s_vesselType, clinfoInx, 0)
        vesselObj = dataInst.find_obj_by_key(vesselKey)
        if vesselObj is None :
            return
        self.m_comVesselCutting.command_separate_vessel(vesselObj.PolyData)
        QMessageBox.information(self.m_mediator, "Alarm", "complete to separate vessel")
    def _on_btn_save_vessel(self) :
        self._command_save_vessel()
        QMessageBox.information(self.m_mediator, "Alarm", "complete to save vessel")


    # private
    def __init_vessel_territory(self) :
        self.m_mediator.remove_key_type(data.CData.s_territoryType)
    def __clear_vessel_territory(self) :
        self.m_mediator.remove_key_type(data.CData.s_territoryType)
    def __add_vessel_territory(self, node : treeVessel.CNodeVesselHier) :
        self.__clear_vessel_territory()

        dataInst = self.get_data()
        validVessel = node.get_valid_vessel()
        if validVessel is None :
            return 

        key = data.CData.make_key(data.CData.s_territoryType, 0, 0)
        terriObj = vtkObjInterface.CVTKObjInterface()
        terriObj.KeyType = data.CData.s_territoryType
        terriObj.Key = key
        terriObj.Color = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 0.0])
        terriObj.Opacity = 0.5
        terriObj.PolyData = validVessel
        dataInst.add_vtk_obj(terriObj)
        self.m_mediator.ref_key_type(data.CData.s_territoryType)


    # slot
    def slot_vessel_hierarchy_node(self, listCLID : list, listNode : list) :
        if len(listNode) == 0 :
            return
        clinfoInx = self.get_clinfo_index()

        self.m_opSelectionCL.process_reset()
        for clID in listCLID :
            clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, clID)
            self.m_opSelectionCL.add_selection_key(clKey)
        self.m_opSelectionCL.process()

        node = listNode[0]
        self.__add_vessel_territory(node)
        self.m_mediator.update_viewer()
    def slot_invalid_node(self, node : treeVessel.CNodeVesselHier) :
        self.__add_vessel_territory(node)
        self.m_mediator.update_viewer()
    def slot_finished_knife(self, node : treeVessel.CNodeVesselHier) :
        self.__add_vessel_territory(node)
        self.m_mediator.update_viewer()

        

if __name__ == '__main__' :
    pass


# print ("ok ..")

