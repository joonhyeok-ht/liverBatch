import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import math

from scipy.spatial import KDTree
# from scipy.spatial import cKDTree

from PySide6.QtCore import Qt, QItemSelection, QItemSelectionModel
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTreeView, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QListWidgetItem, QMessageBox, QAbstractItemView
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
import dataGroup as dataGroup

import operation as operation
import clMask as clMask

import tabState as tabState

import treeVessel as treeVessel
import userDataCommon as userDataCommon

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algMeshLib as algMeshLib
import AlgUtil.algVTK as algVTK

import vtkObjSTL as vtkObjSTL
import vtkObjInterface as vtkObjInterface
import vtkObjGuideMeshBound as vtkObjGuideMeshBound

import com.component as component
import com.componentSelectionCL as componentSelectionCL
import com.componentTreeVessel as componentTreeVessel
import com.componentTerritory as componentTerritory


'''
- label별 cl 저장
- label별 whole-sub 인식 
    - 이 때, clMask 고려 
'''

class MyTreeView(QTreeView) :
    def keyPressEvent(self, event) :
        if event.key() == Qt.Key_Escape :
            self.clearSelection()
        else :
            super().keyPressEvent(event)


class CTabStateCommonTerritory(tabState.CTabState) :
    s_terriColor = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 0.6])


    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_opSelectionCL = operation.COperationDragSelectionCL(mediator)
        self.m_comDragSelCLLabel = None
        self.m_comTreeVessel = None
        self.m_comTerritory = None
    def clear(self) :
        # input your code
        if self.m_comDragSelCLLabel is not None :
            self.m_comDragSelCLLabel.clear()
            self.m_comDragSelCLLabel = None
        if self.m_comTreeVessel is not None :
            self.m_comTreeVessel.clear()
            self.m_comTreeVessel = None
        if self.m_comTerritory is not None :
            self.m_comTerritory.clear()
            self.m_comTerritory = None
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

        # organ ui init
        self.m_cbOrganName.blockSignals(True)
        self.m_cbOrganName.clear()
        iCnt = dataInst.get_terriinfo_count()
        for terriInx in range(0, iCnt) :
            terriInfo = dataInst.get_terriinfo(terriInx)
            organName = terriInfo.BlenderName
            self.m_cbOrganName.addItem(organName)
        self.m_cbOrganName.blockSignals(True)
        self._setui_organ_name(0)

        # component create
        self.m_comDragSelCLLabel = componentSelectionCL.CComDragSelCLLabel(self)
        self.m_comDragSelCLLabel.InputOPDragSelCL = self.m_opSelectionCL
        self.m_comDragSelCLLabel.InputUIRBSelSingle = self.m_rbSelectionSingle
        self.m_comDragSelCLLabel.InputUIRBSelDescendant = self.m_rbSelectionDescendant
        self.m_comDragSelCLLabel.process_init()

        self.m_comTreeVessel = componentTreeVessel.CComTreeVessel(self)
        self.m_comTreeVessel.InputUITVVessel = self.m_tvVessel
        self.m_comTreeVessel.signal_vessel_hierarchy = self.slot_vessel_hierarchy
        self.m_comTreeVessel.process_init()

        self.m_comTerritory = componentTerritory.CComTerritory(self)
        self.m_comTerritory.process_init()

        # component init
        self.m_comTerritory.command_changed_organ_name(self._getui_organ_name(), self.m_checkOrgan.isChecked())
        
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
        if self.m_comTreeVessel is not None :
            self.m_comTreeVessel.process_end()
            self.m_comTreeVessel = None
        if self.m_comTerritory is not None :
            self.m_comTerritory.process_end()
            self.m_comTerritory = None

        self.m_mediator.update_viewer()

    def init_ui(self) :
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        label = QLabel("-- Labeling --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        layout, listRB = self.m_mediator.create_layout_label_radio("Selection Mode", ["Single", "Descendant"])
        self.m_rbSelectionSingle = listRB[0]
        self.m_rbSelectionDescendant = listRB[1]
        self.m_rbSelectionSingle.setChecked(True)
        tabLayout.addLayout(layout)

        layout, self.m_editLabelName = self.m_mediator.create_layout_label_editbox("Label Name", False)
        self.m_editLabelName.returnPressed.connect(self._on_return_pressed_label_name)
        tabLayout.addLayout(layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)


        label = QLabel("-- Vessel Hierarchy --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        # self.m_tvVessel = QTreeView()
        self.m_tvVessel = MyTreeView()
        self.m_tvVessel.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        # self.m_tvVessel.clicked.connect(self._on_tv_vessel_item_clicked)
        tabLayout.addWidget(self.m_tvVessel)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        label = QLabel("-- Territory --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        self.m_checkOrgan = QCheckBox("Show/Hide Organ ")
        self.m_checkOrgan.setChecked(False)
        self.m_checkOrgan.stateChanged.connect(self._on_check_show_organ)
        tabLayout.addWidget(self.m_checkOrgan)

        layout, self.m_cbOrganName = self.m_mediator.create_layout_label_combobox("Selection Organ")
        self.m_cbOrganName.currentIndexChanged.connect(self._on_cb_organ_name)
        tabLayout.addLayout(layout)

        btn = QPushButton("Do Territory")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_do_territory)
        tabLayout.addWidget(btn)

        btn = QPushButton("Save")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_save)
        tabLayout.addWidget(btn)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        # btn = QPushButton("Save Vessel")
        # btn.setStyleSheet(self.get_btn_stylesheet())
        # btn.clicked.connect(self._on_btn_save_vessel)
        # tabLayout.addWidget(btn)

        lastUI = line
        tabLayout.setAlignment(lastUI, Qt.AlignmentFlag.AlignTop)


    def clicked_mouse_rb(self, clickX, clickY) :
        if self.m_comDragSelCLLabel is None :
            return
        self.m_comDragSelCLLabel.click(clickX, clickY)
        self.m_mediator.update_viewer()
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        if self.m_comDragSelCLLabel is None :
            return
        self.m_comDragSelCLLabel.click_with_shift(clickX, clickY)
        self.m_mediator.update_viewer()
    def release_mouse_rb(self) :
        if self.m_comDragSelCLLabel is None :
            return
        self.m_comDragSelCLLabel.release(0, 0)
        self.m_mediator.update_viewer()
    def mouse_move_rb(self, clickX, clickY) :
        if self.m_comDragSelCLLabel is None :
            return
        self.m_comDragSelCLLabel.move(clickX, clickY)
        self.m_mediator.update_viewer()
    def key_press(self, keyCode : str) :
        if keyCode == "Escape" :
            self.m_opSelectionCL.process_reset()
            if self.m_comTreeVessel is not None :
                self.m_comTreeVessel.command_clear_selection()
            # self.m_tvVessel.clearSelection()
            self.m_mediator.unref_key_type(data.CData.s_territoryType)
            self.m_mediator.update_viewer()
        elif keyCode == "c" :
            if self.m_rbSelectionSingle.isChecked() == True :
                self.m_rbSelectionDescendant.setChecked(True)
            else :
                self.m_rbSelectionSingle.setChecked(True)


    # protected
    def _get_userdata(self) -> userDataCommon.CUserDataCommon :
        return self.get_data().find_userdata(userDataCommon.CUserDataCommon.s_userDataKey)
    
    
    # ui setting
    def _setui_organ_name(self, inx : int) :
        self.m_cbOrganName.blockSignals(True)
        self.m_cbOrganName.setCurrentIndex(inx)
        self.m_cbOrganName.blockSignals(False)

    def _getui_tree_vessel_node(self) :
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
    def _getui_organ_name_index(self) -> int :
        return self.m_cbOrganName.currentIndex()
    def _getui_organ_name(self) -> str :
        return self.m_cbOrganName.currentText()

    
    # command
    

    # ui event 
    def _on_return_pressed_label_name(self) :
        labelName = self.m_editLabelName.text()
        self.m_editLabelName.setText("")
        if self.m_comDragSelCLLabel is not None :
            self.m_comDragSelCLLabel.command_label_name(labelName)
            self.m_comTreeVessel.command_init_tree_vessel()
        self.m_mediator.update_viewer()
    def _on_check_show_organ(self, state) :
        '''
        state
            - 0 : unchecked
            - 1 : partially checked
            - 2 : checked
        '''
        bCheck = False
        if state == 2 :
            bCheck = True
        else :
            bCheck = False
        if self.m_comTerritory is not None :
            self.m_comTerritory.command_show_organ(bCheck)
        self.m_mediator.update_viewer()
    def _on_cb_organ_name(self, index) :
        opSelectionCL = self.m_opSelectionCL
        opSelectionCL.process_reset()
        if self.m_comTerritory is not None :
            self.m_comTerritory.command_changed_organ_name(self._getui_organ_name(), self.m_checkOrgan.isChecked())
        self.m_mediator.update_viewer()
    def _on_btn_do_territory(self) :
        self.m_opSelectionCL.process_reset()
        self.m_comTreeVessel.command_clear_selection()
        if self.m_comTerritory is not None :
            self.m_comTerritory.command_do_territory()
            QMessageBox.information(self.m_mediator, "Alarm", "complete to do territory")
        self.m_mediator.update_viewer()
    def _on_btn_save(self) :
        if self.m_comTerritory is None :
            return
        dataGroup = self.m_comTerritory.OutputDataGroupPolyData
        if dataGroup is None :
            return
        listLabel = dataGroup.get_all_polydata_label()
        if listLabel is None or len(listLabel) < 1 :
            return
        terriOutPath = self.get_data().get_terri_out_path()
        if os.path.exists(terriOutPath) == False :
            os.makedirs(terriOutPath)
        for label in listLabel :
            terriPolyData = dataGroup.get_polydata(label)

            if label == "" :
                label = "default"
            fullPath = os.path.join(terriOutPath, f"{label}.stl")
            algVTK.CVTK.save_poly_data_stl(fullPath, terriPolyData)
        QMessageBox.information(self.m_mediator, "Alarm", "completed territory saved")


    # slot
    def slot_vessel_hierarchy(self, listCLID : list) :
        self.m_opSelectionCL.process_reset()
        self.m_opSelectionCL.ChildSelectionMode = False

        clinfoInx = self.get_clinfo_index()

        for clID in listCLID :
            key = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, clID)
            self.m_opSelectionCL.add_selection_key(key)
        self.m_opSelectionCL.process()

        if self.m_comTerritory is not None :
            self.m_comTerritory.command_show_territory(listCLID)
        self.m_mediator.update_viewer()


    # private

        

if __name__ == '__main__' :
    pass


# print ("ok ..")

