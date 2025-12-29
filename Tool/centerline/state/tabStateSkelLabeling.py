import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox
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

import data as data

import operation as operation

import command.commandTerritory as commandTerritory
import command.commandTerritoryVessel as commandTerritoryVessel

import command.curveInfo as curveInfo

import tabState as tabState

import VtkObj.vtkObjText as vtkObjText
import vtkObjGuideMeshBound as vtkObjGuideMeshBound
import vtkObjGuideCLBound as vtkObjGuideCLBound
import vtkObjInterface as vtkObjInterface


class CTabStateSkelLabeling(tabState.CTabState) :
    s_guideBoundType = "guideBound"


    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_opSelectionCL = operation.COperationSelectionCL(mediator)
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
        if dataInst.Ready == False :
            return
        
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)
        if skeleton is None :
            return 

        opSelectionCL = self.m_opSelectionCL
        opSelectionCL.Skeleton = skeleton

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

            key = data.CData.make_key(data.CData.s_textType, 0, cl.ID)
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
        self.m_mediator.remove_key_type(CTabStateSkelLabeling.s_guideBoundType)
        self.m_mediator.remove_key_type(data.CData.s_territoryType)
        self.m_mediator.remove_key_type(data.CData.s_textType)
        self.m_mediator.update_viewer()

    def init_ui(self) :
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        label = QLabel("-- Selection Operator --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        self.m_checkCLHierarchy = QCheckBox("Selection Centerline Hierarchy ")
        self.m_checkCLHierarchy.setChecked(False)
        self.m_checkCLHierarchy.stateChanged.connect(self._on_check_cl_hierarchy)
        tabLayout.addWidget(self.m_checkCLHierarchy)

        self.m_checkCLAncestor = QCheckBox("Selection Centerline Ancestor ")
        self.m_checkCLAncestor.setChecked(False)
        self.m_checkCLAncestor.stateChanged.connect(self._on_check_cl_ancestor)
        tabLayout.addWidget(self.m_checkCLAncestor)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)


        label = QLabel("-- Centerline Info --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        layout, self.m_editCLID = self.m_mediator.create_layout_label_editbox("Centerline ID", True)
        tabLayout.addLayout(layout)

        layout, self.m_editCLName = self.m_mediator.create_layout_label_editbox("Centerline Label", False)
        self.m_editCLName.returnPressed.connect(self._on_return_pressed_clname)
        tabLayout.addLayout(layout)

        layout, self.m_editCLPtCnt = self.m_mediator.create_layout_label_editbox("Centerline Point Count", True)
        tabLayout.addLayout(layout)

        layout, self.m_editCLLength = self.m_mediator.create_layout_label_editbox("Centerline Length(mm)", True)
        tabLayout.addLayout(layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        btn = QPushButton("Test Separation")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_test_separation)
        tabLayout.addWidget(btn)

        btn = QPushButton("Save Separation")
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
        listExceptKeyType = [
            # data.CData.s_territoryType,
            data.CData.s_vesselType,
            # data.CData.s_organType,
            data.CData.s_textType,
        ]
        key = self.m_mediator.picking(clickX, clickY, listExceptKeyType)
        if key == "" or data.CData.get_type_from_key(key) != data.CData.s_skelTypeCenterline :
            key = ""
        operation.COperationSelectionCL.clicked(self.m_opSelectionCL, key)
        self._update_clinfo()
        self.m_mediator.update_viewer()
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        listExceptKeyType = [
            # data.CData.s_territoryType,
            data.CData.s_vesselType,
            # data.CData.s_organType,
            data.CData.s_textType,
        ]
        key = self.m_mediator.picking(clickX, clickY, listExceptKeyType)
        if key == "" or data.CData.get_type_from_key(key) != data.CData.s_skelTypeCenterline :
            key = ""
        operation.COperationSelectionCL.multi_clicked(self.m_opSelectionCL, key)
        self._update_clinfo()
        self.m_mediator.update_viewer()
    def key_press(self, keyCode : str) :
        if keyCode == "Escape" :
            if self.m_guideBoundKey != "" :
                self.m_mediator.remove_key(self.m_guideBoundKey)
                self.m_mediator.remove_key_type(data.CData.s_territoryType)
                self.m_guideBoundKey = ""
                self.m_mediator.update_viewer()


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
        self.m_editCLName.setText(f"{cl.Name}")
        self.m_editCLPtCnt.setText(f"{cl.Vertex.shape[0]}")
        self.m_editCLLength.setText(f"{length}")
    def _update_clname(self, clName : str) :
        opSelectionCL = self.m_opSelectionCL
        iCnt = opSelectionCL.get_selection_key_count()
        if iCnt == 0 :
            return
        skeleton = opSelectionCL.Skeleton
        if skeleton is None :
            return
        
        retListKey = []
        retListKey += opSelectionCL.m_listSelectionKey
        retListKey += opSelectionCL.m_listChildSelectionKey
        retListKey += opSelectionCL.m_listParentSelectionKey
        
        self.__update_clname_with_key(skeleton, retListKey, clName)
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
    def _on_return_pressed_clname(self) :
        # Enter키를 누르면 호출되는 함수
        clName = self.m_editCLName.text()  # QLineEdit에 입력된 텍스트를 가져옴
        self._update_clname(clName)
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

        

        


    # private
    def __update_clname_with_key(self, skeleton : algSkeletonGraph.CSkeleton, listKey : list, clName : str) :
        dataInst = self.get_data()

        for clKey in listKey :
            keyType, groupID, id = data.CData.get_keyinfo(clKey)
            cl = skeleton.get_centerline(id)
            cl.Name = clName

            textKey = data.CData.make_key(data.CData.s_textType, 0, cl.ID)
            textObj = dataInst.find_obj_by_key(textKey)
            if textObj is not None :
                textObj.Text = clName


if __name__ == '__main__' :
    pass


# print ("ok ..")

