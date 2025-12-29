import matplotlib.pyplot as plt
#import SimpleITK as sitk
import cv2
import numpy as np
import os, sys
import open3d as o3d
import open3d.core
import open3d.visualization

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
sys.path.append(fileAbsPath)
import scoUtil
import scoMath
import scoData
import scoRenderObj
import scoBuffer
import scoSkeleton
import scoSkeletonVM
import scoSplineSkeleton
from abc import abstractmethod

import open3d as o3d
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering

import math
from skimage.measure import label


class CScoBufferAlg :
    s_color = [
        (1, 0, 0, 1),
        (1, 1, 0, 1),
        (0, 1, 0, 1),
        (0x20/0xff, 0xb2/0xff, 0xaa/0xff, 1),
        (0x3c/0xff, 0xb3/0xff, 0x71/0xff, 1),
        (0x66/0xff, 0x33/0xff, 0x99/0xff, 1),
        (0x80/0xff, 0x00/0xff, 0x00/0xff, 1),
        (0x6b/0xff, 0x8e/0xff, 0x23/0xff, 1),
        (0xa5/0xff, 0x2a/0xff, 0x2a/0xff, 1),
        (0, 1, 1, 1),
    ]

    s_intersectedVoxel = 1000
    s_maskedVoxel = -1000
    s_clearVoxel = -1
    s_listMtrl = []

    @staticmethod
    def init_mtrl() :
        CScoBufferAlg.s_listMtrl = []
        for inx in range(0, len(CScoBufferAlg.s_color)) :
            mtrl = rendering.MaterialRecord()
            mtrl.shader = "defaultUnlit"
            mtrl.base_color = CScoBufferAlg.s_color[inx]
            mtrl.point_size = 5
            CScoBufferAlg.s_listMtrl.append(mtrl)
    @staticmethod
    def get_mtrl_cnt() :
        return len(CScoBufferAlg.s_listMtrl)


    def __init__(self) -> None:
        pass


class CScoAlgSimpleWavePropagation :
    def __init__(self, buf : scoBuffer.CScoBuffer3D) -> None:
        self.m_buf = buf
        self.m_visit = buf.clone('bool')
    

    def find_voxel_index(self, voxelInx : tuple) :
        self.m_visit.all_set_voxel(False)

        tmpQueue = []
        tmpQueue.append(voxelInx)
        self.m_visit.set_voxel(voxelInx, True)

        while True :
            if len(tmpQueue) == 0 :
                break

            voxelInx = tmpQueue.pop(0)
            xCnt, yCnt, zCnt = self.m_buf.Shape

            for zOffset in range(-1, 2) :
                for yOffset in range(-1, 2) :
                    for xOffset in range(-1, 2) :
                        nowVoxelInx = (voxelInx[0] + xOffset, voxelInx[1] + yOffset, voxelInx[2] + zOffset)

                        # clipping
                        if nowVoxelInx[0] < 0 or nowVoxelInx[0] >= xCnt :
                            continue
                        if nowVoxelInx[1] < 0 or nowVoxelInx[1] >= yCnt :
                            continue
                        if nowVoxelInx[2] < 0 or nowVoxelInx[2] >= zCnt :
                            continue

                        if self.m_visit.get_voxel(nowVoxelInx) == True :
                            continue
                        if self.m_buf.get_voxel(nowVoxelInx) > 0 :
                            return nowVoxelInx
                        
                        tmpQueue.append(nowVoxelInx)
                        self.m_visit.set_voxel(nowVoxelInx, True)
        return (-1, -1, -1)


