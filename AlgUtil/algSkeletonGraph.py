'''
- added centerline edit by sally (2025.03.10)
    - remove_centerlines
    
'''


import sys
import os
import numpy as np
# import math
import networkx as nx
# from sklearn.neighbors import KDTree
from scipy.spatial import KDTree
import gc
import json

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
sys.path.append(fileAbsPath)
import algLinearMath as algLinearMath
import algSpline as algSpline



class CSkeletonNode :
    def __init__(self, id : int) -> None :
        self.m_active = True
        self.m_name = ""
        self.m_id = id
        self.m_graphID = -1
        self.m_treeID = -1
        self.m_listConn = []
    def clear(self) :
        self.m_active = False
        self.m_name = ""
        self.m_id = -1
        self.m_graphID = -1
        self.m_treeID = -1
        self.m_listConn.clear()


    def get_class_name(self) :
        return self.__class__.__name__
    def add_conn(self, conn : object) :
        self.m_listConn.append(conn)
    def set_conn(self, inx : int, conn : object) :
        self.m_listConn[inx] = conn
    def get_conn_count(self) -> int :
        return len(self.m_listConn)
    def get_conn(self, inx : int) -> object :
        return self.m_listConn[inx]
    def find_conn_by_id(self, id : int) -> object :
        for conn in self.m_listConn :
            if conn.ID == id :
                return conn
        return None
    def find_conn_by_name(self, name : str) -> object :
        for conn in self.m_listConn :
            if conn.Name == name :
                return conn
        return None
    def find_conn_inx_by_node(self, conn : object) -> int :
        for inx, tmpConn in enumerate(self.m_listConn) :
            if tmpConn == conn :
                return inx
        return -1
    def remove_conn_by_id(self, id : int) -> object :
        conn = self.find_conn_by_id(id)
        if conn is None :
            return conn
        self.m_listConn.remove(conn)
        return conn
    def remove_conn_by_node(self, conn : object) :
        self.m_listConn.remove(conn)
    def clear_conn(self) :
        self.m_listConn.clear()


    @property
    def Active(self) -> bool :
        return self.m_active
    @Active.setter
    def Active(self, active : bool) :
        self.m_active = active
    @property
    def Name(self) -> str :
        return self.m_name
    @Name.setter
    def Name(self, name : str) :
        self.m_name = name
    @property
    def ID(self) -> int :
        return self.m_id
    @ID.setter
    def ID(self, id : int) :
        self.m_id = id
    @property
    def GraphID(self) -> int :
        return self.m_graphID
    @GraphID.setter
    def GraphID(self, graphID : int) :
        self.m_graphID = graphID
    @property
    def TreeID(self) -> int :
        return self.m_treeID
    @TreeID.setter
    def TreeID(self, treeID : int) :
        self.m_treeID = treeID
    @property
    def ListConn(self) :
        return self.m_listConn

class CSkeletonTreeNode :
    def __init__(self, id : int, node : CSkeletonNode) -> None:
        self.m_id = id
        self.m_node = node
        node.TreeID = id

        self.m_name = ""
        self.m_parent = None
        self.m_listChild = []
    def clear(self) :
        self.m_id = -1
        self.m_node.TreeID = -1
        self.m_node = None

        self.m_name = ""
        self.m_parent = None
        self.m_listChild.clear()

    def add_child(self, child) :
        child.Parent = self
        self.m_listChild.append(child)
    def get_child_count(self) -> int :
        return len(self.m_listChild)
    def get_child(self, inx : int) :
        return self.m_listChild[inx]
    def find_child(self, treeID : int) :
        for inx, treeNode in enumerate(self.ListChild) :
            if treeNode.ID == treeID :
                return inx
        return -1


    @property
    def Name(self) -> str :
        return self.m_name
    @Name.setter
    def Name(self, name : str) -> str :
        self.m_name = name
    @property
    def ID(self) -> int :
        return self.m_id
    @property
    def Node(self) -> CSkeletonNode :
        return self.m_node
    @property
    def Parent(self) :
        return self.m_parent
    @Parent.setter
    def Parent(self, parent) :
        self.m_parent = parent
    @property
    def ListChild(self) :
        return self.m_listChild


