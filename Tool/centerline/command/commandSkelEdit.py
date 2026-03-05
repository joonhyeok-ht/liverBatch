import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget
from PySide6.QtCore import Qt
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAppPath = os.path.dirname(fileAbsPath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algSegment as algSegment

import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer
import Block.reconstruction as reconstruction

import data as data

import commandInterface as commandInterface
# import territory as territory

import vtkObjEP as vtkObjEP
import vtkObjVertex as vtkObjVertex
import copy
from collections import deque


class CCommandSkelEdit(commandInterface.CCommand) :
    @staticmethod
    def resample_points(input_points : np.ndarray) -> np.ndarray :
        # resampling
        # 동일한 간격으로 리샘플링
        desired_distance = 1.0 #0.1  # 원하는 간격
        cumulative_distance = np.cumsum(np.r_[0, np.sqrt(np.sum(np.diff(input_points, axis=0)**2, axis=1))])
        total_distance = cumulative_distance[-1]
        num_samples = int(total_distance / desired_distance)
        uniform_distances = np.linspace(0, total_distance, num_samples)
        # 리샘플링된 점 계산
        resampled_points = np.zeros((num_samples, 3))
        for i in range(3):
            resampled_points[:, i] = np.interp(uniform_distances, cumulative_distance, input_points[:, i])
        
        # 시작, 끝점 원본 유지
        resampled_points[0] = input_points[0]
        resampled_points[-1] = input_points[-1]
        return resampled_points
    @staticmethod
    def resample_radius(input_points, input_radius: np.ndarray) -> np.ndarray:
        desired_distance = 1.0

        cumulative_distance = np.cumsum(np.r_[0, np.sqrt(np.sum(np.diff(input_points, axis=0)**2, axis=1))])
        total_distance = cumulative_distance[-1]

        num_samples = int(total_distance / desired_distance)
        uniform_distances = np.linspace(0, total_distance, num_samples)

        # 3) radius를 arc-length 기준으로 보간
        resampled_radius = np.interp(uniform_distances,
                                    cumulative_distance,
                                    input_radius)

        # 4) 시작/끝 원본 유지(optional)
        resampled_radius[0] = input_radius[0]
        resampled_radius[-1] = input_radius[-1]

        return resampled_radius
    @staticmethod
    def gaussian_smoothing(vertex: np.ndarray,
                           radius: np.ndarray | None = None,
                           sigma: float = 1.0):
        """
        vertex: (N,3)
        radius: (N,) or (N,1)  (optional)
        return:
          - if radius is None: smoothed_vertex
          - else: (smoothed_vertex, smoothed_radius)
        """
        from scipy.ndimage import gaussian_filter1d

        if vertex.ndim != 2 or vertex.shape[1] != 3:
            raise ValueError(f"vertex must be (N,3). got {vertex.shape}")

        n = vertex.shape[0]
        if n < 3:
            # 너무 짧으면 스무딩 의미가 없으니 그대로 반환
            if radius is None:
                return vertex.copy()
            r = radius.reshape(-1) if radius is not None else None
            return vertex.copy(), r.copy()

        # --- Vertex smoothing ---
        smoothed_x = gaussian_filter1d(vertex[:, 0], sigma)
        smoothed_y = gaussian_filter1d(vertex[:, 1], sigma)
        smoothed_z = gaussian_filter1d(vertex[:, 2], sigma)
        smoothed_vertex = np.vstack((smoothed_x, smoothed_y, smoothed_z)).T

        # 끝점은 원본 유지
        smoothed_vertex[0]  = vertex[0]
        smoothed_vertex[-1] = vertex[-1]

        # --- Radius smoothing (optional) ---
        if radius is None:
            return smoothed_vertex

        r = np.asarray(radius).reshape(-1)
        if r.shape[0] != n:
            raise ValueError(f"radius length must match vertex N={n}. got {r.shape[0]}")

        smoothed_radius = gaussian_filter1d(r, sigma)

        # 끝점은 원본 유지
        smoothed_radius[0]  = r[0]
        smoothed_radius[-1] = r[-1]

        return smoothed_vertex, smoothed_radius


    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_inputSkeleton = None
    def clear(self) :
        # input your code
        self.m_inputSkeleton = None
        super().clear()
    def process(self) :
        super().process()
        # input your code
        if self.InputSkeleton == "" :
            print("not setting Skeleton")
            return
        

    # protected
    def _find_index_last_active_cl(self) -> int :
        for idx in range(len(self.InputSkeleton.ListCenterline) - 1, 0, -1) :
            if self.InputSkeleton.ListCenterline[idx].Active == True:
                return idx
        return -1
    def _find_index_last_active_br(self) -> int :
        for idx in range(len(self.InputSkeleton.ListBranch) - 1, -1, -1) :
            if self.InputSkeleton.ListBranch[idx].Active == True :
                return idx
        return -1
    def _find_deactive_cl_inx(self) :
        iCnt = self.InputSkeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = self.InputSkeleton.get_centerline(inx)
            if cl.Active == False :
                return inx
        return -1
    def _find_deactive_br_inx(self) :
        iCnt = self.InputSkeleton.get_branch_count()
        for inx in range(0, iCnt) :
            br = self.InputSkeleton.get_branch(inx)
            if br.Active == False :
                return inx
        return -1
    def _memory_clean(self) :
        clInx = self._find_deactive_cl_inx()
        if clInx > -1 :
            del self.InputSkeleton.ListCenterline[clInx : ]
        brInx = self._find_deactive_br_inx()
        if brInx > -1 :
            del self.InputSkeleton.ListBranch[brInx : ]
            
    def _refresh_changed_cl_data_by_vertex(self, clID : int) :
        dataInst = self.InputData
        groupID = dataInst.CLInfoIndex
        skeleton = dataInst.get_skeleton(groupID)

        key = data.CData.make_key(data.CData.s_skelTypeCenterline, groupID, clID)
        obj = dataInst.find_obj_by_key(key)
        if obj is None :
            return
        self.m_mediator.unref_key(key)

        clID = data.CData.get_id_from_key(key)
        cl = skeleton.get_centerline(clID)
        clPtCnt = cl.get_vertex_count()
        if clPtCnt <= 0 :
            return
        
        appendFilter = vtk.vtkAppendPolyData()
        for clPtInx in range(0, clPtCnt) :
            pos = cl.get_vertex(clPtInx)
            polyData = algVTK.CVTK.create_poly_data_sphere(pos, data.CData.s_clSize)
            appendFilter.AddInputData(polyData)
        appendFilter.Update()
        mergedPolyData = appendFilter.GetOutput()
        obj.PolyData = mergedPolyData
        #self.m_mediator.ref_key(key)
        
        key = data.CData.make_key(data.CData.s_skelTypeVertex, groupID, clID)
        # if obj is None :
            
        vertexObj = vtkObjVertex.CVTKObjVertex(cl, dataInst.s_vertexSize, dataInst.s_vertexColor.flatten())
        if vertexObj.Ready == False :
            return
        
        self.m_mediator.unref_key(key)
        
        vertexObj.KeyType = data.CData.s_skelTypeVertex
        vertexObj.Key = data.CData.make_key(vertexObj.KeyType, groupID, cl.ID)
        #vertexObj.Color = dataInst.VertexColor
        vertexObj.Opacity = 1.0
        vertexObj.Visibility = True
        dataInst.add_vtk_obj(vertexObj)
        
        self.m_mediator.ref_key(key)
        

        if cl.is_leaf() == False :
            return

        # endPoint refresh
        key = data.CData.make_key(data.CData.s_skelTypeEndPoint, groupID, clID)
        obj = dataInst.find_obj_by_key(key)
        if obj is None :
            obj = vtkObjEP.CVTKObjEP(cl, data.CData.s_epSize)
            if obj.Ready == False :
                return

            obj.KeyType = data.CData.s_skelTypeEndPoint
            obj.Key = data.CData.make_key(obj.KeyType, groupID, cl.ID)
            obj.Color = data.CData.s_epColor
            obj.Opacity = 1.0
            obj.Visibility = True
            dataInst.add_vtk_obj(obj)
        endPt = cl.get_end_point()
        obj.Pos = endPt

        
            
    def _refresh_changed_cl_data(self, clID : int) :
        dataInst = self.InputData
        groupID = dataInst.CLInfoIndex
        skeleton = dataInst.get_skeleton(groupID)

        key = data.CData.make_key(data.CData.s_skelTypeCenterline, groupID, clID)
        obj = dataInst.find_obj_by_key(key)
        if obj is None :
            return
        self.m_mediator.unref_key(key)

        clID = data.CData.get_id_from_key(key)
        cl = skeleton.get_centerline(clID)
        clPtCnt = cl.get_vertex_count()
        if clPtCnt <= 0 :
            return
        
        appendFilter = vtk.vtkAppendPolyData()
        for clPtInx in range(0, clPtCnt) :
            pos = cl.get_vertex(clPtInx)
            polyData = algVTK.CVTK.create_poly_data_sphere(pos, data.CData.s_clSize)
            appendFilter.AddInputData(polyData)
        appendFilter.Update()
        mergedPolyData = appendFilter.GetOutput()
        obj.PolyData = mergedPolyData
        self.m_mediator.ref_key(key)
        
        key = data.CData.make_key(data.CData.s_skelTypeVertex, groupID, clID)
        # if obj is None :
            
        vertexObj = vtkObjVertex.CVTKObjVertex(cl, dataInst.s_vertexSize, dataInst.s_vertexColor.flatten())
        if vertexObj.Ready == False :
            return
        
        vertexObj.KeyType = data.CData.s_skelTypeVertex
        vertexObj.Key = data.CData.make_key(vertexObj.KeyType, groupID, cl.ID)
        #vertexObj.Color = dataInst.VertexColor
        vertexObj.Opacity = 1.0
        vertexObj.Visibility = True
        dataInst.add_vtk_obj(vertexObj)

        if cl.is_leaf() == False :
            return

        # endPoint refresh
        key = data.CData.make_key(data.CData.s_skelTypeEndPoint, groupID, clID)
        obj = dataInst.find_obj_by_key(key)
        if obj is None :
            obj = vtkObjEP.CVTKObjEP(cl, data.CData.s_epSize)
            if obj.Ready == False :
                return

            obj.KeyType = data.CData.s_skelTypeEndPoint
            obj.Key = data.CData.make_key(obj.KeyType, groupID, cl.ID)
            obj.Color = data.CData.s_epColor
            obj.Opacity = 1.0
            obj.Visibility = True
            dataInst.add_vtk_obj(obj)
        endPt = cl.get_end_point()
        obj.Pos = endPt


    @property
    def InputSkeleton(self) -> algSkeletonGraph.CSkeleton :
        return self.m_inputSkeleton
    @InputSkeleton.setter
    def InputSkeleton(self, inputSkeleton : algSkeletonGraph.CSkeleton) :
        self.m_inputSkeleton = inputSkeleton


class CCommandDisconnCLFromBr(CCommandSkelEdit) :
    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_inputCLID = -1
        self.m_inputBrID = -1
    def clear(self) :
        # input your code
        self.m_inputCLID = -1
        self.m_inputBrID = -1
        super().clear()
    def process(self) :
        super().process()
        # input your code
        if self.InputCLID == -1 :
            print("not setting cl id")
            return
        if self.InputBrID == -1 :
            print("not setting br id")
            return
        
        cl = self.InputSkeleton.get_centerline(self.InputCLID)
        
        iCnt = cl.get_conn_count()
        for inx in range(0, iCnt) :
            br = cl.get_conn(inx)
            if br is None : 
                continue
            if br.ID == self.InputBrID :
                if br.find_conn_inx_by_node(cl) >= 0 :
                    br.remove_conn_by_node(cl)
                    cl.set_conn(inx, None)
                return
        
    
    @property
    def InputCLID(self) -> int :
        return self.m_inputCLID
    @InputCLID.setter
    def InputCLID(self, inputCLID : int) :
        self.m_inputCLID = inputCLID
    @property
    def InputBrID(self) -> int :
        return self.m_inputBrID
    @InputBrID.setter
    def InputBrID(self, inputBrID : int) :
        self.m_inputBrID = inputBrID

class CCommandConnCLToBr(CCommandSkelEdit) :
    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_inputCLID = -1
        self.m_inputCLConnInx = -1
        self.m_inputBrID = -1
    def clear(self) :
        # input your code
        self.m_inputCLID = -1
        self.m_inputCLConnInx = -1
        self.m_inputBrID = -1
        super().clear()
    def process(self) :
        super().process()
        # input your code
        if self.InputCLID == -1 :
            print("not setting cl id")
            return
        if self.InputCLConnInx == -1 :
            print("not setting cl conn inx")
            return
        if self.InputBrID == -1 :
            print("not setting br id")
            return
        
        cl = self.InputSkeleton.get_centerline(self.InputCLID)
        if cl.get_conn(self.InputCLConnInx) is not None :
            print("failed conn : exist branch")
            return
        
        br = self.InputSkeleton.get_branch(self.InputBrID)
        cl.set_conn(self.InputCLConnInx, br)
        br.add_conn(cl)
        
    
    @property
    def InputCLID(self) -> int :
        return self.m_inputCLID
    @InputCLID.setter
    def InputCLID(self, inputCLID : int) :
        self.m_inputCLID = inputCLID
    @property
    def InputCLConnInx(self) -> int :
        return self.m_inputCLConnInx
    @InputCLConnInx.setter
    def InputCLConnInx(self, inputCLConnInx : int) :
        self.m_inputCLConnInx = inputCLConnInx
    @property
    def InputBrID(self) -> int :
        return self.m_inputBrID
    @InputBrID.setter
    def InputBrID(self, inputBrID : int) :
        self.m_inputBrID = inputBrID
    
class CCommandDisconnBr(CCommandSkelEdit) :
    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_inputBrID = -1
        self.m_listCmdDisconn = []
    def clear(self) :
        # input your code
        for cmdDisconn in self.m_listCmdDisconn :
            cmdDisconn.clear()
        self.m_listCmdDisconn.clear()
        self.m_inputBrID = -1
        super().clear()
    def process(self) :
        super().process()
        # input your code
        if self.InputBrID == -1 :
            print("not setting Skeleton")
            return
        
        br = self.InputSkeleton.get_branch(self.InputBrID)
        iCnt = br.get_conn_count()
        for inx in range(0, iCnt) :
            cl = br.get_conn(0)
            cmdDisconnCL = CCommandDisconnCLFromBr(self.m_mediator)
            cmdDisconnCL.InputData = self.InputData
            cmdDisconnCL.InputSkeleton = self.InputSkeleton
            cmdDisconnCL.InputBrID = br.ID
            cmdDisconnCL.InputCLID = cl.ID
            cmdDisconnCL.process()
            self.m_listCmdDisconn.append(cmdDisconnCL)


    @property
    def InputBrID(self) -> int :
        return self.m_inputBrID
    @InputBrID.setter
    def InputBrID(self, inputBrID : int) :
        self.m_inputBrID = inputBrID
    @property
    def ListCmdDisconn(self) -> list :
        return self.m_listCmdDisconn
    

class CCommandRemoveCL(CCommandSkelEdit) :
    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_inputCLID = -1
        self.m_listCmdDisconn = []
    def clear(self) :
        # input your code
        self.m_outputSwapCLID = -1
        for cmdDisconn in self.m_listCmdDisconn :
            cmdDisconn.clear()
        self.m_listCmdDisconn.clear()
        super().clear()
    def process(self) :
        super().process()
        # input your code
        if self.InputCLID == -1 :
            print("not setting cl id")
            return
        
        self._disconn()
        self._remove_cl()
        self._memory_clean()


    # protected
    def _disconn(self) :
        cl = self.InputSkeleton.get_centerline(self.InputCLID)
        iCnt = cl.get_conn_count()
        for inx in range(0, iCnt) :
            br = cl.get_conn(inx)
            if br is None :
                continue

            cmdDisconn = CCommandDisconnCLFromBr(self.m_mediator)
            cmdDisconn.InputData = self.InputData
            cmdDisconn.InputSkeleton = self.InputSkeleton
            cmdDisconn.InputCLID = cl.ID
            cmdDisconn.InputBrID = br.ID
            cmdDisconn.process()
            self.m_listCmdDisconn.append(cmdDisconn)
    def _remove_cl(self) :
        src_cl_id = self.InputCLID
        dst_cl_idx = self._find_index_last_active_cl()
        if dst_cl_idx == -1 :
            print("skel edit : error")
            return
        
        if src_cl_id == dst_cl_idx : 
            # remove
            self.InputSkeleton.ListCenterline[src_cl_id].Active = False
            self._remove_cl_id(src_cl_id)
        else :
            # swap & id changed
            tmp_cl = self.InputSkeleton.ListCenterline[dst_cl_idx]
            self.InputSkeleton.ListCenterline[dst_cl_idx] = self.InputSkeleton.ListCenterline[src_cl_id]
            self.InputSkeleton.ListCenterline[src_cl_id] = tmp_cl
            self.InputSkeleton.ListCenterline[src_cl_id].ID = src_cl_id
            self.InputSkeleton.ListCenterline[dst_cl_idx].ID = dst_cl_idx 
            # remove
            cl = self.InputSkeleton.get_centerline(dst_cl_idx)
            cl.Active = False

            # swap refresh & remove
            self._refresh_changed_cl_id(src_cl_id, dst_cl_idx)
            self._remove_cl_id(dst_cl_idx)

    def _refresh_changed_cl_id(self, srcID : int, dstID : int) :
        dataInst = self.InputData
        groupID = dataInst.CLInfoIndex

        srcKey = data.CData.make_key(data.CData.s_skelTypeCenterline, groupID, srcID)
        dstKey = data.CData.make_key(data.CData.s_skelTypeCenterline, groupID, dstID)
        srcObj = dataInst.find_obj_by_key(srcKey)
        dstObj = dataInst.find_obj_by_key(dstKey)
        
        srcVertexKey = data.CData.make_key(data.CData.s_skelTypeVertex, groupID, srcID)
        dstVertexKey = data.CData.make_key(data.CData.s_skelTypeVertex, groupID, dstID)
        srcVertexObj = dataInst.find_obj_by_key(srcVertexKey)
        dstVertexObj = dataInst.find_obj_by_key(dstVertexKey)

        if srcObj is None : 
            print("refresh error : not found srcObj")
            return
        if dstObj is None :
            print("refresh error : not found dstObj")
            return
        
        if srcVertexObj is None : 
            print("refresh error : not found srcObj")
            return
        if dstVertexObj is None :
            print("refresh error : not found dstObj")
            return
        
        if srcObj.CL.ID == srcID :
            print("refresh error : invalid src cl id")
            return
        if dstObj.CL.ID == dstID :
            print("refresh error : invalid dst cl id")
            return
        
        bSrcReg = self.m_mediator.is_registered_in_viewer(srcObj)
        bDstReg = self.m_mediator.is_registered_in_viewer(dstObj)
        
        self.m_mediator.detach_key(srcKey)
        self.m_mediator.detach_key(dstKey)

        newSrcKey = data.CData.make_key(data.CData.s_skelTypeCenterline, groupID, srcObj.CL.ID)
        srcObj.Key = newSrcKey
        dataInst.add_vtk_obj(srcObj)

        newDstKey = data.CData.make_key(data.CData.s_skelTypeCenterline, groupID, dstObj.CL.ID)
        dstObj.Key = newDstKey
        dataInst.add_vtk_obj(dstObj)
        
        newSrcVertexKey = data.CData.make_key(data.CData.s_skelTypeVertex, groupID, srcObj.CL.ID)
        srcVertexObj.Key = newSrcVertexKey
        dataInst.add_vtk_obj(srcVertexObj)

        newDstVertexKey = data.CData.make_key(data.CData.s_skelTypeVertex, groupID, dstObj.CL.ID)
        dstVertexObj.Key = newDstVertexKey
        dataInst.add_vtk_obj(dstVertexObj)

        if bSrcReg == True :
            self.m_mediator.ref_key(newSrcKey)
        if bDstReg == True :
            self.m_mediator.ref_key(newDstKey)

        # refresh end-point 
        listEPObj = []
        listEPObjReg = []
        srcEPKey = data.CData.make_key(data.CData.s_skelTypeEndPoint, groupID, srcID)
        dstEPKey = data.CData.make_key(data.CData.s_skelTypeEndPoint, groupID, dstID)
        srcEPObj = dataInst.find_obj_by_key(srcEPKey)
        dstEPObj = dataInst.find_obj_by_key(dstEPKey)

        if srcEPObj is not None : 
            bReg = self.m_mediator.is_registered_in_viewer(srcEPObj)
            listEPObj.append(srcEPObj)
            listEPObjReg.append(bReg)
        if dstEPObj is not None :
            bReg = self.m_mediator.is_registered_in_viewer(dstEPObj)
            listEPObj.append(dstEPObj)
            listEPObjReg.append(bReg)
        
        if len(listEPObj) == 0 :
            return
        
        for epObj in listEPObj :
            self.m_mediator.detach_key(epObj.Key)
        for epObj in listEPObj :
            newEPKey = data.CData.make_key(data.CData.s_skelTypeEndPoint, groupID, epObj.LeafCL.ID)
            epObj.Key = newEPKey
            dataInst.add_vtk_obj(epObj)
        for inx, bFlag in enumerate(listEPObjReg) :
            if bFlag == True :
                self.m_mediator.ref_key(listEPObj[inx].Key)
    def _remove_cl_id(self, clID) :
        dataInst = self.InputData
        groupID = dataInst.CLInfoIndex
        clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, groupID, clID)
        epKey = data.CData.make_key(data.CData.s_skelTypeEndPoint, groupID, clID)
        vertexKey = data.CData.make_key(data.CData.s_skelTypeVertex, groupID, clID)
        self.m_mediator.remove_key(clKey)
        self.m_mediator.remove_key(epKey)
        self.m_mediator.remove_key(vertexKey)


    
    @property
    def InputCLID(self) -> int :
        return self.m_inputCLID
    @InputCLID.setter
    def InputCLID(self, inputCLID : int) :
        self.m_inputCLID = inputCLID
    @property
    def ListCmdDisconn(self) -> list :
        return self.m_listCmdDisconn