class CScoAlgRegionGrowingWithPlane :
    def __init__(self) -> None:
        pass
    def init_skeleton_info(self, skel : scoSkeleton.CScoSkel) :
        self.m_skel = skel
    def init_output_mask(self, buf : scoBuffer.CScoBuffer3D) :
        self.m_buf = buf
        self.m_visit = self.m_buf.clone("bool")
        self.m_visit.all_set_voxel(False)

    def process(self, segInx : int, th : float) : 
        self.m_visit.all_set_voxel(False)
        self.m_th = th
        self.m_segInx = segInx
        vesselSegment = self.m_skel.m_listVesselSeg[self.m_segInx]
        cnt = vesselSegment.CoordCount
        for inx in range(0, cnt) :
            plane = self.m_skel.get_plane(segInx, inx)
            voxelInx = scoSkeleton.CScoSkel.convert_vec3_to_voxel_index(vesselSegment.ListCoord[inx])
            self.voxelize(plane, voxelInx)
    def voxelize(self, plane : scoMath.CScoPlane, voxelInx : tuple) :
        tmpQueue = []
        tmpQueue.append(voxelInx)
        self.m_visit.set_voxel(voxelInx, True)
        self.m_buf.set_voxel(voxelInx, self.m_segInx)
        xCnt, yCnt, zCnt = self.m_visit.Shape

        vSrc = scoSkeleton.CScoSkel.convert_voxel_index_to_vec3(voxelInx)

        while True :
            if len(tmpQueue) == 0 : 
                break

            voxelInx = tmpQueue.pop(0)

            for zOffset in range(-1, 2) :
                for yOffset in range(-1, 2) :
                    for xOffset in range(-1, 2) :
                        nowVoxelInx = (voxelInx[0] + xOffset, voxelInx[1] + yOffset, voxelInx[2] + zOffset)

                        if nowVoxelInx[0] < 0 or nowVoxelInx[0] >= xCnt :
                            continue
                        if nowVoxelInx[1] < 0 or nowVoxelInx[1] >= yCnt :
                            continue
                        if nowVoxelInx[2] < 0 or nowVoxelInx[2] >= zCnt :
                            continue
                        if self.m_visit.get_voxel(nowVoxelInx) == True :
                            continue
                        if self.m_buf.get_voxel(nowVoxelInx) == CScoBufferAlg.s_clearVoxel :
                            continue
                        #if self.m_skel.m_npMaskImg[nowVoxelInx] == 0 :
                        #    continue
                        dist = plane.get_dist(scoMath.CScoVec3(nowVoxelInx[0], nowVoxelInx[1], nowVoxelInx[2]))
                        if dist > self.m_th :
                            continue
                        # 특정 반경을 넘지 않도록 한다.
                        vDst = scoSkeleton.CScoSkel.convert_voxel_index_to_vec3(nowVoxelInx)
                        if vDst.subtract(vSrc).length() >= 15 : 
                            continue

                        if self.m_buf.get_voxel(nowVoxelInx) >= 0 :
                            self.m_buf.set_voxel(nowVoxelInx, CScoBufferAlg.s_intersectedVoxel)
                            self.m_visit.set_voxel(nowVoxelInx, False)
                        else :
                            self.m_buf.set_voxel(nowVoxelInx, self.m_segInx)
                        
                        tmpQueue.append(nowVoxelInx)
                        self.m_visit.set_voxel(nowVoxelInx, True)

