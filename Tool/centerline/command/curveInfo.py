import sys
import os
import numpy as np

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAppPath = os.path.dirname(fileAbsPath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algSkeletonGraph as algSkeletonGraph


import data as data
import geometry as geometry

# import commandInterface as commandInterface



# class CCLCurve : 
#     @staticmethod
#     def compute_curvature_3d(points : np.ndarray) :
#         """
#         3D 곡선에서 곡률을 계산하는 함수
#         :param points: N x 3 형태의 numpy 배열 (x, y, z 좌표)
#         :return: 곡률 값 배열
#         """
#         dr = np.gradient(points, axis=0)
#         d2r = np.gradient(dr, axis=0)

#         cross_product = np.cross(dr, d2r)
#         numerator = np.linalg.norm(cross_product, axis=1)
#         denominator = np.linalg.norm(dr, axis=1) ** 3

#         curvature = np.zeros(len(points))
#         mask = denominator > 1e-8
#         curvature[mask] = numerator[mask] / denominator[mask]

#         return curvature
#     @staticmethod
#     def calc_coord_by_tangent(tangent : np.ndarray, prevUp : np.ndarray) -> tuple :
#         '''
#         ret : (xCoord, yCoord, zCoord), type : np.ndarray
#         '''
#         tangent = tangent.reshape(-1)
#         prevUp = prevUp.reshape(-1)
#         if np.abs(np.dot(tangent, prevUp)) > 0.99 :
#             prevUp = np.array([0.0, 0.0, 1.0])
        
#         binormal = np.cross(prevUp, tangent)
#         binormal = binormal / np.linalg.norm(binormal)
#         up = np.cross(tangent, binormal)

#         return (binormal.reshape(-1, 3), up.reshape(-1, 3), tangent.reshape(-1, 3))
#     @staticmethod
#     def calc_mat(xCoord : np.ndarray, yCoord : np.ndarray, zCoord : np.ndarray, pos : np.ndarray) -> np.ndarray :
#         mat = algLinearMath.CScoMath.rot_mat3_from_axis(xCoord, yCoord, zCoord)
#         rotMat = algLinearMath.CScoMath.from_mat3_to_mat4(mat)
#         transMat = algLinearMath.CScoMath.translation_mat4(pos)
#         return algLinearMath.CScoMath.mul_mat4_mat4(transMat, rotMat)
#     @staticmethod
#     def calc_curve_coord(npVertexCurve : np.ndarray) -> tuple :
#         '''
#         ret : (xCoord, yCoord, zCoord)
#         '''

#         tangents = []
#         normals = []
#         binormals = []

#         prevUp = np.array([0.0, 1.0, 0.0])

#         for inx in range(0, len(npVertexCurve) - 1) :
#             if inx == 0 :
#                 tangentV = (npVertexCurve[inx + 1] - npVertexCurve[inx])
#                 tangentV = tangentV / np.linalg.norm(tangentV)
#                 if np.abs(np.dot(tangentV, prevUp)) > 0.99 :
#                     prevUp = np.array([0.0, 0.0, 1.0])
#             else :
#                 tangentV = (npVertexCurve[inx + 1] - npVertexCurve[inx - 1])
#                 tangentV = tangentV / np.linalg.norm(tangentV)

#             binormalV = np.cross(prevUp, tangentV)
#             binormalV = binormalV / np.linalg.norm(binormalV)
#             upV = np.cross(tangentV, binormalV)

#             tangents.append(tangentV)
#             binormals.append(binormalV)
#             normals.append(upV)

#             prevUp = upV.copy()
        
#         tangents.append(tangents[-1])
#         normals.append(normals[-1])
#         binormals.append(binormals[-1])
        
#         return (np.array(binormals), np.array(normals), np.array(tangents))
    

#     def __init__(self, cl : algSkeletonGraph.CSkeletonCenterline) :
#         self.m_cl = cl
#         # self.m_npCurvature = CCLCurve.compute_curvature_3d(self.m_npVertexCurve)
#         self.m_npXCoord, self.m_npYCoord, self.m_npZCoord = CCLCurve.calc_curve_coord(self.m_cl.Vertex)
#     def clear(self) :
#         self.m_cl = None
#         self.m_npXCoord = None
#         self.m_npYCoord = None
#         self.m_npZCoord = None

#     def get_transform(self, clPtInx : int) :
#         mat = algLinearMath.CScoMath.rot_mat3_from_axis(
#             self.m_npXCoord[clPtInx].reshape(-1, 3),
#             self.m_npYCoord[clPtInx].reshape(-1, 3),
#             self.m_npZCoord[clPtInx].reshape(-1, 3)
#             )
#         rotMat = algLinearMath.CScoMath.from_mat3_to_mat4(mat)
#         transMat = algLinearMath.CScoMath.translation_mat4(self.m_cl.get_vertex(clPtInx))
#         return algLinearMath.CScoMath.mul_mat4_mat4(transMat, rotMat)
    

#     @property
#     def CL(self) -> algSkeletonGraph.CSkeletonCenterline :
#         return self.m_cl


class CCLCurve :
    '''
    Parallel Transport Frames
    '''
    @staticmethod
    def normalize(v : np.ndarray) :
        return v / np.linalg.norm(v)
    @staticmethod
    def rotate_frame_to_tangent(tangent : np.ndarray, N0 : np.ndarray, B0 : np.ndarray, T0 : np.ndarray) -> tuple :
        '''
        input 
            - N0(y-axis) : normal, shape (3, ), default : (0, 1, 0)
            - B0(x-axis) : binormal, shape (3, ), default : (1, 0, 0)
            - T0(z-axis) : tangent, shape (3, ), default : (0, 0, 1)
        ret
            - N(y-axis) : normal, shape (3, )
            - B(x-axis) : binormal, shape (3, )
            - T(z-axis) : tangent, shape (3, )
        '''
        if N0 is None :
            N0 = np.array([0.0, 1.0, 0.0])
        if B0 is None :
            B0 = np.array([1.0, 0.0, 0.0])
        if T0 is None :
            T0 = np.array([0.0, 0.0, 1.0])

        tangent = tangent.reshape(-1)
        T = CCLCurve.normalize(tangent)

        axis = np.cross(T0, T)
        dot = np.dot(T0, T)

        if np.linalg.norm(axis) < 1e-8 :
            # 거의 평행
            if dot > 0 :
                # 같은 방향 → 그대로
                return N0, B0, T0
            else:
                # 정반대 방향 → Normal, Binormal 그대로 두고 Tangent만 뒤집기
                return N0, -B0, -T0   # or N0, B0, -T0 depending on what you want
        else:
            axis = CCLCurve.normalize(axis)
            angle = np.arccos(np.clip(dot, -1.0, 1.0))

            K = np.array([
                [0, -axis[2], axis[1]],
                [axis[2], 0, -axis[0]],
                [-axis[1], axis[0], 0]
            ])
            R = np.eye(3) + np.sin(angle) * K + (1 - np.cos(angle)) * (K @ K)

            N = R @ N0
            B = R @ B0
            T = R @ T0
            return N, B, T
    @staticmethod
    def compute_curvature_3d(points : np.ndarray) -> np.ndarray :
        """
        3D 곡선에서 곡률을 계산하는 함수
        :param points: N x 3 형태의 numpy 배열 (x, y, z 좌표)
        :return: 곡률 값 배열
        """
        dr = np.gradient(points, axis=0)
        d2r = np.gradient(dr, axis=0)

        cross_product = np.cross(dr, d2r)
        numerator = np.linalg.norm(cross_product, axis=1)
        denominator = np.linalg.norm(dr, axis=1) ** 3

        curvature = np.zeros(len(points))
        mask = denominator > 1e-8
        curvature[mask] = numerator[mask] / denominator[mask]

        return curvature
    @staticmethod
    def get_curve_len(npVertex : np.ndarray) -> np.ndarray :
        diffs = np.diff(npVertex, axis=0)
        segmentLen = np.linalg.norm(diffs, axis=1)

        # 시작점은 0, 이후 누적합
        accumulated = np.concatenate([[0], np.cumsum(segmentLen)])
        return accumulated
    @staticmethod
    def get_BNT(points : np.ndarray, N0 : np.ndarray, B0 : np.ndarray, T0 : np.ndarray) :
        '''
        ret : (Binormal, Normal, Tangent)
        '''
        tangents = np.zeros_like(points)
        tangents[1:-1] = points[2:] - points[:-2]
        tangents[0] = points[1] - points[0]
        tangents[-1] = points[-1] - points[-2]
        tangents = tangents / np.linalg.norm(tangents, axis=1)[:, None]

        ptCnt = len(points)
        N, B, T = CCLCurve.rotate_frame_to_tangent(tangents[0], N0, B0, T0)

        npTangent = [T]
        npNormal = [N]
        npBinormal = [B]

        # PTF 업데이트
        for i in range(1, ptCnt) :
            T_next = tangents[i]
            axis = np.cross(T, T_next)
            if np.linalg.norm(axis) < 1e-8 :
                # 평행 → 프레임 그대로 유지
                npTangent.append(T_next)
                npNormal.append(N)
                npBinormal.append(B)
            else:
                axis /= np.linalg.norm(axis)
                angle = np.arccos(np.clip(np.dot(T, T_next), -1, 1))

                # Rodrigues 회전
                K = np.array([
                    [0, -axis[2], axis[1]],
                    [axis[2], 0, -axis[0]],
                    [-axis[1], axis[0], 0]
                ])
                R = np.eye(3) + np.sin(angle) * K + (1 - np.cos(angle)) * (K @ K)

                N = R @ N
                B = R @ B
                T = T_next

                npTangent.append(T)
                npNormal.append(N)
                npBinormal.append(B)

        npTangent = np.array(npTangent)
        npNormal = np.array(npNormal)
        npBinormal = np.array(npBinormal)
        return (npBinormal, npNormal, npTangent)
        
    
    def __init__(self) :
        self.m_point = None
        self.m_tangent = None
        self.m_normal = None
        self.m_binormal = None
    def clear(self) :
        self.m_point = None
        self.m_tangent = None
        self.m_normal = None
        self.m_binormal = None
    def process(self, points: np.ndarray, N0 : np.ndarray, B0 : np.ndarray, T0 : np.ndarray) :
        '''
        points : must be curve point that aligned by order 
        N0 : shape (3, ), default : None
        B0 : shape (3, ), default : None
        T0 : shape (3, ), default : None
        '''
        self.m_point = points
        self.m_binormal, self.m_normal, self.m_tangent = CCLCurve.get_BNT(points, N0, B0, T0)
    def get_transform(self, clPtInx : int) -> np.ndarray :
        mat = algLinearMath.CScoMath.rot_mat3_from_axis(
            self.Binormal[clPtInx].reshape(-1, 3),
            self.Normal[clPtInx].reshape(-1, 3),
            self.Tangent[clPtInx].reshape(-1, 3)
            )
        rotMat = algLinearMath.CScoMath.from_mat3_to_mat4(mat)
        transMat = algLinearMath.CScoMath.translation_mat4(self.m_point[clPtInx].reshape(-1, 3))
        return algLinearMath.CScoMath.mul_mat4_mat4(transMat, rotMat)
    

    # property
    @property
    def Tangent(self) -> np.ndarray :
        return self.m_tangent
    @property
    def Binormal(self) -> np.ndarray :
        return self.m_binormal
    @property
    def Normal(self) -> np.ndarray :
        return self.m_normal



class CCLCircle :
    def __init__(self, cl : algSkeletonGraph.CSkeletonCenterline, clCurve : CCLCurve, circleVertexCnt : int) :
        self.m_cl = cl
        self.m_clCurve = clCurve
        self.m_listCircle = []

        for inx in range(0, cl.get_vertex_count()) :
            circle = geometry.CCircle(cl.get_radius(inx), circleVertexCnt)
            mat = clCurve.get_transform(inx)
            circle.transform(mat)
            self.m_listCircle.append(circle)
    def clear(self) :
        for circle in self.m_listCircle :
            circle.clear()
        self.m_listCircle.clear()
        self.m_clCurve = None
        self.m_cl = None

    def get_circle_count(self) -> int :
        return len(self.m_listCircle)
    def get_circle(self, inx : int) -> geometry.CCircle :
        return self.m_listCircle[inx]
    def get_range_circle_vertex(self, startInx : int, endInx : int) :
        retVertex = None 

        for inx in range(startInx, endInx + 1) :
            circle = self.get_circle(inx)
            if retVertex is None :
                retVertex = circle.m_vertex.copy()
            else :
                retVertex = np.concatenate((retVertex, circle.m_vertex), axis=0)
        return retVertex


    @property
    def Vertex(self) -> np.ndarray :
        retVertex = None 

        iCnt = self.get_circle_count()
        for inx in range(0, iCnt) :
            circle = self.get_circle(inx)
            if retVertex is None :
                retVertex = circle.m_vertex.copy()
            else :
                retVertex = np.concatenate((retVertex, circle.m_vertex), axis=0)
        return retVertex

    

class CSkelCircle :
    def __init__(self, skeleton : algSkeletonGraph.CSkeleton, circleVertexCnt : int) :
        self.m_listCurve = []
        self.m_listCircle = []

        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            clCurve = CCLCurve()
            clCurve.process(cl.Vertex, None, None, None)
            clCircle = CCLCircle(cl, clCurve, circleVertexCnt)
            self.m_listCurve.append(clCurve)
            self.m_listCircle.append(clCircle)
    def clear(self) :
        self.m_listCurve.clear()
        self.m_listCircle.clear()

    
    def get_clinfo_count(self) -> int :
        return len(self.m_listCurve)
    def get_cl_curve(self, clID : int) -> CCLCurve :
        return self.m_listCurve[clID]
    def get_cl_circle(self, clID : int) -> CCLCircle :
        return self.m_listCircle[clID]





if __name__ == '__main__' :
    pass


# print ("ok ..")

