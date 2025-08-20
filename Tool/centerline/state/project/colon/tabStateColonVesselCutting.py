import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

from scipy.spatial import KDTree

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QMessageBox, QGroupBox, QButtonGroup, QRadioButton 
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

import state.project.colon.userDataColon as userDataColon

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algMeshLib as algMeshLib
import AlgUtil.algVTK as algVTK

import VtkObj.vtkObjVertex as vtkObjVertex
import vtkObjSTL as vtkObjSTL
import vtkObjInterface as vtkObjInterface
import vtkObjGuideMeshBound as vtkObjGuideMeshBound

import com.componentSelectionCL as componentSelectionCL

import command.commandTerritory as commandTerritory
import componentColonVesselCutting as componentColonVesselCutting


class CTabStateColonVesselCutting(tabState.CTabState) :
    s_terriColor = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 0.6])

    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_opSelectionCL = operation.COperationDragSelectionCL(mediator)
        self.m_comDragSelCLLabel = None
        self.m_comVesselCutting = None
    def clear(self) :
        # input your code
        if self.m_comDragSelCLLabel is not None :
            self.m_comDragSelCLLabel.clear()
            self.m_comDragSelCLLabel = None
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
        self.m_opSelectionCL.Skeleton = skeleton
        self.m_opSelectionCL.ChildSelectionMode = False

        # component create
        self.m_comDragSelCLLabel = componentSelectionCL.CComDragSelCLLabel(self)
        self.m_comDragSelCLLabel.InputOPDragSelCL = self.m_opSelectionCL
        self.m_comDragSelCLLabel.InputUIRBSelSingle = self.m_rbSelectionSingle
        self.m_comDragSelCLLabel.InputUIRBSelDescendant = self.m_rbSelectionDescendant
        self.m_comDragSelCLLabel.process_init()

        self.m_comVesselCutting = componentColonVesselCutting.CComColonVesselCutting(self)
        self.m_comVesselCutting.InputUILVVessel = self.m_lvVessel
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
        
        self.m_opSelectionCL.process_reset()

        if self.m_comDragSelCLLabel is not None :
            self.m_comDragSelCLLabel.process_end()
            self.m_comDragSelCLLabel = None
        if self.m_comVesselCutting is not None :
            self.m_comVesselCutting.process_end()
            self.m_comVesselCutting = None

        self.m_mediator.update_viewer()

    def init_ui(self) :
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        label = QLabel("-- Vessel Cutting --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        layout, listRB = self.m_mediator.create_layout_label_radio("Selection Mode", ["Single", "Descendant"])
        self.m_rbSelectionSingle = listRB[0]
        self.m_rbSelectionDescendant = listRB[1]
        tabLayout.addLayout(layout)

        self.m_rbSelectionSingle.setChecked(True)
        self.m_rbSelectionSingle.setEnabled(False)
        self.m_rbSelectionDescendant.setEnabled(False)


        groupBox = QGroupBox("Edit Mode")
        groupBox.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        groupBoxLayout = QHBoxLayout()

        self.m_rbEditLabeling = QRadioButton("Labeling")
        self.m_rbEditCutting = QRadioButton("Vessel Cutting")
        bg = QButtonGroup()
        bg.addButton(self.m_rbEditLabeling)
        bg.addButton(self.m_rbEditCutting)

        groupBoxLayout.addWidget(self.m_rbEditLabeling)
        groupBoxLayout.addWidget(self.m_rbEditCutting)
        groupBox.setLayout(groupBoxLayout)
        tabLayout.addWidget(groupBox)

        self.m_rbEditLabeling.setChecked(True)
        self.m_rbEditCutting.toggled.connect(self._ob_rb_cutting)


        label = QLabel("-- Vessel List --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        self.m_lvVessel = QListWidget()
        tabLayout.addWidget(self.m_lvVessel)

        layout, self.m_editLabelName = self.m_mediator.create_layout_label_editbox("Label Name", False)
        self.m_editLabelName.returnPressed.connect(self._on_return_pressed_label_name)
        tabLayout.addLayout(layout)

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
        if self.m_comDragSelCLLabel is None :
            return
        if self.getui_rb_labeling() == True :
            self.m_comDragSelCLLabel.click(clickX, clickY)
        else :
            self.m_comVesselCutting.click(clickX, clickY)
        self.m_mediator.update_viewer()
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        if self.m_comDragSelCLLabel is None :
            return
        if self.getui_rb_labeling() == True :
            self.m_comDragSelCLLabel.click_with_shift(clickX, clickY)
        else :
            self.m_comVesselCutting.click_with_shift(clickX, clickY)
        self.m_mediator.update_viewer()
    def release_mouse_rb(self) :
        if self.m_comDragSelCLLabel is None :
            return
        if self.getui_rb_labeling() == True :
            self.m_comDragSelCLLabel.release(0, 0)
        else :
            self.m_comVesselCutting.release(0, 0)
        self.m_mediator.update_viewer()
    def mouse_move_rb(self, clickX, clickY) :
        if self.m_comDragSelCLLabel is None :
            return
        if self.getui_rb_labeling() == True :
            self.m_comDragSelCLLabel.move(clickX, clickY)
        else :
            self.m_comVesselCutting.move(clickX, clickY)
        self.m_mediator.update_viewer()
    def key_press(self, keyCode : str) :
        if keyCode == "Escape" :
            self.m_opSelectionCL.process_reset()
            self.m_mediator.update_viewer()
        # elif keyCode == "c" :
        #     if self.m_rbSelectionSingle.isChecked() == True :
        #         self.m_rbSelectionDescendant.setChecked(True)
        #     else :
        #         self.m_rbSelectionSingle.setChecked(True)


    # protected
    def _get_userdata(self) -> userDataColon.CUserDataColon :
        return self.get_data().find_userdata(userDataColon.CUserDataColon.s_userDataKey)
    
    
    # ui setting
    def getui_rb_labeling(self) -> bool :
        return self.m_rbEditLabeling.isChecked()
    def getui_rb_cutting(self) -> bool :
        return self.m_rbEditCutting.isChecked()

    
    # command
    def _command_save_vessel(self) :
        if self.m_comVesselCutting is None : 
            return
        
        dicNode = {}
        dataInst = self.get_data()

        iCnt = self.m_comVesselCutting.get_vessel_node_count()
        for inx in range(0, iCnt) :
            node = self.m_comVesselCutting.get_vessel_node(inx)
            if node.m_name not in dicNode :
                dicNode[node.m_name] = []
            dicNode[node.m_name].append(node)
        
        for nodeName, nodeList in dicNode.items() :
            if len(nodeList) > 1 :
                append_filter = vtk.vtkAppendPolyData()
                for node in nodeList :
                    subVesselObj = dataInst.find_obj_by_key(node.m_subVesselKey)
                    subVesselPolydata = subVesselObj.PolyData
                    append_filter.AddInputData(subVesselPolydata)
                append_filter.Update()
                combinedPolydata = append_filter.GetOutput()
            else :
                node = nodeList[0] 
                subVesselObj = dataInst.find_obj_by_key(node.m_subVesselKey)
                combinedPolydata = subVesselObj.PolyData
            
            if combinedPolydata is None :
                continue
            if combinedPolydata.GetNumberOfPoints() == 0 :
                continue

            fileName = f"{nodeName}.stl"
            saveFullPath = os.path.join(dataInst.get_terri_out_path(), fileName)
            algVTK.CVTK.save_poly_data_stl(saveFullPath, combinedPolydata)

        QMessageBox.information(self.m_mediator, "Alarm", "complete to save vessel")
    

    # ui event 
    def _ob_rb_cutting(self, checked) :
        if checked :
            self.m_opSelectionCL.process_reset()
            self.m_mediator.update_viewer()
    def _on_return_pressed_label_name(self) :
        labelName = self.m_editLabelName.text()
        self.m_editLabelName.setText("")
        if self.m_comVesselCutting is not None :
            self.m_comVesselCutting.command_label_name(labelName)
        self.m_mediator.update_viewer()
    def _on_btn_save_vessel(self) :
        self._command_save_vessel()


        

if __name__ == '__main__' :
    pass


# print ("ok ..")