''' 
- branchMask 생성 
    - data : branch index, type : int, initial : -1 
- s_intersectedVoxel에 해당되는 voxel 검출 
    - mask에서 s_intersectedVoxel 추출 
- wave-front propagation 수행 
- branch detection 
- connected vessel segment 추출 
- voronoi 수행 

- input 
    - def init_skeleton_info(self, skel : scoSkeleton.CScoSkel) 
    - def init_mask(self, buf : scoBuffer.CScoBuffer3D), type : int 
- output 
    - init_mask 
'''
class CScoAlgBranchWaveFront : 
    def __init__(self) -> None : 
        pass
    def init_skeleton_info(self, skel : scoSkeleton.CScoSkel) :
        self.m_skel = skel
    def init_output_mask(self, buf : scoBuffer.CScoBuffer3D) : 
        self.m_buf = buf
        self.m_visit = self.m_buf.clone("bool")
        self.m_branchBuf = self.m_buf.clone("int")
        self.m_cacheBuf = self.m_buf.clone("bool")
        self._init_branch_mask()
    def _init_branch_mask(self) :
        self.m_branchBuf.all_set_voxel(-1)

        for branchInx, branch in enumerate(self.m_skel.m_listBranchGroup) :
            for branchCoord in branch.ListBranchCoord :
                voxelInx = self.m_skel.convert_vec3_to_voxel_index(branchCoord)
                self.m_branchBuf.set_voxel(voxelInx, branchInx)

        i = 10


    def process(self) : 
        self.m_listCache = []
        self.m_cacheBuf.all_set_voxel(False)

        # intersected voxel voronoi 적용 
        listCoord = self.m_buf.get_voxel_inx_with_equal(CScoBufferAlg.s_intersectedVoxel)
        cnt = len(listCoord[0])
        for i in range(0, cnt) :
            voxelInx = (listCoord[0][i], listCoord[1][i], listCoord[2][i])

            bRet = self.m_cacheBuf.get_voxel(voxelInx)
            if bRet == True :
                continue

            self.m_listCache.clear()
            branchInx = self._find_branch_inx(voxelInx, CScoBufferAlg.s_intersectedVoxel)

            if branchInx < 0 :
                print(f"{i} : {branchInx}")
                continue

            for cachedVoxelInx in self.m_listCache :
                self._voronoi(branchInx, cachedVoxelInx)
                print(f"{i} : {cachedVoxelInx}({cnt}) : {branchInx} : {self.m_buf.get_voxel(cachedVoxelInx)}")
        
        # 누락 된 voxel voronoi 적용 
        self.m_cacheBuf.all_set_voxel(False)
        listCoord = self.m_buf.get_voxel_inx_with_equal(CScoBufferAlg.s_maskedVoxel)
        cnt = len(listCoord[0])
        for i in range(0, cnt) :
            voxelInx = (listCoord[0][i], listCoord[1][i], listCoord[2][i])

            bRet = self.m_cacheBuf.get_voxel(voxelInx)
            if bRet == True :
                continue

            self.m_listCache.clear()
            branchInx = self._find_branch_inx(voxelInx, CScoBufferAlg.s_maskedVoxel)

            if branchInx < 0 :
                print(f"{i} : {branchInx}")
                continue

            for cachedVoxelInx in self.m_listCache :
                self._voronoi(branchInx, cachedVoxelInx)
                print(f"{i} : {cachedVoxelInx}({cnt}) : {branchInx} : {self.m_buf.get_voxel(cachedVoxelInx)}")

        # branch voxel voronoi 적용 
        print(f"--- branch voronoi start ---")
        for branchInx, branch in enumerate(self.m_skel.m_listBranchGroup) :
            for branchCoord in branch.ListBranchCoord :
                voxelInx = scoSkeleton.CScoSkel.convert_vec3_to_voxel_index(branchCoord)
                self._voronoi(branchInx, cachedVoxelInx)
            
            print(f"branch index : {branchInx}")
        print(f"--- branch voronoi end ---")


    def _find_branch_inx(self, voxelInx : tuple, targetCachedVoxel : int) :
        self.m_visit.all_set_voxel(False) 

        tmpQueue = []
        tmpQueue.append(voxelInx)
        self.m_visit.set_voxel(voxelInx, True)
        
        self.m_cacheBuf.set_voxel(voxelInx, True)
        self.m_listCache.append(voxelInx)

        while True :
            if len(tmpQueue) == 0 :
                break

            voxelInx = tmpQueue.pop(0)
            xCnt, yCnt, zCnt = self.m_buf.Shape

            for zOffset in range(-1, 2) :
                for yOffset in range(-1, 2) :
                    for xOffset in range(-1, 2) :
                        nowVoxelInx = (voxelInx[0] + xOffset, voxelInx[1] + yOffset, voxelInx[2] + zOffset)

                        # clipping
                        if nowVoxelInx[0] < 0 or nowVoxelInx[0] >= xCnt :
                            continue
                        if nowVoxelInx[1] < 0 or nowVoxelInx[1] >= yCnt :
                            continue
                        if nowVoxelInx[2] < 0 or nowVoxelInx[2] >= zCnt :
                            continue
                        if self.m_visit.get_voxel(nowVoxelInx) == True :
                            continue

                        segInx = self.m_buf.get_voxel(nowVoxelInx)
                        if segInx == CScoBufferAlg.s_clearVoxel :
                            continue
                        #mask = self.m_skel.m_npMaskImg[nowVoxelInx]
                        #if mask == 0 :
                        #    continue
                        #if segInx <= 0 :
                        #    continue

                        if segInx == targetCachedVoxel :
                            self.m_listCache.append(nowVoxelInx)
                            self.m_cacheBuf.set_voxel(nowVoxelInx, True)

                        branchInx = self.m_branchBuf.get_voxel(nowVoxelInx)
                        if branchInx >= 0 :
                            return branchInx
                        
                        tmpQueue.append(nowVoxelInx)
                        self.m_visit.set_voxel(nowVoxelInx, True)
        return -1
    def _voronoi(self, branchInx : int, voxelInx : int) :
        branch = self.m_skel.m_listBranchGroup[branchInx]
        coord = scoSkeleton.CScoSkel.convert_voxel_index_to_vec3(voxelInx)

        listMinDist = []
        for vesselInx in branch.ListConnSegmentIndex :
            vessel = self.m_skel.m_listVesselSeg[vesselInx]
            minDist = 100000
            for segCoord in vessel.ListCoord :
                dist = segCoord.subtract(coord).length()
                if dist < minDist :
                    minDist = dist
            
            listMinDist.append(minDist)

        minVesselInx = branch.ListConnSegmentIndex[listMinDist.index(min(listMinDist))]
        self.m_buf.set_voxel(voxelInx, minVesselInx)


