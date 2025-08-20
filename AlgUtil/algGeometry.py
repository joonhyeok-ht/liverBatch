import sys
import os
# import torch
# from torch.autograd import Variable
import numpy as np
import math
from sklearn.decomposition import PCA

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
sys.path.append(fileAbsPath)
import algLinearMath




class CScoAABB :
    s_index = np.array(
        [
            [0, 1],
            [1, 2],
            [2, 3],
            [3, 0],

            [4, 5],
            [5, 6],
            [6, 7],
            [7, 4],

            [0, 4],
            [1, 5],
            [2, 6],
            [3, 7]
        ],
        dtype=np.uint32
    ).reshape(-1)
    def make_vertex_s(minV : np.ndarray, maxV : np.ndarray) -> np.ndarray : 
        vertex = np.concatenate(
            (
                algLinearMath.CScoMath.to_vec3([minV[0, 0], minV[0, 1], minV[0, 2]]), # 0
                algLinearMath.CScoMath.to_vec3([maxV[0, 0], minV[0, 1], minV[0, 2]]), # 1
                algLinearMath.CScoMath.to_vec3([maxV[0, 0], maxV[0, 1], minV[0, 2]]), # 2
                algLinearMath.CScoMath.to_vec3([minV[0, 0], maxV[0, 1], minV[0, 2]]), # 3

                algLinearMath.CScoMath.to_vec3([minV[0, 0], minV[0, 1], maxV[0, 2]]), # 4
                algLinearMath.CScoMath.to_vec3([maxV[0, 0], minV[0, 1], maxV[0, 2]]), # 5
                algLinearMath.CScoMath.to_vec3([maxV[0, 0], maxV[0, 1], maxV[0, 2]]), # 6
                algLinearMath.CScoMath.to_vec3([minV[0, 0], maxV[0, 1], maxV[0, 2]])  # 7
                ),
            axis=0,
            dtype=np.float32
        )
        return vertex
    

    def __init__(self) -> None:
        self.m_min = algLinearMath.CScoMath.to_vec3([10000, 10000, 10000])
        self.m_max = algLinearMath.CScoMath.to_vec3([-10000, -10000, -10000])
        self.m_center = algLinearMath.CScoMath.to_vec3([0, 0, 0])
        self.m_halfSize = algLinearMath.CScoMath.to_vec3([0, 0, 0])
        self.m_vertex = None

    def init_with_vertex(self, v : np.ndarray) :
        self.m_min = algLinearMath.CScoMath.get_min_vec3(v)
        self.m_max = algLinearMath.CScoMath.get_max_vec3(v)
        self.m_center = (self.m_min + self.m_max) / 2.0
        self.m_halfSize = self.m_max - self.m_center
        self.m_vertex = CScoAABB.make_vertex_s(self.m_min, self.m_max)
    def init_with_min_max(self, min : np.ndarray, max : np.ndarray) :
        self.m_min = min.copy()
        self.m_max = max.copy()
        self.m_center = (self.m_min + self.m_max) / 2.0
        self.m_halfSize = self.m_max - self.m_center
        self.m_vertex = CScoAABB.make_vertex_s(self.m_min, self.m_max)
    def init_with_vec3_mat4(self, v : np.ndarray, mat : np.ndarray) :
        retV = algLinearMath.CScoMath.mul_mat4_vec3(mat, v)
        self.init_with_vertex(retV)

    
    def transform(self, m : np.ndarray) -> np.ndarray :
        v = algLinearMath.CScoMath.from_vec3_to_vec4(self.m_vertex)
        v = algLinearMath.CScoMath.mul_mat4_vec4(m, v)
        v = algLinearMath.CScoMath.from_vec4_to_vec3(v)
        min = algLinearMath.CScoMath.get_min_vec3(v)
        max = algLinearMath.CScoMath.get_max_vec3(v)
        return CScoAABB.make_vertex_s(min, max)


    @property
    def Min(self) -> np.ndarray :
        return self.m_min
    @property
    def Max(self) -> np.ndarray :
        return self.m_max
    @property
    def Center(self) -> np.ndarray :
        return self.m_center
    @property
    def HalfSize(self) -> np.ndarray :
        return self.m_halfSize
    @property
    def Vertex(self) -> np.ndarray :
        return self.m_vertex
    

    # private


class CScoRay :
    def __init__(self) -> None:
        self.m_ori = algLinearMath.CScoMath.to_vec3([0, 0, 0])
        self.m_dir = algLinearMath.CScoMath.to_vec3([0, 0, 0])
    
    def init_with_vertex(self, v0 : np.ndarray, v1 : np.ndarray) :
        self.m_ori = v0.copy()
        self.m_dir = algLinearMath.CScoMath.vec3_normalize(v1 - v0)
    def init_with_ray(self, rayOri : np.ndarray, rayDir : np.ndarray) :
        self.m_ori = rayOri.copy()
        self.m_dir = rayDir.copy()

    def get_point(self, t : float) :
        return self.m_ori + self.m_dir * t


    @property
    def Ori(self) -> np.ndarray :
        return self.m_ori
    @property
    def Dir(self) -> np.ndarray :
        return self.m_dir




class CScoIntersection :
    @staticmethod
    def ray_plane(ray : CScoRay, plane : np.ndarray, v : np.ndarray) :
        '''
        v : plane point
        ret : (bIntersect, t, intersected point : vec3)
        '''
        rayOri = ray.Ori
        rayDir = ray.Dir
        planeNor = np.zeros((1, 3))
        planeNor[0, : 3] = plane[ : 3]
        dot = algLinearMath.CScoMath.dot_vec3(rayDir, planeNor)
        if dot == 0 :
            return (False, 0.0, None)
        
        t = algLinearMath.CScoMath.dot_vec3(v - rayOri, planeNor) / dot
        pt = ray.get_point(t)

        return (True, t, pt)
    @staticmethod
    def ray_aabb(ray : CScoRay, aabb : CScoAABB) :
        '''
        v : plane point
        ret : (bIntersect, t, intersected point : vec3)
        '''
        epsilon = 1e-6

        rayOri = ray.Ori
        rayDir = np.where(ray.Dir == 0, ray.Dir + epsilon, ray.Dir)
        aabbMin = aabb.Min
        aabbMax = aabb.Max

        t1 = (aabbMin - rayOri) / rayDir
        t2 = (aabbMax - rayOri) / rayDir

        tMin = np.max(np.minimum(t1, t2))
        tMax = np.min(np.maximum(t1, t2))

        if tMax < 0 or tMin > tMax :
            return (False, 0, None)
        t = tMin if tMin >= 0 else tMax
        pt = ray.get_point(t)

        return (True, t, pt)



    def __init__(self) -> None:
        pass