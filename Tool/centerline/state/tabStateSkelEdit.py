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


import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algSkeletonGraph as algSkeletonGraph

import VtkObj.vtkObjLine as vtkObjLine
import VtkObj.vtkObjSphere as vtkObjSphere

import vtkObjGuideCL as vtkObjGuideCL
import vtkObjInterface as vtkObjInterface

import data as data

import tabState as tabState
import operation as operation

import skelEdit.subStateSkelEdit as subStateSkelEdit
import skelEdit.subStateSkelEditSelectionCL as subStateSkelEditSelectionCL
import skelEdit.subStateSkelEditSelectionBr as subStateSkelEditSelectionBr
import skelEdit.subStateSkelEditSelectionEP as subStateSkelEditSelectionEP


class CTabStateSkelEdit(tabState.CTabState) :
    s_rootPointType = "RootPoint"
    s_rootPointRadius = 3.0

    s_minRange = 2
    s_maxRange = 50


    def __init__(self, mediator):
        self.m_bReady = False

        super().__init__(mediator)
        # input your code
        self.m_state = 0
        self.m_opSelectionCL = operation.COperationSelectionCL(mediator)
        self.m_opSelectionBr = operation.COperationSelectionBr(mediator)
        self.m_opSelectionEP = operation.COperationSelectionEP(mediator)
        self.m_listSubState = []
        self.m_skeleton = None

        self.m_listSubState.append(subStateSkelEditSelectionCL.CSubStateSkelEditSelectionCL(self))
        self.m_listSubState.append(subStateSkelEditSelectionBr.CSubStateSkelEditSelectionBr(self))
        self.m_listSubState.append(subStateSkelEditSelectionEP.CSubStateSkelEditSelectionEP(self))

        self.m_bReady = True
    def clear(self) :
        # input your code
        self.m_listSubState.clear()
        self.m_skeleton = None
        self.m_opSelectionCL.clear()
        self.m_opSelectionCL = None
        self.m_opSelectionBr.clear()
        self.m_opSelectionBr = None
        self.m_opSelectionEP.clear()
        self.m_opSelectionEP = None
        self.m_state = 0
        self.m_bReady = False
        super().clear()

    def process_init(self) :
        rootID = -1
        clCount = 0
        brCount = 0
        self.setui_rootid(rootID)
        self.setui_cl_count(clCount)
        self.setui_br_count(brCount)

        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        
        clinfoInx = self.get_clinfo_index()
        self.m_skeleton = dataInst.get_skeleton(clinfoInx)
        if self.m_skeleton is None :
            return 
        
        rootID = self.Skeleton.RootCenterline.ID
        clCount = self.Skeleton.get_centerline_count()
        brCount = self.Skeleton.get_branch_count()

        self.setui_rootid(rootID)
        self.setui_cl_count(clCount)
        self.setui_br_count(brCount)
        self.__apply_root_point()

        self.m_opSelectionCL.Skeleton = self.Skeleton

        self._get_substate(self.m_state).process_init()
    def process(self) :
        pass
    def process_end(self) :
        self._get_substate(self.m_state).process_end()
        self.m_mediator.remove_key_type("spline")
        self.m_mediator.remove_key_type(self.s_rootPointType)
        self.m_mediator.clear_cmd()

    def init_ui(self) :
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        label = QLabel("-- Skeleton Info --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        layout, self.m_editSKelEditRootID = self.m_mediator.create_layout_label_editbox("RootID", True)
        tabLayout.addLayout(layout)

        layout, self.m_editSkelEditCLCount = self.m_mediator.create_layout_label_editbox("Centerline Count", True)
        tabLayout.addLayout(layout)

        layout, self.m_editSkelEditBranchCount = self.m_mediator.create_layout_label_editbox("Branch Count", True)
        tabLayout.addLayout(layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        # sub tab 추가 
        tabUI = QTabWidget()
        tabLayout.addWidget(tabUI)

        title = "Centerline"
        tab = QWidget()
        subTabLayout = QVBoxLayout(tab)

        layout, retList = self.m_mediator.create_layout_label_radio("SelectionMode", ["Single", "Descendant"])
        self.m_rbSingle = retList[0]
        self.m_rbDescendant = retList[1]
        self.m_rbSingle.toggled.connect(self._on_rb_single)
        self.m_rbDescendant.toggled.connect(self._on_rb_descendant)
        self.m_rbSingle.setChecked(True)
        subTabLayout.addLayout(layout)

        subTabLayout.addStretch()
        tabUI.addTab(tab, title)


        title = "Branch"
        tab = QWidget()
        subTabLayout = QVBoxLayout(tab)

        layout, self.m_sliderBranchRange, self.m_editBranchRange = self.m_mediator.create_layout_label_slider_editbox("Branch Range", CTabStateSkelEdit.s_minRange, CTabStateSkelEdit.s_maxRange, 1, True)
        self.m_sliderBranchRange.setValue(2)
        self.m_sliderBranchRange.valueChanged.connect(self._on_slider_changed_value_branch)
        subTabLayout.addLayout(layout)

        subTabLayout.addStretch()
        tabUI.addTab(tab, title)


        title = "EndPoint"
        tab = QWidget()
        subTabLayout = QVBoxLayout(tab)

        layout, self.m_sliderEpRange, self.m_editEpRange = self.m_mediator.create_layout_label_slider_editbox("EndPoint Range", CTabStateSkelEdit.s_minRange, CTabStateSkelEdit.s_maxRange, 1, True)
        self.m_sliderEpRange.setValue(2)
        self.m_sliderEpRange.valueChanged.connect(self._on_slider_changed_value_ep)
        subTabLayout.addLayout(layout)

        subTabLayout.addStretch()
        tabUI.addTab(tab, title)

        tabUI.currentChanged.connect(self._on_tab_changed)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        label = QLabel("-- Apply --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        btn = QPushButton("Change Root Start Point")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_change_root_point_start)
        tabLayout.addWidget(btn)

        btn = QPushButton("Apply Centerline Root to Selection")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_apply_root_cl)
        tabLayout.addWidget(btn)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        btn = QPushButton("Save Centerline")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_save_cl)
        tabLayout.addWidget(btn)

        # btn = QPushButton("Test Refined Centerline Point")
        # btn.setStyleSheet(self.get_btn_stylesheet())
        # btn.clicked.connect(self._on_btn_refine_cl_point)
        # tabLayout.addWidget(btn)
        

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        lastUI = line
        tabLayout.setAlignment(lastUI, Qt.AlignmentFlag.AlignTop)

    def clicked_mouse_rb(self, clickX, clickY) :
        self._get_substate(self.m_state).clicked_mouse_rb(clickX, clickY)
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        self._get_substate(self.m_state).clicked_mouse_rb_shift(clickX, clickY)
    def release_mouse_rb(self):
        self._get_substate(self.m_state).release_mouse_rb()
    def mouse_move(self, clickX, clickY) :
        self._get_substate(self.m_state).mouse_move(clickX, clickY)
    def mouse_move_rb(self, clickX, clickY):
        self._get_substate(self.m_state).mouse_move_rb(clickX, clickY)
    def key_press(self, keyCode : str) :
        self._get_substate(self.m_state).key_press(keyCode)
    def key_press_with_ctrl(self, keyCode : str) : 
        self._get_substate(self.m_state).key_press_with_ctrl(keyCode)

    # ui
    def setui_rootid(self, rootID : int) :
        self.m_editSKelEditRootID.setText(f"{rootID}")
    def setui_cl_count(self, clCount : int) :
        self.m_editSkelEditCLCount.setText(f"{clCount}")
    def setui_br_count(self, brCount : int) :
        self.m_editSkelEditBranchCount.setText(f"{brCount}")
    def setui_branch_range(self, range : int) :
        self.m_sliderBranchRange.blockSignals(True)
        self.m_sliderBranchRange.setValue(range)
        self.m_sliderBranchRange.blockSignals(False)
        self.m_editBranchRange.setText(f"{range}")
    def setui_ep_range(self, range : int) :
        self.m_sliderEpRange.blockSignals(True)
        self.m_sliderEpRange.setValue(range)
        self.m_sliderEpRange.blockSignals(False)
        self.m_editEpRange.setText(f"{range}")

    def getui_branch_range(self) -> int :
        return self.m_sliderBranchRange.value()
    def getui_ep_range(self) -> int :
        return self.m_sliderBranchRange.value()
    


    # protected 
    def _get_substate(self, inx : int) -> subStateSkelEdit.CSubStateSkelEdit :
        return self.m_listSubState[inx]  


    # ui event
    def _on_tab_changed(self, index):
        print(f"Tab changed: index={index}")
        self._get_substate(self.m_state).process_end()
        self.m_state = index
        self._get_substate(self.m_state).process_init()
    def _on_rb_single(self) :
        if self.m_bReady == False :
            return
    def _on_rb_descendant(self) :
        if self.m_bReady == False :
            return
        
    def _on_btn_change_root_point_start(self) :
        dataInst = self.get_data()
        clinfoInx = self.get_clinfo_index()
        self.m_skeleton = dataInst.get_skeleton(clinfoInx)
        if self.m_skeleton is None :
            return 
        
        rootCL = self.m_skeleton.RootCenterline
        rootCL.reverse()
        self.__apply_root_point()
        self.m_skeleton.build_tree(rootCL.ID)
        self.m_mediator.update_viewer()
    def _on_btn_apply_root_cl(self) :
        self._get_substate(self.m_state).apply_root_cl()
    def _on_btn_save_cl(self) :
        self._get_substate(self.m_state).save_cl()
    def _on_btn_refine_cl_point(self) :
        self.m_mediator.remove_key_type("spline")

        if self.m_mediator.Ready == False :
            return 
        
        dataInst = tabState.CTabState.get_data(self.m_mediator)
        opSelectionCL = tabState.CTabState.get_operator_selection_cl(self.m_mediator)
        retList = opSelectionCL.get_selection_cl_list()
        if retList is None :
            print("not selecting centerline")
            return
        if len(retList) == 1 :
            print("least 2")
            return
        
        # 일단 root 기준으로 order가 정해졌다고 가정
        clID0 = retList[0]
        clID1 = retList[1]
        print(f"{clID0}, {clID1}")

        skeleton = opSelectionCL.Skeleton
        cl0 = skeleton.get_centerline(clID0) # parent
        cl1 = skeleton.get_centerline(clID1) # child

        splineVertex = np.concatenate((cl0.Vertex, cl1.Vertex[1:]), axis=0)
        splineVertex = self.__laplacian_smooth(splineVertex, 25, 0.9)
        splineIndex = algVTK.CVTK.make_line_strip_index(splineVertex.shape[0])

        polyData = algVTK.CVTK.create_poly_data_line(splineVertex, splineIndex)

        # vtkObj
        splineKey = data.CData.make_key("spline", 0, 0)
        vtkObj = dataInst.add_obj(splineKey, polyData, algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0]))
        vtkObj.Actor.GetProperty().SetLineWidth(4.0)

        sphereInx = cl0.Vertex.shape[0] - 1
        sphereKey = data.CData.make_key("spline", 0, 1)
        sphereVtkObj = vtkObjSphere.CVTKObjSphere(splineVertex[sphereInx].reshape((-1, 3)), 1.0)
        sphereVtkObj.set_color(algLinearMath.CScoMath.to_vec3([1.0, 0.0, 1.0]))
        vtkObj = dataInst.add_vtk_obj(sphereKey, sphereVtkObj)


        # vertex0 = cl0.Vertex.copy()
        # vertex1 = cl1.Vertex.copy()
        # self.__adjust_curve_c1(vertex0, vertex1)
        # polyData0 = self.__make_spline_source(vertex0)
        # polyData1 = self.__make_spline_source(vertex1)

        # polyData = self.__merge_polydata(polyData0, polyData1)

        # splineKey = data.CData.make_key("spline", 0, 1)
        # vtkObj = dataInst.add_obj(splineKey, polyData1, algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0]))
        # vtkObj.Actor.GetProperty().SetLineWidth(4.0)


        self.m_mediator.ref_key_type("spline")
        self.m_mediator.update_viewer()
    def _on_slider_changed_value_branch(self) :
        value = self.m_sliderBranchRange.value()
        self.m_editBranchRange.setText(f"{value}")
        self._get_substate(self.m_state).change_range(value)
    def _on_slider_changed_value_ep(self) :
        value = self.m_sliderEpRange.value()
        self.m_editEpRange.setText(f"{value}")
        self._get_substate(self.m_state).change_range(value)

    # private
    def __apply_root_point(self) :
        dataInst = self.get_data()
        clinfoInx = self.get_clinfo_index()

        self.m_skeleton = dataInst.get_skeleton(clinfoInx)
        if self.m_skeleton is None :
            return 
        
        rootCL = self.Skeleton.RootCenterline
        rootPoint = rootCL.get_vertex(0)
        rootPointMesh = algVTK.CVTK.create_poly_data_sphere(rootPoint, self.s_rootPointRadius)

        key = data.CData.make_key(self.s_rootPointType, 0, 0)
        obj = dataInst.find_obj_by_key(key)
        if obj is None :
            obj = vtkObjInterface.CVTKObjInterface()
            obj.KeyType = self.s_rootPointType
            obj.Key = key
            obj.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 1.0])
            obj.Opacity = 1.0
            obj.PolyData = rootPointMesh
            dataInst.add_vtk_obj(obj)
            self.m_mediator.ref_key(key)
        else :
            obj.PolyData = rootPointMesh
    def __adjust_curve_c1(self, vertex0, vertex1) : 
        slope0 = np.diff(vertex0[-2:], axis=0)[0]
        slope1 = np.diff(vertex1[:2], axis=0)[0]
        factor = slope0 / np.linalg.norm(slope1)
        vertex1[0] = vertex0[-1] + slope0 * factor
    def __make_spline_source(self, vertex : np.ndarray) -> vtk.vtkPolyData :
        points = vtk.vtkPoints()
        for point in vertex :
            points.InsertNextPoint(point)
        spline = vtk.vtkParametricSpline()
        spline.SetPoints(points)

        splineSource = vtk.vtkParametricFunctionSource()
        splineSource.SetParametricFunction(spline)
        splineSource.Update()
        return splineSource.GetOutput()
    def __laplacian_smooth(self, vertex : np.ndarray, iterations=10, alpha=0.5) -> np.ndarray:
        """
        라플라시안 스무딩을 적용하여 제어점들의 위치를 부드럽게 보정한다.
        
        control_points: 제어점들의 3D 배열
        iterations: 스무딩을 반복하는 횟수
        alpha: 스무딩 강도 (0~1 사이의 값)
        """
        smoothedVertex = vertex.copy()
        iVertexCnt = vertex.shape[0]

        for _ in range(iterations):
            newPoints = smoothedVertex.copy()
            for i in range(1, iVertexCnt - 1):
                # 현재 제어점을 주변 제어점들의 평균으로 이동
                newPoints[i] = (1 - alpha) * smoothedVertex[i] + \
                                alpha * (smoothedVertex[i - 1] + smoothedVertex[i + 1]) / 2
            smoothedVertex = newPoints
        return smoothedVertex
    def __merge_polydata(self, polyData0, polyData1) -> vtk.vtkPolyData :
        combinedPolyData = vtk.vtkAppendPolyData()
        combinedPolyData.AddInputData(polyData0)
        combinedPolyData.AddInputData(polyData1)
        combinedPolyData.Update()
        return combinedPolyData.GetOutput()

    
    @property
    def Skeleton(self) -> algSkeletonGraph.CSkeleton :
        return self.m_skeleton

        
        





if __name__ == '__main__' :
    pass


# print ("ok ..")

