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

import vtkObjGuideEP as vtkObjGuideEP
import vtkObjGuideCL as vtkObjGuideCL
import vtkObjGuideRange as vtkObjGuideRange
import vtkObjGuideCell as vtkObjGuideCell

import data as data

import operation as operation

import command.commandInterface as commandInterface
import command.commandSkelEdit as commandSkelEdit

import subStateSkelEdit as subStateSkelEdit

class CSelectionEPState :
    def __init__(self, mediator) :
        self.m_mediator = mediator

    
    def init(self) :
        pass
    def clear(self) :
        pass

    def clicked_mouse_rb(self, clickX, clickY) :
        pass
    def mouse_move(self, clickX, clickY) :
        pass
class CSelectionEPStateNonSelection(CSelectionEPState) :
    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
    
    def init(self) :
        super().init()
        # input your code
        self.m_mediator.m_selEPKey = ""
        self.m_mediator.App.update_viewer()
    def clear(self) :
        # input your code
        super().clear()


    def clicked_mouse_rb(self, clickX, clickY) :
        listExceptKeyType = [
            data.CData.s_vesselType,
            data.CData.s_skelTypeCenterline,
            CSubStateSkelEditSelectionEP.s_guideClType,
            CSubStateSkelEditSelectionEP.s_guideEPType,
            CSubStateSkelEditSelectionEP.s_guideRangeType,
            CSubStateSkelEditSelectionEP.s_guideCellType,
        ]
        selKey = self.m_mediator.App.picking(clickX, clickY, listExceptKeyType)
        opSelectionEP = self.m_mediator.get_operator_selection_ep()
        opSelectionCL = self.m_mediator.get_operator_selection_cl()
        opSelectionEP.process_reset()
        opSelectionCL.process_reset()
        self.m_mediator.remove_guide_key()

        if selKey == "" :
            self.m_mediator.m_selEPKey = ""
        else :
            self.m_mediator.m_selEPKey = selKey
            self.m_mediator.set_state(1)
        self.m_mediator.App.update_viewer()
class CSelectionEPStateSelection(CSelectionEPState) :
    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
    
    def init(self) :
        super().init()
        # input your code
        self.m_mediator.create_guide_key(self.m_mediator.s_guideColor, self.m_mediator.s_guideCellColor)
        self.m_mediator.ref_guide_key()

        self.m_mediator.App.update_viewer()
    def clear(self) :
        # input your code
        opSelectionEP = self.m_mediator.get_operator_selection_ep()
        opSelectionCL = self.m_mediator.get_operator_selection_cl()
        opSelectionEP.process_reset()
        opSelectionCL.process_reset()
        self.m_mediator.remove_guide_key()
        super().clear()


    def clicked_mouse_rb(self, clickX, clickY):
        listExceptKeyType = [
            data.CData.s_vesselType,
            data.CData.s_skelTypeCenterline,
            CSubStateSkelEditSelectionEP.s_guideClType,
            CSubStateSkelEditSelectionEP.s_guideEPType,
            CSubStateSkelEditSelectionEP.s_guideRangeType,
            CSubStateSkelEditSelectionEP.s_guideCellType,
        ]
        selKey = self.m_mediator.App.picking(clickX, clickY, listExceptKeyType)
        # cl update 
        if selKey == "" :
            dataInst = self.m_mediator.get_data()
            skeleton = self.m_mediator.get_skeleton()

            selectedEPID = data.CData.get_id_from_key(self.m_mediator.m_selEPKey)
            leafCL = skeleton.get_centerline(selectedEPID) 
            endPt = leafCL.get_end_point()
            guideEP = dataInst.find_obj_by_key(self.m_mediator.m_guideEPKey)
            guideCL = dataInst.find_obj_by_key(self.m_mediator.m_guideCLKey)

            # guideBr의 움직임이 거의 없다면 cmd를 수행하지 않는다. 
            if algLinearMath.CScoMath.is_equal_vec(endPt, guideEP.Pos) == False :
                cmd = commandSkelEdit.CCommandUpdateCL(self.m_mediator.App)
                cmd.InputData = dataInst
                cmd.InputSkeleton = skeleton
                cmd.InputCLID = leafCL.ID
                cmd.InputVertex = guideCL.ModifiedVertex
                cmd.InputMinInx = guideCL.MinInx
                cmd.InputReverse = guideCL.Reverse
                cmd.process()
                self.m_mediator.App.add_cmd(cmd)

                self.m_mediator.set_state(0)
            return
        # change selecton EP key
        if selKey != self.m_mediator.m_selEPKey :
            self.m_mediator.m_selEPKey = selKey
            self.m_mediator.set_state(1)
    def mouse_move(self, clickX, clickY) :
        # vessel과 마우스와의 picking 수행
        # 가장 가까운 cell을 찾음
        # cell의 중심 vertex를 guideEPKey에 세팅 
        listExceptKeyType = [
            data.CData.s_skelTypeEndPoint,
            data.CData.s_skelTypeCenterline,
            CSubStateSkelEditSelectionEP.s_guideClType,
            CSubStateSkelEditSelectionEP.s_guideEPType,
            CSubStateSkelEditSelectionEP.s_guideRangeType,
            CSubStateSkelEditSelectionEP.s_guideCellType,
        ]

        dataInst = self.m_mediator.get_data()

        self.m_mediator.App.unref_key(self.m_mediator.m_guideCellKey)
        selCellID = self.m_mediator.App.picking_cellid(clickX, clickY, listExceptKeyType)
        if selCellID == -1 :
            guideCellObj = dataInst.find_obj_by_key(self.m_mediator.m_guideCellKey) 
            guideCellObj.set_cellid(None, -1)
            return
        
        clinfoInx = self.m_mediator.get_clinfo_index()
        vesselKey = data.CData.make_key(data.CData.s_vesselType, clinfoInx, 0)
        vesselObj = dataInst.find_obj_by_key(vesselKey) 
        if vesselObj is None :
            return
        
        vesselPolyData = vesselObj.PolyData
        selCell = vesselPolyData.GetCell(selCellID)
        points = selCell.GetPoints()

        cellCenter = [0.0, 0.0, 0.0]
        num_points = points.GetNumberOfPoints()
        for i in range(num_points):
            p = points.GetPoint(i)
            cellCenter[0] += p[0]
            cellCenter[1] += p[1]
            cellCenter[2] += p[2]
        
        cellCenter = [c / num_points for c in cellCenter]
        cellCenter = algLinearMath.CScoMath.to_vec3(cellCenter)

        # update
        obj = dataInst.find_obj_by_key(self.m_mediator.m_guideEPKey)
        obj.Pos = cellCenter

        weight = 0.9
        obj = dataInst.find_obj_by_key(self.m_mediator.m_guideCLKey)
        obj.process(cellCenter, weight)

        obj = dataInst.find_obj_by_key(self.m_mediator.m_guideCellKey)
        obj.set_cellid(vesselPolyData, selCellID)
        self.m_mediator.App.ref_key(self.m_mediator.m_guideCellKey)

        self.m_mediator.App.update_viewer()