class CSkeletonBranch(CSkeletonNode) : 
    def __init__(self, id : int) -> None : 
        super().__init__(id)
        # input your code
        self.m_branchPoint = None
    def clear(self) :
        self.m_branchPoint = None
        #input your code
        super().clear()
    

    @property
    def BranchPoint(self) -> np.ndarray :
        return self.m_branchPoint
    @BranchPoint.setter
    def BranchPoint(self, branchPoint : np.ndarray) :
        self.m_branchPoint = branchPoint


class CSkeletonCenterline(CSkeletonNode) :
    def __init__(self, id : int) -> None:
        super().__init__(id)
        # input your code
        self.m_vertex = None
        self.m_radius = None
        self.add_conn(None)
        self.add_conn(None)
    def clear(self) :
        self.m_vertex = None
        self.m_radius = None
        #input your code
        super().clear()

    def get_vertex(self, inx : int) -> np.ndarray :
        return self.m_vertex[inx].reshape(-1, 3)
    def find_vertex_inx_by_vertex(self, vertex : np.ndarray) -> int :
        for inx, tmpVertex in enumerate(self.m_vertex) :
            if algLinearMath.CScoMath.is_equal_vec(tmpVertex, vertex) == True :
                return inx
        return -1
    def get_vertex_count(self) -> int :
        return self.m_vertex.shape[0]
    def get_radius(self, inx : int) -> np.ndarray :
        return self.m_radius[inx]
    def get_radius_by_branch_point(self, branchPoint : np.ndarray) :
        if algLinearMath.CScoMath.is_equal_vec(self.get_vertex(0), branchPoint) == True :
            return self.get_radius(0)
        elif algLinearMath.CScoMath.is_equal_vec(self.get_vertex(-1), branchPoint) == True :
            return self.get_radius(-1)
        else :
            print("not found radius of branch point")
    def get_conn_inx(self, vertex : np.ndarray) -> int :
        if algLinearMath.CScoMath.is_equal_vec(self.m_vertex[0], vertex) == True :
            return 0
        elif algLinearMath.CScoMath.is_equal_vec(self.m_vertex[-1], vertex) == True :
            return self.m_vertex.shape[0] - 1
        else :
            return -1
    def reverse(self) :
        self.m_vertex = self.m_vertex[ : : -1]
        self.m_radius = self.m_radius[ : : -1]
        self.m_listConn.reverse()
    def reverse_by_nn_vertex(self, nnVertex :np.ndarray) :
        npTmp = self.Vertex[0].reshape(-1, 3)
        npTmp = np.concatenate((npTmp, self.Vertex[-1].reshape(-1, 3)), axis=0)
        dist = np.linalg.norm(npTmp - nnVertex, axis=1)
        closestIndex = np.argmin(dist)
        if closestIndex != 0 :
            self.reverse()
    def is_leaf(self) -> bool:
        if self.get_conn(0) is None or self.get_conn(1) is None :
            return True
        return False
    def get_end_point(self) -> np.ndarray:
        if self.get_conn(0) is None :
            return self.get_vertex(0)
        elif self.get_conn(1) is None :
            return self.get_vertex(-1)
        else : 
            return None


    @property
    def Vertex(self) -> np.ndarray :
        return self.m_vertex
    @Vertex.setter
    def Vertex(self, vertex : np.ndarray) :
        self.m_vertex = vertex
    @property
    def Radius(self) -> np.ndarray :
        return self.m_radius
    @Radius.setter
    def Radius(self, radius : np.ndarray) :
        self.m_radius = radius


