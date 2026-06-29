import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

from scipy.spatial import KDTree

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTreeView, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QComboBox, QAbstractItemView, QListWidgetItem
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

import userDataLiver as userDataLiver
import treeVessel as treeVessel

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algMeshLib as algMeshLib
import AlgUtil.algVTK as algVTK

import vtkObjCL as vtkObjCL
import VtkObj.vtkObjVertex as vtkObjVertex
import VtkObj.vtkObjText as vtkObjText
import vtkObjSTL as vtkObjSTL
import vtkObjInterface as vtkObjInterface
import vtkObjGuideMeshBound as vtkObjGuideMeshBound
import command.commandInterface as commandInterface

import command.commandTerritory as commandTerritory
import command.commandVesselKnife as commandVesselKnife
import command.commandTPEdit as commandTPEdit
import com.componentSelectionCL as componentSelectionCL


class CTabStateLiverVesselLabeling(tabState.CTabState) :
    s_pickingDepth = 1000.0
    s_minDragDist = 10


    def __init__(self, mediator) :
        self.m_bReady = False
        
        super().__init__(mediator)
        # input your code
        #self.m_opSelectionCL = operation.COperationSelectionCL(mediator)
        self.m_opDragSelectionCL = operation.COperationDragSelectionCL(self.m_mediator)
        self.m_comDragSelCL = None
        self.App = mediator
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
        self.m_bReady = True
        self.m_anchorObjColor = np.array([[0, 0, 0]])
    def clear(self) :
        # input your code
        self.m_dicMatching.clear()
        self.m_dicText.clear()
        self.m_bDrag = False
        self.m_bReady = False
        super().clear()

    def process_init(self) :
        self.process_end()
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        #userData = self._get_userdata()
        userData = dataInst.UserData
        if userData is None :
            return
        
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)
        #self.m_opSelectionCL.Skeleton = skeleton
        #self.m_opSelectionCL.ChildSelectionMode = False
        #self.m_opSelectionCL.ParentSelectionMode = False
        self.m_opDragSelectionCL.Skeleton = skeleton
        self.m_comDragSelCL = componentSelectionCL.CComDragSelCL(self)
        self.m_comDragSelCL.InputOPDragSelCL = self.m_opDragSelectionCL
        self.m_comDragSelCL.InputUIRBSelSingle = self.m_rbSingle
        self.m_comDragSelCL.InputUIRBSelDescendant = self.m_rbDescendant
        self.m_comDragSelCL.process_init()

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
#        userData = self._get_userdata()
        userData = dataInst.UserData
        if userData is None :
            return
    
        # 자동으로 labeling 정보 세팅 
        # self._command_labeling_descendant()
        if self.m_comDragSelCL is not None :
            self.m_comDragSelCL.process_end()
            self.m_comDragSelCL = None
        
        self.m_bDrag = False
        self.m_anchorObj = None

        #self.m_opSelectionCL.process_reset()
        self.__clear_tp_vessel()
        #self.__clear_cl_color()
        self.m_mediator.update_viewer()

    def init_ui(self) :
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        label = QLabel("-- Liver Vessel Labeling --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)
        
        layout, retList = self.m_mediator.create_layout_label_radio("SelectionMode", ["Single", "Descendant"])
        self.m_rbSingle = retList[0]
        self.m_rbDescendant = retList[1]
        self.m_rbSingle.toggled.connect(self._on_rb_single)
        self.m_rbDescendant.toggled.connect(self._on_rb_descendant)
        self.m_rbSingle.setChecked(True)
        tabLayout.addLayout(layout)

        layout, self.m_editTPName, btn = self.m_mediator.create_layout_label_editbox_btn("TP생성", False, "Create")
        self.m_editTPName.returnPressed.connect(self._on_btn_create_tp)
        btn.clicked.connect(self._on_btn_create_tp)
        tabLayout.addLayout(layout)

        btn = QPushButton("Delete TP")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_delete_tp)
        tabLayout.addWidget(btn)

        # btn = QPushButton("Clear Label")
        # btn.setStyleSheet(self.get_btn_stylesheet())
        # btn.clicked.connect(self._on_btn_clear_label)
        # tabLayout.addWidget(btn)

        btn = QPushButton("Propagate Label")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self.process_init)
        tabLayout.addWidget(btn)
        
        label = QLabel("----- Label List -----")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)
        
        listWidget = QListWidget()

        listWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)

        for name in ["Extra_Artery", "Extra_Vein"]:
            item = QListWidgetItem(name)
            listWidget.addItem(item)

        listWidget.itemClicked.connect(
    lambda item: self.list_widget_create_tp(item.text())
)

        tabLayout.addWidget(listWidget)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        lastUI = line
        tabLayout.setAlignment(lastUI, Qt.AlignmentFlag.AlignTop)
        
    def list_widget_create_tp(self, itemText):
        self._setui_tp_vessel_name(itemText)
        self._on_btn_create_tp()


    def clicked_mouse_rb(self, clickX, clickY) :
        listExceptKeyType = [
            data.CData.s_vesselType,
            data.CData.s_textType
        ]

        key = self.m_mediator.picking(clickX, clickY, listExceptKeyType)

        if key == "" :
            #operation.COperationSelectionCL.clicked(self.m_opSelectionCL, key)
            if self.m_comDragSelCL is None :
                return
            self.m_comDragSelCL.click(clickX, clickY, listExceptKeyType)
            self.m_mediator.update_viewer()
            
            if self.m_anchorObj != None:
                self.m_anchorObj.Color = self.m_anchorObjColor
                self.m_anchorObj = None
            return
        
        keyType = data.CData.get_type_from_key(key)
        if keyType == data.CData.s_skelTypeCenterline :
            clID = data.CData.get_id_from_key(key)
            if self._exist_matching_by_clID(clID) == True :
                print("Do not select the centerline")
                return
            #operation.COperationSelectionCL.clicked(self.m_opSelectionCL, key)
            if self.m_comDragSelCL is None :
                return
            self.m_opDragSelectionCL.process_reset()
            self.m_opDragSelectionCL.add_selection_keys([key])
            self.m_opDragSelectionCL.process()
            if self.m_anchorObj != None:
                self.m_anchorObj.Color = self.m_anchorObjColor
                self.m_anchorObj = None
        elif keyType == userDataLiver.CTPVessel.s_tpVesselKeyType :
            dataInst = self.get_data()
            obj = dataInst.find_obj_by_key(key)

            clickedPoint = self.m_mediator.picking_intersected_point(clickX, clickY, listExceptKeyType)
            if clickedPoint is not None :
                cameraInfo = self.m_mediator.get_active_camerainfo()
                cameraPos = cameraInfo[3]
                dist = algLinearMath.CScoMath.vec3_len(clickedPoint - cameraPos)
                self.m_ratio = dist / CTabStateLiverVesselLabeling.s_pickingDepth
            
            if not np.array_equal(obj.Color[0], np.array([1.0, 1.0, 0])):
                if self.m_anchorObj != None:
                    self.m_anchorObj.Color = self.m_anchorObjColor
                self.m_anchorObj = obj
                self.m_anchorObjColor = np.copy(self.m_anchorObj.Color)
                self.m_anchorObj.Color = np.array([[1.0, 1.0, 0]])
            self.m_bDrag = True
        else :
            return
        
        self.m_mediator.update_viewer()
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        listExceptKeyType = [
            data.CData.s_vesselType,
            userDataLiver.CTPVessel.s_tpVesselKeyType,
            data.CData.s_textType
        ]

        key = self.m_mediator.picking(clickX, clickY, listExceptKeyType)
        if key == "" or data.CData.get_type_from_key(key) == data.CData.s_skelTypeCenterline :
            pass
        else:
            return
        
        if key == "":
            if self.m_comDragSelCL is None :
                return
            
            self.m_comDragSelCL.click_with_shift(clickX, clickY, listExceptKeyType)
        elif data.CData.get_type_from_key(key) == data.CData.s_skelTypeCenterline:
            clID = data.CData.get_id_from_key(key)
            if self._exist_matching_by_clID(clID) == True :
                print("Do not select the centerline")
                return
            
            #self.m_opDragSelectionCL.process_reset()
            self.m_opDragSelectionCL.add_selection_keys([key])
            self.m_opDragSelectionCL.process()
        self.m_mediator.update_viewer()
    def release_mouse_rb(self) :
        if self.m_bDrag == False :
            if self.m_comDragSelCL is None :
                return
            self.m_comDragSelCL.release(0, 0)
            self.App.update_viewer()
            return
        self.m_bDrag = False
        
    def mouse_move_rb(self, clickX, clickY) :
        listExceptKeyType = [
            data.CData.s_vesselType,
            userDataLiver.CTPVessel.s_tpVesselKeyType,
            data.CData.s_textType
        ]
        if self.m_bDrag == False :
            if self.m_comDragSelCL is None :
                return
            self.m_comDragSelCL.move(clickX, clickY, listExceptKeyType)
            self.App.update_viewer()
            return

        cameraInfo = self.m_mediator.get_active_camerainfo()
        cameraPos = cameraInfo[3]
        
        
        lastMatching = None
        if self.m_anchorObj.Key in self.m_dicMatching.keys():
            lastMatching = self.m_dicMatching[self.m_anchorObj.Key]
        currentMatching = lastMatching
        self._clear_matching(self.m_anchorObj.Key)

        clickedPoint = self.m_mediator.picking_intersected_point(clickX, clickY, listExceptKeyType)
        if clickedPoint is not None :
            
            dist = algLinearMath.CScoMath.vec3_len(clickedPoint - cameraPos)
            self.m_ratio = dist / CTabStateLiverVesselLabeling.s_pickingDepth
            # 이 부분에서 centerline도 감지 key_press_with_ctrl
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
                    
        currentMatching = self.m_dicMatching[self.m_anchorObj.Key]
        
        '''
        TP가 labeling 하고 있는 obj가 바뀌면 업데이트
        '''
        if currentMatching != lastMatching:
            self._command_labeling_descendant()

        worldStart, pNearStart, pFarStart= self.m_mediator.get_world_from_mouse(clickX, clickY, CTabStateLiverVesselLabeling.s_pickingDepth)
        dist = algLinearMath.CScoMath.vec3_len(worldStart - cameraPos)
        moveVec = cameraPos + (worldStart - cameraPos) * self.m_ratio
        self.m_anchorObj.Pos = moveVec

        pos = self.m_anchorObj.Pos.copy()
        pos[0, 1] = pos[0, 1] + userDataLiver.CTPVessel.s_tpRadius*1.3
        pos[0, 0] += 1
        textObj = self._get_text_obj(self.m_anchorObj.Key)
        textObj.Pos = pos

        self.m_mediator.update_viewer()
    def key_press(self, keyCode : str) :
        if keyCode == "Escape" :
            #self.m_opSelectionCL.process_reset()
            if self.m_anchorObj != None:
                self.m_anchorObj.Color = self.m_anchorObjColor
                self.m_anchorObj = None
            
            self._command_labeling_descendant()
            self.m_mediator.update_viewer()
        if keyCode == "Delete" :
            self.delete_tp()
        if keyCode == "Return":
            self._on_btn_create_tp()
        if keyCode.lower() == "a":
            self.set_camera_anterior_fit_largest_actor()
            
    def key_press_with_ctrl(self, keyCode : str) :
        if keyCode == "z" :
            self.App.undo()
            self._command_labeling_descendant()
        if keyCode == "r" :
            self.App.redo()

    # protected
    def _get_userdata(self) -> userDataLiver.CUserDataLiver :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        #userData = self._get_userdata()
        userData = dataInst.UserData
        return userData
        return self.get_data().find_userdata(userDataLiver.CUserDataLiver.s_userDataKey)
    def _clear_matching(self, tpVesselObjKey : str) :
        dataInst = self.get_data()
        userData = self._get_userdata()
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)

        clID = self.m_dicMatching[tpVesselObjKey]
        if clID != -1 :
            color = None
            if clID == skeleton.RootCenterline.ID :
                color = dataInst.s_rootCLColor
            else :
                color = dataInst.s_clColor
            clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, clID)
            clObj = dataInst.find_obj_by_key(clKey)
            if clObj == None:
                return
            clObj.Color = color
            clObj.CL.Name = ""

        self.m_dicMatching[tpVesselObjKey] = -1
    
    def delete_tp(self):
        dataInst = self.get_data()
        userData = self._get_userdata()
        clinfoInx = self.get_clinfo_index()
        outDict = userData.get_tp_vessel_group(clinfoInx)
        
        if self.m_anchorObj == None:
            return
        
        cmdContainer = commandInterface.CCommandContainer(self.App)
        cmdContainer.InputData = dataInst
        
        cmdTPInst = commandTPEdit.CCommandUpdateTP(self.App, self)
        cmdTPInst.m_inputTPKey = self.m_anchorObj.Key
        cmdTPInst.Type = "delete"
        cmdTPInst.InputTP = outDict[self.m_anchorObj.Key]
        cmdTPInst.InputText = dataInst.find_obj_by_key(self.m_dicText[self.m_anchorObj.Key])
        cmdTPInst.m_matchedCLID = self.m_dicMatching[self.m_anchorObj.Key]
        
        cmdContainer.add_cmd(cmdTPInst)
        self.App.add_cmd(cmdContainer)
        if self.m_anchorObj is not None:
            if self.m_anchorObj.Key in self.m_dicMatching.keys():
                textKey = self.m_dicText[self.m_anchorObj.Key]
                del self.m_dicMatching[self.m_anchorObj.Key]
                del self.m_dicText[self.m_anchorObj.Key]
                del outDict[self.m_anchorObj.Key]
                self.m_mediator.unref_key(textKey)
                self.m_mediator.unref_key(self.m_anchorObj.Key)
                dataInst.detach_key(self.m_anchorObj.Key)
                dataInst.detach_key(textKey)
                self._command_labeling_descendant()
        self.m_anchorObj = None
        self.m_mediator.update_viewer()
    
    def _set_matching(self, tpVesselObjKey : str, clID : int) :
        dataInst = self.get_data()
        userData = self._get_userdata()
        clinfoInx = self.get_clinfo_index()

        tpVesselObj = dataInst.find_obj_by_key(tpVesselObjKey)
        color = tpVesselObj.Color
        tpVessel = userData.find_tp_vessel_by_key(clinfoInx, tpVesselObjKey)

        clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, clID)
        clObj = dataInst.find_obj_by_key(clKey)
        clObj.Color = self.m_anchorObjColor
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
    def _add_tp_vessel(self, tpVessel : userDataLiver.CTPVessel) :
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

        pos[0, 1] = pos[0, 1] + userDataLiver.CTPVessel.s_tpRadius*1.3
        pos[0, 0] -= 1
        textKey = data.CData.make_key(data.CData.s_textType, 0, tpVessel.ID)
        if "START" in tpVessel.Label:
            tpText = "_".join(tpVessel.Label.split("_")[-2:])
        else:
            tpText = tpVessel.Label.split("_")[-1]
            
        vtkText = vtkObjText.CVTKObjText(activeCamera, pos, tpText, 2.0)
        vtkText.KeyType = data.CData.s_textType
        vtkText.Key = textKey
        vtkText.Color = tpVesselObj.Color
        self.m_dicText[tpVesselKey] = textKey
        dataInst.add_vtk_obj(vtkText)

        clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, cl.ID)
        clObj = dataInst.find_obj_by_key(clKey)
        clObj.m_labelColor = tpVesselObj.Color
        clObj.Color = tpVesselObj.Color
        
        self.m_mediator.m_clColorDic[cl.Name] = tpVesselObj.Color
    
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
            if clID == -1:
                continue
            self.__labeling_descendant(tpVesselKey, clID)
        self.m_mediator.update_viewer()
        

    def _on_btn_delete_tp(self):
        self.delete_tp()
        
    def _on_btn_clear_label(self):
        self._all_clear_label()
        self.m_mediator.update_viewer()
    def _on_rb_single(self) :
        if self.m_bReady == False :
            return
    def _on_rb_descendant(self) :
        if self.m_bReady == False :
            return
        

    # ui event 
    def _on_btn_create_tp(self) :
        listCLID = self.m_opDragSelectionCL.get_selection_cl_list()
        if not listCLID:
            print("please select centerline")
            return
        if len(listCLID) == 0 :
            print("not selected cl")
            return
        #self.m_opSelectionCL.process_reset()
        
        dataInst = self.get_data()
        userData = self._get_userdata()
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)

        label = self._getui_tp_vessel_name()
        label = label.split("_")[-1] if "_" in label else label
        if label in userDataLiver.CUserDataLiver.s_tpClinfoIdxMapper.keys():
            label = label
            #label = userDataLiver.CUserDataLiver.s_tpClinfoIdxMapper.get(label, label)
        else:
            print("Name not in the list")
            return
        self._setui_tp_vessel_name("")
        # if label == "" :
        #     print("please setting label")
        #     return
        
        for clID in listCLID :
            cl = skeleton.get_centerline(clID)
            vertexInx = int(cl.get_vertex_count() / 2)
            pos = cl.get_vertex(vertexInx)

            #index = userData.get_tp_vessel_count(clinfoInx)
            index = userData._get_new_index(clinfoInx)
            identical_vessel = userData.is_exist_name(clinfoInx, label)
            
            # if label in "a":
            #     self.m_mediator.find_obj_by_key
            if label == "" :
                color = dataInst.s_clColor
            else:
                if identical_vessel:
                    color = identical_vessel.m_tpVesselObj.Color
                    label = identical_vessel.Label
                else:
                    index = index % len(self.m_mediator.m_colorList)
                    color = np.array(self.m_mediator.m_colorList[index]).reshape(-1, 3)

                
            #color = userData.get_color(index)
            tpVessel = userData.add_tp_vessel(clinfoInx, index, label, pos, color)

            self._add_tp_vessel(tpVessel)
        
        self.m_mediator.ref_key_type_groupID(userDataLiver.CTPVessel.s_tpVesselKeyType, clinfoInx)
        self.m_mediator.ref_key_type(data.CData.s_textType)
        self.m_mediator.update_viewer()
    def _on_btn_view_label(self) :
        self._command_labeling_descendant()
        
    def _on_btn_remove_tp(self):
        self.m_mediator.update_viewer()
        


    # private
    def __init_tp_vessel(self) :
        dataInst = self.get_data()
        userData = self._get_userdata()
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)
        activeCamera = self.m_mediator.get_active_camera()

        outDict = userData.get_tp_vessel_group(clinfoInx)
        if outDict:
            for tpVesselKey, tpVessel in outDict.items() :
                self._add_tp_vessel(tpVessel)

        self.m_mediator.ref_key_type_groupID(userDataLiver.CTPVessel.s_tpVesselKeyType, clinfoInx)
        self.m_mediator.ref_key_type(data.CData.s_textType)
        self._command_labeling_descendant()
    def __clear_tp_vessel(self) :
        dataInst = self.get_data()
        userData = self._get_userdata()
        clinfoInx = self.get_clinfo_index()

        self.m_dicMatching.clear()
        self.m_dicText.clear()

        self.m_mediator.unref_key_type(userDataLiver.CTPVessel.s_tpVesselKeyType)
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
                color = dataInst.s_rootCLColor
            else :
                color = dataInst.s_clColor

            cl = skeleton.get_centerline(inx)
            cl.Name = ""

            clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, inx)
            clObj = dataInst.find_obj_by_key(clKey)
            clObj.Color = color

        # initialize matching centerline
        for tpVesselKey, clID in self.m_dicMatching.items() :
            if clID == -1:
                continue
            tpVesselObj = dataInst.find_obj_by_key(tpVesselKey)
            color = tpVesselObj.Color

            tpVessel = userData.find_tp_vessel_by_key(clinfoInx, tpVesselKey)
            cl = skeleton.get_centerline(clID)
            cl.Name = tpVessel.Label

            clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, clID)
            clObj = dataInst.find_obj_by_key(clKey)
            if clObj == None:
                continue
            clObj.Color = color
    def _all_clear_label(self):
        dataInst = self.get_data()
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)

        # initialize centerline
        color = None
        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            if inx == skeleton.RootCenterline.ID :
                color = dataInst.s_rootCLColor
            else :
                color = dataInst.s_clColor

            cl = skeleton.get_centerline(inx)
            cl.Name = ""

            clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, inx)
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
            cl = skeleton.get_centerline(inx)
            clObj = vtkObjCL.CVTKObjCL(cl, dataInst.CLSize)

            if clObj.Ready == False :
                continue

            color = dataInst.s_clColor
            if cl == skeleton.RootCenterline :
                color = dataInst.s_rootCLColor
            #sally
            else :
                if cl.Name != '' :
                    self.m_data.s_clColor
                    

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
        if clObj != None:
            if np.array_equal(tpVessel.TPVesselObj.Color[0], np.array([1.0, 1.0, 0])):
                clObj.Color = self.m_anchorObjColor
                clObj.m_labelColor = self.m_anchorObjColor
            else:
                clObj.Color = tpVessel.TPVesselObj.Color
                clObj.m_labelColor = tpVessel.TPVesselObj.Color
        
        parentID, listChildID = skeleton.get_conn_centerline_id(clID)
        for childID in listChildID :
            self.__labeling_descendant(tpVesselKey, childID)



if __name__ == '__main__' :
    pass


# print ("ok ..")

