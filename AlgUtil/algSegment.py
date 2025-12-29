import sys
import os
# import torch
# from torch.autograd import Variable
import numpy as np
import math
from scipy.spatial import KDTree
# from sklearn.decomposition import PCA


fileAbsPath = os.path.abspath(os.path.dirname(__file__))
algorithmPath = os.path.dirname(fileAbsPath)
sys.path.append(fileAbsPath)
sys.path.append(algorithmPath)

# import algLinearMath
# import algGeometry
import Algorithm.scoUtil as scoUtil
import Algorithm.scoBuffer as scoBuffer
import Algorithm.scoBufferAlg as scoBufferAlg


class CSegmentBasedVoxelProcess :
    def __init__(self) -> None :
        self.m_anchor = None
        self.m_anchorSegInx = []
        self.m_npAnchorSegInx = None
        self.m_npNNIndex = None

        self.m_queryVertex = None
        self.m_npQuerySegInx = None

    def add_anchor(self, anchorVertex : np.ndarray, segInx : int) :
        if self.m_anchor is None :
            self.m_anchor = np.copy(anchorVertex)
        else :
            self.m_anchor= np.concatenate((self.m_anchor, anchorVertex), axis=0)
        self.m_anchorSegInx += [segInx for i in range(0, anchorVertex.shape[0])]
    def process(self, queryVertex : np.ndarray) :
        self.m_queryVertex = queryVertex
        self.m_npAnchorSegInx = np.array(self.m_anchorSegInx)

        print("kd-tree build start")
        tree = KDTree(self.m_anchor)
        print("kd-tree build complete")
        distances, self.m_npNNIndex = tree.query(queryVertex, k=1)
        self.m_npQuerySegInx = self.m_npAnchorSegInx[self.m_npNNIndex]
        print("completed segment")
    
    def get_query_vertex_with_seg_index(self, segInx : int) :
        indices = np.where(self.m_npQuerySegInx == segInx)
        return self.m_queryVertex[indices]
    

class CSegmentNode : 
    def __init__(self) -> None :
        self.m_id = 0
        self.m_name = ""
        self.m_queryVertex = None
        self.m_vertex = None
        self.m_parent = None
        self.m_listChild = []
    def clear(self) :
        self.m_id = 0
        self.m_name = ""
        self.m_queryVertex = None
        self.m_vertex = None
        self.m_parent = None
        for child in self.m_listChild :
            child.clear()
        self.m_listChild.clear()
    
    def add_child(self, segNode) :
        id = self.get_child_count()
        segNode.ID = id + 1
        segNode.Parent = self
        self.m_listChild.append(segNode)
    def get_child_count(self) :
        return len(self.m_listChild)
    def get_child(self, inx : int) :
        return self.m_listChild[inx]

    @property
    def Name(self) :
        return self.m_name
    @Name.setter
    def Name(self, name : str) :
        self.m_name = name
    @property
    def Vertex(self) :
        return self.m_vertex
    @Vertex.setter
    def Vertex(self, vertex : np.ndarray) :
        self.m_vertex = vertex
    @property
    def QueryVertex(self) :
        return self.m_queryVertex
    @QueryVertex.setter
    def QueryVertex(self, queryVertex : np.ndarray) :
        self.m_queryVertex = queryVertex
    @property
    def ID(self) :
        return self.m_id
    @ID.setter
    def ID(self, id : int) :
        self.m_id = id
    @property
    def Parent(self) :
        return self.m_parent
    @Parent.setter
    def Parent(self, parent) :
        self.m_parent = parent


class CTreeSegment :
    def __init__(self) -> None:
        self.m_root = CSegmentNode()
        self.m_root.Name = "root"
    def clear(self) :
        if self.m_root != None :
            self.m_root.clear()
        self.m_root.Name = "root"
    def process(self) :
        childCnt = self.Root.get_child_count()
        for i in range(0, childCnt) :
            self.__segment(self.Root.get_child(i))
            

    def add_node(self, tokenList : list) :
        node = self.m_root
        for token in tokenList :
            childNode = self.find_node(node, token)
            if childNode == None :
                childNode = CSegmentNode()
                childNode.Name = token
                node.add_child(childNode)
            node = childNode
        return node
    def find_node(self, parentNode : CSegmentNode, token : str) :
        iCnt = parentNode.get_child_count()
        for i in range(0, iCnt) :
            childNode = parentNode.get_child(i)
            if childNode.Name == token :
                return childNode
        return None
    def find_descendant_node(self, tokenList : list) :
        node = self.m_root
        for token in tokenList :
            childNode = self.find_node(node, token)
            if childNode.Name == token :
                node = childNode
            else :
                node = None
                break
        return node
    

    # private
    def __segment(self, node : CSegmentNode) :
        childCnt = node.get_child_count()
        if childCnt == 0 :
            return
        
        segmentProcess = CSegmentBasedVoxelProcess()

        for i in range(0, childCnt) :
            childNode = node.get_child(i)
            segmentProcess.add_anchor(childNode.Vertex, childNode.ID)

        segmentProcess.process(node.QueryVertex)

        for i in range(0, childCnt) :
            childNode = node.get_child(i)
            childNode.QueryVertex = segmentProcess.get_query_vertex_with_seg_index(childNode.ID)
            self.__segment(childNode)
    

    # debug
    def print(self) :
        retList = [self.m_root]
        for node in retList :
            print(f"{node.Name} : {node.ID}")
            iCnt = node.get_child_count()
            for i in range(0, iCnt) :
                retList.append(node.get_child(i))
    

    @property
    def Root(self) :
        return self.m_root