class CCommandRemoveBr(CCommandSkelEdit) :
    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_inputBrID = -1
    def clear(self) :
        # input your code
        self.m_inputBrID = -1
        super().clear()
    def process(self) :
        super().process()
        # input your code
        if self.InputBrID == -1 :
            print("not setting Skeleton")
            return
        
        self._disconn()
        self._remove_br()
        self._memory_clean()
    

    # protected
    def _disconn(self) :
        cmdDisconn = CCommandDisconnBr(self.m_mediator)
        cmdDisconn.InputData = self.InputData
        cmdDisconn.InputSkeleton = self.InputSkeleton
        cmdDisconn.InputBrID = self.InputBrID
        cmdDisconn.process()
    def _remove_br(self) :
        src_br_id = self.InputBrID
        dst_br_idx = self._find_index_last_active_br()
        if dst_br_idx == -1 :
            print("skel edit : error")
            return
        
        if src_br_id == dst_br_idx :
            self.InputSkeleton.ListBranch[src_br_id].Active = False
            groupID = self.InputData.CLInfoIndex
            srcKey = data.CData.make_key(data.CData.s_skelTypeBranch, groupID, src_br_id)
            self.m_mediator.remove_key(srcKey)
        else :
            # swap & id changed
            tmp_br = self.InputSkeleton.ListBranch[dst_br_idx]
            self.InputSkeleton.ListBranch[dst_br_idx] = self.InputSkeleton.ListBranch[src_br_id]
            self.InputSkeleton.ListBranch[src_br_id] = tmp_br
            self.InputSkeleton.ListBranch[src_br_id].ID = src_br_id
            self.InputSkeleton.ListBranch[dst_br_idx].ID = dst_br_idx
            # remove
            br = self.InputSkeleton.get_branch(dst_br_idx)
            br.Active = False

            # swap refresh & remove
            self._refresh_changed_br_id(src_br_id, dst_br_idx)
            groupID = self.InputData.CLInfoIndex
            srcKey = data.CData.make_key(data.CData.s_skelTypeBranch, groupID, dst_br_idx)
            self.m_mediator.remove_key(srcKey)
    def _refresh_changed_br_id(self, srcID : int, dstID : int) :
        dataInst = self.InputData
        groupID = dataInst.CLInfoIndex

        srcKey = data.CData.make_key(data.CData.s_skelTypeBranch, groupID, srcID)
        dstKey = data.CData.make_key(data.CData.s_skelTypeBranch, groupID, dstID)
        srcObj = dataInst.find_obj_by_key(srcKey)
        dstObj = dataInst.find_obj_by_key(dstKey)

        if srcObj is None : 
            print("refresh error : not found br srcObj")
            return
        if dstObj is None :
            print("refresh error : not found br dstObj")
            return
        
        # skeleton = dataInst.get_skeleton(groupID)
        # srcBr = skeleton.get_branch(srcID)
        # dstBr = skeleton.get_branch(dstID)
        # if srcObj.BR != srcBr :
        #     print("refresh error : mismatched src br")
        #     return
        # if dstObj.BR != dstBr :
        #     print("refresh error : mismatched dst br")
        #     return
        if srcObj.BR.ID == srcID :
            print("refresh error : mismatched src br id")
            return
        if dstObj.BR.ID == dstID :
            print("refresh error : mismatched dst br id")
            return
        
        bSrcReg = self.m_mediator.is_registered_in_viewer(srcObj)
        bDstReg = self.m_mediator.is_registered_in_viewer(dstObj)

        self.m_mediator.detach_key(srcKey)
        self.m_mediator.detach_key(dstKey)

        newSrcKey = data.CData.make_key(data.CData.s_skelTypeBranch, groupID, srcObj.BR.ID)
        srcObj.Key = newSrcKey
        dataInst.add_vtk_obj(srcObj)

        newDstKey = data.CData.make_key(data.CData.s_skelTypeBranch, groupID, dstObj.BR.ID)
        dstObj.Key = newDstKey
        dataInst.add_vtk_obj(dstObj)

        if bSrcReg == True :
            self.m_mediator.ref_key(newSrcKey)
        if bDstReg == True :
            self.m_mediator.ref_key(newDstKey)

    
    @property
    def InputBrID(self) -> int :
        return self.m_inputBrID
    @InputBrID.setter
    def InputBrID(self, inputBrID : int) :
        self.m_inputBrID = inputBrID

    
