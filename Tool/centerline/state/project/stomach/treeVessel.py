import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import SimpleITK as sitk

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
import AlgUtil.algImage as algImage
import AlgUtil.algVTK as algVTK
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algMeshLib as algMeshLib

import Block.optionInfo as optionInfo

import command.curveInfo as curveInfo

import data as data

import userData as userData


'''
a -> b -> d
  -> c

node
- 자신을 의미하는 다수의 centerline들을 포함 
- 다수의 parent centerline들을 포함 
- 다수의 child node를 포함 

'''
class CNodeVesselHier :
    def __init__(self) :
        self.m_listCLID = []
        self.m_parent = None
        self.m_listChild = []
        self.m_vessel = None
    def clear(self) :
        self.m_listCLID.clear()
        self.m_parent = None
        self.m_listChild.clear()
        # if self.m_vessel is not None :
        #     self.m_vessel.Initialize()
        self.m_vessel = None
    def clear_vessel(self) :
        self.m_vessel = None
        iCnt = self.get_child_node_count()
        for inx in range(0, iCnt) :
            child = self.get_child_node(inx)
            child.clear_vessel()


    def add_clID(self, clID : int) :
        self.m_listCLID.append(clID)
    def get_clID_count(self) -> int :
        return len(self.m_listCLID)
    def get_clID(self, inx : int) -> int :
        return self.m_listCLID[inx]
    def find_clID_index(self, clID : int) -> int :
        try:
            return self.m_listCLID.index(clID)
        except ValueError :
            return -1
    
    def add_child_node(self, node) :
        node.Parent = self
        self.m_listChild.append(node)
    def get_child_node_count(self) -> int :
        return len(self.m_listChild)
    def get_child_node(self, inx : int) :
        return self.m_listChild[inx]
    def find_child_node_index(self, clID : int) -> int :
        iCnt = self.get_child_node_count()
        for inx in range(0, iCnt) :
            node = self.get_child_node(inx)
            if node.find_clID_index(clID) >= 0 :
                return inx
        return -1
    
    def get_valid_vessel(self) -> vtk.vtkPolyData :
        '''
        desc : 현재 노드를 중심으로 parent를 조회하면서 Vessel이 존재하는 Mesh를 리턴 
        '''
        node = self
        while node is not None :
            if node.Vessel is not None :
                return node.Vessel
            node = node.Parent
        return None
    def get_whole_vessel(self) -> vtk.vtkPolyData :
        '''
        desc : 현재 노드를 기준으로 whole vessel을 리턴한다.
               현재 노드를 기준으로는 parent vessel이 whole vessel이 된다. 
        '''
        # 이 부분은 엄밀하게 처리가 되어서는 안된다. 
        if self.Parent is None :
            return self.Vessel
        
        node = self.Parent
        while node is not None :
            if node.Vessel is not None :
                return node.Vessel
            node = node.Parent
        return None
    def set_whole_vessel(self, wholeVessel : vtk.vtkPolyData) :
        '''
        desc : 현재 노드를 기준으로 whole vessel을 세팅한다.
               현재 노드를 기준으로는 parent vessel이 whole vessel이 된다. 
        '''
        # 이 부분은 엄밀하게 처리가 되어서는 안된다. 
        if self.Parent is None :
            self.Vessel = wholeVessel
            return
        
        node = self.Parent
        while node is not None :
            if node.Vessel is not None :
                node.Vessel = wholeVessel
                break
            node = node.Parent


    @property
    def Parent(self) : 
        return self.m_parent
    @Parent.setter
    def Parent(self, parent) :
        self.m_parent = parent
    @property
    def Vessel(self) -> vtk.vtkPolyData :
        return self.m_vessel
    @Vessel.setter
    def Vessel(self, vessel : vtk.vtkPolyData) :
        self.m_vessel = vessel


