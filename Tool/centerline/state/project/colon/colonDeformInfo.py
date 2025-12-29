import sys
import os
import numpy as np
import shutil
import glob
import vtk
import subprocess
import copy
import SimpleITK as sitk
import math
from collections import Counter


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
import AlgUtil.algVTK as algVTK
import AlgUtil.algSkeletonGraph as algSkeletonGraph

import vtkObjInterface as vtkObjInterface

import command.curveInfo as curveInfo

import data as data

import userData as userData



class CColonDeformInfo : 
    s_ratioDummyRadius = 0.25       # colon의 시작부터 어느정도까지 dummy radius로 유지할 것인가 (0.0 ~ 1.0)
    s_endDummyRadius = 10           # rectum 끝부터 어느정도까지를 dummy radius로 유지할 것인가 

    @staticmethod
    def find_closest_points_on_centerline_z_only_t_k4(clVertex: np.ndarray, vertex: np.ndarray) :
        """
        z값 기준으로 vertex에 대해 가장 가까운 curve 구간의 인덱스 4개와 t값 계산
        clVertex: (M, 3)
        vertex: (N, 3)
        return:
            nearest_curve_index: (N, 4) — 각 vertex의 (i-1, i, i+1, i+2)
            t_values: (N,) — vertex가 해당 segment 내에서의 상대적 위치 [0, 1]
        """
        k = 4
        clZ = clVertex[:, 2]
        vZ = vertex[:, 2]
        M = len(clZ)
        N = len(vZ)

        nearest_curve_index = np.zeros((N, k), dtype=int)
        t_values = np.zeros(N, dtype=float)

        for n in range(N) :
            vz = vZ[n]
            found = False

            # 0 <= i <= M - 1 범위만 추출
            for i in range(0, M - 1) :
                if int(clZ[i]) <= int(vz) < int(clZ[i + 1]) :
                    found = True
                    break
            if not found :
                if vz < clZ[0] :
                    i = 0
                elif vz >= clZ[M - 1] :
                    i = M - 1
                else :
                    print("warning finding closest point")

            if i == 0 :
                i0 = 0
                i1 = 0
                i2 = 0
                i3 = 0
                t_values[n] = 1.0
            elif i >= M - 2 :
                i0 = M - 2
                i1 = M - 2
                i2 = M - 2
                i3 = M - 2
                t_values[n] = 1.0
            else :
                i0 = i - 1
                i1 = i
                i2 = i + 1
                i3 = i + 2
                # if i + 1 >= 1170 :
                #     a = 0
                denom = clZ[i1 + 1] - clZ[i1]
                t_values[n] = (vz - clZ[i1]) / denom
                t_values[n] = np.clip(t_values[n], 0.0, 1.0)

            nearest_curve_index[n] = [i0, i1, i2, i3]
        return nearest_curve_index, t_values
    @staticmethod
    def calc_radius(polydata : vtk.vtkPolyData, centerline : np.ndarray) -> np.ndarray :
        distCalculator = vtk.vtkImplicitPolyDataDistance()
        distCalculator.SetInput(polydata)
        dist = np.zeros(len(centerline))
        for ptInx, point in enumerate(centerline) :
            radius = abs(distCalculator.EvaluateFunction(point))
            dist[ptInx] = radius
        return dist
    @staticmethod
    def normalize_vertex_array(v : np.ndarray) :
        norm = np.linalg.norm(v, axis=-1, keepdims=True)
        norm[norm == 0] = 1.0
        return v / norm
    @staticmethod
    def compute_skinning_weights_k4(mesh_vertices : np.ndarray, t : np.ndarray) :
        """
        bicubic(Catmull-Rom) 기반 weight 계산
        mesh_vertices: (N, 3)
        t: (N,)

        return:
            weights: (N, 4)
        """
        N = mesh_vertices.shape[0]
        weights = np.zeros((N, 4), dtype=float)

        for i in range(N) :
            tt = t[i]
            tt2 = tt * tt
            tt3 = tt2 * tt

            # Catmull–Rom basis weights
            w0 = -0.5 * tt3 + tt2 - 0.5 * tt
            w1 = 1.5 * tt3 - 2.5 * tt2 + 1.0
            w2 = -1.5 * tt3 + 2.0 * tt2 + 0.5 * tt
            w3 = 0.5 * tt3 - 0.5 * tt2

            weights[i] = [w0, w1, w2, w3]

        weights /= np.sum(weights, axis=1, keepdims=True) + 1e-8
        return weights
    

    def __init__(self) :
        self.m_listFlatMat = []
        self.m_listInvFlatMat = []
        self.m_npFlatVertex = None
        self.m_radius = None
        self.m_skeleton = None
        self.m_curveInfoInst = None
    def clear(self) :
        self.m_listFlatMat.clear()
        self.m_listInvFlatMat.clear()
        self.m_npFlatVertex = None
        self.m_radius = None
        self.m_skeleton = None
        self.m_curveInfoInst = None
    def process(self, skeleton : algSkeletonGraph.CSkeleton) : 
        '''
        '''
        self.m_skeleton = skeleton
        iCLCnt = self.m_skeleton.get_centerline_count()
        cl = self.m_skeleton.get_centerline(0)

        clVertex = cl.Vertex.copy()
        clVertexCnt = clVertex.shape[0]
        self.m_radius = cl.Radius.copy()

        # colon의 시작 방향을 지정 
        self.m_curveInfoInst = curveInfo.CCLCurve()
        N0 = np.array([0.0, 1.0, 0.0])
        B0 = np.array([-1.0, 0.0, 0.0])
        T0 = np.array([0.0, 0.0, -1.0])
        self.m_curveInfoInst.process(clVertex, N0, B0, T0)
        curveLen = curveInfo.CCLCurve.get_curve_len(clVertex)

        print(f"cl vertex count : {cl.get_vertex_count()}")
        print(f"simplfied cl vertex count : {clVertexCnt}")
        print(f"cl tangent count : {self.m_curveInfoInst.Tangent.shape[0]}")
        print(f"curveLen : {curveLen[-1]}")

        # wolrd -> flat 변환 
        self.m_listFlatMat = []
        self.m_listInvFlatMat = []
        for inx in range(0, clVertexCnt) :
            mat = self.m_curveInfoInst.get_transform(inx)
            invMat = algLinearMath.CScoMath.inv_mat4(mat)
            transMat = algLinearMath.CScoMath.translation_mat4(algLinearMath.CScoMath.to_vec3([0.0, 0.0, curveLen[inx]]))
            flatMat = algLinearMath.CScoMath.mul_mat4_mat4(transMat, invMat)
            invFlatMat = algLinearMath.CScoMath.inv_mat4(flatMat)
            self.m_listFlatMat.append(flatMat)
            self.m_listInvFlatMat.append(invFlatMat)
        
        listFlatVertex = []
        for inx in range(0, clVertexCnt) :
            v = clVertex[inx].reshape(-1, 3)
            flatMat = self.m_listFlatMat[inx]
            
            flatV = algLinearMath.CScoMath.mul_mat4_vec3(flatMat, v).reshape(-1)
            listFlatVertex.append(flatV)
        self.m_npFlatVertex = np.array(listFlatVertex)


    def get_physical_plane(self, index : int) :
        pt = self.m_npFlatVertex[index]
        n_phy = np.array([0.0, 0.0, 1.0])

        invPhyMat = self.m_listInvFlatMat[index]
        invRotMat = invPhyMat.copy()
        invRotMat[:3, 3] = 0.0

        normalTransMat = algLinearMath.CScoMath.inv_mat4(invRotMat)
        normalTransMat = normalTransMat.T

        # transform to physical coord
        n_vox = normalTransMat[:3, :3] @ n_phy
        n_vox /= np.linalg.norm(n_vox)
        pt = algLinearMath.CScoMath.mul_mat4_vec3(self.m_listInvFlatMat[index], pt.reshape(-1, 3)).reshape(-1)
        d_vox = -np.dot(n_vox, pt)

        # 최종 plane 반환
        return np.hstack([n_vox, d_vox])
    def get_nearest_vertex_from_clinx(self, phyVertex : np.ndarray, ptInx : int, distRange : float) :
        plane = self.get_physical_plane(ptInx)

        a, b, c, d = plane
        normal = np.array([a, b, c], dtype=float)
        dists = np.dot(phyVertex, normal) + d

        minD = -distRange
        maxD = distRange
        mask = (dists >= minD) & (dists <= maxD)
        indices = np.where(mask)[0]
        return indices


    def transform(
            self, 
            dummyVertex : np.ndarray, dummyIndex : np.ndarray,
            iter=100, relax=0.1
            ) -> np.ndarray :
        '''
        dummyVertex : vtkPolyData로 loading된 dummy vertex
        dummyIndex : vtkPolyData로 loading된 dummy index
        iter : 0이면 mesh smoothing을 하지 않음
        '''
        if self.m_npFlatVertex is None :
            print("invalid flatVertex")
            return None 
        
        self.m_dummyPolydata = algVTK.CVTK.create_poly_data_triangle(dummyVertex, dummyIndex)
        self.m_dummyVertex = dummyVertex
        self.m_dummyIndex = dummyIndex
        
        index, weights = self._get_skinning_info(dummyVertex)
        k = index.shape[1]
        zAxisOrigin, zAxisDir, zAxisLen = self._get_z_axis_ray_info(self.m_dummyVertex)

        # skinning 
        newVertex = np.zeros_like(dummyVertex)
        self.m_dbgFlatVertex = np.zeros_like(dummyVertex)
        for vertexInx in range(0, dummyVertex.shape[0]) :
            transV = np.zeros(3)
            # dbg
            dbgV = np.zeros(3)

            for kInx in range(0, k) :
                clInx = index[vertexInx, kInx]
                weight = weights[vertexInx, kInx]

                invFlatMat = self.m_listInvFlatMat[clInx]
                tmpV = algLinearMath.CScoMath.mul_mat4_vec3(invFlatMat, dummyVertex[vertexInx].reshape(-1, 3))
                transV += weight * tmpV.reshape(-1)

                # dbg
                tmpDbgV = algLinearMath.CScoMath.mul_mat4_vec3(invFlatMat, zAxisOrigin[vertexInx].reshape(-1, 3))
                dbgV += weight * tmpDbgV.reshape(-1)
            newVertex[vertexInx] = transV
            # dbg
            self.m_dbgFlatVertex[vertexInx] = dbgV

        # smoothing 
        if iter > 0 :
            polydata = algVTK.CVTK.create_poly_data_triangle(newVertex, dummyIndex)
            polydata = algVTK.CVTK.laplacian_smoothing(polydata, iter, relax)
            newVertex = algVTK.CVTK.poly_data_get_vertex(polydata)

        return newVertex
    def transform_deform_radius(
            self, 
            dummyVertex : np.ndarray, dummyIndex : np.ndarray,
            iter=100, relax=0.1
            ) -> np.ndarray :
        '''
        dummyVertex : vtkPolyData로 loading된 dummy vertex
        dummyIndex : vtkPolyData로 loading된 dummy index
        iter : 0이면 mesh smoothing을 하지 않음
        '''
        if self.m_npFlatVertex is None :
            print("invalid flatVertex")
            return None 
        
        self.m_dummyPolydata = algVTK.CVTK.create_poly_data_triangle(dummyVertex, dummyIndex)
        self.m_dummyVertex = dummyVertex
        self.m_dummyIndex = dummyIndex

        index, weights = self._get_skinning_info(self.m_dummyVertex)
        k = index.shape[1]
        zAxisOrigin, zAxisDir, zAxisLen = self._get_z_axis_ray_info(self.m_dummyVertex)
        deformVertex = self._deform_radius(
            self.m_dummyVertex, 
            zAxisOrigin, zAxisDir, zAxisLen, index
            )

        # skinning 
        newVertex = np.zeros_like(deformVertex)
        self.m_dbgFlatVertex = np.zeros_like(deformVertex)
        for vertexInx in range(0, deformVertex.shape[0]) :
            transV = np.zeros(3)
            # dbg
            dbgV = np.zeros(3)

            for kInx in range(0, k) :
                clInx = index[vertexInx, kInx]
                weight = weights[vertexInx, kInx]

                invFlatMat = self.m_listInvFlatMat[clInx]
                tmpV = algLinearMath.CScoMath.mul_mat4_vec3(invFlatMat, deformVertex[vertexInx].reshape(-1, 3))
                transV += weight * tmpV.reshape(-1)

                # dbg
                tmpDbgV = algLinearMath.CScoMath.mul_mat4_vec3(invFlatMat, zAxisOrigin[vertexInx].reshape(-1, 3))
                dbgV += weight * tmpDbgV.reshape(-1)
            newVertex[vertexInx] = transV
            # dbg
            self.m_dbgFlatVertex[vertexInx] = dbgV

        # smoothing 
        if iter > 0 :
            polydata = algVTK.CVTK.create_poly_data_triangle(newVertex, dummyIndex)
            polydata = algVTK.CVTK.laplacian_smoothing(polydata, iter, relax)
            newVertex = algVTK.CVTK.poly_data_get_vertex(polydata)

        return newVertex
    def get_total_curvelen(self) -> int :
        if self.m_skeleton is None : 
            return 0
        
        cl = self.m_skeleton.get_centerline(0)
        clVertex = cl.Vertex.copy()
        curveLen = curveInfo.CCLCurve.get_curve_len(clVertex)
        return curveLen[-1]
    

    # protected
    def _get_z_axis_ray_info(self, targetVertex : np.ndarray) -> tuple :
        '''
        desc 
            - targetVertex을 z축에서 발사하는 ray로 기술할때의 ray 정보를 구한다.
        ret : (zAxisOrigin : np.ndarray, zAxisDir : np.ndarray, zAxisLen : np.ndarray)
        '''
        zAxisOrigin = targetVertex.copy()
        zAxisOrigin[ : , : 2] = 0.0
        zAxisDir = CColonDeformInfo.normalize_vertex_array(targetVertex - zAxisOrigin)
        zAxisLen = np.linalg.norm(targetVertex - zAxisOrigin, axis=-1, keepdims=True)
        return (zAxisOrigin, zAxisDir, zAxisLen)
    def _get_skinning_info(self, targetVertex : np.ndarray) -> tuple :
        '''
        desc 
            - targetVertex의 skinning 정보를 얻는다. 
            - skinning 정보는 index와 weight가 있으며, 각각 k=4를 기준으로 한다.
            - targetVertex : (N x 3)
        ret : (index : np.ndarray (N x 4, int), weight : np.ndarray (N x 4, float))
        '''
        index, t = CColonDeformInfo.find_closest_points_on_centerline_z_only_t_k4(self.m_npFlatVertex, targetVertex)
        weights = CColonDeformInfo.compute_skinning_weights_k4(targetVertex, t)
        return (index, weights)
    def _deform_radius(
            self,
            targetVertex : np.ndarray,
            zAxisOrigin : np.ndarray, zAxisDir : np.ndarray, zAxisLen : np.ndarray, skinningIndex : np.ndarray
            ) -> np.ndarray :
        dummyRadius = CColonDeformInfo.calc_radius(self.m_dummyPolydata, self.m_npFlatVertex)
        # delta 보정 
        iTotalCnt = self.m_radius.shape[0]
        zeroCnt = int(iTotalCnt * CColonDeformInfo.s_ratioDummyRadius)

        deformVertex = np.zeros_like(targetVertex)
        for vertexInx in range(0, targetVertex.shape[0]) :
            ptInx = skinningIndex[vertexInx, 1]
            ratio = self.m_radius[ptInx] / dummyRadius[ptInx]

            if ptInx < zeroCnt :
                ratio = 1.0
            if ptInx > iTotalCnt - CColonDeformInfo.s_endDummyRadius :
                ratio = 1.0

            len = zAxisLen[vertexInx]
            len = len * ratio
            if len <= 0.0 :
                len = 1.0
            deformVertex[vertexInx] = zAxisOrigin[vertexInx] + len * zAxisDir[vertexInx]
        return deformVertex




if __name__ == '__main__' :
    pass


# print ("ok ..")

