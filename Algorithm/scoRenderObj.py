import numpy as np
import matplotlib.pyplot as plt
import SimpleITK as sitk
import cv2
import os, sys
import open3d as o3d
import open3d.core
import open3d.visualization
import matplotlib.patches as patches

import scoUtil
import scoReg
import scoMath
import scoBuffer

import open3d as o3d
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering

import math


class CRenderObj :
    def __init__(self) : 
        self.m_key = ""
        self.m_geometry = None
        self.m_mtrl = None
        self.m_matWorld = scoMath.CScoMat4()

        self.m_parent = None
        self.m_listChild = []

        self.m_bUpdate = False
        self.m_bVisible = False
    def clear(self) : 
        self.m_key = ""
        self.m_geometry = None
        self.m_mtrl = None
        self.m_matWorld.identity()

        self.m_parent = None
        self.m_listChild.clear()

        self.m_bUpdate = False
        self.m_bVisible = False

    # post call
    def update(self, scene) :
        for child in self.m_listChild :
            child.update(scene)

    def add_child(self, childRenderObj) :
        childRenderObj.m_parent = self
        self.m_listChild.append(childRenderObj)
    def get_child_cnt(self) :
        return len(self.m_listChild)
    def get_child(self, inx : int) :
        return self.m_listChild[inx]
    def get_child_inx(self, childRenderObj) :
        return self.m_listChild.index(childRenderObj)
    
    # signal

    # invoked
    def invoked_change_child(self, childRenderObj) :
        pass

    

    @staticmethod
    def convert_scovec3_to_open3d(listVec3 : list) -> list :
        listVertex = []

        for v in listVec3 :
            listVertex.append((v.X, v.Y, v.Z))
        
        return listVertex
    @staticmethod
    def convert_scovec3_to_pcd(listVec3 : list, color : tuple) :
        if len(listVec3) == 0 :
            return None
        
        coord = scoMath.CScoMath.convert_vec_to_np(listVec3)

        coordColor = coord.copy()
        # order : r, g, b  range : 0.0 ~ 1.0
        coordColor[:,0] = color[0]
        coordColor[:,1] = color[1]
        coordColor[:,2] = color[2]

        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(coord)
        pcd.colors = o3d.utility.Vector3dVector(coordColor)

        return pcd


    @property
    def Key(self) :
        return self.m_key
    @Key.setter
    def Key(self, key : str) :
        self.m_key = key
    @property
    def Geometry(self) :
        return self.m_geometry
    @Geometry.setter
    def Geometry(self, geometry) :
        self.m_geometry = geometry
    @property
    def Mtrl(self) :
        return self.m_mtrl
    @Mtrl.setter
    def Mtrl(self, mtrl) :
        self.m_mtrl = mtrl
    @property
    def WorldMatrix(self) :
        return self.m_matWorld
    @WorldMatrix.setter
    def WorldMatrix(self, mat : scoMath.CScoMat4) :
        self.m_matWorld = mat.clone()
    @property
    def Parent(self) :
        return self.m_parent
    @property
    def ListChild(self) :
        return self.m_listChild
    @property
    def Update(self) :
        return self.m_bUpdate
    @Update.setter
    def Update(self, bUpdate : bool) :
        self.m_bUpdate = bUpdate
        for child in self.m_listChild :
            child.Update = bUpdate
    @property
    def Visible(self) :
        return self.m_bVisible
    @Visible.setter
    def Visible(self, bVisible : bool) :
        self.m_bVisible = bVisible
        for child in self.m_listChild :
            child.Visible = bVisible


