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

import vtkObjVertex as vtkObjVertex
import vtkObjGuideEP as vtkObjGuideEP
import vtkObjGuideCL as vtkObjGuideCL
import vtkObjGuideConnect as vtkObjGuideConnect
import vtkObjGuideRange as vtkObjGuideRange
import vtkObjGuideCell as vtkObjGuideCell
from vtk.util.numpy_support import vtk_to_numpy

import data as data

import operation as operation

import command.commandInterface as commandInterface
import command.commandSkelEdit as commandSkelEdit

import subStateSkelEdit as subStateSkelEdit

class CSelectionVertexState :
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
    
class CSelectionReattachStateNonSelectionPivot(CSelectionVertexState) :
    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
    
    def init(self) :
        super().init()
        # input your code
        self.m_mediator.unref_candidate()
        self.m_mediator.unref_guide_key()
        self.m_mediator.remove_guide_key()
        self.m_mediator.remove_candidate()
        
        self.m_mediator.m_pivotVertexKey = ""
        self.m_mediator.m_pivotVertexID = ""
        
        opSelectionVertex = self.m_mediator.get_operator_selection_vertex()
        opSelectionVertex.process_reset()
        self.m_mediator.App.reset_vertex_color()
        self.m_mediator.m_lastPickedVertexId = None
        self.m_mediator.m_lastPickedVertexKey = None
        
        self.m_mediator.App.update_viewer()
    def clear(self) :
        # input your code
        super().clear()

    def clicked_mouse_rb(self, clickX, clickY) :
        listExceptKeyType = [
            data.CData.s_vesselType,
            data.CData.s_skelTypeEndPoint,
            data.CData.s_skelTypeCenterline,
            CSubStateSkelEditSelectionReAttach.s_guideRangeType,
            CSubStateSkelEditSelectionReAttach.s_guideVertexType
        ]
        selKey, vid = self.m_mediator.App.picking_point(clickX, clickY, listExceptKeyType)
        # dataInst = self._get_data()
        # if dataInst.Ready == False :
        #     return
        
        # opSelectionCL = self._get_operator_selection_cl()
        # clinfoInx = opSelectionCL.get_selection_groupID()
        # skeleton = dataInst.get_skeleton(clinfoInx)
        # cl = skeleton.
        
        # opSelectionEP = self.m_mediator.get_operator_selection_ep()
        # opSelectionCL = self.m_mediator.get_operator_selection_cl()
        # opSelectionEP.process_reset()
        # opSelectionCL.process_reset()
        # self.m_mediator.remove_guide_key()

        if selKey == "" :
            self.m_mediator.m_pivotVertexKey = ""
        else :
            self.m_mediator.m_pivotVertexKey = selKey
            self.m_mediator.m_pivotVertexID = vid
            self.m_mediator.set_state(1)
        self.m_mediator.App.update_viewer()
        