class CTreeVessel : 
    def __init__(self, skeleton : algSkeletonGraph.CSkeleton):
        self.m_skeleton = skeleton
        self.m_listRootNode = []
    def clear(self) :
        self.m_skeleton = None
        self.clear_node()
    def clear_node(self) :
        for node in self.m_listRootNode :
            node.clear()
        self.m_listRootNode.clear()


    def build_tree_with_label(self, clID : int) :
        '''
        superRoot는 필요함 
        '''
        parentCLID = self._get_parent_clID(clID)
        parentNode = None
        if parentCLID > -1 :
            parentNode = CNodeVesselHier()
            parentNode.add_clID(parentCLID)

        self._build_tree_with_label(parentNode, clID)


    def add_root_node(self, node : CNodeVesselHier) :
        self.m_listRootNode.append(node)
    def get_root_node_count(self) -> int :
        return len(self.m_listRootNode)
    def get_root_node(self, inx : int) -> CNodeVesselHier :
        return self.m_listRootNode[inx]
    def get_first_root_node(self) -> CNodeVesselHier :
        if self.get_root_node_count() == 0 :
            return None
        node = self.get_root_node(0)
        if node.Parent is not None :
            return node.Parent
        else :
            return node
    def get_cl_label(self, node : CNodeVesselHier) -> str :
        if node.get_clID_count() == 0 :
            return ""
        clID = node.get_clID(0)
        cl = self.Skeleton.get_centerline(clID)
        return cl.Name


    # protected
    def _get_parent_clID(self, clID : int) -> int :
        '''
        ret : -1 (non parentCLID)
              else
        '''
        connIDs = self.Skeleton.get_conn_centerline_id(clID)
        parentCLID = connIDs[0]
        return parentCLID
    def _get_child_clID_count(self, clID : int) -> int :
        connIDs = self.Skeleton.get_conn_centerline_id(clID)
        listChild = connIDs[1]
        return len(listChild)
    def _get_child_clID(self, clID : int, childInx : int) -> int :
        connIDs = self.Skeleton.get_conn_centerline_id(clID)
        listChild = connIDs[1]
        return listChild[childInx]
    def _get_cl(self, clID : int) -> algSkeletonGraph.CSkeletonCenterline :
        return self.Skeleton.get_centerline(clID)
    
    def _build_tree_with_label(self, parentNode : CNodeVesselHier, clID : int) :
        node = CNodeVesselHier()
        node.add_clID(clID)
        if parentNode is not None :
            parentNode.add_child_node(node)
        self.add_root_node(node)
        
        cl = self._get_cl(clID)
        label = cl.Name
        listCLID = [self._get_child_clID(clID, inx) for inx in range(0, self._get_child_clID_count(clID))]

        for clID in listCLID :
            cl = self._get_cl(clID)
            if cl.Name == label :
                node.add_clID(clID)
                for inx in range(0, self._get_child_clID_count(clID)) :
                    listCLID.append(self._get_child_clID(clID, inx))
            else :
                self._build_tree_with_label(node, clID)

    
    @property
    def Skeleton(self) -> algSkeletonGraph.CSkeleton :
        return self.m_skeleton
    
class CMergePolyData :
    def __init__(self) :
        '''
        key : label
        value : [node0, node1, ..]
        '''
        self.m_dicNodeList = {}
        '''
        key : label
        value : polyData
        '''
        self.m_outDicPolyData = {}
    def clear(self) :
        self.m_dicNodeList.clear()
        self.m_outDicPolyData.clear()
    def process(self, treeVessel : CTreeVessel) :
        self.m_treeVessel = treeVessel
        firstNode = treeVessel.get_first_root_node()
        self._align_node_by_label(firstNode)
        self._append_polydata()
        
    
    def _align_node_by_label(self, node : CNodeVesselHier) :
        label = self._get_label(node)
        self._add_node(label, node)
        
        iCnt = node.get_child_node_count()
        for inx in range(0, iCnt) :
            childNode = node.get_child_node(inx)
            self._align_node_by_label(childNode)
    def _append_polydata(self) :
        for label, nodeList in self.m_dicNodeList.items() :
            append_filter = vtk.vtkAppendPolyData()
            for node in nodeList :
                if node.Vessel is None :
                    continue
                append_filter.AddInputData(node.Vessel)
            append_filter.Update()
            combinedPolydata = append_filter.GetOutput()

            if combinedPolydata is None :
                continue
            if combinedPolydata.GetNumberOfPoints() == 0 :
                continue

            self.m_outDicPolyData[label] = combinedPolydata

        
    def _get_label(self, node : CNodeVesselHier) -> algSkeletonGraph.CSkeletonCenterline :
        clID = node.get_clID(0)
        cl = self.m_treeVessel.Skeleton.get_centerline(clID)
        if cl.Name == "" :
            return "Whole"
        return cl.Name
    def _add_node(self, label : str, node :CNodeVesselHier) :
        if label not in self.m_dicNodeList :
            self.m_dicNodeList[label] = []
        self.m_dicNodeList[label].append(node)


    @property
    def OutDicPolyData(self) -> dict :
        return self.m_outDicPolyData
        

    

if __name__ == '__main__' :
    pass


# print ("ok ..")

