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
from collections import deque
from collections import defaultdict
import treeVessel as treeVessel





class CInvalidBranch:
    def __init__(self) :
        self.m_clID = -1
        self.m_branchID = -1
        
        #self.m_name = name
        self.m_fromNodeID = None
        self.m_toID = None
        self.m_vessel = None
        self.m_forwardDirection = True
        self.m_nodeIDToNodeID_BRID_clID_InvalidList = defaultdict(lambda: defaultdict(list))
    def clear(self) :
        self.m_ID = -1
        self.m_vessel = None
        self.m_nodeIDToNodeID_BRID_clID_InvalidList.clear()
    
    @property
    def CLID(self):
        return self.m_clID
    @CLID.setter
    def CLID(self, id):
        self.m_clID = id
        
    @property
    def BranchID(self):
        return self.m_branchID
    @BranchID.setter
    def BranchID(self, branchID):
        self.m_branchID = branchID
        
    @property
    def FromNodeID(self):
        return self.m_fromNodeID
    @FromNodeID.setter
    def FromNodeID(self, FromNodeId):
        self.m_fromNodeID = FromNodeId
        
    @property
    def ToNodeID(self):
        return self.m_toID
    @ToNodeID.setter
    def ToNodeID(self, ToNodeId):
        self.m_toID = ToNodeId
        
    @property
    def Vessel(self) -> vtk.vtkPolyData :
        return self.m_vessel
    @Vessel.setter
    def Vessel(self, vessel : vtk.vtkPolyData) :
        self.m_vessel = vessel
        
    @property
    def ForwardDirection(self) -> bool :
        return self.m_forwardDirection
    @ForwardDirection.setter
    def ForwardDirection(self, ForwardDirection : bool) :
        self.m_forwardDirection = ForwardDirection


    def get_valid_vessel(self) -> vtk.vtkPolyData :
        '''
        desc : 현재 노드를 중심으로 parent를 조회하면서 Vessel이 존재하는 Mesh를 리턴 
        '''
        node = self
        if node is not None :
            if node.Vessel is not None :
                return node.Vessel
        return None







class CNodeVessel:
    def __init__(self, id, name) :
        self.m_ID = id
        self.m_name = name
        self.m_listCLID = []
        self.m_seedCLID = set()
        self.m_vessel = None
    def clear(self) :
        self.m_ID = -1
        self.m_listCLID.clear()
        # if self.m_vessel is not None :
        #     self.m_vessel.Initialize()
        self.m_vessel = None
        self.m_seedCLID = set()
        self.m_name = ""
    # def clear_vessel(self) :
    #     self.m_vessel = None
    #     iCnt = self.get_child_node_count()
    #     for inx in range(0, iCnt) :
    #         child = self.get_child_node(inx)
    #         child.clear_vessel()


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
    
    
    @property
    def ID(self):
        return self.m_ID
    @ID.setter
    def ID(self, id):
        self.m_ID = id
    @property
    def Name(self):
        return self.m_name
    @Name.setter
    def Name(self, name):
        self.m_name = name
    @property
    def Vessel(self) -> vtk.vtkPolyData :
        return self.m_vessel
    @Vessel.setter
    def Vessel(self, vessel : vtk.vtkPolyData) :
        self.m_vessel = vessel

    def get_valid_vessel(self) -> vtk.vtkPolyData :
        node = self
        if node is not None :
            if node.Vessel is not None :
                return node.Vessel
        return None




'''
아래 graph를 만듦
Node ID to Node ID


'''

