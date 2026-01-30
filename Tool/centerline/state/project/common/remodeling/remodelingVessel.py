import sys
import os
import numpy as np
import shutil
import subprocess
import math


from scipy import ndimage
from scipy.spatial import KDTree
from scipy.spatial import Delaunay
from scipy.ndimage import maximum_filter
from scipy.interpolate import interp1d
from scipy.ndimage import gaussian_filter
from scipy.ndimage import gaussian_filter1d

import SimpleITK as sitk
import matplotlib.pyplot as plt

import vtk
import vtkmodules.vtkInteractionStyle
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkFiltersSources import vtkCylinderSource
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkRenderer
)
from vtk.util import numpy_support



fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileCommonPath = os.path.dirname(fileAbsPath)
fileStateProjectPath = os.path.dirname(fileCommonPath)
fileStatePath = os.path.dirname(fileStateProjectPath)
fileAppPath = os.path.dirname(fileStatePath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileCommonPath)
sys.path.append(fileStateProjectPath)
sys.path.append(fileStatePath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algOpen3D as algOpen3D
import AlgUtil.algVTK as algVTK
import AlgUtil.algMeshLib as algMeshLib
import AlgUtil.algImage as algImage
import AlgUtil.algGeometry as algGeometry
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algSpline as algSpline

import command.curveInfo as curveInfo


class CTreeVesselRemodelingAnchorNode :
    def __init__(self) :
        self.m_parent = None
        self.m_listConnCLID = []
        self.m_listChildNode = []
        self.m_polydata = None
        self.m_resampledVertex = None
        self.m_resampledRadius = None
    def clear(self) :
        self.m_parent = None
        self.m_listConnCLID.clear()
        self.m_polydata = None
        self.m_resampledVertex = None
        self.m_resampledRadius = None

        iCnt = self.child_node_count()
        for inx in range(0, iCnt) :
            childNode = self.child_node(inx)
            childNode.clear()
        self.m_listChildNode.clear()

    def add_conn_clid(self, clID : int) :
        self.m_listConnCLID.append(clID)
    def conn_clid_count(self) -> int :
        return len(self.m_listConnCLID)
    def conn_clid(self, inx : int) -> int :
        return self.m_listConnCLID[inx]

    def add_child_clid(self, clID : int) :
        node = CTreeVesselRemodelingAnchorNode()
        node.add_conn_clid(clID)
        node.Parent = self
        self.m_listChildNode.append(node)
    def child_node_count(self) -> int :
        return len(self.m_listChildNode)
    def child_node(self, inx : int) :
        return self.m_listChildNode[inx]


    @property
    def Parent(self) :
        return self.m_parent
    @Parent.setter
    def Parent(self, parent) :
        self.m_parent = parent
    @property
    def PolyData(self) -> vtk.vtkPolyData :
        return self.m_polydata
    @PolyData.setter
    def PolyData(self, polydata : vtk.vtkPolyData) :
        self.m_polydata = polydata
    @property
    def ResampledVertex(self) -> np.ndarray :
        return self.m_resampledVertex
    @ResampledVertex.setter
    def ResampledVertex(self, resampledVertex : np.ndarray) :
        self.m_resampledVertex = resampledVertex
    @property
    def ResampledRadius(self) -> np.ndarray :
        return self.m_resampledRadius
    @ResampledRadius.setter
    def ResampledRadius(self, resampledRadius : np.ndarray) :
        self.m_resampledRadius = resampledRadius



class CResampledFrameCL(curveInfo.CCLCurve) :
    @staticmethod
    def check_intersected_disk(
        centerP0 : np.ndarray, centerP1 : np.ndarray,
        t0 : np.ndarray, t1 : np.ndarray,
        r0 : float, r1 : float,
        touchAsIntersection = False
        ) -> bool :
        EPS = 1e-3
        tol = 1e-3

        p0 = centerP0.reshape(-1)
        p1 = centerP1.reshape(-1)
        t0 = t0.reshape(-1)
        t1 = t1.reshape(-1)
        n0 = CTreeVesselRemodeling.normalize(t0)
        n1 = CTreeVesselRemodeling.normalize(t1)

        # cross product -> 교차선 방향(비정규)
        d = np.cross(n0, n1)
        dnorm = np.linalg.norm(d)

        # 평행하거나 거의 평행
        if dnorm < EPS :
            # 평행 평면: 같은 평면인지 확인
            if abs(np.dot(n0, p1 - p0)) < tol :
                # 동일 평면: 평면 내에서의 2D 중심 거리로 원-원 교차 검사
                # p1 - p0를 평면 성분으로 투영
                v = p1 - p0
                v_plane = v - n0 * np.dot(n0, v)
                center_dist = np.linalg.norm(v_plane)
                if touchAsIntersection :
                    return center_dist <= (r0 + r1) + tol
                else :
                    return center_dist < (r0 + r1) - tol
            else :
                # 서로 다른 평행 평면 => 절대 겹치지 않음
                return False

        # 교차선 존재: 단위 방향
        d_hat = d / dnorm

        # 교차선 위의 한 점 Q를 구하기 (n0·Q = n0·p0, n1·Q = n1·p1, d_hat·Q = 0)
        # 행렬 풀기
        A = np.vstack([n0, n1, d_hat])
        b = np.array([np.dot(n0, p0), np.dot(n1, p1), 0.0])
        # A가 invertible이어야 함 (위에서 dnorm > EPS이면 invertible)
        Q = np.linalg.solve(A, b)

        # 각 중심의 L에 대한 스칼라 위치와 수직거리
        s0 = np.dot(d_hat, p0 - Q)
        s1 = np.dot(d_hat, p1 - Q)
        w0 = (p0 - Q) - s0 * d_hat
        w1 = (p1 - Q) - s1 * d_hat
        h0 = np.linalg.norm(w0)
        h1 = np.linalg.norm(w1)

        # 원이 직선과 교차하지 않으면 디스크는 그 교차선에서 아무 구간도 만들지 못함 -> 교차 없음
        if h0 > r0 + tol or h1 > r1 + tol :
            return False

        # 교차 시 구간 길이
        a0 = np.sqrt(max(0.0, r0*r0 - h0*h0))
        a1 = np.sqrt(max(0.0, r1*r1 - h1*h1))
        int0 = (s0 - a0, s0 + a0)
        int1 = (s1 - a1, s1 + a1)

        # 두 구간의 겹침 판정
        start = max(int0[0], int1[0])
        end   = min(int0[1], int1[1])
        if touchAsIntersection :
            return end >= start - tol
        else:
            return end > start + tol


    def __init__(self) :
        super().__init__()
        self.m_radius = None
        self.m_resampleIndex = []
        self.m_resampledVertex = None
        self.m_resampledRadius = None
        self.m_resampledTangent = None
        self.m_resampledNormal = None
        self.m_resampledBinormal = None
    def clear(self) :
        self.m_point = None
        self.m_resampleIndex.clear()
        self.m_resampledVertex = None
        self.m_resampledRadius = None
        self.m_resampledTangent = None
        self.m_resampledNormal = None
        self.m_resampledBinormal = None
        super().clear()
    def process(self, points : np.ndarray, radius : np.ndarray) :
        super().process(points, None, None, None)
        # input your code

        self.m_radius = radius

        N = len(points)

        self._find_resample_index()

        self.m_resampledVertex = []
        self.m_resampledRadius = []
        self.m_resampledTangent = []
        self.m_resampledNormal = []
        self.m_resampledBinormal = []
        for resampledInx in self.m_resampleIndex :
            self.m_resampledVertex.append(self.m_point[resampledInx])
            self.m_resampledRadius.append(self.m_radius[resampledInx])
            self.m_resampledTangent.append(self.m_tangent[resampledInx])
            self.m_resampledNormal.append(self.m_normal[resampledInx])
            self.m_resampledBinormal.append(self.m_binormal[resampledInx])
        self.m_resampledVertex = np.array(self.m_resampledVertex)
        self.m_resampledRadius = np.array(self.m_resampledRadius)
        self.m_resampledTangent = np.array(self.m_resampledTangent)
        self.m_resampledNormal = np.array(self.m_resampledNormal)
        self.m_resampledBinormal = np.array(self.m_resampledBinormal)


    def create_cylinder_polydata(self, resolution : int = 16) -> vtk.vtkPolyData :
        """
        points : (N, 3) numpy array
        radii  : (N,) numpy array
        resolution : int, number of vertices per circle, 이 부분은 theta 기준으로 바뀌어야 함
        return: vertices (M,3), faces (K,3)
        """

        N = len(self.ResampledVertex)
        vertices = []
        faces = []
        circle_idx = []

        for i in range(N) :
            binormal = self.ResampledBinormal[i]
            normal = self.ResampledNormal[i]

            # circle points
            circle = []
            for j in range(resolution) :
                theta = 2 * np.pi * j / resolution
                dir_vec = np.sin(theta) * normal + np.cos(theta) * binormal
                circle.append(self.ResampledVertex[i] + self.ResampledRadius[i] * dir_vec)

            idx_start = len(vertices)
            vertices.extend(circle)
            circle_idx.append(range(idx_start, idx_start + resolution))

        # Connect circles
        for i in range(N - 1) :
            c1 = circle_idx[i]
            c2 = circle_idx[i + 1]

            # v1_first = vertices[c1[0]]
            # c2_verts = np.array([vertices[idx] for idx in c2])
            # dists = np.linalg.norm(c2_verts - v1_first, axis=1)
            # offset = np.argmin(dists)
            # c2 = list(np.roll(c2, -offset))

            # 1. 두 단면의 vertex 좌표 가져오기
            verts1 = np.array([vertices[idx] for idx in c1])
            verts2 = np.array([vertices[idx] for idx in c2])

            # 2. 두 단면 vertex 쌍 간 거리 계산
            dists = np.linalg.norm(verts1[:, None, :] - verts2[None, :, :], axis=2)

            # 3. 최소 거리 쌍 (i,j) 찾기
            i_min, j_min = np.unravel_index(np.argmin(dists), dists.shape)

            # 4. 두 단면 모두 np.roll 적용
            c1 = list(np.roll(c1, -i_min))
            c2 = list(np.roll(c2, -j_min))

            for j in range(resolution) :
                v0 = c1[j]
                v1 = c1[(j + 1) % resolution]
                v2 = c2[j]
                v3 = c2[(j + 1) % resolution]

                # triangle strip
                faces.append([v0, v1, v2])
                faces.append([v2, v1, v3])

        # Start cap
        c0 = circle_idx[0]
        center0 = len(vertices)
        vertices.append(self.ResampledVertex[0])
        for j in range(resolution) :
            faces.append([center0, c0[(j + 1) % resolution], c0[j]])
        # End cap
        cN = circle_idx[-1]
        centerN = len(vertices)
        vertices.append(self.ResampledVertex[-1])
        for j in range(resolution) :
            faces.append([centerN, cN[j], cN[(j + 1) % resolution]])

        vertices = np.array(vertices)
        faces = np.array(faces)
        polydata = algVTK.CVTK.create_poly_data_triangle(vertices, faces)

        return polydata


    # protected
    def _find_resample_index(self) :
        '''
        - index 0에서 시작
        - s_min 만큼 떨어진 지점의 point searching
            - s_min : radius * 0.5
        - check disk intersection
            - true일 경우 다음 point로 넘김
            - 끝점일 경우 처리를 깔끔하게 해야 되는데 ..
        '''

        state = 0
        state0TargetInx = 0
        state0RetInx = -1
        state1RetInx = -1

        self.m_resampleIndex.clear()
        self.m_resampleIndex.append(state0TargetInx)
        s_min = self.m_radius[state0TargetInx] * 0.5
        while True :
            '''
            state
                - 0 : searching point
                - 1 : searching not intersected disk
                - 2 : add resample point
            '''

            if state == 0 :
                segLen = 0.0
                state0RetInx = -1

                for j in range(state0TargetInx + 1, len(self.m_point)) :
                    seg = self.m_point[j] - self.m_point[j - 1]
                    segLen += np.linalg.norm(seg)
                    if segLen >= s_min :
                        state0RetInx = j
                        state = 1
                        break
                    j += 1

                # 이 부분은 마지막 point를 무조건 포함시킬 것인가?에 대한 판단을 따져봐야 함
                if state0RetInx == -1 :
                    state1RetInx = len(self.m_point) - 1
                    state = 2
            elif state == 1 :
                state1RetInx = -1

                p0 = self.m_point[state0TargetInx]
                t0 = self.Tangent[state0TargetInx]
                r0 = self.m_radius[state0TargetInx]
                for j in range(state0RetInx, len(self.m_point)) :
                    p1 = self.m_point[j]
                    t1 = self.Tangent[j]
                    r1 = self.m_radius[j]
                    bRet = CResampledFrameCL.check_intersected_disk(p0, p1, t0, t1,r0, r1)
                    if bRet == True :
                        j += 1
                    else :
                        state1RetInx = j
                        state = 2
                        break

                # 이 부분은 마지막 point를 무조건 포함시킬 것인가?에 대한 판단을 따져봐야함
                if state1RetInx == -1 :
                    state1RetInx = len(self.m_point) - 1
                    state = 2
            else :
                self.m_resampleIndex.append(state1RetInx)

                if state1RetInx == len(self.m_point) - 1 :
                    break
                else :
                    state0TargetInx = state1RetInx
                    s_min = self.m_radius[state0TargetInx] * 0.5
                    state = 0


    @property
    def ResampledVertex(self) -> np.ndarray :
        return self.m_resampledVertex
    @property
    def ResampledRadius(self) -> np.ndarray :
        return self.m_resampledRadius
    @property
    def ResampledTangent(self) -> np.ndarray :
        return self.m_resampledTangent
    @property
    def ResampledNormal(self) -> np.ndarray :
        return self.m_resampledNormal
    @property
    def ResampledBinormal(self) -> np.ndarray :
        return self.m_resampledBinormal


class CTreeVesselRemodeling :
    s_minRadius = 0.2

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
    @staticmethod
    def parent_tangent(vecs: np.ndarray) -> np.ndarray :
        v = vecs[-1] - vecs[-2]
        return v / np.linalg.norm(v)
    @staticmethod
    def child_tangent(vecs: np.ndarray) -> np.ndarray :
        v = vecs[1] - vecs[0]
        return v / np.linalg.norm(v)
    @staticmethod
    def normalize(v : np.ndarray) :
        return v / np.linalg.norm(v)
    @staticmethod
    def find_outside_inx(spherePos : np.ndarray, radius : float, cl : algSkeletonGraph.CSkeletonCenterline) -> int :
        return CTreeVesselRemodeling.find_outside_inx_by_vertex(spherePos, radius, cl.Vertex)
    @staticmethod
    def find_outside_inx_by_vertex(spherePos : np.ndarray, radius : float, vertex : np.ndarray) -> int :
        spherePos = spherePos.reshape(-1)
        dist = np.linalg.norm(vertex - spherePos, axis=1)
        outSideInx = np.where(dist > radius)[0]
        if outSideInx.size == 0 :
            return -1
        return outSideInx[0]
    @staticmethod
    def resampling_centerline(clPt : np.ndarray, clRadius : np.ndarray, spacing : float) :
        '''
        Returns
        -------
        newPts : np.ndarray
            (M, 3) 균일 간격으로 보간된 점들
        newRadius : np.ndarray
            (M,) 각 점에 대응되는 반경
        '''
        diffs = np.diff(clPt, axis=0)
        seg_lengths = np.linalg.norm(diffs, axis=1)
        dist = np.concatenate(([0], np.cumsum(seg_lengths)))
        total_length = dist[-1]

        new_dist = np.arange(0, total_length, spacing)
        if new_dist.size == 0 :
            return None
        if new_dist[-1] < total_length :
            new_dist = np.append(new_dist, total_length)

        newPts = np.zeros((len(new_dist), 3))
        for i in range(3) :
            newPts[:, i] = np.interp(new_dist, dist, clPt[:, i])

        newRadius = None
        if clRadius is not None :
            newRadius = np.interp(new_dist, dist, clRadius)

        return newPts, newRadius
    @staticmethod
    def smooth_centerline(vertices: np.ndarray, sigma: float = 1.0) -> np.ndarray:
        smoothed = vertices.copy()
        for i in range(3):
            smoothed[:, i] = gaussian_filter1d(vertices[:, i], sigma=sigma)
        return smoothed
    @staticmethod
    def bridge_mesh(A : vtk.vtkPolyData, B : vtk.vtkPolyData) -> vtk.vtkPolyData :
        meshA = CTreeVesselRemodeling.get_meshlib(A)
        meshB = CTreeVesselRemodeling.get_meshlib(B)

        mesh = algMeshLib.CMeshLib.meshlib_boolean_union(meshA, meshB)
        if mesh is None :
            return None
        mesh = algMeshLib.CMeshLib.meshlib_healing(mesh)

        mergedPolydata = CTreeVesselRemodeling.get_vtkmesh(mesh)

        return mergedPolydata


    def __init__(self) :
        self.m_inputSkeleton = None
        self.m_inputRadiusMargin = 0.0
        self.m_rootAnchorNode = None
        self.m_mergedMesh = None
        self.m_mainSkeleton = None
        self.subToMainClID = {}

        self.m_listResampleVertex = None
        self.m_listResampleRadius = None
        self.m_kdTree = None
        self.m_dbgList = []

    def clear(self) :
        if self.m_rootAnchorNode is not None :
            self.m_rootAnchorNode.clear()
        self.m_rootAnchorNode = None
        self.m_inputSkeleton = None
        self.m_inputRadiusMargin = 0.0
        self.m_mergedMesh = None
        self.m_mainSkeleton = None
        self.subToMainClID = {}

        self.m_listResampleVertex = None
        self.m_listResampleRadius = None
        self.m_kdTree = None

        self.m_dbgList.clear()
        self.m_dbgList = []
    def process(self) :
        if self.m_rootAnchorNode is not None :
            self.m_rootAnchorNode.clear()
        self.m_rootAnchorNode = None

        if self.InputSkeleton is None :
            return None


        rootCLID = self.InputSkeleton.RootCenterline.ID
        self._make_anchor(rootCLID)
        self._make_anchor_mesh()
        self.m_mergedMesh = self._merge_anchor_mesh()

    def build_kd_tree(self) -> KDTree :
        if self.m_listResampleVertex is None :
            return None
        self.m_kdTree = KDTree(self.m_listResampleVertex)
    def get_nearest_pos_radius(self, vertex : np.ndarray) -> tuple :
        '''
        ret : (nearestPos, radius)
            None -> not found nearest point info
        '''
        if self.m_kdTree is None :
            return None
        _, npNNIndex = self.m_kdTree.query(vertex.reshape(-1, 3), k=1)
        nearestInx = npNNIndex[0]
        return (self.m_listResampleVertex[nearestInx].reshape(-1, 3), self.m_listResampleRadius[nearestInx])




    # protected
    def _make_anchor(self, rootCLID : int) :
        self.m_rootAnchorNode = CTreeVesselRemodelingAnchorNode()
        anchorNode = self.m_rootAnchorNode
        anchorNode.add_conn_clid(rootCLID)
        self.__recur_make_anchor(anchorNode)
        
    def gaussian_smooth_from_middle(self, values, start_idx, end_value=1.0, sigma=1.0):
        """
        values: list or np.ndarray
        start_idx: 이 index부터 smoothing 시작
        end_value: 마지막 값 (예: 1)
        sigma: gaussian 강도
        """
        values = np.asarray(values, dtype=np.float64)
        n = len(values)

        if start_idx < 0 or start_idx >= n - 1:
            raise ValueError("start_idx must be in [0, n-2]")

        out = values.copy()

        # smoothing 대상 구간
        tail_len = n - start_idx
        start_value = values[start_idx]

        # 1) 선형 taper 생성
        base = np.linspace(start_value, end_value, tail_len)

        # 2) Gaussian smoothing (tail에만)
        smooth_tail = gaussian_filter1d(base, sigma=sigma, mode="nearest")

        # 3) 끝값 고정
        smooth_tail[0] = start_value
        smooth_tail[-1] = end_value

        out[start_idx:] = smooth_tail
        return out
    def _make_anchor_mesh(self) :
        if self.m_rootAnchorNode is None :
            return
        self.m_listResampleVertex = None
        self.m_listResampleRadius = None
        listNode = [self.m_rootAnchorNode]
        while listNode :
            node = listNode.pop(0)
            iCnt = node.conn_clid_count()

            mergedVertex = None
            mergedRadius = None
            for inx in range(0, iCnt) :
                clID = node.conn_clid(inx)
                cl = self.InputSkeleton.get_centerline(clID)
                clippedRadius = self.__refine_cl_radius(cl)
                if self.m_mainSkeleton is None:
                    if mergedVertex is None :
                        mergedVertex = cl.Vertex
                        mergedRadius = clippedRadius
                    else :
                        mergedVertex = np.vstack((mergedVertex, cl.Vertex[ : ]))
                        mergedRadius = np.hstack((mergedRadius, clippedRadius[ : ]))
                else:
                    maincl = self.m_mainSkeleton.get_centerline(self.subToMainClID.get(clID, 0))
                    if not maincl.is_leaf() and cl.is_leaf():
                        clippedRadius = self.gaussian_smooth_from_middle(clippedRadius, int(len(clippedRadius)/3), 0.5)
                        
                    if mergedVertex is None :
                        mergedVertex = cl.Vertex
                        mergedRadius = clippedRadius
                    else :
                        mergedVertex = np.vstack((mergedVertex, cl.Vertex[ : ]))
                        mergedRadius = np.hstack((mergedRadius, clippedRadius[ : ]))

            parent = node.Parent
            if parent is not None :
                startVertex = mergedVertex[0].reshape(-1, 3)
                resampledVertex = parent.ResampledVertex
                resampledRadius = parent.ResampledRadius

                dists = np.linalg.norm(resampledVertex - startVertex, axis=1)
                nearestVertexInx = np.argmin(dists)

                spherePos = resampledVertex[nearestVertexInx].reshape(-1, 3)
                sphereRadius = resampledRadius[nearestVertexInx]

                outsideInx = CTreeVesselRemodeling.find_outside_inx_by_vertex(spherePos, sphereRadius, mergedVertex)
                if outsideInx != -1 and outsideInx !=  mergedVertex.shape[0] - 1 :
                    mergedVertex = np.vstack((spherePos.reshape(-1, 3), mergedVertex[outsideInx : ]))
                    mergedRadius = np.hstack((mergedRadius[outsideInx], mergedRadius[outsideInx : ]))
                    # mergedVertex = np.vstack((spherePos.reshape(-1, 3), mergedVertex[ : ]))
                    # mergedRadius = np.hstack((mergedRadius[outsideInx], mergedRadius[ : ]))

            # radius margin 적용
            mergedRadius = np.maximum(mergedRadius + self.InputRadiusMargin, self.s_minRadius)
            # 1.0 간격의 resampling 추가
            mergedVertex, mergedRadius = CTreeVesselRemodeling.resampling_centerline(mergedVertex, mergedRadius, 1.0)
            # mergedVertex = CTreeVesselRemodeling.smooth_centerline(mergedVertex, 1.0)

            # resampling
            if mergedVertex.shape[0] >= 3 :
                resampledCL = CResampledFrameCL()
                resampledCL.process(mergedVertex, mergedRadius)

                node.ResampledVertex = resampledCL.ResampledVertex
                node.ResampledRadius = resampledCL.ResampledRadius
                node.PolyData = resampledCL.create_cylinder_polydata()

                if self.m_listResampleVertex is None :
                    self.m_listResampleVertex = node.ResampledVertex.copy()
                    self.m_listResampleRadius = node.ResampledRadius.copy()
                else :
                    self.m_listResampleVertex = np.concatenate(
                        (self.m_listResampleVertex, node.ResampledVertex), axis=0
                    )
                    self.m_listResampleRadius = np.concatenate(
                        (self.m_listResampleRadius, node.ResampledRadius), axis=0
                    )

                mesh = CTreeVesselRemodeling.get_meshlib(node.PolyData)
                mesh = algMeshLib.CMeshLib.meshlib_healing(mesh)
                node.PolyData = CTreeVesselRemodeling.get_vtkmesh(mesh)

                iCnt = node.child_node_count()
                for inx in range(0, iCnt) :
                    childNode = node.child_node(inx)
                    listNode.append(childNode)

    def _get_similar_direction_centerline(self, cl, childClList):
        """
        parent centerline 끝 방향과 가장 비슷한 방향을 갖는 child centerline을 반환.
        - cl.vertex: (N,3)
        - childClList[i].vertex: (Mi,3)
        """
        if cl is None or childClList is None or len(childClList) == 0:
            return None

        if len(getattr(cl, "Vertex", [])) < 2:
            return childClList[0]

        def _unit(v: np.ndarray):
            v = np.asarray(v, dtype=float).reshape(3,)
            n = np.linalg.norm(v)
            if n == 0 or not np.isfinite(n):
                return None
            return v / n

        def _direction(points: np.ndarray, idx0: int, idx1: int):
            # points[idx1] - points[idx0]
            if points is None or len(points) <= max(idx0, idx1):
                return None
            return _unit(points[idx1] - points[idx0])

        # ---- parent direction (끝쪽) ----
        parentVertex = np.asarray(cl.Vertex, dtype=float).reshape(-1, 3)
        # 끝 방향: [-1] - [-2]
        parentDir = _direction(parentVertex, -2, -1)
        if parentDir is None:
            # fallback: 첫 방향 [1]-[0]
            parentDir = _direction(parentVertex, 0, 1)
            if parentDir is None:
                return childClList[0]

        bestChild = None
        bestScore = -np.inf  # cos(theta) 최대가 가장 유사

        for child in childClList:
            childVertex = np.asarray(child.Vertex, dtype=float).reshape(-1, 3)
            if len(childVertex) < 2:
                continue

            # child 시작 방향: [1] - [0]
            childDir = _direction(childVertex, 0, 1)
            if childDir is None:
                continue

            # 방향 유사도: cos(theta) = dot(u, v)  (1에 가까울수록 유사)
            score = float(np.dot(parentDir, childDir))

            if score > bestScore:
                bestScore = score
                bestChild = child

        # 다 실패했으면 첫 child 반환
        return bestChild if bestChild is not None else childClList[0]

    def _merge_anchor_mesh(self) -> vtk.vtkPolyData :
        if self.m_rootAnchorNode is None :
            return None

        mergedMesh = None

        listNode = [self.m_rootAnchorNode]
        while listNode :
            node = listNode.pop(0)
            print(f"id : {node.m_listConnCLID}")

            if node.PolyData is not None :
                if mergedMesh is None :
                    mergedMesh = node.PolyData
                else :
                    retMesh = CTreeVesselRemodeling.bridge_mesh(mergedMesh, node.PolyData)
                    if retMesh is None :
                        print("passed remodeling ..")
                        # savePath = "/Users/hutom/Desktop/solution/project/anaconda/Solution/UnitTestPrev/CommonPipeline_20/Tool/dbg"
                        # algVTK.CVTK.save_poly_data_stl(os.path.join(savePath, "mergedMesh.stl"), mergedMesh)
                        # algVTK.CVTK.save_poly_data_stl(os.path.join(savePath, "nodePolyData.stl"), node.PolyData)
                    else :
                        mergedMesh = retMesh

            iCnt = node.child_node_count()
            for inx in range(0, iCnt) :
                childNode = node.child_node(inx)
                listNode.append(childNode)

        return mergedMesh


    # private
    def __refine_radius(self, parentRadius : float, radius : np.ndarray, outSideInx : int) -> np.ndarray :
        minRadius = np.min(radius[outSideInx : ])
        maxRadius = np.max(radius[outSideInx : ])
        if maxRadius > parentRadius :
            maxRadius = parentRadius
        if minRadius < CTreeVesselRemodeling.s_minRadius :
            minRadius = CTreeVesselRemodeling.s_minRadius
        if minRadius > maxRadius :
            minRadius = maxRadius

        N = radius.shape[0]
        startInx = outSideInx

        fixedPart = np.full(startInx, maxRadius)
        t = np.linspace(0, 1, N - startInx)
        interpPart = maxRadius + (minRadius - maxRadius) * t

        refinedRadius = np.concatenate([fixedPart, interpPart])
        return refinedRadius
    def __refine_leaf_radius(self, radius : np.ndarray, outSideInx : int)  -> np.ndarray :
        refindedRadius = np.sort(radius)[::-1]
        return refindedRadius
    def __refine_cl_radius(self, cl : algSkeletonGraph.CSkeletonCenterline, skeleton = None) -> np.ndarray :
        '''
        ret : refined radius (N,)
        '''
        if skeleton == None:
            skeleton = self.InputSkeleton

        clID = cl.ID
        connCLIDs = skeleton.get_conn_centerline_id(clID)
        parentCLID = connCLIDs[0]

        parentRadius = 0.0
        radius = 0.0
        spherePos = None
        # parent가 없으므로 자기 자신을 그대로 return 함
        if parentCLID == -1 :
            parentRadius = cl.Radius[0]
            spherePos = cl.Vertex[0]
            radius = cl.Radius[0]
        else :
            parentCL = skeleton.get_centerline(parentCLID)
            parentRadius = parentCL.Radius[-1]
            spherePos = parentCL.Vertex[-1]
            radius = parentCL.Radius[-1]

        outSideInx = CTreeVesselRemodeling.find_outside_inx(spherePos, radius, cl)
        if outSideInx == -1 :
            return cl.Radius.copy()

        refinedRadius = None
        if cl.is_leaf() == True :
            refinedRadius = self.__refine_leaf_radius(cl.Radius, outSideInx)
        else :
            refinedRadius = self.__refine_radius(parentRadius, cl.Radius, outSideInx)
        cl.Radius = refinedRadius.copy()
        return refinedRadius
    def __connection_cost(self, parentCLID : int, childCLID : int, angleWeight : float = 1.0, radiusWeight : float = 0.2) -> float :
        '''
        angleWeight : 두 곡선의 angle diff의 weight를 지정
        childRadius : 두 곡선의 radius diff의 weight를 지정
                      이 때, child radius는 곡선의 중간 지점의 radius를 취한다.
        '''
        parentCL = self.InputSkeleton.get_centerline(parentCLID)
        childCL = self.InputSkeleton.get_centerline(childCLID)

        parentVertex = parentCL.Vertex
        parentRadius = parentCL.Radius
        childVertex = None
        childRadius = None

        if childCL.Vertex.shape[0] > 2 :
            childVertex = childCL.Vertex[1 : ]
            childRadius = childCL.Radius[1 : ]
        else :
            childVertex = childCL.Vertex
            childRadius = childCL.Radius

        # 1. 각도의 차이
        tp = CTreeVesselRemodeling.parent_tangent(parentVertex)
        tc = CTreeVesselRemodeling.child_tangent(childVertex)
        tpLen = max(np.linalg.norm(tp), 0.0001)
        tcLen = max(np.linalg.norm(tc), 0.0001)
        cosAngle = max(np.dot(tp, tc) / (tpLen * tcLen), 0.0)
        angleCost = 1 - cosAngle

        # 2. 반지름 차이
        pr = max(parentRadius[-1], 1e-4)
        childRadiusIndex = len(childRadius) // 2
        radiusCost = abs(pr - childRadius[childRadiusIndex]) / pr
        radiusCost = np.clip(radiusCost, 0.0, 1.0)

        return angleWeight * angleCost + radiusWeight * radiusCost
    def __recur_make_anchor(self, node : CTreeVesselRemodelingAnchorNode) :
        clID = node.conn_clid(0)
        while clID != -1 :
            _, listChildCLID = self.InputSkeleton.get_conn_centerline_id(clID)

            if len(listChildCLID) == 0 :
                clID = -1
                continue

            listCost = []
            for inx in range(0, len(listChildCLID)) :
                childCLID = listChildCLID[inx]
                listCost.append(self.__connection_cost(clID, childCLID))
            bestInx = np.argmin(listCost)

            clID = -1
            for inx in range(0, len(listChildCLID)) :
                childCLID = listChildCLID[inx]
                if inx == bestInx :
                    node.add_conn_clid(childCLID)
                    clID = childCLID
                else :
                    node.add_child_clid(childCLID)

        iCnt = node.child_node_count()
        for inx in range(0, iCnt) :
            childNode = node.child_node(inx)
            self.__recur_make_anchor(childNode)


    @property
    def InputSkeleton(self) -> algSkeletonGraph.CSkeleton :
        return self.m_inputSkeleton
    @InputSkeleton.setter
    def InputSkeleton(self, inputSkeleton : algSkeletonGraph.CSkeleton) :
        self.m_inputSkeleton = inputSkeleton
    @property
    def InputRadiusMargin(self) -> float :
        return self.m_inputRadiusMargin
    @InputRadiusMargin.setter
    def InputRadiusMargin(self, inputRadiusMargin : float) :
        self.m_inputRadiusMargin = inputRadiusMargin
    @property
    def MergedMesh(self) -> vtk.vtkPolyData :
        return self.m_mergedMesh
    @MergedMesh.setter
    def MergedMesh(self, mergedMesh : vtk.vtkPolyData) :
        self.m_mergedMesh = mergedMesh


if __name__ == '__main__' :
    pass


# print ("ok ..")