class CRenderObjRay(CRenderObj) :
    def __init__(self):
        super().__init__()
        self.m_origin = scoMath.CScoVec3()
        self.m_dir = scoMath.CScoVec3()
        self.m_geometry = o3d.geometry.LineSet()

        self.m_mtrl = rendering.MaterialRecord()
        self.m_mtrl.shader = "unlitLine"  # to use line_width property
        self.m_mtrl.base_color = (1, 1, 1, 1)
        self.m_mtrl.line_width = 5

        listLine = []
        listLine.append((0, 1))
        resLine = o3d.utility.Vector2iVector(listLine)
        self.Geometry.lines = resLine

        self.m_bUpdate = True


    def update(self, scene) :
        # input your code 
        if self.m_bUpdate == True :
            if scene.has_geometry(self.Key) == True :
                scene.remove_geometry(self.Key)

            retV = self.m_origin.add(self.m_dir)

            listVertex = []
            listVertex.append((self.m_origin.X, self.m_origin.Y, self.m_origin.Z))
            listVertex.append((retV.X, retV.Y, retV.Z))
            resVertex = o3d.utility.Vector3dVector(listVertex)
            self.Geometry.points = resVertex

            scene.add_geometry(self.Key, self.Geometry, self.Mtrl)

            self.m_bUpdate = False

        scene.set_geometry_transform(self.Key, self.WorldMatrix.m_npMat)
        super().update(scene)

    def set_ray(self, origin : scoMath.CScoVec3, dir : scoMath.CScoVec3, color : tuple) :
        self.m_origin = origin.clone()
        self.m_dir = dir.clone()
        self.m_mtrl.base_color = color
        self.m_matWorld.identity()
        self.m_bUpdate = True


    @property
    def Origin(self) :
        return self.m_origin
    @Origin.setter
    def Origin(self, origin : scoMath.CScoVec3) :
        self.m_origin = origin.clone()
        self.m_bUpdate = True
    @property
    def Dir(self) :
        return self.m_dir
    @Dir.setter
    def Dir(self, dir : scoMath.CScoVec3) :
        self.m_dir = dir.clone()
        self.m_bUpdate = True


class CRenderObjCircle(CRenderObj) :
    def __init__(self):
        super().__init__()

        self.m_pos = scoMath.CScoVec3(0, 0, 0)
        self.m_radius = 1.0

        self.Mtrl = rendering.MaterialRecord()
        self.Mtrl.shader = "defaultUnlit"  # to use line_width property
        self.Mtrl.base_color = (1, 1, 0, 1)
        self.Mtrl.point_size = 1

        self.Geometry = o3d.geometry.LineSet()

    def update(self, scene) :
        # input your code 
        if self.Update == True :
            if scene.has_geometry(self.Key) == True :
                scene.remove_geometry(self.Key)

            self.update_resource()
            scene.add_geometry(self.Key, self.Geometry, self.Mtrl)

            self.Update = False

        scene.set_geometry_transform(self.Key, self.WorldMatrix.m_npMat)
        super().update(scene)

    def make(self, radius : float) :
        self.m_radius = radius
        self.Update = True
    def set_coord(self, xAxis : scoMath.CScoVec3, yAxis : scoMath.CScoVec3, zAxis : scoMath.CScoVec3, pos : scoMath.CScoVec3) :
        self.m_pos = pos.clone()
        self.WorldMatrix.rot_from_axis(xAxis, yAxis, zAxis)
        self.WorldMatrix.set_translate(pos.X, pos.Y, pos.Z)

    def update_resource(self) :
        listVertex = []
        listLine = []

        axis = scoMath.CScoVec3(0, 0, 1)
        v = scoMath.CScoVec4(self.m_radius, 0, 0, 1)
        rotMat = scoMath.CScoMat4()
        for degree in range(0, 361, 10) :
            radian = scoMath.CScoMath.deg_to_rad(degree)
            rotMat.rot_from_axis_radian(axis, radian)
            retV = scoMath.CScoMath.mul_mat4_vec4(rotMat, v)
            listVertex.append([retV.X, retV.Y, retV.Z])

        for inx in range(0, len(listVertex) - 1) :
            listLine.append([inx, inx + 1])

        resLine = o3d.utility.Vector2iVector(listLine)
        self.Geometry.points = o3d.utility.Vector3dVector(listVertex)
        self.Geometry.lines = resLine


    @property
    def Radius(self) :
        return self.m_radius
    @Radius.setter
    def Radius(self, radius : float) :
        self.m_radius = radius
        self.Update = True
    @property
    def Pos(self) :
        return self.m_pos
    @Pos.setter
    def Pos(self, pos : scoMath.CScoVec3) :
        self.m_pos = pos.clone()
        self.WorldMatrix.set_translate(self.m_pos.X, self.m_pos.Y, self.m_pos.Z)
    


