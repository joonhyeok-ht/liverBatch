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
        print(f"resampled_points : {resampled_points} len: {len(resampled_points)}")    
        return resampled_points
    @staticmethod
    def gaussian_smoothing(input_points : np.ndarray, sigma=1) -> np.ndarray :
        from scipy.ndimage import gaussian_filter1d
        from scipy.interpolate import interp1d
        # 각 좌표의 가우시안 스무딩
        # sigma = 2  # 가우시안 커널의 표준 편차, #TUNING-POINT
        smoothed_x = gaussian_filter1d(input_points[:, 0], sigma)
        smoothed_y = gaussian_filter1d(input_points[:, 1], sigma)
        smoothed_z = gaussian_filter1d(input_points[:, 2], sigma)
        smoothed_points = np.vstack((smoothed_x, smoothed_y, smoothed_z)).T
        smoothed_points2 = np.concatenate((np.array([input_points[0]]), smoothed_points, np.array([input_points[-1]])), axis=0)
        return smoothed_points2


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
        for idx in range(len(self.InputSkeleton.ListBranch) - 1, 0, -1) :
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
    def _refresh_changed_cl_data(self, clID : int) :
        dataInst = self.InputData
        groupID = self.m_mediator.get_clinfo_index()
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
            polyData = algVTK.CVTK.create_poly_data_sphere(pos, dataInst.CLSize)
            appendFilter.AddInputData(polyData)
        appendFilter.Update()
        mergedPolyData = appendFilter.GetOutput()
        obj.PolyData = mergedPolyData
        self.m_mediator.ref_key(key)

        if cl.is_leaf() == False :
            return

        # endPoint refresh
        key = data.CData.make_key(data.CData.s_skelTypeEndPoint, groupID, clID)
        obj = dataInst.find_obj_by_key(key)
        if obj is None :
            obj = vtkObjEP.CVTKObjEP(cl, dataInst.EPSize)
            if obj.Ready == False :
                return

            obj.KeyType = data.CData.s_skelTypeEndPoint
            obj.Key = data.CData.make_key(obj.KeyType, groupID, cl.ID)
            obj.Color = dataInst.EPColor
            obj.Opacity = 1.0
            obj.Visibility = True
            dataInst.add_vtk_obj(obj)
        endPt = cl.get_end_point()
        obj.Pos = endPt

    # private

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
        groupID = self.m_mediator.get_clinfo_index()

        srcKey = data.CData.make_key(data.CData.s_skelTypeCenterline, groupID, srcID)
        dstKey = data.CData.make_key(data.CData.s_skelTypeCenterline, groupID, dstID)
        srcObj = dataInst.find_obj_by_key(srcKey)
        dstObj = dataInst.find_obj_by_key(dstKey)

        if srcObj is None : 
            print("refresh error : not found srcObj")
            return
        if dstObj is None :
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
        groupID = self.m_mediator.get_clinfo_index()
        clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, groupID, clID)
        epKey = data.CData.make_key(data.CData.s_skelTypeEndPoint, groupID, clID)
        self.m_mediator.remove_key(clKey)
        self.m_mediator.remove_key(epKey)

    
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
            groupID = self.m_mediator.get_clinfo_index()
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
            groupID = self.m_mediator.get_clinfo_index()
            srcKey = data.CData.make_key(data.CData.s_skelTypeBranch, groupID, dst_br_idx)
            self.m_mediator.remove_key(srcKey)
    def _refresh_changed_br_id(self, srcID : int, dstID : int) :
        dataInst = self.InputData
        groupID = self.m_mediator.get_clinfo_index()

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

    
class CCommandMergeCL(CCommandSkelEdit) :
    def __init__(self, mediator) :
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
        concat_vertex = CCommandSkelEdit.gaussian_smoothing(concat_vertex, sigma=5)
        concat_vertex = CCommandSkelEdit.resample_points(concat_vertex)
        dst_cl.Vertex = concat_vertex
        dst_cl.Radius = concat_radius

        groupID = self.m_mediator.get_clinfo_index()
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
    

    @property
    def InputBrID(self) -> int :
        return self.m_inputBrID
    @InputBrID.setter
    def InputBrID(self, inputBrID : int) :
        self.m_inputBrID = inputBrID

class CCommandAutoRemoveCL(CCommandSkelEdit) :
    '''
    only remove leaf centerline
    '''
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_inputListCLID = []
        self.m_listCmd = []
    def clear(self) :
        # input your code
        self.m_inputListCLID.clear()
        for cmd in self.m_listCmd :
            cmd.clear()
        self.m_listCmd.clear()
        super().clear()
    # def process_undo(self) :
    #     reverseListCmd = self.m_listCmd[ : : -1]
    #     for cmd in reverseListCmd :
    #         cmd.process_undo()
    def process(self) :
        super().process()
        # input your code
        if len(self.m_inputListCLID) == 0 :
            print("not setting cl id")
            return
        
        retListCL = []
        for clID in self.m_inputListCLID :
            cl = self.InputSkeleton.get_centerline(clID)
            retListCL.append(cl)
        
        retListBrID = []
        for cl in retListCL :
            if cl.is_leaf() == False :
                continue

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


    def add_clID(self, clID : int) :
        self.m_inputListCLID.append(clID)
    def get_clID_count(self) -> int :
        return len(self.m_inputListCLID)
    def get_clID(self, inx : int) -> int :
        return self.m_inputListCLID[inx]
    
    @property
    def ListCmd(self) -> list :
        return self.m_listCmd
    

class CCommandUpdateCL(CCommandSkelEdit) :
    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_inputCLID = -1
        self.m_inputVertex = None
        self.m_inputMinInx = -1
        self.m_inputReverse = False

        self.m_undoCLVertex = None
        self.m_undoCLRadius = None
    def clear(self) :
        # input your code
        self.m_inputCLID = -1
        self.m_inputVertex = None
        self.m_inputMinInx = -1
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
        if self.InputReverse == True :
            reverseVertex = self.InputVertex[ : : -1].copy()
            startInx = 0
            endInx = self.InputVertex.shape[0]
        else :
            reverseVertex = self.InputVertex.copy()
            startInx = self.InputMinInx
            endInx = cl.Vertex.shape[0]
        
        clVertex = cl.Vertex.copy()
        clVertex[startInx : endInx] = reverseVertex[ : ].copy()
        refinedVertex = CCommandSkelEdit.gaussian_smoothing(clVertex, sigma=5)
        refinedVertex = CCommandSkelEdit.resample_points(refinedVertex)

        # 나중에 radius도 고려해야 함 
        cl.Vertex = refinedVertex

        self._refresh_changed_cl_data(cl.ID)
    def process_undo(self):
        super().process_undo()
        # input your code
        cl = self.InputSkeleton.get_centerline(self.InputCLID)
        cl.Vertex = self.m_undoCLVertex.copy()
        cl.Radius = self.m_undoCLRadius.copy()
        self._refresh_changed_cl_data(cl.ID)

    
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
    def InputMinInx(self) -> int :
        return self.m_inputMinInx
    @InputMinInx.setter
    def InputMinInx(self, inputMinInx : int) :
        self.m_inputMinInx = inputMinInx
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
    def process_undo(self):
        super().process_undo()
        br = self.InputSkeleton.get_branch(self.InputBrID)
        br.BranchPoint = self.m_undoPos.copy()
        self._refresh_changed_br_data(br.ID)


    # protected
    def _refresh_changed_br_data(self, brID : int) :
        dataInst = self.InputData
        groupID = self.m_mediator.get_clinfo_index()

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

