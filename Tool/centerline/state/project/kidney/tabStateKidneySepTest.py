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

import userDataKidney as userDataKidney

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algMeshLib as algMeshLib
import AlgUtil.algVTK as algVTK

import vtkObjSTL as vtkObjSTL
import vtkObjInterface as vtkObjInterface


class CTabStateKidneySepTest(tabState.CTabState) :
    s_kidneyKeyType = "kidney"
    s_exoKeyType = "exo"
    s_sepKeyType = "sep"


    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
    def clear(self) :
        # input your code
        super().clear()

    def process_init(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        
        userData = self._get_userdata()
        if userData is None :
            return
        
        iCnt = userData.get_kidneyname_count()
        for inx in range(0, iCnt) :
            kidneyName = userData.get_kidneyname(inx)
            self.m_cbKidney.addItem(f"{kidneyName}")

            terriInPath = dataInst.get_terri_in_path()
            fullPath = os.path.join(terriInPath, f"{kidneyName}.stl")

            key = data.CData.make_key(CTabStateKidneySepTest.s_kidneyKeyType, 0, inx)
            kidneyObj = vtkObjSTL.CVTKObjSTL(self.get_optioninfo(), fullPath)
            kidneyObj.KeyType = CTabStateKidneySepTest.s_kidneyKeyType
            kidneyObj.Key = key
            kidneyObj.Color = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 1.0])
            kidneyObj.Opacity = 0.3
            if kidneyObj.Ready == False :
                print(f"not found kindney : {kidneyName}")
                continue

            dataInst.add_vtk_obj(kidneyObj)


        iCnt = userData.get_exoname_count()
        for inx in range(0, iCnt) :
            exoName = userData.get_exoname(inx)
            self.m_cbExo.addItem(f"{exoName}")

            terriInPath = dataInst.get_terri_in_path()
            fullPath = os.path.join(terriInPath, f"{exoName}.stl")

            key = data.CData.make_key(CTabStateKidneySepTest.s_exoKeyType, 0, inx)
            exoObj = vtkObjSTL.CVTKObjSTL(self.get_optioninfo(), fullPath)
            exoObj.KeyType = CTabStateKidneySepTest.s_exoKeyType
            exoObj.Key = key
            exoObj.Color = algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0])
            exoObj.Opacity = 0.3
            if exoObj.Ready == False :
                print(f"not found kindney : {exoName}")
                continue

            dataInst.add_vtk_obj(exoObj)
        
        self.setui_kidney_index(0)
        self.setui_exo_index(0)
        self.setui_check_visible_kidney_tumor(True)
        self.m_mediator.update_viewer()
    def process(self) :
        pass
    def process_end(self) :
        self.m_cbKidney.clear()
        self.m_cbExo.clear()

        self.m_mediator.remove_key_type(CTabStateKidneySepTest.s_kidneyKeyType)
        self.m_mediator.remove_key_type(CTabStateKidneySepTest.s_exoKeyType)
        self.m_mediator.remove_key_type(CTabStateKidneySepTest.s_sepKeyType)

    def init_ui(self) :
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        label = QLabel("-- Kidney-Tumor Separation Test --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        self.m_checkVisibleKidneyTumor = QCheckBox("Visible Kidney-Tumor ")
        self.m_checkVisibleKidneyTumor.setChecked(True)
        self.m_checkVisibleKidneyTumor.stateChanged.connect(self._on_check_visible_kidney_tumor)
        tabLayout.addWidget(self.m_checkVisibleKidneyTumor)

        layout, self.m_cbKidney = self.m_mediator.create_layout_label_combobox("Kidney")
        self.m_cbKidney.currentIndexChanged.connect(self._on_cb_kidney)
        tabLayout.addLayout(layout)

        layout, self.m_cbExo = self.m_mediator.create_layout_label_combobox("Exo")
        self.m_cbExo.currentIndexChanged.connect(self._on_cb_exo)
        tabLayout.addLayout(layout)

        btn = QPushButton("Test Separation")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_test_separation)
        tabLayout.addWidget(btn)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        lastUI = line
        tabLayout.setAlignment(lastUI, Qt.AlignmentFlag.AlignTop)


    def clicked_mouse_rb(self, clickX, clickY) :
        pass
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        pass

    def setui_kidney(self, kidneyName : str) :
        self.m_cbKidney.blockSignals(True)
        self.m_cbKidney.setCurrentText(kidneyName)
        self.m_cbKidney.blockSignals(False)
    def setui_kidney_index(self, index : int) :
        self.m_cbKidney.blockSignals(True)
        self.m_cbKidney.setCurrentIndex(index)
        self.m_cbKidney.blockSignals(False)
    def setui_exo(self, exoName : str) :
        self.m_cbExo.blockSignals(True)
        self.m_cbExo.setCurrentText(exoName)
        self.m_cbExo.blockSignals(False)
    def setui_exo_index(self, index : int) :
        self.m_cbExo.blockSignals(True)
        self.m_cbExo.setCurrentIndex(index)
        self.m_cbExo.blockSignals(False)
    def setui_check_visible_kidney_tumor(self, bCheck : bool) :
        self.m_checkVisibleKidneyTumor.blockSignals(True)
        self.m_checkVisibleKidneyTumor.setChecked(bCheck)
        self.m_checkVisibleKidneyTumor.blockSignals(False)
        self._refresh_visible_kidney_tumor()
    
    def getui_kidney(self) -> str :
        return self.m_cbKidney.currentText()
    def getui_kidney_index(self) -> int :
        return self.m_cbKidney.currentIndex()
    def getui_exo(self) -> str :
        return self.m_cbExo.currentText()
    def getui_exo_index(self) -> int :
        return self.m_cbExo.currentIndex()
    def getui_check_visible_kidney_tumor(self) -> bool :
        return self.m_checkVisibleKidneyTumor.isChecked() 



    # protected
    def _get_userdata(self) -> userDataKidney.CUserDataKidney :
        return self.get_data().find_userdata(userDataKidney.CUserDataKidney.s_userDataKey)
    def _refresh_visible_kidney_tumor(self) :
        if self.getui_check_visible_kidney_tumor() == True :
            self.m_mediator.ref_key_type(CTabStateKidneySepTest.s_kidneyKeyType)
            self.m_mediator.ref_key_type(CTabStateKidneySepTest.s_exoKeyType)
        else :
            self.m_mediator.unref_key_type(CTabStateKidneySepTest.s_kidneyKeyType)
            self.m_mediator.unref_key_type(CTabStateKidneySepTest.s_exoKeyType)
        self.m_mediator.update_viewer()
    def _polydata_dilation(self, obj : vtkObjInterface.CVTKObjInterface, factor : float = 0.2) :
        polyData = obj.PolyData

        normalsGenerator = vtk.vtkPolyDataNormals()
        normalsGenerator.SetInputData(polyData)
        normalsGenerator.ComputePointNormalsOn()  # Vertex마다 normal 계산
        normalsGenerator.Update()
        normals = normalsGenerator.GetOutput().GetPointData().GetNormals()

        points = polyData.GetPoints()
        for i in range(points.GetNumberOfPoints()):
            point = points.GetPoint(i)
            normal = normals.GetTuple(i)
            
            # normal 방향으로 point를 이동
            newPoint = [
                point[0] + factor * normal[0],
                point[1] + factor * normal[1],
                point[2] + factor * normal[2]
            ]
            
            points.SetPoint(i, newPoint)

        # 업데이트된 mesh로 설정
        polyData.Modified()
    def _remove_noise(self, obj : vtkObjInterface.CVTKObjInterface) :
        polyData = obj.PolyData
        connectivityFilter = vtk.vtkConnectivityFilter()
        connectivityFilter.SetInputData(polyData)

        connectivityFilter.SetExtractionModeToLargestRegion()
        connectivityFilter.Update()

        # 가장 큰 구성 요소를 추출한 결과를 vtkPolyData로 얻기
        polyData = connectivityFilter.GetOutput()
        obj.PolyData = polyData
    
    # ui event 
    def _on_cb_kidney(self, index) :
        pass
    def _on_cb_exo(self, index) :
        pass
    def _on_btn_test_separation(self) :
        userData = self._get_userdata()
        if userData is None :
            return
        if userData.get_kidneyname_count() == 0 :
            return
        
        dataInst = self.get_data()
        
        kidneyInx = self.getui_kidney_index()
        key = data.CData.make_key(CTabStateKidneySepTest.s_kidneyKeyType, 0, kidneyInx)
        kidneyObj = dataInst.find_obj_by_key(key)
        if kidneyObj is None :
            return
        
        exoInx = self.getui_exo_index()
        key = data.CData.make_key(CTabStateKidneySepTest.s_exoKeyType, 0, exoInx)
        exoObj = dataInst.find_obj_by_key(key)
        if exoObj is None :
            return 
        
        self._polydata_dilation(exoObj, 0.2)
        
        kidneyPolyData = kidneyObj.PolyData
        exoPolyData = exoObj.PolyData

        npVertex = algVTK.CVTK.poly_data_get_vertex(kidneyPolyData)
        npIndex = algVTK.CVTK.poly_data_get_triangle_index(kidneyPolyData)
        meshLibKidney = algMeshLib.CMeshLib.meshlib_create(npVertex, npIndex)
        meshLibKidney = algMeshLib.CMeshLib.meshlib_healing(meshLibKidney)

        npVertex = algVTK.CVTK.poly_data_get_vertex(exoPolyData)
        npIndex = algVTK.CVTK.poly_data_get_triangle_index(exoPolyData)
        meshLibExo = algMeshLib.CMeshLib.meshlib_create(npVertex, npIndex)
        meshLibExo = algMeshLib.CMeshLib.meshlib_healing(meshLibExo)

        retMesh = algMeshLib.CMeshLib.meshlib_boolean_subtraction(meshLibKidney, meshLibExo)
        npVertex = algMeshLib.CMeshLib.meshlib_get_vertex(retMesh)
        npIndex = algMeshLib.CMeshLib.meshlib_get_index(retMesh)
        vtkMesh = algVTK.CVTK.create_poly_data_triangle(npVertex, npIndex)

        # rendering 
        key = data.CData.make_key(CTabStateKidneySepTest.s_sepKeyType, 0 ,0)
        sepObj = vtkObjInterface.CVTKObjInterface()
        sepObj.KeyType = CTabStateKidneySepTest.s_sepKeyType
        sepObj.Key = key
        sepObj.Color = algLinearMath.CScoMath.to_vec3([0.53, 0.81, 0.92])
        sepObj.Opacity = 0.6
        sepObj.PolyData = vtkMesh
        dataInst.add_vtk_obj(sepObj)
        self._remove_noise(sepObj)
        self.m_mediator.ref_key(key)

        savePath = dataInst.get_terri_out_path()
        savePath = os.path.join(savePath, "sep.stl")
        polyData = sepObj.PolyData
        algVTK.CVTK.save_poly_data_stl(savePath, polyData)

        self.m_mediator.update_viewer()
    def _on_check_visible_kidney_tumor(self, state) :
        self._refresh_visible_kidney_tumor()
        

if __name__ == '__main__' :
    pass


# print ("ok ..")

