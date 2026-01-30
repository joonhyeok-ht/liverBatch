import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import math
from scipy.spatial import KDTree

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QMessageBox
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileCommonPath = os.path.dirname(fileAbsPath)
fileStateProjectPath = os.path.dirname(fileCommonPath)
fileStatePath = os.path.dirname(fileStateProjectPath)
fileAppPath = os.path.dirname(fileStatePath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileCommonPath)
sys.path.append(fileStateProjectPath)
sys.path.append(fileStatePath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algSkeletonGraph as algSkeletonGraph

import VtkObj.vtkObjLine as vtkObjLine
import VtkObj.vtkObjSphere as vtkObjSphere

import vtkObjInterface as vtkObjInterface

import data as data

import operation as operation

import remodelingNode as remodelingNode
import tabState as tabState
import subStateRemodeling as subStateRemodeling 


class CSubStateRemodelingExtractionEnCL(subStateRemodeling.CSubStateRemodeling) :
    s_guideCellType = "guideCell"
    '''
    groupID : 0 고정
    ID : only 0, 1
    '''


    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_stateSelCell = -1
        self.m_selCellID = -1
    def clear(self) :
        # input your code
        self.m_stateSelCell = -1
        self.m_selCellID = -1
        super().clear()

    def process_init(self) :
        self.m_mediator.setui_check_sel_cell(False)
        self._set_selcellstate(0)
    def process(self) :
        pass
    def process_end(self) :
        self.m_mediator.clear_render_entity()
        self.m_mediator.setui_check_sel_cell(False)
        self._set_selcellstate(-1)

    def clicked_mouse_rb(self, clickX, clickY) :
        dataInst = self._get_data()
        if dataInst.Ready == False :
            return
        
        if self.m_stateSelCell == 0 : 
            return
        
        guideCell = self.__get_guide_cell_obj(0)
        polyData = guideCell.PolyData
        if polyData is None :
            return
        
        guideCell = self.__get_guide_cell_obj(1)
        guideCell.PolyData = polyData
        self.m_mediator.setui_cellID(self.m_selCellID)
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        pass
    def release_mouse_rb(self) :
        dataInst = self._get_data()
        if dataInst.Ready == False :
            return
        
    def mouse_move(self, clickX, clickY) :
        dataInst = self._get_data()
        if dataInst.Ready == False :
            return
        
        # vessel과 마우스와의 picking 수행
        # 가장 가까운 cell을 찾음
        # cell의 중심 vertex를 guideEPKey에 세팅 
        listExceptKeyType = [
            data.CData.s_skelTypeCenterline,
            data.CData.s_vesselType,
            subStateRemodeling.CSubStateRemodeling.s_subRemodelingKey,
            CSubStateRemodelingExtractionEnCL.s_guideCellType,
        ]

        if self.m_stateSelCell == 0 : 
            return

        self.m_selCellID = self.App.picking_cellid(clickX, clickY, listExceptKeyType)
        if self.m_selCellID <= 0 :
            return

        if self.m_selCellID > 0 :
            selectedNode = self.m_mediator.getui_lv_cuttednode_selected_node()
            if selectedNode is None :
                print("invalid selectedNode")
                return
            
            cuttedMesh = self.m_mediator.get_cuttedmesh_polydata(selectedNode.Key)
            pickedPoly = algVTK.CVTK.get_sub_polydata_by_face_fast(cuttedMesh, [self.m_selCellID])

            retPoly = vtk.vtkPolyData()
            retPoly.DeepCopy(pickedPoly)
            guideCell = self.__get_guide_cell_obj(0)
            guideCell.PolyData = retPoly
            self.App.update_viewer()
    def mouse_move_rb(self, clickX, clickY) :
        dataInst = self._get_data()
        if dataInst.Ready == False :
            return
    def key_press(self, keyCode : str) :
        if keyCode == "Escape" :
            pass
        elif keyCode == "Delete" :
            pass
    def key_press_with_ctrl(self, keyCode : str) :
        if keyCode == "z" :
            pass
    

    def changed_cutting_mesh(self, prevNode : remodelingNode.CRemodelingNode, nowNode : remodelingNode.CRemodelingNode) :
        if self.m_stateSelCell == 0 :
            return 
        
        guideCell = self.__get_guide_cell_obj(0)
        guideCell.PolyData = None
        guideCell = self.__get_guide_cell_obj(1)
        guideCell.PolyData = None
    def checked_sel_cell(self, bChecked : bool) :
        if bChecked == True :
            self._set_selcellstate(1)
        else :
            self._set_selcellstate(0)


    # protected
    def _set_selcellstate(self, state : int) :
        # state exit
        if self.m_stateSelCell >= 0 :
            if self.m_stateSelCell == 0 :
                pass
            else :
                self.App.remove_key_type(CSubStateRemodelingExtractionEnCL.s_guideCellType)

        self.m_stateSelCell = state
        self.m_selCellID = -1
        self.m_mediator.setui_cellID(-1)

        if self.m_stateSelCell >= 0 :
            if self.m_stateSelCell == 0 :
                pass
            else :
                self.m_picker = vtk.vtkCellPicker()
                self.m_picker.SetTolerance(0.0005)
                self.__create_guide_cell_key(0, algLinearMath.CScoMath.to_vec3([1.0, 0.9, 0.2]))
                self.__create_guide_cell_key(1, algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0]))
                self.App.ref_key_type(CSubStateRemodelingExtractionEnCL.s_guideCellType)

        self.App.update_viewer()

    
    # private
    def __create_guide_cell_key(self, id : int, color : np.ndarray) -> str :
        guideKey = data.CData.make_key(CSubStateRemodelingExtractionEnCL.s_guideCellType, 0, id)
        guideObj = vtkObjInterface.CVTKObjInterface()
        guideObj.KeyType = CSubStateRemodelingExtractionEnCL.s_guideCellType
        guideObj.Key = guideKey
        guideObj.Color = color
        guideObj.Opacity = 1.0

        dataInst = self._get_data()
        dataInst.add_vtk_obj(guideObj)
        return guideKey
    def __get_guide_cell_obj(self, id : int) -> vtkObjInterface.CVTKObjInterface :
        guideKey = data.CData.make_key(CSubStateRemodelingExtractionEnCL.s_guideCellType, 0, id)
        dataInst = self._get_data()
        guideObj = dataInst.find_obj_by_key(guideKey)
        return guideObj

if __name__ == '__main__' :
    pass


# print ("ok ..")