class CSelectionReattachStateNonSelectionBranch(CSelectionVertexState) :
    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
    
    def init(self) :
        super().init()
        # input your code
        self.m_mediator.m_selectedBranchKey = ""
        self.m_centerlineBranchIDList = []
        self.m_mediator.clear_candidate()
        self.m_mediator.create_guide_key(self.m_mediator.s_guideColor)
        self.m_mediator.ref_guide_key()
        
        dataInst = self.m_mediator._get_data()
        clinfoInx = data.CData.get_groupID_from_key(self.m_mediator.m_pivotVertexKey)
        skeleton = dataInst.get_skeleton(clinfoInx)
        selectedCL = skeleton.get_centerline(data.CData.get_id_from_key(self.m_mediator.m_pivotVertexKey))
        
        brCnt = skeleton.get_branch_count()
        
        for inx in range(brCnt):
            br = skeleton.get_branch(inx)
            
            if (algLinearMath.CScoMath.is_equal_vec(selectedCL.get_vertex(0), br.BranchPoint) or algLinearMath.CScoMath.is_equal_vec(selectedCL.get_vertex(-1), br.BranchPoint)):
                self.m_centerlineBranchIDList.append(br.ID)
            else:
                continue
        
        for brID in self.m_centerlineBranchIDList:
            branchKey = data.CData.make_key(data.CData.s_skelTypeBranch, clinfoInx, brID)
            self.m_mediator.App.ref_key(branchKey)

        self.m_mediator.App.update_viewer()
    def clear(self) :
        # input your code
        for clinfoInx in self.m_mediator.m_clinfoInxs:
            self.m_mediator.App.unref_key_type_groupID(data.CData.s_skelTypeBranch, clinfoInx)
        
        super().clear()

    def clicked_mouse_rb(self, clickX, clickY):
        listExceptKeyType = [
            data.CData.s_vesselType,
            data.CData.s_skelTypeEndPoint,
            data.CData.s_skelTypeCenterline,
            data.CData.s_skelTypeVertex,
            CSubStateSkelEditSelectionReAttach.s_guideRangeType,
            CSubStateSkelEditSelectionReAttach.s_guideVertexType
        ]
        selKey = self.m_mediator.App.picking(clickX, clickY, listExceptKeyType)

        if selKey == "" :
            self.m_mediator.set_state(0)
            return
        if self.m_mediator.m_pivotVertexKey == "" :
            self.m_mediator.set_state(0)
            return
        if self.m_mediator.m_pivotVertexID == "" :
            self.m_mediator.set_state(0)
            return
        
        dataInst = self.m_mediator._get_data()
        clinfoInx = data.CData.get_groupID_from_key(self.m_mediator.m_pivotVertexKey)
        skeleton = dataInst.get_skeleton(clinfoInx)
        
        selectedBrID = data.CData.get_id_from_key(selKey)
        br = skeleton.get_branch(selectedBrID)
        selectedCL = skeleton.get_centerline(data.CData.get_id_from_key(self.m_mediator.m_pivotVertexKey))
        
        if (algLinearMath.CScoMath.is_equal_vec(selectedCL.get_vertex(0), br.BranchPoint) or algLinearMath.CScoMath.is_equal_vec(selectedCL.get_vertex(-1), br.BranchPoint)):
            pass
        else:
            return
        
        cmdContainer = commandInterface.CCommandContainer(self.m_mediator.App)
        cmdContainer.InputData = dataInst
        
        cnt = br.get_conn_count()
        
        for inx in range(cnt):
            if selectedCL.ID != br.get_conn(inx).ID:
                self.m_mediator.m_targetClCandidate.add(br.get_conn(inx).ID)
        
        self.m_mediator.m_selectedBranchKey = selKey
        self.m_mediator.set_state(2)
        self.m_mediator.App.update_viewer()
        return
    
