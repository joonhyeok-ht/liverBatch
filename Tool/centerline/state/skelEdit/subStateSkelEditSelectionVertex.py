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
import vtkObjGuideVertex as vtkObjGuideVertex
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
class CSelectionVertexStateNonSelection(CSelectionVertexState) :
    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
    
    def init(self) :
        super().init()
        # input your code
        self.m_mediator.m_selVertexKey = ""
        self.m_mediator.App.update_viewer()
    def clear(self) :
        # input your code
        super().clear()


    def clicked_mouse_rb(self, clickX, clickY) :
        listExceptKeyType = [
            data.CData.s_vesselType,
            data.CData.s_skelTypeEndPoint,
            data.CData.s_skelTypeCenterline,
            CSubStateSkelEditSelectionVertex.s_guideRangeType,
            CSubStateSkelEditSelectionVertex.s_guideVertexType
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
            self.m_mediator.m_selVertexKey = ""
        else :
            self.m_mediator.m_firstSelectedVertexkey = selKey
            self.m_mediator.m_firstSelectedVertexID = vid
                
            self.m_mediator.m_selVertexKey = selKey
            self.m_mediator.set_state(1)
        self.m_mediator.App.update_viewer()
class CSelectionVertexStateSelection(CSelectionVertexState) :
    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
    
    def init(self) :
        super().init()
        # input your code
        self.m_mediator.create_guide_key(self.m_mediator.s_guideColor)
        self.m_mediator.ref_guide_key()

        self.m_mediator.App.update_viewer()
    def clear(self) :
        # input your code
        opSelectionVertex = self.m_mediator.get_operator_selection_vertex()
        opSelectionVertex.process_reset()
        self.m_mediator.App.reset_vertex_color()
        self.m_mediator.m_lastPickedVertexId = None
        self.m_mediator.m_lastPickedVertexKey = None
        self.m_mediator.remove_guide_key()
        super().clear()
        
    def split_centerline(self, skeleton, centerline, splitVertexInx):
        
        splitCenterlineID = centerline.ID
        
        #range_cl = range(len(skeleton.m_listCenterline))
        
        tempCenterline1 = algSkeletonGraph.CSkeletonCenterline(splitCenterlineID)
        tempCenterline1.Name = skeleton.m_listCenterline[splitCenterlineID].Name
        tempCenterline1.Vertex = skeleton.m_listCenterline[splitCenterlineID].Vertex[:splitVertexInx+1].copy()
        tempCenterline1.Radius = skeleton.m_listCenterline[splitCenterlineID].Radius[:splitVertexInx+1].copy()
        tempCenterline2 = algSkeletonGraph.CSkeletonCenterline(len(skeleton.m_listCenterline))
        tempCenterline2.Name = skeleton.m_listCenterline[splitCenterlineID].Name
        tempCenterline2.Vertex = skeleton.m_listCenterline[splitCenterlineID].Vertex[splitVertexInx:].copy()
        tempCenterline2.Radius = skeleton.m_listCenterline[splitCenterlineID].Radius[splitVertexInx:].copy()
        
        skeleton.m_listCenterline[splitCenterlineID] = tempCenterline1
        skeleton.m_listCenterline.append(tempCenterline2)
        
        
        # for inx in range_cl:
        #     if skeleton.m_listCenterline[inx].ID == splitCenterlineID:
        #         tempCenterline1 = algSkeletonGraph.CSkeletonCenterline(inx)
        #         tempCenterline1.Name = skeleton.m_listCenterline[inx].Name
        #         tempCenterline1.Vertex = skeleton.m_listCenterline[inx].Vertex[:splitVertexInx].copy()
        #         tempCenterline1.Radius = skeleton.m_listCenterline[inx].Radius[:splitVertexInx].copy()
        #         tempCenterline2 = algSkeletonGraph.CSkeletonCenterline(len(skeleton.m_listCenterline))
        #         tempCenterline2.Name = skeleton.m_listCenterline[inx].Name
        #         tempCenterline2.Vertex = skeleton.m_listCenterline[inx].Vertex[splitVertexInx:].copy()
        #         tempCenterline2.Radius = skeleton.m_listCenterline[inx].Radius[splitVertexInx:].copy()
                
        #         skeleton.m_listCenterline[inx] = tempCenterline1
        #         skeleton.m_listCenterline.append(tempCenterline2)
                
                # self.save_vertices_as_spheres_stl(tempCenterline1.Vertex, f"C:/Users/hutom/Desktop/jh_test/data/test/{centerline.ID}_1.stl")
                # self.save_vertices_as_spheres_stl(tempCenterline2.Vertex, f"C:/Users/hutom/Desktop/jh_test/data/test/{centerline.ID}_2.stl")
                
                # if inx < len(skeleton.m_listCenterline):
                #     skeleton.m_listCenterline[inx+1] = tempCenterline2
                # elif inx == len(skeleton.m_listCenterline):
            #     skeleton.m_listCenterline.append(tempCenterline2)
            # elif inx > splitCenterlineID:
            #     skeleton.m_listCenterline[inx].ID = skeleton.m_listCenterline[inx].ID + 1

        return
    
    def rebuild_skeleton(self, skeleton):               
        for i, centerline in enumerate(skeleton.ListCenterline) :
            skeleton.init_conn_centerline(centerline) #__init_conn_centerline
        # leaf centerline
        skeleton.extract_leaf_centerline()

        skeleton.build_graph()
        skeleton.build_kd_tree()
        if skeleton.m_rootCenterline != -1 :
            skeleton.build_tree(skeleton.m_rootCenterline.ID)
        return
        


    def clicked_mouse_rb(self, clickX, clickY):
        listExceptKeyType = [
            data.CData.s_vesselType,
            data.CData.s_skelTypeEndPoint,
            data.CData.s_skelTypeCenterline,
            CSubStateSkelEditSelectionVertex.s_guideRangeType,
            CSubStateSkelEditSelectionVertex.s_guideVertexType
        ]
        selKey, vid = self.m_mediator.App.picking_point(clickX, clickY, listExceptKeyType)

        if selKey == "" :
            self.m_mediator.set_state(0)
            return
        if self.m_mediator.m_firstSelectedVertexkey == "" :
            self.m_mediator.set_state(0)
            return
        if self.m_mediator.m_firstSelectedVertexID == "" :
            self.m_mediator.set_state(0)
            return
        
        
        dataInst = self.m_mediator._get_data()
        
        firstGroupID = data.CData.get_groupID_from_key(self.m_mediator.m_firstSelectedVertexkey)
        firstSkeleton = dataInst.get_skeleton(firstGroupID)
        firstSelectedCLID = data.CData.get_id_from_key(self.m_mediator.m_firstSelectedVertexkey)
        firstSelectedCL = firstSkeleton.get_centerline(firstSelectedCLID)
        firstV = firstSelectedCL.get_vertex(self.m_mediator.m_firstSelectedVertexID)
        firstR = firstSelectedCL.get_radius(self.m_mediator.m_firstSelectedVertexID)
        
        secondGroupID = data.CData.get_groupID_from_key(selKey)
        secondSkeleton = dataInst.get_skeleton(secondGroupID)
        secondSelectedCLID = data.CData.get_id_from_key(selKey)
        secondSelectedCL = secondSkeleton.get_centerline(secondSelectedCLID)
        secondV = secondSelectedCL.get_vertex(vid)
        secondR = secondSelectedCL.get_radius(vid)
        
        if firstGroupID == secondGroupID and firstSelectedCLID == secondSelectedCLID:
            self.m_mediator.set_state(0)
            return 
        
        firstVNeedSplitCenterline = True
        secondVNeedSplitCenterline = True
        '''
        fitstV나 secondV가 branch 혹은 ep 가 아니면 cl를 분리해야 함. 
        '''
        
        if firstSelectedCL.get_conn_inx(firstV) != -1:
            firstVNeedSplitCenterline = False
            
        if secondSelectedCL.get_conn_inx(secondV) != -1:
            secondVNeedSplitCenterline = False
        
        for bi in range(firstSkeleton.get_branch_count()):
            if algLinearMath.CScoMath.is_equal_vec(firstSkeleton.get_branch(bi).BranchPoint, firstV) == True:
                firstVNeedSplitCenterline = False
                
        for bi in range(secondSkeleton.get_branch_count()):
            if algLinearMath.CScoMath.is_equal_vec(secondSkeleton.get_branch(bi).BranchPoint, secondV) == True:
                secondVNeedSplitCenterline = False
        
        refinedVertex = np.concatenate((firstV, secondV), axis=0)
        
        refinedRadius = np.array([firstR, secondR])
        refinedRadius = commandSkelEdit.CCommandSkelEdit.resample_radius(refinedVertex, refinedRadius)
        refinedVertex = commandSkelEdit.CCommandSkelEdit.resample_points(refinedVertex)
        #print(f"resampled refinedVertex shape : {refinedVertex.shape}", file=sys.__stdout__,flush=True)
        
        
        bridgeCLID = len(firstSkeleton.m_listCenterline) + len(secondSkeleton.m_listCenterline)
        bridgeCenterline = algSkeletonGraph.CSkeletonCenterline(bridgeCLID)
        bridgeCenterline.Name = firstSelectedCL.Name
        bridgeCenterline.Vertex = refinedVertex
        bridgeCenterline.Radius = refinedRadius
        
        #skeleton.m_listCenterline.append(bridgeCenterline)
        #skeleton.merge_and_rebuild_centerline(bridgeCenterline)
        
        '''
        firstVNeedSplitCenterline 와 secondVNeedSplitCenterline 에 따라서 firstCL과 secondCL을 나눠야할 지 말지 정해야 함.
        그리고 나눈 후에 bridge Centerline과 기존의 centerline list 와 합쳐서 skeleton을 다시 build 해야 함
        '''
        
        if firstVNeedSplitCenterline:
            self.split_centerline(firstSkeleton, firstSelectedCL, int(self.m_mediator.m_firstSelectedVertexID))
            
        if secondVNeedSplitCenterline:
            self.split_centerline(secondSkeleton, secondSelectedCL, int(vid))
        
        mergedskeleton = self.merge_centerline(secondSkeleton, firstSkeleton, bridgeCenterline)
        
        ################### 임시로 첫번째 group ID로 덮어씌워서테스트 ########################
        dataInst.m_listSkelInfo[firstGroupID].Skeleton = mergedskeleton
        self.m_mediator.m_mediator.m_mediator.add_skeleton_obj(firstGroupID)
        
        # #dataInst = self.m_mediator.get_data()
        self.m_mediator.App.unref_key_type(data.CData.s_skelTypeCenterline)
        self.m_mediator.App.unref_key_type(data.CData.s_skelTypeVertex)
        self.m_mediator.App.ref_key_type_groupID(data.CData.s_skelTypeVertex, firstGroupID)
        
        self.m_mediator.App.update_viewer()
        self.m_mediator.set_state(0)

        return
    
    def merge_centerline(self, srcSkeleton, tgtSkeleton, bridgeCenterline):
        mergedskeleton = algSkeletonGraph.CSkeleton()
        
        rootcenterlineID = 0
        for centerline in tgtSkeleton.m_listCenterline:
            _centerline = algSkeletonGraph.CSkeletonCenterline(len(mergedskeleton.m_listCenterline))
            _centerline.Name = centerline.Name
            _centerline.Vertex = centerline.Vertex.copy()
            _centerline.Radius = centerline.Radius.copy()
            mergedskeleton.m_listCenterline.append(_centerline)
            if tgtSkeleton.m_rootCenterline.ID == centerline.ID:
                rootcenterlineID = _centerline.ID
            
        _centerline = algSkeletonGraph.CSkeletonCenterline(len(mergedskeleton.m_listCenterline))
        _centerline.Name = bridgeCenterline.Name
        _centerline.Vertex = bridgeCenterline.Vertex.copy()
        _centerline.Radius = bridgeCenterline.Radius.copy()
        mergedskeleton.m_listCenterline.append(_centerline)

        if len(srcSkeleton.m_listBranch) == len(tgtSkeleton.m_listBranch) and len(srcSkeleton.m_listCenterline) == len(tgtSkeleton.m_listCenterline):
            pass
        else:
            for centerline in srcSkeleton.m_listCenterline:
                _centerline = algSkeletonGraph.CSkeletonCenterline(len(mergedskeleton.m_listCenterline))
                _centerline.Name = centerline.Name
                _centerline.Vertex = centerline.Vertex.copy()
                _centerline.Radius = centerline.Radius.copy()
                mergedskeleton.m_listCenterline.append(_centerline)
            
        # conn branch and centerline
        for centerline in mergedskeleton.ListCenterline :
            mergedskeleton.init_conn_centerline(centerline)
        # leaf centerline
        mergedskeleton.extract_leaf_centerline()
        print("passed extracting centerline & branch")

        mergedskeleton.build_graph()
        mergedskeleton.build_kd_tree()
        mergedskeleton.build_tree(rootcenterlineID)
        
        return mergedskeleton



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
            CSubStateSkelEditSelectionVertex.s_guideRangeType,
            CSubStateSkelEditSelectionVertex.s_guideVertexType
        ]

        dataInst = self.m_mediator.get_data()
        selKey, vid = self.m_mediator.App.picking_point(clickX, clickY, listExceptKeyType)
        
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