class CCommandReAttach(CCommandSkelEdit) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_inputData = None
        self.m_pivotVertexKey = ""
        self.m_newBranchVertexKey = ""
        self.m_selectedBranchKey = ""
        self.m_numOfConnCl = 0
        
        self.m_piviotVertexID = -1
        self.m_newBranchVertexID = -1
        
        self.m_undoSkeleton = None
        self.m_inputSkeleton = None
        self.m_inputClID = -1
        
    def clear(self) :
        # input your code
        self.m_inputData = None
        self.m_pivotVertexKey = ""
        self.m_newBranchVertexKey = ""
        self.m_selectedBranchKey = ""
        self.m_numOfConnCl = 0
        
        self.m_piviotVertexID = -1
        self.m_newBranchVertexID = -1
        
        self.m_undoSkeleton = None
        self.m_inputSkeleton = None
        self.m_inputClID = -1
        
        super().clear()
    def process(self) :
        groupID = data.CData.get_groupID_from_key(self.PivotVertexKey)
        clID  = data.CData.get_id_from_key(self.PivotVertexKey)
        self.m_inputSkeleton = self.InputData.get_skeleton(groupID)
        self.m_undoSkeleton = copy.deepcopy(self.m_inputSkeleton)
        
        cl = self.m_inputSkeleton.get_centerline(clID)
        selectedBrID = data.CData.get_id_from_key(self.m_selectedBranchKey)
        br = self.m_inputSkeleton.get_branch(selectedBrID)
        
        newBranchClID = data.CData.get_id_from_key(self.NewBranchVertexKey)
        newBranchCl = self.m_inputSkeleton.get_centerline(newBranchClID)
        
        refinedDirection = ""
        
        if algLinearMath.CScoMath.is_equal_vec(cl.get_vertex(0), br.BranchPoint):
            minInx = 0
            maxInx = self.m_piviotVertexID
            refinedDirection = "left"
            refinedVertex = np.concatenate((newBranchCl.get_vertex(self.NewBranchVertexID), cl.get_vertex(self.m_piviotVertexID)), axis=0)
            refinedRadius = np.array([newBranchCl.get_radius(self.NewBranchVertexID), cl.get_radius(self.m_piviotVertexID)])
        
        else:
            minInx = self.m_piviotVertexID
            maxInx = cl.Vertex.shape[0]-1
            refinedDirection = "right"
            refinedVertex = np.concatenate((cl.get_vertex(self.m_piviotVertexID), newBranchCl.get_vertex(self.NewBranchVertexID)), axis=0)
            refinedRadius = np.array([cl.get_radius(self.m_piviotVertexID), newBranchCl.get_radius(self.NewBranchVertexID)])
            
        refinedRadius = CCommandSkelEdit.resample_radius(refinedVertex, refinedRadius)
        refinedVertex = CCommandSkelEdit.resample_points(refinedVertex)
        
        modifiedVertex, modifiedRadius = None, None
        
        if refinedDirection == "left":
            modifiedVertex = np.concatenate((refinedVertex, cl.Vertex[self.m_piviotVertexID:]))
            modifiedRadius = np.concatenate((refinedRadius, cl.Radius[self.m_piviotVertexID:]))
        else:
            modifiedVertex = np.concatenate((cl.Vertex[:self.m_piviotVertexID], refinedVertex))
            modifiedRadius = np.concatenate((cl.Radius[:self.m_piviotVertexID], refinedRadius))
            
        modifiedVertex, modifiedRadius = CCommandSkelEdit.gaussian_smoothing(modifiedVertex, modifiedRadius, sigma=5)
        modifiedRadius = CCommandSkelEdit.resample_radius(modifiedVertex, modifiedRadius)
        modifiedVertex = CCommandSkelEdit.resample_points(modifiedVertex)
        
        cl.Vertex = modifiedVertex.copy()
        cl.Radius = modifiedRadius.copy()
        
        newBranchNeedSplitCenterline = True
        
        if newBranchCl.get_conn_inx(newBranchCl.get_vertex(self.NewBranchVertexID)) != -1:
            newBranchNeedSplitCenterline = False
        
        for bi in range(self.m_inputSkeleton.get_branch_count()):
            if algLinearMath.CScoMath.is_equal_vec(self.m_inputSkeleton.get_branch(bi).BranchPoint, newBranchCl.get_vertex(self.NewBranchVertexID)) == True:
                newBranchNeedSplitCenterline = False
        
        if newBranchNeedSplitCenterline:
            self.split_centerline(self.m_inputSkeleton, newBranchCl, int(self.NewBranchVertexID))
            
        newSkeleton = algSkeletonGraph.CSkeleton()
        #self.m_inputSkeleton.m_listCenterline[clID] = cl
        rootcenterlineID = 0
        for centerline in self.m_inputSkeleton.m_listCenterline:
            _centerline = algSkeletonGraph.CSkeletonCenterline(len(newSkeleton.m_listCenterline))
            _centerline.Name = centerline.Name
            _centerline.Vertex = centerline.Vertex.copy()
            _centerline.Radius = centerline.Radius.copy()
            newSkeleton.m_listCenterline.append(_centerline)
            if self.m_inputSkeleton.m_rootCenterline.ID == centerline.ID:
                rootcenterlineID = _centerline.ID
        
        for cl in newSkeleton.ListCenterline :
            newSkeleton.init_conn_centerline(cl)
        # leaf centerline
        newSkeleton.extract_leaf_centerline()

        newSkeleton.build_graph()
        newSkeleton.build_kd_tree()
        newSkeleton.build_tree(rootcenterlineID)
        
        self.InputData.m_listSkelInfo[groupID].Skeleton = newSkeleton
        self.m_mediator.add_skeleton_obj(groupID)
        
    def process_undo(self, state):
        clinfoInx = data.CData.get_groupID_from_key(self.PivotVertexKey)

        if state in [0, 1, 2]:
            self.m_mediator.unref_key_type_groupID(data.CData.s_skelTypeCenterline, clinfoInx)
            if state == 1:
                self.m_mediator.unref_key_type_groupID(data.CData.s_skelTypeBranch, clinfoInx)
            elif state == 2:
                self.m_mediator.unref_key_type_groupID(data.CData.s_skelTypeEndPoint, clinfoInx)
        else:
            self.m_mediator.unref_key_type_groupID(data.CData.s_skelTypeVertex, clinfoInx)
        self.InputData.remove_all_key_by_type_groupID(data.CData.s_skelTypeCenterline, clinfoInx)
        self.InputData.remove_all_key_by_type_groupID(data.CData.s_skelTypeBranch, clinfoInx)
        self.InputData.remove_all_key_by_type_groupID(data.CData.s_skelTypeEndPoint, clinfoInx)
        self.InputData.remove_all_key_by_type_groupID(data.CData.s_skelTypeVertex, clinfoInx)
        self.InputData.m_listSkelInfo[clinfoInx].Skeleton = self.m_undoSkeleton
        self.m_mediator.add_skeleton_obj(clinfoInx)
        
        if state in [0, 1, 2]:
            self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeCenterline, clinfoInx)
            if state == 1:
                self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeBranch, clinfoInx)
            elif state == 2:
                self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeEndPoint, clinfoInx)
        else:
            self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeVertex, clinfoInx)

            
        
    def split_centerline(self, skeleton, centerline, splitVertexInx):
        splitCenterlineID = centerline.ID
        
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


    @property
    def InputData(self) :
        return self.m_inputData
    @InputData.setter
    def InputData(self, inputData) :
        self.m_inputData = inputData
        
    @property
    def PivotVertexKey(self) :
        return self.m_pivotVertexKey
    @PivotVertexKey.setter
    def PivotVertexKey(self, pivotVertexKey):
        self.m_pivotVertexKey = pivotVertexKey
        
    @property
    def NewBranchVertexKey(self) :
        return self.m_newBranchVertexKey
    @NewBranchVertexKey.setter
    def NewBranchVertexKey(self, newBranchVertexKey):
        self.m_newBranchVertexKey = newBranchVertexKey
        
    @property
    def PiviotVertexID(self) :
        return self.m_piviotVertexID
    @PiviotVertexID.setter
    def PiviotVertexID(self, piviotVertexID):
        self.m_piviotVertexID = piviotVertexID
        
    @property
    def NewBranchVertexID(self) :
        return self.m_newBranchVertexID
    @NewBranchVertexID.setter
    def NewBranchVertexID(self, newBranchVertexID):
        self.m_newBranchVertexID = newBranchVertexID
        
        
    
    
