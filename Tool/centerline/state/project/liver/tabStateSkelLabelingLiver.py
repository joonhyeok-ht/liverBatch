import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QGridLayout
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAppPath = os.path.dirname(fileAbsPath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import AlgUtil.algSpline as algSpline
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algMeshLib as algMeshLib
import AlgUtil.algVTK as algVTK
import subSkelEditLiver
from collections import deque

import data as data

import operationColored as operation

import command.commandTerritory as commandTerritory
import command.commandTerritoryVessel as commandTerritoryVessel

import command.curveInfo as curveInfo

import tabState as tabState

import VtkObj.vtkObjText as vtkObjText
import vtkObjGuideMeshBound as vtkObjGuideMeshBound
import vtkObjGuideCLBound as vtkObjGuideCLBound
import vtkObjInterface as vtkObjInterface
from PySide6.QtWidgets import QDialog, QMessageBox
import com.componentTreeVessel as componentTreeVessel
import command.commandExtractingCLLink as commandExtractingCLLink
import skelEdit.subStateSkelEditSelectionCL as subStateSkelEditSelectionCL
import progressWindow as PW

class SelectBox(QFrame):
    def __init__(self, text, parent=None):
        super().__init__(parent)

        self.setFrameShape(QFrame.NoFrame)
        self.text = text
        self.selected = False

        self.label = QLabel(text)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                border: none;
                background: transparent;
                font-size: 14px;
            }
        """)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)
        self.setFixedSize(140, 80)

        self.update_style()

    def mousePressEvent(self, event):
        parent = self.parent()

        if parent:
            parent.toggle_box(self)

        super().mousePressEvent(event)

    def set_selected(self, selected: bool):
        self.selected = selected
        self.update_style()

    def update_style(self):
        if self.selected:
            self.setStyleSheet("""
                SelectBox {
                    border: 3px solid #0078D7;
                    border-radius: 10px;
                    background-color: #DDEEFF;
                }
            """)
        else:
            self.setStyleSheet("""
                SelectBox {
                    border: 3px solid #999999;
                    border-radius: 10px;
                    background-color: #F5F5F5;
                }

                SelectBox:hover {
                    background-color: #EEEEEE;
                }
            """)


class BoxSelectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Select Tumor Segment")
        self.resize(650, 320)

        self.box_names = [
            "S1", "S2", "S3", "S4",
            "S5", "S6", "S7", "S8"
        ]
        
        self.boxes = []

        main_layout = QVBoxLayout(self)
        self.gridLayout = QGridLayout()

        for i, name in enumerate(self.box_names):
            box = SelectBox(name, self)

            row = i // 4
            col = i % 4
            self.boxes.append(box)
            self.gridLayout.addWidget(box, row, col)

        btnLayout = QHBoxLayout()

        self.btnOk = QPushButton("ok")
        self.btnCancel = QPushButton("cancel")

        self.btnOk.clicked.connect(self.on_ok_clicked)
        self.btnCancel.clicked.connect(self.reject)

        btnLayout.addStretch()
        btnLayout.addWidget(self.btnOk)
        btnLayout.addWidget(self.btnCancel)

        main_layout.addLayout(self.gridLayout)
        main_layout.addLayout(btnLayout)

    def toggle_box(self, box):
        box.set_selected(not box.selected)

    def on_ok_clicked(self):
        selected_names = self.get_selected_box_names()

        if len(selected_names) == 0:
            QMessageBox.warning(
                self,
                "알림",
                "선택된 박스가 없습니다."
            )
            return

        self.accept()

    def get_selected_box_names(self):
        return [
            box.text
            for box in self.boxes
            if box.selected
        ]

class CTabStateSkelLabelingLiver(tabState.CTabState) :
    s_guideBoundType = "guideBound"

    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_opSelectionCL = operation.COperationSelectionCL(mediator)
        self.m_subState = subStateSkelEditSelectionCL.CSubStateSkelEditSelectionCL(self)
        self.m_guideBoundKey = ""
        self.m_skelCircle = None
    def clear(self) :
        # input your code
        self.m_guideBoundKey = ""
        self.m_opSelectionCL.clear()
        self.m_opSelectionCL = None
        self.m_skelCircle = None
        super().clear()

    def process_init(self) :
        dataInst = self.get_data()
        clinfoInx = self.get_clinfo_index()
        self.m_skeleton = dataInst.get_skeleton(clinfoInx)
        
        self.m_subState.process_end()
        self.m_subState.process_init()
        if dataInst.Ready == False :
            return
        
        for clinfoIndex in dataInst.m_clinfoIndexList:
            skeleton = dataInst.get_skeleton(clinfoIndex)
            if skeleton is None :
                return 

            # opSelectionCL = self.m_opSelectionCL
            # opSelectionCL.Skeleton = skeleton

            self.m_skelCircle = curveInfo.CSkelCircle(skeleton, 30)
            # labeling obj
            # labelColor = algLinearMath.CScoMath.to_vec3([1.0, 0.647, 0.0])
            # labelColor = algLinearMath.CScoMath.to_vec3([0.53, 0.81, 0.92])
            labelColor = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
            iCnt = skeleton.get_centerline_count()
            for inx in range(0, iCnt) :
                cl = skeleton.get_centerline(inx)
                iCLInx = int(cl.get_vertex_count() / 2)
                pos = cl.get_vertex(iCLInx)
                activeCamera = self.m_mediator.get_active_camera()
                clName = cl.Name

                key = data.CData.make_key(data.CData.s_textType, clinfoIndex, cl.ID)
                vtkText = vtkObjText.CVTKObjText(activeCamera, pos, clName, 1.0)
                vtkText.KeyType = data.CData.s_textType
                vtkText.Key = key
                vtkText.Color = labelColor
                dataInst.add_vtk_obj(vtkText)
            
            self.m_mediator.ref_key_type(data.CData.s_textType)
            
        self.m_mediator.update_viewer()
    def process(self) :
        pass
        
    def process_end(self) :
        opSelectionCL = self.m_opSelectionCL
        opSelectionCL.process_reset()
        if self.m_skelCircle is not None :
            self.m_skelCircle.clear()
            self.m_skelCircle = None
        self.m_mediator.remove_key_type(CTabStateSkelLabelingLiver.s_guideBoundType)
        self.m_mediator.remove_key_type(data.CData.s_territoryType)
        self.m_mediator.remove_key_type(data.CData.s_textType)
        self.m_mediator.update_viewer()
        self.m_cbVisibleMesh.setChecked(False)
        self.m_subState.process_end()
    def init_ui(self) :
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        label = QLabel("-- Selection Operator --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        # self.m_checkCLHierarchy = QCheckBox("Selection Centerline Hierarchy ")
        # self.m_checkCLHierarchy.setChecked(False)
        # self.m_checkCLHierarchy.stateChanged.connect(self._on_check_cl_hierarchy)
        # tabLayout.addWidget(self.m_checkCLHierarchy)

        # self.m_checkCLAncestor = QCheckBox("Selection Centerline Ancestor ")
        # self.m_checkCLAncestor.setChecked(False)
        # self.m_checkCLAncestor.stateChanged.connect(self._on_check_cl_ancestor)
        # tabLayout.addWidget(self.m_checkCLAncestor)
        layout, retList = self.m_mediator.create_layout_label_radio("SelectionMode", ["Single", "Descendant"])
        self.m_rbSingle = retList[0]
        self.m_rbDescendant = retList[1]
        self.m_rbSingle.toggled.connect(self._on_rb_single)
        self.m_rbDescendant.toggled.connect(self._on_rb_descendant)
        self.m_rbSingle.setChecked(True)
        tabLayout.addLayout(layout)
        
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)


        label = QLabel("-- Centerline Info --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        layout, self.m_editCLID = self.m_mediator.create_layout_label_editbox("Centerline ID", True)
        #tabLayout.addLayout(layout)

        layout, self.m_editCLName = self.m_mediator.create_layout_label_editbox("Centerline Label", False)
        self.m_editCLName.returnPressed.connect(self._on_btn_return_pressed_clname)
        tabLayout.addLayout(layout)

        layout, self.m_editCLPtCnt = self.m_mediator.create_layout_label_editbox("Centerline Point Count", True)
        #tabLayout.addLayout(layout)

        layout, self.m_editCLLength = self.m_mediator.create_layout_label_editbox("Centerline Length(mm)", True)
        #tabLayout.addLayout(layout)
        
        # layout, self.m_separatedDepath = self.m_mediator.create_layout_label_editbox("Threshold Depth for Main", False)
        # tabLayout.addLayout(layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        # btn = QPushButton("Test Separation")
        # btn.setStyleSheet(self.get_btn_stylesheet())
        # btn.clicked.connect(self._on_btn_test_separation)
        # tabLayout.addWidget(btn)

        btn = QPushButton("Set Labeling")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_return_pressed_clname)
        tabLayout.addWidget(btn)
        
        # btn = QPushButton("Rename Main/Extra")
        # btn.setStyleSheet(self.get_btn_stylesheet())
        # btn.clicked.connect(self._on_btn_separate_main_extra)
        # tabLayout.addWidget(btn)

        # btn = QPushButton("Save Separation")
        # btn.setStyleSheet(self.get_btn_stylesheet())
        # btn.clicked.connect(self._on_btn_save_separation)
        # tabLayout.addWidget(btn)

        
        # btn = QPushButton("Clear All Labeling")
        # btn.setStyleSheet(self.get_btn_stylesheet())
        # btn.clicked.connect(self._on_btn_clear)
        # tabLayout.addWidget(btn)

        btn = QPushButton("Select Tumor Segment")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_set_tumor_seg)
        tabLayout.addWidget(btn)
        
        label = QLabel("-- Visible --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        layout, listCB = self.m_mediator.create_layout_checkbox_array(["Tumor"])
        self.m_cbVisibleMesh = listCB[0]
        self.m_cbVisibleMesh.setChecked(False)
        self.m_cbVisibleMesh.stateChanged.connect(self._on_check_visible_tumor)
        tabLayout.addLayout(layout)
        
        btn = QPushButton("Save Centerline")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_save_for_graphics)
        tabLayout.addWidget(btn)

        # 마지막에 stretch 추가
        tabLayout.addStretch()
        
        lastUI = line
        tabLayout.setAlignment(lastUI, Qt.AlignmentFlag.AlignTop)


    # def clicked_mouse_rb(self, clickX, clickY) :
    #     listExceptKeyType = [
    #         # data.CData.s_territoryType,
    #         data.CData.s_vesselType,
    #         # data.CData.s_organType,
    #         data.CData.s_textType,
    #     ]
    #     key = self.m_mediator.picking(clickX, clickY, listExceptKeyType)
    #     if key == "" or data.CData.get_type_from_key(key) != data.CData.s_skelTypeCenterline :
    #         key = ""
    #     operation.COperationSelectionCL.clicked(self.m_opSelectionCL, key)
    #     self._update_clinfo()
    #     self.m_mediator.update_viewer()
    # def clicked_mouse_rb_shift(self, clickX, clickY) :
    #     listExceptKeyType = [
    #         # data.CData.s_territoryType,
    #         data.CData.s_vesselType,
    #         # data.CData.s_organType,
    #         data.CData.s_textType,
    #     ]
    #     key = self.m_mediator.picking(clickX, clickY, listExceptKeyType)
    #     if key == "" or data.CData.get_type_from_key(key) != data.CData.s_skelTypeCenterline :
    #         key = ""
    #     operation.COperationSelectionCL.multi_clicked(self.m_opSelectionCL, key)
    #     self._update_clinfo()
    #     self.m_mediator.update_viewer()
    # def key_press(self, keyCode : str) :
    #     if keyCode == "Escape" :
    #         if self.m_guideBoundKey != "" :
    #             self.m_mediator.remove_key(self.m_guideBoundKey)
    #             self.m_mediator.remove_key_type(data.CData.s_territoryType)
    #             self.m_guideBoundKey = ""
    #             self.m_mediator.update_viewer()
    # def key_press_with_ctrl(self, keyCode : str) : 
    #     if keyCode == "z" :
    #         print("test")
    #         #self._undo()
    def clicked_mouse_rb(self, clickX, clickY) :
        self.m_subState.clicked_mouse_rb(clickX, clickY)
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        self.m_subState.clicked_mouse_rb_shift(clickX, clickY)
    def release_mouse_rb(self):
        self.m_subState.release_mouse_rb()
    def mouse_move(self, clickX, clickY) :
        self.m_subState.mouse_move(clickX, clickY)
    def mouse_move_rb(self, clickX, clickY):
        self.m_subState.mouse_move_rb(clickX, clickY)
    def key_press(self, keyCode : str) :
        self.m_subState.key_press(keyCode)
    def key_press_with_ctrl(self, keyCode : str) : 
        self.m_subState.key_press_with_ctrl(keyCode)

    


    # protected   
    def _check_cl_hierarchy(self, bCheck : bool) :
        operation.COperationSelectionCL.checked_hierarchy(self.m_opSelectionCL, bCheck)
        self.m_mediator.update_viewer()
    def _check_cl_ancestor(self, bCheck : bool) :
        operation.COperationSelectionCL.checked_ancestor(self.m_opSelectionCL, bCheck)
        self.m_mediator.update_viewer()
    def _update_clinfo(self) :
        self.m_editCLID.setText("-1")
        self.m_editCLName.setText("")
        self.m_editCLPtCnt.setText("0")
        self.m_editCLLength.setText("0")
        #self.m_separatedDepath.setText("0")

        opSelectionCL = self.m_opSelectionCL
        iCnt = opSelectionCL.get_selection_key_count()
        if iCnt == 0 :
            return
        
        clKey = opSelectionCL.get_selection_key(0)
        keyType, groupID, id = data.CData.get_keyinfo(clKey)
        skeleton = opSelectionCL.Skeleton
        if skeleton is None :
            return
        
        cl = skeleton.get_centerline(id)
        length = float(algSpline.CCurveInfo.get_curve_len(cl.Vertex))
        self.m_editCLID.setText(f"{cl.ID}")
        self.m_editCLName.setText(f"{(cl.Name).split('_')[0]}")
        self.m_editCLPtCnt.setText(f"{cl.Vertex.shape[0]}")
        self.m_editCLLength.setText(f"{length}")
        
    def _update_clname(self, clName : str) :
        self.__update_clname_with_key(self.Skeleton, [], clName)
        # dataInst = self.get_data()
        # opSelectionCL = self.m_opSelectionCL
        # iCnt = opSelectionCL.get_selection_key_count()
        # if iCnt == 0 :
        #     return
        
        # skeleton = None
        
        # for selectionKey in opSelectionCL.m_listSelectionKey:
        #     skeleton = dataInst.get_skeleton(data.CData.get_groupID_from_key(selectionKey))
        #     if skeleton is None :
        #         return
            
        #     retListKey = []
        #     retListKey += opSelectionCL.m_listSelectionKey
        #     retListKey += opSelectionCL.m_listChildSelectionKey
        #     retListKey += opSelectionCL.m_listParentSelectionKey
              
        #     self.__update_clname_with_key(skeleton, retListKey, clName)
        self.m_mediator.update_viewer()

    # ui event
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
        self._check_cl_hierarchy(bCheck)
    def _on_check_cl_ancestor(self, state) :
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
        self._check_cl_ancestor(bCheck)
    def _on_btn_return_pressed_clname(self) :
        # Enter키를 누르면 호출되는 함수
        clName = self.m_editCLName.text()  # QLineEdit에 입력된 텍스트를 가져옴
        self._update_clname(clName)
        
    def _on_btn_separate_main_extra(self) :
        dataInst = self.get_data()
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)
        
        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            if "extra" not in cl.Name:
                cl.Name = "main"
            
                textKey = data.CData.make_key(data.CData.s_textType, 0, cl.ID)
                textObj = dataInst.find_obj_by_key(textKey)
                if textObj is not None :
                    textObj.Text = "main"
                
        ketList = dataInst.find_key_list_by_type_groupID(dataInst.s_skelTypeCenterline, clinfoInx)
        self.m_opSelectionCL._color_setting(ketList, dataInst.s_rootCLColor, dataInst.s_clColor)
        self.m_mediator.update_viewer()


        
    def _generate_progress_window(self, instance):
        dialog = PW.ProgressWindow(self.m_mediator, instance)
        result = dialog.exec()

        if result == QDialog.Accepted:
            QMessageBox.information(self.m_mediator, "Done", "작업이 완료되었습니다!")
            return True
        elif result == QDialog.Rejected:
            QMessageBox.warning(self.m_mediator, "Canceled", "작업이 취소되었습니다.")
            return False
        
        
    def _on_btn_test_separation(self) :
        dataInst = self.get_data()
        clinfoInx = self.get_clinfo_index()
        vesselKey = data.CData.make_key(data.CData.s_vesselType, clinfoInx, 0)
        vesselObj = dataInst.find_obj_by_key(vesselKey) 
        if vesselObj is None :
            return
        
        if self.m_guideBoundKey != "" :
            self.m_mediator.remove_key(self.m_guideBoundKey)
            self.m_mediator.remove_key_type(data.CData.s_territoryType)
        
        # vessel의 min-max 추출 및 정육면체 생성
        vesselPolyData = vesselObj.PolyData
        margin = 5.0
        # guideObj = vtkObjGuideMeshBound.CVTKObjGuideMeshBound(vesselPolyData, margin)
        # guideObj.KeyType = CTabStateSkelLabeling.s_guideBoundType
        # guideObj.Key = data.CData.make_key(guideObj.KeyType, 0, 0)
        # guideObj.Color = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 0.0])
        # guideObj.Opacity = 0.3
        # self.m_guideBoundKey = guideObj.Key
        # dataInst.add_vtk_obj(guideObj)
        # self.m_mediator.ref_key(guideObj.Key)

        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)
        guideObj = vtkObjGuideCLBound.CVTKObjGuideCLBound(skeleton, margin, "a")
        guideObj.KeyType = CTabStateSkelLabeling.s_guideBoundType
        guideObj.Key = data.CData.make_key(guideObj.KeyType, 0, 0)
        guideObj.Color = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 0.0])
        guideObj.Opacity = 0.3
        self.m_guideBoundKey = guideObj.Key
        dataInst.add_vtk_obj(guideObj)
        self.m_mediator.ref_key(guideObj.Key)

        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)
        # cmd = commandTerritoryVessel.CCommandTerritoryVessel(self.m_mediator)
        cmd = commandTerritoryVessel.CCommandTerritoryVesselEnhanced(self.m_mediator)
        cmd.InputData = self.get_data()
        cmd.InputSkeleton = skeleton
        cmd.InputPolyData = guideObj.PolyData
        cmd.InputVoxelizeSpacing = (1.0, 1.0, 1.0)

        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            if cl.Name != "" :
                cmd.add_cl_id(cl.ID)
        cmd.process()

        terriPolyData = cmd.OutputTerriPolyData
        if terriPolyData is None :
            print("failed to territory")
            return

        # mesh boolean
        npVertex = algVTK.CVTK.poly_data_get_vertex(vesselPolyData)
        npIndex = algVTK.CVTK.poly_data_get_triangle_index(vesselPolyData)
        meshLibVessel = algMeshLib.CMeshLib.meshlib_create(npVertex, npIndex)

        npVertex = algVTK.CVTK.poly_data_get_vertex(terriPolyData)
        npIndex = algVTK.CVTK.poly_data_get_triangle_index(terriPolyData)
        meshLibTerri = algMeshLib.CMeshLib.meshlib_create(npVertex, npIndex)

        retMesh = algMeshLib.CMeshLib.meshlib_boolean_intersection(meshLibVessel, meshLibTerri)
        npVertex = algMeshLib.CMeshLib.meshlib_get_vertex(retMesh)
        npIndex = algMeshLib.CMeshLib.meshlib_get_index(retMesh)
        vtkMesh = algVTK.CVTK.create_poly_data_triangle(npVertex, npIndex)
        vtkMesh = self.remove_noise_polydata(vtkMesh)

        # test
        self.wholeVTKMesh = algMeshLib.CMeshLib.meshlib_boolean_subtraction(meshLibVessel, meshLibTerri)
        npVertex = algMeshLib.CMeshLib.meshlib_get_vertex(self.wholeVTKMesh)
        npIndex = algMeshLib.CMeshLib.meshlib_get_index(self.wholeVTKMesh)
        self.wholeVTKMesh = algVTK.CVTK.create_poly_data_triangle(npVertex, npIndex)
        self.wholeVTKMesh = self.remove_noise_polydata(self.wholeVTKMesh)

        # rendering 
        key = data.CData.make_key(data.CData.s_territoryType, 0 ,0)
        terriObj = vtkObjInterface.CVTKObjInterface()
        terriObj.KeyType = data.CData.s_territoryType
        terriObj.Key = key
        terriObj.Color = algLinearMath.CScoMath.to_vec3([0.53, 0.81, 0.92])
        terriObj.Opacity = 0.3
        terriObj.PolyData = terriPolyData
        dataInst.add_vtk_obj(terriObj)
        self.m_mediator.ref_key(key)

        key = data.CData.make_key(data.CData.s_territoryType, 0, 1)
        terriObj = vtkObjInterface.CVTKObjInterface()
        terriObj.KeyType = data.CData.s_territoryType
        terriObj.Key = key
        terriObj.Color = algLinearMath.CScoMath.to_vec3([0.5, 0.0, 0.5])
        terriObj.Opacity = 0.5
        terriObj.PolyData = vtkMesh
        dataInst.add_vtk_obj(terriObj)
        self.m_mediator.ref_key(key)

        self.m_mediator.update_viewer()
    def _on_btn_save_for_graphics(self) :
        dataInst = self.get_data()
        userData = dataInst.UserData
        
        clOutPath = dataInst.get_cl_out_path()
        clInPath = dataInst.get_cl_in_path()
        
        for clinfoIndex in dataInst.m_clinfoIndexList:
            skelInfo = dataInst.get_skelinfo(clinfoIndex)
            blenderName = skelInfo.BlenderName # "Artery", "Bronchus", "Vein"
            outputFileName = skelInfo.JsonName
            outputFullPath = os.path.join(clOutPath, f"Centerline_{outputFileName}.json")

            vessel_key = data.CData.make_key(dataInst.s_vesselType, clinfoIndex, 0) # CLInfoIndex는 tabStatePatientLung에서 셋팅됨       
            skeleton = dataInst.get_skeleton(clinfoIndex)
            if skeleton != None :
                editInst = commandExtractingCLLink.CCommandExtractingCLLink(blenderName, skeleton, clInPath, dataInst.PatientID)
                editInst.m_secondSavePath = os.path.join(userData.m_movingBlenderPath, f"Centerline_{outputFileName}.json")
                if editInst.init(outputFullPath, commandExtractingCLLink.CCommandExtractingCLLink.MODE_VESSEL) :
                    self._generate_progress_window(editInst)
            else :
                print(f"_on_btn_save_centerline_info_for_graphics() : skeleton is None!")
                
            self._save_centerline_recontools(clinfoIndex)

    def _save_centerline_recontools(self, clinfoIndex):
        dataInst = self.get_data()
        if dataInst.Ready == False : 
            return
        
        skeleton = dataInst.get_skeleton(clinfoIndex)
        if skeleton is None :
            return
        
        self._update_skeleton(skeleton, clinfoIndex)

        clOutPath = dataInst.get_cl_out_path()

        skelinfo = dataInst.get_skelinfo(clinfoIndex)
        blenderName = skelinfo.BlenderName
        jsonName = skelinfo.JsonName
        outputFullPath = os.path.join(clOutPath, f"{jsonName}.json")
        skeleton.save(outputFullPath, blenderName)
        
    def _update_skeleton(self, skeleton, clinfoIndex) : 
        self.__update_cl_radius(skeleton, clinfoIndex)
        skeleton.rebuild_centerline_related_data()
        
    def __update_cl_radius(self, skeleton, clinfoIndex) :
        dataInst = self.get_data()

        vesselKey = data.CData.make_key(data.CData.s_vesselType, clinfoIndex, 0)
        vesselObj = dataInst.find_obj_by_key(vesselKey)
        if vesselObj is None :
            return
        vesselPolyData = vesselObj.PolyData
        # anchorVertex = algVTK.CVTK.poly_data_get_vertex(vesselPolyData)
        # tree = KDTree(anchorVertex)

        distCalculator = vtk.vtkImplicitPolyDataDistance()
        distCalculator.SetInput(vesselPolyData)

        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            dist = np.zeros(len(cl.Vertex))
            for ptInx, point in enumerate(cl.Vertex) :
                radius = abs(distCalculator.EvaluateFunction(point))
                # radius = distCalculator.EvaluateFunction(point)
                dist[ptInx] = radius
            # dist, self.m_npNNIndex = tree.query(cl.Vertex, k=1)
            # print(f"dist : {dist}")
            cl.Radius = dist
            inx = 0
                    
    def _on_btn_save_separation(self) :
        dataInst = self.get_data()
        key = data.CData.make_key(data.CData.s_territoryType, 0, 1)
        obj = dataInst.find_obj_by_key(key)
        if obj is None :
            print("not found separated vessel")
            return
        
        savePath, _ = QFileDialog.getSaveFileName(
            self.get_main_widget(),
            "Save Mesh File", 
            "", 
            "STL Files (*.stl)"
        )
        if savePath == "" : 
            return
        
        polyData = obj.PolyData
        algVTK.CVTK.save_poly_data_stl(savePath, polyData)
        print("separated vessel saved successfully.")

        # test
        polyData = self.wholeVTKMesh
        stlPath = os.path.dirname(savePath)
        savePath = os.path.join(stlPath, "whole.stl")
        algVTK.CVTK.save_poly_data_stl(savePath, polyData)
        print("whole vessel saved successfully.")
        
    def _on_btn_set_tumor_seg(self):
        self.show_boxes()
    
    def show_boxes(self):
        dialog = BoxSelectDialog(self.m_mediator)
        result = dialog.exec()
        dataInst = self.get_data()
        userdata = dataInst.UserData

        if result == QDialog.Accepted:
            selectedNames = dialog.get_selected_box_names()
            for selectedSegment in selectedNames:
                userdata.m_tumorSegSet.add(selectedSegment)
                
            QMessageBox.information(self.m_mediator, "Alarm", f"Selected Segments : {str(', ').join(selectedNames)}")
        
    def _on_btn_clear(self):
        dataInst = self.get_data()
        clinfoInxs = self.get_clinfo_indices()
        for clinfoInx in clinfoInxs:
            skeleton = dataInst.get_skeleton(clinfoInx)
            
            iCnt = skeleton.get_centerline_count()
            for inx in range(0, iCnt) :
                cl = skeleton.get_centerline(inx)
                cl.Name = ""
                
                textKey = data.CData.make_key(data.CData.s_textType, clinfoInx, cl.ID)
                textObj = dataInst.find_obj_by_key(textKey)
                if textObj is not None :
                    textObj.Text = ""
                    
            ketList = dataInst.find_key_list_by_type_groupID(dataInst.s_skelTypeCenterline, clinfoInx)
            self.m_opSelectionCL._color_setting(ketList, dataInst.s_rootCLColor, dataInst.s_clColor)
        self.m_mediator.update_viewer()

    # private
    def __update_clname_with_key(self, skeleton : algSkeletonGraph.CSkeleton, listKey : list, clName : str) :
        dataInst = self.get_data()
                
        retList = self.m_subState.m_opDragSelectionCL.get_all_selection_cl()
        groupID = self.m_subState.m_opDragSelectionCL.get_selection_groupID()
                
        for clID in retList:
            cl = skeleton.get_centerline(clID)
            cl.Name = clName

            textKey = data.CData.make_key(data.CData.s_textType, groupID, cl.ID)
            textObj = dataInst.find_obj_by_key(textKey)
            if textObj is not None :
                textObj.Text = clName

        # if self.m_separatedDepath.text() == "0":
        #     for clKey in listKey :
        #         keyType, groupID, id = data.CData.get_keyinfo(clKey)
        #         cl = skeleton.get_centerline(id)
        #         cl.Name = clName

        #         textKey = data.CData.make_key(data.CData.s_textType, groupID, cl.ID)
        #         textObj = dataInst.find_obj_by_key(textKey)
        #         if textObj is not None :
        #             textObj.Text = clName
        # else:
        #     if len(listKey) > 1:
        #         keyType, groupID, id = data.CData.get_keyinfo(listKey[0])
        #         #self._separate_leaf_with_bfs(skeleton, id, int(self.m_separatedDepath.text()), clName)
        #         self._update_clname_with_bfs(skeleton, id, int(self.m_separatedDepath.text()), clName)
        #     else:
        #         keyType, groupID, id = data.CData.get_keyinfo(listKey[0])
        #         cl = skeleton.get_centerline(id)
        #         cl.Name = clName

        #         textKey = data.CData.make_key(data.CData.s_textType, groupID, cl.ID)
        #         textObj = dataInst.find_obj_by_key(textKey)
        #         if textObj is not None :
        #             textObj.Text = clName

            
    def _update_clname_with_bfs(self, skeleton, clickRootID, maxDepth, clName):
        dataInst = self.get_data()
        
        
        depth = 0
        queue = deque([(clickRootID, depth, "main")])
        
        while queue:
            id, d, depthClass = queue.popleft()
            cl = skeleton.get_centerline(id)
            cl.Name = str(clName) + "_" + depthClass

            textKey = data.CData.make_key(data.CData.s_textType, 0, cl.ID)
            textObj = dataInst.find_obj_by_key(textKey)
            if textObj is not None :
                textObj.Text = str(clName) + "_" + depthClass
            
            parentCLID, listChildCLID = skeleton.get_conn_centerline_id(id)
            
            if cl.is_leaf():
                continue
            
            for CID in listChildCLID:
                if d < maxDepth:
                    queue.append((CID, d+1, "main"))
                else:
                    queue.append((CID, d, "extra"))
                    
                    
    def _separate_leaf_with_bfs(self, skeleton, clickRootID, maxDepth, clName):
        dataInst = self.get_data()

        
        depth = 0
        queue = deque([(clickRootID, depth, "main")])
        
        while queue:
            id, d, depthClass = queue.popleft()
            cl = skeleton.get_centerline(id)
            cl.Name = str(clName) + "_" + depthClass

            textKey = data.CData.make_key(data.CData.s_textType, 0, cl.ID)
            textObj = dataInst.find_obj_by_key(textKey)
            if textObj is not None :
                textObj.Text = str(clName) + "_" + depthClass
            
            parentCLID, listChildCLID = skeleton.get_conn_centerline_id(id)
            
            if cl.is_leaf():
                continue
            
            for CID in listChildCLID:
                
                childCL = skeleton.get_centerline(CID)
                if childCL.is_leaf() and (d >= maxDepth):
                    queue.append((CID, d+1, "extra"))
                else:
                    queue.append((CID, d+1, "main"))
        
    def _on_rb_single(self) :
        return
    def _on_rb_descendant(self) :
        return
    def getui_cb_visiblemesh_checked(self) -> bool :
        return self.m_cbVisibleMesh.isChecked()
    def _refresh_visible_vessel(self) :
        clinfoInx = self.get_clinfo_index()
        tumorKey = data.CData.make_key(data.CData.s_tumorType, 0, 0)
        if self.getui_cb_visiblemesh_checked() == False :
            self.m_mediator.unref_key(tumorKey)
        else :
            self.m_mediator.ref_key(tumorKey)
        self.m_mediator.update_viewer()
    def _on_check_visible_tumor(self):
        self._refresh_visible_vessel()
        return
    
    @property
    def Skeleton(self) -> algSkeletonGraph.CSkeleton :
        return self.m_skeleton

        

if __name__ == '__main__' :
    pass


# print ("ok ..")

