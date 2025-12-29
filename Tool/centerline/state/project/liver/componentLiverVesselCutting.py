import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import copy
import SimpleITK as sitk
import math
from collections import Counter

from PySide6.QtCore import Qt, QItemSelection, QItemSelectionModel
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTreeView, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QListWidgetItem, QMessageBox, QAbstractItemView
from PySide6.QtGui import QStandardItemModel, QStandardItem
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


import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algVTK as algVTK

import VtkObj.vtkObjLine as vtkObjLine
import vtkObjInterface as vtkObjInterface

import data as data

import userData as userData

import com.componentSelectionCL as componentSelectionCL

import command.commandKnife as commandKnife
import command.commandVesselKnife as commandVesselKnife



class CComLiverVesselCutting(componentSelectionCL.CComDrag) :
    ''' 
    input 
        - edit vessel key 
    output 
        - edited main polydata 
    desc
    ''' 
    s_knifeKeyType = "knife" 

    s_pickingDepth = 1000.0 
    s_minDragDist = 10 


    def __init__(self, mediator) :
        super().__init__(mediator)
        self.m_inputEditVesselKey = ""
        self.m_inputCLInfoInx = -1
        self.m_knifeKey = ""

        # slot_finished_knife(polydata : vtk.vtkPolyData)
        self.signal_finished_knife = None
    def clear(self) :
        self.m_inputEditVesselKey = ""
        self.m_inputCLInfoInx = -1
        self.m_knifeKey = ""

        self.signal_finished_knife = None
        super().clear()

    
    # override 
    def ready(self) -> bool :
        if self.m_inputEditVesselKey == "" :
            return False
        return True
    def process_init(self) :
        super().process_init()
        # input your code
        if self.ready() == False :
            return
        
        self.m_knifeKey = ""
    def process_end(self) :
        # input your code
        if self.ready() == False :
            return

        self.m_knifeKey = ""
        self.App.remove_key_type(CComLiverVesselCutting.s_knifeKeyType)
        self.signal_finished_knife = None
        
        super().process_end()
    
    def click(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        
        super().click(clickX, clickY)
        
        dataInst = self._get_data()
        worldStart, pNearStart, pFarStart= self.App.get_world_from_mouse(self.m_startX, self.m_startY, CComLiverVesselCutting.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(self.m_endX, self.m_endY, CComLiverVesselCutting.s_pickingDepth)

        self.m_knifeKey = data.CData.make_key(CComLiverVesselCutting.s_knifeKeyType, 0, 0)
        inst = vtkObjLine.CVTKObjLine()
        inst.KeyType = CComLiverVesselCutting.s_knifeKeyType
        inst.Key = self.m_knifeKey
        inst.set_line_width(2.0)
        inst.set_pos(pFarStart, pFarEnd)
        inst.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        dataInst.add_vtk_obj(inst)

        self.App.ref_key_type(CComLiverVesselCutting.s_knifeKeyType)

        self.m_bDrag = True
        return True
    def click_with_shift(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        return True
    def release(self, clickX : int, clickY : int) :
        if self.ready() == False :
            return False
        if self.Drag == False :
            return False
        
        self.App.remove_key_type(CComLiverVesselCutting.s_knifeKeyType)

        # drag 영역이 너무 작을 경우 무시
        dx = self.m_endX - self.m_startX
        dy = self.m_endY - self.m_startY
        dist = math.hypot(dx, dy)
        if dist < CComLiverVesselCutting.s_minDragDist :
            return False

        self.command_knife_vessel(self.m_startX, self.m_startY, self.m_endX, self.m_endY)

        self.m_bDrag = False
        return True
    def move(self, clickX : int, clickY : int, listExceptKeyType=None) :
        if self.ready() == False :
            return
        if self.Drag == False :
            return False
        
        super().move(clickX, clickY, listExceptKeyType)

        dataInst = self._get_data()
        worldStart, pNearStart, pFarStart = self.App.get_world_from_mouse(self.m_startX, self.m_startY, CComLiverVesselCutting.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(self.m_endX, self.m_endY, CComLiverVesselCutting.s_pickingDepth)
        inst = dataInst.find_obj_by_key(self.m_knifeKey)
        inst.set_pos(pFarStart, pFarEnd)
 
        return True


    # command
    def command_knife_vessel(self, startMx, startMy, endMx, endMy) :
        dataInst = self._get_data()
        clinfoInx = self.InputCLInfoInx
        skeleton = dataInst.get_skeleton(clinfoInx)
        if skeleton is None :
            print("not found skeleton")
            return

        worldStart, pNearStart, pFarStart = self.App.get_world_from_mouse(startMx, startMy, CComLiverVesselCutting.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(endMx, endMy, CComLiverVesselCutting.s_pickingDepth)
        cameraInfo = self.App.get_active_camerainfo()
        cameraPos = cameraInfo[3]

        vesselObj = dataInst.find_obj_by_key(self.InputEditVesselKey)
        vesselPolydata = vesselObj.PolyData
        vertex = algVTK.CVTK.poly_data_get_vertex(vesselPolydata)
        index = algVTK.CVTK.poly_data_get_triangle_index(vesselPolydata)
        vesselPolydata = algVTK.CVTK.create_poly_data_triangle(vertex, index)
        
        cmd = commandVesselKnife.CCommandSepVesselKMGraphVesselKnife(self.App)
        cmd.InputData = dataInst
        cmd.InputSkeleton = skeleton
        cmd.InputWorldA = worldStart
        cmd.InputWorldB = worldEnd
        cmd.InputWorldC = cameraPos
        cmd.InputWholeVessel = vesselPolydata
        cmd.process()

        iCnt = cmd.get_output_polydata_count()
        print(f"command_knife_vessel : output polydata count {iCnt}")

        if iCnt <= 1 :
            print("not intersected knife")
            return
        else :
            if cmd.OutputWhole is None and cmd.OutputSub is None :
                wholePolydata = cmd.get_output_polydata(0)
                subPolydata = cmd.get_output_polydata(1)
            else :
                wholePolydata = cmd.OutputWhole
                subPolydata = cmd.OutputSub

        if self.signal_finished_knife is not None :
            self.signal_finished_knife(wholePolydata)


    
    # ui setting


    # event


    # private
        

    @property
    def InputEditVesselKey(self) -> str : 
        return self.m_inputEditVesselKey
    @InputEditVesselKey.setter
    def InputEditVesselKey(self, inputEditVesselKey : str) :
        self.m_inputEditVesselKey = inputEditVesselKey
    @property
    def InputCLInfoInx(self) -> str : 
        return self.m_inputCLInfoInx
    @InputCLInfoInx.setter
    def InputCLInfoInx(self, inputCLInfoInx : str) :
        self.m_inputCLInfoInx = inputCLInfoInx
    

if __name__ == '__main__' :
    pass


# print ("ok ..")