class CCommandConnect(CCommandSkelEdit) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_inputData = None
        self.m_firstSelectedVertexKey = ""
        self.m_secondSelectedVertexKey = ""
        
        self.m_firstSelectedVertexID = -1
        self.m_secondSelectedVertexID = -1
        
        self.m_undoSkeleton = None
        self.m_secondSkeleton = None
        
        self.m_inputSkeleton = None
        self.m_inputClID = -1
        
        self.m_undoSecondCLVertex = None
        self.m_undoSecondCLRadius = None
    def clear(self) :
        # input your code
        self.m_inputData = None
        self.m_firstSelectedVertexKey = ""
        self.m_secondSelectedVertexKey = ""
        
        self.m_firstSelectedVertexID = -1
        self.m_secondSelectedVertexID = -1
        
        self.m_undoSkeleton = None
        self.m_secondSkeleton = None
        
        self.m_inputSkeleton = None
        self.m_inputClID = -1
        
        self.m_undoSecondCLVertex = None
        self.m_undoSecondCLRadius = None
        super().clear()
    def process(self) :
        firstGroupID = data.CData.get_groupID_from_key(self.FirstSelectedVertexKey)
        firstSkeleton = self.InputData.get_skeleton(firstGroupID)
        firstSelectedCLID = data.CData.get_id_from_key(self.FirstSelectedVertexKey)
        firstSelectedCL = firstSkeleton.get_centerline(firstSelectedCLID)
        firstV = firstSelectedCL.get_vertex(self.FirstSelectedVertexID)
        firstR = firstSelectedCL.get_radius(self.FirstSelectedVertexID)
        
        self.m_undoSkeleton = copy.deepcopy(firstSkeleton)
        
        secondGroupID = data.CData.get_groupID_from_key(self.SecondSelectedVertexKey)
        secondSkeleton = self.InputData.get_skeleton(secondGroupID)
        secondSelectedCLID = data.CData.get_id_from_key(self.SecondSelectedVertexKey)
        secondSelectedCL = secondSkeleton.get_centerline(secondSelectedCLID)
        secondV = secondSelectedCL.get_vertex(self.SecondSelectedVertexID)
        secondR = secondSelectedCL.get_radius(self.SecondSelectedVertexID)
        
        self.m_secondSkeleton = secondSkeleton
        self.m_undoSecondCLVertex = secondSelectedCL.Vertex.copy()
        self.m_undoSecondCLRadius = secondSelectedCL.Radius.copy()
        
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
        refinedRadius = CCommandSkelEdit.resample_radius(refinedVertex, refinedRadius)
        refinedVertex = CCommandSkelEdit.resample_points(refinedVertex)
        #print(f"resampled refinedVertex shape : {refinedVertex.shape}", file=sys.__stdout__,flush=True)
        bridgeCLID = len(firstSkeleton.m_listCenterline) + len(secondSkeleton.m_listCenterline)
        bridgeCenterline = algSkeletonGraph.CSkeletonCenterline(bridgeCLID)
        bridgeCenterline.Name = firstSelectedCL.Name
        bridgeCenterline.Vertex = refinedVertex
        bridgeCenterline.Radius = refinedRadius
        
        '''
        firstVNeedSplitCenterline 와 secondVNeedSplitCenterline 에 따라서 firstCL과 secondCL을 나눠야할 지 말지 정해야 함.
        그리고 나눈 후에 bridge Centerline과 기존의 centerline list 와 합쳐서 skeleton을 다시 build 해야 함
        '''
        if firstVNeedSplitCenterline:
            self.split_centerline(firstSkeleton, firstSelectedCL, int(self.FirstSelectedVertexID))
            
        if secondVNeedSplitCenterline:
            self.split_centerline(secondSkeleton, secondSelectedCL, int(self.SecondSelectedVertexID))
        mergedskeleton = self.merge_centerline(secondSkeleton, firstSkeleton, bridgeCenterline)
        ''' 
        임시로 첫번째 group ID로 덮어씌우는 방향으로 설정 
        '''
        self.InputData.m_listSkelInfo[firstGroupID].Skeleton = mergedskeleton
        self.m_mediator.add_skeleton_obj(firstGroupID)
        
    def process_undo(self, state):
        firstGroupID = data.CData.get_groupID_from_key(self.FirstSelectedVertexKey)
        secondGroupID = data.CData.get_groupID_from_key(self.SecondSelectedVertexKey)
        if state in [0, 1, 2]:
            self.m_mediator.unref_key_type_groupID(data.CData.s_skelTypeCenterline, firstGroupID)
            if state == 1:
                self.m_mediator.unref_key_type_groupID(data.CData.s_skelTypeBranch, firstGroupID)
            elif state == 2:
                self.m_mediator.unref_key_type_groupID(data.CData.s_skelTypeEndPoint, firstGroupID)
        else:
            self.m_mediator.unref_key_type_groupID(data.CData.s_skelTypeVertex, firstGroupID)
        self.InputData.remove_all_key_by_type_groupID(data.CData.s_skelTypeCenterline, firstGroupID)
        self.InputData.remove_all_key_by_type_groupID(data.CData.s_skelTypeBranch, firstGroupID)
        self.InputData.remove_all_key_by_type_groupID(data.CData.s_skelTypeEndPoint, firstGroupID)
        self.InputData.remove_all_key_by_type_groupID(data.CData.s_skelTypeVertex, firstGroupID)
        self.InputData.m_listSkelInfo[firstGroupID].Skeleton = self.m_undoSkeleton
        self.m_mediator.add_skeleton_obj(firstGroupID)
            
        if state in [0, 1, 2]:
            self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeCenterline, firstGroupID)
            if firstGroupID != secondGroupID:
                self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeCenterline, secondGroupID)
                
            if state == 1:
                self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeBranch, firstGroupID)
                if firstGroupID != secondGroupID:
                    self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeBranch, secondGroupID)
            elif state == 2:
                self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeEndPoint, firstGroupID)
                if firstGroupID != secondGroupID:
                    self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeEndPoint, secondGroupID)
        else:
            self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeVertex, firstGroupID)
            if firstGroupID != secondGroupID:
                self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeVertex, secondGroupID)
        
    def split_centerline(self, skeleton, centerline, splitVertexInx):
        splitCenterlineID = centerline.ID
        
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


    @property
    def InputData(self) :
        return self.m_inputData
    @InputData.setter
    def InputData(self, inputData) :
        self.m_inputData = inputData
        
    @property
    def FirstSelectedVertexKey(self) :
        return self.m_firstSelectedVertexKey
    @FirstSelectedVertexKey.setter
    def FirstSelectedVertexKey(self, firstSelectedVertexKey):
        self.m_firstSelectedVertexKey = firstSelectedVertexKey
        
    @property
    def SecondSelectedVertexKey(self) :
        return self.m_secondSelectedVertexKey
    @SecondSelectedVertexKey.setter
    def SecondSelectedVertexKey(self, secondSelectedVertexKey):
        self.m_secondSelectedVertexKey = secondSelectedVertexKey
        
    @property
    def FirstSelectedVertexID(self) :
        return self.m_firstSelectedVertexID
    @FirstSelectedVertexID.setter
    def FirstSelectedVertexID(self, firstSelectedVertexID):
        self.m_firstSelectedVertexID = firstSelectedVertexID
        
    @property
    def SecondSelectedVertexID(self) :
        return self.m_secondSelectedVertexID
    @SecondSelectedVertexID.setter
    def SecondSelectedVertexID(self, secondSelectedVertexID):
        self.m_secondSelectedVertexID = secondSelectedVertexID
        
