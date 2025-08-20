import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import math
import time

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
import clMask as clMask

import operation as operation

import tabState as tabState

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algMeshLib as algMeshLib
import AlgUtil.algVTK as algVTK

import VtkObj.vtkObjLine as vtkObjLine
import vtkObjSTL as vtkObjSTL
import vtkObjInterface as vtkObjInterface
import vtkObjGuideCLBound as vtkObjGuideCLBound
import vtkObjKnifeCL as vtkObjKnifeCL 

import command.commandTerritory as commandTerritory
import command.commandTerritoryVessel as commandTerritoryVessel
import command.commandKnife as commandKnife

import subStateKnifeEn as subStateKnifeEn



class CSubStateKnifeCLKnifeEn(subStateKnifeEn.CSubStateKnifeEn) :
    s_knifeKeyType = "knife"
    s_knifeCLKeyType = "knifeCL"

    s_pickingDepth = 1000.0
    s_minDragDist = 10

    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_startMx = 0
        self.m_startMy = 0
        self.m_endMx = 0
        self.m_endMy = 0
        self.m_bActiveKnife = False

        self.m_knifeCLID = -1
        self.m_knifeInx = -1
        self.m_tangent = None

        self.m_knifeKey = ""

        self.m_actorPlane = None
    def clear(self) :
        # input your code
        self.m_startMx = 0
        self.m_startMy = 0
        self.m_endMx = 0
        self.m_endMy = 0
        self.m_bActiveKnife = False

        self.m_knifeCLID = -1
        self.m_knifeInx = -1
        self.m_tangent = None

        self.m_knifeKey = ""
        super().clear()

    def process_init(self) :
        self.App.update_viewer()
    def process(self) :
        pass
    def process_end(self) :
        self.m_startMx = 0
        self.m_startMy = 0
        self.m_endMx = 0
        self.m_endMy = 0
        self.m_bActiveKnife = False

        self.m_knifeKey = ""

        opSelectionCL = self._get_operator_selection_cl()
        opSelectionCL.process_reset()
        self._set_whole_vessel(None)
        self.App.remove_key_type(CSubStateKnifeCLKnifeEn.s_knifeKeyType)
        self.App.remove_key_type(CSubStateKnifeCLKnifeEn.s_knifeCLKeyType)
        self.App.remove_key_type(data.CData.s_territoryType)
        self.m_knifeCLID = -1
        self.m_knifeInx = -1
        self.m_tangent = None

    def clicked_mouse_rb(self, clickX, clickY) :
        dataInst = self._get_data()

        self.m_startMx = clickX
        self.m_startMy = clickY
        self.m_endMx = clickX
        self.m_endMy = clickY
        self.m_bActiveKnife = True

        worldStart, pNearStart, pFarStart= self.App.get_world_from_mouse(self.m_startMx, self.m_startMy, CSubStateKnifeCLKnifeEn.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(self.m_endMx, self.m_endMy, CSubStateKnifeCLKnifeEn.s_pickingDepth)

        self.m_knifeKey = data.CData.make_key(CSubStateKnifeCLKnifeEn.s_knifeKeyType, 0, 0)
        inst = vtkObjLine.CVTKObjLine()
        inst.KeyType = CSubStateKnifeCLKnifeEn.s_knifeKeyType
        inst.Key = self.m_knifeKey
        inst.set_line_width(2.0)
        inst.set_pos(pFarStart, pFarEnd)
        # inst.set_pos(pNearStart, pNearEnd)
        inst.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        dataInst.add_vtk_obj(inst)

        # 초기화 
        opSelectionCL = self._get_operator_selection_cl()
        opSelectionCL.process_reset()
        self._set_whole_vessel(None)
        self.App.ref_key_type(CSubStateKnifeCLKnifeEn.s_knifeKeyType)
        self.App.remove_key_type(CSubStateKnifeCLKnifeEn.s_knifeCLKeyType)
        self.App.remove_key_type(data.CData.s_territoryType)
        self.m_knifeCLID = -1
        self.m_knifeInx = -1
        self.m_tangent = None
        self.App.update_viewer()
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        super().clicked_mouse_rb_shift(clickX, clickY)
        self._update_knife_cl()
        self.App.update_viewer()
    def release_mouse_rb(self) :
        if self.m_bActiveKnife == False :
            return
        
        # self.App.remove_key_type(CSubStateKnifeCLKnifeEn.s_knifeKeyType)

        # drag 영역이 너무 작을 경우 무시
        dx = self.m_endMx - self.m_startMx
        dy = self.m_endMy - self.m_startMy
        dist = math.hypot(dx, dy)
        if dist < CSubStateKnifeCLKnifeEn.s_minDragDist :
            return

        self._command_knife(self.m_startMx, self.m_startMy, self.m_endMx, self.m_endMy)
        self._update_knife_cl()

        self.m_bActiveKnife = False
        self.App.update_viewer()
    def mouse_move_rb(self, clickX, clickY) :
        if self.m_bActiveKnife == False :
            return
        
        dataInst = self._get_data()
        
        self.m_endMx = clickX
        self.m_endMy = clickY
        worldStart, pNearStart, pFarStart = self.App.get_world_from_mouse(self.m_startMx, self.m_startMy, CSubStateKnifeCLKnifeEn.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(self.m_endMx, self.m_endMy, CSubStateKnifeCLKnifeEn.s_pickingDepth)

        inst = dataInst.find_obj_by_key(self.m_knifeKey)
        # inst.set_pos(pNearStart, pNearEnd)
        inst.set_pos(pFarStart, pFarEnd)
        self.App.update_viewer()
    def key_press(self, keyCode : str) :
        if keyCode == "Escape" :
            self.m_bActiveKnife = False
            opSelectionCL = self._get_operator_selection_cl()
            opSelectionCL.process_reset()
            self.m_knifeCLID = -1
            self.m_knifeInx = -1
            self.m_tangent = None
            self._set_whole_vessel(None)
            self.App.remove_key_type(CSubStateKnifeCLKnifeEn.s_knifeKeyType)
            self.App.remove_key_type(CSubStateKnifeCLKnifeEn.s_knifeCLKeyType)
            self.App.remove_key_type(data.CData.s_territoryType)
            self.App.update_viewer()
        if keyCode == "x" :
            self._command_except_cl_point()

        # print(f"keyCode : {keyCode}")

    def on_btn_view_territory(self) :
        if self.m_knifeCLID == -1 :
            self._command_territory()
        else :
            self._command_territory_knife(self.m_knifeCLID, self.m_knifeInx, self.m_tangent)
    def on_btn_view_vessel(self) :
        if self.m_knifeCLID == -1 :
            self._command_vessel()
        else :
            self._command_vessel_enhanced_knife(self.m_a, self.m_b, self.m_c)
    def cl_hierarchy(self) :
        self._update_knife_cl()


    # protected
    def _command_knife(self, startMx, startMy, endMx, endMy) :
        dataInst = self._get_data()
        skeleton = self._get_skeleton()

        worldStart, pNearStart, pFarStart = self.App.get_world_from_mouse(startMx, startMy, CSubStateKnifeCLKnifeEn.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(endMx, endMy, CSubStateKnifeCLKnifeEn.s_pickingDepth)
        cameraInfo = self.App.get_active_camerainfo()
        cameraPos = cameraInfo[3]

        self.m_a = worldStart
        self.m_b = worldEnd
        self.m_c = cameraPos

        knifeCL = commandKnife.CCommandKnifeCL(self.App)
        knifeCL.InputData = dataInst
        knifeCL.InputSkeleton = skeleton
        knifeCL.InputWorldA = worldStart
        knifeCL.InputWorldB = worldEnd
        knifeCL.InputWorldC = cameraPos
        knifeCL.process()

        if knifeCL.OutputKnifedCLID == -1 :
            print("not intersected cl")
            return
        
        self.m_knifeCLID = knifeCL.OutputKnifedCLID
        self.m_knifeInx = knifeCL.OutputKnifedIndex
        self.m_tangent = knifeCL.OutputTangent
        print(f"knifeCLID : {self.m_knifeCLID}")
        print(f"knifeInx : {self.m_knifeInx}")

        clinfoInx = self._get_clinfo_index()
        clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, self.m_knifeCLID)
        opSelectionCL = self._get_operator_selection_cl()
        opSelectionCL.add_selection_key(clKey)
        opSelectionCL.process()

        knifeCL = None
    def _command_territory_knife(self, knifeCLID : int, knifeInx : int, tangent : np.ndarray) :
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
        cmd = commandTerritory.CCommandTerritoryKnife(self.App)
        cmd.InputData = dataInst
        cmd.InputSkeleton = skeleton
        cmd.InputCLMask = self._get_clmask()
        cmd.InputTerriInfo = terriInfo
        cmd.InputKnifeCLID = knifeCLID
        cmd.InputKnifeIndex = knifeInx
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
        
        key = data.CData.make_key(data.CData.s_territoryType, 0, 0)
        terriObj = vtkObjInterface.CVTKObjInterface()
        terriObj.KeyType = data.CData.s_territoryType
        terriObj.Key = key
        terriObj.Color = subStateKnifeEn.CSubStateKnifeEn.s_terriOrganColor
        terriObj.Opacity = 0.5
        terriObj.PolyData = terriPolyData
        dataInst.add_vtk_obj(terriObj)
        self.App.ref_key(key)
        self.App.update_viewer()
    def _command_except_cl_point(self) :
        if self.m_knifeCLID == -1 :
            return
        
        cmd = commandKnife.CCommandKnifeCLMask(self.App)
        cmd.InputData = self._get_data()
        cmd.InputSkeleton = self._get_skeleton()
        cmd.InputKnifedCLID = self.m_knifeCLID
        cmd.InputKnifedIndex = self.m_knifeInx
        cmd.InputCLMask = self._get_clmask()
        cmd.process()
        self.App.add_cmd(cmd)

        opSelectionCL = self._get_operator_selection_cl()
        opSelectionCL.process_reset()
        self.m_bActiveKnife = False
        self._set_whole_vessel(None)
        self.App.remove_key_type(CSubStateKnifeCLKnifeEn.s_knifeKeyType)
        self.App.remove_key_type(CSubStateKnifeCLKnifeEn.s_knifeCLKeyType)
        self.App.remove_key_type(data.CData.s_territoryType)
        self.m_knifeCLID = -1
        self.m_knifeInx = -1
        self.m_tangent = None

        self.App.update_viewer()

        print("check exception point")
    
    def _update_knife_cl(self) :
        self.App.remove_key_type(CSubStateKnifeCLKnifeEn.s_knifeCLKeyType)
        
        dataInst = self._get_data()
        skeleton = self._get_skeleton()
        opSelectionCL = self._get_operator_selection_cl()

        key = data.CData.make_key(CSubStateKnifeCLKnifeEn.s_knifeCLKeyType, 0, 0)
        obj = vtkObjKnifeCL.CVTKObjKnifeCL(skeleton, opSelectionCL, self.m_knifeCLID, self.m_knifeInx, dataInst.CLSize + 0.01)
        obj.KeyType = CSubStateKnifeCLKnifeEn.s_knifeCLKeyType
        obj.Key = key
        obj.Color = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 1.0])
        
        if obj.Ready == True :
            dataInst.add_vtk_obj(obj)
            self.App.ref_key_type(CSubStateKnifeCLKnifeEn.s_knifeCLKeyType)

        self.App.update_viewer()

    def render_plane(self, a, b, c) :
        renderer = self.App.get_viewercl_renderer()
        if self.m_actorPlane is not None :
            renderer.RemoveActor(self.m_actorPlane)
            self.m_actorPlane = None

        points = vtk.vtkPoints()
        points.InsertNextPoint(a.reshape(-1))
        points.InsertNextPoint(b.reshape(-1))
        points.InsertNextPoint(c.reshape(-1))

        # 삼각형 정의 (각 인덱스는 points에서의 순서)
        triangle = vtk.vtkTriangle()
        triangle.GetPointIds().SetId(0, 0)
        triangle.GetPointIds().SetId(1, 1)
        triangle.GetPointIds().SetId(2, 2)

        # 폴리곤 데이터 구성
        triangles = vtk.vtkCellArray()
        triangles.InsertNextCell(triangle)

        polyData = vtk.vtkPolyData()
        polyData.SetPoints(points)
        polyData.SetPolys(triangles)

        # 매퍼 설정
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(polyData)
        # 반투명 액터 생성
        self.m_actorPlane = vtk.vtkActor()
        self.m_actorPlane.SetMapper(mapper)
        # 반투명 재질 설정
        self.m_actorPlane.GetProperty().SetColor(1.0, 0.5, 0.0)    # 주황빛 색상
        self.m_actorPlane.GetProperty().SetOpacity(0.4)           # 투명도 (0.0~1.0)

        renderer.AddActor(self.m_actorPlane)




if __name__ == '__main__' :
    pass


# print ("ok ..")

