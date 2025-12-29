import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

from scipy.spatial import KDTree

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTreeView, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox
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

import userDataStomach as userDataStomach
import treeVessel as treeVessel

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algMeshLib as algMeshLib
import AlgUtil.algVTK as algVTK
import AlgUtil.algSkeletonGraph as algSkeletonGraph

import vtkObjSTL as vtkObjSTL
import vtkObjInterface as vtkObjInterface
import vtkObjGuideMeshBound as vtkObjGuideMeshBound

import com.componentSelectionCL as componentSelectionCL




class CTabStateStomachVesselLabeling(tabState.CTabState) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_opSelectionCL = operation.COperationDragSelectionCL(mediator)
        self.m_comDragSelCLTP = None
    def clear(self) :
        # input your code
        if self.m_comDragSelCLTP is not None :
            self.m_comDragSelCLTP.clear()
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

        # skeleton labeling 초기화 
        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            cl.Name = userData.get_label_cl(clinfoinx, cl)

        # skeleton labeling 초기 세팅 
        iCnt = userData.get_tpinfo_count(clinfoinx)
        self.m_comDragSelCLTP = componentSelectionCL.CComDragSelCLTP(self)
        for inx in range(0, iCnt) :
            tpName = userData.get_tpinfo_name(clinfoinx, inx)
            tpPos = userData.get_tpinfo_pos(clinfoinx, inx)
            self.m_comDragSelCLTP.add_tpinfo(tpName, tpPos)
        self.m_comDragSelCLTP.InputOPDragSelCL = self.m_opSelectionCL
        self.m_comDragSelCLTP.process_init()
        
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
        
        self.m_opSelectionCL.process_reset()
        
        clinfoinx = self.get_clinfo_index()
        if self.m_comDragSelCLTP is not None :
            # userdata update
            iTPCnt = userData.get_tpinfo_count(clinfoinx)
            for inx in range(0, iTPCnt) :
                name, pos = self.m_comDragSelCLTP.get_tpinfo(inx)
                userData.set_tpinfo(clinfoinx, inx, name, pos)
            
            userData.clear_label_cl(clinfoinx)
            retList = self.m_comDragSelCLTP.get_label_cl_list()
            if retList is not None :
                for cl in retList :
                    userData.add_label_cl(clinfoinx, cl)

            self.m_comDragSelCLTP.process_end()
            self.m_comDragSelCLTP = None
    
        # 자동으로 labeling 정보 세팅 
        self._command_labeling_descendant()
        self.m_mediator.update_viewer()

    def init_ui(self) :
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        label = QLabel("-- Stomach Vessel Labeling --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        layout, self.m_editLabelName = self.m_mediator.create_layout_label_editbox("Label Name", False)
        self.m_editLabelName.returnPressed.connect(self._on_return_pressed_label_name)
        tabLayout.addLayout(layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        lastUI = line
        tabLayout.setAlignment(lastUI, Qt.AlignmentFlag.AlignTop)


    def clicked_mouse_rb(self, clickX, clickY) :
        listExceptKeyType = [
            data.CData.s_vesselType,
            data.CData.s_textType
        ]

        if self.m_comDragSelCLTP is None :
            return
        self.m_comDragSelCLTP.click(clickX, clickY, listExceptKeyType)
        self.m_mediator.update_viewer()
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        if self.m_comDragSelCLTP is None :
            return
        
        self.m_comDragSelCLTP.click_with_shift(clickX, clickY)
        self.m_mediator.update_viewer()
    def release_mouse_rb(self) :
        if self.m_comDragSelCLTP is None : 
            return
        
        self.m_comDragSelCLTP.release(0, 0)
        self.m_mediator.update_viewer()
    def mouse_move_rb(self, clickX, clickY) :
        if self.m_comDragSelCLTP is None :
            return
        listExceptKeyType = [
            data.CData.s_vesselType,
            componentSelectionCL.CComDragSelCLTP.s_tpVesselKeyType,
            data.CData.s_textType
        ]
        self.m_comDragSelCLTP.move(clickX, clickY, listExceptKeyType)
        self.m_mediator.update_viewer()
    def key_press(self, keyCode : str) :
        if keyCode == "Escape" :
            pass
        if keyCode == "Delete" :
            self.m_editLabelName.setText("")
            if self.m_comDragSelCLTP is not None :
                self.m_comDragSelCLTP.command_label_name("")

        self.m_mediator.update_viewer()

        # print(f"keyCode : {keyCode}")

    
    # protected
    def _get_userdata(self) -> userDataStomach.CUserDataStomach :
        return self.get_data().find_userdata(userDataStomach.CUserDataStomach.s_userDataKey)
    
    
    # command
    def _command_labeling_descendant(self) :
        dataInst = self.get_data()
        userData = self._get_userdata()
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)

        # 기존것은 지운 후 labeling 수행
        rootID = skeleton.RootCenterline.ID
        self.__labeling_descendant(rootID)
        self._command_save_cl()
        self.m_mediator.update_viewer()
    def _command_save_cl(self) :
        dataInst = self.get_data()
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)
        if skeleton is None :
            return

        clOutPath = dataInst.get_cl_out_path()

        clInfo = dataInst.OptionInfo.get_centerlineinfo(clinfoInx)
        blenderName = clInfo.get_input_blender_name()
        outputFileName = clInfo.OutputName
        outputFullPath = os.path.join(clOutPath, f"{outputFileName}.json")
        skeleton.save(outputFullPath, blenderName)


    # ui event 
    def _on_return_pressed_label_name(self) :
        labelName = self.m_editLabelName.text()
        self.m_editLabelName.setText("")
        if self.m_comDragSelCLTP is not None :
            self.m_comDragSelCLTP.command_label_name(labelName)
        self.m_mediator.update_viewer()
    # def _on_btn_create_tp(self) :
    #     listCLID = self.m_opSelectionCL.get_selection_cl_list()
    #     if len(listCLID) == 0 :
    #         print("not selected cl")
    #         return
    #     self.m_opSelectionCL.process_reset()
        
    #     dataInst = self.get_data()
    #     userData = self._get_userdata()
    #     clinfoInx = self.get_clinfo_index()
    #     skeleton = dataInst.get_skeleton(clinfoInx)

    #     label = self._getui_tp_vessel_name()
    #     self._setui_tp_vessel_name("")
    #     if label == "" :
    #         print("please setting label")
    #         return
        
    #     for clID in listCLID :
    #         cl = skeleton.get_centerline(clID)
    #         vertexInx = int(cl.get_vertex_count() / 2)
    #         pos = cl.get_vertex(vertexInx)

    #         index = userData.get_tp_vessel_count(clinfoInx)
    #         color = userData.get_color(index)
    #         tpVessel = userData.add_tp_vessel(clinfoInx, index, label, pos, color)

    #         self._add_tp_vessel(tpVessel)
        
    #     self.m_mediator.ref_key_type_groupID(userDataStomach.CTPVessel.s_tpVesselKeyType, clinfoInx)
    #     self.m_mediator.ref_key_type(data.CData.s_textType)
    #     self.m_mediator.update_viewer()


    # private
    def __labeling_descendant(self, clID : int) :
        dataInst = self.get_data()
        userData = self._get_userdata()
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)

        cl = skeleton.get_centerline(clID)
        label = cl.Name

        parentID, listChildID = skeleton.get_conn_centerline_id(clID)
        for childID in listChildID :
            clChild = skeleton.get_centerline(childID)
            if clChild.Name == "" :
                clChild.Name = label
            self.__labeling_descendant(childID)


if __name__ == '__main__' :
    pass


# print ("ok ..")