class CRenderObjAABB(CRenderObj) :
    def __init__(self):
        super().__init__()

        listLine = [
            [0, 1], [1, 2], [2, 3], [3, 0],
            [4, 5], [5, 6], [6, 7], [7, 4],
            [0, 4], [1, 5], [2, 6], [3, 7]
        ]
        self.m_resLine = o3d.utility.Vector2iVector(listLine)
        self.Mtrl = rendering.MaterialRecord()
        self.Mtrl.shader = "defaultUnlit"  # to use line_width property
        self.Mtrl.base_color = (0, 0, 1, 1)
        self.Mtrl.point_size = 1

        self.m_key = "keyAABB"
        self.m_aabb = scoMath.CScoAABB()
        self.Geometry = o3d.geometry.LineSet()

    def update(self, scene) :
        # input your code 
        if self.Update == True :
            if scene.has_geometry(self.Key) == True :
                scene.remove_geometry(self.Key)

            self.update_resource()
            scene.add_geometry(self.Key, self.Geometry, self.Mtrl)
            self.Update = False

        scene.set_geometry_transform(self.Key, self.WorldMatrix.m_npMat)
        super().update(scene)

    def make_with_min_max(self, min : scoMath.CScoVec3, max : scoMath.CScoVec3) :
        self.m_aabb.make_min_max(min, max)
        self.Update = True
    def get_min_max_with_world_matrix(self, worldMat : scoMath.CScoMat4) :
        return self.m_aabb.get_min_max_with_world_matrix(worldMat)

    def update_resource(self) :
        listVertex = [
            [self.m_aabb.Min.X, self.m_aabb.Max.Y, self.m_aabb.Min.Z],  # p0
            [self.m_aabb.Min.X, self.m_aabb.Min.Y, self.m_aabb.Min.Z],  # p1
            [self.m_aabb.Max.X, self.m_aabb.Min.Y, self.m_aabb.Min.Z],  # p2
            [self.m_aabb.Max.X, self.m_aabb.Max.Y, self.m_aabb.Min.Z],  # p3

            [self.m_aabb.Min.X, self.m_aabb.Max.Y, self.m_aabb.Max.Z],  # p0
            [self.m_aabb.Min.X, self.m_aabb.Min.Y, self.m_aabb.Max.Z],  # p1
            [self.m_aabb.Max.X, self.m_aabb.Min.Y, self.m_aabb.Max.Z],  # p2
            [self.m_aabb.Max.X, self.m_aabb.Max.Y, self.m_aabb.Max.Z]   # p3
        ]

        self.Geometry.points = o3d.utility.Vector3dVector(listVertex)
        self.Geometry.lines = self.m_resLine
    
    @property
    def AABB(self) :
        return self.m_aabb
    

