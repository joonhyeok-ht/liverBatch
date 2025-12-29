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
fileStatePath = os.path.dirname(fileAbsPath)
fileAppPath = os.path.dirname(fileStatePath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
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
import vtkObjRadius as vtkObjRadius

import data as data

import operation as operation

import command.commandSkelEdit as commandSkelEdit

import com.componentSelectionCL as componentSelectionCL

import subStateSkelEdit as subStateSkelEdit


class CSubStateSkelEditSelectionCL(subStateSkelEdit.CSubStateSkelEdit) :
    s_radiusKeyType = "radius"


    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_opSelectionCL = operation.COperationDragSelectionCL(self.App)
        self.m_comDragSelCL = None
    def clear(self) :
        # input your code
        self.m_comDragSelCL = None
        super().clear()

    def process_init(self) :
        self.m_opSelectionCL.Skeleton = self._get_skeleton()
        self.m_comDragSelCL = componentSelectionCL.CComDragSelCL(self.m_mediator)
        self.m_comDragSelCL.InputOPDragSelCL = self.m_opSelectionCL
        self.m_comDragSelCL.InputUIRBSelSingle = self.m_mediator.m_rbSingle
        self.m_comDragSelCL.InputUIRBSelDescendant = self.m_mediator.m_rbDescendant
        self.m_comDragSelCL.process_init()
        self.App.update_viewer()
    def process(self) :
        pass
    def process_end(self) :
        if self.m_comDragSelCL is not None :
            self.m_comDragSelCL.process_end()
            self.m_comDragSelCL = None
        self.m_opSelectionCL.process_reset()

    def clicked_mouse_rb(self, clickX, clickY) :
        listExceptKeyType = [
            data.CData.s_vesselType
        ]

        if self.m_comDragSelCL is None :
            return
        self.m_comDragSelCL.click(clickX, clickY, listExceptKeyType)
        self.App.update_viewer()
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        listExceptKeyType = [
            data.CData.s_vesselType,
        ]

        if self.m_comDragSelCL is None :
            return
        self.m_comDragSelCL.click_with_shift(clickX, clickY, listExceptKeyType)
        self.App.update_viewer()
    def release_mouse_rb(self) :
        listExceptKeyType = [
            data.CData.s_vesselType,
        ]

        if self.m_comDragSelCL is None :
            return
        self.m_comDragSelCL.release(0, 0)
        self.App.update_viewer()
    def mouse_move_rb(self, clickX, clickY) :
        listExceptKeyType = [
            data.CData.s_vesselType,
        ]

        if self.m_comDragSelCL is None :
            return
        self.m_comDragSelCL.move(clickX, clickY, listExceptKeyType)
        self.App.update_viewer()
    def key_press(self, keyCode : str) :
        if keyCode == "Delete" :
            self._remove_cl()

    def apply_root_cl(self) :
        dataInst = self._get_data()
        if dataInst.Ready == False :
            return
        
        clinfoInx = self._get_clinfo_index()
        skeleton = self._get_skeleton()
        if skeleton is None :
            return
        
        retList = self.m_opSelectionCL.get_all_selection_cl()
        if retList is None :
            print("not selecting centerline")
            return
        
        clID = retList[0]
        skeleton.build_tree(clID)

        self.App.refresh_key_type_groupID(data.CData.s_skelTypeCenterline, clinfoInx, data.CData.s_clColor)
        rootKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, clID)
        self.App.refresh_key(rootKey, data.CData.s_rootCLColor)

        rootID = skeleton.RootCenterline.ID
        clCount = skeleton.get_centerline_count()
        brCount = skeleton.get_branch_count()
        self._setui_rootid(rootID)
        self._setui_cl_count(clCount)
        self._setui_br_count(brCount)
        self.App.update_viewer()
    

    # protected
    def _remove_cl(self) :
        dataInst = self._get_data()
        if dataInst.Ready == False :
            return
        
        retList = self.m_opSelectionCL.get_all_selection_cl()
        self.m_opSelectionCL.process_reset()
        if retList is None :
            return

        cmd = commandSkelEdit.CCommandAutoRemoveCL(self.App)
        cmd.InputData = dataInst
        cmd.InputSkeleton = self._get_skeleton()
        for clID in retList :
            cmd.add_clID(clID)
        cmd.process()

        skeleton = self._get_skeleton()
        skeleton.extract_leaf_centerline()
        skeleton.build_graph()
        skeleton.init_kd_anchor()

        rootID = skeleton.RootCenterline.ID
        clCount = skeleton.get_centerline_count()
        brCount = skeleton.get_branch_count()
        self._setui_rootid(rootID)
        self._setui_cl_count(clCount)
        self._setui_br_count(brCount)

        self.App.update_viewer()

    
    # private

if __name__ == '__main__' :
    pass


# print ("ok ..")