class CSkeleton :
    def __init__(self) -> None :
        self.m_topology = None
        self.m_listCenterline = []
        self.m_listBranch = []
        self.m_listLeafCenterline = []
        self.m_listGraph = []
        self.m_listTree = []
        self.m_graph = None
        self.m_kdTree = None
        self.m_listKDTreeAnchor = None
        self.m_listKDTreeAnchorID = []
        self.m_rootCenterline = None
    def clear(self) -> None :
        self.m_kdTree = None
        self.m_listKDTreeAnchor = None
        self.m_listKDTreeAnchorID.clear()
        if self.m_graph is not None :
            self.m_graph.clear()
            self.m_graph = None
        for treeNode in self.m_listTree :
            treeNode.clear()
        self.m_listTree.clear()

        for centerline in self.m_listCenterline :
            centerline.clear()
        for branch in self.m_listBranch :
            branch.clear()
        self.m_topology = None
        self.m_listCenterline.clear()
        self.m_listBranch.clear()
        self.m_listLeafCenterline.clear()
        self.m_listGraph.clear()
        self.m_rootCenterline = None


    def init_with_vtk_skel_info(self, vtkSkelInfo : list) :
        '''
        vtkSkelInfo : 
            [
                npTopology,
                [npVertex, npRadius],
                ..
            ]
        '''
        self.clear()
        self.m_topology = vtkSkelInfo[0]
        centerCnt = len(vtkSkelInfo) - 1

        # centerline 
        for i in range(0, centerCnt) : 
            centerline = CSkeletonCenterline(i)
            centerline.Vertex = vtkSkelInfo[1 + i][0]
            centerline.Radius = vtkSkelInfo[1 + i][1]
            self.m_listCenterline.append(centerline)
        # conn branch and centerline
        for centerline in self.ListCenterline :
            self.__init_conn_centerline(centerline)
        # leaf centerline
        self.extract_leaf_centerline()
        print("passed extracting centerline & branch")

        self.build_graph()
        self.build_kd_tree()
    def rebuild_centerline_related_data(self) :
        for centerline in self.ListCenterline :
            self.__init_conn_centerline(centerline)
        self.extract_leaf_centerline()
        self.build_graph()
        self.build_kd_tree()

        rootCenterlineID = -1
        if self.RootCenterline is not None :
            rootCenterlineID = self.RootCenterline.ID
        if rootCenterlineID >= self.get_centerline_count() :
            rootCenterlineID = -1
            self.RootCenterline = None
        if rootCenterlineID != -1 :
            self.build_tree(rootCenterlineID)


    def get_centerline_count(self) -> int :
        return len(self.m_listCenterline)
    def get_centerline(self, inx : int) -> CSkeletonCenterline :
        return self.m_listCenterline[inx]
    def get_branch_count(self) -> int :
        return len(self.m_listBranch)
    def get_branch(self, inx : int) -> CSkeletonBranch :
        return self.m_listBranch[inx]
    def get_leaf_centerline_count(self) -> int :
        return len(self.m_listLeafCenterline)
    def get_leaf_centerline(self, inx : int) -> CSkeletonCenterline :
        return self.m_listLeafCenterline[inx]
    def get_graph_count(self) -> int :
        return len(self.m_listGraph)
    def get_graph(self, inx : int) -> CSkeletonNode :
        return self.m_listGraph[inx]
    def transform(self, mat4 : np.ndarray) :
        for inx in range(0, self.get_centerline_count()) :
            skeletonCenterline = self.get_centerline(inx)
            outV = algLinearMath.CScoMath.mul_mat4_vec3(mat4, skeletonCenterline.Vertex)
            skeletonCenterline.Vertex = outV
        for inx in range(0, self.get_branch_count()) :
            skeletonBranch = self.get_branch(inx)
            branchPoint = skeletonBranch.BranchPoint
            outV = algLinearMath.CScoMath.mul_mat4_vec3(mat4, branchPoint)
            skeletonBranch.BranchPoint = outV
        self.build_kd_tree()

    def attach_branch_centerline(self, branch : CSkeletonBranch, centerline : CSkeletonCenterline) :
        # 이미 branch에 등록된 상황이므로 pass
        if branch.find_conn_inx_by_node(centerline) >= 0 :
            return
        connInx = centerline.get_conn_inx(branch.BranchPoint)
        if connInx < -1 :
            # 무언가 잘못 되었다. 
            return
        
        if connInx == 0 :
            centerline.set_conn(0, branch)
        else :
            centerline.set_conn(1, branch)
        branch.add_conn(centerline)
    def find_conn_centerline(self, vertex : np.ndarray) :
        retList = []
        for centerline in self.m_listCenterline :
            connInx = centerline.get_conn_inx(vertex)
            if connInx < 0 :
                continue
            retList.append(centerline)
        if len(retList) == 0 :
            return None
        return retList
    def save(self, jsonFullPath : str, name : str) :
        dic = {}

        dic["name"] = name
        if self.RootCenterline is None :
            dic["rootCenterlineID"] = -1
        else :
            dic["rootCenterlineID"] = self.RootCenterline.ID

        listCL = []
        iCLCnt = self.get_centerline_count()
        dic["centerline count"] = iCLCnt
        dic["endline count"] = self.get_leaf_centerline_count()

        listTree = []
        dic["tree"] = listTree
        if self.RootCenterline is not None :
            iCLCnt = self.get_centerline_count()
            for inx in range(0, iCLCnt) :
                dicCL = {}
                cl = self.get_centerline(inx)
                clID = cl.ID
                parentCLID, listChildCLID = self.get_conn_centerline_id(clID)
                dicCL["id"] = clID
                dicCL["parentID"] = parentCLID
                dicCL["childID"] = listChildCLID
                listTree.append(dicCL)

        dic["centerlineList"] = listCL
        for inx in range(0, iCLCnt) :
            dicCL = {}
            cl = self.get_centerline(inx)
            clID = cl.ID
            listVertex = cl.Vertex.tolist()
            listRadius = cl.Radius.tolist()
            dicCL["name"] = cl.Name
            dicCL["id"] = clID
            dicCL["length(mm)"] = float(algSpline.CCurveInfo.get_curve_len(cl.Vertex))
            dicCL["vertex"] = listVertex
            dicCL["radius"] = listRadius
            listCL.append(dicCL)

        with open(jsonFullPath, "w", encoding="utf-8") as fp:
            json.dump(dic, fp, ensure_ascii=False, indent=4)
    def load(self, jsonFullPath : str) -> str :
        '''
        return : name
        '''
        if os.path.exists(jsonFullPath) == False :
            print(f"not found {jsonFullPath}")
            return 
        
        dic = None
        with open(jsonFullPath, 'r') as fp :
            dic = json.load(fp)

        self.clear()
        self.m_topology = None
        
        name = dic["name"]
        rootCenterlineID = dic["rootCenterlineID"]
        listCL = dic["centerlineList"]
        for inx, dicCL in enumerate(listCL) :
            clID = dicCL["id"]
            name = dicCL["name"]
            npVertex = np.array(dicCL["vertex"], dtype=np.float32)
            npRadius = np.array(dicCL["radius"], dtype=np.float32)

            centerline = CSkeletonCenterline(inx)
            centerline.Name = name
            centerline.Vertex = npVertex
            centerline.Radius = npRadius
            self.m_listCenterline.append(centerline)
        
        # conn branch and centerline
        for centerline in self.ListCenterline :
            self.__init_conn_centerline(centerline)
        # leaf centerline
        self.extract_leaf_centerline()
        print("passed extracting centerline & branch")

        self.build_graph()
        self.build_kd_tree()
        if rootCenterlineID != -1 :
            self.build_tree(rootCenterlineID)

        return name
    
    def extract_leaf_centerline(self) :
        self.m_listLeafCenterline.clear()
        iCnt = self.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = self.get_centerline(inx)
            if cl.is_leaf() == True :
                self.m_listLeafCenterline.append(cl)
        

    # graph member
    def build_graph(self) :
        self.m_listGraph.clear()

        # graphID construction node
        self.m_graph = nx.Graph()
        for inx, centerline in enumerate(self.ListCenterline) :
            centerline.GraphID = inx
            self.m_listGraph.append(centerline)
            self.m_graph.add_node(centerline.GraphID)
        deltaInx = len(self.ListCenterline)
        for inx, branch in enumerate(self.ListBranch) :
            branch.GraphID = inx + deltaInx
            self.m_listGraph.append(branch)
            self.m_graph.add_node(branch.GraphID)
        # graph edge connection
        for branch in self.ListBranch :
            connCnt = branch.get_conn_count()
            for i in range(0, connCnt) :
                conn = branch.get_conn(i)
                self.m_graph.add_edge(branch.GraphID, conn.GraphID)    
        print("completed building Centerline Graph")
    def get_shortest_path(self, targetGraphID : int, sourceGraphID : int) -> list :
        path = None
        try :
            path = nx.shortest_path(self.m_graph, sourceGraphID, targetGraphID)
        except nx.NetworkXNoPath :
            print("no path")
        return path


    # tree member
    def build_tree(self, rootCenterlineID : int) :
        print("start building centerline tree")
        self.__clear_tree()

        self.m_rootCenterline = self.get_centerline(rootCenterlineID)
        rootCenterline = self.m_rootCenterline
        rootGraphID = rootCenterline.GraphID

        if len(self.m_listCenterline) == 1 :
            treeNode = self.__create_tree_node(rootCenterline)
        else :
            for centerline in self.m_listCenterline :
                if centerline == rootCenterline :
                    continue

                srcGraphID = centerline.GraphID
                graphNode = self.get_graph(srcGraphID)
                # 현재 node가 이미 tree로 구축된 상황이므로 건너뛴다. 
                if graphNode.TreeID >= 0 :
                    continue
                # path가 존재하지 않으므로 건너뛴다. 
                listPath = self.get_shortest_path(rootGraphID, srcGraphID)
                if listPath is None :
                    continue

                childTreeNode = None
                for path in listPath :
                    graphNode = self.get_graph(path)

                    # treeNode 생성 
                    treeNode = self.__get_tree_node(graphNode)
                    if treeNode is None :
                        treeNode = self.__create_tree_node(graphNode)

                    if childTreeNode is not None :
                        childInx = treeNode.find_child(childTreeNode.ID)
                        if childInx < 0 :
                            treeNode.add_child(childTreeNode)
                        else :
                            break
                    childTreeNode = treeNode
        print("completed building centerline tree")

        for centerline in self.m_listCenterline :
            self.__rearrange_centerline(centerline.ID)
        rootCL = self.RootCenterline
        if rootCL.get_conn(0) is not None and rootCL.get_conn(1) is None :
            rootCL.reverse()
        print("completed rearranging centerline")
    def get_tree_node(self, centerlineID : int) -> CSkeletonTreeNode :
        # not building tree 
        if len(self.m_listTree) == 0 :
            return None
        centerline = self.get_centerline(centerlineID)
        treeID = centerline.TreeID
        return self.m_listTree[treeID]
    def get_conn_centerline_id(self, centerlineID : int) -> tuple :
        '''
        ret : (parentID, listChildID[..])
        '''
        treeNode = self.get_tree_node(centerlineID)

        parentID = -1
        listChild = []

        if treeNode.Parent is not None :
            branchTreeNode = treeNode.Parent
            parentTreeNode = branchTreeNode.Parent
            parentID = parentTreeNode.Node.ID
        
        iChildCnt = treeNode.get_child_count()
        if iChildCnt == 0 :
            return (parentID, listChild)
        
        for i in range(0, iChildCnt) :
            branchTreeNode = treeNode.get_child(i)
            if branchTreeNode.Node.get_class_name() != "CSkeletonBranch" :
                print("무언가 잘못 되었다")
                continue
            else :
                jChildCnt = branchTreeNode.get_child_count()
                for j in range(0, jChildCnt) :
                    clTreeNode = branchTreeNode.get_child(j)
                    listChild.append(clTreeNode.Node.ID)
        return (parentID, listChild)
    def find_centerline_list_by_tree_depth(self, depth : int) -> list :
        # not building tree 
        if len(self.m_listTree) == 0 :
            return None

        retList = []
        for centerline in self.ListCenterline :
            treeID = centerline.TreeID
            treeNode = self.m_listTree[treeID]
            retDepth = self.__get_tree_node_centerline_depth(treeNode)
            if retDepth == depth :
                retList.append(centerline)

        if len(retList) == 0 :
            return None
        return retList
    def find_descendant_centerline_by_centerline_id(self, centerlineID : int) -> list :
        if len(self.m_listTree) == 0 :
            return None
        
        retList = []
        centerline = self.get_centerline(centerlineID)
        treeID = centerline.TreeID
        treeNode = self.m_listTree[treeID]

        listTreeNode = []
        listTreeNode.append(treeNode)
        for treeNode in listTreeNode :
            graphNode = treeNode.Node
            if graphNode.get_class_name() == "CSkeletonCenterline" :
                retList.append(graphNode)
            treeChildCnt = treeNode.get_child_count()
            for childInx in range(0, treeChildCnt) :
                treeNodeChild = treeNode.get_child(childInx)
                listTreeNode.append(treeNodeChild)
        
        if len(retList) == 0 :
            return None
        return retList
    def find_ancestor_centerline_by_centerline_id(self, centerlineID : int) -> list :
        if len(self.m_listTree) == 0 :
            return None
        
        retList = []
        centerline = self.get_centerline(centerlineID)
        treeID = centerline.TreeID
        treeNode = self.m_listTree[treeID]

        listTreeNode = []
        listTreeNode.append(treeNode)
        for treeNode in listTreeNode :
            graphNode = treeNode.Node
            if graphNode.get_class_name() == "CSkeletonCenterline" :
                retList.append(graphNode)
            treeNodeParent = treeNode.Parent
            if treeNodeParent is not None :
                listTreeNode.append(treeNodeParent)
        if len(retList) == 0 :
            return None
        return retList
    

    # kd-tree member
    def build_kd_tree(self) :
        if self.m_kdTree is not None :
            del self.m_kdTree
            gc.collect()

            self.m_kdTree = None
            self.m_listKDTreeAnchor = None
            self.m_listKDTreeAnchorID.clear()

        print("kd-tree build start")
        iCenterlineCnt = self.get_centerline_count()
        if iCenterlineCnt == 0 :
            print("not found centerline, failed building kd-tree")
            return 
        
        centerline = self.get_centerline(0)
        self.m_listKDTreeAnchor = np.copy(centerline.Vertex)
        self.m_listKDTreeAnchorID += [centerline.ID for i in range(0, centerline.Vertex.shape[0])]

        for centerlineInx in range(1, iCenterlineCnt) :
            centerline = self.get_centerline(centerlineInx)
            self.m_listKDTreeAnchor = np.concatenate((self.m_listKDTreeAnchor, centerline.Vertex), axis=0)
            self.m_listKDTreeAnchorID += [centerline.ID for i in range(0, centerline.Vertex.shape[0])]
        
        self.m_kdTree = KDTree(self.m_listKDTreeAnchor)
        print("kd-tree build completed")
    def find_nearest_centerline(self, vertex : np.ndarray) -> CSkeletonCenterline :
        distances, self.m_npNNIndex = self.m_kdTree.query(vertex, k=1)
        centerlineID = self.m_listKDTreeAnchorID[self.m_npNNIndex[0]]
        return self.get_centerline(centerlineID)


    # protected


    # private
    def __init_conn_centerline(self, centerline) :
        for inx in [0, -1] :
            branch = centerline.get_conn(inx)
            if branch is not None :
                continue

            vertex = centerline.get_vertex(inx)
            listNeighborCenterline = self.find_conn_centerline(vertex)
            if listNeighborCenterline is None :
                continue
            # 연결된 것이 자신밖에 없으므로 branch가 아니다. 
            if len(listNeighborCenterline) == 1 :
                continue

            branch = CSkeletonBranch(len(self.m_listBranch))
            branch.BranchPoint = vertex
            self.m_listBranch.append(branch)
            for neighborCenterline in listNeighborCenterline :
                self.attach_branch_centerline(branch, neighborCenterline)
    def __create_tree_node(self, skeletonNode : CSkeletonNode) :
        treeID = len(self.m_listTree)
        treeNode = CSkeletonTreeNode(treeID, skeletonNode)
        self.m_listTree.append(treeNode)
        return treeNode
    def __get_tree_node(self, skeletonNode : CSkeletonNode) :
        if skeletonNode.TreeID >= 0 :
            treeID = skeletonNode.TreeID
            return self.m_listTree[treeID]
        return None
    def __get_tree_node_centerline_depth(self, treeNode : CSkeletonTreeNode) :
        depthCnt = 0

        parent = treeNode.Parent 
        while parent is not None :
            graphNode = parent.Node
            if graphNode.get_class_name() == "CSkeletonCenterline" :
                depthCnt += 1
            parent = parent.Parent

        return depthCnt
    def __rearrange_centerline(self, centerlineID : int) :
        centerline = self.get_centerline(centerlineID)
        treeID = centerline.TreeID
        treeNode = self.m_listTree[treeID]

        treeNodeParent = treeNode.Parent
        if treeNodeParent is None :
            return
        else :
            branch = treeNodeParent.Node
            vertex = branch.BranchPoint
        inx = centerline.find_vertex_inx_by_vertex(vertex)
        if inx != 0 :
            centerline.reverse()
    def __clear_tree(self) :
        for treeNode in self.m_listTree :
            treeNode.clear()
        self.m_listTree.clear()
        self.m_rootCenterline = None
    

    @property
    def RootCenterline(self) -> CSkeletonCenterline :
        return self.m_rootCenterline
    @RootCenterline.setter
    def RootCenterline(self, centerline : CSkeletonCenterline) :
        self.m_rootCenterline = centerline
    @property
    def ListCenterline(self) -> list :
        return self.m_listCenterline
    @property
    def ListBranch(self) -> list :
        return self.m_listBranch
    @property
    def ListLeafCenterline(self) -> list : 
        return self.m_listLeafCenterline
    @property
    def ListGraph(self) -> list :
        return self.m_listGraph
    @property
    def KDTree(self) -> KDTree :
        return self.m_kdTree
    @property
    def KDTreeAnchorVertex(self) -> np.ndarray :
        return self.m_listKDTreeAnchor