class CScoAlgIntersectedVoxel :
    def __init__(self) -> None:
        pass
    def init_skeleton_info(self, skel : scoSkeleton.CScoSkel) :
        self.m_skel = skel
    def init_output_mask(self, buf : scoBuffer.CScoBuffer3D) :
        self.m_buf = buf

    def process(self) : 
        xInx, yInx, zInx = np.where(self.m_skel.MaskImg > 0)
        self.m_buf.set_voxel((xInx, yInx, zInx), CScoBufferAlg.s_intersectedVoxel)



class CAlgSeparatedVessel :
    def __init__(self, skel : scoSkeleton.CScoSkel) -> None:
        self.m_skel = skel
        self.m_separatedMask = scoBuffer.CScoBuffer3D(self.m_skel.MaskImg.shape, "int")
        self.m_listSeparatedSegInx = []
        self.m_listPcdSeparatedMask = []


    def process(self, bDebug : bool) :
        self.m_separatedMask.all_set_voxel(CScoBufferAlg.s_clearVoxel)
        xVoxel, yVoxel, zVoxel = np.where(self.m_skel.MaskImg > 0)
        self.m_separatedMask.set_voxel((xVoxel, yVoxel, zVoxel), CScoBufferAlg.s_maskedVoxel)

        alg = CScoAlgRegionGrowingWithPlane()
        alg.init_skeleton_info(self.m_skel)
        alg.init_output_mask(self.m_separatedMask)

        self.m_listSeparatedSegInx.clear()
        for vesselSegInx, vesselSeg in enumerate(self.m_skel.m_listVesselSeg) :
            if vesselSeg.SegmentType == scoSkeleton.CScoSkelSegment.eSegmentType_None :
                continue
            self.m_listSeparatedSegInx.append(vesselSegInx)
            alg.process(vesselSegInx, 5.0)
            print(f"passed vesselSegInx : {vesselSegInx}")
        
        # wavefront propagation & voroni
        alg = CScoAlgBranchWaveFront()
        alg.init_skeleton_info(self.m_skel)
        alg.init_output_mask(self.m_separatedMask)
        alg.process()

        if bDebug == True :
            self.process_dbg()
    def process_dbg(self) :
        if CScoBufferAlg.s_intersectedVoxel in self.m_listSeparatedSegInx :
            self.m_listSeparatedSegInx.remove(CScoBufferAlg.s_intersectedVoxel)

        self.m_listPcdSeparatedMask.clear()

        for segInx in self.m_listSeparatedSegInx :
            pcd = self.m_separatedMask.get_pcd_with_equal(segInx, (1, 1, 1))
            self.m_listPcdSeparatedMask.append(pcd)

        #'''
        pcd = self.m_separatedMask.get_pcd_with_equal(CScoBufferAlg.s_intersectedVoxel, (1, 1, 1))
        if pcd is not None :
            print('ok intersected pcd')
            self.m_listSeparatedSegInx.append(CScoBufferAlg.s_intersectedVoxel)
            self.m_listPcdSeparatedMask.append(pcd)
        #'''
    

    @property
    def SeparatedMask(self) :
        return self.m_separatedMask
    @property
    def ListSeparatedSegInx(self) :
        return self.m_listSeparatedSegInx
    @property
    def ListPcdSeparatedMask(self) :
        return self.m_listPcdSeparatedMask