class CCommandAutoRemoveCL(CCommandSkelEdit) :
    '''
    only remove leaf centerline
    '''
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_inputListCLID = []
        self.m_listCmd = []
        self.m_undoSkeleton = None
        self.m_clinfoInx = -1
    def clear(self) :
        # input your code
        self.m_inputListCLID.clear()
        for cmd in self.m_listCmd :
            cmd.clear()
        self.m_listCmd.clear()
        self.m_undoSkeleton = None
        self.m_clinfoInx = -1
        super().clear()
    # def process_undo(self) :
    #     reverseListCmd = self.m_listCmd[ : : -1]
    #     for cmd in reverseListCmd :
    #         cmd.process_undo()
    def process(self) :
        super().process()
        # input your code
        self.m_undoSkeleton = copy.deepcopy(self.InputSkeleton)
        if len(self.m_inputListCLID) == 0 :
            print("not setting cl id")
            return
        
        retListCL = []
        for clID in self.m_inputListCLID :
            cl = self.InputSkeleton.get_centerline(clID)
            retListCL.append(cl)
        
        retListBrID = []
        leafCL = []
        for cl in retListCL :
            if cl.is_leaf() == False :
                if self.check_is_loop_centerline(cl) and len(retListCL)==1:
                    cmd = CCommandRemoveCL(self.m_mediator)
                    cmd.InputData = self.InputData
                    cmd.InputSkeleton = self.InputSkeleton
                    cmd.InputCLID = cl.ID
                    cmd.process()
                    self.m_listCmd.append(cmd)
                    
                    brIDSet = set([])
                    for disCmd in cmd.ListCmdDisconn :
                        brIDSet.add(disCmd.InputBrID)
                        
                    for brID in brIDSet:
                        br = self.InputSkeleton.get_branch(brID)
                        if br.get_conn_count() == 2 :
                            cmd = CCommandMergeCL(self.m_mediator)
                            cmd.InputData = self.InputData
                            cmd.InputSkeleton = self.InputSkeleton
                            cmd.InputBrID = br.ID
                            cmd.m_gaussianSmoothing = False
                            cmd.process()
                            self.m_listCmd.append(cmd)
                    return
                continue
            else:
                leafCL.append(cl)
            
        for cl in leafCL:
            cmd = CCommandRemoveCL(self.m_mediator)
            cmd.InputData = self.InputData
            cmd.InputSkeleton = self.InputSkeleton
            cmd.InputCLID = cl.ID
            cmd.process()
            self.m_listCmd.append(cmd)

            for disCmd in cmd.ListCmdDisconn :
                retListBrID.append(disCmd.InputBrID)
        
        if len(retListBrID) == 0 :
            print("skel edit : error")
            return
        
        retListBrID = list(set(retListBrID))
        retListBr = []
        for brID in retListBrID :
            br = self.InputSkeleton.get_branch(brID)
            retListBr.append(br)
        
        for br in retListBr :
            if br.get_conn_count() == 1 :
                cmd = CCommandRemoveBr(self.m_mediator)
                cmd.InputData = self.InputData
                cmd.InputSkeleton = self.InputSkeleton
                cmd.InputBrID = br.ID
                cmd.process()
                self.m_listCmd.append(cmd)
            elif br.get_conn_count() == 2 :
                cmd = CCommandMergeCL(self.m_mediator)
                cmd.InputData = self.InputData
                cmd.InputSkeleton = self.InputSkeleton
                cmd.InputBrID = br.ID
                cmd.process()
                self.m_listCmd.append(cmd)
                
                

    def process_undo(self, state):
            super().process_undo(state)
            
            clinfoInx = self.m_clinfoInx

            if state in [0, 1, 2]:
                self.m_mediator.unref_key_type_groupID(data.CData.s_skelTypeCenterline, clinfoInx)
                if state == 1:
                    self.m_mediator.unref_key_type_groupID(data.CData.s_skelTypeBranch, clinfoInx)
                elif state == 2:
                    self.m_mediator.unref_key_type_groupID(data.CData.s_skelTypeEndPoint, clinfoInx)
            else:
                self.m_mediator.unref_key_type_groupID(data.CData.s_skelTypeVertex, clinfoInx)
            self.InputData.remove_all_key_by_type_groupID(data.CData.s_skelTypeCenterline, clinfoInx)
            self.InputData.remove_all_key_by_type_groupID(data.CData.s_skelTypeBranch, clinfoInx)
            self.InputData.remove_all_key_by_type_groupID(data.CData.s_skelTypeEndPoint, clinfoInx)
            self.InputData.remove_all_key_by_type_groupID(data.CData.s_skelTypeVertex, clinfoInx)
            self.InputData.m_listSkelInfo[clinfoInx].Skeleton = self.m_undoSkeleton
            self.m_mediator.add_skeleton_obj(clinfoInx)
            
            if state in [0, 1, 2]:
                self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeCenterline, clinfoInx)
                if state == 1:
                    self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeBranch, clinfoInx)
                elif state == 2:
                    self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeEndPoint, clinfoInx)
            else:
                self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeVertex, clinfoInx)

            
    def check_is_loop_centerline(self, cl):
        skeleton = self.InputSkeleton
        
        rootCLID = skeleton.RootCenterline.ID
        
        ID = 0
        m_visitedCLID = set()
        queueCLID = deque([])
        queueCLID.append(rootCLID)
        m_visitedCLID.add(rootCLID)
        
        # bfs 알고리즘 기반으로 centerline graph 전파
        
        while queueCLID:
            currentCLID = queueCLID.popleft()
            ID += 1
            currentCL = skeleton.get_centerline(currentCLID)
            if currentCL.is_leaf() and currentCLID != rootCLID:
                continue
            elif currentCLID == cl.ID:
                continue
            else:
                for bi in range(2):
                    currentBR = currentCL.get_conn(bi)
                    if currentBR == None:
                        continue
                    listAdjCLID = [currentBR.get_conn(inx).ID for inx in range(currentBR.get_conn_count())]
                    for adjCLID in listAdjCLID:
                        adjCL = skeleton.get_centerline(adjCLID)
                        if adjCLID in m_visitedCLID:
                            continue
                        else:
                            m_visitedCLID.add(adjCLID)
                            queueCLID.append(adjCLID)
        
        if ID == skeleton.get_centerline_count():
            return True
        else:
            return False

            
            
            
            
    def add_clID(self, clID : int) :
        self.m_inputListCLID.append(clID)
    def get_clID_count(self) -> int :
        return len(self.m_inputListCLID)
    def get_clID(self, inx : int) -> int :
        return self.m_inputListCLID[inx]
    
    @property
    def ListCmd(self) -> list :
        return self.m_listCmd
    

    
