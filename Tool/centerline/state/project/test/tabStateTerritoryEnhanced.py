import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox
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


import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algSkeletonGraph as algSkeletonGraph

import command.commandTerritory as commandTerritory

import data as data

import operation as operation

import tabState as tabState

import clMask as clMask

import vtkObjInterface as vtkObjInterface
import vtkObjOutsideCL as vtkObjOutsideCL

import command.commandTerritoryVessel as commandTerritoryVessel
import command.commandKnife as commandKnife

import subStateKnifeEn as subStateKnifeEn
import subStateKnifeCLEn as subStateKnifeCLEn
import subStateKnifeCLKnifeEn as subStateKnifeCLKnifeEn


class CTabStateTerritoryEnhanced(tabState.CTabState) :
    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_state = 0
        self.m_listSubState = []
        self.m_listSubState.append(subStateKnifeCLEn.CSubStateKnifeCLEn(self))
        self.m_listSubState.append(subStateKnifeCLKnifeEn.CSubStateKnifeCLKnifeEn(self))

        self.m_opSelectionCL = operation.COperationSelectionCL(mediator)
        self.m_clMask = None
        self.m_terriInfo = None
        self.m_organKey = ""
        self.m_wholeVesselPolyData = None
    def clear(self) :
        # input your code
        self.m_state = 0
        self.m_listSubState.clear()

        self.m_opSelectionCL.clear()
        self.m_opSelectionCL = None

        self.m_organKey = ""

        self.m_terriInfo = None
        if self.m_clMask is not None :
            self.m_clMask.clear()
            self.m_clMask = None
        self.m_wholeVesselPolyData = None
        super().clear()
    def process_init(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)
        if skeleton is None :
            return 
        opSelectionCL = self.m_opSelectionCL
        opSelectionCL.Skeleton = skeleton

        self.m_cbTerriOrganName.blockSignals(True)
        self.m_cbTerriOrganName.clear()
        iCnt = dataInst.get_terriinfo_count()
        for terriInx in range(0, iCnt) :
            terriInfo = dataInst.get_terriinfo(terriInx)
            organName = terriInfo.BlenderName
            self.m_cbTerriOrganName.addItem(organName)
        self.m_cbTerriOrganName.blockSignals(True)
        self.setui_terri_organ_name(0)

        self.m_wholeVesselPolyData = None
        self._command_changed_organ_name()
        self._get_substate(self.m_state).process_init()
        self.m_mediator.update_viewer()
        
    def process(self) :
        pass
    def process_end(self) :
        self._get_substate(self.m_state).process_end()

        self.m_wholeVesselPolyData = None
        self.m_mediator.unref_key(self.m_organKey)
        self.m_mediator.remove_key_type(data.CData.s_outsideKeyType)
        self.m_mediator.clear_cmd()
        self.m_mediator.update_viewer()

    def init_ui(self) :
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        label = QLabel("-- Territory Info --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        layout, self.m_cbTerriOrganName = self.m_mediator.create_layout_label_combobox("Selection Organ")
        self.m_cbTerriOrganName.currentIndexChanged.connect(self._on_cb_terri_organ_name)
        tabLayout.addLayout(layout)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        label = QLabel("-- Selection Unit --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        layout, retList = self.m_mediator.create_layout_label_radio("Selection Unit", ["CL", "Knife"])
        self.m_rbSelectionUnitCL = retList[0]
        self.m_rbSelectionUnitKnife = retList[1]
        self.m_rbSelectionUnitCL.toggled.connect(self._on_rb_selection_unit_cl)
        self.m_rbSelectionUnitKnife.toggled.connect(self._on_rb_selection_unit_knife)
        self.setui_selection_unit_cl(True)
        tabLayout.addLayout(layout)

        self.m_checkCLHierarchy = QCheckBox("Selection Centerline Hierarchy ")
        self.m_checkCLHierarchy.setChecked(False)
        self.m_checkCLHierarchy.stateChanged.connect(self._on_check_cl_hierarchy)
        tabLayout.addWidget(self.m_checkCLHierarchy)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        btn = QPushButton("View Territory")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_view_territory)
        tabLayout.addWidget(btn)

        btn = QPushButton("View Vessel")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_view_vessel)
        tabLayout.addWidget(btn)

        btn = QPushButton("Save")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_save_separation)
        tabLayout.addWidget(btn)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        lastUI = line
        tabLayout.setAlignment(lastUI, Qt.AlignmentFlag.AlignTop)

    def clicked_mouse_rb(self, clickX, clickY) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        self._get_substate(self.m_state).clicked_mouse_rb(clickX, clickY)
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        self._get_substate(self.m_state).clicked_mouse_rb_shift(clickX, clickY)
    def release_mouse_rb(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        self._get_substate(self.m_state).release_mouse_rb()
    def mouse_move_rb(self, clickX, clickY) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        self._get_substate(self.m_state).mouse_move_rb(clickX, clickY)
    def key_press(self, keyCode : str) :
        self._get_substate(self.m_state).key_press(keyCode)
    def key_press_with_ctrl(self, keyCode : str) : 
        self._get_substate(self.m_state).key_press_with_ctrl(keyCode)


    # ui 
    def setui_terri_organ_name(self, inx : int) :
        self.m_cbTerriOrganName.blockSignals(True)
        self.m_cbTerriOrganName.setCurrentIndex(inx)
        self.m_cbTerriOrganName.blockSignals(False)
    def setui_selection_unit_cl(self, bCheck : bool) :
        self.m_rbSelectionUnitCL.blockSignals(True)
        self.m_rbSelectionUnitCL.setChecked(bCheck)
        self.m_rbSelectionUnitCL.blockSignals(False)
    def setui_selection_unit_knife(self, bCheck : bool) :
        self.m_rbSelectionUnitKnife.blockSignals(True)
        self.m_rbSelectionUnitKnife.setChecked(bCheck)
        self.m_rbSelectionUnitKnife.blockSignals(False)
    
    def getui_terri_organ_name_index(self) -> int :
        return self.m_cbTerriOrganName.currentIndex()
    def getui_terri_organ_name(self) -> str :
        return self.m_cbTerriOrganName.currentText()


    # protected
    def _get_substate(self, inx : int) -> subStateKnifeEn.CSubStateKnifeEn :
        return self.m_listSubState[inx]  
    
    
    def _command_changed_organ_name(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False : 
            return
        
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)
        if skeleton is None :
            return 
        
        if self.m_organKey != "" :
            self.m_mediator.unref_key(self.m_organKey)
        self.m_mediator.remove_key_type(data.CData.s_outsideKeyType)
        self.m_mediator.remove_key_type(data.CData.s_territoryType)
        if self.m_clMask is not None :
            self.m_clMask.clear()
            self.m_clMask = None
        
        opSelectionCL = self.m_opSelectionCL
        opSelectionCL.process_reset()

        selectionOrganName = self.getui_terri_organ_name()
        findTerriInx = dataInst.find_terriinfo_index_by_blender_name(selectionOrganName)
        self.m_terriInfo = dataInst.find_terriinfo_by_blender_name(selectionOrganName)
        self.m_organKey = data.CData.make_key(data.CData.s_organType, 0, findTerriInx)
        organObj = dataInst.find_obj_by_key(self.m_organKey)
        if organObj is None :
            print(f"not found organObj : {self.m_organKey}")
            return
        self.m_mediator.ref_key(self.m_organKey)

        # clMask setting
        self.m_clMask = clMask.CCLMask(organObj.PolyData)
        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            self.m_clMask.attach_cl(cl)
        self.m_mediator.load_outside_key(self.m_clMask)
        self.m_mediator.ref_key_type(data.CData.s_outsideKeyType)
    def _command_check_cl_hierarchy(self, bCheck : bool) :
        operation.COperationSelectionCL.checked_hierarchy(self.m_opSelectionCL, bCheck)
        self.m_mediator.update_viewer()


    # ui event
    def _on_cb_terri_organ_name(self, index) :
        self._command_changed_organ_name()
    def _on_rb_selection_unit_cl(self) :
        if self.m_rbSelectionUnitCL.isChecked() :
            self.m_state = 0
            self._get_substate(self.m_state).process_init()
        else :
            self._get_substate(self.m_state).process_end()
    def _on_rb_selection_unit_knife(self) :
        if self.m_rbSelectionUnitKnife.isChecked() :
            self.m_state = 1
            self._get_substate(self.m_state).process_init()
        else :
            self._get_substate(self.m_state).process_end()
    def _on_check_cl_hierarchy(self, state) :
        '''
        state
            - 0 : unchecked
            - 1 : partially checked
            - 2 : checked
        '''
        if state == 2 :
            bCheck = True
        else :
            bCheck = False
        self._command_check_cl_hierarchy(bCheck)
        self._get_substate(self.m_state).cl_hierarchy()
    def _on_return_pressed_clname(self) :
        # Enter키를 누르면 호출되는 함수
        clName = self.m_editCLName.text()  # QLineEdit에 입력된 텍스트를 가져옴
        # self._update_clname(clName)
    def _on_btn_view_territory(self) :
        self._get_substate(self.m_state).on_btn_view_territory()
    def _on_btn_view_vessel(self) :
        self._get_substate(self.m_state).on_btn_view_vessel()
    def _on_btn_save_separation(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False : 
            return 
        if self.m_organKey == "" :
            return
        
        savePath, _ = QFileDialog.getSaveFileName(
            self.get_main_widget(),
            "Save Mesh File", 
            "", 
            "STL Files (*.stl)"
        )
        if savePath == "" :
            return

        dirPath = os.path.dirname(savePath) 
        fileName = os.path.splitext(os.path.basename(savePath))[0]

        clinfoinx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoinx)
        if skeleton is None :
            return
        
        # save territory
        key = data.CData.make_key(data.CData.s_territoryType, 0, 0)
        obj = dataInst.find_obj_by_key(key)
        if obj is None :
            print("not found territory")
            return
        polyData = obj.PolyData
        algVTK.CVTK.save_poly_data_stl(savePath, polyData)
        print("Territory file saved successfully.")

        # save whole
        fullPath = os.path.join(dirPath, f"{fileName}_whole.stl")
        key = data.CData.make_key(data.CData.s_territoryType, 0, 1)
        obj = dataInst.find_obj_by_key(key)
        if obj is None :
            print("not found whole")
            return
        polyData = obj.PolyData
        algVTK.CVTK.save_poly_data_stl(fullPath, polyData)
        print("whole file saved successfully.")

        # save vessel
        fullPath = os.path.join(dirPath, f"{fileName}_vessel.stl")
        key = data.CData.make_key(data.CData.s_territoryType, 0, 2)
        obj = dataInst.find_obj_by_key(key)
        if obj is None :
            print("not found sub-vessel")
            return
        polyData = obj.PolyData
        algVTK.CVTK.save_poly_data_stl(fullPath, polyData)
        print("sub file saved successfully.")

        # save wholeVessel
        # fullPath = os.path.join(dirPath, f"{fileName}_whole.stl")
        # if self.m_wholeVesselPolyData is None :
        #     print("not found whole vessel")
        #     return
        # algVTK.CVTK.save_poly_data_stl(fullPath, self.m_wholeVesselPolyData)
        # print("whole vessel file saved successfully.")


if __name__ == '__main__' :
    pass


# print ("ok ..")