class CNodeGraph:
    def __init__(self, skeleton : algSkeletonGraph.CSkeleton):
        self.m_skeleton = skeleton
        self.m_graph = defaultdict(list)
        self.m_IDtoNode = defaultdict(CNodeVessel)
        
        self.m_connectedNodeID_BRIDtoCLID = defaultdict(lambda: defaultdict(set))
        
        self.m_visitedCLID = set()
        self.m_nodeNameSet = set()
        self.m_startNode = None
        
    def clear(self):
        self.m_graph = defaultdict(list)
        self.m_IDtoNode = defaultdict(CNodeVessel)
        
        self.m_connectedNodeID_BRIDtoCLID = defaultdict(lambda: defaultdict(set))
        
        self.m_visitedCLID = set()
        self.m_nodeNameSet = set()
        self.m_startNode = None
        
    def _get_child_clID(self, clID : int, childInx : int) -> int :
        connIDs = self.Skeleton.get_conn_centerline_id(clID)
        listChild = connIDs[1]
        return listChild[childInx]            
    
    def build_graph(self):
        skeleton = self.m_skeleton
        
        rootCLID = skeleton.RootCenterline.ID
        
        ID = 0
        
        startNode = CNodeVessel(ID, skeleton.get_centerline(rootCLID).Name)

        self.m_IDtoNode[startNode.ID] = startNode 
        self.m_startNode = startNode
        
        queueCLID = deque([])
        queueCLID.append((rootCLID, startNode))
        self.m_visitedCLID.add(rootCLID)
        startNode.m_seedCLID.add(rootCLID)
        self.m_nodeNameSet.add(skeleton.get_centerline(rootCLID).Name)
        
        # bfs 알고리즘 기반으로 centerline graph 전파
        
        while queueCLID:
            currentCLID, currentNode = queueCLID.popleft()
            #print(currentCLID, file=sys.__stdout__, flush=True)
            
            currentCL = skeleton.get_centerline(currentCLID)
            
            if currentCL.is_leaf() and currentCLID != rootCLID:
                pass
            else:
                for bi in range(2):
                    currentBR = currentCL.get_conn(bi)
                    if currentBR == None:
                        continue
                    listAdjCLID = [currentBR.get_conn(inx).ID for inx in range(currentBR.get_conn_count())]
                    for adjCLID in listAdjCLID:
                        adjCL = skeleton.get_centerline(adjCLID)
                        if adjCLID in self.m_visitedCLID:
                            if adjCL.Name != currentCL.Name:
                                for nodeID in range(ID+1):
                                    Node = self.m_IDtoNode[nodeID]
                                    if Node.Name == adjCL.Name:
                                        self.m_connectedNodeID_BRIDtoCLID[str(currentNode.ID) + "," + str(Node.ID)][currentBR.ID].add(currentCL.ID)
                                        self.m_connectedNodeID_BRIDtoCLID[str(Node.ID) + "," + str(currentNode.ID)][currentBR.ID].add(adjCL.ID)
                                        if Node.ID not in self.m_graph[currentNode.ID]:
                                            self.m_graph[currentNode.ID].append(Node.ID)
                                        if currentNode.ID not in self.m_graph[Node.ID]:
                                            self.m_graph[Node.ID].append(currentNode.ID)
                                continue
                            else:
                                continue
                        else:
                            # 같은 cl name 의 cl을 만났을 때    
                            if currentNode.Name == adjCL.Name:
                                currentNode.add_clID(adjCLID)
                                queueCLID.append((adjCLID, currentNode))
                                
                                for adjCLID_ in listAdjCLID:
                                    adjCL_ = skeleton.get_centerline(adjCLID_)
                                    if adjCL_.Name != currentCL.Name:
                                        for nodeID in range(ID+1):
                                            Node = self.m_IDtoNode[nodeID]
                                            if Node.Name == adjCL_.Name:
                                                self.m_connectedNodeID_BRIDtoCLID[str(currentNode.ID) + "," + str(Node.ID)][currentBR.ID].add(adjCL_.ID)
                                
                            
                            # 순회 중 처음 보는 Name 일 때 새로운 Node를 만듦
                            elif adjCL.Name not in self.m_nodeNameSet:
                                ID += 1
                                NewNode = CNodeVessel(ID, adjCL.Name)
                                self.m_graph[currentNode.ID].append(NewNode.ID)
                                self.m_graph[NewNode.ID].append(currentNode.ID)
                                self.m_connectedNodeID_BRIDtoCLID[str(currentNode.ID) + "," + str(NewNode.ID)][currentBR.ID].add(currentCL.ID)
                                self.m_connectedNodeID_BRIDtoCLID[str(NewNode.ID) + "," + str(currentNode.ID)][currentBR.ID].add(adjCL.ID)
                                NewNode.m_seedCLID.add(adjCLID)
                                self.m_IDtoNode[NewNode.ID] = NewNode
                                NewNode.add_clID(adjCLID)
                                self.m_nodeNameSet.add(NewNode.Name)
                                #print(NewNode.Name, file=sys.__stdout__, flush=True)
                                queueCLID.append((adjCLID, NewNode))
                                
                                for adjCLID_ in listAdjCLID:
                                    adjCL_ = skeleton.get_centerline(adjCLID_)
                                    if adjCL_.Name == currentCL.Name:
                                        self.m_connectedNodeID_BRIDtoCLID[str(currentNode.ID) + "," + str(NewNode.ID)][currentBR.ID].add(adjCL_.ID)
                                
                            # 순회 중 기존에 봤던 Name 인데 이전 CL의 Name과 다를 때 (Node가 이미 존재)
                            else:
                                for nodeID in range(ID+1):
                                    Node = self.m_IDtoNode[nodeID]
                                    if Node.Name == adjCL.Name:
                                        Node.add_clID(adjCLID)
                                        queueCLID.append((adjCLID, Node))
                                        self.m_connectedNodeID_BRIDtoCLID[str(currentNode.ID) + "," + str(Node.ID)][currentBR.ID].add(currentCL.ID)
                                        self.m_connectedNodeID_BRIDtoCLID[str(Node.ID) + "," + str(currentNode.ID)][currentBR.ID].add(adjCL.ID)
                                        Node.m_seedCLID.add(adjCLID)
                                        if Node.ID not in self.m_graph[currentNode.ID]:
                                            self.m_graph[currentNode.ID].append(Node.ID)
                                            self.m_graph[Node.ID].append(currentNode.ID)
                                        break
                                        
                            self.m_visitedCLID.add(adjCLID)
                            
    def get_adjacent_node(self, node):
        return [self.m_IDtoNode[id] for id in self.m_graph[node.ID]]
            
    @property
    def Skeleton(self) -> algSkeletonGraph.CSkeleton :
        return self.m_skeleton
    @property
    def StartNode(self) -> CNodeVessel :
        return self.m_startNode
    @StartNode.setter
    def StartNode(self, startNode):
        self.m_startNode = startNode
        

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
    def process(self, graphVessel : CNodeGraph) :
        self.m_graphVessel = graphVessel
        for nodeID in range(len(self.m_graphVessel.m_IDtoNode.keys())):
            self._add_node(self.m_graphVessel.m_IDtoNode[nodeID].Name, self.m_graphVessel.m_IDtoNode[nodeID])
            
        # firstNode = graphVessel.StartNode
        
        # visitedNodeID = set()
        # self._add_node(firstNode.Name, firstNode)
        # visitedNodeID.add(graphVessel.m_startNode.ID)
        # nodeQueue = deque([graphVessel.m_startNode])
        
        # while nodeQueue:
        #     node = nodeQueue.popleft()
        #     for adjNodeID in graphVessel.m_graph[node.ID]:
        #         if adjNodeID in visitedNodeID:
        #             continue
        #         adjNode = graphVessel.m_IDtoNode[adjNodeID]

        #         self._add_node(adjNode.Name, adjNode)
        #         nodeQueue.append(adjNode)
        #         visitedNodeID.add(adjNodeID)
        
        self._append_polydata()
        
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

        
    def _get_label(self, node : CNodeVessel) -> algSkeletonGraph.CSkeletonCenterline :
        clID = node.get_clID(0)
        cl = self.m_treeVessel.Skeleton.get_centerline(clID)
        if cl.Name == "" :
            return "Root"
        return cl.Name
    def _add_node(self, label : str, node :CNodeVessel) :
        if label not in self.m_dicNodeList :
            self.m_dicNodeList[label] = []
        self.m_dicNodeList[label].append(node)


    @property
    def OutDicPolyData(self) -> dict :
        return self.m_outDicPolyData
        

    