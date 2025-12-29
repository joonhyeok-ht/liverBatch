import sys
import os
import numpy as np
import math

# from sklearn.neighbors import KDTree
# from scipy.spatial import KDTree

from scipy.interpolate import make_interp_spline
# from scipy.integrate import cumtrapz

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
sys.path.append(fileAbsPath)
import algLinearMath as algLinearMath


class CCurveInfo :
    @staticmethod
    def get_curve_len(vertex : np.ndarray) -> float :
        curveLen = np.sum(np.linalg.norm(np.diff(vertex, axis=0), axis=1))
        return curveLen
    @staticmethod
    def get_vertex_by_curve_len(vertex : np.ndarray, targetCurveLen : float) :
        dist = np.linalg.norm(vertex[1:] - vertex[:-1], axis=1)
        cumulLen = np.hstack(([0], np.cumsum(dist)))
        validInx = np.where(cumulLen <= targetCurveLen)[0]
        return vertex[validInx]
    @staticmethod
    def cumtrapz(y, x=None, initial=0):
        if x is None:
            x = np.arange(len(y))
        dx = np.diff(x)
        integral = np.cumsum((y[1:] + y[:-1]) * dx / 2)
        return np.concatenate([[initial], integral])
    
    
    def __init__(self) :
        self.m_npVertex = None
        self.m_npTangent = None
        self.m_npF1 = None
        self.m_npF2 = None
        self.m_npRadius = None
    def clear(self) :
        self.m_npVertex = None
        self.m_npTangent = None
        self.m_npF1 = None
        self.m_npF2 = None
        self.m_npRadius = None


    def get_cnt(self) -> int :
        return self.m_npVertex.shape[0]
    def get_vertex(self, inx : int) -> np.ndarray :
        return self.m_npVertex[inx].reshape(-1, 3)
    def get_tangent(self, inx : int) -> np.ndarray : 
        return self.m_npTangent[inx].reshape(-1, 3)
    def get_f1(self, inx : int) -> np.ndarray :
        return self.m_npF1[inx].reshape(-1, 3)
    def get_f2(self, inx : int) -> np.ndarray :
        return self.m_npF2[inx].reshape(-1, 3)
    def get_radius(self, inx : int) -> float :
        if self.m_npRadius is None :
            return 0.0
        return self.m_npRadius[inx]
    def get_mat3(self, inx : int) -> np.ndarray :
        return algLinearMath.CScoMath.rot_mat3_from_axis(self.m_npF1[inx].reshape(-1, 3), self.m_npF2[inx].reshape(-1, 3), self.m_npTangent[inx].reshape(-1, 3))


    @property
    def Vertex(self) :
        return self.m_npVertex
    @Vertex.setter
    def Vertex(self, vertex : np.ndarray) :
        self.m_npVertex = vertex.copy()
    @property
    def Tangent(self) :
        return self.m_npTangent
    @Tangent.setter
    def Tangent(self, tangent : np.ndarray) :
        self.m_npTangent = tangent.copy()
    @property
    def F1(self) :
        return self.m_npF1
    @F1.setter
    def F1(self, f1 : np.ndarray) :
        self.m_npF1 = f1.copy()
    @property
    def F2(self) :
        return self.m_npF2
    @F2.setter
    def F2(self, f2 : np.ndarray) :
        self.m_npF2 = f2.copy()
    @property
    def Radius(self) :
        return self.m_npRadius
    @Radius.setter
    def Radius(self, radius : np.ndarray) :
        self.m_npRadius = radius.copy()