class CSelectionReAttachStateNonSelectionTarget(CSelectionVertexState) :
    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
    
    def init(self) :
        super().init()
        # input your code
        self.m_mediator.create_guide_candicate_key(self.m_mediator.s_candidateColor)
        self.m_mediator.ref_candidate()
        self.m_mediator.App.update_viewer()
    def clear(self) :
        # input your code
        super().clear()
        
        self.m_mediator.unref_candidate()
        self.m_mediator.unref_guide_key()
        self.m_mediator.remove_guide_key()
        self.m_mediator.remove_candidate()
        
        opSelectionVertex = self.m_mediator.get_operator_selection_vertex()
        opSelectionVertex.process_reset()
        self.m_mediator.App.reset_vertex_color()
        self.m_mediator.m_lastPickedVertexId = None
        self.m_mediator.m_lastPickedVertexKey = None

    def clicked_mouse_rb(self, clickX, clickY) :
        listExceptKeyType = [
            data.CData.s_vesselType,
            data.CData.s_skelTypeEndPoint,
            data.CData.s_skelTypeCenterline,
            data.CData.s_skelTypeVertex,
            CSubStateSkelEditSelectionReAttach.s_guideRangeType,
            CSubStateSkelEditSelectionReAttach.s_guideVertexType
        ]
        selKey, vid = self.m_mediator.App.picking_point(clickX, clickY, listExceptKeyType)

        if selKey == "" :
            self.m_mediator.set_state(0)
            return
        if self.m_mediator.m_pivotVertexKey == "" :
            self.m_mediator.set_state(0)
            return
        if self.m_mediator.m_pivotVertexID == "" :
            self.m_mediator.set_state(0)
            return
        
        dataInst = self.m_mediator._get_data()
        cmdContainer = commandInterface.CCommandContainer(self.m_mediator.App)
        cmdContainer.InputData = dataInst

        ##/////////////////////////////////////////////////////////
        cmd = commandSkelEdit.CCommandReAttach(self.m_mediator.App)
        cmd.InputData= dataInst
        cmd.PivotVertexKey = self.m_mediator.m_pivotVertexKey
        cmd.PiviotVertexID = self.m_mediator.m_pivotVertexID
        cmd.NewBranchVertexKey = selKey
        cmd.NewBranchVertexID = vid
        cmd.m_selectedBranchKey = self.m_mediator.m_selectedBranchKey
        cmd.m_numOfConnCl = len(self.m_mediator.m_targetClCandidate) + 1

        cmdContainer.add_cmd(cmd)
        cmdContainer.process()
        self.m_mediator.App.add_cmd(cmdContainer)


        groupID = data.CData.get_groupID_from_key(self.m_mediator.m_pivotVertexKey)
        self.m_mediator.App.unref_key_type(data.CData.s_skelTypeVertex)
        self.m_mediator.App.ref_key_type_groupID(data.CData.s_skelTypeVertex, groupID)
        
        self.m_mediator.App.update_viewer()
        self.m_mediator.set_state(0)
    


    def save_vertices_as_spheres_stl(self, vertices: np.ndarray,
                                    out_path: str) -> None:
        """
        vertices: (N, 3) numpy 배열
        radius: 각 vertex에 만들 구의 반지름
        out_path: 저장할 stl 경로
        """
        radius = 0.2
        # 혹시 (3,) 들어오면 한 점만 있다고 보고 형식 맞춰주기
        vertices = np.asarray(vertices)
        if vertices.ndim == 1:
            vertices = vertices.reshape(1, 3)

        append = vtk.vtkAppendPolyData()

        for p in vertices:
            sphere = vtk.vtkSphereSource()
            sphere.SetCenter(float(p[0]), float(p[1]), float(p[2]))
            sphere.SetRadius(float(radius))
            sphere.SetPhiResolution(16)
            sphere.SetThetaResolution(16)
            sphere.Update()

            append.AddInputData(sphere.GetOutput())

        append.Update()

        # 여러 polydata 합치면 중복점 생길 수 있으니 한 번 정리
        clean = vtk.vtkCleanPolyData()
        clean.SetInputData(append.GetOutput())
        clean.Update()

        writer = vtk.vtkSTLWriter()
        writer.SetFileName(out_path)
        writer.SetInputData(clean.GetOutput())
        writer.SetFileTypeToBinary()
        writer.Write()
    # -----------------------------------------------
    
    
        
    def mouse_move(self, clickX, clickY) :
        # vessel과 마우스와의 picking 수행
        # 가장 가까운 cell을 찾음
        # cell의 중심 vertex를 guideEPKey에 세팅 
        listExceptKeyType = [
            data.CData.s_vesselType,
            data.CData.s_skelTypeEndPoint,
            data.CData.s_skelTypeCenterline,
            data.CData.s_skelTypeVertex,
            CSubStateSkelEditSelectionReAttach.s_guideRangeType,
            CSubStateSkelEditSelectionReAttach.s_guideVertexType
        ]

        dataInst = self.m_mediator.get_data()
        selKey, vid = self.m_mediator.App.picking_point(clickX, clickY, listExceptKeyType, self.m_mediator.s_candidateColor)
        
        if selKey == None or vid == None:
            return
        else:
            pass
        
        clinfoInx = data.CData.get_groupID_from_key(selKey)
        cl_vertices_obj = dataInst.find_obj_by_key(selKey) 
        if cl_vertices_obj is None :
            return
        
        if cl_vertices_obj.PolyData is None:
            return
        
        pts = cl_vertices_obj.PolyData.GetPoints()
        if pts is None :
            return
            
        npts = pts.GetNumberOfPoints()
        if npts == 0:
            return None

        point_id = None
        arr = cl_vertices_obj.PolyData.GetPointData().GetArray("VertexID")
        if arr is not None and arr.GetNumberOfTuples() == npts:
            try:
                ids = vtk_to_numpy(arr)
                hit = np.where(ids == vid)[0]
                if hit.size > 0:
                    point_id = int(hit[0])
            except Exception:
                point_id = None

        if point_id is None:
            if 0 <= vid < npts:
                point_id = vid
            else:
                return None

        x, y, z = pts.GetPoint(point_id)
        
        targetPoint = algLinearMath.CScoMath.to_vec3([x, y, z])

        obj = dataInst.find_obj_by_key(self.m_mediator.m_guideVertexKey)
        obj.process(targetPoint)
        
        self.m_mediator.App.update_viewer()



