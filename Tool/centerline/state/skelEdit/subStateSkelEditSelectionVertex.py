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
import vtkObjGuideNearVertex as vtkObjGuideNearVertex
import vtkObjGuideVertex as vtkObjGuideVertex
import vtkObjGuideRange as vtkObjGuideRange
import vtkObjGuideCell as vtkObjGuideCell
from vtk.util.numpy_support import vtk_to_numpy

import data as data

import operation as operation

import command.commandInterface as commandInterface
import command.commandSkelEdit as commandSkelEdit

import subStateSkelEdit as subStateSkelEdit
import vtkObjVertex as vtkObjVertex


class CSubStateSkelEditSelectionVertex(subStateSkelEdit.CSubStateSkelEdit) :
    s_guideVertexType = "guideVertex"
    s_guideClType = "guideCL"
    s_guideRangeType = "guideRange"
    
    s_guideColor = algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0])


    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_selVertexKey = ""
        self.m_selVertexID = -1
        
        self.m_guideVertexKey = ""
        self.m_listGuideNearVertexKey = []
        self.m_guideRangeKey = ""
        self.m_anchorX = 0
        self.m_anchorY = 0
        self.m_anchorPos = None
        self.m_range = 2
    def clear(self) :
        # input your code
        self.m_selVertexKey = ""
        self.m_selVertexID = -1
        self.m_guideVertexKey = ""
        self.m_listGuideNearVertexKey.clear()
        self.m_guideRangeKey = ""
        self.m_anchorX = 0
        self.m_anchorY = 0
        self.m_anchorPos = None
        self.m_range = 2
        super().clear()

    def process_init(self) :
        self.m_state = 0
        opSelectionCL = self.get_operator_selection_cl()
        opSelectionCL.ChildSelectionMode = False
        opSelectionCL.ParentSelectionMode = False

        clinfoInxs = self.get_clinfo_indices()
        
        self.App.unref_key_type(data.CData.s_skelTypeCenterline)
        self.App.unref_key_type(self.m_mediator.s_rootPointType)
        for clinfoInx in clinfoInxs:
            self.App.ref_key_type_groupID(data.CData.s_skelTypeVertex, clinfoInx)
        
        #
        self._setui_vertex_range(self.m_range)
        self.App.update_viewer()
    def process(self) :
        pass
    def process_end(self) :
        self._remove_guide_key()
        clinfoInxs = self.get_clinfo_indices()
        self.App.unref_key_type(data.CData.s_skelTypeVertex)
        for clinfoInx in clinfoInxs:
            self.App.ref_key_type_groupID(data.CData.s_skelTypeCenterline, clinfoInx)
            self.App.ref_key_type_groupID(self.m_mediator.s_rootPointType, clinfoInx)

    def clicked_mouse_rb(self, clickX, clickY) :
        if self.m_selVertexKey == "" :
            listExceptKeyType = [
                data.CData.s_vesselType,
                data.CData.s_skelTypeEndPoint,
                data.CData.s_skelTypeCenterline,
                CSubStateSkelEditSelectionVertex.s_guideRangeType,
                CSubStateSkelEditSelectionVertex.s_guideVertexType
            ]
            selKey, vid = self.App.picking_point(clickX, clickY, listExceptKeyType)

            # opSelectionBr = self._get_operator_selection_br()
            # opSelectionCL = self._get_operator_selection_cl()
            # opSelectionBr.process_reset()
            # opSelectionCL.process_reset()
            # self._remove_guide_key()
            
            self._remove_guide_key()

            if selKey == "" :
                self.m_selVertexKey = ""
                self.m_selVertexID = -1
            else :
                
                self.m_selVertexKey = selKey
                self.m_selVertexID = vid
                self._create_guide_key(algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0]))
                self._ref_guide_key()
                
                dataInst = self._get_data()
                dataInst.CLInfoIndex = data.CData.get_groupID_from_key(self.m_selVertexKey)
                
                skelinfo = dataInst.get_skelinfo(dataInst.CLInfoIndex)
                skeleton = skelinfo.Skeleton            
                skeletonCL = skeleton.get_centerline(data.CData.get_id_from_key(self.m_selVertexKey))
                    
                self.m_anchorX = clickX
                self.m_anchorY = clickY
                
                self.m_anchorPos = skeletonCL.get_vertex(self.m_selVertexID)
                
                for bi in range(skeleton.get_branch_count()):
                    if algLinearMath.CScoMath.is_equal_vec(skeleton.get_branch(bi).BranchPoint, self.m_anchorPos) == True:
                        
                        self.App.highlight_vertex_by_actor_and_id(self.App.m_lastPickedVertexKey, self.App.m_lastPickedVertexId, dataInst.s_vertexColor.flatten())
                        
                        self.App.m_lastPickedVertexId = self.m_selVertexID
                        self.App.m_lastPickedVertexKey = self.m_selVertexKey
                        
                        self._remove_guide_key()

                        self.m_selVertexKey = ""
                        self.m_selVertexID = -1
                        self.App.update_viewer()
                        return
        
        else:
            listExceptKeyType = [
                data.CData.s_vesselType,
                data.CData.s_skelTypeEndPoint,
                data.CData.s_skelTypeCenterline,
                CSubStateSkelEditSelectionVertex.s_guideRangeType,
                CSubStateSkelEditSelectionVertex.s_guideVertexType
            ]
            selKey, vid = self.App.picking_point(clickX, clickY, listExceptKeyType)

            if selKey == "" :
                self._remove_guide_key()

                self.m_selVertexKey = ""
                self.m_selVertexID = -1
                self.App.update_viewer()
                return
            else :
                self.m_selVertexKey = selKey
                self.m_selVertexID = vid
                self._remove_guide_key()
                self._create_guide_key(algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0]))
                self._ref_guide_key()
                
            dataInst = self._get_data()
            dataInst.CLInfoIndex = data.CData.get_groupID_from_key(self.m_selVertexKey)
            obj = dataInst.find_obj_by_key(self.m_guideVertexKey)
            self.m_anchorX = clickX
            self.m_anchorY = clickY
            self.m_anchorPos = obj.Pos.copy()

                
        self.App.update_viewer()
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        pass
    def release_mouse_rb(self) :
        if self.m_selVertexKey != "" :
            dataInst = self._get_data()
            groupID = data.CData.get_groupID_from_key(self.m_selVertexKey)
            skelinfo = dataInst.get_skelinfo(groupID)
            skeleton = skelinfo.Skeleton            
            skeletonCL = skeleton.get_centerline(data.CData.get_id_from_key(self.m_selVertexKey))
            guideVertex = dataInst.find_obj_by_key(self.m_guideVertexKey)
            
            if algLinearMath.CScoMath.is_equal_vec(self.m_anchorPos, guideVertex.Pos) == False :
                cmdContainer = commandInterface.CCommandContainer(self.App)
                cmdContainer.InputData = dataInst
                
                leftGuideCL = dataInst.find_obj_by_key(self.m_listGuideNearVertexKey[0])
                rightGuideCL = dataInst.find_obj_by_key(self.m_listGuideNearVertexKey[1])

                ModifiedVertex = np.concatenate((leftGuideCL.ModifiedVertex, rightGuideCL.ModifiedVertex[1:]))
                ModifiedRadius = np.concatenate((leftGuideCL.ModifiedRadius, rightGuideCL.ModifiedRadius[1:]))

                cmd = commandSkelEdit.CCommandUpdateCL(self.App)
                cmd.InputData = dataInst
                cmd.InputSkeleton = skeleton
                cmd.InputCLID = skeletonCL.ID
                cmd.InputVertex = ModifiedVertex
                cmd.InputRadius = ModifiedRadius
                cmd.InputMinInx = leftGuideCL.m_minInx
                cmd.InputEndInx = rightGuideCL.m_endInx
                cmd.SelectedGroupID = skelinfo
                cmdContainer.add_cmd(cmd)
            
                cmdContainer.process()
                self.App.add_cmd(cmdContainer)
            
                self._remove_guide_key()
                self.m_selVertexKey = ""
                self.m_selVertexID = -1
                #self.App.ref_key(self.m_selVertexKey)
                
                self.App.update_viewer()
                
            
    def mouse_move_rb(self, clickX, clickY) :
        if self.m_selVertexKey == "" :
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
        obj = dataInst.find_obj_by_key(self.m_guideVertexKey) #m_guideVertexKey
        
        moveVec = self.m_anchorPos + moveVec
        obj.Pos = np.array(moveVec)

        weight = 0.9
        for key in self.m_listGuideNearVertexKey :
            obj = dataInst.find_obj_by_key(key)
            obj.process(moveVec, weight)

        self.App.update_viewer()
    def key_press_with_ctrl(self, keyCode : str) :
        if keyCode == "z" :
            self.App.undo(3)
        if keyCode == "r" :
            self.App.redo()
            
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
    def get_operator_selection_vertex(self) -> operation.COperationSelectionVertex:
        return self._get_operator_selection_vertex()
    def get_clinfo_index(self) -> int :
        return self._get_clinfo_index()
    def get_clinfo_indices(self) -> int :
        return self._get_clinfo_indices()
    
    def change_range(self, range : int) :
        self.m_range = range
        if self.m_guideRangeKey == "" :
            return
        dataInst = self._get_data()
        obj = dataInst.find_obj_by_key(self.m_guideRangeKey)
        obj.Range = self.m_range

        for guideCLKey in self.m_listGuideNearVertexKey :
            obj = dataInst.find_obj_by_key(guideCLKey)
            obj.Range = self.m_range
        
        self.App.update_viewer()
    
    def _ref_guide_key(self) :
        self.App.ref_key(self.m_guideRangeKey)
        self.App.ref_key(self.m_guideVertexKey)
        for gcl in self.m_listGuideNearVertexKey:
            self.App.ref_key(gcl)
        
    def _remove_guide_key(self) :
        if self.m_selVertexKey != "" :
            self.App.remove_key(self.m_guideVertexKey)
            self.App.remove_key(self.m_guideRangeKey)
            
            for guideKey in self.m_listGuideNearVertexKey :
                self.App.remove_key(guideKey)

            self.m_guideVertexKey = ""
            self.m_guideRangeKey = ""
    def _create_guide_key(self, guideColor : np.ndarray) :
        dataInst = self._get_data()

        if self.m_selVertexKey == "":
            return
        
        # branch guide create
        selectedCLID = data.CData.get_id_from_key(self.m_selVertexKey)
        selectedGroupID = data.CData.get_groupID_from_key(self.m_selVertexKey)
        
        skeleton = dataInst.get_skeleton(selectedGroupID)
        selectedCL = skeleton.get_centerline(selectedCLID)
        
        guideVertexKey = data.CData.make_key(CSubStateSkelEditSelectionVertex.s_guideVertexType, selectedGroupID, 0)
        guideVertexObj = vtkObjGuideVertex.CVTKObjGuideVertex(selectedCL.get_vertex(self.m_selVertexID), dataInst.BrSize)
        guideVertexObj.KeyType = CSubStateSkelEditSelectionVertex.s_guideVertexType
        guideVertexObj.Key = guideVertexKey
        guideVertexObj.Color = guideColor
        guideVertexObj.Opacity = 0.5
        self.m_guideVertexKey = guideVertexKey
        dataInst.add_vtk_obj(guideVertexObj)
        
        guideRangeKey = data.CData.make_key(CSubStateSkelEditSelectionVertex.s_guideRangeType, selectedGroupID, 0)
        guideRangeObj = vtkObjGuideRange.CVTKObjGuideRange(selectedCL.get_vertex(self.m_selVertexID), self.m_range)
        guideRangeObj.KeyType = CSubStateSkelEditSelectionVertex.s_guideRangeType
        guideRangeObj.Key = guideRangeKey
        guideRangeObj.Color = guideColor
        guideRangeObj.Opacity = 0.5
        self.m_guideRangeKey = guideRangeKey
        dataInst.add_vtk_obj(guideRangeObj)
        
        
        for i, state in enumerate(["left", "right"]):
            guideKey = data.CData.make_key(CSubStateSkelEditSelectionVertex.s_guideClType, selectedGroupID, i)
            guideObj = vtkObjGuideNearVertex.CVTKObjGuideNearVertex(selectedCL, selectedCL.get_vertex(self.m_selVertexID), self.m_range, state)
            guideObj.KeyType = CSubStateSkelEditSelectionVertex.s_guideClType
            guideObj.Key = guideKey
            guideObj.Color = guideColor
            guideObj.Opacity = 1.0
            guideObj.set_line_width(4.0)
            self.m_listGuideNearVertexKey.append(guideKey)
            dataInst.add_vtk_obj(guideObj)
        

if __name__ == '__main__' :
    pass


# print ("ok ..")