class CRenderObjCylinder(CRenderObj) :
    def __init__(self):
        super().__init__()

        listLine = [
            [0, 1], [0, 2], [0, 3]
        ]

        self.m_resLine = o3d.utility.Vector2iVector(listLine)

        self.Mtrl = rendering.MaterialRecord()
        self.Mtrl.shader = "defaultUnlit"  # to use line_width property
        self.Mtrl.base_color = (0, 0, 0, 1)
        self.Mtrl.point_size = 1

        self.m_cylinder = scoMath.CScoCylinder()
        self.Geometry = o3d.geometry.LineSet()

    def update(self, scene) :
        # input your code 
        if self.Update == True :
            if scene.has_geometry(self.Key) == True :
                scene.remove_geometry(self.Key)

            self.update_resource()
            scene.add_geometry(self.Key, self.Geometry, self.Mtrl)
            #scene.set_geometry_transform(self.Key, self.WorldMatrix.m_npMat)
            self.Update = False
        super().update(scene)
    
    def make_with_2_point(self, p0 : scoMath.CScoVec3, p1 : scoMath.CScoVec3, halfSize : scoMath.CScoVec3) :
        self.m_cylinder.make_with_2_point(p0, p1, halfSize)
        self.Update = True
    def make_with_3_point(self, p0 : scoMath.CScoVec3, p1 : scoMath.CScoVec3, p2 : scoMath.CScoVec3, halfSize : scoMath.CScoVec3) :
        self.m_cylinder.make_with_3_point(p0, p1, p2, halfSize)
        self.Update = True
    def update_resource(self) :
        p0 = self.m_cylinder.Pos
        p1 = self.m_cylinder.Pos.add(self.m_cylinder.Tangent)
        p2 = self.m_cylinder.Pos.add(self.m_cylinder.Up)
        p3 = self.m_cylinder.Pos.add(self.m_cylinder.View)

        listVertex = [
            [p0.X, p0.Y, p0.Z],    # p0
            [p1.X, p1.Y, p1.Z],    # p1
            [p2.X, p2.Y, p2.Z],    # p2
            [p3.X, p3.Y, p3.Z]     # p3
        ]

        self.Geometry.points = o3d.utility.Vector3dVector(listVertex)
        self.Geometry.lines = self.m_resLine

    @property
    def WorldMatrix(self) :
        return self.m_cylinder.WorldMatrix
    @property
    def Cylinder(self) :
        return self.m_cylinder

class CRenderObjOBB(CRenderObj) :
    def __init__(self):
        super().__init__()

        listLine = [
            [0, 1], [1, 2], [2, 3], [3, 0],
            [4, 5], [5, 6], [6, 7], [7, 4],
            [0, 4], [1, 5], [2, 6], [3, 7],
            [8, 9], [8, 10], [8, 11]
        ]
        self.m_resLine = o3d.utility.Vector2iVector(listLine)
        self.m_mtrlNormal = rendering.MaterialRecord()
        self.m_mtrlNormal.shader = "defaultUnlit"  # to use line_width property
        self.m_mtrlNormal.base_color = (0, 0, 1, 1)
        self.m_mtrlNormal.point_size = 1
        self.m_mtrlCollision = rendering.MaterialRecord()
        self.m_mtrlCollision.shader = "defaultUnlit"  # to use line_width property
        self.m_mtrlCollision.base_color = (1, 0, 0, 1)
        self.m_mtrlCollision.point_size = 1

        self.m_key = "key_obb"
        self.m_obb = scoMath.CScoOBB()
        self.Geometry = o3d.geometry.LineSet()

        '''
        0 : normal
        1 : collision
        '''
        self.m_state = 0
        self.m_bUpdateRes = False

    def update(self, scene) :
        # input your code 

        if self.Update == True :
            if scene.has_geometry(self.Key) == True :
                scene.remove_geometry(self.Key)

            self.update_resource()
            scene.add_geometry(self.Key, self.Geometry, self.Mtrl)
            self.Update = False

        if scene.has_geometry(self.Key) == False :
            scene.add_geometry(self.Key, self.Geometry, self.Mtrl)
        scene.set_geometry_transform(self.Key, self.WorldMatrix.m_npMat)

        super().update(scene)

    def make_with_2_point(self, p0 : scoMath.CScoVec3, p1 : scoMath.CScoVec3) :
        self.m_obb.make_with_2_point(p0, p1, self.m_obb.HalfSize)
        self.Update = True
    def make_with_3_point(self, p0 : scoMath.CScoVec3, p1 : scoMath.CScoVec3, p2 : scoMath.CScoVec3) :
        self.m_obb.make_with_3_point(p0, p1, p2, self.m_obb.HalfSize)
        self.Update = True

    def update_resource(self) :
        listVertex = [
            [-self.m_obb.HalfSize.X, self.m_obb.HalfSize.Y, 0],     # p0
            [-self.m_obb.HalfSize.X, -self.m_obb.HalfSize.Y, 0],    # p1
            [self.m_obb.HalfSize.X, -self.m_obb.HalfSize.Y, 0],     # p2
            [self.m_obb.HalfSize.X, self.m_obb.HalfSize.Y, 0],      # p3

            [-self.m_obb.HalfSize.X, self.m_obb.HalfSize.Y, self.m_obb.HalfSize.Z],     # p4
            [-self.m_obb.HalfSize.X, -self.m_obb.HalfSize.Y, self.m_obb.HalfSize.Z],    # p5
            [self.m_obb.HalfSize.X, -self.m_obb.HalfSize.Y, self.m_obb.HalfSize.Z],     # p6
            [self.m_obb.HalfSize.X, self.m_obb.HalfSize.Y, self.m_obb.HalfSize.Z],      # p7

            [0, 0, 0],                      # p8 origin
            [self.m_obb.HalfSize.X, 0, 0],  # p9
            [0, self.m_obb.HalfSize.Y, 0],  # p10
            [0, 0, self.m_obb.HalfSize.Z]   # p11
        ]

        self.Geometry.points = o3d.utility.Vector3dVector(listVertex)
        self.Geometry.lines = self.m_resLine


    @property
    def WorldMatrix(self) :
        return self.m_obb.WorldMatrix
    @property
    def Mtrl(self) :
        if self.State == 0 :
            return self.m_mtrlNormal
        else  :
            return self.m_mtrlCollision
    @property
    def HalfSize(self) :
        return self.m_obb.HalfSize
    @HalfSize.setter
    def HalfSize(self, halfSize : scoMath.CScoVec3) :
        self.m_obb.HalfSize = halfSize
        self.Update = True
    @property
    def State(self) :
        return self.m_state
    @State.setter
    def State(self, state : int) :
        self.m_state = state
        self.Update = True
    @property
    def OBB(self) :
        return self.m_obb