class CCommandMergeCL(CCommandSkelEdit) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_inputBrID = -1
        self.m_gaussianSmoothing = True
        self.m_undoSkeleton = None
        self.m_clinfoInx = -1
        
    def clear(self) :
        # input your code
        self.m_inputBrID = -1
        super().clear()
        self.m_undoSkeleton = None
        self.m_clinfoInx = -1
    def process(self) :
        super().process()
        self.m_undoSkeleton = copy.deepcopy(self.InputSkeleton)
        # input your code
        if self.InputBrID == -1 :
            print("not setting src br id")
            return
        
        br = self.InputSkeleton.get_branch(self.InputBrID)
        if br.get_conn_count() != 2 :
            print(f"failed merge : total conn count is {br.get_conn_count()}")
            return
        
        # decide src, dst
        cl1 = self.InputSkeleton.get_centerline(br.get_conn(0).ID)
        cl2 = self.InputSkeleton.get_centerline(br.get_conn(1).ID)
        src_cl, dst_cl = self._decide_src_and_dst(cl1, cl2)

        # align src, dst
        srcInx = src_cl.get_conn_inx(br.BranchPoint)
        if srcInx != 0 :
            src_cl.reverse()
        elif srcInx == -1 :
            return
        dstInx = dst_cl.get_conn_inx(br.BranchPoint)
        if dstInx == 0 :
            dst_cl.reverse()
        elif dstInx == -1 :
            return

        # branch disconn
        cmdRemoveBr = CCommandRemoveBr(self.m_mediator)
        cmdRemoveBr.InputData = self.InputData
        cmdRemoveBr.InputSkeleton = self.InputSkeleton
        cmdRemoveBr.InputBrID = self.InputBrID
        cmdRemoveBr.process()

        if src_cl.get_conn(1) is not None :
            cmdConn = CCommandConnCLToBr(self.m_mediator)
            cmdConn.InputData = self.InputData
            cmdConn.InputSkeleton = self.InputSkeleton
            cmdConn.InputCLID = dst_cl.ID
            cmdConn.InputCLConnInx = 1
            cmdConn.InputBrID = src_cl.get_conn(1).ID
            cmdConn.process()

        # modified dst_cl & refresh
        concat_vertex = np.concatenate((dst_cl.Vertex, src_cl.Vertex[1:]), axis=0)
        concat_radius = np.concatenate((dst_cl.Radius, src_cl.Radius[1:]), axis=0)
        
        if self.m_gaussianSmoothing:
            concat_vertex, concat_radius = CCommandSkelEdit.gaussian_smoothing(concat_vertex, concat_radius, sigma=5)
        
        concat_radius = CCommandSkelEdit.resample_radius(concat_vertex, concat_radius)
        concat_vertex = CCommandSkelEdit.resample_points(concat_vertex)
        dst_cl.Vertex = concat_vertex
        dst_cl.Radius = concat_radius

        groupID = self.InputData.CLInfoIndex
        self._refresh_changed_cl_data(dst_cl.ID)

        # removed src_cl
        cmdRemoveCL = CCommandRemoveCL(self.m_mediator)
        cmdRemoveCL.InputData = self.InputData
        cmdRemoveCL.InputSkeleton = self.InputSkeleton
        cmdRemoveCL.InputCLID = src_cl.ID
        cmdRemoveCL.process()

    # protected
    def _decide_src_and_dst(self, cl1 : algSkeletonGraph.CSkeletonCenterline, cl2 : algSkeletonGraph.CSkeletonCenterline) :
        '''
        ret : (srcCL, dstCL)
        '''
        if cl1.is_leaf() :
            return cl1, cl2
        elif cl2.is_leaf() :
            return cl2, cl1
        else :
            return cl1, cl2
        
    def process_undo(self, state):
        clinfoInx = self.m_clinfoInx

        if state in [0, 1, 2]:
            self.m_mediator.unref_key_type_groupID(data.CData.s_skelTypeCenterline, clinfoInx)
            if state == 1:
                self.m_mediator.unref_key_type_groupID(data.CData.s_skelTypeBranch, clinfoInx)
            elif state == 2:
                self.m_mediator.unref_key_type_groupID(data.CData.s_skelTypeEndPoint, clinfoInx)
        else:
            self.m_mediator.unref_key_type_groupID(data.CData.s_skelTypeVertex, clinfoInx)
        self.InputData.remove_all_key_by_type_groupID(data.CData.s_skelTypeCenterline, clinfoInx)
        self.InputData.remove_all_key_by_type_groupID(data.CData.s_skelTypeBranch, clinfoInx)
        self.InputData.remove_all_key_by_type_groupID(data.CData.s_skelTypeEndPoint, clinfoInx)
        self.InputData.remove_all_key_by_type_groupID(data.CData.s_skelTypeVertex, clinfoInx)
        self.InputData.m_listSkelInfo[clinfoInx].Skeleton = self.m_undoSkeleton
        self.m_mediator.add_skeleton_obj(clinfoInx)
        
        if state in [0, 1, 2]:
            self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeCenterline, clinfoInx)
            if state == 1:
                self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeBranch, clinfoInx)
            elif state == 2:
                self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeEndPoint, clinfoInx)
        else:
            self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeVertex, clinfoInx)

    @property
    def InputBrID(self) -> int :
        return self.m_inputBrID
    @InputBrID.setter
    def InputBrID(self, inputBrID : int) :
        self.m_inputBrID = inputBrID