class CSubStateSkelEditSelectionReAttach(subStateSkelEdit.CSubStateSkelEdit) :
    s_guideVertexType = "guideVertex"
    s_guideRangeType = "guideRange"
    s_guideCandidateType = "guideCandidate"
    
    s_guideColor = algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0])
    s_candidateColor = algLinearMath.CScoMath.to_vec3([1.0, 0.85, 0.35])


    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_listState = [CSelectionReattachStateNonSelectionPivot(self), CSelectionReattachStateNonSelectionBranch(self), CSelectionReAttachStateNonSelectionTarget(self)]
        self.m_state = 0
        self.m_newState = -1
        self.m_pivotVertexKey = ""
        self.m_pivotVertexID = ""
        
        self.m_selectedBranchKey = ""
        self.m_secondSelectedVertexID = ""
        self.m_targetClCandidate = set()
        self.m_clinfoInxs = []

        self.m_guideVertexKey = ""
        self.m_guideRangeKey = ""
        self.m_range = 0.6
    def clear(self) :
        # input your code
        self.m_listState.clear()
        self.unref_candidate()
        self.unref_guide_key()
        self.remove_guide_key()
        self.remove_candidate()
        
        self.m_state = 0
        self.m_newState = -1
        self.m_pivotVertexKey = ""
        self.m_pivotVertexID = ""
        
        self.m_selectedBranchKey = ""
        self.m_secondSelectedVertexID = ""
        self.m_targetClCandidate = set()
        self.m_clinfoInxs = []
        self.m_guideVertexKey = ""
        self.m_guideRangeKey = ""
        self.m_range = 0.6
        super().clear()

    def process_init(self) :
        self.m_state = 0
        opSelectionCL = self.get_operator_selection_cl()
        opSelectionCL.ChildSelectionMode = False
        opSelectionCL.ParentSelectionMode = False

        clinfoInxs = self.get_clinfo_indices()
        self.m_clinfoInxs = clinfoInxs
        
        self.App.unref_key_type(data.CData.s_skelTypeCenterline)
        self.App.unref_key_type(self.m_mediator.s_rootPointType)
        for clinfoInx in clinfoInxs:
            self.App.ref_key_type_groupID(data.CData.s_skelTypeVertex, clinfoInx)
        
        self.get_state().init()
        #
        #self.App.update_viewer()
    def process(self) :
        pass
    def process_end(self) :
        self.get_state().clear()
        clinfoInxs = self.get_clinfo_indices()
        self.unref_candidate()
        self.unref_guide_key()
        self.remove_guide_key()
        self.remove_candidate()
        opSelectionVertex = self.get_operator_selection_vertex()
        opSelectionVertex.process_reset()
        self.App.reset_vertex_color()
        self.App.m_lastPickedVertexId = None
        self.App.m_lastPickedVertexKey = None
        self.App.unref_key_type(data.CData.s_skelTypeVertex)
        for clinfoInx in clinfoInxs:
            self.App.ref_key_type_groupID(data.CData.s_skelTypeCenterline, clinfoInx)
            self.App.ref_key_type_groupID(self.m_mediator.s_rootPointType, clinfoInx)

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
            self.App.undo(5)
        if keyCode == "r" :
            self.App.redo()
            
    @property
    def PivotVertexKey(self):
        return self.m_pivotVertexKey
    @PivotVertexKey.setter
    def PivotVertexKey(self, pivotVertexKey):
        self.m_pivotVertexKey = pivotVertexKey
    @property
    def PivotVertexID(self):
        return self.m_pivotVertexID
    @PivotVertexID.setter
    def PivotVertexID(self, pivotVertexID):
        self.m_pivotVertexID = pivotVertexID
    @property
    def SelectedBranchKey(self):
        return self.m_selectedBranchKey
    @SelectedBranchKey.setter
    def SelectedBranchKey(self, selectedBranchKey):
        self.m_selectedBranchKey = selectedBranchKey
    @property
    def SecondVertexID(self):
        return self.m_secondSelectedVertexID
    @SecondVertexID.setter
    def SecondVertexID(self, secondVertexID):
        self.m_secondSelectedVertexID = secondVertexID

    # state 
    def get_state(self) -> CSelectionVertexState :
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
    def get_operator_selection_vertex(self) -> operation.COperationSelectionVertex:
        return self._get_operator_selection_vertex()
    def get_clinfo_index(self) -> int :
        return self._get_clinfo_index()
    def get_clinfo_indices(self) -> int :
        return self._get_clinfo_indices()
    
    def ref_candidate(self):
        self.App.ref_key_type(self.s_guideCandidateType)
        
    def remove_candidate(self):
        self.App.remove_key_type(self.s_guideCandidateType)
    
    def ref_guide_key(self) :
        self.App.ref_key(self.m_guideRangeKey)
        self.App.ref_key(self.m_guideVertexKey)
        
        
    def remove_guide_key(self) :
        if self.m_guideVertexKey != "" :
            self.App.remove_key(self.m_guideVertexKey)
            self.App.remove_key(self.m_guideRangeKey)

            self.m_guideVertexKey = ""
            self.m_guideRangeKey = ""
            
    def unref_guide_key(self) :
        self.App.unref_key(self.m_guideRangeKey)
        self.App.unref_key(self.m_guideVertexKey)
        
    def unref_candidate(self):
        self.App.unref_key_type(self.s_guideCandidateType)
        
    def clear_candidate(self):
        self.m_targetClCandidate.clear()
        
    def create_guide_key(self, guideColor : np.ndarray) :
        dataInst = self._get_data()

        if self.m_pivotVertexKey == "" :
            return
        if self.m_pivotVertexID == "" :
            return

        # branch guide create
        selectedCLID = data.CData.get_id_from_key(self.m_pivotVertexKey)
        selectedGroupID = data.CData.get_groupID_from_key(self.m_pivotVertexKey)
        
        skeleton = dataInst.get_skeleton(selectedGroupID)
        selectedCL = skeleton.get_centerline(selectedCLID)
        
        guideVertexKey = data.CData.make_key(CSubStateSkelEditSelectionReAttach.s_guideVertexType, 0, 0)
        guideVertexObj = vtkObjGuideConnect.CVTKObjGuideConnect(selectedCL, selectedCL.get_vertex(self.m_pivotVertexID), self.m_range)
        guideVertexObj.KeyType = CSubStateSkelEditSelectionReAttach.s_guideVertexType
        guideVertexObj.Key = guideVertexKey
        guideVertexObj.Color = guideColor
        guideVertexObj.Opacity = 1.0
        guideVertexObj.set_line_width(4.0)
        self.m_guideVertexKey = guideVertexKey
        dataInst.add_vtk_obj(guideVertexObj)
        
        guideRangeKey = data.CData.make_key(CSubStateSkelEditSelectionReAttach.s_guideRangeType, 0, 0)
        guideRangeObj = vtkObjGuideRange.CVTKObjGuideRange(selectedCL.get_vertex(self.m_pivotVertexID), self.m_range)
        guideRangeObj.KeyType = CSubStateSkelEditSelectionReAttach.s_guideRangeType
        guideRangeObj.Key = guideRangeKey
        guideRangeObj.Color = guideColor
        guideRangeObj.Opacity = 1.0
        self.m_guideRangeKey = guideRangeKey
        dataInst.add_vtk_obj(guideRangeObj)
        
    def create_guide_candicate_key(self, guideColor : np.ndarray):
        
        if self.m_pivotVertexKey == "":
            return
        
        if len(self.m_targetClCandidate) == 0:
            return
        
        dataInst = self._get_data()
        clinfoInx = data.CData.get_groupID_from_key(self.m_pivotVertexKey)
        skeleton = dataInst.get_skeleton(clinfoInx)
        
        
        for clInx in self.m_targetClCandidate:
            skeletonCL = skeleton.get_centerline(clInx)
            vertexObj = vtkObjVertex.CVTKObjVertex(skeletonCL, self.m_range , guideColor.flatten())
            if vertexObj.Ready == False :
                continue
            
            vertexObj.KeyType = self.s_guideCandidateType
            vertexObj.Key = data.CData.make_key(vertexObj.KeyType, clinfoInx, skeletonCL.ID)
            #vertexObj.Color = dataInst.VertexColor
            vertexObj.Opacity = 1.0
            vertexObj.Visibility = True
            dataInst.add_vtk_obj(vertexObj)
        
        

if __name__ == '__main__' :
    pass


# print ("ok ..")


