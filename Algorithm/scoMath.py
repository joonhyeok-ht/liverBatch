import matplotlib.pyplot as plt
import numpy as np
import cv2
from scipy.spatial.transform import Rotation as R
from scipy import optimize
from scipy.optimize import least_squares
import math
import SimpleITK as sitk

from pyquaternion import Quaternion



class CScoVec3 :
    def __init__(self, x = 0.0, y = 0.0, z = 0.0) :
        npVec = np.array([x, y, z])
        self.m_npVec = npVec.reshape(1, 3)

    def clone(self) : 
        vecClone = CScoVec3()
        vecClone.m_npVec = np.array(self.m_npVec)
        return vecClone
    def clone_from(self, vec3) :
        self.m_npVec = np.array(vec3.m_npVec)
    def length(self) :
        return np.linalg.norm(self.m_npVec)
    def length_square(self) :
        return self.X * self.X + self.Y * self.Y + self.Z * self.Z
    def dot(self, v) :
        return np.dot(self.m_npVec[0], v.m_npVec[0])
    def cross(self, v) :
        npCross = np.cross(self.m_npVec[0], v.m_npVec[0])
        return CScoVec3(npCross[0], npCross[1], npCross[2])
    def normalize(self) :
        fLen = self.length()
        fFactor = 1.0 / fLen
        
        fX = self.X * fFactor
        fY = self.Y * fFactor
        fZ = self.Z * fFactor

        return CScoVec3(fX, fY, fZ)
    def add(self, v) :
        npAdd = np.add(self.m_npVec, v.m_npVec)
        return CScoVec3(npAdd[0, 0], npAdd[0, 1], npAdd[0, 2])
    def subtract(self, v) :
        npSub = np.subtract(self.m_npVec, v.m_npVec)
        return CScoVec3(npSub[0, 0], npSub[0, 1], npSub[0, 2])
    
    def print(self) :
        print(f"X:{self.X}, Y:{self.Y}, Z:{self.Z}")
    

    @property
    def X(self) :
        return self.m_npVec[0, 0]
    @X.setter
    def X(self, x : float) :
        self.m_npVec[0, 0] = x
    @property
    def Y(self) :
        return self.m_npVec[0, 1]
    @Y.setter
    def Y(self, y : float) :
        self.m_npVec[0, 1] = y
    @property
    def Z(self) :
        return self.m_npVec[0, 2]
    @Z.setter
    def Z(self, z : float) :
        self.m_npVec[0, 2] = z


class CScoVec4 :
    def __init__(self, x = 0.0, y = 0.0, z = 0.0, w = 0.0) :
        npVec = np.array([x, y, z, w])
        self.m_npVec = npVec.reshape(1, 4)
    
    def clone(self) : 
        vecClone = CScoVec4()
        vecClone.m_npVec = np.array(self.m_npVec)
        return vecClone
    def clone_from(self, vec4) :
        self.m_npVec = np.array(vec4.m_npVec)
    def length(self) : 
        return np.linalg.norm(self.m_npVec)
    def length_square(self) :
        return self.X * self.X + self.Y * self.Y + self.Z * self.Z + self.W * self.W
    def dot(self, v) : 
        return np.dot(self.m_npVec[0], v.m_npVec[0])
    def normalize(self) : 
        fLen = self.length()
        fFactor = 1.0 / fLen
        
        fX = self.X * fFactor
        fY = self.Y * fFactor
        fZ = self.Z * fFactor
        fW = self.W * fFactor

        return CScoVec4(fX, fY, fZ, fW)
    def add(self, v) :
        npAdd = np.add(self.m_npVec, v.m_npVec)
        return CScoVec4(npAdd[0, 0], npAdd[0, 1], npAdd[0, 2], npAdd[0, 3])
    def subtract(self, v) :
        npSub = np.subtract(self.m_npVec, v.m_npVec)
        return CScoVec4(npSub[0, 0], npSub[0, 1], npSub[0, 2], npSub[0, 3])
    
    def print(self) :
        print(f"X:{self.X}, Y:{self.Y}, Z:{self.Z}, W:{self.W}")
    

    @property
    def X(self) :
        return self.m_npVec[0, 0]
    @X.setter
    def X(self, x : float) :
        self.m_npVec[0, 0] = x
    @property
    def Y(self) :
        return self.m_npVec[0, 1]
    @Y.setter
    def Y(self, y : float) :
        self.m_npVec[0, 1] = y
    @property
    def Z(self) :
        return self.m_npVec[0, 2]
    @Z.setter
    def Z(self, z : float) :
        self.m_npVec[0, 2] = z
    @property
    def W(self) :
        return self.m_npVec[0, 3]
    @W.setter
    def W(self, w : float) :
        self.m_npVec[0, 3] = w


