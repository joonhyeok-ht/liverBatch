import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import math
from scipy.spatial import KDTree

from PySide6.QtCore import Qt, QEvent, QObject, QPoint
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QMessageBox, QMenu
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

import vtkObjGuideCL as vtkObjGuideCL

import data as data

import operation as operation

import subStateCutting as subStateCutting 

import treeVessel as treeVessel
import com.componentVesselCutting as componentVesselCutting


class CSubStateCuttingCutting(subStateCutting.CSubStateCutting) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_comAutoCutting = None
        self.m_comKnifeCutting = None
        self.m_state = 0
    def clear(self) :
        # input your code
        self.m_state = 0
        if self.m_comAutoCutting is not None :
            self.m_comAutoCutting.clear()
            self.m_comAutoCutting = None
        if self.m_comKnifeCutting is not None :
            self.m_comKnifeCutting.clear()
            self.m_comKnifeCutting = None
        super().clear()

    def process_init(self) :
        self.m_comAutoCutting = componentVesselCutting.CComAutoCuttingTree(self.m_mediator)
        self.m_comAutoCutting.InputUILVInvalidVessel = self.m_mediator.m_lvInvalidNode
        self.m_comAutoCutting.signal_finished_knife = self.slot_finished_knife
        self.m_comAutoCutting.process_init()

        self.m_comKnifeCutting = componentVesselCutting.CComKnifeCutting(self.m_mediator)
        self.m_comKnifeCutting.InputUILVVessel = self.m_mediator.m_lvNode
        self.m_comKnifeCutting.process_init()
        self._command_auto_cutting()
    def process(self) :
        pass
    def process_end(self) :
        if self.m_comAutoCutting is not None :
            self.m_comAutoCutting.process_end()
            self.m_comAutoCutting = None
        if self.m_comKnifeCutting is not None :
            self.m_comKnifeCutting.process_end()
            self.m_comKnifeCutting = None

    def clicked_mouse_rb(self, clickX, clickY) :
        dataInst = self._get_data()
        if dataInst.Ready == False :
            return
        
        if self.m_comAutoCutting is None : 
            return
        if self.m_comKnifeCutting is None : 
            return
        
        if self.m_state == 0 :
            self.m_comAutoCutting.click(clickX, clickY)
        else :
            self.m_comKnifeCutting.click(clickX, clickY)
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        pass
    def release_mouse_rb(self) :
        if self.m_comAutoCutting is None :
            return
        if self.m_comKnifeCutting is None : 
            return
        
        if self.m_state == 0 :
            self.m_comAutoCutting.release(0, 0)
        else :
            self.m_comKnifeCutting.release(0, 0)
    def mouse_move(self, clickX, clickY) :
        pass
    def mouse_move_rb(self, clickX, clickY) :
        if self.m_comAutoCutting is None :
            return
        if self.m_comKnifeCutting is None : 
            return
        
        if self.m_state == 0 :
            self.m_comAutoCutting.move(clickX, clickY)
        else :
            self.m_comKnifeCutting.move(clickX, clickY)
    def key_press(self, keyCode : str) :
        if keyCode == "Escape" :
            pass
        elif keyCode == "Delete" :
            pass
    def key_press_with_ctrl(self, keyCode : str) :
        if self.m_comKnifeCutting is None :
            return
        
        if self.m_state == 0 :
            pass
        else :
            if keyCode == "z" :
                self.m_comKnifeCutting.command_undo()


    # protected
    def _command_auto_cutting(self) :
        datainst = self._get_data()
        clinfoinx = self._get_clinfo_index()

        treevessel = self._get_tree_vessel()
        vesselKey = data.CData.make_key(data.CData.s_vesselType, clinfoinx, 0)
        vesselObj = datainst.find_obj_by_key(vesselKey)
        mesh = vesselObj.PolyData
        
        self.m_comAutoCutting.command_cutting_vessel(treevessel, mesh)
        if self.m_comAutoCutting.get_invalid_node_count() == 0 :
            self.m_comKnifeCutting.command_init_with_tree_vessel(treevessel)
            self.m_state = 1
    

    def slot_finished_knife(self, node : treeVessel.CNodeVesselHier) :
        if self.m_state == 1 :
            return
        
        if self.m_comAutoCutting.get_invalid_node_count() == 0 :
            treevessel = self._get_tree_vessel()
            self.m_comKnifeCutting.command_init_with_tree_vessel(treevessel)
            self.m_state = 1
    def slot_vessel_hierarchy(self, listCLID : list) :
        self.m_mediator.m_opSelectionCL.process_reset()
        clinfoInx = self._get_clinfo_index()
        for clID in listCLID :
            key = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, clID)
            self.m_mediator.m_opSelectionCL.add_selection_key(key)
        self.m_mediator.m_opSelectionCL.process()
    def on_return_pressed_cutting_name(self, cuttingName : str) :
        if self.m_state == 1 :
            self.m_comKnifeCutting.command_label_name(cuttingName)
    def on_btn_save_cutting_mesh(self) :
        if self.m_state == 0 :
            QMessageBox.information(self.App, "Alarm", "please remove invalid node")
            return
        
        terriOutPath = self._get_data().get_terri_out_path()
        if os.path.exists(terriOutPath) == False :
            return
        
        retDict = self.m_comKnifeCutting.get_all_polydata()
        if len(retDict) == 0 :
            QMessageBox.information(self.App, "Alarm", "failed save cutting mesh : not found cutting mesh")
            return
        
        for cuttingName, cuttingMesh in retDict.items() :
            fullPath = os.path.join(terriOutPath, f"{cuttingName}.stl")
            algVTK.CVTK.save_poly_data_stl(fullPath, cuttingMesh)
        
        QMessageBox.information(self.App, "Alarm", "completed save cutting mesh")




if __name__ == '__main__' :
    pass


# print ("ok ..")

