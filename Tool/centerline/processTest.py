import sys
import os
import numpy as np
import math
from scipy.spatial import KDTree
import multiprocessing
import SimpleITK as sitk

import vtk
# import vtkmodules.vtkInteractionStyle
# import vtkmodules.vtkRenderingOpenGL2
# from vtkmodules.vtkCommonColor import vtkNamedColors
# from vtkmodules.vtkFiltersSources import vtkCylinderSource
# from vtkmodules.vtkRenderingCore import (
#     vtkActor,
#     vtkPolyDataMapper,
#     vtkRenderWindow,
#     vtkRenderWindowInteractor,
#     vtkRenderer
# )

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QRadioButton, QSlider, QMessageBox
#from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor


fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileToolPath = os.path.dirname(fileAbsPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)
print(fileCommonPipelinePath)
sys.path.append(fileAbsPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import AlgUtil.algLinearMath as algLinearMath

import VtkObj.vtkObj as vtkObj
import vtkObjCL as vtkObjCL
import vtkObjBr as vtkObjBr
import vtkObjEP as vtkObjEP
import vtkObjSTL as vtkObjSTL
import vtkObjOutsideCL as vtkObjOutsideCL

import VtkUI.vtkUI as vtkUI

import command.commandInterface as commandInterface

import state.tabState as tabState
import state.tabStatePatient as tabStatePatient
import state.tabStateSkelEdit as tabStateSkelEdit
import state.tabStateSkelLabeling as tabStateSkelEditLabeling
import state.tabStateTerritory as tabStateTerritory
import state.tabStateVesselRemodeling as tabStateVesselRemodeling
import state.operation as op

import data as data
import clMask as clMask
import vtkUIViewerCL as vtkUIViewerCL

# user data
import state.project.kidney.tabStateKidneySepTest as tabStateKidneySepTest
import state.project.colon.tabStateColonTerritory as tabStateColonTerritory
import state.project.colon.tabStateColonMerge as tabStateColonMerge
import state.project.stomach.tabStateStomachVesselKnife as tabStateStomachVesselKnife
import state.project.stomach.tabStateStomachVesselLabeling as tabStateStomachVesselLabeling
import state.project.test.tabStateTerritoryEnhanced as tabStateTerritoryEnhanced
#import state.project.test.tabStateKnife as tabStateKnife

import state.project.kidney.userDataKidney as userDataKidney
import state.project.colon.userDataColon as userDataColon
import state.project.stomach.userDataStomach as userDataStomach
import state.project.lung.userDataLung as userDataLung
import state.project.kidneyBatch.userDataKidneyBatch as userDataKidneyBatch
import state.project.stomachBatch.userDataStomachBatch as userDataStomachBatch


#sally--->
#import state.project.lung.tabStateReconLung as tabStateReconLung
import state.project.lung.tabStatePatientLung as tabStatePatientLung
import state.project.lung.tabStateSkelEditLung as tabStateSkelEditLung
import state.project.lung.tabStateSkelLabelingLung as tabStateSkelEditLabelingLung
import state.project.lung.tabStateTerritoryLung as tabStateTerritoryLung
import state.project.lung.tabStateLungVesselKnife as tabStateLungVesselKnife

import state.project.kidneyBatch.tabStatePatientKidneyBatch as tabStatePatientKidney
import state.project.stomachBatch.tabStatePatientStomachBatch as tabStatePatientStomach

#<---sally
class COutputRedirector :
    def __init__(self, listWidget) :
        self.m_listWdget = listWidget

    def write(self, message) :
        self.m_listWdget.addItem(message.strip())
        self.m_listWdget.scrollToBottom()
    def flush(self):
        pass


class CTestApp(QMainWindow) :
    # 일단 하드코딩 
    # 
    #  = [ #sally
    #     {"Recon" : "Recon"},
    #     {"Patient" : "Patient Info"},
    #     {"SkelEdit" : "Edit"},
    #     {"SkelLabeling" : "Labeling"},
    #     {"Territory" : "Territory"}
        
    # ]

    s_projectTypeInfo = {
         "StomachBatch" : {
            "TabInfo" : [
                {"TabName" : "Patient Info", "TabInst" : tabStatePatientStomach.CTabStatePatient},
            ],
            "UserDataKey" : userDataStomachBatch.CUserDataStomach.s_userDataKey,
            "UserDataInst" : userDataStomachBatch.CUserDataStomach
        },
         "KidneyBatch" : {
            "TabInfo" : [
                {"TabName" : "Patient Info", "TabInst" : tabStatePatientKidney.CTabStatePatient},
            ],
            "UserDataKey" : userDataKidneyBatch.CUserDataKidney.s_userDataKey,
            "UserDataInst" : userDataKidneyBatch.CUserDataKidney
        },
        "Lung" : {
            "TabInfo" : [
                {"TabName" : "Patient Info", "TabInst" : tabStatePatientLung.CTabStatePatient},
                {"TabName" : "Edit", "TabInst" : tabStateSkelEditLung.CTabStateSkelEdit},
                {"TabName" : "Labeling", "TabInst" : tabStateSkelEditLabelingLung.CTabStateSkelLabeling},
                {"TabName" : "Territory", "TabInst" : tabStateTerritoryLung.CTabStateTerritory},
                {"TabName" : "Cut", "TabInst" : tabStateTerritory.CTabStateTerritory},
                {"TabName" : "Vessel Knife", "TabInst" : tabStateLungVesselKnife.CTabStateLungVesselKnife},
            ],
            "UserDataKey" : userDataLung.CUserDataLung.s_userDataKey,
            "UserDataInst" : userDataLung.CUserDataLung
        },
        "Common" : {
            "TabInfo" : [
                {"TabName" : "Patient Info", "TabInst" : tabStatePatient.CTabStatePatient},
                {"TabName" : "Edit", "TabInst" : tabStateSkelEdit.CTabStateSkelEdit},
                {"TabName" : "Labeling", "TabInst" : tabStateSkelEditLabeling.CTabStateSkelLabeling},
                {"TabName" : "Territory", "TabInst" : tabStateTerritory.CTabStateTerritory},
                {"TabName" : "Territory Enhanced", "TabInst" : tabStateTerritoryEnhanced.CTabStateTerritoryEnhanced},
                {"TabName" : "VesselRemodeling", "TabInst" : tabStateVesselRemodeling.CTabStateVesselRemodeling},
            ],
            "UserDataKey" : "",
            "UserDataInst" : None
        },
        "Stomach" : {
            "TabInfo" : [
                {"TabName" : "Patient Info", "TabInst" : tabStatePatient.CTabStatePatient},
                {"TabName" : "Edit", "TabInst" : tabStateSkelEdit.CTabStateSkelEdit},
                {"TabName" : "Vessel Labeling", "TabInst" : tabStateStomachVesselLabeling.CTabStateStomachVesselLabeling},
                {"TabName" : "Vessel Knife", "TabInst" : tabStateStomachVesselKnife.CTabStateStomachVesselKnife},
                {"TabName" : "Vessel Remodeling", "TabInst" : tabStateVesselRemodeling.CTabStateVesselRemodeling},
            ],
            "UserDataKey" : userDataStomach.CUserDataStomach.s_userDataKey,
            "UserDataInst" : userDataStomach.CUserDataStomach
        },
        "Kidney" : {
            "TabInfo" : [
                {"TabName" : "Patient Info", "TabInst" : tabStatePatient.CTabStatePatient},
                {"TabName" : "Edit", "TabInst" : tabStateSkelEdit.CTabStateSkelEdit},
                {"TabName" : "Labeling", "TabInst" : tabStateSkelEditLabeling.CTabStateSkelLabeling},
                {"TabName" : "Territory", "TabInst" : tabStateTerritory.CTabStateTerritory},
                {"TabName" : "Kidney-Tumor Separation", "TabInst" : tabStateKidneySepTest.CTabStateKidneySepTest},
            ],
            "UserDataKey" : userDataKidney.CUserDataKidney.s_userDataKey,
            "UserDataInst" : userDataKidney.CUserDataKidney
        },
        "Liver" : {
            "TabInfo" : [
                {"TabName" : "Patient Info", "TabInst" : tabStatePatient.CTabStatePatient},
                {"TabName" : "Edit", "TabInst" : tabStateSkelEdit.CTabStateSkelEdit},
                {"TabName" : "Labeling", "TabInst" : tabStateSkelEditLabeling.CTabStateSkelLabeling},
                {"TabName" : "Territory", "TabInst" : tabStateTerritory.CTabStateTerritory},
                {"TabName" : "VesselRemodeling", "TabInst" : tabStateVesselRemodeling.CTabStateVesselRemodeling},
            ],
            "UserDataKey" : "",
            "UserDataInst" : None
        },
        "Colon" : {
            "TabInfo" : [
                {"TabName" : "Patient Info", "TabInst" : tabStatePatient.CTabStatePatient},
                {"TabName" : "Edit", "TabInst" : tabStateSkelEdit.CTabStateSkelEdit},
                {"TabName" : "Labeling", "TabInst" : tabStateSkelEditLabeling.CTabStateSkelLabeling},
                {"TabName" : "Colon Merge", "TabInst" : tabStateColonMerge.CTabStateColonMerge},
                {"TabName" : "Colon Territory", "TabInst" : tabStateColonTerritory.CTabStateColonTerritory},
            ],
            "UserDataKey" : userDataColon.CUserDataColon.s_userDataKey,
            "UserDataInst" : userDataColon.CUserDataColon
        },

    }

    def __init__(self, width : int, height : int) :
        super().__init__()

        self.m_width = width
        self.m_height = height

        self.m_styleSheetBtn = """
QPushButton {
                border: 2px solid #5F6368;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                border-color: #1A73E8;
            }
"""
        self.m_styleSheetTab = """
        QTabBar::tab {
            margin: 0;          
            padding: 5px 10px;
        }
        QTabWidget::pane {
            margin: 0;
        }
        QTabBar {
            alignment: left;
        }
"""

        try :
        # PyInstaller로 패키징된 실행 파일의 경우
            fileAbsPath = sys._MEIPASS
            fileAbsPath = "."
        except AttributeError :
            # 개발 환경에서
            fileAbsPath = os.path.abspath(os.path.dirname(__file__))
        
        fileToolPath = os.path.dirname(fileAbsPath)
        fileCommonPipelinePath = os.path.dirname(fileToolPath)

        self.m_projectType = "StomachBatch"
        self.m_filePath = fileAbsPath
        self.m_commonPipelinePath = fileCommonPipelinePath
        
# Sally Usser data로 가능하면 옮기기------------------------------------------>
        #sally
        self.m_colorList = [    
            # [1.00, 0.00, 0.00],  # #FF0000 기사용중
            # [0.00, 1.00, 0.00],  # #00FF00 기사용중
            # [0.50, 0.50, 0.50],  # #808080 기사용중
            # [1.00, 1.00, 0.00],  # #FFFF00 기사용중   
            [0.00, 0.00, 1.00],  # #0000FF
            [1.00, 0.00, 1.00],  # #FF00FF
            [0.00, 1.00, 1.00],  # #00FFFF
            [1.00, 0.50, 0.00],  # #FF8000
            [0.50, 0.00, 1.00],  # #8000FF
            [0.00, 0.50, 1.00],  # #0080FF
            [0.63, 1.00, 0.00],  # #a0FF00 
            [1.00, 0.00, 0.50],  # #FF007F 
            [0.50, 0.00, 0.50],  # #800080
            [0.50, 0.63, 0.00],  # #80a000 
            [0.00, 0.50, 0.50],  # #008080
            [0.75, 0.25, 0.50],  # #BF4080
            [0.25, 0.75, 0.50],  # #40BF80 
            [0.50, 0.25, 0.75],  # #8040BF
            [0.75, 0.50, 0.25],  # #BF8040
            [0.25, 0.50, 0.75],  # #4080BF
            [1.00, 0.75, 0.50],  # #FFC080
            [0.19, 0.44, 0.19],  # #306F30
            [0.63, 0.75, 1.00],  # #a0C0FF
            [1.00, 0.50, 0.75],  # #FF80C0
            [0.82, 0.63, 1.00],  # #d0a0FF
            [0.25, 1.00, 0.75],  # #40FFBF
            [0.75, 0.25, 1.00],  # #BF40FF
            [1.00, 0.25, 0.75],  # #FF40BF
            [0.25, 0.75, 1.00],  # #40BFFF
            [1.00, 1.00, 0.50],   # #FFFF80
            [1.0, 0.753, 0.796], # #FFC0CB
            [0.980, 0.502, 0.447],# #FA8072
            [0.604, 0.804, 0.196],# #9ACD32
            [0.18, 0.545, 0.341], # #2E8B57
            [0.545, 0.271, 0.075],# #8B4513
            [0.753, 0.753, 0.224], # #C0C03A
            [0.678, 0.847, 0.902], # #ADEDDF
            [0.933, 0.510, 0.933], # #EE83EE
            [0.961, 0.624, 0.075], # #F59F13
        ]
        #sally
        self.m_clColorDic = {}
        self.m_clColorDicCnt = 0
        # self.m_currPatientID = ""
        # self.m_currOptionPath =""
        # self.m_intermediateDataPath =""
#<---------------------------------------------------------------------------------
        self.m_data = data.CData()
        self.m_listUndoCmd = []
        self.m_listRedoCmd = []
        self.m_operatorSelectionCL = op.COperationSelectionCL(self)

        # ui
        self.resize(width, height)

        self.m_mainWidget = QWidget(self)
        self.setCentralWidget(self.m_mainWidget)

        self.m_tabIndex = -1
        self.m_listTabState = []

        self._init_layout_main_ui()
        self._init_layout_bottom()
        self._init_layout_vtk()
        self._init_tab()


    # operator interface 
    def show_dialog(self, message : str) :
        msg_box = QMessageBox()
        msg_box.setWindowTitle("ServiceBatch")
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()
    def create_layout_label_editbox(self, title : str, bReadOnly : bool = False) -> tuple :
        '''
        ret : (QHBoxLayout, QLineEdit)
        '''
        layout = QHBoxLayout()
        label = QLabel(title)
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        editBox = QLineEdit()
        editBox.setReadOnly(bReadOnly)
        layout.addWidget(label)
        layout.addWidget(editBox)
        return (layout, editBox)
    def create_layout_label_editbox3(self, title : str) -> tuple :
        '''
        ret : (QHBoxLayout, QLineEdit1, QLineEdit2, QLineEdit3)
        '''
        layout = QHBoxLayout()
        label = QLabel(title)
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        editBox1 = QLineEdit()
        editBox2 = QLineEdit()
        editBox3 = QLineEdit()
        layout.addWidget(label)
        layout.addWidget(editBox1)
        layout.addWidget(editBox2)
        layout.addWidget(editBox3)
        return (layout, editBox1, editBox2, editBox3)
    def create_layout_label_editbox_btn(self, title : str, bReadOnly : bool = False, btnTitle : str = "") -> tuple :
        '''
        ret : (QHBoxLayout, QLineEdit, QPushButton)
        '''
        layout = QHBoxLayout()
        label = QLabel(title)
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        editBox = QLineEdit()
        editBox.setReadOnly(bReadOnly)
        btn = QPushButton(btnTitle)
        btn.setStyleSheet(self.m_styleSheetBtn)
        layout.addWidget(label)
        layout.addWidget(editBox)
        layout.addWidget(btn)
        return (layout, editBox, btn)
    def create_layout_label_slider_editbox(
            self, 
            title : str, 
            sliderMin : int, sliderMax : int, sliderInterval : int,
            bReadOnly : bool = False
            ) -> tuple :
        '''
        ret : (QHBoxLayout, QSlider, QLineEdit)
        '''
        layout = QHBoxLayout()

        label = QLabel(title)
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(sliderMin)
        slider.setMaximum(sliderMax)
        slider.setTickPosition(QSlider.TicksBelow)
        slider.setTickInterval(sliderInterval)

        editBox = QLineEdit()
        editBox.setReadOnly(bReadOnly)

        layout.addWidget(label)
        layout.addWidget(slider)
        layout.addWidget(editBox)
        return (layout, slider, editBox)
    def create_layout_label_combobox(self, title : str) -> tuple :
        '''
        ret : (QHBoxLayout, QComboBox)
        '''
        layout = QHBoxLayout()
        label = QLabel(title)
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        comboBox = QComboBox()
        layout.addWidget(label)
        layout.addWidget(comboBox)
        return (layout, comboBox)
    def create_layout_label_radio(self, title : str, btnNameList : list) -> tuple :
        '''
        ret : (QHBoxLayout, [QRadioButton0, QRadioButton1])
        '''
        layout = QHBoxLayout()
        label = QLabel(title)
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        retList = []
        for btnName in btnNameList :
            rb = QRadioButton(btnName, self)
            retList.append(rb)
        
        layout.addWidget(label)
        for rb in retList :
            layout.addWidget(rb)
        return (layout, retList)
    def create_layout_btn_array(self, btnNameList : list) -> tuple :
        '''
        ret : (QHBoxLayout, [btn0, btn1, ..])
        '''
        layout = QHBoxLayout()

        retList = []
        for btnName in btnNameList :
            btn = QPushButton(btnName)
            btn.setStyleSheet(self.m_styleSheetBtn)
            retList.append(btn)
        
        for btn in retList :
            layout.addWidget(btn)
        return (layout, retList)

    def add_cmd(self, cmd : commandInterface.CCommand) :
        self.m_listUndoCmd.append(cmd)
        for redoCmd in self.m_listRedoCmd :
            redoCmd.clear()
        self.m_listRedoCmd.clear()
    def clear_cmd(self) :
        for cmd in self.m_listUndoCmd :
            cmd.clear()
        for cmd in self.m_listRedoCmd :
            cmd.clear()
        self.m_listUndoCmd.clear()
        self.m_listRedoCmd.clear()
    def undo(self) :
        if len(self.m_listUndoCmd) == 0 :
            return
        cmd = self.m_listUndoCmd.pop()
        cmd.process_undo()
        self.m_listRedoCmd.append(cmd)
        self.update_viewer()
    def redo(self) :
        if len(self.m_listRedoCmd) == 0 :
            return
        cmd = self.m_listRedoCmd.pop()
        cmd.process()
        self.m_listUndoCmd.append(cmd)
        self.update_viewer()
    
    def get_tab_index(self) -> int :
        return self.m_mainTab.currentIndex()
    def get_tab_state_count(self) -> int :
        return len(self.m_listTabState)
    def get_tab_state(self, tabInx : int) -> tabState.CTabState :
        return self.m_listTabState[tabInx]
    def get_operator_selection_cl(self) -> op.COperationSelectionCL :
        return self.m_operatorSelectionCL
    
    def update_viewer(self) :
        self.UIViewerCL.update_render()
    def attach_vtk_obj_to_viewer(self, vtkObj : vtkObj.CVTKObj) :
        cnt = self.UIViewerCL.get_vtk_obj_count()
        self.UIViewerCL.add_vtk_obj(vtkObj)
        if cnt == 0 :
            self.UIViewerCL.reset_camera()
    def get_vtk_obj_count_from_viewer(self) -> int :
        return self.UIViewerCL.get_vtk_obj_count()
    def remove_vtk_obj_from_viewer(self, vtkObj : vtkObj.CVTKObj) :
        self.UIViewerCL.remove_vtk_obj(vtkObj)
    def remove_all_vtk_obj_of_viewer(self) :
        self.UIViewerCL.remove_all_vtk_obj()
    def is_registered_in_viewer(self, vtkObj : vtkObj.CVTKObj) -> bool :
        return self.UIViewerCL.is_registered_vtk_obj(vtkObj)
    def get_viewercl_renderer(self) -> vtk.vtkRenderer :
        return self.UIViewerCL.Renderer
    
    def ref_all_key(self) :
        dataInst = self.m_data
        for key, obj in dataInst.m_dicObj.items() :
            self.attach_vtk_obj_to_viewer(obj)
    def ref_key(self, key : str) :
        dataInst = self.m_data
        obj = dataInst.find_obj_by_key(key)
        if obj is not None :
            self.attach_vtk_obj_to_viewer(obj)
    def ref_key_type(self, keyType : str) :
        dataInst = self.m_data
        retObj = dataInst.find_obj_list_by_type(keyType)
        if retObj is not None :
            for obj in retObj :
                self.attach_vtk_obj_to_viewer(obj)
    def ref_key_type_groupID(self, keyType : str, groupID : int) :
        dataInst = self.m_data
        retObj = dataInst.find_obj_list_by_type_groupID(keyType, groupID)
        if retObj is not None :
            for obj in retObj :
                self.attach_vtk_obj_to_viewer(obj)

    def unref_all_key(self) :
        self.remove_all_vtk_obj_of_viewer()
    def unref_key(self, key : str) :
        dataInst = self.m_data
        obj = dataInst.find_obj_by_key(key)
        if obj is not None :
            self.remove_vtk_obj_from_viewer(obj)
    def unref_key_type(self, keyType : str) :
        dataInst = self.m_data
        retObj = dataInst.find_obj_list_by_type(keyType)
        if retObj is not None :
            for obj in retObj :
                self.remove_vtk_obj_from_viewer(obj)
    def unref_key_type_groupID(self, keyType : str, groupID : int) :
        dataInst = self.m_data
        retObj = dataInst.find_obj_list_by_type_groupID(keyType, groupID)
        if retObj is not None :
            for obj in retObj :
                self.remove_vtk_obj_from_viewer(obj)
    
    def detach_key(self, key : str) -> vtkObj.CVTKObj : 
        dataInst = self.Data
        self.unref_key(key)
        retObj = dataInst.detach_key(key)
        return retObj

    def remove_all_key(self) -> bool :
        self.unref_all_key()
        dataInst = self.m_data
        dataInst.remove_all_key()
        return True
    def remove_key(self, key : str) :
        self.unref_key(key)
        dataInst = self.m_data
        dataInst.remove_key(key)
    def remove_key_type(self, keyType : str) :
        self.unref_key_type(keyType)
        dataInst = self.m_data
        retList = dataInst.find_obj_list_by_type(keyType)
        if retList is not None :
            for clObj in retList :
                self.remove_vtk_obj_from_viewer(clObj)
                dataInst.remove_key(clObj.Key)
    def remove_key_type_groupID(self, keyType : str, groupID : int) :
        self.unref_key_type_groupID(keyType, groupID)
        dataInst = self.m_data
        retList = dataInst.find_obj_list_by_type_groupID(keyType, groupID)
        if retList is not None :
            for clObj in retList :
                self.remove_vtk_obj_from_viewer(clObj)
                dataInst.remove_key(clObj.Key)

    def visibility_key_type(self, keyType : str, bVisible : bool) :
        dataInst = self.m_data

        retList = dataInst.find_obj_list_by_type(keyType)
        if retList is not None :
            for obj in retList :
                obj.Visibility = bVisible

    def refresh_key(self, key : str, color : np.ndarray, opacity=1.0) :
        dataInst = self.m_data
        obj = dataInst.find_obj_by_key(key)
        if obj is not None :
            obj.Color = color
            obj.Opacity = opacity
    def refresh_key_type(self, keyType : str, color : np.ndarray, opacity=1.0) :
        dataInst = self.m_data
        retList = dataInst.find_obj_list_by_type(keyType)
        if retList is not None :
            for obj in retList :
                obj.Color = color
                obj.Opacity = opacity
    def refresh_key_type_groupID(self, keyType : str, groupID : int, color : np.ndarray, opacity=1.0) :
        dataInst = self.m_data
        retList = dataInst.find_obj_list_by_type_groupID(keyType, groupID)
        if retList is not None :
            for obj in retList :
                obj.Color = color
                obj.Opacity = opacity
    #sally
    def get_cl_color(self, clName) :
        if clName == '' :
            color = self.m_data.m_clColor
        else :
            # name을 가지고 있는 경우 해당 색상 부여, name이 없으면 디폴트색
            if clName not in self.m_clColorDic.keys() :
                cnt = self.m_clColorDicCnt % len(self.m_colorList)
                self.m_clColorDic[clName] = self.m_colorList[cnt]
                color = algLinearMath.CScoMath.to_vec3(self.m_colorList[cnt])
                self.m_clColorDicCnt = self.m_clColorDicCnt + 1
            else : 
                color = algLinearMath.CScoMath.to_vec3(self.m_clColorDic[clName])
        return color
        
    def load_userdata(self) :
        # projectType에 따라 userData를 로딩해야 한다. 
        self.Data.remove_all_userdata()
        projectType = self.ProjectType
        projectInfo = self.s_projectTypeInfo[projectType]
        if projectInfo["UserDataKey"] == "" :
            return
        
        userData = projectInfo["UserDataInst"](self.Data, self)
        userData.load_patient()
        self.Data.add_userdata(projectInfo["UserDataKey"], userData)
    def load_cl_key(self, groupID : int) :
        dataInst = self.m_data
        skeleton = dataInst.get_skeleton(groupID)
        if skeleton is None :
            return

        clCnt = skeleton.get_centerline_count()
        for clInx in range(0, clCnt) :
            cl = skeleton.get_centerline(clInx)
            clObj = vtkObjCL.CVTKObjCL(cl, dataInst.CLSize)

            if clObj.Ready == False :
                continue

            color = dataInst.CLColor
            if cl == skeleton.RootCenterline :
                color = dataInst.RootCLColor
            #sally
            else :
                if cl.Name != '' :
                    color = self.get_cl_color(cl.Name)

            clObj.KeyType = data.CData.s_skelTypeCenterline
            key = data.CData.make_key(clObj.KeyType, groupID, cl.ID)
            clObj.Key = key
            clObj.Color = color
            clObj.Opacity = 1.0
            clObj.Visibility = True
            dataInst.add_vtk_obj(clObj)
    def load_br_key(self, groupID : int) :
        dataInst = self.m_data
        skeleton = dataInst.get_skeleton(groupID)
        if skeleton is None :
            return
        
        brCnt = skeleton.get_branch_count()
        for brInx in range(0, brCnt) :
            br = skeleton.get_branch(brInx)
            brObj = vtkObjBr.CVTKObjBr(br, dataInst.BrSize)
            
            if brObj.Ready == False :
                continue

            brObj.KeyType = data.CData.s_skelTypeBranch
            brObj.Key = data.CData.make_key(brObj.KeyType, groupID, br.ID)
            brObj.Color = dataInst.BrColor
            brObj.Opacity = 1.0
            brObj.Visibility = True
            dataInst.add_vtk_obj(brObj)
    def load_ep_key(self, groupID : int) :
        dataInst = self.m_data
        skeleton = dataInst.get_skeleton(groupID)
        if skeleton is None : 
            return
        
        epCnt = skeleton.get_leaf_centerline_count()
        for epInx in range(0, epCnt) :
            leafCL = skeleton.get_leaf_centerline(epInx)
            epObj = vtkObjEP.CVTKObjEP(leafCL, dataInst.EPSize)
            if epObj.Ready == False :
                continue

            epObj.KeyType = data.CData.s_skelTypeEndPoint
            epObj.Key = data.CData.make_key(epObj.KeyType, groupID, leafCL.ID)
            epObj.Color = dataInst.EPColor
            epObj.Opacity = 1.0
            epObj.Visibility = True
            dataInst.add_vtk_obj(epObj)
        
    def load_vessel_key(self, groupID : int, id : int) :
        dataInst = self.m_data

        clinfo = dataInst.DataInfo.get_clinfo(groupID)
        clInPath = dataInst.get_cl_in_path()
        blenderName = clinfo.get_input_blender_name()
        vesselFullPath = os.path.join(f"{clInPath}", f"{blenderName}.stl")
        if os.path.exists(vesselFullPath) == False :
            print(f"failed to extract vessel : {vesselFullPath}")
            return
        
        vesselObj = vtkObjSTL.CVTKObjSTL(self.Data.OptionInfo, vesselFullPath)
        if vesselObj.Ready == False :
            return
        
        vesselObj.KeyType = dataInst.s_vesselType
        vesselKey = dataInst.make_key(vesselObj.KeyType, groupID, id)
        vesselObj.Key = vesselKey
        vesselObj.Color = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 1.0])
        vesselObj.Opacity = 0.3
        dataInst.add_vtk_obj(vesselObj)
    def load_organ_key(self) :
        dataInst = self.m_data
        terriInPath = dataInst.get_terri_in_path()

        iCnt = self.Data.OptionInfo.get_segmentinfo_count()
        for inx in range(0, iCnt) :
            segInfo = self.Data.OptionInfo.get_segmentinfo(inx)
            blenderName = segInfo.Organ

            terriInfo = dataInst.find_terriinfo_by_blender_name(blenderName)
            if terriInfo is None :
                continue
            if terriInfo.QueryVertex is not None :
                continue

            terriFullPath = os.path.join(f"{terriInPath}", f"{blenderName}.stl")
            terriObj =vtkObjSTL.CVTKObjSTL(self.Data.OptionInfo, terriFullPath)
            if terriObj.Ready == False :
                continue

            terriInx = dataInst.find_terriinfo_index_by_blender_name(blenderName)
            terriObj.KeyType = dataInst.s_organType
            key = dataInst.make_key(terriObj.KeyType, 0, terriInx)
            terriObj.Key = key
            terriObj.Color = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 1.0])
            terriObj.Opacity = 0.1
            dataInst.add_vtk_obj(terriObj)

            terriInfo.voxelize(terriObj.PolyData)
    def load_outside_key(self, clMaskInst : clMask.CCLMask) :
        dataInst = self.m_data
        skeleton = dataInst.get_skeleton(dataInst.CLInfoIndex)
        if skeleton is None :
            return

        clCnt = skeleton.get_centerline_count()
        for clInx in range(0, clCnt) :
            cl = skeleton.get_centerline(clInx)
            clObj = vtkObjOutsideCL.CVTKObjOutsideCL(cl, clMaskInst, dataInst.CLSize + 0.03)
            if clObj.Ready == False :
                continue

            key = data.CData.make_key(data.CData.s_outsideKeyType, 0, cl.ID)
            clObj.KeyType = data.CData.s_outsideKeyType
            clObj.Key = key
            clObj.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
            clObj.Opacity = 1.0
            dataInst.add_vtk_obj(clObj)

    def picking(self, clickX, clickY, listKeyType : list, tolerance : float = 0.001) -> str :
        for keyType in listKeyType :
            self.visibility_key_type(keyType, False)

        renderer = self.get_viewercl_renderer()
        picker = vtk.vtkCellPicker()
        picker.SetTolerance(tolerance)

        clKey = ""

        picker.Pick(clickX, clickY, 0, renderer)
        if picker.GetActor() :
            pickedActor = picker.GetActor()
            clKey = pickedActor.GetObjectName()
            print(f"Picked Actor: {clKey}")
        else :
            print("No polyData picked.")
        
        for keyType in listKeyType :
            self.visibility_key_type(keyType, True)
        return clKey
    def picking_cellid(self, clickX, clickY, listKeyType : list, tolerance : float = 0.001) -> int :
        '''
        ret : -1 (nothing picking)
        '''
        for keyType in listKeyType :
            self.visibility_key_type(keyType, False)
        
        renderer = self.get_viewercl_renderer()
        picker = vtk.vtkCellPicker()
        picker.SetTolerance(tolerance)
        picker.Pick(clickX, clickY, 0, renderer)

        cellID = picker.GetCellId()

        for keyType in listKeyType :
            self.visibility_key_type(keyType, True)
        return cellID
    def picking_intersected_point(self, clickX, clickY, listKeyType : list, tolerance : float = 0.001) -> np.ndarray :
        '''
        ret : -1 (nothing picking)
        '''
        for keyType in listKeyType :
            self.visibility_key_type(keyType, False)
        
        renderer = self.get_viewercl_renderer()
        picker = vtk.vtkCellPicker()
        picker.SetTolerance(tolerance)
        picker.Pick(clickX, clickY, 0, renderer)

        retPt = None

        cellID = picker.GetCellId()
        if cellID != -1 :
            retPt = picker.GetPickPosition()
            retPt = np.array(retPt).reshape(-1, 3)

        for keyType in listKeyType :
            self.visibility_key_type(keyType, True)
        return retPt

    def get_active_camera(self) -> vtk.vtkCamera :
        return self.UIViewerCL.Renderer.GetActiveCamera() 
    def get_active_camerainfo(self) -> tuple :
        '''
        ret : (rightVec, upVec, viewVec, camPos)
        '''
        camera = self.get_active_camera()
        upVec = algLinearMath.CScoMath.to_vec3(camera.GetViewUp())
        camPos = algLinearMath.CScoMath.to_vec3(camera.GetPosition())
        viewVec = algLinearMath.CScoMath.to_vec3(camera.GetDirectionOfProjection())
        rightVec = algLinearMath.CScoMath.cross_vec3(upVec, viewVec)
        return (rightVec, upVec, viewVec, camPos)
    def get_world_from_mouse(self, mx : int, my : int, distFromCamera=1000.0) :
        '''
        ret : (worldPos, pNear, pFar)
            - worldPos : 마우스 좌표의 world 좌표, camera로부터 distFromCamera만큼 떨어진 지점.
            - pNear : 마우스 좌표의 world 좌표, camera의 near-plane과 교차 된 지점
            - pFar : 마우스 좌표의 world 좌표, camera의 far-plane과 교차 된 지점
        '''
        renderer = self.get_viewercl_renderer()
        camera = self.get_active_camera()

        renderer.SetDisplayPoint(mx, my, 0)
        renderer.DisplayToWorld()
        pNear = np.array(renderer.GetWorldPoint()[0:3]).reshape(-1, 3)

        renderer.SetDisplayPoint(mx, my, 0.9)
        renderer.DisplayToWorld()
        pFar = np.array(renderer.GetWorldPoint()[0:3]).reshape(-1, 3)

        camPos = np.array(camera.GetPosition()).reshape(-1, 3)
        camDir = pNear - camPos
        camDir = algLinearMath.CScoMath.vec3_normalize(camDir)
        myFar = camPos + camDir * distFromCamera

        return myFar, pNear, pFar
        
    # tab name을 입력해서 인덱스 가져오기 sally
    def get_tabstate_index(self, tabStateName:str) -> int :
        projectType = self.ProjectType        
        projectInfo = self.s_projectTypeInfo[projectType]
        tabList = projectInfo["TabInfo"]
        index = next((i for i, tab in enumerate(tabList) if tab["TabName"] == tabStateName), -1)

        print(f"{tabStateName} Tab의 Index:", index)

        return index
    #sally 
    def get_clinfo_index(self) -> int :
        patientTabIdx = self.get_tabstate_index("Patient Info")
        if patientTabIdx != -1 :
            return self.m_listTabState[patientTabIdx].get_clinfo_index() 
        else :
            return -1
    #sally 
    def save_cl(self) -> int :
        editTabIdx = self.get_tabstate_index("Edit")
        if editTabIdx != -1:
            self.m_listTabState[editTabIdx].Skeleton = self.m_data.get_skeleton(self.m_data.CLInfoIndex)
            self.m_listTabState[editTabIdx]._on_btn_save_cl()



    @property
    def ProjectType(self) -> str :
        return self.m_projectType
    @ProjectType.setter
    def ProjectType(self, projectType : str) :
        self.m_projectType = projectType
    @property
    def FilePath(self) -> str :
        return self.m_filePath
    @property
    def CommonPipelinePath(self) -> str :
        return self.m_commonPipelinePath
    @property
    def Data(self) -> data.CData :
        return self.m_data
        

    # protected
    def _init_layout_main_ui(self) :
        self.m_layoutMain = QVBoxLayout(self.m_mainWidget)
        self.m_layoutTop = QHBoxLayout()
        self.m_layoutBottom = QVBoxLayout()

        self.m_mainTab = QTabWidget()
        self.m_mainTab.setTabPosition(QTabWidget.North)
        self.m_mainTab.setStyleSheet(self.m_styleSheetTab)
        self.m_mainTab.currentChanged.connect(self._on_tab_changed)
        tabBar = self.m_mainTab.tabBar()
        tabBar.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        layout, self.m_cbProjectType = self.create_layout_label_combobox("ProjectType ")
        self.m_cbProjectType.currentIndexChanged.connect(self._on_cb_projectType_changed)
        self.m_cbProjectType.blockSignals(True)
        for key in CTestApp.s_projectTypeInfo.keys() :
            self.m_cbProjectType.addItem(key)
        self.m_cbProjectType.blockSignals(False)
        self._setui_project_type(self.ProjectType)

        # main layer
        self.m_layoutMain.addLayout(self.m_layoutTop, 2)
        self.m_layoutMain.addLayout(self.m_layoutBottom, 1)
        # top layer
        self.m_layoutVTK = QHBoxLayout()
        self.m_layoutUI = QVBoxLayout()
        self.m_layoutTop.addLayout(self.m_layoutVTK, 3)
        self.m_layoutTop.addLayout(self.m_layoutUI, 1)
        # tab
        self.m_layoutUI.addLayout(layout)
        self.m_layoutUI.addWidget(self.m_mainTab)
    def _init_layout_bottom(self) :
        self.m_listWidget = QListWidget()
        self.m_listWidget.setFixedHeight(200)
        self.m_listWidget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.m_layoutBottom.addWidget(self.m_listWidget)
        sys.stdout = COutputRedirector(self.m_listWidget)
    def _init_layout_vtk(self) :
        self.UIViewerCL = vtkUIViewerCL.CVTKUIViewerCL(self.m_layoutVTK, self.m_mainWidget, self)
        self.UIViewerCL.set_interactor_style(vtkUIViewerCL.CViewerCLStyle(self.UIViewerCL))
        self.UIViewerCL.set_background(algLinearMath.CScoMath.to_vec3([0.5, 0.5, 0.5]))
        self.UIViewerCL.start()
    def _init_tab(self) :
        while self.m_mainTab.count() > 0 :
            self.m_mainTab.removeTab(0)
        self.m_tabIndex = -1
        self.m_listTabState.clear()

        projectType = self.ProjectType
        if projectType not in self.s_projectTypeInfo :
            print("Invalidate ProjectType")
            return
        
        projectInfo = self.s_projectTypeInfo[projectType]
        tabInfo = projectInfo["TabInfo"]
        for ele in tabInfo :
            tabName = ele["TabName"]
            inst = ele["TabInst"](self)
            self.m_listTabState.append(inst)
            self.m_mainTab.addTab(inst.Tab, tabName)
        
        iCnt = self.get_tab_state_count()
        for inx in range(0, iCnt) :
            self.get_tab_state(inx).changed_project_type()

    
    def _setui_project_type(self, projectType : str) :
        self.m_cbProjectType.blockSignals(True)
        self.m_cbProjectType.setCurrentText(projectType)
        self.m_cbProjectType.blockSignals(False)
    def _getui_project_type(self) -> str :
        return self.m_cbProjectType.currentText()


    # ui event
    def _on_tab_changed(self, inx) :
        if self.m_tabIndex == inx :
            return
        self.get_tab_state(self.m_tabIndex).process_end()
        self.m_tabIndex = inx
        self.get_tab_state(self.m_tabIndex).process_init()
        self.get_tab_state(self.m_tabIndex).process()
    def _on_cb_projectType_changed(self, index) :
        self.m_projectType = self._getui_project_type()
        self._init_tab()


    # UIViewer event
    def uiviewer_on_click_mouse_right(self, clickX, clickY) :
        self.get_tab_state(self.m_tabIndex).clicked_mouse_rb(clickX, clickY)
    def uiviewer_on_click_mouse_right_shift(self, clickX, clickY) :
        self.get_tab_state(self.m_tabIndex).clicked_mouse_rb_shift(clickX, clickY)
    def uiviewer_on_release_mouse_right(self) :
        self.get_tab_state(self.m_tabIndex).release_mouse_rb()
    def uiviewer_on_mouse_move(self, clickX, clickY) :
        self.get_tab_state(self.m_tabIndex).mouse_move(clickX, clickY)
    def uiviewer_on_mouse_move_right(self, clickX, clickY) :
        self.get_tab_state(self.m_tabIndex).mouse_move_rb(clickX, clickY)
    def uiviewer_on_key_press(self, keyCode) :
        self.get_tab_state(self.m_tabIndex).key_press(keyCode)
    def uiviewer_on_key_press_with_ctrl(self, keyCode) :
        self.get_tab_state(self.m_tabIndex).key_press_with_ctrl(keyCode)


if __name__ == '__main__' :
    multiprocessing.freeze_support()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    verstr = "v0.0.0"
    try:
        with open('Version.dat', 'r', encoding='utf-8') as ver_file:
            verstr = ver_file.readline()
        print(f"Version : {verstr}")
    except FileNotFoundError:
        print("Version File Not Exists.")

    guiWindow = CTestApp(1920, 1080)
    guiWindow.setWindowTitle(f"stomach Service Batch {verstr}")
    guiWindow.show()
    sys.exit(app.exec())


# print ("ok ..")