class CAlgSplineSkel :
    def __init__(self, splineSkel : scoSplineSkeleton.CScoSplineSkel) -> None:
        self.m_splineSkel = splineSkel
        self.m_splineMask = scoBuffer.CScoBuffer3D(self.m_splineSkel.Shape, "int")
        self.m_listPcd = []
        self.m_listCurveObj = []


    def process(self, bDebug : bool) :
        self.m_splineMask.all_set_voxel(CScoBufferAlg.s_clearVoxel)

        for inx in range(0, len(self.m_splineSkel.ListSplineSeg)) :
            splineSeg = self.m_splineSkel.ListSplineSeg[inx]
            if splineSeg.SegmentType == scoSkeleton.CScoSkelSegment.eSegmentType_None :
                continue

            spline = scoMath.CScoSpline()
            spline.clear_cp()
            for cp in splineSeg.ListCP :
                spline.add_cp(cp)
            spline.process_U(splineSeg.StartU, splineSeg.EndU)

            listVertex = spline.get_all_points()
            xInx, yInx, zInx = self._get_spline_voxel_inx(listVertex)
            self.m_splineMask.set_voxel((xInx, yInx, zInx), inx)

            if bDebug == True :
                key = f"keyCurve_{inx}"
                curveObj = scoRenderObj.CRenderObjCurve(key, spline, 0.5)
                self.m_listCurveObj.append(curveObj)

        if bDebug == True :
            self.process_dbg()
    def process_dbg(self) :
        self.m_listPcd.clear()

        for inx, splineSeg in enumerate(self.m_splineSkel.ListSplineSeg) :
            if splineSeg.SegmentType == scoSkeleton.CScoSkelSegment.eSegmentType_None :
                continue

            pcd = self.m_splineMask.get_pcd_with_equal(inx, (1, 1, 1))
            self.m_listPcd.append(pcd)


    # protected
    def _get_spline_voxel_inx(self, listVertex : list) -> tuple :
        xInx = []
        yInx = []
        zInx = []
        for inx in range(0, len(listVertex) - 1) :
            startVoxelInx = scoSkeleton.CScoSkel.convert_vec3_to_voxel_index(listVertex[inx])
            endVoxelInx = scoSkeleton.CScoSkel.convert_vec3_to_voxel_index(listVertex[inx + 1])

            _, xTmpInx, yTmpInx, zTmpInx = self.m_splineMask.get_line_voxel_inx(startVoxelInx, endVoxelInx)

            xInx += xTmpInx
            yInx += yTmpInx
            zInx += zTmpInx
        return (xInx, yInx, zInx)
    

    @property
    def SplineMask(self) :
        return self.m_splineMask
    @property
    def ListPCD(self) :
        return self.m_listPcd
    @property
    def ListCurveObj(self) :
        return self.m_listCurveObj



