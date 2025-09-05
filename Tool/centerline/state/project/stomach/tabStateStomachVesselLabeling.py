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

import VtkObj.vtkObjVertex as vtkObjVertex
import VtkObj.vtkObjText as vtkObjText
import vtkObjSTL as vtkObjSTL
import vtkObjInterface as vtkObjInterface
import vtkObjGuideMeshBound as vtkObjGuideMeshBound

import command.commandTerritory as commandTerritory
import command.commandVesselKnife as commandVesselKnife



class CTabStateStomachVesselLabeling(tabState.CTabState) :
    s_pickingDepth = 1000.0
    s_minDragDist = 10


    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_opSelectionCL = operation.COperationSelectionCL(mediator)
        '''
        key : tpVesselObj Key
        value : clID
        '''
        self.m_dicMatching = {}
        '''
        key : tpVesselObj Key
        value : text Key
        '''
        self.m_dicText = {}
        self.m_bDrag = False
        self.m_bLabel = False
    def clear(self) :
        # input your code
        self.m_dicMatching.clear()
        self.m_dicText.clear()
        self.m_bDrag = False
        super().clear()

    def process_init(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        userData = self._get_userdata()
        if userData is None :
            return
        
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)
        self.m_opSelectionCL.Skeleton = skeleton
        self.m_opSelectionCL.ChildSelectionMode = False
        self.m_opSelectionCL.ParentSelectionMode = False

        self.m_bDrag = False
        self.m_anchorObj = None
        self.m_ratio = 0.0

        self.__init_tp_vessel()
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
    
        # 자동으로 labeling 정보 세팅 
        self._command_labeling_descendant()
        
        self.m_bDrag = False
        self.m_anchorObj = None

        self.m_opSelectionCL.process_reset()
        self.__clear_tp_vessel()
        self.__clear_cl_color()
        self.m_mediator.update_viewer()

    def init_ui(self) :
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        label = QLabel("-- Stomach Vessel Labeling --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        layout, self.m_editTPName, btn = self.m_mediator.create_layout_label_editbox_btn("TP생성", False, "Create")
        btn.clicked.connect(self._on_btn_create_tp)
        tabLayout.addLayout(layout)

        btn = QPushButton("View Label")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_view_label)
        tabLayout.addWidget(btn)

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

        key = self.m_mediator.picking(clickX, clickY, listExceptKeyType)

        if key == "" :
            return
        
        keyType = data.CData.get_type_from_key(key)
        if keyType == data.CData.s_skelTypeCenterline :
            clID = data.CData.get_id_from_key(key)
            if self._exist_matching_by_clID(clID) == True :
                print("Do not select the centerline")
                return
            operation.COperationSelectionCL.clicked(self.m_opSelectionCL, key)
        elif keyType == userDataStomach.CTPVessel.s_tpVesselKeyType :
            dataInst = self.get_data()
            obj = dataInst.find_obj_by_key(key)

            clickedPoint = self.m_mediator.picking_intersected_point(clickX, clickY, listExceptKeyType)
            if clickedPoint is not None :
                cameraInfo = self.m_mediator.get_active_camerainfo()
                cameraPos = cameraInfo[3]
                dist = algLinearMath.CScoMath.vec3_len(clickedPoint - cameraPos)
                self.m_ratio = dist / CTabStateStomachVesselLabeling.s_pickingDepth

            self.m_anchorObj = obj
            self.m_bDrag = True
        else :
            return
        
        self.m_mediator.update_viewer()
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        listExceptKeyType = [
            data.CData.s_vesselType,
            userDataStomach.CTPVessel.s_tpVesselKeyType,
            data.CData.s_textType
        ]

        key = self.m_mediator.picking(clickX, clickY, listExceptKeyType)
        if key == "" or data.CData.get_type_from_key(key) != data.CData.s_skelTypeCenterline :
            key = ""
            return
        clID = data.CData.get_id_from_key(key)
        if self._exist_matching_by_clID(clID) == True :
            print("Do not select the centerline")
            return

        operation.COperationSelectionCL.multi_clicked(self.m_opSelectionCL, key)
        self.m_mediator.update_viewer()
    def release_mouse_rb(self) :
        if self.m_bDrag == False :
            return
        self.m_bDrag = False
        
    def mouse_move_rb(self, clickX, clickY) :
        if self.m_bDrag == False :
            return
        listExceptKeyType = [
            data.CData.s_vesselType,
            userDataStomach.CTPVessel.s_tpVesselKeyType,
            data.CData.s_textType
        ]

        cameraInfo = self.m_mediator.get_active_camerainfo()
        cameraPos = cameraInfo[3]

        self._clear_matching(self.m_anchorObj.Key)

        clickedPoint = self.m_mediator.picking_intersected_point(clickX, clickY, listExceptKeyType)
        if clickedPoint is not None :
            dist = algLinearMath.CScoMath.vec3_len(clickedPoint - cameraPos)
            self.m_ratio = dist / CTabStateStomachVesselLabeling.s_pickingDepth
            # 이 부분에서 centerline도 감지 
            key = self.m_mediator.picking(clickX, clickY, listExceptKeyType)
            if key != "" and data.CData.get_type_from_key(key) == data.CData.s_skelTypeCenterline :
                '''
                # 기존 matching 정보 갱신
                    - anchorObj에 matching된 cl이 있다면 제거
                    - 현재 key의 cl을 anchorObj와 matching 
                '''
                clID = data.CData.get_id_from_key(key)
                if self._exist_matching_by_clID(clID) == False : 
                    self._set_matching(self.m_anchorObj.Key, clID)

        worldStart, pNearStart, pFarStart= self.m_mediator.get_world_from_mouse(clickX, clickY, CTabStateStomachVesselLabeling.s_pickingDepth)
        dist = algLinearMath.CScoMath.vec3_len(worldStart - cameraPos)
        moveVec = cameraPos + (worldStart - cameraPos) * self.m_ratio
        self.m_anchorObj.Pos = moveVec

        pos = self.m_anchorObj.Pos.copy()
        pos[0, 1] = pos[0, 1] + userDataStomach.CTPVessel.s_tpRadius
        textObj = self._get_text_obj(self.m_anchorObj.Key)
        textObj.Pos = pos

        self.m_mediator.update_viewer()
    def key_press(self, keyCode : str) :
        if keyCode == "Escape" :
            self.m_opSelectionCL.process_reset()
            self.__end_labeling_simulation()
            self.m_mediator.update_viewer()


    # protected
    def _get_userdata(self) -> userDataStomach.CUserDataStomach :
        return self.get_data().find_userdata(userDataStomach.CUserDataStomach.s_userDataKey)
    def _clear_matching(self, tpVesselObjKey : str) :
        dataInst = self.get_data()
        userData = self._get_userdata()
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)

        clID = self.m_dicMatching[tpVesselObjKey]
        if clID != -1 :
            color = None
            if clID == skeleton.RootCenterline.ID :
                color = dataInst.RootCLColor
            else :
                color = dataInst.CLColor
            clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, clID)
            clObj = dataInst.find_obj_by_key(clKey)
            clObj.Color = color
            clObj.CL.Name = ""

        self.m_dicMatching[tpVesselObjKey] = -1
    def _set_matching(self, tpVesselObjKey : str, clID : int) :
        dataInst = self.get_data()
        userData = self._get_userdata()
        clinfoInx = self.get_clinfo_index()

        tpVesselObj = dataInst.find_obj_by_key(tpVesselObjKey)
        color = tpVesselObj.Color
        tpVessel = userData.find_tp_vessel_by_key(clinfoInx, tpVesselObjKey)

        clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, clID)
        clObj = dataInst.find_obj_by_key(clKey)
        clObj.Color = color
        clObj.CL.Name = tpVessel.Label

        self.m_dicMatching[tpVesselObjKey] = clID
    def _get_matching_tpVesselObjKey(self, clID : int) -> str :
        for tpVesselObjKey, value in self.m_dicMatching.items() :
            if value == clID :
                return tpVesselObjKey
        return ""
    def _exist_matching_by_clID(self, clID : int) -> bool :
        if clID in self.m_dicMatching.values() :
            return True
        return False 
    def _get_text_obj(self, tpVesselObjKey : str) :
        dataInst = self.get_data()
        textKey = self.m_dicText[tpVesselObjKey]
        textObj = dataInst.find_obj_by_key(textKey)
        return textObj
    def _add_tp_vessel(self, tpVessel : userDataStomach.CTPVessel) :
        dataInst = self.get_data()
        userData = self._get_userdata()
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)
        activeCamera = self.m_mediator.get_active_camera()

        tpVesselObj = tpVessel.TPVesselObj
        tpVesselKey = tpVesselObj.Key
        pos = tpVesselObj.Pos.copy()
        cl = skeleton.find_nearest_centerline(pos)
        cl.Name = tpVessel.Label
        self.m_dicMatching[tpVesselKey] = cl.ID

        pos[0, 1] = pos[0, 1] + userDataStomach.CTPVessel.s_tpRadius
        textKey = data.CData.make_key(data.CData.s_textType, 0, tpVessel.ID)
        vtkText = vtkObjText.CVTKObjText(activeCamera, pos, tpVessel.Label, 2.0)
        vtkText.KeyType = data.CData.s_textType
        vtkText.Key = textKey
        vtkText.Color = tpVesselObj.Color
        self.m_dicText[tpVesselKey] = textKey
        dataInst.add_vtk_obj(vtkText)

        clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, cl.ID)
        clObj = dataInst.find_obj_by_key(clKey)
        clObj.Color = tpVesselObj.Color
    
    # ui setting
    def _getui_tp_vessel_name(self) -> str :
        return self.m_editTPName.text()
    def _setui_tp_vessel_name(self, tpVesselName : str) :
        self.m_editTPName.setText(tpVesselName)
    
    # command
    def _command_labeling_descendant(self) :
        dataInst = self.get_data()
        userData = self._get_userdata()
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)

        # 기존것은 지운 후 labeling 수행
        self.__end_labeling_simulation()
        for tpVesselKey, clID in self.m_dicMatching.items() :
            self.__labeling_descendant(tpVesselKey, clID)
        self.m_mediator.update_viewer()

    # ui event 
    def _on_btn_create_tp(self) :
        listCLID = self.m_opSelectionCL.get_selection_cl_list()
        if len(listCLID) == 0 :
            print("not selected cl")
            return
        self.m_opSelectionCL.process_reset()
        
        dataInst = self.get_data()
        userData = self._get_userdata()
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)

        label = self._getui_tp_vessel_name()
        self._setui_tp_vessel_name("")
        if label == "" :
            print("please setting label")
            return
        
        for clID in listCLID :
            cl = skeleton.get_centerline(clID)
            vertexInx = int(cl.get_vertex_count() / 2)
            pos = cl.get_vertex(vertexInx)

            index = userData.get_tp_vessel_count(clinfoInx)
            color = userData.get_color(index)
            tpVessel = userData.add_tp_vessel(clinfoInx, index, label, pos, color)

            self._add_tp_vessel(tpVessel)
        
        self.m_mediator.ref_key_type_groupID(userDataStomach.CTPVessel.s_tpVesselKeyType, clinfoInx)
        self.m_mediator.ref_key_type(data.CData.s_textType)
        self.m_mediator.update_viewer()
    def _on_btn_view_label(self) :
        self._command_labeling_descendant()


    # private
    def __init_tp_vessel(self) :
        dataInst = self.get_data()
        userData = self._get_userdata()
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)
        activeCamera = self.m_mediator.get_active_camera()

        outDict = userData.get_tp_vessel_group(clinfoInx)
        for tpVesselKey, tpVessel in outDict.items() :
            self._add_tp_vessel(tpVessel)

        self.m_mediator.ref_key_type_groupID(userDataStomach.CTPVessel.s_tpVesselKeyType, clinfoInx)
        self.m_mediator.ref_key_type(data.CData.s_textType)
    def __clear_tp_vessel(self) :
        dataInst = self.get_data()
        userData = self._get_userdata()
        clinfoInx = self.get_clinfo_index()

        self.m_dicMatching.clear()
        self.m_dicText.clear()

        self.m_mediator.unref_key_type(userDataStomach.CTPVessel.s_tpVesselKeyType)
        self.m_mediator.remove_key_type(data.CData.s_textType)
    def __end_labeling_simulation(self) :
        dataInst = self.get_data()
        userData = self._get_userdata()
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)

        # initialize centerline
        color = None
        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            if inx == skeleton.RootCenterline.ID :
                color = dataInst.RootCLColor
            else :
                color = dataInst.CLColor

            cl = skeleton.get_centerline(inx)
            cl.Name = ""

            clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, inx)
            clObj = dataInst.find_obj_by_key(clKey)
            clObj.Color = color

        # initialize matching centerline
        for tpVesselKey, clID in self.m_dicMatching.items() :
            tpVesselObj = dataInst.find_obj_by_key(tpVesselKey)
            color = tpVesselObj.Color

            tpVessel = userData.find_tp_vessel_by_key(clinfoInx, tpVesselKey)
            cl = skeleton.get_centerline(clID)
            cl.Name = tpVessel.Label

            clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, clID)
            clObj = dataInst.find_obj_by_key(clKey)
            clObj.Color = color
    def __clear_cl_color(self) :
        dataInst = self.get_data()
        userData = self._get_userdata()
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)

        color = None
        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            if inx == skeleton.RootCenterline.ID :
                color = dataInst.RootCLColor
            else :
                color = dataInst.CLColor

            clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, inx)
            clObj = dataInst.find_obj_by_key(clKey)
            clObj.Color = color
    def __labeling_descendant(self, tpVesselKey : str, clID : int) :
        dataInst = self.get_data()
        userData = self._get_userdata()
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)

        tpVessel = userData.find_tp_vessel_by_key(clinfoInx, tpVesselKey)
        clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, clID)
        cl = skeleton.get_centerline(clID)
        clObj = dataInst.find_obj_by_key(clKey)
        label = tpVessel.Label

        if cl.Name != "" and cl.Name != label :
            return
        cl.Name = label
        clObj.Color = tpVessel.TPVesselObj.Color
        
        parentID, listChildID = skeleton.get_conn_centerline_id(clID)
        for childID in listChildID :
            self.__labeling_descendant(tpVesselKey, childID)



if __name__ == '__main__' :
    pass


# print ("ok ..")