class CRenderObjCP(CRenderObj) :
    '''
    - local 좌표계 기준으로 sphere 생성
    '''
    def __init__(self) :
        super().__init__()
        # input your code 
        self.m_radius = 1.0
        self.m_pos = scoMath.CScoVec3(0, 0, 0)
        #self.m_tangent = scoMath.CScoVec3(0, 0, 0)

        self.m_mtrl = rendering.MaterialRecord()
        self.m_mtrl.shader = "defaultUnlit"  # to use line_width property
        self.m_mtrl.base_color = (1, 1, 1, 1)
        self.m_mtrl.point_size = 1

        self.m_bUpdate = True

    def update(self, scene) :
        # input your code 
        if self.m_bUpdate == True :
            if scene.has_geometry(self.Key) == False :
                listPt = [(0, 0, 0)]
                self.m_geometry = scoUtil.CScoUtilSimpleITK.get_pcd_sphere_from_list(listPt, self.m_radius, (1, 1, 1))
                scene.add_geometry(self.Key, self.Geometry, self.Mtrl)

            self.m_matWorld.set_translate(self.m_pos.X, self.m_pos.Y, self.m_pos.Z)
            scene.set_geometry_transform(self.Key, self.WorldMatrix.m_npMat)
            self.m_bUpdate = False

        super().update(scene)

    def set_sphere(self, pos : scoMath.CScoVec3, radius : float, color : tuple) :
        self.m_pos = pos.clone()
        self.m_radius = radius
        self.m_mtrl.base_color = color
        self.m_bUpdate = True
    def add_child(self, ray : CRenderObjRay) :
        super().add_child(ray)
        self.m_bUpdate = True

    @property
    def Pos(self) :
        return self.m_pos
    @Pos.setter
    def Pos(self, pos : scoMath.CScoVec3) :
        self.m_pos = pos.clone()
        if self.Parent is not None :
            self.Parent.invoked_change_child(self)
        self.Update = True
    @property
    def Radius(self) :
        return self.m_radius
    @Radius.setter
    def Radius(self, radius : float) :
        self.m_radius = radius
        self.m_bUpdate = True


