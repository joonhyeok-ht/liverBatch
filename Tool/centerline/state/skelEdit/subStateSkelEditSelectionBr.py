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

import VtkObj.vtkObjLine as vtkObjLine
import VtkObj.vtkObjSphere as vtkObjSphere

import vtkObjGuideBr as vtkObjGuideBr
import vtkObjGuideCL as vtkObjGuideCL
import vtkObjGuideRange as vtkObjGuideRange

import data as data

import operation as operation

import command.commandInterface as commandInterface
import command.commandSkelEdit as commandSkelEdit

import subStateSkelEdit as subStateSkelEdit


class CSubStateSkelEditSelectionBr(subStateSkelEdit.CSubStateSkelEdit) :
    s_guideBrType = "guideBranch" 
    s_guideClType = "guideCL"
    s_guideRangeType = "guideRange"


    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_selBrKey = ""
        self.m_guideBrKey = ""
        self.m_listGuideCLKey = []
        self.m_guideRangeKey = ""
        self.m_anchorX = 0
        self.m_anchorY = 0
        self.m_anchorPos = None
        self.m_range = 2
    def clear(self) :
        # input your code
        self.m_guideBrKey = ""
        self.m_listGuideCLKey.clear()
        self.m_guideRangeKey = ""
        self.m_anchorX = 0
        self.m_anchorY = 0
        self.m_anchorPos = None
        self.m_range = 2
        super().clear()

    def process_init(self) :
        opSelectionCL = self._get_operator_selection_cl()
        opSelectionCL.ChildSelectionMode = False
        opSelectionCL.ParentSelectionMode = False

        clinfoInx = self._get_clinfo_index()
        self._setui_range(self.m_range)
        self.App.ref_key_type_groupID(data.CData.s_skelTypeBranch, clinfoInx)
        self.App.update_viewer()
    def process(self) :
        pass
    def process_end(self) :
        opSelectionBr = self._get_operator_selection_br()
        opSelectionCL = self._get_operator_selection_cl()
        opSelectionBr.process_reset()
        opSelectionCL.process_reset()
        self._remove_guide_key()
        self.App.unref_key_type(data.CData.s_skelTypeBranch)

        self.m_selBrKey = ""
        self.m_anchorX = 0
        self.m_anchorY = 0
        self.m_anchorPos = None

    def clicked_mouse_rb(self, clickX, clickY) :
        # 기존에 선택된 것이 없다면 branch를 찾으려는 시도를 한다.
        if self.m_selBrKey == "" :
            listExceptKeyType = [
                data.CData.s_vesselType,
                data.CData.s_skelTypeCenterline,
                CSubStateSkelEditSelectionBr.s_guideClType,
                CSubStateSkelEditSelectionBr.s_guideBrType,
                CSubStateSkelEditSelectionBr.s_guideRangeType
            ]
            selKey = self.App.picking(clickX, clickY, listExceptKeyType)
            opSelectionBr = self._get_operator_selection_br()
            opSelectionCL = self._get_operator_selection_cl()
            opSelectionBr.process_reset()
            opSelectionCL.process_reset()
            self._remove_guide_key()

            if selKey == "" :
                self.m_selBrKey = ""
            else :
                self.m_selBrKey = selKey
                self._create_guide_key(algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0]))
                self._ref_guide_key()

                dataInst = self._get_data()
                obj = dataInst.find_obj_by_key(self.m_guideBrKey)
                self.m_anchorX = clickX
                self.m_anchorY = clickY
                self.m_anchorPos = obj.Pos.copy()
        else :
            listExceptKeyType = [
                data.CData.s_vesselType,
                data.CData.s_skelTypeCenterline,
                CSubStateSkelEditSelectionBr.s_guideClType,
                CSubStateSkelEditSelectionBr.s_guideBrType,
                CSubStateSkelEditSelectionBr.s_guideRangeType
            ]
            selKey = self.App.picking(clickX, clickY, listExceptKeyType)

            if selKey == "" :
                opSelectionBr = self._get_operator_selection_br()
                opSelectionCL = self._get_operator_selection_cl()
                opSelectionBr.process_reset()
                opSelectionCL.process_reset()
                self._remove_guide_key()

                self.m_selBrKey = ""
                
                self.App.update_viewer()
                return
            
            if selKey != self.m_selBrKey :
                opSelectionBr = self._get_operator_selection_br()
                opSelectionCL = self._get_operator_selection_cl()
                opSelectionBr.process_reset()
                opSelectionCL.process_reset()
                self._remove_guide_key()

                self.m_selBrKey = selKey
                self._create_guide_key(algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0]))
                self._ref_guide_key()
            
            dataInst = self._get_data()
            obj = dataInst.find_obj_by_key(self.m_guideBrKey)
            self.m_anchorX = clickX
            self.m_anchorY = clickY
            self.m_anchorPos = obj.Pos.copy()

        self.App.update_viewer()
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        pass
    def release_mouse_rb(self) :
        if self.m_selBrKey != "" :
            # update가 수행됨
            dataInst = self._get_data()
            skeleton = self._get_skeleton()

            selectedBrID = data.CData.get_id_from_key(self.m_selBrKey)
            br = skeleton.get_branch(selectedBrID) 
            guideBr = dataInst.find_obj_by_key(self.m_guideBrKey)

            # guideBr의 움직임이 거의 없다면 cmd를 수행하지 않는다. 
            if algLinearMath.CScoMath.is_equal_vec(br.BranchPoint, guideBr.Pos) == False :
                cmdContainer = commandInterface.CCommandContainer(self.App)
                cmdContainer.InputData = dataInst

                cmd = commandSkelEdit.CCommandUpdateBr(self.App)
                cmd.InputData = dataInst
                cmd.InputSkeleton = skeleton
                cmd.InputBrID = br.ID
                cmd.InputPos = guideBr.Pos
                cmdContainer.add_cmd(cmd)

                iCnt = br.get_conn_count()
                for inx in range(0, iCnt) :
                    cl = br.get_conn(inx)
                    guideCL = dataInst.find_obj_by_key(self.m_listGuideCLKey[inx])

                    cmd = commandSkelEdit.CCommandUpdateCL(self.App)
                    cmd.InputData = dataInst
                    cmd.InputSkeleton = skeleton
                    cmd.InputCLID = cl.ID
                    cmd.InputVertex = guideCL.ModifiedVertex
                    cmd.InputMinInx = guideCL.MinInx
                    cmd.InputReverse = guideCL.Reverse
                    cmdContainer.add_cmd(cmd)
            
                cmdContainer.process()
                self.App.add_cmd(cmdContainer)

                opSelectionBr = self._get_operator_selection_br()
                opSelectionCL = self._get_operator_selection_cl()
                opSelectionBr.process_reset()
                opSelectionCL.process_reset()
                self._remove_guide_key()
                self.m_selBrKey = ""
                self.App.update_viewer()
    def mouse_move_rb(self, clickX, clickY) :
        if self.m_selBrKey == "" :
            return
        
        cameraInfo = self.App.get_active_camerainfo()
        dx = clickX - self.m_anchorX
        dy = clickY - self.m_anchorY

        scaleFactor = 0.05

        rightVec = -cameraInfo[0].copy()
        upVec = cameraInfo[1].copy()
        rightVec *= dx * scaleFactor
        upVec *= dy * scaleFactor
        moveVec = rightVec + upVec

        # update
        dataInst = self._get_data()
        obj = dataInst.find_obj_by_key(self.m_guideBrKey)
        moveVec = self.m_anchorPos + moveVec
        obj.Pos = moveVec

        weight = 0.9
        for key in self.m_listGuideCLKey :
            obj = dataInst.find_obj_by_key(key)
            obj.process(moveVec, weight)

        self.App.update_viewer()
    def key_press_with_ctrl(self, keyCode : str) :
        if keyCode == "z" :
            self.App.undo()
        if keyCode == "r" :
            self.App.redo()
    def change_range(self, range : int) :
        self.m_range = range
        if self.m_guideRangeKey == "" :
            return
        dataInst = self._get_data()
        obj = dataInst.find_obj_by_key(self.m_guideRangeKey)
        obj.Range = self.m_range

        for guideCLKey in self.m_listGuideCLKey :
            obj = dataInst.find_obj_by_key(guideCLKey)
            obj.Range = self.m_range
        
        self.App.update_viewer()


    # protected
    def _remove_guide_key(self) :
        if self.m_guideBrKey != "" :
            self.App.remove_key(self.m_guideBrKey)
            for guideKey in self.m_listGuideCLKey :
                self.App.remove_key(guideKey)
            self.App.remove_key(self.m_guideRangeKey)

            self.m_guideBrKey = ""
            self.m_listGuideCLKey.clear()
            self.m_guideRangeKey = ""
    def _ref_guide_key(self) :
        self.App.ref_key(self.m_guideBrKey)
        for guideCLKey in self.m_listGuideCLKey :
            self.App.ref_key(guideCLKey)
        self.App.ref_key(self.m_guideRangeKey)
    def _create_guide_key(self, guideColor : np.ndarray) :
        dataInst = self._get_data()
        skeleton = self._get_skeleton()
        if self.m_selBrKey == "" :
            return
        
        # branch guide create
        selectedBrID = data.CData.get_id_from_key(self.m_selBrKey)
        br = skeleton.get_branch(selectedBrID)

        guideBrKey = data.CData.make_key(CSubStateSkelEditSelectionBr.s_guideBrType, 0, 0)
        guideBrObj = vtkObjGuideBr.CVTKObjGuideBr(br, dataInst.BrSize)
        guideBrObj.KeyType = CSubStateSkelEditSelectionBr.s_guideBrType
        guideBrObj.Key = guideBrKey
        guideBrObj.Color = guideColor
        guideBrObj.Opacity = 1.0
        dataInst.add_vtk_obj(guideBrObj)
        self.m_guideBrKey = guideBrKey

        iCnt = br.get_conn_count()
        for inx in range(0, iCnt) :
            cl = br.get_conn(inx)
            guideKey = data.CData.make_key(CSubStateSkelEditSelectionBr.s_guideClType, 0, inx)
            guideObj = vtkObjGuideCL.CVTKObjGuideCL(cl, br.BranchPoint, self.m_range)
            guideObj.KeyType = CSubStateSkelEditSelectionBr.s_guideClType
            guideObj.Key = guideKey
            guideObj.Color = guideColor
            guideObj.Opacity = 1.0
            guideObj.set_line_width(4.0)
            self.m_listGuideCLKey.append(guideKey)
            dataInst.add_vtk_obj(guideObj)
        
        guideRangeKey = data.CData.make_key(CSubStateSkelEditSelectionBr.s_guideRangeType, 0, 0)
        guideRangeObj = vtkObjGuideRange.CVTKObjGuideRange(br.BranchPoint, self.m_range)
        guideRangeObj.KeyType = CSubStateSkelEditSelectionBr.s_guideRangeType
        guideRangeObj.Key = guideRangeKey
        guideRangeObj.Color = guideColor
        guideRangeObj.Opacity = 0.5
        dataInst.add_vtk_obj(guideRangeObj)
        self.m_guideRangeKey = guideRangeKey

if __name__ == '__main__' :
    pass


# print ("ok ..")

