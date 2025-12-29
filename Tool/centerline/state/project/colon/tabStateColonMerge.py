import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import math
import copy

from scipy.spatial import KDTree
from scipy.ndimage import label, generate_binary_structure

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

import state.project.colon.userDataColon as userDataColon

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algMeshLib as algMeshLib
import AlgUtil.algVTK as algVTK
import AlgUtil.algImage as algImage

import Block.reconstruction as reconstruction

import VtkObj.vtkObjVertex as vtkObjVertex
import VtkObj.vtkObjLine as vtkObjLine
import vtkObjSTL as vtkObjSTL
import vtkObjInterface as vtkObjInterface
import vtkObjGuideMeshBound as vtkObjGuideMeshBound

import componentColonMerge as componentColonMerge


class CTabStateColonMerge(tabState.CTabState) : 
    s_mergedColonType = "mergedColon"
    s_pickingDepth = 1000.0
    s_minDragDist = 10

    @staticmethod
    def get_meshlib(vtkMeshInst : vtk.vtkPolyData) :
        npVertex = algVTK.CVTK.poly_data_get_vertex(vtkMeshInst)
        npIndex = algVTK.CVTK.poly_data_get_triangle_index(vtkMeshInst)
        meshLibInst = algMeshLib.CMeshLib.meshlib_create(npVertex, npIndex)
        return meshLibInst
    @staticmethod
    def get_vtkmesh(meshlibInst) -> vtk.vtkPolyData :
        npVertex = algMeshLib.CMeshLib.meshlib_get_vertex(meshlibInst)
        npIndex = algMeshLib.CMeshLib.meshlib_get_index(meshlibInst)
        vtkMesh = algVTK.CVTK.create_poly_data_triangle(npVertex, npIndex)
        return vtkMesh


    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_opSelectionCL = operation.COperationSelectionCL(mediator)
        self.m_comColonMerge = None
    def clear(self) :
        # input your code
        if self.m_comColonMerge is not None :
            self.m_comColonMerge.clear()

        super().clear()

    def process_init(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        userData = self._get_userdata()
        if userData is None :
            return
        if userData.get_mergeinfo_res_count() != 2 :
            return
        if userData.DummyObjInfo is None :
            return
        
        # 이 부분은 수정이 필요해 보임.. 다른 상태에서 ref 된 것은 그 상태에서 unref 시켜야 된다. 
        self.m_mediator.unref_key_type(data.CData.s_skelTypeCenterline)
        self.m_mediator.unref_key_type(data.CData.s_vesselType)

        mergeInfo = userData.get_mergeinfo()

        ctColonRes = userData.get_mergeinfo_res(0)
        ctColonKey = ctColonRes.ColonKey
        if ctColonKey != "" :
            self.m_mediator.ref_key(ctColonKey)
        mrColonRes = userData.get_mergeinfo_res(1)
        mrColonKey = mrColonRes.ColonKey
        if mrColonKey != "" :
            self.m_mediator.ref_key(mrColonKey)
        self.m_mediator.ref_key_type(userDataColon.CUserDataColon.s_colonMaskType)

        clinfoinx = mergeInfo.ClinfoInx
        self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeCenterline, clinfoinx)

        self.m_comColonMerge = componentColonMerge.CComColonMerge(self)
        self.m_comColonMerge.signal_finished_knife = self.slot_finished_knife
        self.m_comColonMerge.process_init()
        self.m_comColonMerge.m_refMesh = dataInst.find_obj_by_key(ctColonKey).PolyData # test 
        
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
        if userData.get_mergeinfo_res_count() != 2 :
            return
        if userData.DummyObjInfo is None :
            return
        
        self._attach_merged_colon()
        
        if self.m_comColonMerge is not None :
            self.m_comColonMerge.process_end()
            self.m_comColonMerge = None
        
        self.m_opSelectionCL.process_reset()

        ctColonRes = userData.get_mergeinfo_res(0)
        ctColonKey = ctColonRes.ColonKey
        if ctColonKey != "" :
            self.m_mediator.unref_key(ctColonKey)
        
        mrColonRes = userData.get_mergeinfo_res(1)
        mrColonKey = mrColonRes.ColonKey
        if mrColonKey != "" :
            self.m_mediator.unref_key(mrColonKey)

        self.m_mediator.unref_key_type(data.CData.s_skelTypeCenterline)
        self.m_mediator.unref_key_type(userDataColon.CUserDataColon.s_colonMaskType)
        self.m_mediator.remove_key_type(CTabStateColonMerge.s_mergedColonType)

        # 원복 
        clinfoInx = self.get_clinfo_index()
        self.m_mediator.ref_key_type_groupID(data.CData.s_vesselType, clinfoInx)
        self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeCenterline, clinfoInx)

        self.m_mediator.update_viewer()

    def init_ui(self) :
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        label = QLabel("-- Colon Territory Test --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        btn = QPushButton("Review Colon Test")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_review_colon_test)
        tabLayout.addWidget(btn)


        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        lastUI = line
        tabLayout.setAlignment(lastUI, Qt.AlignmentFlag.AlignTop)


    def clicked_mouse_rb(self, clickX, clickY) :
        if self.m_comColonMerge is None :
            return
        self.m_comColonMerge.click(clickX, clickY)
        self.m_mediator.update_viewer()
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        if self.m_comColonMerge is None :
            return
        self.m_comColonMerge.click_with_shift(clickX, clickY)
        self.m_mediator.update_viewer()
    def release_mouse_rb(self) :
        if self.m_comColonMerge is None :
            return
        self.m_comColonMerge.release(0, 0)
        self.m_mediator.update_viewer()
    def mouse_move_rb(self, clickX, clickY) :
        if self.m_comColonMerge is None :
            return
        self.m_comColonMerge.move(clickX, clickY)
        
        self.m_mediator.update_viewer()
    def key_press(self, keyCode : str) :
        if keyCode == "Escape" :
            self.m_mediator.remove_key_type(CTabStateColonMerge.s_mergedColonType)
            self.m_mediator.update_viewer()

    # protected
    def _get_userdata(self) -> userDataColon.CUserDataColon :
        return self.get_data().find_userdata(userDataColon.CUserDataColon.s_userDataKey)
    def _attach_merged_colon(self) :
        dataInst = self.get_data()
        userdata = self._get_userdata()

        key = data.CData.make_key(CTabStateColonMerge.s_mergedColonType, 0, 0)
        obj = dataInst.find_obj_by_key(key)
        if obj is None :
            return
        mergedColonMesh = obj.PolyData

        mergeInfo = userdata.get_mergeinfo()
        mergeColonName = mergeInfo.MergeBlenderName
        mergeColonFileName = f"{mergeColonName}.stl"

        meshlibRet = CTabStateColonMerge.get_meshlib(mergedColonMesh)
        meshlibRet = algMeshLib.CMeshLib.meshlib_healing(meshlibRet)
        decimation = mergeInfo.Decimation
        if decimation != -1 :
            meshlibRet = algMeshLib.CMeshLib.meshlib_decimation(meshlibRet, decimation)
        mergedColonMesh = CTabStateColonMerge.get_vtkmesh(meshlibRet)
            

        savePath = os.path.join(userdata.get_merge_out_path(), f"{mergeColonFileName}")
        algVTK.CVTK.save_poly_data_stl(savePath, mergedColonMesh)

        savePath = os.path.join(dataInst.get_cl_in_path(), f"{mergeColonFileName}")
        algVTK.CVTK.save_poly_data_stl(savePath, mergedColonMesh)
        print("vessel file saved successfully.")

        if userdata.MergeCLInfoInx >= dataInst.DataInfo.get_info_count() :
            clInfo = copy.deepcopy(mergeInfo.Clinfo)
            clParam = dataInst.OptionInfo.find_centerline_param(clInfo.CenterlineType)
            reconType = clInfo.get_input_recon_type()
            reconParam = dataInst.OptionInfo.find_recon_param(reconType)

            clInfo.InputKey = "blenderName"
            clInfo.Input["blenderName"] = mergeColonName
            clInfo.OutputName = mergeColonName

            dataInst.DataInfo.add_info(clInfo, clParam, reconParam)
            dataInst.attach_skeleton()
        
        mergeGroupInx = userdata.MergeCLInfoInx
        vesselKey = dataInst.make_key(data.CData.s_vesselType, mergeGroupInx, 0)
        self.m_mediator.remove_key(vesselKey)
        self.m_mediator.remove_key_type_groupID(data.CData.s_skelTypeCenterline, mergeGroupInx)
        self.m_mediator.remove_key_type_groupID(data.CData.s_skelTypeBranch, mergeGroupInx)
        self.m_mediator.remove_key_type_groupID(data.CData.s_skelTypeEndPoint, mergeGroupInx)
        self.m_mediator.load_vessel_key(mergeGroupInx, 0)

    
    # ui event 
    def _on_btn_review_colon_test(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        userData = self._get_userdata()
        if userData is None :
            return

    # private
    


    # slot
    def slot_finished_knife(self, clID : int, vertexIndex : int, tangent : np.ndarray, intersectedPt : np.ndarray, mergedPolydata : vtk.vtkPolyData) :
        print(f"clID : {clID}")
        print(f"vertexIndex : {vertexIndex}")
        print(f"tangent : {tangent}")
        print(f"intersectedPt : {intersectedPt}")

        dataInst = self.get_data()
        self.m_mediator.remove_key_type(CTabStateColonMerge.s_mergedColonType)

        colonKey = data.CData.make_key(CTabStateColonMerge.s_mergedColonType, 0, 0)
        obj = vtkObjInterface.CVTKObjInterface()
        obj.KeyType = CTabStateColonMerge.s_mergedColonType
        obj.Key = colonKey
        obj.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        obj.Opacity = 0.7
        obj.PolyData = mergedPolydata
        dataInst.add_vtk_obj(obj)
        self.m_mediator.ref_key(colonKey)


        

if __name__ == '__main__' :
    pass


# print ("ok ..")

