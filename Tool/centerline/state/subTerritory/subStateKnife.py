import sys
import os
import numpy as np
import shutil
import time
import vtk
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileStatePath = os.path.dirname(fileAbsPath)
fileAppPath = os.path.dirname(fileStatePath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileStatePath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import data as data
import clMask as clMask

import operation as operation

import tabState as tabState

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algMeshLib as algMeshLib
import AlgUtil.algVTK as algVTK
import AlgUtil.algSkeletonGraph as algSkeletonGraph

import VtkObj.vtkObjLine as vtkObjLine
import vtkObjSTL as vtkObjSTL
import vtkObjInterface as vtkObjInterface
import vtkObjGuideCLBound as vtkObjGuideCLBound

import command.commandTerritory as commandTerritory
import command.commandTerritoryVessel as commandTerritoryVessel



class CSubStateKnife() :
    s_terriOrganColor = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 0.6])
    s_terriVesselColor = algLinearMath.CScoMath.to_vec3([0.5, 0.0, 0.5])
    

    def __init__(self, mediator):
        # input your code
        self.m_mediator = mediator
    def clear(self) :
        # input your code
        self.m_mediator = None

    def process_init(self) :
        pass
    def process(self) :
        pass
    def process_end(self) :
        pass

    def clicked_mouse_rb(self, clickX, clickY) :
        pass
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        listExceptKeyType = [
            data.CData.s_territoryType,
            data.CData.s_vesselType,
            data.CData.s_organType,
        ]
        key = self.App.picking(clickX, clickY, listExceptKeyType)
        if key == "" or data.CData.get_type_from_key(key) != data.CData.s_skelTypeCenterline :
            key = ""

        opSelectionCL = self._get_operator_selection_cl()

        self._set_whole_vessel(None)
        self.App.remove_key_type(data.CData.s_territoryType)
        operation.COperationSelectionCL.multi_clicked(opSelectionCL, key)
    def release_mouse_rb(self) :
        pass
    def mouse_move(self, clickX, clickY) :
        pass
    def mouse_move_rb(self, clickX, clickY) :
        pass
    def key_press(self, keyCode : str) :
        pass
    def key_press_with_ctrl(self, keyCode : str) :
        if keyCode == "z" :
            self.App.undo()
        if keyCode == "r" :
            self.App.redo()

    def on_btn_view_territory(self) :
        pass
    def on_btn_view_vessel(self) :
        pass
    def cl_hierarchy(self) :
        pass


    # protected
    def _get_data(self) -> data.CData :
        return self.m_mediator.get_data()
    def _get_operator_selection_cl(self) -> operation.COperationSelectionCL :
        return self.m_mediator.m_opSelectionCL
    def _get_clinfo_index(self) -> int :
        return self.m_mediator.get_clinfo_index()
    def _get_skeleton(self) -> algSkeletonGraph.CSkeleton :
        clinfoInx = self._get_clinfo_index()
        return self._get_data().get_skeleton(clinfoInx)
    def _get_clmask(self) -> clMask.CCLMask :
        return self.m_mediator.m_clMask
    def _get_organ_key(self) -> str :
        return self.m_mediator.m_organKey
    def _get_terriinfo(self) -> data.CTerritoryInfo :
        return self.m_mediator.m_terriInfo
    
    def _set_whole_vessel(self, wholeVessel : vtk.vtkPolyData) :
        self.m_mediator.m_wholeVesselPolyData = wholeVessel
    

    def _getui_terri_organ_name_index(self) -> int :
        return self.m_mediator.getui_terri_organ_name_index()
    def _getui_terri_organ_name(self) -> str :
        return self.m_mediator.getui_terri_organ_name()
    

    def _command_territory(self) :
        key = data.CData.make_key(data.CData.s_territoryType, 0, 0)
        self.App.remove_key(key)

        dataInst = self._get_data()
        if dataInst.Ready == False :
            return

        clinfoinx = self._get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoinx)
        if skeleton is None :
            return
        
        opSelectionCL = self._get_operator_selection_cl()
        retList = opSelectionCL.get_all_selection_cl()
        if retList is None :
            print("not selecting centerline")
            return
        
        terriInfo = self._get_terriinfo()
        if terriInfo is None :
            return
        
        startTime = time.perf_counter()
        cmd = commandTerritory.CCommandTerritory(self.App)
        cmd.InputData = dataInst
        cmd.InputSkeleton = skeleton
        cmd.InputCLMask = self._get_clmask()
        cmd.InputTerriInfo = terriInfo
        for id in retList :
            cmd.add_cl_id(id)
        cmd.process()
        terriPolyData = cmd.OutputTerriPolyData
        if terriPolyData is None :
            print("failed to territory")
            return
        endTime = time.perf_counter()
        elapsedTime = (endTime - startTime) * 1000
        print(f"territory elapsed time : {elapsedTime:.3f}ms")
        
        terriObj = vtkObjInterface.CVTKObjInterface()
        terriObj.KeyType = data.CData.s_territoryType
        terriObj.Key = key
        terriObj.Color = CSubStateKnife.s_terriOrganColor
        terriObj.Opacity = 0.5
        terriObj.PolyData = terriPolyData
        dataInst.add_vtk_obj(terriObj)
        self.App.ref_key(key)
        self.App.update_viewer()
    def _command_vessel(self) :
        key = data.CData.make_key(data.CData.s_territoryType, 0, 1)
        self.App.remove_key(key)
        self._set_whole_vessel(None)

        dataInst = self._get_data()
        clinfoInx = self._get_clinfo_index()
        skeleton = self._get_skeleton()

        opSelectionCL = self._get_operator_selection_cl()
        selList = opSelectionCL.get_all_selection_cl()

        # vessel territory
        vesselKey = data.CData.make_key(data.CData.s_vesselType, clinfoInx, 0)
        vesselObj = dataInst.find_obj_by_key(vesselKey)
        if vesselObj is None :
            return
        
        # vessel의 min-max 추출 및 정육면체 생성
        vesselPolyData = vesselObj.PolyData

        cmd = commandTerritoryVessel.CCommandTerritoryVesselEnhanced(self.App)
        cmd.InputData = self._get_data()
        cmd.InputSkeleton = skeleton
        cmd.InputVoxelizeSpacing = (1.0, 1.0, 1.0)
        for clID in selList :
            cmd.add_cl_id(clID)
        cmd.process()

        iCnt = cmd.get_subterri_polydata_count()
        if iCnt == 0 :
            print("failed to territory")
            return 
        
        # vessel & whole vessel 추출
        appendFilter = vtk.vtkAppendPolyData()
        for inx in range(0, iCnt) :
            terriPolyData = cmd.get_subterri_polydata(inx)

            # mesh boolean
            if inx == 0 :
                npVertex = algVTK.CVTK.poly_data_get_vertex(vesselPolyData)
                npIndex = algVTK.CVTK.poly_data_get_triangle_index(vesselPolyData)
                meshLibVessel = algMeshLib.CMeshLib.meshlib_create(npVertex, npIndex)

            npVertex = algVTK.CVTK.poly_data_get_vertex(terriPolyData)
            npIndex = algVTK.CVTK.poly_data_get_triangle_index(terriPolyData)
            meshLibTerri = algMeshLib.CMeshLib.meshlib_create(npVertex, npIndex)

            # vessel extraction
            retMesh = algMeshLib.CMeshLib.meshlib_boolean_intersection(meshLibVessel, meshLibTerri)
            npVertex = algMeshLib.CMeshLib.meshlib_get_vertex(retMesh)
            npIndex = algMeshLib.CMeshLib.meshlib_get_index(retMesh)
            vtkMesh = algVTK.CVTK.create_poly_data_triangle(npVertex, npIndex)
            vtkMesh = self.m_mediator.remove_noise_polydata(vtkMesh)
            appendFilter.AddInputData(vtkMesh)

            # whole vessel extraction
            meshLibVessel = algMeshLib.CMeshLib.meshlib_boolean_subtraction(meshLibVessel, meshLibTerri)


        # whole vessel
        npVertex = algMeshLib.CMeshLib.meshlib_get_vertex(meshLibVessel)
        npIndex = algMeshLib.CMeshLib.meshlib_get_index(meshLibVessel)
        wholeVTKMesh = algVTK.CVTK.create_poly_data_triangle(npVertex, npIndex)
        wholeVTKMesh = self.m_mediator.remove_noise_polydata(wholeVTKMesh)
        self._set_whole_vessel(wholeVTKMesh)

        # vessel
        appendFilter.Update()
        vtkMesh = appendFilter.GetOutput()
        appendFilter = None

        # rendering 
        terriObj = vtkObjInterface.CVTKObjInterface()
        terriObj.KeyType = data.CData.s_territoryType
        terriObj.Key = key
        terriObj.Color = CSubStateKnife.s_terriVesselColor
        terriObj.Opacity = 0.5
        terriObj.PolyData = vtkMesh
        dataInst.add_vtk_obj(terriObj)
        self.App.ref_key(key)

        self.App.update_viewer()


    @property
    def App(self) : 
        return self.m_mediator.m_mediator



if __name__ == '__main__' :
    pass


# print ("ok ..")

