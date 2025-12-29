import matplotlib.pyplot as plt
import SimpleITK as sitk
import cv2
import numpy as np
import os
import open3d as o3d
import open3d.core
import open3d.visualization

import scoUtil
import scoMath
import scoRenderObj
import scoSkeleton
from abc import abstractmethod

import open3d as o3d
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering

import json

    

class CScoSplineSegment(scoSkeleton.CScoSkelNode) :
    def __init__(self) :
        super().__init__()
        self.m_type = scoSkeleton.CScoSkelNode.eVoxelTypeVessel
        self.m_segmentType = scoSkeleton.CScoSkelSegment.eSegmentType_None
        self.m_listCP = []
        self.m_listRadius = []
        self.m_listConnNode = []
        self.m_startU = scoMath.CScoVec3(0, 0, 0)
        self.m_endU = scoMath.CScoVec3(0, 0, 0)
    def clear(self) :
        self.m_listCP.clear()
        self.m_listRadius.clear()
        self.m_listConnNode.clear()
        self.m_segmentType = scoSkeleton.CScoSkelSegment.eSegmentType_None
        self.m_startU = scoMath.CScoVec3(0, 0, 0)
        self.m_endU = scoMath.CScoVec3(0, 0, 0)
        super().clear()

    def add_cp(self, coord : scoMath.CScoVec3) :
        self.m_listCP.append(coord)
    def get_cp(self, inx : int) -> scoMath.CScoVec3 :
        return self.m_listCP[inx]
    def add_radius(self, radius : float) :
        self.m_listRadius.append(radius)
    def get_radius(self, inx : int) -> float :
        return self.m_listRadius[inx]
    def add_conn_node(self, node : scoSkeleton.CScoSkelNode) :
        self.m_listConnNode.append(node)
    def get_conn_node(self, inx : int) -> scoSkeleton.CScoSkelNode :
        return self.m_listConnNode[inx]


    def dbg_process(self, color : tuple) :
        pass
        #self.DBGPCD = scoRenderObj.CRenderObj.convert_scovec3_to_pcd(self.ListCoord, color)

    
    @property
    def SegmentType(self) :
        return self.m_segmentType
    @property
    def ListCP(self) :
        return self.m_listCP
    @property
    def CPCount(self) :
        return len(self.m_listCP)
    @property
    def ListRadius(self) :
        return self.m_listRadius
    @property
    def RadiusCount(self) :
        return len(self.m_listRadius)
    @property
    def ListConnNode(self) :
        return self.m_listConnNode
    @property
    def ConnNodeCount(self) :
        return len(self.m_listConnNode)
    @property
    def StartU(self) :
        return self.m_startU
    @StartU.setter
    def StartU(self, startU : scoMath.CScoVec3) :
        self.m_startU = startU.clone()
    @property
    def EndU(self) :
        return self.m_endU
    @EndU.setter
    def EndU(self, endU : scoMath.CScoVec3) :
        self.m_endU = endU.clone()



class CScoSplineSkel :
    def __init__(self) :
        self.m_shape = (0, 0, 0)
        self.m_listBranchGroup = []     # list(CScoSkelBranch, ..)
        self.m_listEndPoint = []        # list(CScoSkelEndPoint, ..)
        self.m_listSplineSeg = []       # list(CScoSplineSegment, ..)

        self.m_matPhysical = scoMath.CScoMat4()
    def clear(self) :
        self.m_shape = (0, 0, 0)
        self.m_listBranchGroup.clear()
        self.m_listEndPoint.clear()
        self.m_listSplineSeg.clear()

        self.m_matPhysical.identity()


    @property
    def Shape(self) :
        return self.m_shape
    @property
    def ListBranchGroup(self) :
        return self.m_listBranchGroup
    @property
    def ListEndPoint(self) :
        return self.m_listEndPoint
    @property
    def ListSplineSeg(self) :
        return self.m_listSplineSeg
    @property
    def BranchGroupCount(self) :
        return len(self.m_listBranchGroup)
    @property
    def EndPointCount(self) :
        return len(self.m_listEndPoint)
    @property
    def SplineSegCount(self) :
        return len(self.m_listSplineSeg)
    @property
    def MatPhysical(self) :
        return self.m_matPhysical
    @MatPhysical.setter
    def MatPhysical(self, matPhysical : scoMath.CScoMat4) :
        self.m_matPhysical = matPhysical.clone()