class CRenderObjCurve(CRenderObj) :
    def __init__(self, key : str, spline : scoMath.CScoSpline, cpRadius = 5.0):
        super().__init__()
        # input your code 

        self.Key = key
        self.m_geometry = o3d.geometry.LineSet()
        self.m_geometryU = o3d.geometry.LineSet()

        self.m_mtrl = rendering.MaterialRecord()
        self.m_mtrl.shader = "unlitLine"        # to use line_width property
        self.m_mtrl.base_color = (1, 0, 0, 1)
        self.m_mtrl.line_width = 5

        self.m_mtrlU = rendering.MaterialRecord()
        self.m_mtrlU.shader = "unlitLine"		# to use line_width property
        self.m_mtrlU.base_color = (0, 1, 0, 1)
        self.m_mtrlU.line_width = 2

        # create scene graph
        self.m_spline = spline
        #listLine.append((0, 1))
        #'''
        for inx, cp in enumerate(self.m_spline.ListCP) :
            renderObjCP = CRenderObjCP()
            renderObjCP.Key = f"{self.Key}keyCP{inx}"
            renderObjCP.set_sphere(cp, cpRadius, (1, 0, 0, 1))
            self.add_child(renderObjCP)
        #'''
        self.update_u()
        self.m_bUpdate = True
        self.m_bDbg = True

    def update(self, scene) :
        # input your code 
        if self.m_bUpdate == True :
            if len(self.ListChild) < 2 : 
                self.m_geometry = None
            else :
                self.render_segment(scene)
                self.render_u(scene)
            
            super().update(scene)
            self.m_bUpdate = False
    def update_u(self) :
        listLine = []
        listVertex = []
        for inx, cp in enumerate(self.m_spline.ListCP) :
            u = self.m_spline.ListU[inx]
            retV = cp.add(u)

            listVertex.append((cp.X, cp.Y, cp.Z))
            listVertex.append((retV.X, retV.Y, retV.Z))
            lineInx0 = len(listVertex) - 2
            listLine.append((lineInx0, lineInx0 + 1))
        #'''

        resLine = o3d.utility.Vector2iVector(listLine)
        self.m_geometryU.lines = resLine
        resVertex = o3d.utility.Vector3dVector(listVertex)
        self.m_geometryU.points = resVertex

    def render_segment(self, scene) :
        if scene.has_geometry(self.Key) == True :
            scene.remove_geometry(self.Key)

        listLine = []
        listV = self.m_spline.get_all_points()
        #listV = self.m_spline.get_points_ratio_to_end_in_knot(0.5)
        #listV = self.m_spline.get_points_start_to_ratio_in_knot(0.6)
        #listV = self.m_spline.get_points_within_ratio_range_in_knot(0.2, 0.8)
        #listV = self.m_spline.get_points_within_ratio_range(0.6, 2.6)
        listVertex = self.convert_scovec3_to_open3d(listV)

        for inx in range(0, len(listVertex) - 1) :
            listLine.append([inx, inx + 1])

        resVertex = o3d.utility.Vector3dVector(listVertex)
        resLine = o3d.utility.Vector2iVector(listLine)
        self.m_geometry.points = resVertex
        self.m_geometry.lines = resLine

        scene.add_geometry(self.Key, self.Geometry, self.Mtrl)
    def render_u(self, scene) :
        key = f"{self.Key}keyU"
        if scene.has_geometry(key) == True :
            scene.remove_geometry(key)
        scene.add_geometry(key, self.m_geometryU, self.m_mtrlU)

    # invoked
    def invoked_change_child(self, childRenderObj) :
        childInx = self.get_child_inx(childRenderObj)
        self.m_spline.ListCP[childInx] = childRenderObj.Pos.clone()

        firstU = self.m_spline.FirstU
        endU = self.m_spline.EndU
        self.m_spline.process_U(firstU, endU)

        self.update_u()
        self.Update = True

    

    