class CScoMat4 :
    '''
    4x4 열우선 행렬을 정의한다. 
    '''

    def __init__(self) :
        self.identity()


    def clone(self) :
        matClone = CScoMat4()
        matClone.m_npMat = np.array(self.m_npMat)
        return matClone
    def clone_from(self, mat4) :
        self.m_npMat = np.array(mat4.m_npMat)
    def identity(self) :
        self.m_npMat = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ])
    def inverse(self) :
        npMat = self.m_npMat
        matInv = CScoMat4()
        matInv.m_npMat = np.linalg.inv(npMat)
        return matInv
    def translate_3d(self, x, y, z) :
        self.m_npMat = np.array([
            [1.0, 0.0, 0.0, x],
            [0.0, 1.0, 0.0, y],
            [0.0, 0.0, 1.0, z],
            [0.0, 0.0, 0.0, 1.0],
        ])
    def scale(self, x, y, z) :
        self.m_npMat = np.array([
            [x, 0.0, 0.0, 0.0],
            [0.0, y, 0.0, 0.0],
            [0.0, 0.0, z, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ])
    def rot_from_row(self, listRot : tuple) :
        self.m_npMat = np.array([
            [listRot[0], listRot[1], listRot[2], 0.0],
            [listRot[3], listRot[4], listRot[5], 0.0],
            [listRot[6], listRot[7], listRot[8], 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ])
    def rot_from_column(self, listRot : tuple) :
        self.m_npMat = np.array([
            [listRot[0], listRot[3], listRot[6], 0.0],
            [listRot[1], listRot[4], listRot[7], 0.0],
            [listRot[2], listRot[5], listRot[8], 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ])
    def rot_from_axis(self, xAxis : CScoVec3, yAxis : CScoVec3, zAxis : CScoVec3) :
        self.m_npMat = np.array([
            [xAxis.X, yAxis.X, zAxis.X, 0.0],
            [xAxis.Y, yAxis.Y, zAxis.Y, 0.0],
            [xAxis.Z, yAxis.Z, zAxis.Z, 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ])
    def rot_from_axis_radian(self, axis : CScoVec3, radian : float) :
        theta = radian / 2.0
        qAxis = axis.m_npVec * np.sin(theta)
        r = R.from_quat([qAxis[0][0], qAxis[0][1], qAxis[0][2], np.cos(theta)])
        self.m_npMat = r.as_matrix()
        self.m_npMat = np.hstack([self.m_npMat, np.array([0.0, 0.0, 0.0]).reshape(3, 1)])
        self.m_npMat = np.vstack([self.m_npMat, np.array([0.0, 0.0, 0.0, 1.0])])
    def set_translate(self, x : float, y : float, z : float) :
        self.m_npMat[0][3] = x
        self.m_npMat[1][3] = y
        self.m_npMat[2][3] = z
    def get_translate(self) :
        return CScoVec3(self.m_npMat[0][3], self.m_npMat[1][3], self.m_npMat[2][3])
    def set_scale(self, x : float, y : float, z : float) :
        self.m_npMat[0][0] = x
        self.m_npMat[1][1] = y
        self.m_npMat[2][2] = z
    def get_scale(self) :
        return CScoVec3(self.m_npMat[0][0], self.m_npMat[1][1], self.m_npMat[2][2])
    def get_x_axis(self) :
        return CScoVec3(self.m_npMat[0][0], self.m_npMat[1][0], self.m_npMat[2][0])
    def get_y_axis(self) :
        return CScoVec3(self.m_npMat[0][1], self.m_npMat[1][1], self.m_npMat[2][1])
    def get_z_axis(self) :
        return CScoVec3(self.m_npMat[0][2], self.m_npMat[1][2], self.m_npMat[2][2])
    def get_axis_radian(self) :
        """
        desc : 행렬의 회전 속성에 대한 회전축과 radian을 리턴한다. 
        return : (axis : CScoVec3, radian : float)
        """
        q = CScoMath.mat4_to_quat(self)
        axis = CScoVec3(q.axis[0], q.axis[1], q.axis[2])
        radian = q.radians
        return (axis, radian)
    def make_from_3_point(self, p0 : CScoVec3, p1 : CScoVec3, p2 : CScoVec3) :
        pos = p1
        dir0 = p1.subtract(p0)
        dir1 = p2.subtract(p1)
        view = pos.add(dir0.add(dir1))
        up = CScoVec3(0, 1, 0)

        viewDir = view.subtract(pos)
        # note
        # tangent를 계산할 경우 viewDir과 up이 거의 유사할 경우 무한대에 빠질 가능성이 있다.
	    # 따라서 추후에 viewDir을 up과 일치하지 않도록 약간 조정할 필요가 있다. 
        tangent = up.cross(viewDir).normalize()
        view = viewDir.normalize()
        up = view.cross(tangent).normalize()

        self.rot_from_axis(tangent, up, view)
        self.set_translate(pos.X, pos.Y, pos.Z)

    def print(self) :
        print(self.m_npMat)


class CScoPlane :
    def __init__(self) :
        self.m_normal = CScoVec3(0, 0, 1)
        self.m_d = 0
        self.m_point = CScoVec3(0, 0, 0)


    def make_with_point(self, v0 : CScoVec3, v1 : CScoVec3, v2 : CScoVec3) :
        u = v1.subtract(v0)
        v = v2.subtract(v0)
        self.m_normal = (u.cross(v)).normalize()
        self.m_d = -v0.dot(self.m_normal)
        self.m_point = v0.clone()
    def dot(self, v : CScoVec3) :
        ret = self.Normal.dot(v) + self.D
        return ret
    # infinity error 조심 
    def get_x(self, y : float, z : float) :
        x = (-self.Normal.Y * y - self.Normal.Z * z - self.D) * 1. / self.Normal.X
        return x
    def get_y(self, x : float, z : float) :
        y = (-self.Normal.X * x - self.Normal.Z * z - self.D) * 1. / self.Normal.Y
        return y
    def get_z(self, x : float, y : float) :
        z = (-self.Normal.X * x - self.Normal.Y * y - self.D) * 1. / self.Normal.Z
        return z
    def get_dist(self, v : CScoVec3) :
        dist = self.m_normal.dot(v.subtract(self.m_point))
        return math.fabs(dist)

    def print(self) :
        print(f"NX:{self.Normal.X}, NY:{self.Normal.Y}, NZ:{self.Normal.Z}, D:{self.D}")


    @property
    def Normal(self) :
        return self.m_normal
    @Normal.setter
    def Normal(self, normal : CScoVec3) :
        self.m_normal = normal.clone()
    @property
    def D(self) :
        return self.m_d
    @D.setter
    def D(self, d : float) :
        self.m_d = d
    @property
    def Point(self) :
        return self.m_point
    @Point.setter
    def Point(self, pt : CScoVec3) :
        self.m_point = pt.clone()


class CScoRay : 
    def __init__(self) :
        self.m_origin = CScoVec3()
        self.m_dir = CScoVec3()


    def make_with_point(self, startPt : CScoVec3, endPt : CScoVec3, bNormalized = False) :
        self.m_origin = startPt.clone()
        self.m_dir = endPt.subtract(startPt)

        if bNormalized == True :
            self.m_dir = self.m_dir.normalize()
    def get_pos(self, ratio : float) :
        pos = self.m_origin.add(CScoMath.mul_vec3_scalar(self.m_dir, ratio))
        return pos
    
    def print(self) :
        self.m_origin.print()
        self.m_dir.print()

    
    @property
    def Origin(self) :
        return self.m_origin
    @Origin.setter
    def Origin(self, origin : CScoVec3) :
        self.m_origin = origin
    @property
    def Dir(self) :
        return self.m_dir
    @Dir.setter
    def Dir(self, dir : CScoVec3) :
        self.m_dir = dir


class CScoAABB :
    def __init__(self) -> None:
        self.m_min = CScoVec3(0, 0, 0)
        self.m_max = CScoVec3(1, 1, 1)


    def make_min_max(self, minV : CScoVec3, maxV : CScoVec3) :
        self.m_min = minV.clone()
        self.m_max = maxV.clone()
    """
    note
        pos.xy - halfSize.xy ~  pos.xy - halfSize.xy
        pos.z ~ pos.z + halfSize.z
    """
    def make_pos_half_size(self, pos : CScoVec3, halfSize : CScoVec3) :
        self.m_min = CScoVec3(pos.X - halfSize.X, pos.Y - halfSize.Y , pos.Z)
        self.m_max = CScoVec3(pos.X + halfSize.X, pos.Y + halfSize.Y , pos.Z)
    
    def get_min_max_with_world_matrix(self, worldMat : CScoMat4) :
        retP0 = CScoVec3(self.Min.X, self.Max.Y, self.Min.Z)
        retP1 = CScoVec3(self.Min.X, self.Min.Y, self.Min.Z)
        retP2 = CScoVec3(self.Max.X, self.Min.Y, self.Min.Z)
        retP3 = CScoVec3(self.Max.X, self.Max.Y, self.Min.Z)
        retP4 = CScoVec3(self.Min.X, self.Max.Y, self.Max.Z)
        retP5 = CScoVec3(self.Min.X, self.Min.Y, self.Max.Z)
        retP6 = CScoVec3(self.Max.X, self.Min.Y, self.Max.Z)
        retP7 = CScoVec3(self.Max.X, self.Max.Y, self.Max.Z)

        retP0 = CScoMath.mul_mat4_vec3(worldMat, retP0)
        retP1 = CScoMath.mul_mat4_vec3(worldMat, retP1)
        retP2 = CScoMath.mul_mat4_vec3(worldMat, retP2)
        retP3 = CScoMath.mul_mat4_vec3(worldMat, retP3)
        retP4 = CScoMath.mul_mat4_vec3(worldMat, retP4)
        retP5 = CScoMath.mul_mat4_vec3(worldMat, retP5)
        retP6 = CScoMath.mul_mat4_vec3(worldMat, retP6)
        retP7 = CScoMath.mul_mat4_vec3(worldMat, retP7)

        listTmp = [
            [retP0.X, retP0.Y, retP0.Z],
            [retP1.X, retP1.Y, retP1.Z],
            [retP2.X, retP2.Y, retP2.Z],
            [retP3.X, retP3.Y, retP3.Z],

            [retP4.X, retP4.Y, retP4.Z],
            [retP5.X, retP5.Y, retP5.Z],
            [retP6.X, retP6.Y, retP6.Z],
            [retP7.X, retP7.Y, retP7.Z]
        ]

        retMin = np.min(listTmp, axis=0)
        retMax = np.max(listTmp, axis=0)

        return (CScoVec3(retMin[0], retMin[1], retMin[2]), CScoVec3(retMax[0], retMax[1], retMax[2]))


    @property
    def Min(self) :
        return self.m_min
    @Min.setter
    def Min(self, min : CScoVec3) :
        self.m_min = min.clone()
    @property
    def Max(self) :
        return self.m_max
    @Max.setter
    def Max(self, max : CScoVec3) :
        self.m_max = max.clone()


class CScoOBB :
    """
    note
        여기에서 정의된 OBB는 z축을 기준으로 원점이 center가 아닌 bottom이다. 
        x,y는 기존처럼 원점이 center이다. 
    """
    def __init__(self) :
        self.m_pos = CScoVec3(0, 0, 0)
        self.m_halfSize = CScoVec3(1, 1, 1)
        self.m_view = CScoVec3(0, 0, 1)
        self.m_up = CScoVec3(0, 1, 0)
        self.m_tangent = CScoVec3(1, 0, 0)
        self.m_worldMatrix = CScoMat4()
        self.m_bUpdate = True


    def make_with_pos_view_up(self, pos : CScoVec3, view : CScoVec3, up : CScoVec3, halfSize : CScoVec3) :
        viewDir = view.subtract(pos)
        self.m_tangent = up.cross(viewDir).normalize()
        self.m_view = viewDir.normalize()
        self.m_up = self.m_view.cross(self.m_tangent).normalize()
        self.m_pos = pos.clone()
        self.m_halfSize = halfSize.clone()
        self.m_bUpdate = True
    def make_with_2_point(self, p0 : CScoVec3, p1 : CScoVec3, halfSize : CScoVec3) :
        pos = p1
        dir = p1.subtract(p0)
        view = p1.add(dir)
        up = CScoVec3(0, 1, 0)
        self.make_with_pos_view_up(pos, view, up, halfSize)
    def make_with_3_point(self, p0 : CScoVec3, p1 : CScoVec3, p2 : CScoVec3, halfSize : CScoVec3) :
        self.m_worldMatrix.make_from_3_point(p0, p1, p2)
        self.Pos = self.m_worldMatrix.get_translate()
        self.HalfSize = halfSize
        self.Tangent = self.m_worldMatrix.get_x_axis()
        self.Up = self.m_worldMatrix.get_y_axis()
        self.View = self.m_worldMatrix.get_z_axis()

    def print(self) :
        print("-"*30)
        self.m_pos.print()
        self.m_halfSize.print()
        self.m_view.print()
        self.m_tangent.print()
        self.m_up.print()
        print("-"*30)

    
    @property
    def Pos(self) :
        return self.m_pos
    @Pos.setter
    def Pos(self, pos : CScoVec3) :
        self.m_pos = pos.clone()
        self.m_bUpdate = True
    @property
    def HalfSize(self) :
        return self.m_halfSize
    @HalfSize.setter
    def HalfSize(self, halfSize : CScoVec3) :
        self.m_halfSize = halfSize.clone()
        self.m_bUpdate = True
    @property
    def View(self) :
        return self.m_view
    @View.setter
    def View(self, view : CScoVec3) :
        self.m_view = view.clone()
        self.m_bUpdate = True
    @property
    def Tangent(self) :
        return self.m_tangent
    @Tangent.setter
    def Tangent(self, tangent : CScoVec3) :
        self.m_tangent = tangent.clone()
        self.m_bUpdate = True
    @property
    def Up(self) :
        return self.m_up
    @Up.setter
    def Up(self, up : CScoVec3) :
        self.m_up = up.clone()
        self.m_bUpdate = True
    @property
    def WorldMatrix(self) :
        if self.m_bUpdate == True :
            self.m_worldMatrix.rot_from_axis(self.Tangent, self.Up, self.View)
            self.m_worldMatrix.set_translate(self.Pos.X, self.Pos.Y, self.Pos.Z)
            self.m_bUpdate = False
        return self.m_worldMatrix


class CScoCylinder :
    """
    note
        여기에서 정의된 Cylinder는 z축을 기준으로 원점이 center가 아닌 bottom이다. 
        x,y는 기존처럼 원점이 center이다. 
    """
    def __init__(self) -> None:
        self.m_pos = CScoVec3(0, 0, 0)
        self.m_halfSize = CScoVec3(1, 1, 1)
        self.m_view = CScoVec3(0, 0, 1)
        self.m_up = CScoVec3(0, 1, 0)
        self.m_tangent = CScoVec3(1, 0, 0)
        self.m_radius = self.m_halfSize.X
        self.m_worldMatrix = CScoMat4()
        self.m_bUpdate = True


    def make_with_pos_view_up(self, pos : CScoVec3, view : CScoVec3, up : CScoVec3, halfSize : CScoVec3) :
        viewDir = view.subtract(pos)
        self.m_tangent = up.cross(viewDir).normalize()
        self.m_view = viewDir.normalize()
        self.m_up = self.m_view.cross(self.m_tangent).normalize()
        self.m_pos = pos.clone()
        self.m_halfSize = halfSize.clone()
        self.m_radius = self.m_halfSize.X
        self.m_bUpdate = True
    def make_with_2_point(self, p0 : CScoVec3, p1 : CScoVec3, halfSize : CScoVec3) :
        pos = p1
        dir = p1.subtract(p0)
        view = p1.add(dir)
        up = CScoVec3(0, 1, 0)
        self.make_with_pos_view_up(pos, view, up, halfSize)
    def make_with_3_point(self, p0 : CScoVec3, p1 : CScoVec3, p2 : CScoVec3, halfSize : CScoVec3) :
        self.m_worldMatrix.make_from_3_point(p0, p1, p2)
        self.Pos = self.m_worldMatrix.get_translate()
        self.HalfSize = halfSize
        self.Tangent = self.m_worldMatrix.get_x_axis()
        self.Up = self.m_worldMatrix.get_y_axis()
        self.View = self.m_worldMatrix.get_z_axis()


    @property
    def Pos(self) :
        return self.m_pos
    @Pos.setter
    def Pos(self, pos : CScoVec3) :
        self.m_pos = pos.clone()
        self.m_bUpdate = True
    @property
    def HalfSize(self) :
        return self.m_halfSize
    @HalfSize.setter
    def HalfSize(self, halfSize : CScoVec3) :
        self.m_halfSize = halfSize.clone()
        self.m_radius = self.m_halfSize.X
        self.m_bUpdate = True
    @property
    def View(self) :
        return self.m_view
    @View.setter
    def View(self, view : CScoVec3) :
        self.m_view = view.clone()
        self.m_bUpdate = True
    @property
    def Tangent(self) :
        return self.m_tangent
    @Tangent.setter
    def Tangent(self, tangent : CScoVec3) :
        self.m_tangent = tangent.clone()
        self.m_bUpdate = True
    @property
    def Up(self) :
        return self.m_up
    @Up.setter
    def Up(self, up : CScoVec3) :
        self.m_up = up.clone()
        self.m_bUpdate = True
    @property
    def WorldMatrix(self) :
        if self.m_bUpdate == True :
            self.m_worldMatrix.rot_from_axis(self.Tangent, self.Up, self.View)
            self.m_worldMatrix.set_translate(self.Pos.X, self.Pos.Y, self.Pos.Z)
            self.m_bUpdate = False
        return self.m_worldMatrix
    @WorldMatrix.setter
    def WorldMatrix(self, worldMat : CScoMat4) :
        self.m_worldMatrix = worldMat.clone()
        self.m_tangent = self.m_worldMatrix.get_x_axis()
        self.m_up = self.m_worldMatrix.get_y_axis()
        self.m_view = self.m_worldMatrix.get_z_axis()
        self.m_pos = self.m_worldMatrix.get_translate()
        self.m_bUpdate = False
    @property
    def Radius(self) :
        return self.m_radius
    

class CScoSpline :
    """
    desc
        Hermite 기반 Spline Curve를 정의
    """
    def __init__(self) -> None:
        # CScoVec3
        self.m_listCP = []
        self.m_listU = []
        self.m_deltaRatio = 0.1

    def process_U(self, firstU : CScoVec3, endU : CScoVec3) :
        if self.CPCnt < 3 :
            return
        
        self.m_listU.clear()
        self.m_listU.append(firstU)

        for inx in range(1, len(self.m_listCP) - 1) :
            preV = self.m_listCP[inx - 1]
            nextV = self.m_listCP[inx + 1]
            nowV = self.m_listCP[inx]
            p0 = nowV.subtract(preV)
            p1 = nextV.subtract(nowV)
            scale = p1.length() * 0.5
            ret = p0.add(p1)
            ret = ret.normalize()
            ret = CScoMath.mul_vec3_scalar(ret, scale)
            self.m_listU.append(ret)

        self.m_listU.append(endU)

    def clear_cp(self) :
        self.m_listCP.clear()
        self.m_listU.clear()
    def add_cp(self, cp : CScoVec3) :
        self.m_listCP.append(cp)
    def get_cp(self, inx : int) :
        return self.m_listCP[inx]
    def get_u(self, inx : int) :
        return self.m_listU[inx]
    def get_point(self, ratio : float) -> CScoVec3 :
        if self.CPCnt < 3 :
            return CScoVec3(0, 0, 0)
        if ratio > self.MaxRatio or ratio < 0.0 :
            return CScoVec3(0, 0, 0)
        
        preInx = int(math.floor(ratio) + 0.5)
        nextInx = preInx + 1
        if nextInx >= self.CPCnt :
            nextInx = preInx
        
        if nextInx == preInx :
            return CScoVec3(0, 0, 0)
        
        ratio = ratio - math.floor(ratio)
        
        A = self.get_cp(preInx)
        D = self.get_cp(nextInx)
        U = self.get_u(preInx)
        V = self.get_u(nextInx)

        return self._get_point(A, D, U, V, ratio)
    def get_points_start_to_ratio_in_knot(self, ratio) -> list :
        if self.CPCnt < 3 :
            return []
        if ratio > self.MaxRatio or ratio < 0.0 :
            return []
        
        preInx = int(math.floor(ratio) + 0.5)
        nextInx = preInx + 1
        if nextInx >= self.CPCnt :
            nextInx = preInx
        
        if nextInx == preInx :
            return []
        
        maxRatio = ratio - math.floor(ratio)

        A = self.get_cp(preInx)
        D = self.get_cp(nextInx)
        U = self.get_u(preInx)
        V = self.get_u(nextInx)

        listVertex = []
        nowRatio = 0.0
        while nowRatio <= maxRatio :
            retVec = self._get_point(A, D, U, V, nowRatio)
            listVertex.append(retVec)
            nowRatio += self.DeltaRatio

        return listVertex
    def get_points_ratio_to_end_in_knot(self, ratio) -> list :
        if self.CPCnt < 3 :
            return []
        if ratio > self.MaxRatio or ratio < 0.0 :
            return []
        
        preInx = int(math.floor(ratio) + 0.5)
        nextInx = preInx + 1
        if nextInx >= self.CPCnt :
            nextInx = preInx
        
        if nextInx == preInx :
            return []
        
        nowRatio = ratio - math.floor(ratio)

        A = self.get_cp(preInx)
        D = self.get_cp(nextInx)
        U = self.get_u(preInx)
        V = self.get_u(nextInx)

        listVertex = []
        while nowRatio <= 1.0 :
            retVec = self._get_point(A, D, U, V, nowRatio)
            listVertex.append(retVec)
            nowRatio += self.DeltaRatio
        
        return listVertex
    def get_points_within_ratio_range_in_knot(self, startRatio : float, endRatio : float) -> list :
        if self.CPCnt < 3 :
            return []
        
        preInx = int(math.floor(startRatio) + 0.5)
        nextInx = preInx + 1
        if nextInx >= self.CPCnt :
            nextInx = preInx

        if nextInx == preInx :
            return []
        
        nowRatio = startRatio - math.floor(startRatio)
        maxRatio = endRatio = math.floor(endRatio)

        if maxRatio > 1.0 :
            maxRatio = 1.0

        A = self.get_cp(preInx)
        D = self.get_cp(nextInx)
        U = self.get_u(preInx)
        V = self.get_u(nextInx)

        listVertex = []
        while nowRatio <= maxRatio :
            retVec = self._get_point(A, D, U, V, nowRatio)
            listVertex.append(retVec)
            nowRatio += self.DeltaRatio
        
        return listVertex
    def get_points_within_ratio_range(self, startRatio : float, endRatio : float) -> list:
        if self.CPCnt < 3 :
            return []
        
        iCeilRatio = int(math.ceil(startRatio) + 0.5)
        iFloorRatio = int(math.floor(endRatio) + 0.5)
        iRet = iFloorRatio - iCeilRatio

        listVertex = []
        if iRet < 0 :
            return self.get_points_within_ratio_range_in_knot(startRatio, endRatio)
        elif iRet == 0 :
            listVertex += self.get_points_ratio_to_end_in_knot(startRatio)
            listVertex += self.get_points_start_to_ratio_in_knot(endRatio)
        else :
            listVertex += self.get_points_ratio_to_end_in_knot(startRatio)

            nowRatio = iCeilRatio
            maxRatio = iFloorRatio
            while nowRatio < maxRatio :
                listVertex += self.get_points_ratio_to_end_in_knot(nowRatio)
                nowRatio += 1
                
            listVertex += self.get_points_start_to_ratio_in_knot(endRatio)

        return listVertex

    def get_all_points(self) -> list :
        if self.CPCnt < 3 :
            return []
        
        maxRatio = self.MaxRatio
        ratio = 0.0

        listVertex = []
        while ratio <= maxRatio :
            listVertex += self.get_points_ratio_to_end_in_knot(ratio)
            ratio += 1.0

        return listVertex
    def get_world_matrix(self, ratio : float, delta = 0.1) -> CScoMat4 :
        p0 = self.get_point(ratio - delta)
        p1 = self.get_point(ratio)
        p2 = self.get_point(ratio + delta)

        dir0 = p1.subtract(p0)
        dir1 = p2.subtract(p1)
        view = p1.add(dir0.add(dir1))
        normal = view.subtract(p1).normalize()

        axis, radian = CScoMath.get_axis_radian(CScoVec3(0, 0, 1), normal)
        if axis.length() < CScoMath.s_epsilon :
            axis = CScoVec3(0, 1, 0)

        worldMat = CScoMat4()
        worldMat.rot_from_axis_radian(axis, radian)
        worldMat.set_translate(p1.X, p1.Y, p1.Z)
        return worldMat


    # protected 
    def _get_point(self, A, D, U, V, ratio) -> CScoVec3:
        ratio3 = math.pow(ratio, 3)
        ratio2 = math.pow(ratio, 2)
        aFactor = 2 * ratio3 - 3 * ratio2 + 1
        dFactor = -2 * ratio3 + 3 * ratio2
        uFactor = ratio3 - 2 * ratio2 + ratio
        vFactor = ratio3 - ratio2

        adVec = CScoMath.mul_vec3_scalar(A, aFactor).add(CScoMath.mul_vec3_scalar(D, dFactor))
        uvVec = CScoMath.mul_vec3_scalar(U, uFactor).add(CScoMath.mul_vec3_scalar(V, vFactor))
        retVec = adVec.add(uvVec)

        return retVec

    
    @property
    def FirstU(self) :
        return self.m_listU[0]
    @property
    def EndU(self) :
        return self.m_listU[-1]
    @property
    def DeltaRatio(self) :
        return self.m_deltaRatio
    @DeltaRatio.setter
    def DeltaRatio(self, deltaRatio : float) :
        self.m_deltaRatio = deltaRatio
    @property
    def CPCnt(self) :
        return len(self.m_listCP)
    @property
    def MaxRatio(self) :
        return float(self.CPCnt - 1)
    @property
    def ListCP(self) :
        return self.m_listCP
    @property
    def ListU(self) :
        return self.m_listU
    


class CScoMath :
    s_epsilon = 0.0001

    def __init__(self) :
        pass


    @staticmethod
    def deg_to_rad(deg : float) :
        return math.radians(deg)
    @staticmethod
    def rad_to_deg(rad : float) :
        return math.degrees(rad)
    
    @staticmethod
    def equal_vec3(v0 : CScoVec3, v1 : CScoVec3) :
        dist = v0.subtract(v1).length()
        return dist < CScoMath.s_epsilon
    @staticmethod
    def equal_vec4(v0 : CScoVec4, v1 : CScoVec4) :
        dist = v0.subtract(v1).length()
        return dist < CScoMath.s_epsilon
    
    @staticmethod
    def convert_vec_to_np(listVec : list) -> np.ndarray :
        retV = None
        for inx, v in enumerate(listVec) :
            if inx == 0 :
                retV = v.m_npVec.copy()
            else :
                retV = np.vstack((retV, v.m_npVec))
        return retV

    # vector & matrix 
    @staticmethod
    def mul_vec3_scalar(v : CScoVec3, s : float) :
        return CScoVec3(v.X * s, v.Y * s, v.Z * s)
    @staticmethod
    def mul_vec4_scalar(v : CScoVec3, s : float) :
        return CScoVec4(v.X * s, v.Y * s, v.Z * s, v.W * s)
    @staticmethod
    def mul_mat4(m0 : CScoMat4, m1 : CScoMat4) :
        retMat = CScoMat4()
        retMat.m_npMat = np.dot(m0.m_npMat, m1.m_npMat)
        return retMat
    @staticmethod
    def mul_mat4_vec3(m : CScoMat4, v : CScoVec3) :
        npVec3 = v.m_npVec.reshape(3, 1)
        npVec4 = np.vstack([npVec3, np.array([1.0])])

        retV = CScoVec4()
        retV.m_npVec = np.dot(m.m_npMat, npVec4).reshape(1, 4)
        return retV
    @staticmethod
    def mul_mat4_vec4(m : CScoMat4, v : CScoVec4) :
        npVec4 = v.m_npVec.reshape(4, 1)

        retV = CScoVec4()
        retV.m_npVec = np.dot(m.m_npMat, npVec4).reshape(1, 4)
        return retV
    
    # quaternion 
    @staticmethod
    def make_quaternion(x, y, z, w) :
        """
        x, y, z : vector 성분
        w       : scalar 성분
        """
        return Quaternion(w=w, x=x, y=y, z=z)
    @staticmethod
    def make_quaternion_with_axis_angle(axis : CScoVec3, radian=0.0) :
        return Quaternion(axis=axis.m_npVec[0], radians=radian)
    @staticmethod
    def quat_add(q0 : Quaternion, q1 : Quaternion) :
        return q0 + q1
    @staticmethod
    def quat_subtract(q0 : Quaternion, q1 : Quaternion) :
        return q0 - q1
    @staticmethod
    def quat_slerp(q0 : Quaternion, q1 : Quaternion, ratio=0.0) :
        return Quaternion.slerp(q0, q1, amount=ratio)
    @staticmethod
    def mul_quat(q0 : Quaternion, q1 : Quaternion) :
        return q0 * q1
    @staticmethod
    def get_quat_axis_radian(q : Quaternion) :
        """
        desc : quaternion의 회전축과 radian을 리턴한다. 
        return : (axis : CScoVec3, radian : float)
        """
        axis = CScoVec3(q.axis[0], q.axis[1], q.axis[2])
        radian = q.radians
        return (axis, radian)
    @staticmethod
    def quat_to_mat4(quat : Quaternion) :
        mat4 = CScoMat4()
        mat4.m_npMat = np.copy(quat.transformation_matrix)
        return mat4
    @staticmethod
    def mat4_to_quat(m : CScoMat4) :
        npMat = m.m_npMat.copy()
        npMat = np.delete(npMat, (3), axis=0)
        npMat = np.delete(npMat, (3), axis=1)
        q = R.from_matrix(npMat).as_quat()
        return Quaternion(x=q[0], y=q[1], z=q[2], w=q[3])
    @staticmethod
    def quat_rotation(q : Quaternion, v : CScoVec3) :
        npArr = np.array(q.rotate(v.m_npVec[0]))
        return CScoVec3(npArr[0], npArr[1], npArr[2])
    

    @staticmethod
    def get_axis_radian(view : CScoVec3, target : CScoVec3) :
        theta = math.acos(view.dot(target))
        axis = view.cross(target)

        # 이 부분은 임시 방편일 뿐임 
        if axis.length() <  CScoMath.s_epsilon :
            axis = CScoVec3(0, 0, 0)
        else :
            axis = axis.normalize()

        return (axis, theta)
    @staticmethod
    def get_rot_quat(view : CScoVec3, target : CScoVec3) :
        '''
        - desc
            - this method returns a quaternion that rotate view to target
            - 예외 처리 이슈 있음 
        - input
            - view : normalized
            - target : normalized 

        - base 
            - theta : acos(dot(view, target)) 
            - rotation axis : cross(view, target) -> CCW 
            - ret : rotation matrix -> pos 제외 
        '''
        theta = math.acos(view.dot(target))
        axis = view.cross(target).normalize()

        return CScoMath.make_quaternion_with_axis_angle(axis, theta)
    @staticmethod
    def get_rot_mat(view : CScoVec3, target : CScoVec3) :
        '''
        - desc
            - this method returns a matrix that rotate view to target
            - 예외 처리 이슈 있음 
        - input
            - view : normalized
            - target : normalized 

        - base 
            - theta : acos(dot(view, target)) 
            - rotation axis : cross(view, target) -> CCW 
            - ret : rotation matrix -> pos 제외 
        '''
        quat = CScoMath.get_rot_quat(view, target)

        return CScoMath.quat_to_mat4(quat)
    @staticmethod
    def get_rot_mat_with_pos(view : CScoVec3, target : CScoVec3, pos : CScoVec3) :
        '''
        - desc
            - this method returns a matrix that rotate view to target
        - input
            - view : normalized
            - target : normalized 

        - base 
            - theta : acos(dot(view, target)) 
            - rotation axis : cross(view, target) -> CCW 
            - ret : rotation matrix -> pos 제외 
        '''
        quat = CScoMath.get_rot_quat(view, target)
        mat = CScoMath.quat_to_mat4(quat)
        mat.set_translate(pos.X, pos.Y, pos.Z)

        return mat
    @staticmethod
    def get_mat_with_spacing_direction_origin(spacing : tuple, direction : tuple, origin : tuple) -> CScoMat4 :
        matScale = CScoMat4()
        matRot = CScoMat4()
        matTrans = CScoMat4()

        matScale.set_scale(spacing[0], spacing[1], spacing[2])
        matRot.rot_from_row(direction)
        matTrans.set_translate(origin[0], origin[1], origin[2])

        matRet = CScoMath.mul_mat4(matRot, matScale)
        matRet = CScoMath.mul_mat4(matTrans, matRet)
        return matRet
    @staticmethod
    def get_mat_with_direction_origin(direction : tuple, origin : tuple) -> CScoMat4 :
        matRot = CScoMat4()
        matTrans = CScoMat4()

        matRot.rot_from_row(direction)
        matTrans.set_translate(origin[0], origin[1], origin[2])

        matRet = CScoMath.mul_mat4(matTrans, matRot)
        return matRet
    
    @staticmethod
    def transform_plane(plane : CScoPlane, mat : CScoMat4) :
        transPt = CScoMath.mul_mat4_vec3(mat, plane.Point)
        transNormal = CScoMath.mul_mat4_vec4(mat, CScoVec4(plane.Normal.X, plane.Normal.Y, plane.Normal.Z, 0.0))

        plane = CScoPlane()
        plane.m_point = CScoVec3(transPt.X, transPt.Y, transPt.Z)
        plane.m_normal = CScoVec3(transNormal.X, transNormal.Y, transNormal.Z).normalize()
        plane.m_d =  -plane.Point.dot(plane.Normal)
        return plane
    @staticmethod
    def get_plane_mat(plane : CScoPlane) -> CScoMat4:
        centerPos = plane.Point
        axis, radian = CScoMath.get_axis_radian(CScoVec3(0, 0, 1), plane.Normal)
        if axis.length() < CScoMath.s_epsilon :
            axis = CScoVec3(0, 1, 0)
        matPlane = CScoMat4()
        matPlane.rot_from_axis_radian(axis, radian)
        matPlane.set_translate(centerPos.X, centerPos.Y, centerPos.Z)
        return matPlane


    # with SimpleITK
    @staticmethod
    def convert_mat4_from_sitk_versor_rigid3d_transform(transform : sitk.Transform) :
        tr = sitk.VersorRigid3DTransform(transform)

        center = tr.GetCenter()
        translation = tr.GetTranslation()
        rot = tr.GetMatrix()

        matCenter = CScoMat4()
        matTrans = CScoMat4()
        matRot = CScoMat4()

        matCenter.translate_3d(center[0], center[1], center[2])
        matInvCenter = matCenter.inverse()
        matTrans.translate_3d(translation[0], translation[1], translation[2])
        matRot.rot_from_row(rot)

        retMat = CScoMath.mul_mat4(matTrans, matCenter)
        retMat = CScoMath.mul_mat4(retMat, matRot)
        retMat = CScoMath.mul_mat4(retMat, matInvCenter)

        return retMat
    @staticmethod
    def convert_mat4_from_sitk_translate_transform(transform : sitk.Transform) :
        tr = sitk.Similarity3DTransform(transform)

        center = tr.GetCenter()
        scale = tr.GetScale()
        translation = tr.GetTranslation()
        rot = tr.GetMatrix()

        matCenter = CScoMat4()
        matScale = CScoMat4()
        matTrans = CScoMat4()
        matRot = CScoMat4()

        matCenter.translate_3d(center[0], center[1], center[2])
        matInvCenter = matCenter.inverse()
        matTrans.translate_3d(translation[0], translation[1], translation[2])
        matRot.rot_from_row(rot)
        matScale.scale(scale, scale, scale)

        retMat = CScoMath.mul_mat4(matTrans, matCenter)
        retMat = CScoMath.mul_mat4(retMat, matRot)
        retMat = CScoMath.mul_mat4(retMat, matScale)
        retMat = CScoMath.mul_mat4(retMat, matInvCenter)

        return retMat
    @staticmethod
    def convert_mat4_from_sitk_affine_transform(transform : sitk.Transform) :
        tr = sitk.AffineTransform(transform)

        center = tr.GetCenter()
        translation = tr.GetTranslation()
        rot = tr.GetMatrix()

        matCenter = CScoMat4()
        matTrans = CScoMat4()
        matRot = CScoMat4()

        matCenter.translate_3d(center[0], center[1], center[2])
        matInvCenter = matCenter.inverse()
        matTrans.translate_3d(translation[0], translation[1], translation[2])
        matRot.rot_from_row(rot)

        retMat = CScoMath.mul_mat4(matTrans, matCenter)
        retMat = CScoMath.mul_mat4(retMat, matRot)
        retMat = CScoMath.mul_mat4(retMat, matInvCenter)

        return retMat


    # intersection and collision
    @staticmethod
    def intersect_plane_ray(plane : CScoPlane, ray : CScoRay) :
        """
        desc : plane과 ray의 교차 테스트를 수행
        ret  : (bIntersect : Bool, ratio : float)
                bIntersect : True    교차
                            False   비교차
                ratio      : 교차 시점 
        """
        nd = plane.Normal.dot(ray.Dir)
        if abs(nd) < 0.0001 :
            return (False, 0.0)
        
        w = ray.Origin.subtract(plane.Point)
        ratio = -plane.Normal.dot(w) / nd

        return (True, ratio)
    @staticmethod
    def intersect_sphere_ray(spherePos : CScoVec3, radius : float, ray : CScoRay) :
        """
        ret  : (bIntersect : Bool, t1 : float, t2 : float)
                bIntersect : True    교차
                            False   비교차
                t1 : 첫번째 교차
                t2 : 두번째 교차
                t1 == t2 인 경우 ray는 sphere에 접한다.
        """
        L = spherePos.subtract(ray.Origin)
        tc = L.dot(ray.Dir)
        L = L.length()
        d = math.sqrt(L * L - tc * tc)

        if d > radius :
            return (False, 0.0, 0.0)
        
        t1c = math.sqrt(radius * radius - d * d)
        t1 = tc - t1c
        t2 = tc + t1c

        return (True, t1, t2)
    @staticmethod
    def intersect_aabb_vec3(aabb : CScoAABB, v : CScoVec3) :
        """
        desc : aabb 내부에 v가 존재하는가를 리턴
        ret  : True    내부에 있음
               False   외부에 있다.
        """

        # x, y는 기존과 동일하게 
        if v.X < aabb.Min.X or v.X > aabb.Max.X:
            return False
        if v.Y < aabb.Min.Y or v.Y > aabb.Max.Y:
            return False
        if v.Z < aabb.Min.Z or v.Z > aabb.Max.Z:
            return False
            
        return True
    @staticmethod
    def intersect_obb_vec3(obb : CScoOBB, v : CScoVec3) :
        """
        desc : obb 내부에 v가 존재하는가를 리턴
        ret  : True    내부에 있음
               False   외부에 있다.
        """
        mat4 = CScoMat4()
        mat4.rot_from_axis(obb.Tangent, obb.Up, obb.View)
        mat4.set_translate(obb.Pos.X, obb.Pos.Y, obb.Pos.Z)
        invMat4 = mat4.inverse()

        localV = CScoMath.mul_mat4_vec3(invMat4, v)

        # x, y는 기존과 동일하게 
        if np.abs(localV.X) > obb.HalfSize.X:
            return False
        if np.abs(localV.Y) > obb.HalfSize.Y:
            return False
        # z는 원점이 bottom으로  
        if localV.Z < 0 or localV.Z > obb.HalfSize.Z : 
            return False
            
        return True
    @staticmethod
    def intersect_obb_vec3_return_project(obb : CScoOBB, v : CScoVec3) :
        """
        desc : obb 내부에 v가 존재하는가를 리턴
               projectedVec3는 v를 obb의 local 좌표계로 이동후 XY-Plane에 대해 투영한 값이다. 
        ret  : (bIntersection, projectedVec3)
        """
        mat4 = CScoMat4()
        mat4.rot_from_axis(obb.Tangent, obb.Up, obb.View)
        mat4.set_translate(obb.Pos.X, obb.Pos.Y, obb.Pos.Z)
        invMat4 = mat4.inverse()

        localV = CScoMath.mul_mat4_vec3(invMat4, v)

        # x, y는 기존과 동일하게 
        if np.abs(localV.X) > obb.HalfSize.X:
            return (False, CScoVec3())
        if np.abs(localV.Y) > obb.HalfSize.Y:
            return (False, CScoVec3())
        # z는 원점이 bottom으로  
        if localV.Z < 0 or localV.Z > obb.HalfSize.Z : 
            return (False, CScoVec3())
            
        return (True, CScoVec3(localV.X, localV.Y, 0))
    @staticmethod
    def intersect_cylinder_vec3(cylinder : CScoCylinder, v : CScoVec3) :
        """
        desc : obb 내부에 v가 존재하는가를 리턴
        ret  : True    내부에 있음
                False   외부에 있다.
        """
        mat4 = CScoMat4()
        mat4.rot_from_axis(cylinder.Tangent, cylinder.Up, cylinder.View)
        mat4.set_translate(cylinder.Pos.X, cylinder.Pos.Y, cylinder.Pos.Z)
        
        invMat4 = mat4.inverse()

        localV = CScoMath.mul_mat4_vec3(invMat4, v)

        # x, y는 기존과 동일하게 
        if np.abs(localV.X) > cylinder.HalfSize.X:
            return False
        if np.abs(localV.Y) > cylinder.HalfSize.Y:
            return False
        # z는 원점이 bottom  
        if localV.Z < 0 or localV.Z > cylinder.HalfSize.Z : 
            return False
        
        localV.Z = 0
        lenSq = localV.X * localV.X + localV.Y * localV.Y
        radiusSq = cylinder.Radius * cylinder.Radius
        if lenSq > radiusSq : 
            return False
            
        return True
    
    # fitting 
    '''
    @staticmethod
    def circle_fitting_with_leastsq(xList : list, yList : list) :
        x = np.array(xList)
        y = np.array(yList)
        x_m = np.mean(x)
        y_m = np.mean(y)
        method = "leastsq"

        def calc_R(xc, yc) :
            return np.sqrt((x - xc) ** 2 + (y - yc) ** 2)
        def f_2(c):
            Ri = calc_R(*c)
            return Ri - Ri.mean()

        center_estimate = x_m, y_m
        center_2, iter = optimize.leastsq(f_2, center_estimate)

        cx, cy = center_2
        Ri_2       = calc_R(cx, cy)
        radius        = Ri_2.mean()

        return (cx, cy, radius)
    '''
    @staticmethod
    def circle_fitting_with_leastsq(xList : list, yList : list) :
        def circle_residuals(params, xList, yList):
            x0, y0, radius = params
            distance = np.sqrt((xList - x0)**2 + (yList - y0)**2)
            residuals = distance - radius
            return residuals

        x = np.array(xList)
        y = np.array(yList)
        x_m = np.mean(x)
        y_m = np.mean(y)
        radius_m = np.sqrt(np.mean((x - x_m)**2 + (y - y_m)**2))
        params_guess = [x_m, y_m, radius_m]

        result = least_squares(circle_residuals, params_guess, args=(xList, yList))
        cx, cy, radius = result.x

        return (cx, cy, radius)
    @staticmethod
    def circle_fitting_with_powell(xList : list, yList : list) :
        def objective(xc_yc_r, points):
            xc, yc, r = xc_yc_r
            dist = np.sqrt((points[:,0] - xc)**2 + (points[:,1] - yc)**2)
            return np.sum((dist - r)**2)

        def fit_circle(points):
            x0 = np.array([np.mean(points[:,0]), np.mean(points[:,1]), 1.0])
            res = optimize.minimize(objective, x0, args=points, method='Powell')
            #res = optimize.minimize(objective, x0, args=points, method='lm')
            return res.x[:2], res.x[2]

        arrTmp = []
        for inx, _ in enumerate(xList) :
            arrTmp.append([xList[inx], yList[inx]])

        points = np.array(arrTmp)
        center, radius = fit_circle(points)
        cx, cy = center

        return (cx, cy, radius)
    @staticmethod
    def circle_fitting_with_cv(xList : list, yList : list) :
        minX = np.min(xList)
        maxX = np.max(xList)
        minY = np.min(yList)
        maxY = np.max(yList)
        width = int(maxX + 0.5) - int(minX + 0.5) + 3
        height = int(maxY + 0.5) - int(minY + 0.5) + 3
        npTmp = np.zeros((width, height), dtype='uint8')

        for inx in range(0, len(xList)) :
            x = xList[inx] - minX
            y = yList[inx] - minY
            x = int(x + 0.5)
            y = int(y + 0.5)
            npTmp[(x, y)] = 255

        contours, _ = cv2.findContours(npTmp, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        areas = [cv2.contourArea(c) for c in contours]
        sorted_areas = np.sort(areas)

        #bounding box
        cnt = contours[areas.index(sorted_areas[-1])] #the biggest contour
        #r = cv2.boundingRect(cnt)
        #cv2.rectangle(npTmp,(r[0],r[1]),(r[0]+r[2],r[1]+r[3]),(0,0,255),2)

        #min circle
        (cx, cy), radius = cv2.minEnclosingCircle(cnt)

        ''' dbg start
        plt.imshow(npTmp)
        plt.show()
        dbg end '''

        return (cx, cy, radius)




class CCircleFitting :
    def __init__(self) -> None:
        self.m_listLocalCoord = []

    def process(self, plane : CScoPlane, listVoxelInx : list) -> float : 
        # plane matrix 및 inverse matrix 추출 
        # 모든 vertex에 대한 inverse matrix 적용 
        # xy-plane projection 
        # circle fitting 
        axis, radian = CScoMath.get_axis_radian(CScoVec3(0, 0, 1), plane.Normal)
        if axis.length() < CScoMath.s_epsilon :
            axis = CScoVec3(0, 1, 0)
        
        planeCoord = plane.Point
        
        matPlane = CScoMat4()
        matPlane.rot_from_axis_radian(axis, radian)
        matPlane.set_translate(planeCoord.X, planeCoord.Y, planeCoord.Z)
        invMatPlane = matPlane.inverse()
        self.dbg_invMatPlane = invMatPlane

        self.m_listLocalCoord.clear()

        for voxelInx in listVoxelInx : 
            v = CScoVec3(voxelInx[0], voxelInx[1], voxelInx[2])
            retV = CScoMath.mul_mat4_vec3(invMatPlane, v)
            self.m_listLocalCoord.append(CScoVec3(retV.X, retV.Y, 0.0)) # xy-plane projection

        listX = []
        listY = []
        for localCoord in self.m_listLocalCoord :
            listX.append(localCoord.X)
            listY.append(localCoord.Y)

        cx, cy, radius = CScoMath.circle_fitting_with_cv(listX, listY)
        #cx, cy, radius = CScoMath.circle_fitting_with_leastsq(listX, listY)
        #cx, cy, radius = CScoMath.circle_fitting_with_powell(listX, listY)

        ''' debug with plotXY
        t = np.linspace(0, 2 * np.pi, 1000, endpoint=True)
        plt.scatter(listX, listY, color='r')
        plt.plot(radius * np.cos(t) + cx, radius * np.sin(t) + cy)
        plt.axis('equal')
        plt.show()
        #'''
        return radius
    




