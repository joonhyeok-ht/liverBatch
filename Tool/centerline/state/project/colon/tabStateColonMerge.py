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

import command.commandTerritory as commandTerritory


class CTabStateColonMerge(tabState.CTabState) : 
    s_vertexKeyType = "vertex"
    s_knifeKeyType = "knife"
    s_colonKeyType = "colon"

    s_pickingDepth = 1000.0
    s_minDragDist = 10

    s_ctColor = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 1.0])
    s_mrColor = algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0])


    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_opSelectionCL = operation.COperationSelectionCL(mediator)

        self.m_startMx = -1
        self.m_startMy = -1
        self.m_endMx = -1
        self.m_endMy = -1
        self.m_bActiveKnife = False

        self.m_targetVertex = None
        self.m_srcVertex = None
        self.m_ctVertex = None
        self.m_mrVertex = None

        self.m_knifeKey = ""
    def clear(self) :
        # input your code
        self.m_startMx = -1
        self.m_startMy = -1
        self.m_endMx = -1
        self.m_endMy = -1
        self.m_bActiveKnife = False

        self.m_targetVertex = None
        self.m_srcVertex = None
        self.m_ctVertex = None
        self.m_mrVertex = None

        self.m_knifeKey = ""
        self.m_tangent = None

        super().clear()

    def process_init(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        userData = self._get_userdata()
        if userData is None :
            return
        if userData.MergeTargetInx == -1 :
            return
        if userData.MergeSrcInx == -1 :
            return
        
        # 이 부분은 수정이 필요해 보임.. 다른 상태에서 ref 된 것은 그 상태에서 unref 시켜야 된다. 
        self.m_mediator.unref_key_type(data.CData.s_skelTypeCenterline)
        self.m_mediator.unref_key_type(data.CData.s_vesselType)

        self._command_changed_merge_mesh()

        self.m_startMx = -1
        self.m_startMy = -1
        self.m_endMx = -1
        self.m_endMy = -1
        self.m_bActiveKnife = False

        self.m_knifeKey = ""
        self.m_tangent = None
        
        self.m_mediator.update_viewer()
    def process(self) :
        pass
    def process_end(self) :
        self.m_opSelectionCL.process_reset()

        self.m_mediator.unref_key_type(data.CData.s_skelTypeCenterline)
        self.m_mediator.unref_key_type(data.CData.s_vesselType)
        self.m_mediator.remove_key_type(CTabStateColonMerge.s_vertexKeyType)
        self.m_mediator.remove_key_type(CTabStateColonMerge.s_colonKeyType)
        self.m_mediator.remove_key_type(CTabStateColonMerge.s_knifeKeyType)

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
        dataInst = self.get_data()
        userData = self._get_userdata()

        self.m_startMx = clickX
        self.m_startMy = clickY
        self.m_endMx = clickX
        self.m_endMy = clickY
        self.m_bActiveKnife = True
        self.m_mediator.remove_key_type(CTabStateColonMerge.s_colonKeyType)
        self.m_mediator.remove_key_type(CTabStateColonMerge.s_knifeKeyType)
        vesselKey = data.CData.make_key(data.CData.s_vesselType, userData.MergeTargetInx, 0)
        self.m_mediator.ref_key(vesselKey)
        vesselKey = data.CData.make_key(data.CData.s_vesselType, userData.MergeSrcInx, 0)
        self.m_mediator.ref_key(vesselKey)

        worldStart, pNearStart, pFarStart= self.m_mediator.get_world_from_mouse(self.m_startMx, self.m_startMy, CTabStateColonMerge.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.m_mediator.get_world_from_mouse(self.m_endMx, self.m_endMy, CTabStateColonMerge.s_pickingDepth)

        self.m_knifeKey = data.CData.make_key(CTabStateColonMerge.s_knifeKeyType, 0, 0)
        inst = vtkObjLine.CVTKObjLine()
        inst.KeyType = CTabStateColonMerge.s_knifeKeyType
        inst.Key = self.m_knifeKey
        inst.set_line_width(2.0)
        inst.set_pos(pFarStart, pFarEnd)
        # inst.set_pos(pNearStart, pNearEnd)
        inst.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        dataInst.add_vtk_obj(inst)

        self.m_mediator.ref_key_type(CTabStateColonMerge.s_knifeKeyType)
        self.m_tangent = None
    
        self.m_mediator.update_viewer()
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        self.m_mediator.update_viewer()
    def release_mouse_rb(self) :
        if self.m_bActiveKnife == False :
            return
        
        self.m_mediator.remove_key_type(CTabStateColonMerge.s_knifeKeyType)

        # drag 영역이 너무 작을 경우 무시
        dx = self.m_endMx - self.m_startMx
        dy = self.m_endMy - self.m_startMy
        dist = math.hypot(dx, dy)
        if dist < CTabStateColonMerge.s_minDragDist :
            return
        
        # input algorithm code 
        self._command_knife(self.m_startMx, self.m_startMy, self.m_endMx, self.m_endMy)

        self.m_bActiveKnife = False
        self.m_mediator.update_viewer()
    def mouse_move_rb(self, clickX, clickY) :
        if self.m_bActiveKnife == False :
            return
        
        dataInst = self.get_data()
        
        self.m_endMx = clickX
        self.m_endMy = clickY
        worldStart, pNearStart, pFarStart = self.m_mediator.get_world_from_mouse(self.m_startMx, self.m_startMy, CTabStateColonMerge.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.m_mediator.get_world_from_mouse(self.m_endMx, self.m_endMy, CTabStateColonMerge.s_pickingDepth)

        inst = dataInst.find_obj_by_key(self.m_knifeKey)
        # inst.set_pos(pNearStart, pNearEnd)
        inst.set_pos(pFarStart, pFarEnd)
        self.m_mediator.update_viewer()
    def key_press(self, keyCode : str) :
        if keyCode == "Escape" :
            userData = self._get_userdata()
            self.m_startMx = -1
            self.m_startMy = -1
            self.m_endMx = -1
            self.m_endMy = -1
            self.m_bActiveKnife = False
            self.m_mediator.remove_key_type(CTabStateColonMerge.s_colonKeyType)
            self.m_mediator.remove_key_type(CTabStateColonMerge.s_knifeKeyType)
            vesselKey = data.CData.make_key(data.CData.s_vesselType, userData.MergeTargetInx, 0)
            self.m_mediator.ref_key(vesselKey)
            vesselKey = data.CData.make_key(data.CData.s_vesselType, userData.MergeSrcInx, 0)
            self.m_mediator.ref_key(vesselKey)
            self.m_mediator.update_viewer()

    # protected
    def _get_userdata(self) -> userDataColon.CUserDataColon :
        return self.get_data().find_userdata(userDataColon.CUserDataColon.s_userDataKey)
    
    def _command_changed_merge_mesh(self) :
        dataInst = self.get_data()
        userData = self._get_userdata()

        targetInx = userData.MergeTargetInx
        srcInx = userData.MergeSrcInx

        if targetInx == -1 or srcInx == -1 :
            return
        if targetInx == srcInx :
            print("invalidate setting target and src")
            return
        
        self.m_mediator.unref_key_type(data.CData.s_vesselType)
        self.m_mediator.unref_key_type(data.CData.s_skelTypeCenterline)
        self.m_mediator.remove_key_type(CTabStateColonMerge.s_vertexKeyType)
        self._command_changed_target()
        self._command_changed_src()
    def _command_changed_target(self) :
        dataInst = self.get_data()
        userData = self._get_userdata()

        self.m_targetVertex = userData.get_mergeinfo_vertex(userData.MergeTargetInx)
        mat = userData.get_mergeinfo_physical_mat(userData.MergeTargetInx)
        self.m_ctVertex = algLinearMath.CScoMath.mul_mat4_vec3(mat, self.m_targetVertex)

        vesselKey = data.CData.make_key(data.CData.s_vesselType, userData.MergeTargetInx, 0)
        self.m_mediator.ref_key(vesselKey)
        self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeCenterline, userData.MergeTargetInx)
        obj = dataInst.find_obj_by_key(vesselKey)
        obj.Color = CTabStateColonMerge.s_ctColor

        vertexKey = data.CData.make_key(CTabStateColonMerge.s_vertexKeyType, 0, userData.MergeTargetInx)
        obj = vtkObjVertex.CVTKObjVertex(self.m_ctVertex, 1.0)
        obj.KeyType = CTabStateColonMerge.s_vertexKeyType
        obj.Key = vertexKey
        obj.Color = CTabStateColonMerge.s_ctColor
        dataInst.add_vtk_obj(obj)
        self.m_mediator.ref_key(vertexKey)
    def _command_changed_src(self) :
        dataInst = self.get_data()
        userData = self._get_userdata()

        self.m_srcVertex = userData.get_mergeinfo_resampling_vertex(userData.MergeTargetInx, userData.MergeSrcInx)
        mat = userData.get_mergeinfo_physical_mat(userData.MergeTargetInx)
        self.m_mrVertex = algLinearMath.CScoMath.mul_mat4_vec3(mat, self.m_srcVertex)

        vesselKey = data.CData.make_key(data.CData.s_vesselType, userData.MergeSrcInx, 0)
        self.m_mediator.ref_key(vesselKey)
        self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeCenterline, userData.MergeSrcInx)
        obj = dataInst.find_obj_by_key(vesselKey)
        obj.Color = CTabStateColonMerge.s_mrColor

        vertexKey = data.CData.make_key(CTabStateColonMerge.s_vertexKeyType, 0, userData.MergeSrcInx)
        obj = vtkObjVertex.CVTKObjVertex(self.m_mrVertex, 1.0)
        obj.KeyType = CTabStateColonMerge.s_vertexKeyType
        obj.Key = vertexKey
        obj.Color = CTabStateColonMerge.s_mrColor
        dataInst.add_vtk_obj(obj)
        self.m_mediator.ref_key(vertexKey)
    def _command_knife(self, startMx, startMy, endMx, endMy) :
        dataInst = self.get_data()

        worldStart, pNearStart, pFarStart = self.m_mediator.get_world_from_mouse(startMx, startMy, CTabStateColonMerge.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.m_mediator.get_world_from_mouse(endMx, endMy, CTabStateColonMerge.s_pickingDepth)
        cameraInfo = self.m_mediator.get_active_camerainfo()
        cameraPos = cameraInfo[3]

        a = worldStart
        b = worldEnd
        c = cameraPos

        plane = algLinearMath.CScoMath.create_plane(a, b, c)
        abc = plane[ : 3]
        d = plane[3]
        sign = algLinearMath.CScoMath.dot_vec3(abc.reshape(-1, 3), algLinearMath.CScoMath.to_vec3([0.0, 0.0, 1.0]))

        dist = np.dot(self.m_ctVertex, abc) + d
        ctValidInx = None
        if sign >= 0 :
            ctValidInx = np.where(dist >= 0)[0]
        else :
            ctValidInx = np.where(dist < 0)[0]
        
        dist = np.dot(self.m_mrVertex, abc) + d
        mrValidInx = None
        if sign >= 0 :
            mrValidInx = np.where(dist >= 0)[0]
        else :
            mrValidInx = np.where(dist < 0)[0]

        userData = self._get_userdata()
        targetInx = userData.MergeTargetInx
        if targetInx == -1 :
            return
        
        tmpImg = userData.get_mergeinfo_npimg(targetInx)

        # ct segment
        vertex = self.m_targetVertex[ctValidInx]
        seedInx = np.argmax(vertex[ : , 1])
        seedV = vertex[seedInx].reshape(-1, 3)
        ctVertex = self.__find_segment_vertex(tmpImg, vertex, seedV)

        # mr segment
        vertex = self.m_srcVertex[mrValidInx]
        seedInx = np.argmax(vertex[ : , 1])
        seedV = vertex[seedInx].reshape(-1, 3)
        mrVertex = self.__find_segment_vertex(tmpImg, vertex, seedV)

        # recon 
        retColonPolyData = self.__recon_merged_colon(tmpImg, ctVertex, mrVertex)
        
        
        vesselKey = data.CData.make_key(data.CData.s_vesselType, userData.MergeTargetInx, 0)
        self.m_mediator.unref_key(vesselKey)
        vesselKey = data.CData.make_key(data.CData.s_vesselType, userData.MergeSrcInx, 0)
        self.m_mediator.unref_key(vesselKey)
        
        key = data.CData.make_key(CTabStateColonMerge.s_colonKeyType, 0, 0)
        obj = vtkObjInterface.CVTKObjInterface()
        obj.KeyType = data.CData.s_territoryType
        obj.Key = key
        obj.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        obj.Opacity = 0.5
        obj.PolyData = retColonPolyData
        dataInst.add_vtk_obj(obj)
        self.m_mediator.ref_key(key)

    
    # ui event 
    def _on_btn_review_colon_test(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        userData = self._get_userdata()
        if userData is None :
            return
        if userData.MergeTargetInx == -1 :
            return
        if userData.MergeSrcInx == -1 :
            return
        
        # savePath, _ = QFileDialog.getSaveFileName(
        #     self.get_main_widget(),
        #     "Save Mesh File", 
        #     "", 
        #     "STL Files (*.stl)"
        # )
        # if savePath == "" :
        #     return

        mergeColonName = "colonMerge"
        mergeColonFileName = f"{mergeColonName}.stl"

        if os.path.exists(userData.get_merge_in_path()) == False :
            os.makedirs(userData.get_merge_in_path())
        if os.path.exists(userData.get_merge_out_path()) == False :
            os.makedirs(userData.get_merge_out_path())
        
        key = data.CData.make_key(CTabStateColonMerge.s_colonKeyType, 0, 0)
        obj = dataInst.find_obj_by_key(key)
        if obj is None :
            print("not found merged colon")
            return
        polyData = obj.PolyData

        savePath = os.path.join(userData.get_merge_out_path(), f"{mergeColonFileName}")
        algVTK.CVTK.save_poly_data_stl(savePath, polyData)

        savePath = os.path.join(dataInst.get_cl_in_path(), f"{mergeColonFileName}")
        algVTK.CVTK.save_poly_data_stl(savePath, polyData)
        print("vessel file saved successfully.")

        if userData.MergeClinfoInx >= dataInst.DataInfo.get_info_count() :
            clInfo = copy.deepcopy(dataInst.OptionInfo.get_centerlineinfo(userData.MergeTargetInx))
            clParam = dataInst.OptionInfo.find_centerline_param(clInfo.CenterlineType)
            reconType = clInfo.get_input_recon_type()
            reconParam = dataInst.OptionInfo.find_recon_param(reconType)

            clInfo.InputKey = "blenderName"
            clInfo.Input["blenderName"] = mergeColonName
            clInfo.OutputName = mergeColonName

            dataInst.DataInfo.add_info(clInfo, clParam, reconParam)
            dataInst.attach_skeleton()

        mergeGroupInx = userData.MergeClinfoInx
        vesselKey = dataInst.make_key(data.CData.s_vesselType, mergeGroupInx, 0)
        self.m_mediator.remove_key(vesselKey)
        self.m_mediator.remove_key_type_groupID(data.CData.s_skelTypeCenterline, mergeGroupInx)
        self.m_mediator.remove_key_type_groupID(data.CData.s_skelTypeBranch, mergeGroupInx)
        self.m_mediator.remove_key_type_groupID(data.CData.s_skelTypeEndPoint, mergeGroupInx)
        self.m_mediator.load_vessel_key(mergeGroupInx, 0)


    # private
    def __find_segment_vertex(self, npImg : np.ndarray, npVertex : np.ndarray, seedVertex : np.ndarray) -> np.ndarray :
        structure = generate_binary_structure(3, 3)

        algImage.CAlgImage.set_clear(npImg, 0)
        seed = tuple(seedVertex.reshape(-1).astype(int))
        algImage.CAlgImage.set_value(npImg, npVertex, 255)

        labeled, numFeatures = label(npImg, structure=structure)
        seedLabel = labeled[seed]
        segVertex = np.argwhere(labeled == seedLabel)

        return segVertex
    def __recon_merged_colon(self, npImg : np.ndarray, ctVertex : np.ndarray, mrVertex : np.ndarray) -> vtk.vtkPolyData :
        userData = self._get_userdata()

        algImage.CAlgImage.set_clear(npImg, 0)
        algImage.CAlgImage.set_value(npImg, self.m_targetVertex, 255)
        algImage.CAlgImage.set_value(npImg, ctVertex, 0)
        algImage.CAlgImage.set_value(npImg, mrVertex, 255)

        reconParam = userData.get_mergeinfo_reconparam(userData.MergeTargetInx)
        contour = reconParam.Contour
        algorithm = reconParam.Algorithm
        param = reconParam.Param
        gaussian = reconParam.Gaussian
        resampling = reconParam.ResamplingFactor

        phaseInfo = userData.get_mergeinfo_phaseinfo(userData.MergeTargetInx)
        origin = phaseInfo.Origin
        spacing = phaseInfo.Spacing
        direction = phaseInfo.Direction
        phaseOffset = phaseInfo.Offset

        niftiPath = "colonTmp.nii.gz"
        algImage.CAlgImage.save_nifti_from_np(niftiPath, npImg, origin, spacing, direction, (2, 1, 0))

        retColonPolyData = reconstruction.CReconstruction.reconstruction_nifti(
            niftiPath, 
            origin, spacing, direction, phaseOffset,
            contour, param, algorithm, gaussian, resampling
            )
        
        if os.path.exists(niftiPath) == True :
            os.remove(niftiPath)
        
        return retColonPolyData
        

if __name__ == '__main__' :
    pass


# print ("ok ..")