class CCommandUpdateCL(CCommandSkelEdit) :
    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_inputCLID = -1
        self.m_inputVertex = None
        self.m_inputRadius = None
        self.m_inputMinInx = -1
        self.m_inputEndInx = -1
        self.m_inputReverse = False

        self.m_undoCLVertex = None
        self.m_undoCLRadius = None
    def clear(self) :
        # input your code
        self.m_inputCLID = -1
        self.m_inputVertex = None
        self.m_inputRadius = None
        self.m_inputMinInx = -1
        self.m_inputEndInx = -1
        self.m_inputReverse = False

        self.m_undoCLVertex = None
        self.m_undoCLRadius = None
        super().clear()
    def process(self) :
        super().process()
        # input your code
        if self.InputCLID == -1 :
            print("not setting cl id")
            return
        if self.InputVertex is None :
            print("not setting vertex")
            return
        if self.InputMinInx == -1 :
            print("not setting min index")
            return
        
        cl = self.InputSkeleton.get_centerline(self.InputCLID)
        self.m_undoCLVertex = cl.Vertex.copy()
        self.m_undoCLRadius = cl.Radius.copy()

        startInx = -1
        endInx = -1
        reverseVertex = None
        reverseRadius = None
        if self.InputReverse == True :
            reverseVertex = self.InputVertex[ : : -1].copy()
            reverseRadius = self.InputRadius[ : : -1].copy()
            startInx = 0
            endInx = self.InputVertex.shape[0]
        else :
            reverseVertex = self.InputVertex.copy()
            reverseRadius = self.InputRadius.copy()
            startInx = self.InputMinInx
            if self.m_inputEndInx == -1:
                endInx = cl.Vertex.shape[0]
            else:
                endInx = self.m_inputEndInx
        clVertex = cl.Vertex.copy()
        clRadius = cl.Radius.copy()
        if not np.isnan(reverseVertex[ : ]).any():
            clVertex[startInx : endInx] = reverseVertex[ : ].copy()
            clRadius[startInx : endInx] = reverseRadius[ : ].copy()
        # refinedVertex = CCommandSkelEdit.gaussian_smoothing(clVertex, sigma=5)
        # refinedVertex = CCommandSkelEdit.resample_points(refinedVertex)
        # if np.isnan(reverseVertex[ : ]).any():
        #     print(f"cl{cl.Vertex.copy()}", file=sys.__stdout__, flush=True)
        #     print(f"clVertex{clVertex}", file=sys.__stdout__, flush=True)
        #     print(f"reverseVertex{reverseVertex}", file=sys.__stdout__, flush=True)
        refinedVertex = CCommandSkelEdit.resample_points(clVertex)
        refinedRadius = CCommandSkelEdit.resample_radius(clVertex, clRadius)

        cl.Vertex = refinedVertex
        cl.Radius = refinedRadius

        
        if self.m_inputEndInx == -1:
            self._refresh_changed_cl_data(cl.ID)
        else:
            self._refresh_changed_cl_data_by_vertex(cl.ID)
    def process_undo(self, state):
        super().process_undo(state)
        # input your code
        cl = self.InputSkeleton.get_centerline(self.InputCLID)
        cl.Vertex = self.m_undoCLVertex.copy()
        cl.Radius = self.m_undoCLRadius.copy()
        if state in [0, 1, 2]:
            self._refresh_changed_cl_data(cl.ID)
        else:
            self._refresh_changed_cl_data_by_vertex(cl.ID)

    
    # protected

          
    @property
    def InputCLID(self) -> int :
        return self.m_inputCLID
    @InputCLID.setter
    def InputCLID(self, inputCLID : int) :
        self.m_inputCLID = inputCLID
    @property
    def InputVertex(self) -> np.ndarray :
        return self.m_inputVertex
    @InputVertex.setter
    def InputVertex(self, inputVertex : np.ndarray) :
        self.m_inputVertex = inputVertex
    @property
    def InputRadius(self) -> np.ndarray :
        return self.m_inputRadius
    @InputRadius.setter
    def InputRadius(self, inputRadius : np.ndarray) :
        self.m_inputRadius = inputRadius
    @property
    def InputMinInx(self) -> int :
        return self.m_inputMinInx
    @InputMinInx.setter
    def InputMinInx(self, inputMinInx : int) :
        self.m_inputMinInx = inputMinInx
    @property
    def InputEndInx(self) -> int :
        return self.m_inputEndInx
    @InputEndInx.setter
    def InputEndInx(self, inputEndInx : int) :
        self.m_inputEndInx = inputEndInx
    @property
    def InputReverse(self) -> bool :
        return self.m_inputReverse
    @InputReverse.setter
    def InputReverse(self, inputReverse : bool) :
        self.m_inputReverse = inputReverse


