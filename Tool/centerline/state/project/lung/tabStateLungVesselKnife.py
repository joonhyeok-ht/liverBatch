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

import operationLung as operation #sally

import tabState as tabState

import treeVessel as treeVessel

import userDataLung as userDataLung #sally

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


class CSeparatedVessel :
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
        
        meshLibVessel = commandVesselKnife.CCommandSepVessel.get_meshlib(wholeVessel)
        meshLibVessel = algMeshLib.CMeshLib.meshlib_healing(meshLibVessel)
        clID = node.get_clID(0)

        cmd = commandVesselKnife.CCommandSepVesselPick(self.m_mediator)
        cmd.m_inputData = self.m_dataInst
        cmd.m_inputSkeleton = self.m_treeVessel.Skeleton
        cmd.m_inputMeshLibWholeVessel = meshLibVessel
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


class CTabStateLungVesselKnife(tabState.CTabState) :
    s_knifeKeyType = "knife"

    s_pickingDepth = 1000.0
    s_minDragDist = 10


    def __init__(self, mediator):
        super().__init__(mediator)
        try:
        # PyInstaller로 패키징된 실행 파일의 경우
            self.fileAbsPath = sys._MEIPASS
            self.fileAbsPath = os.getcwd() #"."
        except AttributeError:
            # 개발 환경에서
            self.fileAbsPath = os.path.abspath(os.path.dirname(__file__))
        
        # input your code
        self.m_opSelectionCL = operation.COperationSelectionCL(mediator)
        self.m_treeVessel = None
        self.m_startMx = 0
        self.m_startMy = 0
        self.m_endMx = 0
        self.m_endMy = 0
        self.m_bActiveKnife = False
        self.m_userData = None
    def clear(self) :
        # input your code
        self.m_startMx = 0
        self.m_startMy = 0
        self.m_endMx = 0
        self.m_endMy = 0
        self.m_bActiveKnife = False
        self.m_userData = None
        self.__clear_tree_vessel()
        super().clear()

    def process_init(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        self.m_userData = self._get_userdata()
        if self.m_userData is None :
            return
        
        clinfoinx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoinx)
        self.m_opSelectionCL.Skeleton = skeleton
        self.m_opSelectionCL.ChildSelectionMode = False
        self.m_opSelectionCL.ParentSelectionMode = False

        self._init_cl_label()
        self.__init_tree_vessel()
        self.__init_vessel_territory()

        self.m_startMx = 0
        self.m_startMy = 0
        self.m_endMx = 0
        self.m_endMy = 0
        self.m_bActiveKnife = False
        
        self.m_mediator.update_viewer()
        #sally
        patientPath = dataInst.DataInfo.PatientPath
        self.m_cutOutPath = os.path.join(patientPath, "VesselCut") 
        if not os.path.exists(self.m_cutOutPath) :
            os.makedirs(self.m_cutOutPath)
    def process(self) :
        pass
    def process_end(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
                
        self.m_startMx = 0
        self.m_startMy = 0
        self.m_endMx = 0
        self.m_endMy = 0
        self.m_bActiveKnife = False
        
        self.m_opSelectionCL.process_reset()
        self.__clear_tree_vessel()
        self._clear_cl_label()
        self.__clear_vessel_territory()
        self.m_mediator.update_viewer()

    def init_ui(self) :
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        label = QLabel("-- Lung Vessel Hierarchy Test --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        self.m_tvVessel = QTreeView()
                # scrollbar style  TODO 안먹힘 다시 해보기
        scrollbar_style = """
        QScrollBar:vertical {
            background: #f0f0f0;
            width: 12px;
            margin: 0px 0px 0px 0px;
        }
        QScrollBar::handle:vertical {
            background: #8888ff;
            min-height: 20px;
            border-radius: 6px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            background: none;
            height: 0px;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }
        """
        self.m_tvVessel.setStyleSheet(scrollbar_style)
        self.m_tvVessel.clicked.connect(self._on_tv_vessel_item_clicked)
        tabLayout.addWidget(self.m_tvVessel)

        self.m_lvInvalidNode = QListWidget()
        self.m_lvInvalidNode.itemClicked.connect(self.on_lb_invalid_node)
        tabLayout.addWidget(self.m_lvInvalidNode)

        btn = QPushButton("View Separated Vessel")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_view_separated_vessel)
        tabLayout.addWidget(btn)

        btn = QPushButton("Save Vessel(STL)")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_save_vessel)
        tabLayout.addWidget(btn)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        # btn = QPushButton("Vessel.blend")
        # btn.setStyleSheet(self.get_btn_stylesheet())
        # btn.clicked.connect(self._on_btn_blender_proc_vessel)
        # tabLayout.addWidget(btn)
        
        layout, btnList = self.m_mediator.create_layout_btn_array(["Vessel.blend(Join)", "Separate"])
        btnList[0].clicked.connect(self._on_btn_blender_proc_vessel_join)
        btnList[1].clicked.connect(self._on_btn_blender_proc_vessel_separate)
        tabLayout.addLayout(layout)
        
        btn = QPushButton("Merge To PatientID.blend + Save Latest")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_patientid_blender_with_vessel)
        tabLayout.addWidget(btn)

        lastUI = btn
        tabLayout.setAlignment(lastUI, Qt.AlignmentFlag.AlignTop)


    def clicked_mouse_rb(self, clickX, clickY) :
        dataInst = self.get_data()

        self.m_startMx = clickX
        self.m_startMy = clickY
        self.m_endMx = clickX
        self.m_endMy = clickY
        self.m_bActiveKnife = True

        worldStart, pNearStart, pFarStart= self.m_mediator.get_world_from_mouse(self.m_startMx, self.m_startMy, CTabStateLungVesselKnife.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.m_mediator.get_world_from_mouse(self.m_endMx, self.m_endMy, CTabStateLungVesselKnife.s_pickingDepth)

        self.m_knifeKey = data.CData.make_key(CTabStateLungVesselKnife.s_knifeKeyType, 0, 0)
        inst = vtkObjLine.CVTKObjLine()
        inst.KeyType = CTabStateLungVesselKnife.s_knifeKeyType
        inst.Key = self.m_knifeKey
        inst.set_line_width(2.0)
        inst.set_pos(pFarStart, pFarEnd)
        inst.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        dataInst.add_vtk_obj(inst)

        self.m_mediator.ref_key_type(CTabStateLungVesselKnife.s_knifeKeyType)

        self.m_mediator.update_viewer()
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        self.m_mediator.update_viewer()
    def release_mouse_rb(self) :
        if self.m_bActiveKnife == False :
            return
        
        self.m_bActiveKnife = False
        self.m_mediator.remove_key_type(CTabStateLungVesselKnife.s_knifeKeyType)

        # drag 영역이 너무 작을 경우 무시
        dx = self.m_endMx - self.m_startMx
        dy = self.m_endMy - self.m_startMy
        dist = math.hypot(dx, dy)
        if dist < CTabStateLungVesselKnife.s_minDragDist :
            self.m_mediator.update_viewer()
            return

        self._command_knife_vessel(self.m_startMx, self.m_startMy, self.m_endMx, self.m_endMy)
        self.m_mediator.update_viewer()
    def mouse_move_rb(self, clickX, clickY) :
        if self.m_bActiveKnife == False :
            return
        
        dataInst = self.get_data()
        
        self.m_endMx = clickX
        self.m_endMy = clickY
        worldStart, pNearStart, pFarStart = self.m_mediator.get_world_from_mouse(self.m_startMx, self.m_startMy, CTabStateLungVesselKnife.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.m_mediator.get_world_from_mouse(self.m_endMx, self.m_endMy, CTabStateLungVesselKnife.s_pickingDepth)

        inst = dataInst.find_obj_by_key(self.m_knifeKey)
        inst.set_pos(pFarStart, pFarEnd)
        self.m_mediator.update_viewer()
    def key_press(self, keyCode : str) :
        if keyCode == "Escape" :
            self.m_opSelectionCL.process_reset()
            self.__clear_vessel_territory()
            self.m_tvVessel.clearSelection()
            self.m_lvInvalidNode.clearSelection()
            self.m_mediator.update_viewer()
        elif keyCode == "m" :
            node = self._getui_tree_vessel_node()
            if node is None :
                print("not selection node")
                return
            
            # nodeVessel = node.get_valid_vessel()
            # parentNodeVessel = node.get_whole_vessel()
            # if nodeVessel == parentNodeVessel :
            #     print("parent-child is same")
            #     return

            # mergedVessel = commandVesselKnife.CCommandSepVessel.merge_vtkmesh(parentNodeVessel, nodeVessel, 0.001)
            # mergedVessel = commandVesselKnife.CCommandSepVessel.remove_duplicate_faces(mergedVessel)
            # node.set_whole_vessel(mergedVessel)
            # node.Vessel = None
            # self.__add_vessel_territory(node)
            # self._setui_list_add_node(node)
            # self.m_mediator.update_viewer()


    # protected
    def _get_userdata(self) -> userDataLung.CUserDataLung :
        return self.get_data().find_userdata(userDataLung.CUserDataLung.s_userDataKey)  
    
    # ui setting
    def _setui_tree_vessel(self, node : treeVessel.CNodeVesselHier, item : QStandardItem) :
        iCnt = node.get_child_node_count()
        for inx in range(0, iCnt) :
            childNode = node.get_child_node(inx)
            clLabel = self.m_treeVessel.get_cl_label(childNode)

            childItem = QStandardItem(clLabel)
            childItem.setData(childNode, Qt.UserRole)
            item.appendRow(childItem)
            self._setui_tree_vessel(childNode, childItem)
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
    def _setui_list_add_node(self, node : treeVessel.CNodeVesselHier) :
        self.m_lvInvalidNode.blockSignals(True)

        clLabel = self.m_treeVessel.get_cl_label(node)
        item = QListWidgetItem(f"{clLabel}")
        item.setData(Qt.UserRole, node)
        self.m_lvInvalidNode.addItem(item)

        self.m_lvInvalidNode.blockSignals(False)
    def _setui_list_add_listnode(self, listNode : list) :
        self.m_lvInvalidNode.blockSignals(True)
        self.m_lvInvalidNode.clear()

        for node in listNode :
            clLabel = self.m_treeVessel.get_cl_label(node)
            item = QListWidgetItem(f"{clLabel}")
            item.setData(Qt.UserRole, node)
            self.m_lvInvalidNode.addItem(item)

        self.m_lvInvalidNode.blockSignals(False)
    def _setui_list_remove_node(self, targetNode : treeVessel.CNodeVesselHier) :
        self.m_lvInvalidNode.blockSignals(True)

        # current_item = self.m_lvInvalidNode.currentItem()
        self.m_lvInvalidNode.setCurrentItem(None)
        self.m_lvInvalidNode.clearSelection()

        count = self.m_lvInvalidNode.count()
        for i in reversed(range(count)):
            item = self.m_lvInvalidNode.item(i)
            node = item.data(Qt.UserRole)
            if node == targetNode :
                self.m_lvInvalidNode.takeItem(i)
                del item
                break
        
        self.m_lvInvalidNode.blockSignals(False)
    def _getui_list_selected_node(self) -> treeVessel.CNodeVesselHier :
        selectedItems = self.m_lvInvalidNode.selectedItems()
        if not selectedItems :
            return None
        
        item = selectedItems[0]
        text = item.text()
        node = item.data(Qt.UserRole) 
        
        return node
    
    # command
    def _command_clicked_clID(self, clID : int) :
        self.m_treeVessel.clear_node()
        self.m_treeVessel.build_tree_with_label(clID)

        firstRootNode = self.m_treeVessel.get_first_root_node()
        if firstRootNode is None :
            return
        
        clLabel = self.m_treeVessel.get_cl_label(firstRootNode)
        
        # 빈 모델 생성
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(['Vessel Hierarchy'])

        # 항목 추가
        parentItem = QStandardItem(clLabel)
        parentItem.setData(firstRootNode, Qt.UserRole)
        self._setui_tree_vessel(firstRootNode, parentItem)

        # 모델에 루트 아이템 추가
        model.appendRow(parentItem)
        self.m_tvVessel.setModel(model)
        self.m_tvVessel.expandAll()
    def _command_clicked_vessel_hierarchy(self, item : QStandardItem) :
        dataInst = self.get_data()
        clinfoInx = self.get_clinfo_index()
        self.m_opSelectionCL.process_reset()

        if item is None :
            self.m_mediator.update_viewer()
            return
        
        node = item.data(Qt.UserRole)

        iCnt = node.get_clID_count()
        for inx in range(0, iCnt) :
            clID = node.get_clID(inx)
            key = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, clID)
            self.m_opSelectionCL.add_selection_key(key)
        self.m_opSelectionCL.process()

        self.__add_vessel_territory(node)
        self.m_mediator.update_viewer()
    def _command_clicked_invalid_node(self, item : QListWidgetItem) :
        node = item.data(Qt.UserRole)
        if node is None :
            print("not found node")
            return
        self.__add_vessel_territory(node)
        self.m_mediator.update_viewer()
    def _command_separate_vessel(self) :
        dataInst = self.get_data()
        clinfoInx = self.get_clinfo_index()

        vesselKey = data.CData.make_key(data.CData.s_vesselType, clinfoInx, 0)
        vesselObj = dataInst.find_obj_by_key(vesselKey)
        if vesselObj is None :
            return

        cmd = CSeparatedVessel(self.m_mediator, dataInst)
        cmd.process(self.m_treeVessel, vesselObj.PolyData)
        if len(cmd.ListInvalidNode) > 0 :
            self._setui_list_add_listnode(cmd.ListInvalidNode)

        cmd.clear()
    def _command_knife_vessel(self, startMx, startMy, endMx, endMy) :
        dataInst = self.get_data()
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)

        worldStart, pNearStart, pFarStart = self.m_mediator.get_world_from_mouse(startMx, startMy, CTabStateLungVesselKnife.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.m_mediator.get_world_from_mouse(endMx, endMy, CTabStateLungVesselKnife.s_pickingDepth)
        cameraInfo = self.m_mediator.get_active_camerainfo()
        cameraPos = cameraInfo[3]

        knifeCL = commandKnife.CCommandKnifeCL(self.m_mediator)
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
        
        meshLibVessel = commandVesselKnife.CCommandSepVessel.get_meshlib(wholeVessel)
        meshLibVessel = algMeshLib.CMeshLib.meshlib_healing(meshLibVessel)

        knifeCL.InputWorldA = worldStart
        knifeCL.InputWorldB = worldEnd
        knifeCL.InputWorldC = cameraPos

        cmd = commandVesselKnife.CCommandSepVesselKnife(self.m_mediator)
        cmd.m_inputData = dataInst
        cmd.m_inputSkeleton = skeleton
        cmd.m_inputMeshLibWholeVessel = meshLibVessel
        cmd.m_inputWorldA = worldStart
        cmd.m_inputWorldB = worldEnd
        cmd.m_inputWorldC = cameraPos
        cmd.process()

        if cmd.OutputWhole is None or cmd.OutputSub is None :
            print("failed to vessel knife")
        else :
            node.set_whole_vessel(cmd.OutputWhole)
            node.Vessel = cmd.OutputSub

        self.__add_vessel_territory(node)
        self.m_mediator.update_viewer()
    def _command_save_vessel(self, outputFolder : str) :
        mergeCmd = treeVessel.CMergePolyData()
        mergeCmd.process(self.m_treeVessel)

        for label, polyData in mergeCmd.OutDicPolyData.items() :
            fullPath = os.path.join(outputFolder, f"{label}.stl")
            algVTK.CVTK.save_poly_data_stl(fullPath, polyData)
    def _command_blender_proc_vessel_join(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False : 
            return 

        currPatientID = self.m_userData.Data.DataInfo.PatientID
        if currPatientID == '' :
            print(f"_command_blender_proc_vessel_join()-ERROR : CurrPatientID is empty.")
            return
        terriStlPath = dataInst.get_terri_out_path()
        saveAs = f"{currPatientID}.blend"
        vesselOutPath = self.m_cutOutPath

        cmd = f"{dataInst.OptionInfo.BlenderExe} --python {os.path.join(self.fileAbsPath, 'blenderScriptLung.py')} -- --patientID {currPatientID} --path {terriStlPath} --saveAs {saveAs} --funcMode VesselProc --vesselOutPath {vesselOutPath} --vesselProcMode JOIN"
        os.system(cmd)
        QMessageBox.information(self.m_mediator, "Alarm", "Vessel.blend Done. Separate를 실행해주세요.")
    def _command_blender_proc_vessel_separate(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False : 
            return 
        currPatientID = self.m_userData.Data.DataInfo.PatientID
        if currPatientID == '' :
            print(f"_command_blender_proc_vessel_separate()-ERROR : CurrPatientID is empty.")
            return
        terriStlPath = dataInst.get_terri_out_path()
        saveAs = f"{currPatientID}.blend"
        vesselOutPath = self.m_cutOutPath

        cmd = f"{dataInst.OptionInfo.BlenderExe} --python {os.path.join(self.fileAbsPath, 'blenderScriptLung.py')} -- --patientID {currPatientID} --path {terriStlPath} --saveAs {saveAs} --funcMode VesselProc --vesselOutPath {vesselOutPath} --vesselProcMode SEPARATE"
        os.system(cmd)
        QMessageBox.information(self.m_mediator, "Alarm", "Separate Done.")
    def _command_patientid_blender_with_vessel(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False : 
            return 
        currPatientID = self.m_userData.Data.DataInfo.PatientID
        if currPatientID == '' :
            print(f"_command_patientid_blender_with_vessel()-ERROR : CurrPatientID is empty.")
            return
        terriStlPath = dataInst.get_terri_out_path()
        saveAs = f"{currPatientID}.blend"
        vesselOutPath = self.m_cutOutPath

        cmd = f"{dataInst.OptionInfo.BlenderExe} --python {os.path.join(self.fileAbsPath, 'blenderScriptLung.py')} -- --patientID {currPatientID} --path {terriStlPath} --saveAs {saveAs} --funcMode VesselProc --vesselOutPath {vesselOutPath} --vesselProcMode MERGE"
        os.system(cmd)
        QMessageBox.information(self.m_mediator, "Alarm", "Merge Done.")
    # ui event 
    def _on_tv_vessel_item_clicked(self, index) :
        model = self.m_tvVessel.model()
        item = model.itemFromIndex(index)
        self._command_clicked_vessel_hierarchy(item)
    def on_lb_invalid_node(self, item) :
        self._command_clicked_invalid_node(item)
    def _on_btn_view_separated_vessel(self) :
        self._command_separate_vessel()
        QMessageBox.information(self.m_mediator, "Alarm", "complete to separate vessel")
    def _on_btn_save_vessel(self) :
        # outputPath = QFileDialog.getExistingDirectory(self.get_main_widget(), "Selection Output Path")
        # if outputPath == "" :
        #     return
        if os.path.exists(self.m_cutOutPath) :
            clinfoInx = self.get_clinfo_index()
            clInfo = self.get_data().DataInfo.get_clinfo(clinfoInx)
            vesselName = clInfo.get_input_blender_name() 
            vesselNameWithoutDirection = vesselName.split("_")[0]
            outPath = os.path.join(self.m_cutOutPath, vesselNameWithoutDirection)
            if not os.path.exists(outPath) :
                os.makedirs(outPath)
            self._command_save_vessel(outPath)
            QMessageBox.information(self.m_mediator, "Alarm", "complete to save vessel")

    def _on_btn_blender_proc_vessel_join(self) :
        self._command_blender_proc_vessel_join()
    def _on_btn_blender_proc_vessel_separate(self) :
        self._command_blender_proc_vessel_separate()
    def _on_btn_patientid_blender_with_vessel(self) :
        self._command_patientid_blender_with_vessel()
    # private
    def __init_tree_vessel(self) :
        dataInst = self.get_data()
        clinfoinx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoinx)
        self.m_treeVessel = treeVessel.CTreeVessel(skeleton)
        self._command_clicked_clID(skeleton.RootCenterline.ID)
    def __clear_tree_vessel(self) :
        if self.m_treeVessel is not None :
            self.m_treeVessel.clear()
        self.m_treeVessel = None
        
        if self.m_tvVessel.model() is not None :
            self.m_tvVessel.model().clear()
        self.m_lvInvalidNode.clear()
    def __init_vessel_territory(self) :
        self.m_mediator.remove_key_type(data.CData.s_territoryType)
    def __clear_vessel_territory(self) :
        self.m_mediator.remove_key_type(data.CData.s_territoryType)
    def __add_vessel_territory(self, node : treeVessel.CNodeVesselHier) :
        self.__clear_vessel_territory()

        dataInst = self.get_data()
        # if node.Vessel is None :
        #     print("not found vessel mesh")
        #     return 

        key = data.CData.make_key(data.CData.s_territoryType, 0, 0)
        terriObj = vtkObjInterface.CVTKObjInterface()
        terriObj.KeyType = data.CData.s_territoryType
        terriObj.Key = key
        terriObj.Color = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 0.0])
        terriObj.Opacity = 0.5
        # terriObj.PolyData = node.Vessel
        terriObj.PolyData = node.get_valid_vessel()
        dataInst.add_vtk_obj(terriObj)
        self.m_mediator.ref_key_type(data.CData.s_territoryType)

        

if __name__ == '__main__' :
    pass


# print ("ok ..")