class CAlgRemodeling :
    def __init__(
            self, 
            rootNiftiPath : str, rootMode : int, skel : scoSkeleton.CScoSkel, 
            patient : scoData.CPatient, dataPatientType : int,
            cpInterval : int, initRadius : float
            ) -> None:
        self.m_skel = skel
        self.m_patient = patient
        self.m_dataPatientType = dataPatientType
        self.m_skelVM = scoSkeletonVM.CScoSkelVMCreateSplineSkel(skel)
        self.m_skelVM.process(rootNiftiPath, rootMode, patient, dataPatientType, cpInterval, initRadius)

        print("completed skeleton radius & root end-point")

        self.m_splineSkel = self.m_skelVM.SplineSkel
        self.m_remodelingMask = scoBuffer.CScoBuffer3D(self.m_splineSkel.Shape, "int")
        self.m_pcd = None

        print("completed spline skeleton")

    def process(self, cylinderLen : float, interval : float, bDebug : bool) :
        self.m_remodelingMask.all_set_voxel(CScoBufferAlg.s_clearVoxel)
        xInx, yInx, zInx = self.m_skelVM.RootMask.get_voxel_inx_with_greater(0)
        self.m_remodelingMask.set_voxel((xInx, yInx, zInx), 0)

        maxMaskCnt = scoData.CPatient.get_labeling_cnt(self.m_dataPatientType)
        # root는 제외해야 하므로 1부터 시작 
        for targetMask in range(1, maxMaskCnt) :
            for inx in range(0, len(self.m_splineSkel.ListSplineSeg)) :
            #for inx in range(101, 102) :   # 
            #for inx in range(112, 113) :  # Aorta-CT 파생 지점 
            #for inx in range(110, 111) :  # CT 첫번째 파생 지점 
            #for inx in range(108, 109) :  # CT 두번째 파생 지점 
            #for inx in range(48, 49) :  # 
                splineSeg = self.m_splineSkel.ListSplineSeg[inx]
                if splineSeg.SegmentType == scoSkeleton.CScoSkelSegment.eSegmentType_None :
                    continue
                maskID = scoData.CPatient.find_mask_id(self.m_dataPatientType, splineSeg.Name)
                if maskID != targetMask :
                    continue

                self._voxelize(splineSeg, maskID, cylinderLen, interval)

                print(f"complete voxelize : {inx} : {maskID}")

        if bDebug == True :
            self.process_dbg()


    def _voxelize(
            self, 
            splineSeg : scoSplineSkeleton.CScoSplineSegment, voxel : int, 
            cylinderLen : float ,interval : float
            ) :
        spline = scoMath.CScoSpline()
        for cp in splineSeg.ListCP :
            spline.add_cp(cp)
        spline.process_U(splineSeg.StartU, splineSeg.EndU)

        aabb = scoMath.CScoAABB()
        cylinder = scoMath.CScoCylinder()

        xInx = []
        yInx = []
        zInx = []
        nowRatio = interval

        fTmp = 1.0 / spline.MaxRatio

        while nowRatio < spline.MaxRatio - interval :
            worldMat = spline.get_world_matrix(nowRatio, interval)

            #fRatio = nowRatio * fTmp
            #nowRadius = startHalfSize.X + fRatio * (endHalfSize.X - startHalfSize.X)
            radiusInx = math.floor(nowRatio)
            radiusRatio = nowRatio - radiusInx
            startRadius = splineSeg.get_radius(radiusInx)
            endRadius = splineSeg.get_radius(radiusInx + 1)
            nowRadius = startRadius + radiusRatio * (endRadius - startRadius)

            cylinder.HalfSize = scoMath.CScoVec3(nowRadius, nowRadius, cylinderLen)
            cylinder.WorldMatrix = worldMat

            # world 변환을 통해 aabb의 world 영역을 추출 
            aabb.make_min_max(
                scoMath.CScoVec3(-cylinder.HalfSize.X, -cylinder.HalfSize.Y, 0), 
                scoMath.CScoVec3(cylinder.HalfSize.X, cylinder.HalfSize.Y, cylinder.HalfSize.Z)
                )
            min, max = aabb.get_min_max_with_world_matrix(worldMat)
            aabb.make_min_max(min, max)

            # clipping 처리 
            if aabb.Min.X < 0 :
                aabb.Min.X = 0
            elif aabb.Max.X >= self.m_splineSkel.Shape[0] - 0.5 :
                aabb.Max.X = self.m_splineSkel.Shape[0] - 1
            if aabb.Min.Y < 0 :
                aabb.Min.Y = 0
            elif aabb.Max.Y >= self.m_splineSkel.Shape[1] - 0.5 :
                aabb.Max.Y = self.m_splineSkel.Shape[1] - 1
            if aabb.Min.Z < 0 :
                aabb.Min.Z = 0
            elif aabb.Max.Z >= self.m_splineSkel.Shape[2] - 0.5 :
                aabb.Max.Z = self.m_splineSkel.Shape[2] - 1

            for z in range(int(aabb.Min.Z + 0.5), int(aabb.Max.Z + 0.5) + 1) :
                for y in range(int(aabb.Min.Y + 0.5), int(aabb.Max.Y + 0.5) + 1) :
                    for x in range(int(aabb.Min.X + 0.5), int(aabb.Max.X + 0.5) + 1) :
                        # 이전에 이미 방문한 적이 있으므로 건너뛴다. 
                        if self.m_remodelingMask.get_voxel((x, y, z)) > CScoBufferAlg.s_clearVoxel :
                            continue

                        v = scoMath.CScoVec3(x, y, z)
                        bRet = scoMath.CScoMath.intersect_cylinder_vec3(cylinder, v)
                        #if bRet == True :
                        #    xInx.append(x)
                        #    yInx.append(y)
                        #    zInx.append(z)
                        if bRet == True :
                            self.m_remodelingMask.set_voxel((x, y, z), voxel)
            
            nowRatio += interval
            
        #self.m_remodelingMask.set_voxel((xInx, yInx, zInx), voxel)
    def process_dbg(self) :
        self.m_pcd = self.m_remodelingMask.get_pcd_with_greater(CScoBufferAlg.s_clearVoxel, (1, 1, 1))

    # protected


    @property
    def RemodelingMask(self) :
        return self.m_remodelingMask
    @property
    def PCD(self) :
        return self.m_pcd
    