class CSubStateSkelEditSelectionVertex(subStateSkelEdit.CSubStateSkelEdit) :
    s_guideVertexType = "guideVertex"
    s_guideRangeType = "guideRange"
    
    s_guideColor = algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0])


    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_listState = [CSelectionVertexStateNonSelection(self), CSelectionVertexStateSelection(self)]
        self.m_state = 0
        self.m_newState = -1
        self.m_firstSelectedVertexkey = ""
        self.m_firstSelectedVertexID = ""
        
        self.m_secondSelectedVertexkey = ""
        self.m_secondSelectedVertexID = ""

        self.m_selVertexKey = ""
        self.m_guideVertexKey = ""
        self.m_guideRangeKey = ""
        self.m_range = 1
    def clear(self) :
        # input your code
        self.m_listState.clear()
        self.m_state = 0
        self.m_newState = -1
        self.m_firstSelectedVertexkey = ""
        self.m_firstSelectedVertexID = ""
        
        self.m_secondSelectedVertexkey = ""
        self.m_secondSelectedVertexID = ""
        
        self.m_selVertexKey = ""
        self.m_guideRangeKey = ""
        self.m_range = 1
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
        
        self.get_state().init()
        #
        #self.App.update_viewer()
    def process(self) :
        pass
    def process_end(self) :
        self.get_state().clear()
        clinfoInxs = self.get_clinfo_indices()
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
            self.App.undo()
        if keyCode == "r" :
            self.App.redo()
            
    @property
    def FirstVertexKey(self):
        return self.m_firstSelectedVertexkey
    @FirstVertexKey.setter
    def FirstVertexKey(self, firstVertexKey):
        self.m_firstSelectedVertexkey = firstVertexKey
    @property
    def FirstVertexID(self):
        return self.m_firstSelectedVertexID
    @FirstVertexID.setter
    def FirstVertexID(self, firstVertexID):
        self.m_firstSelectedVertexID = firstVertexID
    @property
    def SecondvertexKey(self):
        return self.m_secondSelectedVertexkey
    @SecondvertexKey.setter
    def SecondvertexKey(self, secondVertexKey):
        self.m_secondSelectedVertexkey = secondVertexKey
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
    
    
    
    def ref_guide_key(self) :
        self.App.ref_key(self.m_guideRangeKey)
        self.App.ref_key(self.m_guideVertexKey)
        
    def remove_guide_key(self) :
        if self.m_selVertexKey != "" :
            self.App.remove_key(self.m_guideVertexKey)
            self.App.remove_key(self.m_guideRangeKey)

            self.m_guideVertexKey = ""
            self.m_guideRangeKey = ""
    def create_guide_key(self, guideColor : np.ndarray) :
        dataInst = self._get_data()

        if self.m_firstSelectedVertexkey == "" :
            return
        if self.m_firstSelectedVertexID == "" :
            return
        if self.m_selVertexKey == "":
            return
        
        # branch guide create
        selectedCLID = data.CData.get_id_from_key(self.m_selVertexKey)
        selectedGroupID = data.CData.get_groupID_from_key(self.m_selVertexKey)
        
        skeleton = dataInst.get_skeleton(selectedGroupID)
        selectedCL = skeleton.get_centerline(selectedCLID)
        
        guideVertexKey = data.CData.make_key(CSubStateSkelEditSelectionVertex.s_guideVertexType, 0, 0)
        guideVertexObj = vtkObjGuideVertex.CVTKObjGuideVertex(selectedCL, selectedCL.get_vertex(self.m_firstSelectedVertexID), self.m_range)
        guideVertexObj.KeyType = CSubStateSkelEditSelectionVertex.s_guideVertexType
        guideVertexObj.Key = guideVertexKey
        guideVertexObj.Color = guideColor
        guideVertexObj.Opacity = 1.0
        guideVertexObj.set_line_width(4.0)
        self.m_guideVertexKey = guideVertexKey
        dataInst.add_vtk_obj(guideVertexObj)
        
        guideRangeKey = data.CData.make_key(CSubStateSkelEditSelectionVertex.s_guideRangeType, 0, 0)
        guideRangeObj = vtkObjGuideRange.CVTKObjGuideRange(selectedCL.get_vertex(self.m_firstSelectedVertexID), self.m_range)
        guideRangeObj.KeyType = CSubStateSkelEditSelectionVertex.s_guideRangeType
        guideRangeObj.Key = guideRangeKey
        guideRangeObj.Color = guideColor
        guideRangeObj.Opacity = 1.0
        self.m_guideRangeKey = guideRangeKey
        dataInst.add_vtk_obj(guideRangeObj)
        

if __name__ == '__main__' :
    pass


# print ("ok ..")


