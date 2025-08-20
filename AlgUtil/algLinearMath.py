import sys
import os
# import torch
# from torch.autograd import Variable
import numpy as np
import math
from sklearn.decomposition import PCA

# import gen_utils as gu
# from sklearn.neighbors import KDTree
# from scipy.spatial import KDTree
# import open3d as o3d

# from torch.utils.tensorboard import SummaryWriter


'''
type numpy shape
    - vec3 : (1, 3)
    - mat3 : (3, 3)
    - color : (1, 3)
    - plane : (4) : [a, b, c, d]
    - ray : list : [rayOri : vec3, rayDir : vec3]
'''

class CScoMath :
    s_epsilon = 0.001

    def __init__(self) -> None:
        pass

    
    def deg_to_rad(degree : np.ndarray) -> np.ndarray :
        return np.radians(degree)
    def rad_to_deg(radian : np.ndarray) -> np.ndarray :
        return np.degrees(radian)


    @staticmethod
    def vec3_len(v : np.ndarray) -> np.ndarray :
        return np.linalg.norm(v, axis=1)
    @staticmethod
    def vec3_normalize(v : np.ndarray) -> np.ndarray :
        n = CScoMath.vec3_len(v)
        n = n.reshape(-1, 1)
        v = v / n
        return v
    @staticmethod
    def add_vec3_scalar(v : np.ndarray, scalar : float) -> np.ndarray :
        return v + scalar
    @staticmethod
    def add_vec3_vec3(v0 : np.ndarray, v1 : np.ndarray) -> np.ndarray :
        '''
        element-wise multiply
        '''
        return v0 + v1
    @staticmethod
    def sub_vec3_scalar(v : np.ndarray, scalar : float) -> np.ndarray :
        return v - scalar
    @staticmethod
    def sub_vec3_vec3(v0 : np.ndarray, v1 : np.ndarray) -> np.ndarray :
        '''
        element-wise multiply
        '''
        return v0 - v1
    @staticmethod
    def mul_vec3_scalar(v : np.ndarray, scalar : float) -> np.ndarray :
        return v * scalar
    @staticmethod
    def mul_vec3_vec3(v0 : np.ndarray, v1 : np.ndarray) -> np.ndarray :
        '''
        element-wise multiply
        '''
        return v0 * v1
    @staticmethod
    def mul_mat3_vec3(mat : np.ndarray, v : np.ndarray) -> np.ndarray :
        return v.dot(mat.T)
    @staticmethod
    def mul_mat3_mat3(m0 : np.ndarray, m1 : np.ndarray) -> np.ndarray :
        return m0.dot(m1)
    @staticmethod
    def mul_mat4_vec3(mat : np.ndarray, v : np.ndarray) -> np.ndarray :
        v4 = CScoMath.from_vec3_to_vec4(v)
        v4[:, 3] = 1.0
        v4 = v4.dot(mat.T)
        return CScoMath.from_vec4_to_vec3(v4)
    @staticmethod
    def mul_mat4_vec4(mat : np.ndarray, v : np.ndarray) -> np.ndarray :
        return v.dot(mat.T)
    @staticmethod
    def mul_mat4_mat4(m0 : np.ndarray, m1 : np.ndarray) -> np.ndarray :
        return m0.dot(m1)
    @staticmethod
    def dot_vec3(v0 : np.ndarray, v1 : np.ndarray) -> np.ndarray :
        return np.einsum('ij,ij->i', v0, v1)
    @staticmethod
    def cross_vec3(v0 : np.ndarray, v1 : np.ndarray) -> np.ndarray :
        return np.cross(v0, v1)
    @staticmethod
    def dot_vec4(v0 : np.ndarray, v1 : np.ndarray) -> np.ndarray :
        return np.einsum('ij,ij->i', v0, v1)
    
    

    @staticmethod
    def identity_mat3() -> np.ndarray :
        return np.eye(3)
    @staticmethod
    def inv_mat3(m : np.ndarray) -> np.ndarray :
        return np.linalg.inv(m)
    @staticmethod
    def rot_mat3_from_axis(xAxis : np.ndarray, yAxis : np.ndarray, zAxis : np.ndarray) -> np.ndarray :
        xTmp = xAxis.copy()
        yTmp = yAxis.copy()
        zTmp = zAxis.copy()
        mat = np.concatenate((xTmp, yTmp, zTmp), axis=0)
        return mat.T
    @staticmethod
    def rot_mat3_from_axis_angle(axis : np.ndarray, radian : float) -> np.ndarray :
        """
        Return the rotation matrix associated with counterclockwise rotation about
        the given axis by theta radians.
        """
        axis = CScoMath.vec3_normalize(axis)
        a = np.cos(radian / 2.0)
        bcd = -axis * np.sin(radian / 2.0)
        b, c, d = bcd[0, 0], bcd[0, 1], bcd[0, 2]
        aa, bb, cc, dd = a * a, b * b, c * c, d * d
        bc, ad, ac, ab, bd, cd = b * c, a * d, a * c, a * b, b * d, c * d
        return np.array([[aa + bb - cc - dd, 2 * (bc + ad), 2 * (bd - ac)],
                            [2 * (bc - ad), aa + cc - bb - dd, 2 * (cd + ab)],
                            [2 * (bd + ac), 2 * (cd - ab), aa + dd - bb - cc]])
    

    @staticmethod
    def identity_mat4() -> np.ndarray :
        return np.eye(4, dtype=np.float32)
    @staticmethod
    def inv_mat4(m : np.ndarray) -> np.ndarray :
        retM = np.linalg.inv(m)
        return retM
    @staticmethod
    def scale_mat4(scale : np.ndarray) -> np.ndarray :
        retM = np.eye(4, dtype=np.float32)
        retM[0, 0] = scale[0, 0]
        retM[1, 1] = scale[0, 1]
        retM[2, 2] = scale[0, 2]
        return retM
    @staticmethod
    def translation_mat4(trans : np.ndarray) -> np.ndarray :
        retM = np.eye(4, dtype=np.float32)
        retM[0 : 3, 3] = trans
        return retM
    @staticmethod
    def object_view_mat4(pos : np.ndarray, view : np.ndarray, up : np.ndarray) -> np.ndarray:
        z = view - pos
        z = CScoMath.vec3_normalize(z)
        x = CScoMath.cross_vec3(up, z)
        y = CScoMath.cross_vec3(z, x)

        # 4x4 변환 행렬을 만듭니다.
        m = np.eye(4, dtype=np.float32)
        m[0 : 3, 0] = x
        m[0 : 3, 1] = y
        m[0 : 3, 2] = z
        m[0 : 3, 3] = pos
        return m
    def look_at_mat4(pos : np.ndarray, view : np.ndarray, up : np.ndarray) -> np.ndarray :
        z = view - pos
        z = CScoMath.vec3_normalize(z)
        x = CScoMath.cross_vec3(z, up)
        y = CScoMath.cross_vec3(x, z)

        m = np.eye(4, dtype=np.float32)
        m[0, 0:3] = x
        m[1, 0:3] = y
        m[2, 0:3] = -z
        m[0, 3] = -CScoMath.dot_vec3(x, pos)
        m[1, 3] = -CScoMath.dot_vec3(y, pos)
        m[2, 3] = CScoMath.dot_vec3(z, pos)
        return m
    @staticmethod
    def perspective_projection_mat4(fovDeg : float, aspect : float, near : float, far : float) -> np.ndarray :
        fov_rad = CScoMath.deg_to_rad(fovDeg)

        t = np.tan(fov_rad / 2) * near
        r = t * aspect
        l = -r
        b = -t

        P = np.zeros((4, 4), dtype=np.float32)
        P[0, 0] = 2 * near / (r - l)
        P[1, 1] = 2 * near / (t - b)
        P[0, 2] = (r + l) / (r - l)
        P[1, 2] = (t + b) / (t - b)
        P[2, 2] = -(far + near) / (far - near)
        P[2, 3] = -2 * far * near / (far - near)
        P[3, 2] = -1
        return P
    

    @staticmethod
    def create_plane(v0 : np.ndarray, v1 : np.ndarray, v2 : np.ndarray) :
        e0 = v1 - v0
        e1 = v2 - v0
        normal = CScoMath.cross_vec3(e0, e1)
        normal = CScoMath.vec3_normalize(normal)
        d = -CScoMath.dot_vec3(normal, v0)

        retPlane = np.zeros(4)
        retPlane[ : 3] = normal[0, : 3]
        retPlane[3] = d
        return retPlane
    @staticmethod
    def dot_plane_vec3(plane : np.ndarray, v : np.ndarray) :
        v0 = plane.reshape(-1, 4)
        v1 = CScoMath.from_vec3_to_vec4(v)
        return CScoMath.dot_vec4(v0, v1)
    
    
    @staticmethod
    def to_vec3(v : list) :
        return np.array(v, dtype=np.float32).reshape(-1, 3)
    @staticmethod
    def to_vec4(v : list) :
        return np.array(v, dtype=np.float32).reshape(-1, 4)
    @staticmethod
    def is_equal_vec(point1 : np.ndarray, point2 : np.ndarray, epsilon=0.0001) :
        return np.allclose(point1, point2, atol=epsilon)
    @staticmethod
    def from_vec3_to_vec4(v : np.ndarray) :
        h = np.ones(v.shape[0], dtype=np.float32).reshape(-1, 1)
        retV = np.concatenate((v, h), axis=1)
        return retV
    @staticmethod
    def from_vec4_to_vec3(v : np.ndarray) :
        retV = np.zeros((v.shape[0], 3), dtype=np.float32)
        retV[ : , : 3] = v[ : , : 3]
        return retV
    @staticmethod
    def from_mat3_to_mat4(m : np.ndarray) -> np.ndarray :
        retM = np.eye(4, dtype=np.float32)
        retM[:3, :3] = m
        return retM
    

    @staticmethod
    def get_radian_vec3_vec3(v0 : np.ndarray, v1 : np.ndarray) -> np.ndarray :
        d = CScoMath.dot_vec3(v0, v1)
        return np.arccos(d)
    @staticmethod
    def get_degree_vec3_vec3(v0 : np.ndarray, v1 : np.ndarray) -> np.ndarray :
        return CScoMath.rad_to_deg(CScoMath.get_radian_vec3_vec3(v0, v1))
    @staticmethod
    def get_min_vec3(v : np.ndarray) :
        return np.min(v, axis=0).reshape(-1, 3).astype(np.float32)
    @staticmethod
    def get_max_vec3(v : np.ndarray) :
        return np.max(v, axis=0).reshape(-1, 3).astype(np.float32)
    @staticmethod
    def get_mean_vec3(v : np.ndarray) :
        return np.mean(v, axis=0).reshape(-1, 3).astype(np.float32)
    @staticmethod
    def get_axis_mat3(m : np.ndarray) :
        xAxis = m[ : , 0].reshape(-1, 3).astype(np.float32)
        yAxis = m[ : , 1].reshape(-1, 3).astype(np.float32)
        zAxis = m[ : , 2].reshape(-1, 3).astype(np.float32)
        return [xAxis, yAxis, zAxis]
    @staticmethod
    def get_axis_mat4(m : np.ndarray) :
        xAxis = m[ : 3, 0].reshape(-1, 3).astype(np.float32)
        yAxis = m[ : 3, 1].reshape(-1, 3).astype(np.float32)
        zAxis = m[ : 3, 2].reshape(-1, 3).astype(np.float32)
        return [xAxis, yAxis, zAxis]
    

    @staticmethod
    def transform_vec3(rotMat : np.ndarray, trans : np.ndarray, v : np.ndarray) :
        vRot = CScoMath.mul_mat3_vec3(rotMat, v)
        return vRot + trans
    @staticmethod
    def transform_vec3_with_axis(axis : np.ndarray, radian : float, trans : np.ndarray, v : np.ndarray) :
        rotMat = CScoMath.rot_mat3_from_axis_angle(axis, radian)
        return CScoMath.transform_vec3(rotMat, trans, v)
    
    
    @staticmethod
    def intersection_obb_sphere(
        obbCenter : np.ndarray, obbAxis : np.ndarray, obbSize : np.ndarray,
        sphereCenter : np.ndarray, radius : float
        ) -> bool :
        v = sphereCenter - obbCenter
        obbHalfSize = obbSize
        vRot = CScoMath.mul_mat3_vec3(obbAxis.T, v)

        npTmp = np.abs(vRot) - radius
        npRet = npTmp < obbHalfSize
        count = np.count_nonzero(npRet == False)

        if count > 0 :
            return False
        else :
            return True