class CAlgRemoveStricture :
    def __init__(self) -> None:
        pass
    def process(self, mask : scoBuffer.CScoBuffer3D) :
        self.m_mask = mask
        self.m_retMask = self.m_mask.clone("uint8")
        self.m_dilate = self.m_mask.clone("uint8")
        dilate = self._dilation(self.m_mask)
        self._xor(self.m_dilate, self.m_mask, dilate)
        
        # dilate에서 coords를 추출한다. 
        # loop coords
        #       self.m_dilate가 0이라면 loop를 건너뛴다. 
        #       coord가 clip 영역 밖이라면 건너뛴다. 
        #       coord에서 주변 5 x 5 x 5를 확인한다. 이 때 확인 대상은 self.m_mask 이다. 
        #       5 x 5 x 5 영역내에서 blob의 갯수를 확인한다. 
        #       blob의 갯수가 2 이상인 부분에 대해 0으로 초기화 한다. 이 때 대상은 self.m_dilate 이다
        coords = self.m_dilate.get_voxel_inx_with_greater(0)
        iCoordCnt = len(coords[0])
        for inx in range(0, iCoordCnt) :
            # print(f"check : {iCoordCnt}, {inx}")
            x = coords[0][inx]
            y = coords[1][inx]
            z = coords[2][inx]
            if z < 2 or z > self.m_dilate.Shape[2] - 3 :
                continue
            if self.m_dilate.get_voxel((x, y, z)) == 0 :
                continue

            npMask = self.m_mask.NpImg[x - 2 : x + 3, y - 2 : y + 3, z - 2 : z + 3]
            # npDilate = self.m_dilate.NpImg[x - 1 : x + 2, y - 1 : y + 2, z - 1 : z + 2]
            # npDilate = self.m_dilate.NpImg[x - 1 : x + 1, y - 1 : y + 1, z - 1 : z + 1]
            npDilate = self.m_dilate.NpImg[x - 0 : x + 1, y - 0 : y + 1, z - 0 : z + 1]

            labelImg = label(npMask)
            blobCnt = np.amax(labelImg)

            if blobCnt > 1 :
                npDilate[::] = 0
        
        xVoxel, yVoxel, zVoxel = self.m_mask.get_voxel_inx_with_greater(0)
        self.m_retMask.set_voxel((xVoxel, yVoxel, zVoxel), 255)
        xVoxel, yVoxel, zVoxel = self.m_dilate.get_voxel_inx_with_greater(0)
        self.m_retMask.set_voxel((xVoxel, yVoxel, zVoxel), 255)
    def clear(self) :
        self.m_mask = None
        self.m_dilate.clear()
        self.m_dilate = None
        self.m_retMask.clear()
        self.m_retMask = None


    @property
    def RemovedStrictureMask(self) :
        return self.m_retMask
    

    # protected
    def _get_clone_mask(self, mask : scoBuffer.CScoBuffer3D) -> scoBuffer.CScoBuffer3D :
        cloneMask = mask.clone("uint8")
        coord = mask.get_voxel_inx_with_greater(0)
        cloneMask.set_voxel(coord, 1)
        return cloneMask
    def _dilation(self, mask : scoBuffer.CScoBuffer3D) -> scoBuffer.CScoBuffer3D :
        dilatedMask = self._get_clone_mask(mask)
        dilatedMask.dilation(3)
        return dilatedMask
    def _erosion(self, mask : scoBuffer.CScoBuffer3D) -> scoBuffer.CScoBuffer3D :
        erosionMask = self._get_clone_mask(mask)
        erosionMask.erosion(3)
        return erosionMask
    def _xor(self, outMask : scoBuffer.CScoBuffer3D, mask0 : scoBuffer.CScoBuffer3D, mask1 : scoBuffer.CScoBuffer3D) :
        npRet = np.bitwise_xor(mask0.NpImg, mask1.NpImg)
        outMask.NpImg = npRet