class CSubStateSkelEditSelectionEP(subStateSkelEdit.CSubStateSkelEdit) :
    s_guideEPType = "guideEP" 
    s_guideClType = "guideCL"
    s_guideRangeType = "guideRange"
    s_guideCellType = "guideCell"

    s_guideColor = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
    s_guideCellColor = algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0])


    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_listState = [CSelectionEPStateNonSelection(self), CSelectionEPStateSelection(self)]
        self.m_state = 0
        self.m_newState = -1

        self.m_selEPKey = ""
        self.m_guideEPKey = ""
        self.m_guideCLKey = ""
        self.m_guideRangeKey = ""
        self.m_guideCellKey = ""
        self.m_range = 2
    def clear(self) :
        # input your code
        self.m_listState.clear()
        self.m_state = 0
        self.m_newState = -1

        self.m_selEPKey = ""
        self.m_guideEPKey = ""
        self.m_guideCLKey = ""
        self.m_guideRangeKey = ""
        self.m_guideCellKey = ""
        self.m_range = 2
        super().clear()

    def process_init(self) :
        self.m_state = 0
        opSelectionCL = self.get_operator_selection_cl()
        opSelectionCL.ChildSelectionMode = False
        opSelectionCL.ParentSelectionMode = False

        clinfoInx = self.get_clinfo_index()
        self.setui_range(self.m_range)
        self.App.ref_key_type_groupID(data.CData.s_skelTypeEndPoint, clinfoInx)
        self.get_state().init()
    def process(self) :
        pass
    def process_end(self) :
        self.get_state().clear()
        self.App.unref_key_type(data.CData.s_skelTypeEndPoint)

    def clicked_mouse_rb(self, clickX, clickY) :
        self.get_state().clicked_mouse_rb(clickX, clickY)
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        pass
    def release_mouse_rb(self) :
        pass
    def mouse_move(self, clickX, clickY) :
        self.get_state().mouse_move(clickX, clickY)
    def mouse_move_rb(self, clickX, clickY) :
        pass
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

        obj = dataInst.find_obj_by_key(self.m_guideCLKey)
        obj.Range = self.m_range
        
        self.App.update_viewer()

    # state 
    def get_state(self) -> CSelectionEPState :
        return self.m_listState[self.m_state]
    def set_state(self, newState : int) :
        self.get_state().clear()
        self.m_state = newState
        self.get_state().init()
    

    def get_data(self) -> data.CData :
        return self._get_data()
    def get_skeleton(self)  -> algSkeletonGraph.CSkeleton :
        return self._get_skeleton()
    def setui_range(self, range : int) :
        self._setui_range(range)
    def get_operator_selection_cl(self) -> operation.COperationSelectionCL :
        return self._get_operator_selection_cl()
    def get_operator_selection_ep(self) -> operation.COperationSelectionEP:
        return self._get_operator_selection_ep()
    def get_clinfo_index(self) -> int :
        return self._get_clinfo_index()
    def remove_guide_key(self) :
        if self.m_guideEPKey != "" :
            self.App.remove_key(self.m_guideEPKey)
            self.App.remove_key(self.m_guideCLKey)
            self.App.remove_key(self.m_guideRangeKey)
            self.App.remove_key(self.m_guideCellKey)

            self.m_guideEPKey = ""
            self.m_guideCLKey = ""
            self.m_guideRangeKey = ""
            self.m_guideCellKey = ""
    def ref_guide_key(self) :
        self.App.ref_key(self.m_guideEPKey)
        self.App.ref_key(self.m_guideCLKey)
        self.App.ref_key(self.m_guideRangeKey)

        dataInst = self._get_data()
        guideCellObj = dataInst.find_obj_by_key(self.m_guideCellKey)
        if guideCellObj.Ready == True :
            self.App.ref_key(self.m_guideCellKey)
    def create_guide_key(self, guideColor : np.ndarray, guideCellColor : np.ndarray) :
        dataInst = self._get_data()
        skeleton = self._get_skeleton()
        if self.m_selEPKey == "" :
            return
        
        # branch guide create
        selectedEPID = data.CData.get_id_from_key(self.m_selEPKey)
        leafCL = skeleton.get_centerline(selectedEPID)

        guideEPKey = data.CData.make_key(CSubStateSkelEditSelectionEP.s_guideEPType, 0, 0)
        guideEPObj = vtkObjGuideEP.CVTKObjGuideEP(leafCL, 0.1)
        guideEPObj.KeyType = CSubStateSkelEditSelectionEP.s_guideEPType
        guideEPObj.Key = guideEPKey
        guideEPObj.Color = guideColor
        guideEPObj.Opacity = 1.0
        dataInst.add_vtk_obj(guideEPObj)
        self.m_guideEPKey = guideEPKey

        guideCLKey = data.CData.make_key(CSubStateSkelEditSelectionEP.s_guideClType, 0, 0)
        guideCLObj = vtkObjGuideCL.CVTKObjGuideCL(leafCL, leafCL.get_end_point(), self.m_range)
        guideCLObj.KeyType = CSubStateSkelEditSelectionEP.s_guideClType
        guideCLObj.Key = guideCLKey
        guideCLObj.Color = guideColor
        guideCLObj.Opacity = 1.0
        guideCLObj.set_line_width(4.0)
        self.m_guideCLKey = guideCLKey
        dataInst.add_vtk_obj(guideCLObj)
        
        guideRangeKey = data.CData.make_key(CSubStateSkelEditSelectionEP.s_guideRangeType, 0, 0)
        guideRangeObj = vtkObjGuideRange.CVTKObjGuideRange(leafCL.get_end_point(), self.m_range)
        guideRangeObj.KeyType = CSubStateSkelEditSelectionEP.s_guideRangeType
        guideRangeObj.Key = guideRangeKey
        guideRangeObj.Color = guideColor
        guideRangeObj.Opacity = 0.5
        self.m_guideRangeKey = guideRangeKey
        dataInst.add_vtk_obj(guideRangeObj)

        guideCellKey = data.CData.make_key(CSubStateSkelEditSelectionEP.s_guideCellType, 0, 0)
        guideCellObj = vtkObjGuideCell.CVTKObjGuideCell()
        guideCellObj.KeyType = CSubStateSkelEditSelectionEP.s_guideCellType
        guideCellObj.Key = guideCellKey
        guideCellObj.Color = guideCellColor
        guideCellObj.Opacity = 1.0
        guideCellObj.set_cellid(None, -1)
        self.m_guideCellKey = guideCellKey
        dataInst.add_vtk_obj(guideCellObj)

if __name__ == '__main__' :
    pass


# print ("ok ..")