class CCommandUpdateBr(CCommandSkelEdit) :
    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_inputBrID = -1
        self.m_inputPos = None

        self.m_undoPos = None
    def clear(self) :
        # input your code
        self.m_inputBrID = -1
        self.m_inputPos = None
        self.m_undoPos = None
        super().clear()
    def process(self) :
        super().process()
        # input your code
        if self.InputBrID == -1 :
            print("not setting br id")
            return
        if self.InputPos is None :
            print("not setting pos")
            return
        
        br = self.InputSkeleton.get_branch(self.InputBrID)
        self.m_undoPos = br.BranchPoint.copy()
        br.BranchPoint = self.InputPos.copy()
        self._refresh_changed_br_data(br.ID)
    def process_undo(self, state):
        super().process_undo(state)
        br = self.InputSkeleton.get_branch(self.InputBrID)
        br.BranchPoint = self.m_undoPos.copy()
        self._refresh_changed_br_data(br.ID)


    # protected
    def _refresh_changed_br_data(self, brID : int) :
        dataInst = self.InputData
        groupID = dataInst.CLInfoIndex

        key = data.CData.make_key(data.CData.s_skelTypeBranch, groupID, brID)
        obj = self.InputData.find_obj_by_key(key)
        obj = dataInst.find_obj_by_key(key)
        if obj is None :
            return

        br = self.InputSkeleton.get_branch(brID)
        obj.Pos = br.BranchPoint

    
    @property
    def InputBrID(self) -> int :
        return self.m_inputBrID
    @InputBrID.setter
    def InputBrID(self, inputBrID : int) :
        self.m_inputBrID = inputBrID
    @property
    def InputPos(self) -> np.ndarray :
        return self.m_inputPos
    @InputPos.setter
    def InputPos(self, inputPos : np.ndarray) :
        self.m_inputPos = inputPos

        

if __name__ == '__main__' :
    pass


# print ("ok ..")

