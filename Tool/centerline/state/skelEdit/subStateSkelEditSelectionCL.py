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
import vtkObjVertex as vtkObjVertex

import data as data

import operation as operation

import command.commandSkelEdit as commandSkelEdit
import command.commandInterface as commandInterface

import com.componentSelectionCL as componentSelectionCL

import subStateSkelEdit as subStateSkelEdit


class CSubStateSkelEditSelectionCL(subStateSkelEdit.CSubStateSkelEdit) :
    s_radiusKeyType = "radius"


    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_opDragSelectionCL = operation.COperationDragSelectionCL(self.App)
        #self.m_opDragSelectionCL = operation.COperationSelectionCL(self.App)
        self.m_comDragSelCL = None
    def clear(self) :
        # input your code
        self.m_comDragSelCL = None
        super().clear()

    def process_init(self) :
        self.m_opDragSelectionCL.Skeleton = self._get_skeleton()
        self.m_comDragSelCL = componentSelectionCL.CComDragSelCL(self.m_mediator)
        self.m_comDragSelCL.InputOPDragSelCL = self.m_opDragSelectionCL
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
        self.m_opDragSelectionCL.process_reset()
    def key_press_with_ctrl(self, keyCode : str) :
        if keyCode == "z" :
            self.App.undo(0)
        if keyCode == "r" :
            self.App.redo()
    def clicked_mouse_rb(self, clickX, clickY) :
        listExceptKeyType = [
            data.CData.s_vesselType,
            data.CData.s_tumorType
        ]

        if self.m_comDragSelCL is None :
            return
        self.m_comDragSelCL.click(clickX, clickY, listExceptKeyType)
        
        key = self.App.picking(clickX, clickY, listExceptKeyType)
        if key == "" or data.CData.get_type_from_key(key) != data.CData.s_skelTypeCenterline :
            key = ""
        
        
        if self.m_mediator.m_rbSingle.isChecked(): 
            self.m_opDragSelectionCL.ChildSelectionMode = False
        elif self.m_mediator.m_rbDescendant.isChecked():
            self.m_opDragSelectionCL.ChildSelectionMode = True
        if key == "" :
            pass
        else :
            self.m_opDragSelectionCL.process_reset()
            self.m_opDragSelectionCL.add_selection_keys([key])
            self.m_opDragSelectionCL.process()
            
        
        self.App.update_viewer()
        
        dataInst = self._get_data()
        if dataInst.Ready == False :
            return
        
        clinfoInx = self.m_opDragSelectionCL.get_selection_groupID()

        if clinfoInx is None:
            return
        else:
            dataInst.CLInfoIndex = clinfoInx
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

        ################/////////////////

        # if len(retListBrID) == 0 :
        #     print("skel edit : error")
        #     return
        
        # retListBrID = list(set(retListBrID))
        # retListBr = []
        # for brID in retListBrID :
        #     br = self.InputSkeleton.get_branch(brID)
        #     retListBr.append(br)
        
        # for br in retListBr :
        #     if br.get_conn_count() == 1 :
        #         cmd = CCommandRemoveBr(self.m_mediator)
        #         cmd.InputData = self.InputData
        #         cmd.InputSkeleton = self.InputSkeleton
        #         cmd.InputBrID = br.ID
        #         cmd.process()
        #         self.m_listCmd.append(cmd)
        #     elif br.get_conn_count() == 2 :
        #         cmd = CCommandMergeCL(self.m_mediator)
        #         cmd.InputData = self.InputData
        #         cmd.InputSkeleton = self.InputSkeleton
        #         cmd.InputBrID = br.ID
        #         cmd.process()
        #         self.m_listCmd.append(cmd)

        
    def key_press(self, keyCode : str) :
        if keyCode == "Delete" :
            self._remove_cl()

    def apply_root_cl(self) :
        dataInst = self._get_data()
        if dataInst.Ready == False :
            return
        
        #clinfoInx = self._get_clinfo_index()
        clinfoInx = self.m_opDragSelectionCL.get_selection_groupID()
        if clinfoInx is None :
            return
        #skeleton = self._get_skeleton()
        skeleton = dataInst.get_skeleton(clinfoInx)
        if skeleton is None :
            return
        
        retList = self.m_opDragSelectionCL.get_all_selection_cl()
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
        #skeleton = self._get_skeleton()
        dataInst = self._get_data()
        if dataInst.Ready == False :
            return
        
        retList = self.m_opDragSelectionCL.get_all_selection_cl()
        clinfoInx = self.m_opDragSelectionCL.get_selection_groupID()
        
        self.m_opDragSelectionCL.process_reset()
        if retList is None :
            return
        
        cmdContainer = commandInterface.CCommandContainer(self.App)
        cmdContainer.InputData = dataInst
        
        cmd = commandSkelEdit.CCommandAutoRemoveCL(self.App)
        cmd.m_clinfoInx = clinfoInx
        cmd.InputData = dataInst
        #cmd.InputSkeleton = self._get_skeleton()
        cmd.InputSkeleton = dataInst.get_skeleton(clinfoInx)
        cmd.m_opDragSelectionCL = self.m_opDragSelectionCL
        for clID in retList :
            cmd.add_clID(clID)
            
        #cmd.process()
        cmdContainer.add_cmd(cmd)
        cmdContainer.process()
        self.App.add_cmd(cmdContainer)
        
        ## centerline 다시 빌드
        skeleton = dataInst.get_skeleton(clinfoInx)
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