class CBSplineCurve :
    # @staticmethod
    # def adaptive_sampling_cnt(controlPoints : np.ndarray, min_density=5, max_density=20):
    #     """
    #     곡률에 따라 샘플링 밀도를 조정

    #     Args:
    #         min_density (int): 곡률이 작은 구간의 최소 밀도.
    #         max_density (int): 곡률이 큰 구간의 최대 밀도.

    #     Returns:
    #         int: 적절한 샘플링 점의 개수.
    #     """
    #     # 곡선 길이 계산
    #     curveLen = np.sum(np.linalg.norm(np.diff(controlPoints, axis=0), axis=1))

    #     # 곡률 계산 (1차 미분과 2차 미분을 사용)
    #     diff1 = np.diff(controlPoints, axis=0)
    #     diff2 = np.diff(diff1, axis=0)
    #     curvature = np.linalg.norm(np.cross(diff1[:-1], diff2), axis=1) / (np.linalg.norm(diff1[:-1], axis=1) ** 3)

    #     # 곡률 기반 샘플링 밀도
    #     avgCurvature = np.mean(curvature)
    #     density = min_density + (max_density - min_density) * (avgCurvature / np.max(curvature))

    #     # 샘플링 개수 계산
    #     samplingPointCnt = int(curveLen * density)
    #     return max(samplingPointCnt, 100)
    @staticmethod
    def adaptive_sampling_cnt(controlPoints: np.ndarray, min_density=5, max_density=20):
        """
        곡률에 따라 샘플링 밀도를 조정

        Args:
            controlPoints (np.ndarray): 곡선을 정의하는 제어점 (N x 3 형태의 배열)
            min_density (int): 곡률이 작은 구간의 최소 밀도.
            max_density (int): 곡률이 큰 구간의 최대 밀도.

        Returns:
            int: 적절한 샘플링 점의 개수.
        """
        # 곡선 길이 계산
        curveLen = np.sum(np.linalg.norm(np.diff(controlPoints, axis=0), axis=1))

        # 곡률 계산 (1차 미분과 2차 미분을 사용)
        diff1 = np.diff(controlPoints, axis=0)  # 1차 미분 (변화량)
        diff2 = np.diff(diff1, axis=0)          # 2차 미분 (변화율)

        # 곡률 계산식 (직선일 경우 곡률이 0)
        with np.errstate(divide='ignore', invalid='ignore'):  # 0 나누기 오류 방지
            curvature = np.linalg.norm(np.cross(diff1[:-1], diff2), axis=1) / (
                np.linalg.norm(diff1[:-1], axis=1) ** 3
            )
            curvature = np.nan_to_num(curvature)  # NaN 또는 Inf 값을 0으로 처리

        # 직선 예외처리: 곡률이 모두 0인 경우
        if np.all(curvature == 0) or np.max(curvature) == 0:
            # 직선이므로 최소 밀도로 샘플링
            samplingPointCnt = int(curveLen * min_density)
            return max(samplingPointCnt, 100)

        # 곡률 기반 샘플링 밀도
        avgCurvature = np.mean(curvature)
        density = min_density + (max_density - min_density) * (avgCurvature / np.max(curvature))

        # 샘플링 개수 계산
        samplingPointCnt = int(curveLen * density)
        return max(samplingPointCnt, 100)
    

    def __init__(self):
        self.m_controlPt = None
        self.m_controlPtRadius = None
        self.m_sampledPoint = None
        self.m_sampledPointRadius = None
        self.m_t = None
        self.m_tNew = None
        self.m_dx = None
        self.m_ddx = None
        self.m_d3x = None
        self.m_torsion = None
        self.m_listMat = []
    def clear(self) :
        self.m_controlPt = None
        self.m_controlPtRadius = None
        self.m_sampledPoint = None
        self.m_sampledPointRadius = None
        self.m_t = None
        self.m_tNew = None
        self.m_dx = None
        self.m_ddx = None
        self.m_d3x = None
        self.m_torsion = None
        self.m_listMat.clear()
    
    def make_spline(self, controlPt : np.ndarray, controlPtRadius : np.ndarray, k : int, samplingCnt : int) :
        self.clear()

        self.m_controlPt = controlPt
        self.m_controlPtRadius = controlPtRadius

        x = controlPt[ : , 0]
        y = controlPt[ : , 1]
        z = controlPt[ : , 2]

        self.m_t = np.linspace(0, 1, len(controlPt))
        splX = make_interp_spline(self.m_t, x, k=k)
        splY = make_interp_spline(self.m_t, y, k=k)
        splZ = make_interp_spline(self.m_t, z, k=k)
        if controlPtRadius is not None :
            splRadius = make_interp_spline(self.m_t, controlPtRadius, k=k)

        self.m_tNew = np.linspace(0, 1, samplingCnt)
        xNew = splX(self.m_tNew)
        yNew = splY(self.m_tNew)
        zNew = splZ(self.m_tNew)
        self.m_sampledPoint = np.array([xNew, yNew, zNew]).T
        if controlPtRadius is not None :
            self.m_sampledPointRadius = splRadius(self.m_tNew)

        # 1차, 2차, 3차 도함수 계산
        dx = splX.derivative(1)(self.m_tNew)
        dy = splY.derivative(1)(self.m_tNew)
        dz = splZ.derivative(1)(self.m_tNew)

        ddx = splX.derivative(2)(self.m_tNew)
        ddy = splY.derivative(2)(self.m_tNew)
        ddz = splZ.derivative(2)(self.m_tNew)

        d3x = splX.derivative(3)(self.m_tNew)
        d3y = splY.derivative(3)(self.m_tNew)
        d3z = splZ.derivative(3)(self.m_tNew)

        self.m_dx = np.array([dx, dy, dz]).T
        self.m_ddx = np.array([ddx, ddy, ddz]).T
        self.m_d3x = np.array([d3x, d3y, d3z]).T

        # torsion
        crossV = np.cross(self.m_dx, self.m_ddx)
        torsionNumerator = np.einsum('ij,ij->i', crossV, self.m_d3x)
        torsionDenominator = np.linalg.norm(crossV, axis=1) ** 2
        # self.m_torsion = torsionNumerator / torsionDenominator
        epsilon = 1e-8  # 작은 값 (0으로 나누는 것을 방지하기 위한 임계값)
        torsionDenominator_safe = np.where(torsionDenominator < epsilon, epsilon, torsionDenominator)
        self.m_torsion = torsionNumerator / torsionDenominator_safe
        self.m_torsion = np.nan_to_num(self.m_torsion)

        # 곡선의 1차 도함수 크기
        dxNorm = np.linalg.norm(self.m_dx, axis=1)

        # Omega(u) 계산: -적분(τ * ||c'(u)||)
        # omega = -cumtrapz(self.m_torsion * dxNorm, self.m_tNew, initial=0)
        omega = CCurveInfo.cumtrapz(self.m_torsion * dxNorm, self.m_tNew, initial=0)

        # Tangent, Normal, Binormal 계산
        self.m_tangents = self.m_dx / dxNorm[:, None]

        # self.m_normals = self.m_ddx - np.sum(self.m_ddx * self.m_tangents, axis=1)[:, None] * self.m_tangents
        # self.m_normals = self.m_normals / np.linalg.norm(self.m_normals, axis=1)[:, None]
        self.m_normals = np.zeros_like(self.m_tangents)
        for i in range(len(self.m_tangents)):
            if np.linalg.norm(self.m_ddx[i]) < 1e-8:  # 직선(2차 도함수가 0)인 경우
                # 직선일 때 임의의 수직 벡터를 설정
                ref_vector = np.array([1, 0, 0]) if not np.allclose(self.m_tangents[i], [1, 0, 0]) else np.array([0, 1, 0])
                self.m_normals[i] = np.cross(self.m_tangents[i], ref_vector)
                self.m_normals[i] /= np.linalg.norm(self.m_normals[i])
            else:
                # 일반 곡선의 경우 Normal 벡터 계산
                self.m_normals[i] = self.m_ddx[i] - np.sum(self.m_ddx[i] * self.m_tangents[i]) * self.m_tangents[i]
                self.m_normals[i] /= np.linalg.norm(self.m_normals[i])
        


        self.m_binormals = np.cross(self.m_tangents, self.m_normals)

        # f1(u)와 f2(u) 계산
        sinOmega = np.sin(omega)
        cosOmega = np.cos(omega)
        self.m_f1 = sinOmega[:, None] * self.m_binormals + cosOmega[:, None] * self.m_normals
        self.m_f2 = cosOmega[:, None] * self.m_binormals - sinOmega[:, None] * self.m_normals

        for inx in range(0, samplingCnt) :
            # mat = algLinearMath.CScoMath.rot_mat3_from_axis(self.m_tangents[inx].reshape(-1, 3), self.m_f1[inx].reshape(-1, 3), self.m_f2[inx].reshape(-1, 3))
            mat = algLinearMath.CScoMath.rot_mat3_from_axis(self.m_f1[inx].reshape(-1, 3), self.m_f2[inx].reshape(-1, 3), self.m_tangents[inx].reshape(-1, 3))
            self.m_listMat.append(mat)
    def get_sample_point_cnt(self) -> int :
        return self.m_sampledPoint.shape[0]
    def get_sample_point(self, inx : int) -> np.ndarray :
        return self.m_sampledPoint[inx].reshape(-1, 3)
    def get_sample_point_radius_cnt(self) -> int :
        if self.m_sampledPointRadius is None :
            return 0
        return self.m_sampledPointRadius.shape[0]
    def get_sample_point_radius(self, inx : int) -> float :
        if self.m_sampledPointRadius is None :
            return 0.0
        return self.m_sampledPointRadius[inx]
    def get_tangent_f1_f2(self, inx : int) -> tuple : 
        """
        ret : (tangent, f1, f2)
        """
        return (self.m_tangents[inx].reshape(-1, 3), self.m_f1[inx].reshape(-1, 3), self.m_f2[inx].reshape(-1, 3))
    def get_control_point_tangent_f1_f2(self) -> list :
        """
        ret : [(tangent, f1, f2), ..]
        """ 
        retList = []
        for t in self.m_t:
            index = np.argmin(np.abs(self.m_tNew - t))
            # retList.append((self.m_tangents[index].reshape(-1, 3), self.m_f1[index].reshape(-1, 3), self.m_f2[index].reshape(-1, 3)))
            retList.append((self.m_tangents[index].reshape(-1, 3), self.m_f1[index].reshape(-1, 3), self.m_f2[index].reshape(-1, 3)))
        return retList
    def get_rot_mat(self, inx : int) -> np.ndarray :
        return self.m_listMat[inx]
    def get_curve_len(self) -> float :
        curveLen = np.sum(np.linalg.norm(np.diff(self.m_sampledPoint, axis=0), axis=1))
        return curveLen
    def get_curveinfo_by_count(self, cnt : int) -> CCurveInfo :
        interval = (self.get_sample_point_cnt() - 2) // (cnt - 2)

        retList = [self.m_sampledPoint[0]]
        retList.extend(self.m_sampledPoint[1:-1:interval])
        retList.append(self.m_sampledPoint[-1])
        sampledPoint = np.array(retList)

        retList = [self.m_tangents[0]]
        retList.extend(self.m_tangents[1:-1:interval])
        retList.append(self.m_tangents[-1])
        tangent = np.array(retList)

        retList = [self.m_f1[0]]
        retList.extend(self.m_f1[1:-1:interval])
        retList.append(self.m_f1[-1])
        f1 = np.array(retList)

        retList = [self.m_f2[0]]
        retList.extend(self.m_f2[1:-1:interval])
        retList.append(self.m_f2[-1])
        f2 = np.array(retList)

        if self.m_sampledPointRadius is not None :
            retList = [self.m_sampledPointRadius[0]]
            retList.extend(self.m_sampledPointRadius[1:-1:interval])
            retList.append(self.m_sampledPointRadius[-1])
            radius = np.array(retList)

        curveInfo = CCurveInfo()
        curveInfo.Vertex = sampledPoint
        curveInfo.Tangent = tangent
        curveInfo.F1 = f1
        curveInfo.F2 = f2
        if self.m_sampledPointRadius is not None :
            curveInfo.Radius = radius
        return curveInfo
    def get_curveinfo_cp(self) :
        sampledPoint = None
        tangent = None
        f1 = None
        f2 = None
        radius = []
        for t in self.m_t:
            index = np.argmin(np.abs(self.m_tNew - t))
            if index == 0 :
                sampledPoint = self.m_sampledPoint[index].reshape(-1, 3)
                tangent = self.m_tangents[index].reshape(-1, 3)
                f1 = self.m_f1[index].reshape(-1, 3)
                f2 = self.m_f2[index].reshape(-1, 3)
            else :
                sampledPoint = np.concatenate((sampledPoint, self.m_sampledPoint[index].reshape(-1, 3)), axis=0)
                tangent = np.concatenate((tangent, self.m_tangents[index].reshape(-1, 3)), axis=0)
                f1 = np.concatenate((f1, self.m_f1[index].reshape(-1, 3)), axis=0)
                f2 = np.concatenate((f2, self.m_f2[index].reshape(-1, 3)), axis=0)
            if self.m_sampledPointRadius is not None :
                radius.append(self.m_sampledPointRadius[index])
            
        curveInfo = CCurveInfo()
        curveInfo.Vertex = sampledPoint
        curveInfo.Tangent = tangent
        curveInfo.F1 = f1
        curveInfo.F2 = f2
        if self.m_sampledPointRadius is not None :
            curveInfo.Radius = np.array(radius)
        return curveInfo


    @property
    def SamplePoint(self) -> np.ndarray :
        return self.m_sampledPoint
    @property
    def SamplePointRadius(self) -> np.ndarray :
        return self.m_sampledPointRadius



