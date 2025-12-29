import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import copy
import SimpleITK as sitk
import math
from scipy.ndimage import label
from collections import Counter
from collections import deque

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileStateProjectPath = os.path.dirname(fileAbsPath)
fileStatePath = os.path.dirname(fileStateProjectPath)
fileAppPath = os.path.dirname(fileStatePath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileStateProjectPath)
sys.path.append(fileStatePath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algMeshLib as algMeshLib
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algImage as algImage
import AlgUtil.algVTK as algVTK

import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer
import Block.reconstruction as reconstruction

import VtkObj.vtkObjLine as vtkObjLine
import VtkObj.vtkObjVertex as vtkObjVertex
import vtkObjInterface as vtkObjInterface

import data as data
import userData as userData
import userDataColon as userDataColon

import com.componentSelectionCL as componentSelectionCL

import command.commandVesselKnife as commandVesselKnife
import commandKnifeColon as commandKnifeColon

import colonDeformInfo as colonDeformInfo



class CComColonMerge(componentSelectionCL.CComDrag) :
    s_knifeKeyType = "knife"
    s_dbgType = "dbg"

    s_pickingDepth = 1000.0
    s_minDragDist = 10

    @staticmethod
    def get_meshlib(vtkMeshInst : vtk.vtkPolyData) :
        npVertex = algVTK.CVTK.poly_data_get_vertex(vtkMeshInst)
        npIndex = algVTK.CVTK.poly_data_get_triangle_index(vtkMeshInst)
        meshLibInst = algMeshLib.CMeshLib.meshlib_create(npVertex, npIndex)
        return meshLibInst
    @staticmethod
    def get_vtkmesh(meshlibInst) -> vtk.vtkPolyData :
        npVertex = algMeshLib.CMeshLib.meshlib_get_vertex(meshlibInst)
        npIndex = algMeshLib.CMeshLib.meshlib_get_index(meshlibInst)
        vtkMesh = algVTK.CVTK.create_poly_data_triangle(npVertex, npIndex)
        return vtkMesh


    def __init__(self, mediator) :
        super().__init__(mediator)
        self.signal_finished_knife = None   # (self, clID : int, vertexIndex : int, tangent : np.ndarray, pt : np.ndarray, mergedMesh : vtkPolyData)
        self.m_knifeKey = ""
        self.m_refMesh = None
    def clear(self) :
        self.signal_finished_knife = None
        super().clear()

    
    # override 
    def ready(self) -> bool :
        return True
    def process_init(self) :
        super().process_init()
        # input your code
        if self.ready() == False :
            return
        
        self.m_knifeKey = ""
        dataInst = self._get_data()
    def process_end(self) :
        # input your code
        if self.ready() == False :
            return
        self.m_knifeKey = ""
        self.App.remove_key_type(CComColonMerge.s_knifeKeyType)
        self.App.remove_key_type(CComColonMerge.s_dbgType)
        self.signal_finished_knife = None
        
        super().process_end()
    
    def click(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        
        super().click(clickX, clickY)
        
        dataInst = self._get_data()
        worldStart, pNearStart, pFarStart= self.App.get_world_from_mouse(self.m_startX, self.m_startY, CComColonMerge.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(self.m_endX, self.m_endY, CComColonMerge.s_pickingDepth)

        self.m_knifeKey = data.CData.make_key(CComColonMerge.s_knifeKeyType, 0, 0)
        inst = vtkObjLine.CVTKObjLine()
        inst.KeyType = CComColonMerge.s_knifeKeyType
        inst.Key = self.m_knifeKey
        inst.set_line_width(2.0)
        inst.set_pos(pFarStart, pFarEnd)
        inst.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        dataInst.add_vtk_obj(inst)

        self.App.ref_key_type(CComColonMerge.s_knifeKeyType)

        self.m_bDrag = True
        return True
    def click_with_shift(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        return True
    def release(self, clickX : int, clickY : int) :
        if self.ready() == False :
            return False
        if self.Drag == False :
            return False
        
        self.App.remove_key_type(CComColonMerge.s_knifeKeyType)

        # drag 영역이 너무 작을 경우 무시
        dx = self.m_endX - self.m_startX
        dy = self.m_endY - self.m_startY
        dist = math.hypot(dx, dy)
        if dist < CComColonMerge.s_minDragDist :
            return False

        self.command_knife_colon(self.m_startX, self.m_startY, self.m_endX, self.m_endY)

        self.m_bDrag = False
        return True
    def move(self, clickX : int, clickY : int, listExceptKeyType=None) :
        if self.ready() == False :
            return
        if self.Drag == False :
            return False
        
        super().move(clickX, clickY, listExceptKeyType)

        dataInst = self._get_data()
        worldStart, pNearStart, pFarStart = self.App.get_world_from_mouse(self.m_startX, self.m_startY, CComColonMerge.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(self.m_endX, self.m_endY, CComColonMerge.s_pickingDepth)
        inst = dataInst.find_obj_by_key(self.m_knifeKey)
        inst.set_pos(pFarStart, pFarEnd)
 
        return True


    # command
    def command_knife_colon(self, startMx, startMy, endMx, endMy) :
        dataInst = self._get_data()
        userdata = self._get_userdata()

        mergeInfo = userdata.get_mergeinfo()
        clinfoinx = mergeInfo.ClinfoInx
        skeleton = self._get_data().get_skeleton(clinfoinx)
        if skeleton is None :
            return

        worldStart, pNearStart, pFarStart = self.App.get_world_from_mouse(startMx, startMy, CComColonMerge.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(endMx, endMy, CComColonMerge.s_pickingDepth)
        cameraInfo = self.App.get_active_camerainfo()
        cameraPos = cameraInfo[3]
        
        cmdKnife = commandKnifeColon.CCommandKnifeColon(self.m_mediator)
        cmdKnife.InputData = dataInst
        cmdKnife.InputSkeleton = skeleton
        cmdKnife.InputWorldA = worldStart
        cmdKnife.InputWorldB = worldEnd
        cmdKnife.InputWorldC = cameraPos
        cmdKnife.process()
        if cmdKnife.OutputKnifedCLID == -1 :
            return

        clID = cmdKnife.OutputKnifedCLID
        vertexIndex = cmdKnife.OutputKnifedIndex
        tangent = cmdKnife.OutputTangent
        pt = cmdKnife.OutputIntersectedPt

        plane = algLinearMath.CScoMath.create_plane(worldStart, worldEnd, cameraPos)

        # tangent align 
        cl = skeleton.get_centerline(clID)
        p0 = cl.get_vertex(vertexIndex)
        p1 = cl.get_vertex(vertexIndex + 1)
        anchorDir = algLinearMath.CScoMath.vec3_normalize(p1 - p0)
        if algLinearMath.CScoMath.dot_vec3(anchorDir, tangent) < 0 :
            tangent = -tangent
            plane = -plane

        invPhyMat = algLinearMath.CScoMath.inv_mat4(mergeInfo.get_physical_mat())
        voxelPt = algLinearMath.CScoMath.mul_mat4_vec3(invPhyMat, pt)

        voxelPlane = mergeInfo.translate_plane(plane, voxelPt)
        abc = voxelPlane[ : 3]
        d = voxelPlane[3]

        # dummy 
        colonDeformInfoInst = colonDeformInfo.CColonDeformInfo()
        colonDeformInfoInst.process(skeleton)
        dummyObjInfo = userdata.DummyObjInfo
        originDummyVertex = dummyObjInfo.Vertex.copy()
        dummyVertex = dummyObjInfo.Vertex
        dummyVertex = self._refine_vertex_en(dummyVertex, colonDeformInfoInst.get_total_curvelen())
        dummyIndex = dummyObjInfo.Face
        deformedVertex = colonDeformInfoInst.transform_deform_radius(dummyVertex, dummyIndex, 10, 0.1)      # 일단 smoothing factor는 고정한다. 
        # deformedVertex = colonDeformInfoInst.transform(dummyVertex, dummyIndex, 20, 0.1)      # 일단 smoothing factor는 고정한다. 
        # deformedVertex = colonDeformInfoInst.transform_enhanced_deform_radius(dummyVertex, dummyIndex, 20, 0.1, self.m_refMesh, int(cl.get_vertex_count() * 0.25))
        dummyObjInfo.Vertex = deformedVertex

        # dummy save
        dummyColonName = mergeInfo.MergeBlenderName
        dummyColonFileName = f"{dummyColonName}_Dummy.obj"
        savePath = os.path.join(userdata.get_merge_out_path(), f"{dummyColonFileName}")
        dummyObjInfo.save(savePath)
        dummyObjInfo.Vertex = originDummyVertex

        polyDataDummy = algVTK.CVTK.create_poly_data_triangle(deformedVertex, dummyIndex)
        mesh = CComColonMerge.get_meshlib(polyDataDummy)
        mesh = algMeshLib.CMeshLib.meshlib_healing(mesh)
        polyDataDummy = CComColonMerge.get_vtkmesh(mesh)

        # rectum
        mrColonRes = userdata.get_mergeinfo_res(1)
        npImgRectum = mrColonRes.Img
        polyDataMerge = self._merge_rectum(
            polyDataDummy, npImgRectum,
            cl, vertexIndex, pt, tangent
        )

        if self.signal_finished_knife is not None :
            self.signal_finished_knife(clID, vertexIndex, tangent, pt, polyDataMerge)

    
    def _get_userdata(self) -> userDataColon.CUserDataColon :
        return self._get_data().find_userdata(userDataColon.CUserDataColon.s_userDataKey)
    
    def _refine_vertex_en(self, vertex : np.ndarray, curveLen : float) -> np.ndarray :
        # 원점 이동 
        center = vertex.mean(axis=0)
        shifted = vertex - center
        rotated = shifted
        # x-axis를 회전축으로 90도 회전
        rotMat = algLinearMath.CScoMath.rot_mat3_from_axis_angle(algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0]), algLinearMath.CScoMath.deg_to_rad(90.0))
        rotMat = algLinearMath.CScoMath.from_mat3_to_mat4(rotMat)
        rotated = algLinearMath.CScoMath.mul_mat4_vec3(rotMat, rotated)
        # y축, z축 반전
        rotated = rotated * np.array([1, -1, -1])
        # colon 시작점을 원점으로 맞춤
        minZ = np.min(rotated[:, 2])
        rotated[:, 2] -= minZ
        # curve에 맞게 길이 colon 길이 조정 
        maxZ = np.max(rotated[:, 2])
        if maxZ > 0.0 :
            rotated[:, 2] = rotated[:, 2] / maxZ * curveLen
        else :
            rotated[:, 2] = 0.0
        
        # # 이 부분에서 dummy에 맞게 회전 적용
        rotMat = algLinearMath.CScoMath.rot_mat3_from_axis_angle(algLinearMath.CScoMath.to_vec3([0.0, 0.0, 1.0]), algLinearMath.CScoMath.deg_to_rad(90.0))
        rotMat = algLinearMath.CScoMath.from_mat3_to_mat4(rotMat)
        rotated = algLinearMath.CScoMath.mul_mat4_vec3(rotMat, rotated)
        # # 여기까지
        return rotated
    def _merge_rectum(
            self, 
            polydataDummy : vtk.vtkPolyData, npImgRectum : np.ndarray,
            cl : algSkeletonGraph.CSkeletonCenterline, knifeIndex : int, knifePt : np.ndarray, knifeTangent : np.ndarray
        ) :
        dataInst = self._get_data()
        userdata = self._get_userdata()
        mergeInfo = userdata.get_mergeinfo()

        targetOrigin = mergeInfo.Origin
        targetSpacing = mergeInfo.Spacing
        targetDirection = mergeInfo.Direction
        targetOffset = mergeInfo.PhaseOffset
        
        targetSize = list(npImgRectum.shape)
        p0 = cl.get_vertex(knifeIndex)
        p1 = cl.get_vertex(knifeIndex + 1)

        phyMat = algVTK.CVTK.get_vtk_phy_matrix_with_spacing(targetOrigin, targetSpacing, targetDirection, targetOffset)
        invPhyMat = algLinearMath.CScoMath.inv_mat4(phyMat)
        plane = algLinearMath.CScoMath.create_plane_normal_point(knifeTangent, knifePt)
        voxelPlane = algLinearMath.CScoMath.transform_plane(invPhyMat, plane, knifePt)

        npImgDummy = algVTK.CVTK.poly_data_voxelize_to_phase(
            polydataDummy,
            targetOrigin, targetSpacing, targetDirection, targetSize, targetOffset
        )
        npTmpImg = npImgDummy.copy()
        dummyVertex = algImage.CAlgImage.get_vertex_from_np(npImgDummy, dtype=np.int32)
        rectumVertex = algImage.CAlgImage.get_vertex_from_np(npImgRectum, dtype=np.int32)

        # ct
        algImage.CAlgImage.set_clear(npTmpImg, 0)
        algImage.CAlgImage.set_value(npTmpImg, dummyVertex, 127)

        voxelPt = algLinearMath.CScoMath.mul_mat4_vec3(invPhyMat, p1)
        voxelPt = np.round(voxelPt).astype(int)
        seed = tuple(voxelPt[0])  # (x, y, z)
        ct_mask_plane = algImage.CAlgImage.region_growing_plane_fast(npTmpImg, seed, voxelPlane, voxel_value_condition=127, dist_range=(0,3))
        npTmpImg[ct_mask_plane] = 255

        p = cl.get_vertex(knifeIndex + 10)
        voxelPt = algLinearMath.CScoMath.mul_mat4_vec3(invPhyMat, p)
        voxelPt = np.round(voxelPt).astype(int)
        seed = tuple(voxelPt[0])  # (x, y, z)
        ct_mask_region = algImage.CAlgImage.region_growing_seed_value_fast(npTmpImg, seed, target_value=127, stop_values=(0, 255))


        # mr 
        algImage.CAlgImage.set_clear(npTmpImg, 0)
        algImage.CAlgImage.set_value(npTmpImg, rectumVertex, 127)
        voxelPt = algLinearMath.CScoMath.mul_mat4_vec3(invPhyMat, p1)
        voxelPt = np.round(voxelPt).astype(int)
        seed = tuple(voxelPt[0])  # (x, y, z)
        mr_mask_plane = algImage.CAlgImage.region_growing_plane_fast(npTmpImg, seed, voxelPlane, voxel_value_condition=127, dist_range=(0,3))
        npTmpImg[mr_mask_plane] = 255


        p = cl.get_vertex(knifeIndex + 10)
        voxelPt = algLinearMath.CScoMath.mul_mat4_vec3(invPhyMat, p)
        voxelPt = np.round(voxelPt).astype(int)
        seed = tuple(voxelPt[0])  # (x, y, z)
        mr_mask_region = algImage.CAlgImage.region_growing_seed_value_fast(npTmpImg, seed, target_value=127, stop_values=(0, 255))

        algImage.CAlgImage.set_clear(npTmpImg, 0)
        algImage.CAlgImage.set_value(npTmpImg, dummyVertex, 255)
        npTmpImg[ct_mask_plane] = 0
        npTmpImg[ct_mask_region] = 0
        if np.count_nonzero(mr_mask_plane) > 0 :
            npTmpImg[mr_mask_plane] = 255
            npTmpImg[mr_mask_region] = 255

        niftiFullPath = "tmp.nii.gz" 
        algImage.CAlgImage.save_nifti_from_np(
            niftiFullPath, 
            npTmpImg, 
            targetOrigin, targetSpacing, targetDirection, (2, 1, 0)
            )
        
        reconParam = mergeInfo.ReconParam
        contour = reconParam.Contour
        algorithm = reconParam.Algorithm
        param = reconParam.Param
        gaussian = reconParam.Gaussian
        resampling = reconParam.ResamplingFactor
        retColonPolyData = reconstruction.CReconstruction.reconstruction_nifti(
            niftiFullPath,
            targetOrigin, targetSpacing, targetDirection, targetOffset,
            contour, param, algorithm, gaussian, resampling
            )

        # decimation
        triCnt = mergeInfo.Decimation
        mesh = CComColonMerge.get_meshlib(retColonPolyData)
        mesh = algMeshLib.CMeshLib.meshlib_healing(mesh)
        mesh = algMeshLib.CMeshLib.meshlib_decimation(mesh, triCnt)
        retColonPolyData = CComColonMerge.get_vtkmesh(mesh)

        if os.path.exists(niftiFullPath) == True :
            os.remove(niftiFullPath)

        return retColonPolyData
    
    

if __name__ == '__main__' :
    pass


# print ("ok ..")

