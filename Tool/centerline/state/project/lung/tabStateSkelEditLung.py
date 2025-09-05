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

import data as data

import tabState as tabState
import operation as operation

import skelEdit.subStateSkelEdit as subStateSkelEdit
import skelEdit.subStateSkelEditSelectionCL as subStateSkelEditSelectionCL
import skelEdit.subStateSkelEditSelectionBr as subStateSkelEditSelectionBr
import skelEdit.subStateSkelEditSelectionEP as subStateSkelEditSelectionEP

import subSkelEdit.subSkelEditLung as subSkelEditLung

class CTabStateSkelEdit(tabState.CTabState) :
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
        self.m_opSelectionBr.clear()
        self.m_opSelectionBr = None
        self.m_opSelectionCL.clear()
        self.m_opSelectionCL = None
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

        self.m_opSelectionCL.Skeleton = self.Skeleton

        self._get_substate(self.m_state).process_init()
    def process(self) :
        pass
    def process_end(self) :
        self._get_substate(self.m_state).process_end()
        self.m_mediator.remove_key_type("spline")
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

        label = QLabel("-- Selection Operator --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        layout, retList = self.m_mediator.create_layout_label_radio("SelectionMode", ["CL", "Br", "EP"])
        self.m_rbSelectionModeCL = retList[0]
        self.m_rbSelectionModeBr = retList[1]
        self.m_rbSelectionModeEP = retList[2]
        self.m_rbSelectionModeCL.toggled.connect(self._on_rb_selection_mode_cl)
        self.m_rbSelectionModeBr.toggled.connect(self._on_rb_selection_mode_br)
        self.m_rbSelectionModeEP.toggled.connect(self._on_rb_selection_mode_ep)
        self.m_rbSelectionModeCL.setChecked(True)
        tabLayout.addLayout(layout)

        self.m_checkCLHierarchy = QCheckBox("Selection Centerline Hierarchy ")
        self.m_checkCLHierarchy.setChecked(False)
        self.m_checkCLHierarchy.stateChanged.connect(self._on_check_cl_hierarchy)
        tabLayout.addWidget(self.m_checkCLHierarchy)

        self.m_checkCLAncestor = QCheckBox("Selection Centerline Ancestor ")
        self.m_checkCLAncestor.setChecked(False)
        self.m_checkCLAncestor.stateChanged.connect(self._on_check_cl_ancestor)
        tabLayout.addWidget(self.m_checkCLAncestor)

        layout, self.m_sliderRange, self.m_editRange = self.m_mediator.create_layout_label_slider_editbox("Range", CTabStateSkelEdit.s_minRange, CTabStateSkelEdit.s_maxRange, 1, True)
        self.m_sliderRange.setValue(2)
        self.m_sliderRange.valueChanged.connect(self._on_slider_changed_value)
        tabLayout.addLayout(layout)

        btn = QPushButton("Apply Centerline Root to Selection")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_apply_root_cl)
        tabLayout.addWidget(btn)

        btn = QPushButton("Save Centerline")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_save_cl)
        tabLayout.addWidget(btn)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        btn = QPushButton("Test Refined Centerline Point")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_refine_cl_point)
        tabLayout.addWidget(btn)
        

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        #TODO 보완해야함.
        btn = QPushButton("Check Outside")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_check_outside)
        tabLayout.addWidget(btn)

        btn = QPushButton("Save (Graphics)")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_save_centerline_info_for_graphics)
        tabLayout.addWidget(btn)
        

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
    def setui_range(self, range : int) :
        self.m_sliderRange.blockSignals(True)
        self.m_sliderRange.setValue(range)
        self.m_sliderRange.blockSignals(False)
        self.m_editRange.setText(f"{range}")

    def getui_cl_hierarchy(self) -> bool :
        if self.m_checkCLHierarchy.isChecked() :
            return True
        return False
    def getui_cl_ancestor(self) -> bool :
        if self.m_checkCLAncestor.isChecked() :
            return True
        return False
    def getui_range(self) -> int :
        return self.m_sliderRange.value()


    # protected 
    def _get_substate(self, inx : int) -> subStateSkelEdit.CSubStateSkelEdit :
        return self.m_listSubState[inx]  


    # ui event
    def _on_rb_selection_mode_cl(self) :
        if self.m_bReady == False :
            return
        
        if self.m_rbSelectionModeCL.isChecked() :
            self.m_state = 0
            self._get_substate(self.m_state).process_init()
        else :
            self._get_substate(self.m_state).process_end()
    def _on_rb_selection_mode_br(self) :
        if self.m_bReady == False :
            return
        
        if self.m_rbSelectionModeBr.isChecked() :
            self.m_state = 1
            self._get_substate(self.m_state).process_init()
        else :
            self._get_substate(self.m_state).process_end()
    def _on_rb_selection_mode_ep(self) :
        if self.m_bReady == False :
            return
        
        if self.m_rbSelectionModeEP.isChecked() :
            self.m_state = 2
            self._get_substate(self.m_state).process_init()
        else :
            self._get_substate(self.m_state).process_end()
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
        self._get_substate(self.m_state).check_cl_hierarchy(bCheck)
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
        self._get_substate(self.m_state).check_cl_ancestor(bCheck)
    def _on_btn_apply_root_cl(self) :
        self._get_substate(self.m_state).apply_root_cl()
    def _on_btn_save_cl(self) :
        self._get_substate(self.m_state).save_cl()
    def _on_btn_refine_cl_point(self) :
        self.m_mediator.remove_key_type("spline")
        # self.m_mediator.unref_key_type(data.CData.s_skelTypeCenterline)

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
    def _on_slider_changed_value(self) :
        value = self.m_sliderRange.value()
        self.m_editRange.setText(f"{value}")
        self._get_substate(self.m_state).change_range(value)
    
    def _on_btn_check_outside(self) :
        # polydata 가져오기
        dataInst = self.get_data()
        vessel_key = data.CData.make_key(dataInst.s_vesselType, dataInst.CLInfoIndex, 0) # CLInfoIndex는 tabStatePatientLung에서 셋팅됨       
        # skeleton = dataInst.get_skeleton(skelinfoInx)
        vessel_obj = dataInst.find_obj_by_key(vessel_key)
        polydata = vessel_obj.PolyData
        if polydata != None :
            editInst = subSkelEditLung.CSubSkelEditLung(polydata)
            outside_list = editInst.check_outside_centerline_point(skeleton=self.m_skeleton, polydata=polydata)
            #TODO : outside_list 를 화면에 표시하기
        else :
            print(f"check_outside_ERROR : polydata is None!")
    def _on_btn_save_centerline_info_for_graphics(self) :
        dataInst = self.get_data()

        clOutPath = dataInst.get_cl_out_path()
        clInPath = dataInst.get_cl_in_path()
        clInfo = dataInst.OptionInfo.get_centerlineinfo(dataInst.CLInfoIndex)
        blenderName = clInfo.get_input_blender_name() # "Artery", "Bronchus", "Vein"
        outputFileName = clInfo.OutputName
        outputFullPath = os.path.join(clOutPath, f"Centerline_{outputFileName}.json")

        vessel_key = data.CData.make_key(dataInst.s_vesselType, dataInst.CLInfoIndex, 0) # CLInfoIndex는 tabStatePatientLung에서 셋팅됨       
        vessel_obj = dataInst.find_obj_by_key(vessel_key)
        # polydata = vessel_obj.PolyData
        skeleton = dataInst.get_skeleton(dataInst.CLInfoIndex)
        # if polydata != None and skeleton != None :
        if skeleton != None :
            editInst = subSkelEditLung.CSubSkelEditLung(blenderName, skeleton, clInPath)
            if editInst.init(outputFullPath) :
                editInst.process()
                self.m_mediator.show_dialog("Save Info Done!" ) 
        else :
            print(f"_on_btn_save_centerline_info_for_graphics() : skeleton is None!")

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
    #sally
    @Skeleton.setter
    def Skeleton(self, skeleton) :
        self.m_skeleton = skeleton


        
        





if __name__ == '__main__' :
    pass


# print ("ok ..")

