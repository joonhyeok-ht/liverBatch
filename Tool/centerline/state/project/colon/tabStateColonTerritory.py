import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

from scipy.spatial import KDTree

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

import VtkObj.vtkObjVertex as vtkObjVertex
import vtkObjSTL as vtkObjSTL
import vtkObjInterface as vtkObjInterface
import vtkObjGuideMeshBound as vtkObjGuideMeshBound

import command.commandTerritory as commandTerritory


class CTabStateColonTerritory(tabState.CTabState) :
    s_guideBoundType = "guideBound"


    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_opSelectionCL = operation.COperationSelectionCL(mediator)
        self.m_guideBoundKey = ""
    def clear(self) :
        # input your code
        self.m_guideBoundKey = ""
        super().clear()

    def process_init(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        userData = self._get_userdata()
        if userData is None :
            return
        if userData.ArteryCLInfoInx == -1 :
            return
        if userData.ColonCLInfoInx == -1 :
            return
        
        self.m_mediator.unref_key_type(data.CData.s_skelTypeCenterline)
        self.m_mediator.unref_key_type(data.CData.s_vesselType)

        iCnt = dataInst.get_skeleton_count()
        for inx in range(0, iCnt) :
            self.m_mediator.ref_key_type(data.CData.s_vesselType)
            self.m_mediator.ref_key_type(data.CData.s_skelTypeCenterline)
        
        skeleton = dataInst.get_skeleton(userData.ArteryCLInfoInx)
        self.m_opSelectionCL.Skeleton = skeleton
        self.m_opSelectionCL.ChildSelectionMode = True
        self.m_opSelectionCL.ParentSelectionMode = False
        
        self.m_mediator.update_viewer()
    def process(self) :
        pass
    def process_end(self) :
        self.m_opSelectionCL.process_reset()

        self.m_mediator.remove_key_type(data.CData.s_territoryType)
        self.m_mediator.remove_key_type(CTabStateColonTerritory.s_guideBoundType)
        self.m_mediator.unref_key_type(data.CData.s_skelTypeCenterline)
        self.m_mediator.unref_key_type(data.CData.s_vesselType)

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
        listExceptKeyType = [
            data.CData.s_vesselType,
        ]

        key = self.m_mediator.picking(clickX, clickY, listExceptKeyType)
        if key == "" or data.CData.get_type_from_key(key) != data.CData.s_skelTypeCenterline :
            key = ""

        operation.COperationSelectionCL.clicked(self.m_opSelectionCL, key)
        self.m_mediator.update_viewer()
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        listExceptKeyType = [
            data.CData.s_vesselType,
        ]

        key = self.m_mediator.picking(clickX, clickY, listExceptKeyType)
        if key == "" or data.CData.get_type_from_key(key) != data.CData.s_skelTypeCenterline :
            key = ""

        operation.COperationSelectionCL.multi_clicked(self.m_opSelectionCL, key)
        self.m_mediator.update_viewer()
    def key_press(self, keyCode : str) :
        if keyCode == "Escape" :
            self.m_mediator.remove_key_type(CTabStateColonTerritory.s_guideBoundType)
            self.m_mediator.remove_key_type(data.CData.s_territoryType)
            self.m_opSelectionCL.process_reset()
            self.m_mediator.update_viewer()
            # if self.m_guideBoundKey != "" :
            #     self.m_mediator.remove_key(self.m_guideBoundKey)
            #     self.m_mediator.remove_key_type(data.CData.s_territoryType)
            #     self.m_guideBoundKey = ""
            #     self.m_mediator.update_viewer()


    # protected
    def _get_userdata(self) -> userDataColon.CUserDataColon :
        return self.get_data().find_userdata(userDataColon.CUserDataColon.s_userDataKey)
    
    # ui event 
    def _on_btn_review_colon_test(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        userData = self._get_userdata()
        if userData is None :
            return
        if userData.ArteryCLInfoInx == -1 :
            return
        if userData.ColonCLInfoInx == -1 :
            return
        
        vesselKey = data.CData.make_key(data.CData.s_vesselType, userData.ColonCLInfoInx, 0)
        vesselObj = dataInst.find_obj_by_key(vesselKey) 
        if vesselObj is None :
            return
        
        if self.m_guideBoundKey != "" :
            self.m_mediator.remove_key_type(CTabStateColonTerritory.s_guideBoundType)
            self.m_mediator.remove_key_type(data.CData.s_territoryType)

        listSelectionCL = self.m_opSelectionCL.get_all_selection_cl()
        if listSelectionCL is None :
            return
        
        skeleton = dataInst.get_skeleton(userData.ArteryCLInfoInx)
        colonSkeleton = dataInst.get_skeleton(userData.ColonCLInfoInx)

        # selection 중 end-point만 추출 
        queryVertex = None
        for clID in listSelectionCL :
            cl = skeleton.get_centerline(clID)
            if cl.is_leaf() == True :
                if queryVertex is None :
                    queryVertex = cl.get_end_point().copy()
                else :
                    queryVertex = np.concatenate((queryVertex, cl.get_end_point()), axis=0)
        
        if queryVertex.shape[0] < 2 :
            print("invalid queryVertex count") 
            return
        
        kdtree = KDTree(colonSkeleton.get_centerline(0).Vertex)
        # 가장 가까운 vertex 찾기 (임의의 vertex와 곡선 vertex들 사이)
        distance, querySegInx = kdtree.query(queryVertex)
        minInx = np.min(querySegInx)
        maxInx = np.max(querySegInx)

        # 0 ~ 0.25 까지만 허용 
        cl = colonSkeleton.get_centerline(0)

        margin = 22.0
        minV = algLinearMath.CScoMath.get_min_vec3(cl.Vertex[minInx : maxInx + 1])
        maxV = algLinearMath.CScoMath.get_max_vec3(cl.Vertex[minInx : maxInx + 1])
        minV -= margin
        maxV += margin

        vesselPolyData = vesselObj.PolyData
        guideObj = vtkObjGuideMeshBound.CVTKObjGuideMeshBound(vesselPolyData, margin, minV, maxV)
        guideObj.KeyType = CTabStateColonTerritory.s_guideBoundType
        guideObj.Key = data.CData.make_key(guideObj.KeyType, 0, 0)
        guideObj.Color = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 0.0])
        guideObj.Opacity = 0.3
        self.m_guideBoundKey = guideObj.Key
        # dataInst.add_vtk_obj(guideObj)
        # self.m_mediator.ref_key(guideObj.Key)

        wholeVertex = cl.Vertex[0 : minInx]
        if maxInx + 1 < cl.Vertex.shape[0] :
            wholeVertex = np.concatenate((wholeVertex, cl.Vertex[maxInx + 1 : -1]), axis=0)

        cmd = commandTerritory.CCommandTerritoryDefault(self.m_mediator)
        cmd.InputData = self.get_data()
        # cmd.InputWholeVertex = cl.Vertex[0 : minInx]
        cmd.InputWholeVertex = wholeVertex
        cmd.InputSubVertex = cl.Vertex[minInx : maxInx + 1]
        cmd.InputPolyData = guideObj.PolyData
        cmd.InputVoxelizeSpacing = (1.0, 1.0, 1.0)
        cmd.process()

        
        # segVertex = cl.Vertex[indices]

        # key = data.CData.make_key(data.CData.s_territoryType, 0 ,0)
        # segCLObj = vtkObjVertex.CVTKObjVertex(segVertex, 8.0)
        # segCLObj.KeyType = data.CData.s_territoryType
        # segCLObj.Key = key
        # segCLObj.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        # dataInst.add_vtk_obj(segCLObj)
        # self.m_mediator.ref_key(key)
        

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

        
        # key = data.CData.make_key(data.CData.s_territoryType, 0 ,0)
        # terriObj = vtkObjInterface.CVTKObjInterface()
        # terriObj.KeyType = data.CData.s_territoryType
        # terriObj.Key = key
        # terriObj.Color = algLinearMath.CScoMath.to_vec3([0.53, 0.81, 0.92])
        # terriObj.Opacity = 0.3
        # terriObj.PolyData = terriPolyData
        # dataInst.add_vtk_obj(terriObj)
        # self.m_mediator.ref_key(key)

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
        

if __name__ == '__main__' :
    pass


# print ("ok ..")

