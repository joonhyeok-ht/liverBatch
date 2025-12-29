# commandExtractingCLLink.py
# 25.11.10 
# DESC : extract 'Centerline & Vertex Link' 
#        for Colon, Vessel
#        (apply CPNode)

import sys
import os
import numpy as np
import vtk
import datetime as dt
import json
import time
from collections import OrderedDict
from scipy.spatial import KDTree

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileStatePath = os.path.dirname(fileAbsPath)
fileAppPath = os.path.dirname(fileStatePath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileStatePath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import AlgUtil.algVTK as algVTK
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import vtkObjGuideCL as vtkObjGuideCL
import data as data
import operation as operation


class CCPNode :
    def __init__(self, clid, cpid, cpid_all, is_last, is_br, pos) :
        self.m_IDAll = cpid_all     #all cp 에서의 인덱스
        self.m_CLID = clid          #소속 CL의 ID
        self.m_ID = cpid            #CL에서의 인덱스
        self.m_isLast = is_last     #마지막 cp인지의 여부
        self.m_isBr = is_br         #Br point인지의 여부
        self.m_backwards = []      #backwards CPNode object
        self.m_forwards = []        #forwards CPNode objects
        self.m_pos = pos            #cp의 좌표
    def clear(self) :
        self.m_IDAll = -1    
        self.m_CLID = -1     
        self.m_ID = -1  
        self.m_isLast = False 
        self.m_isBr = False   
        self.m_backwards.clear()
        self.m_forwards.clear() 
        self.m_pos = None     

    @property
    def CPIDAll(self) -> int: 
        return self.m_IDAll
    @property
    def CLID(self) -> int:
        return self.m_CLID
    @property
    def CPID(self) -> int:
        return self.m_ID    
    @property
    def IsLast(self) -> bool: 
        return self.m_isLast
    @property
    def IsBr(self) -> bool:
        return self.m_isBr    
    @property
    def Backwards(self) : 
        return self.m_backwards
    @property
    def Forwards(self) :
        return self.m_forwards
    @property
    def Vertex(self) -> np.ndarray: 
        return self.m_pos    

class CCPNodeAll :
    FIRST_CP_IDX = 0
    NO_MORE_NEXT_CP = 0
    MORE_NEXT_CP = 1
    NO_MORE_PREV_CP = 0
    MORE_PREV_CP = 1
    CL_NONE = -1
    CP_NONE = -1
    def __init__(self) :
        self.m_listCPNode = []
    def clear(self) :
        self.m_listCPNode.clear()
    def add_cp_node(self, clid, cpid, cpid_all, is_last, is_br, pos) -> CCPNode :
        cp_node = CCPNode(clid, cpid, cpid_all, is_last, is_br, pos)
        # 부모는 항상 0~1개, 자식은 0~n 개
        self.m_listCPNode.append(cp_node)
        return cp_node
    def check_all_idx(self) :
        # 실제 cpid_all 과 리스트의 인덱스가 같은지 비교. 같아야함.
        for idx, cpnode in enumerate(self.m_listCPNode) :
            if idx != cpnode.CPIDAll:
                CCommandExtractingCLLink.print_log(f"ERROR : listCPNode[{idx}].CPIDAll = {cpnode.CPIDAll} : Wrong ID")
    def set_backward(self, cpid_all, backward_clid, backward_cpid) :
        # find backwards cpnode
        backwardCPNode = self._get_cp_node_by_clid_cpid(backward_clid, backward_cpid)
        if backwardCPNode != None :                
            curr_cp_node = self.m_listCPNode[cpid_all]
            curr_cp_node.Backwards.append(backwardCPNode)
            # curr_cp_node.Backwards.Forwards.append(curr_cp_node) Backwards가 여러개인 경우가 있어서 외부에서 별도셋팅하도록 set_forward()를 만듬.
    def set_forward(self, cpid_all, forward_clid, forward_cpid) :
        forwardCPNode = self._get_cp_node_by_clid_cpid(forward_clid, forward_cpid)
        if forwardCPNode != None :
            curr_cp_node = self.m_listCPNode[cpid_all]
            curr_cp_node.Forwards.append(forwardCPNode)
    def get_backwards(self, cpid_all) -> list:
        curr_cp_node = self.m_listCPNode[cpid_all]
        return curr_cp_node.Backwards
    def get_forwards(self, cpid_all) -> list:
        curr_cp_node = self.m_listCPNode[cpid_all]
        return curr_cp_node.Forwards
    def _get_cp_node_by_clid_cpid(self, clid, cpid) -> CCPNode :
        for cpnode in self.m_listCPNode :
            if cpnode.CLID == clid and cpnode.CPID == cpid :
                return cpnode
        return None
    def _get_cp_node_by_cpid_all(self, cpid_all) -> CCPNode :
        ret_cp_node = None
        if len(self.m_listCPNode) > cpid_all :
            ret_cp_node = self.m_listCPNode[cpid_all]
        return ret_cp_node
    @property
    def ListCPNode(self) :
        return self.m_listCPNode

class CCommandExtractingCLLink :
    MODE_VESSEL = 1
    MODE_COLON = 2

    @staticmethod
    def print_log(*args, **kwargs):
        return
        # print(object,file=sys.__stdout__, flush=True)
        kwargs.setdefault("file", sys.__stdout__)  
        kwargs.setdefault("flush", True)           
        print(*args, **kwargs)

    def __init__(self, objName : str, skeleton : algSkeletonGraph.CSkeleton, clInPath : str, patientId : str):
        self.NEEDED_LINE_CNT = 4
        self.FIRST_GET_CNT = 14
        self.SPHERE_RADIUS = 10.0 # 10.0 for Vessel(default), 40.0 for Colon

        # Error-Code 
        self.NO_ERROR = 1
        self.ERROR_LESS_THAN_4 = 2

        self.m_patientID = patientId
        self.m_objName = objName
        self.m_clInPath = clInPath
        self.m_polyData = None
        self.m_skeleton = skeleton
        self.m_saveFullPath = ""
        
        self.m_mode = 0

        self.m_outJson = None
        self.m_listCenterline = []    
        self.m_cpNodeAllInst = None    
        self.m_cpNodeAllInstReady = False   
        
        self.progress_callback  = lambda x: x  # For ProgressBar
        self.is_interrupted = lambda: False    # For ProgressBar
    def clear(self) :
        self.m_polyData = None
        self.m_skeleton = None
    def init(self, saveFullPath : str, mode) -> bool:
        self.m_mode = mode
        self.m_saveFullPath = saveFullPath
        
        if mode == self.MODE_COLON :
            self.SPHERE_RADIUS = 40.0

        self.curr_sphere_radius = self.SPHERE_RADIUS
        
        clInFullPath = os.path.join(self.m_clInPath, f"{self.m_objName}.stl")
        if not os.path.exists(clInFullPath) :
            self.print_log(f"{clInFullPath} is not exist.")
            return False
        if self.m_skeleton == None :
            self.print_log(f"skeleton is None.")
            return False
        self.m_polyData = algVTK.CVTK.load_poly_data_stl(clInFullPath)
        
        self.init_json()
        return True
    
    def process(self) :
        self.progress_callback(1, "Save Centerline ...")
        polydata = self.m_polyData
        skeleton = self.m_skeleton
        
        vertex = self.get_vertices(polydata)
        self.m_outJson["Vertices"] = vertex.tolist()
        self.m_outJson["Hierarchy"], listCenterlineByDepth, brokenLoopCLList = self.get_hierarchy(skeleton, skeleton.RootCenterline.ID) #sally 

        listCenterline = []
        listClLabel = []
        for inx in range(0, skeleton.get_centerline_count()) :
            skeletonCenterline = skeleton.get_centerline(inx)
            listCenterline.append(skeletonCenterline)
            listClLabel.append(skeletonCenterline.Name)
        
        self.m_outJson["CenterlineLabels"] = listClLabel

        normal_generator = vtk.vtkPolyDataNormals()
        normal_generator.SetInputData(polydata)
        normal_generator.ComputePointNormalsOn()
        normal_generator.Update()

        polydata = normal_generator.GetOutput()
        polydata_normals = algVTK.CVTK.poly_data_get_normal(polydata)
        
        self.find_neighbors(vertex, polydata_normals, listCenterline, listCenterlineByDepth, brokenLoopCLList)  

        # save
        with open(self.m_saveFullPath, "w", encoding="utf-8") as fp:
            json.dump(self.m_outJson, fp, ensure_ascii=False, indent="\t")
            self.print_log(f"centerlinedata.json dump done.")
        self.progress_callback(100, "Save Centerline ...")  # For ProgressBar
        
        return True

    def init_json(self) :
        self.m_outJson = OrderedDict()
        self.m_outJson["Object"]={}
        self.m_outJson["Object"]["Name"] = self.m_objName
        self.m_outJson["Object"]["PatientID"] = self.m_patientID
        self.m_outJson["Object"]["Date"] = dt.datetime.now().strftime("%m%d_%H%M%S")
        self.m_outJson["Object"]["DESC"] = f"centerline data"        
        self.m_outJson["Vertices"] = []
        self.m_outJson["CenterlinePoints"] = []
        self.m_outJson["Centerlines"] = []
        self.m_outJson["Hierarchy"] = []
        self.m_outJson["Neighbors"] = []
        self.m_outJson["CenterlineLabels"] = [""]
        self.m_outJson["CenterlineRadius"] = []
        self.m_outJson["BrokenLoopCPIndex"] = []

    def check_outside_centerline_point(self, skeleton, polydata) :
        self.print_log(f"Check if the centerline points are inside the mesh ->")
        outside_list = []
        for cl_inx in range(0, skeleton.get_centerline_count()) :
            skeletonCenterline = skeleton.get_centerline(cl_inx)
            for index, vert in enumerate(skeletonCenterline.Vertex):
                pos = np.array([vert])
                if not self._is_point_inside_mesh(pos[0], polydata) :
                    self.print_log(f"cl_pos[{index}] (in cl[{cl_inx}]) is not in Mesh")
                    outside_list.append([cl_inx, index, vert])
        self.print_log(f"Check Done.")
        return outside_list
    def get_vertices(self, vesselPolyData : vtk.vtkPolyData) -> np.ndarray :
        npVertex = algVTK.CVTK.poly_data_get_vertex(vesselPolyData)
        return npVertex
    def get_hierarchy(self, skeleton : algSkeletonGraph.CSkeleton, rootCenterlineID : int) :
        #TODO : 원본코드에서 _render_centerline_by_depth_sally_stl() 함수임.
        skeleton.build_tree(rootCenterlineID)
        stopFlag = True
        depth = 0
        
        hierarchy_list = []
        listCenterlineByDepth = []
        broken_loop_cl_list = []  # cl.ID
        while(stopFlag==True) :
            retListCenterline = skeleton.find_centerline_list_by_tree_depth(depth)
            if retListCenterline is not None :
                listCenterlineByDepth.append(retListCenterline) # 250611

                for cl in retListCenterline :
                    hierarchy = skeleton.get_conn_centerline_id(cl.ID)                    
                    if hierarchy[0] < 0 :
                        continue
                    if len(hierarchy[1]) == 0 : 
                        if cl.is_leaf() == False :
                            self.print_log(f"[]Info]Broken Loop Centerline(in Tree) : CL {cl.ID}")
                            broken_loop_cl_list.append(cl.ID)  #뒷단에서 이 cl의 마지막 cp를 끊어진cl리스트에 등록하게 됨.
                    hierarchy_list.append([hierarchy[0], cl.ID])
            else :
                self.print_log(f"not found centerline in depth. Stop. depth = {depth}")
                stopFlag = False
            depth = depth + 1
        return hierarchy_list, listCenterlineByDepth, broken_loop_cl_list
    def find_neighbors(self, polyVertex : np.ndarray, polyNormal : np.ndarray, listCenterline : list, listCenterlineByDepth : list, listBrokenLoopCL : list):
                
        retCenterlineVertCnt = []
        retCenterlineVert = []
        retCenterlineRadius = []
        centerlineSegInx = []
        brokenLoopCLCPIdxList = []
        brokenLoopCLCPIdxAllList = []
		# listCenterline = [] # root cl부터 계층에 따라 cl들을 저장. 기존 listCenterline은 ID 0부터 차례로 저장되어 있었음.
        dicCLIDAndLevel = {}
        for level, same_level_centerlines in enumerate(listCenterlineByDepth):
            for centerline in same_level_centerlines :
                # listCenterline.append(centerline)
                dicCLIDAndLevel[centerline.ID] = level
 
        self.print_log(f"Centerline Count : {len(listCenterline)}")
        ## 모든 centerline의 점을 하나의 리스트로 모으기.
        vertCntSum = 0
        centerline_line_info_all = []
        if self.m_cpNodeAllInst == None :
            self.m_cpNodeAllInst = CCPNodeAll()
        for inx, centerline in enumerate(listCenterline) :
            vertexCnt = centerline.get_vertex_count()
            vertex = centerline.Vertex
            radius = centerline.Radius
            
            ##Centerline 의 모든 CP에 대해 노드를 생성하고, 하나의 리스트에 모두 저장
            if self.m_cpNodeAllInst and self.m_cpNodeAllInstReady == False:
                is_leaf = centerline.is_leaf()
                for cpidx, cp in enumerate(vertex) :
                    ## CPNode 생성
                    is_last_cp = False
                    if cpidx == len(vertex)-1 :
                        is_last_cp = True
                        if centerline.ID in listBrokenLoopCL :
                            brokenLoopCLCPIdxList.append([centerline.ID, cpidx])
                    is_br = False
                    if is_last_cp and not is_leaf :
                        is_br = True
                    cpid_all = cpidx + vertCntSum    
                    
                    self.m_cpNodeAllInst.add_cp_node(centerline.ID, cpidx, cpid_all, is_last_cp, is_br, cp)

            retCenterlineVertCnt.append(vertexCnt)
            retCenterlineVert.append(vertex)
            retCenterlineRadius.append(radius)
            centerlineSegInx += [inx for i in range(0, len(vertex))]

            ## 한 centerline 안의 cell(작은라인들)정보를 저장
            centerline_line_info_sub = [] 
            line_strip_index = algVTK.CVTK.make_line_strip_index(vertexCnt)
            ## 개별 centerline의 cp기준이 아닌 '전체 cp의개수'를 기준으로 인덱스를 생성함.
            for idx in line_strip_index: 
                idx[0] = idx[0] + vertCntSum
                idx[1] = idx[1] + vertCntSum
                centerline_line_info_sub.append(idx.tolist())
            centerline_line_info_all.append(centerline_line_info_sub)    
            vertCntSum = vertCntSum + vertexCnt #jys

        ## 각 cp의 index 값 검사
        self.m_cpNodeAllInst.check_all_idx()
        if self.m_cpNodeAllInst and self.m_cpNodeAllInstReady == False:
            ## 각 cp에 연결된 cp를 설정한다.(previous(==backward), next(==forward) 를 설정함)
            self.m_cpNodeAllInst = self.__set_pre_next_of_cp(listCenterline, self.m_cpNodeAllInst, dicCLIDAndLevel)
            self.m_cpNodeAllInstReady = True

        ## 트리구조상 끊어진 Loop지점의 점 인덱스를  얻어오기        
        for clcp in brokenLoopCLCPIdxList :
            cpnode = self.m_cpNodeAllInst._get_cp_node_by_clid_cpid(clcp[0], clcp[1])
            brokenLoopCLCPIdxAllList.append([clcp[0], cpnode.CPIDAll])
        brokenLoopCpIdxList = []
        if len(brokenLoopCLCPIdxAllList) > 0 :
            brokenLoopCpIdxList = [row[1] for row in brokenLoopCLCPIdxAllList]
            
        self.print_log(f"brokenLoopCLCPIdxList : {brokenLoopCLCPIdxList}")    
        self.print_log(f"brokenLoopCLCPIdxAllList : {brokenLoopCLCPIdxAllList}") 

        ## CP들을 하나로 모으기
        npCenterlinePoints = np.concatenate(retCenterlineVert, axis=0)
        npCenterlineRadius = np.concatenate(retCenterlineRadius, axis=0)

        self.m_outJson["CenterlinePoints"] = npCenterlinePoints.tolist()
        self.m_outJson["CenterlineRadius"] = npCenterlineRadius.tolist()
        self.m_outJson["Centerlines"] = centerline_line_info_all
        self.m_outJson["BrokenLoopCPIndex"] = brokenLoopCpIdxList
        
        self.print_log("Number of Centerline Points : ", len(npCenterlinePoints))

        self.print_log("kd-tree build start")
        tree = KDTree(npCenterlinePoints)
        #<---------------------------------colon,vessel 공통코드
        if self.m_mode == self.MODE_COLON :
            #colon 코드
            self._find_neighbors_colon(tree, polyVertex, npCenterlinePoints, centerline_line_info_all, polyNormal)
        elif self.m_mode == self.MODE_VESSEL :
            #vessel 코드
            self._find_neighbors_vessel(tree, polyVertex, npCenterlinePoints, centerline_line_info_all)

        self.m_outJson["Object"]["NumVertices"] = len(polyVertex)
        self.m_outJson["Object"]["CntCenterlines"] = len(listCenterline)
        self.print_log(f"end of __find_neighbors()")
        return True

    def _find_neighbors_colon(self, tree:KDTree, polyVertex:np.ndarray, npCenterlinePoints:np.ndarray, centerline_line_info_all:list, polyNormal : np.ndarray) -> bool:
        neighbors_info_list = []
        
        for vertidx, vert in enumerate(polyVertex):
            if self.is_interrupted(): # For ProgressBar
                return False
            
            self.CURR_SPHERE_POSITION = np.array([vert])
            
            neighbor_cp_idx_list = self.__find_near_centerline_points2_modi3_fast(tree, npCenterlinePoints, vert, vertidx, polyNormal[vertidx], self.m_cpNodeAllInst)
            try_no = 1
            neighbor_line_info, neighbor_points_ordered, errors = self.__get_near_lines4_fast(vert, neighbor_cp_idx_list, npCenterlinePoints, centerline_line_info_all, try_no) #25.11.04
 
            if errors == self.ERROR_LESS_THAN_4:  
                self.print_log(f"ERROR_LESS_THAN_4 : Try again vertidx:{vertidx}")
                neighbor_cp_idx_list = self.__find_near_centerline_points3(npCenterlinePoints, vert, vertidx, self.m_cpNodeAllInst)
                neighbor_line_info, neighbor_points_ordered, errors = self.__get_near_lines4_fast(vert, neighbor_cp_idx_list, npCenterlinePoints, centerline_line_info_all, try_no) #25.11.04
                if errors == self.ERROR_LESS_THAN_4:
                    self.print_log(f"FINAL-ERROR vertidx:{vertidx}")
                    with open("error_log.txt", "a", encoding="utf-8") as fp:
                        fp.writelines(f"({dt.datetime})-rel ERROR_LESS_THAN_4 vertidx = {vertidx}")
                    continue
                
            ln_idx = []
            weights = []
            for idx in range(0, self.NEEDED_LINE_CNT) :
                cl_id = neighbor_line_info[idx]["CenterlineID"]
                cell_id = neighbor_line_info[idx]["LineID"]
                ln_idx.append([cl_id,cell_id])
                weights.append(neighbor_line_info[idx]["Weight"])
            
            neighbors_info_list.append({"LnIdx":ln_idx, "Weight":weights})
            # For ProgressBar
            self.progress_callback(1 + int(vertidx / len(polyVertex) * 98), "Save Centerline ...")


        self.print_log(f"num of neighbors_info_list = {len(neighbors_info_list)}")  
        self.print_log(f"num of vertex = {len(polyVertex)}") 
        self.m_outJson["Neighbors"] = neighbors_info_list
        # return npCenterlinePoints, ret_neighbor_points, ret_neighbor_line_info
        return True
    def _find_neighbors_vessel(self, tree:KDTree, polyVertex:np.ndarray, npCenterlinePoints:np.ndarray, centerline_line_info_all:list) -> bool:
        neighbors_info_list = []
        
        for vertidx, vert in enumerate(polyVertex):
            if self.is_interrupted():
                return False
            
            # self.print_log(f"VertIdx : [{vertidx}]")
            self.CURR_SPHERE_POSITION = np.array([vert])
            neighbor_cp_idx_list = self.__find_near_centerline_points5(tree, npCenterlinePoints, vert, self.m_cpNodeAllInst)
            try_no = 1
            neighbor_line_info, neighbor_points_ordered, errors = self.__get_near_lines4_fast(vert, neighbor_cp_idx_list, npCenterlinePoints, centerline_line_info_all, try_no)
            if errors == self.ERROR_LESS_THAN_4:  
                    self.print_log(f"FINAL-ERROR : vertidx:{vertidx}")
                    with open("error_log.txt", "a", encoding="utf-8") as fp:
                        fp.writelines(f"({dt.datetime})-rel ERROR_LESS_THAN_4 vertidx = {vertidx}")
                    continue   
                    
            ln_idx = []
            weights = []
            for idx in range(0, self.NEEDED_LINE_CNT) :
                cl_id = neighbor_line_info[idx]["CenterlineID"]
                cell_id = neighbor_line_info[idx]["LineID"]
                ln_idx.append([cl_id,cell_id])
                weights.append(neighbor_line_info[idx]["Weight"])
            
            neighbors_info_list.append({"LnIdx":ln_idx, "Weight":weights})
            # For ProgressBar
            self.progress_callback(1 + int(vertidx / len(polyVertex) * 98), "Save Centerline ...")

        self.print_log(f"num of neighbors_info_list = {len(neighbors_info_list)}")  
        self.print_log(f"num of vertex = {len(polyVertex)}") 
        self.m_outJson["Neighbors"] = neighbors_info_list
        return True
    def __check_time(self) :
        # pass
        return time.time()
    def _is_point_inside_mesh(self, point, polydata) -> bool:
        # 포인트를 vtkPoints 객체로 변환
        points = vtk.vtkPoints()
        points.InsertNextPoint(point)
        
        # 포인트를 vtkPolyData 객체로 변환
        point_polydata = vtk.vtkPolyData()
        point_polydata.SetPoints(points)
        
        # 포인트를 메쉬와 비교
        select_enclosed_points = vtk.vtkSelectEnclosedPoints()
        select_enclosed_points.SetInputData(point_polydata)
        select_enclosed_points.SetSurfaceData(polydata)
        select_enclosed_points.Update()
        
        # 포인트가 메쉬 내부에 있는지 확인
        return select_enclosed_points.IsInside(0)
    

    def __set_pre_next_of_cp(self, listCenterline, cpNodeAllInst : CCPNodeAll, dicCLIDAndLevel) :
        vertCntSum = 0
        for inx, centerline in enumerate(listCenterline) :
            vertexCnt = centerline.get_vertex_count()
            vertex = centerline.Vertex
            for cpidx, cp in enumerate(vertex) :
                cpid_all = cpidx + vertCntSum    
                ## CPNode의 backwards 셋팅
                if cpidx == 0 : # CL의 첫번째 CP 인 경우(Br이거나 아니거나)
                    startBrOfCL = centerline.ListConn[0]
                    if startBrOfCL != None : # CP가 Branch-Point 인 경우 (None이면 root의 첫cp임)
                        for conned_cl in startBrOfCL.ListConn :
                            if conned_cl.ID != centerline.ID : # 자기자신은 제외.
                                #parent뿐만 아니라 같은 레벨의 형제 CL의 첫CP도 추가하기 위해 조건을 나눔.
                                if dicCLIDAndLevel[conned_cl.ID] < dicCLIDAndLevel[centerline.ID] : #부모 CL
                                    cpNodeAllInst.set_backward(cpid_all, conned_cl.ID, conned_cl.get_vertex_count()-1) 
                                else : # 형제 cl
                                    cpNodeAllInst.set_backward(cpid_all, conned_cl.ID, 0) 
                else : # 첫번째 CP가 아닌 경우임(lastcp & Br, lastcp & end-point 포함): 직전 CP를 backwards로 셋팅
                    cpNodeAllInst.set_backward(cpid_all, centerline.ID, cpidx - 1)
                    
                ## CPNode의 forwards 셋팅
                if cpidx == (vertexCnt - 1) : # last cp & Br , last cp & end-point
                    endBrOfCL = centerline.ListConn[1]
                    if endBrOfCL != None : # last cp & Br (not end-point)
                        for conned_cl in endBrOfCL.ListConn : 
                            if conned_cl.ID != centerline.ID :  # 자기자신은 제외
                                cpNodeAllInst.set_forward(cpid_all, conned_cl.ID, 0)
                else : # br도 아니고, end-point도 아니면, 다음 CP를 forward로 셋팅
                    cpNodeAllInst.set_forward(cpid_all, centerline.ID, cpidx + 1)
            vertCntSum = vertCntSum + vertexCnt #jys    
        return cpNodeAllInst       
    def __find_near_centerline_points2_modi3_fast(self, tree : KDTree, cl_all : list, cp_all : np.ndarray,
                                                radius_all : np.ndarray, target_vertex, vertidx,
                                                vertex_normal, cpNodeAllInst : 'CCPNodeAll') :    
        """
        High-performance replacement of __find_near_centerline_points2_modi3.
        Assumptions:
        - cp_all is numpy array shape (M,3)
        - tree is KDTree built on cp_all
        - firstGetCPCount exists as self.firstGetCPCount (k for KDTree.query)
        - self.SPHERE_RADIUS exists
        Returns: ret_cp_idx_list (same as original)
        """

        # ensure numpy types
        cp_all_np = np.asarray(cp_all, dtype=float)
        tv = np.asarray(target_vertex, dtype=float)
        vn = np.asarray(vertex_normal, dtype=float)

        ret_cp_idx_list = []

        # 1) KDTree initial nearest neighbor query (fast)
        k = int(getattr(self, "firstGetCPCount", 14))
        # handle case where tree.query returns scalars for k=1
        distances, neighbor_idx = tree.query(tv, k=k)
        # neighbor_idx can be scalar or array; make it numpy array
        if np.isscalar(neighbor_idx):
            neighbor_idx_arr = np.array([int(neighbor_idx)], dtype=int)
        else:
            neighbor_idx_arr = np.asarray(neighbor_idx, dtype=int)
            # sometimes tree.query returns padded indices if less points than k; remove invalid ones
            neighbor_idx_arr = neighbor_idx_arr[neighbor_idx_arr >= 0]

        # 2) dot filtering using vectorized helper (angle1 = -0.45 per original for the main case)
        newpos_dict, cp_idx_list, newpos_list = self.__check_neighbors_vec(cp_all_np, neighbor_idx_arr, tv, vn, angle1=-0.45, angle2=-1.0)

        # 3.1 if we have candidates -> find nearest among them and expand using cpNodeAllInst
        if len(cp_idx_list) > 0:
            # use the original helper that expands around nearest cp (we assume it expects lists)
            ret_cp_idx_list = self.__find_near_points_sub_case1(neighbor_idx.tolist() if isinstance(neighbor_idx, (list, np.ndarray)) else [int(neighbor_idx)],
                                                            cp_idx_list, cp_all, cpNodeAllInst)
            return ret_cp_idx_list

        # 3.2 If no dot-filtered candidates, do sphere expansion — but vectorized & cached distances
        # Precompute all distances once (vectorized)
        # NOTE: cp_all_np shape (M,3); computing d_all only once per call
        d_all = np.linalg.norm(cp_all_np - tv, axis=1)  # (M,)

        radius_value = float(self.SPHERE_RADIUS)
        trycnt = 0
        input_cp_idx = []

        # We will expand radius up to 5 times (same behavior). Each iteration uses d_all to pick indices.
        while True:
            # vectorized selection of indices inside sphere
            inside_indices = np.nonzero(d_all < radius_value)[0]  # numpy indices array
            print(f"inside_indeces : {inside_indices}")
            if inside_indices.size > 0:
                # do vectorized dot-filtering with tighter angle threshold used in original (-0.7)
                newpos_dict, cp_idx_list, newpos_list = self.__check_neighbors_vec(cp_all_np, inside_indices, tv, vn, angle1=-0.7, angle2=-1.0)
                print(f"cp_idx_list : {cp_idx_list}")
                
                if len(cp_idx_list) > 0:
                    input_cp_idx = inside_indices.tolist()
                    print(f"input_cp_idx : {input_cp_idx}")
                    break
                else:
                    # if no cp_idx_list found but we have inside points, clear and either retry or expand radius
                    if trycnt >= 5:
                        # leave input_cp_idx empty — will fall through to sphere KD fallback
                        input_cp_idx = []
                        break
                    else:
                        # increment try counter and expand
                        trycnt += 1
                        radius_value += 10.0
                        continue
            else:
                # no points in sphere
                trycnt += 1
                if trycnt > 5:
                    break
                radius_value += 10.0
                continue

        # store curr_sphere_radius like original
        self.curr_sphere_radius = radius_value

        # After expansion:
        if len(cp_idx_list) > 0:
            # Case [1]-1: we have dot-filtered interior CPs, expand to neighbors
            ret_cp_idx_list = self.__find_near_points_sub_case2(tv, cp_idx_list, cp_all, cpNodeAllInst)
            return ret_cp_idx_list
        else:
            # Case [1]-2: no dot-filtered CPs; fallback — build KDTree on CPs inside sphere (but cp_in_sphere likely small)
            # If input_cp_idx is empty -> no points in expanded sphere -> try global KDTree as fallback
            if len(input_cp_idx) == 0:
                # fallback: query tree globally for k nearest (use slightly larger k to be safe)
                fallback_k = min( max( self.firstGetCPCount * 2, 20 ), cp_all_np.shape[0] )
                new_distances, new_indices = tree.query(tv, k=fallback_k)
                # sanitize indices
                if np.isscalar(new_indices):
                    result_indices = [int(new_indices)]
                else:
                    new_indices_arr = np.asarray(new_indices, dtype=int)
                    result_indices = [int(x) for x in new_indices_arr if x >= 0]
            else:
                # build small KDTree on inside points
                cp_in_sphere_pts = cp_all_np[input_cp_idx]
                if cp_in_sphere_pts.shape[0] == 0:
                    result_indices = []
                else:
                    tree_for_sphere = KDTree(cp_in_sphere_pts)
                    qk = min(self.firstGetCPCount, cp_in_sphere_pts.shape[0])
                    new_distances, new_indices_local = tree_for_sphere.query(tv, k=qk)
                    # convert local indices to global
                    if np.isscalar(new_indices_local):
                        local_idxs = [int(new_indices_local)]
                    else:
                        local_idxs = [int(x) for x in new_indices_local if x < cp_in_sphere_pts.shape[0]]
                    result_indices = [ input_cp_idx[li] for li in local_idxs ]

            # transform result_indices to cp_all global indices and call sub_case4
            if len(result_indices) == 0:
                # nothing found even by fallback
                return []
            else:
                # result_indices are global cp indices (or converted to so); call original helper
                ret_cp_idx_list = self.__find_near_points_sub_case4(result_indices, cp_all, cpNodeAllInst)
                return ret_cp_idx_list
    def __find_near_centerline_points3(self, cp_all : np.ndarray, target_vertex, vertidx, cpNodeAllInst) :    
        ret_cp_idx_list = []
        ## Sphere범위 내에서 이웃점을 가져오기        
        self.print_log(f"===========> Case [1]  vert_idx: {vertidx}")        
        input_cp_idx = []
        radius_value = self.SPHERE_RADIUS
        while(True) : # radius 초기값 범위에서 내부에 포함되는 cp가 없는 경우 radius를 늘려가며 내부에 cp가 들어올때까지 수행.
            pos_target = np.array([target_vertex])
            spherePolyData = algVTK.CVTK.create_poly_data_sphere(pos_target, radius_value)
            for inx, clpos in enumerate(cp_all):
                if self._is_point_inside_mesh(clpos, spherePolyData) == True:
                    input_cp_idx.append(inx)
            if len(input_cp_idx) > 0 :
                self.print_log(f"latest Sphere Radius = {radius_value}")
                break
            radius_value = radius_value + 10.0

        cp_in_sphere = []
        for idx in input_cp_idx : #input_cp_idx = 스피어 내부의 cp들의 인덱스
            clpos = np.array(cp_all[idx].tolist())
            cp_in_sphere.append(clpos)
        
        ## sphere 내부 점들 중 target vertex와 가까운 점들 찾기
        tree_for_sphere = KDTree(cp_in_sphere)
        new_distances, new_indices = tree_for_sphere.query(target_vertex, k=self.FIRST_GET_CNT)
        
        self.print_log(f"===========> Case [1]-2  vert_idx: {vertidx}")
        self.print_log(f"스피어내부점 인덱스 input_cp_idx = {input_cp_idx}")
        self.print_log(f"최단거리점들 인덱스 tree_for_sphere_query result : indices {new_indices}")
        ## new_indices는 실제cp의 인덱스가 아니므로 변환을 해줘야함.(아래)
        result_indices = []
        for idx in new_indices:
            result_indices.append(input_cp_idx[idx])
        self.print_log(f"근접점리스트 결과 : {result_indices}")
        
        ## 최근접점을 설정하고 주변 12개의 점들 가져오기
        ret_cp_idx_list = self.__find_near_points_sub_case4(result_indices, cp_all, cpNodeAllInst)
        return ret_cp_idx_list    
    def __find_near_centerline_points5(self, tree : KDTree, cp_all : np.ndarray, target_vertex, cpNodeAllInst : CCPNodeAll) :    
        ## 1. 이웃점들 찾기(거리순)
        distances, neighbor_idx = tree.query(target_vertex, k=self.FIRST_GET_CNT)
    
        ## 최근접점 설정 (neighbor_idx는 최소거리부터 들어 있으므로 최근접점 인덱스는 0임)
        nearest_pos_idx = neighbor_idx[0]   #sally : __find_near_points_sub_case3 코드에서 이부분만 수정함. 버그였음.

        neighbor_cpid_list_next = []
        base_cpid_list = []
        nearest_cp_node = cpNodeAllInst._get_cp_node_by_cpid_all(nearest_pos_idx)
        
        if nearest_cp_node.IsLast == False : # 최근접 cp의 forward cp 와 라인을 형성하는데 있어서, LastCp인 경우 좌표가 같은 Br이나, 다음점이 없는 end-point인 경우이므로 최근점이라 할지라도 neighbor list에서 제외한다. __get_next()에서도 해당 내용 적용됨.
            neighbor_cpid_list_next.append(nearest_pos_idx)
        base_cpid_list.append(nearest_pos_idx)
        status = CCPNodeAll.MORE_NEXT_CP
        while(len(neighbor_cpid_list_next) < 6 and status != CCPNodeAll.NO_MORE_NEXT_CP) :
            base_cpid_list, neighbor_cpid_list_next, status = self.__get_next(cpNodeAllInst, base_cpid_list, neighbor_cpid_list_next)
        
        neighbor_cpid_list_prev = []
        base_cpid_list = []
        base_cpid_list.append(nearest_pos_idx)
        status = CCPNodeAll.MORE_PREV_CP
        while(len(neighbor_cpid_list_prev) < 6 and status != CCPNodeAll.NO_MORE_PREV_CP) :
            base_cpid_list, neighbor_cpid_list_prev, status = self.__get_prev(cpNodeAllInst, base_cpid_list, neighbor_cpid_list_prev)

        # self.print_log(f"neighbor_cpid_list_next[] = {neighbor_cpid_list_next}")
        # self.print_log(f"neighbor_cpid_list_prev[] = {neighbor_cpid_list_prev}")
        # self.print_log(f"최근접 CP Index : {nearest_pos_idx}")
        # endpoint인경우 backward최소 5개 필요 중간에br만나는 경우 고려
        # br인경우 중복제외 주변 점 가져오기
        # 모든 방향에서 br만나는 경우 고려해야함.
        merged_neighbor_list = list(set(neighbor_cpid_list_next + neighbor_cpid_list_prev))
        # self.print_log(f"merged_neighbor_list[] = {merged_neighbor_list}")
        return merged_neighbor_list
    def __get_prev(self, cp_node_all_inst, base_cpid_list, neighbor_cpid_list) :
        new_base_cpid_list = []
        for base_cpid in base_cpid_list :
            next_cp_nodes = cp_node_all_inst.get_backwards(base_cpid)
            for next_cp_node in next_cp_nodes :
                new_base_cpid_list.append(next_cp_node.CPIDAll)
                if not next_cp_node.IsLast:
                    neighbor_cpid_list.append(next_cp_node.CPIDAll)
        if len(new_base_cpid_list) == 0 :
            return new_base_cpid_list, neighbor_cpid_list, CCPNodeAll.NO_MORE_PREV_CP
        return new_base_cpid_list, neighbor_cpid_list, CCPNodeAll.MORE_PREV_CP
    def __get_next(self, cp_node_all_inst, base_cpid_list, neighbor_cpid_list) :        
        new_base_cpid_list = []
        for base_cpid in base_cpid_list :
            next_cp_nodes = cp_node_all_inst.get_forwards(base_cpid)
            for next_cp_node in next_cp_nodes :
                new_base_cpid_list.append(next_cp_node.CPIDAll)
                if not next_cp_node.IsLast: # 마지막점이면 br인경우 같은좌표의 다른cp와 라인을 생성하는데 이건 의미가 없으므로 제외시킨다. end-point인 경우에도 
                    neighbor_cpid_list.append(next_cp_node.CPIDAll)
        if len(new_base_cpid_list) == 0 :
            return new_base_cpid_list, neighbor_cpid_list, CCPNodeAll.NO_MORE_NEXT_CP
        return new_base_cpid_list, neighbor_cpid_list, CCPNodeAll.MORE_NEXT_CP
    def __check_neighbors_vec(self, cp_all_np: np.ndarray, neighbor_idx_arr: np.ndarray,
                          target_vertex: np.ndarray, vertex_normal: np.ndarray,
                          angle1=-0.5, angle2=-1.0):
        ## __check_neighbors_fast()보다 더 빠름
        """
        Vectorized replacement for __check_neighbors
        - cp_all_np: (M,3) numpy array
        - neighbor_idx_arr: 1D numpy array of indices
        - target_vertex: (3,) array
        - vertex_normal: (3,) array
        Returns: newpos_dict, cp_idx_list, newpos_list  (same semantics as original)
        """
        if neighbor_idx_arr.size == 0:
            return {}, [], []

        # slice candidate coordinates (N,3)
        pts = cp_all_np[neighbor_idx_arr]                   # (N,3)

        # vectors from target to cp
        vecs = pts - target_vertex                          # (N,3)
        dists = np.linalg.norm(vecs, axis=1)                # (N,)
        # avoid division by zero for exact same point
        zero_mask = dists == 0
        if np.any(zero_mask):
            # For zero-distance, set normalized vector to vertex_normal * -1 to make dot small (choose as 'use')
            dists[zero_mask] = 1e-12
        vecs_norm = vecs / dists[:, None]                   # (N,3)

        # dot with vertex normal (vectorized)
        dots = np.dot(vecs_norm, vertex_normal)             # (N,)

        # mask by angle thresholds
        mask = (dots < angle1) & (dots >= angle2)

        if not np.any(mask):
            return {}, [], []

        filtered_idx = neighbor_idx_arr[mask]               # indices (k,)
        filtered_dots = dots[mask]
        filtered_pts = pts[mask]

        # sort by dot ascending (same as original: smaller dot first)
        order = np.argsort(filtered_dots)
        filtered_idx = filtered_idx[order]
        filtered_dots = filtered_dots[order]
        filtered_pts = filtered_pts[order]

        newpos_dict = {int(filtered_idx[i]): tuple(filtered_pts[i].tolist()) for i in range(filtered_idx.size)}
        cp_idx_list = [int(x) for x in filtered_idx.tolist()]
        newpos_list = [[int(filtered_idx[i]), float(filtered_dots[i]), filtered_pts[i].tolist()] for i in range(filtered_idx.size)]

        return newpos_dict, cp_idx_list, newpos_list
    def __find_near_points_sub_case1(self, neighbor_idx, cp_idx_list, cp_all, cpNodeAllInst : CCPNodeAll) :
        ret_cp_idx_list = []    
        ## 최근접점 찾기 (neighbor_idx는 최소거리부터 들어 있으므로 cp_idx_list와 교차되는 첫 점이 최근접점이 됨)
        nearest_pos_idx = -1
        for n_idx in neighbor_idx:
            if n_idx in cp_idx_list :
                nearest_pos_idx = n_idx
                break
        ## 최근접점(KDTree결과와순차비교)이 있으면 전후로 12개데이터 가져오기
        if nearest_pos_idx != -1:
            ret_cp_idx_list = self.__get_near_12_cps_with_nearest_cp(nearest_pos_idx, cpNodeAllInst)
        else : # sphere범위내의 적정 dot값을 가지고 점들이지만 KDTree와는 겹치지 않는 점들인 경우임. cp_idx_list 내에서 가장 근거리점을 하나 찾고 주변 6개점을 가져오기
            # __find_near_points_sub_case2()에서 구현하기로 함. 그러므로 여기 도달하면 안됨.
            self.print_log(f"----------------->CRITICAL-ERROR 1: Not implemented Case. Check the logic~!!!")
        return ret_cp_idx_list
    def __get_near_12_cps_with_nearest_cp(self, nearestCPIdx,  cpNodeAllInst : CCPNodeAll) :
        ## 입력된 최근접점을 기준으로 전후 12개의 이웃 cp들을 가져온다. (__find_near_centerline_points5 함수에서 가져옴)
        nearest_pos_idx = nearestCPIdx

        neighbor_cpid_list_next = []
        base_cpid_list = []
        nearest_cp_node = cpNodeAllInst._get_cp_node_by_cpid_all(nearest_pos_idx)
        
        if nearest_cp_node.IsLast == False : 
            # 최근접 cp의 forward cp 와 라인을 형성하는데 있어서, LastCp인 경우 좌표가 같은 Br이나, 
            # 다음점이 없는 end-point인 경우이므로 최근접점이라 할지라도 neighbor list에서 제외한다. 
            # __get_next()에서도 해당 내용 적용됨.
            neighbor_cpid_list_next.append(nearest_pos_idx)
        base_cpid_list.append(nearest_pos_idx)
        status = CCPNodeAll.MORE_NEXT_CP
        while(len(neighbor_cpid_list_next) < 6 and status != CCPNodeAll.NO_MORE_NEXT_CP) :
            base_cpid_list, neighbor_cpid_list_next, status = self.__get_next(cpNodeAllInst, base_cpid_list, neighbor_cpid_list_next)
        
        neighbor_cpid_list_prev = []
        base_cpid_list = []
        base_cpid_list.append(nearest_pos_idx)
        status = CCPNodeAll.MORE_PREV_CP
        while(len(neighbor_cpid_list_prev) < 6 and status != CCPNodeAll.NO_MORE_PREV_CP) :
            base_cpid_list, neighbor_cpid_list_prev, status = self.__get_prev(cpNodeAllInst, base_cpid_list, neighbor_cpid_list_prev)

        self.print_log(f"neighbor_cpid_list_next[] = {neighbor_cpid_list_next}")
        self.print_log(f"neighbor_cpid_list_prev[] = {neighbor_cpid_list_prev}")
        self.print_log(f"최근접 CP Index : {nearest_pos_idx}")
        # endpoint인경우 backward최소 5개 필요 중간에br만나는 경우 고려
        # br인경우 중복제외 주변 점 가져오기
        # 모든 방향에서 br만나는 경우 고려해야함.
        merged_neighbor_list = list(set(neighbor_cpid_list_next + neighbor_cpid_list_prev))
        self.print_log(f"merged_neighbor_list[] = {merged_neighbor_list}")
        return merged_neighbor_list
    def __find_near_points_sub_case2(self, target_vertex, cp_idx_list, cp_all, cpNodeAllInst : CCPNodeAll) :
        ret_cp_idx_list = []
        nearest_pos_idx = -1
        ## sphere범위내의 적정 dot값을 가지고 있는 점들이지만 KDTree와는 겹치지 않는 점들인 경우임. cp_idx_list 내에서 가장 근거리점을 하나 찾고 주변 6개점을 가져오기
        distance_list = []
        for cp_idx in cp_idx_list:
            cp = cp_all[cp_idx].tolist()
            distance = np.sqrt(np.sum((target_vertex - np.array(cp))**2))
            distance_list.append([cp_idx, distance])
        sorted_distance_list = sorted(distance_list, key=lambda x: x[1])
        
        ###TODO 아래 두 방법 중 하나를 택해야함.
        nearest_pos_idx = sorted_distance_list[0][0]  ###근거리 기준
        # nearest_pos_idx = cp_idx_list[0]    ### 최소dot값 기준

        ## 최근접점(KDTree결과와순차비교)이 있으면 전후로 12개(기존6개)개데이터 가져오기
        if nearest_pos_idx != -1:
            ret_cp_idx_list = self.__get_near_12_cps_with_nearest_cp(nearest_pos_idx, cpNodeAllInst)
            
        return ret_cp_idx_list
    def __find_near_points_sub_case4(self, neighbor_idx, cp_all, cpNodeAllInst : CCPNodeAll) :
        ret_cp_idx_list = []
        
        ## 최근접점 설정 (neighbor_idx는 최소거리부터 들어 있으므로 최근접점 인덱스는 0임)
        nearest_pos_idx = neighbor_idx[0]
        
        ## 최근접점 전후로 12개데이터 가져오기
        ret_cp_idx_list = self.__get_near_12_cps_with_nearest_cp(nearest_pos_idx, cpNodeAllInst)
        return ret_cp_idx_list
    def __get_near_lines4(self, target_vertex, neighbor_cp_indices : list, cp_all : np.ndarray, cell_info : list, try_no) -> list:
        ## cp index를 보고 line 정보를 가져오기
        neighbor_line_info_list = []
        tv = target_vertex
        
        for cnt in range(len(neighbor_cp_indices)) : 
            cp0_idx = neighbor_cp_indices[cnt]
            cp1_idx = cp0_idx + 1   
            cp0 = cp_all.tolist()[cp0_idx]
            cp1 = cp_all.tolist()[cp1_idx]
            
            lineIdx = -1
            centerlineIdx = -1
            findLineIdxFlag = False  
            distance = -1			 	
            for centerlineID, linecells in enumerate(cell_info): # 한 centerline의 line들
                if [cp0_idx, cp1_idx] in linecells :
                    lineIdx = linecells.index([cp0_idx, cp1_idx])
                    centerlineIdx = centerlineID
                    # 중점 구해서 target과의 거리 구하기
                    npcp0 = np.array(cp0)
                    npcp1 = np.array(cp1)
                    mid = npcp0 + (npcp1 - npcp0) / 2
                    distance = np.sqrt(np.sum((tv - mid)**2))                    
                    neighbor_line_info_list.append({"CenterlineID":centerlineIdx, "LineID":lineIdx, "Mid": list(mid), 
                                                    "Distance":distance, "CP0":cp0, "CP1":cp1, "Weight":0.0})
                    findLineIdxFlag = True 
                    break            
            if findLineIdxFlag :
                self.print_log(f"{[cp0_idx, cp1_idx]} in linecellIdx[{lineIdx}] CLIdx: {centerlineIdx} 거리: {distance}")
            else :
                self.print_log(f"{[cp0_idx, cp1_idx]} 을 포함하는 linecell이 없어요.")
        
        ## 데이터가 4개 미만인 경우 다시 처리해야함. 바깥 루틴에서 처리.
        if len(neighbor_line_info_list) < self.NEEDED_LINE_CNT:
            self.print_log(f"ERROR : Number of neighbors(LineCell) are less than {self.NEEDED_LINE_CNT}.(Try ({try_no})")
            return None, None, self.ERROR_LESS_THAN_4
        
        ## Distance 순서로 정렬
        neighbor_line_info_list_ordered = sorted(neighbor_line_info_list , key= lambda x: x['Distance'])

        ## 4개의 데이터(거리순)만 weight를 계산
        dist = []
        for idx in range(0, self.NEEDED_LINE_CNT):
            dist.append(neighbor_line_info_list_ordered[idx]["Distance"])

        sum_of_distance = dist[0] + dist[1] + dist[2] + dist[3]
        
        neighbor_points_ordered = []
        for idx in range(0, self.NEEDED_LINE_CNT):
            neighbor_line_info_list_ordered[idx]["Weight"] = dist[idx] / sum_of_distance
            
            ##화면에 표시하기 위해 거리순 점 저장
            if neighbor_line_info_list_ordered[idx]["CP0"] not in neighbor_points_ordered:
                neighbor_points_ordered.append(neighbor_line_info_list_ordered[idx]["CP0"])
            if neighbor_line_info_list_ordered[idx]["CP1"] not in neighbor_points_ordered:
                neighbor_points_ordered.append(neighbor_line_info_list_ordered[idx]["CP1"])

        ## 출력값 =>
        ##      neighbor_line_info_list_ordered : 해당 vertex의 이웃점들로 구성된 라인정보를 출력
        return neighbor_line_info_list_ordered[:self.NEEDED_LINE_CNT], neighbor_points_ordered, self.NO_ERROR
    def __get_near_lines4_fast(self, target_vertex, neighbor_cp_indices : list, cp_all : np.ndarray, cell_info : list, try_no) -> list:
        """
        Optimized version of __get_near_lines4:
        - vectorized midpoint & distance computation for candidate cp pairs
        - lazy cached mapping from (cp0,cp1) -> (centerlineID, lineID) for O(1) lookup
        - optional bounding-sphere prefilter (computed lazily)
        Returns same structure as original: (neighbor_line_info_list_ordered[:NEEDED_LINE_CNT], neighbor_points_ordered, NO_ERROR)
        """

        # 빠른 로컬 이름
        NEEDED = self.NEEDED_LINE_CNT
        tv = np.asarray(target_vertex, dtype=float)

        # neighbor_cp_indices는 보통 ~12개 (네가 준 정보)
        if len(neighbor_cp_indices) == 0:
            return None, None, self.ERROR_LESS_THAN_4

        # --- 1) lazy 초기화: cp_all 은 numpy array 라고 가정
        cp_all_np = np.asarray(cp_all, dtype=float)  # shape (M,3)

        # 캐시: 전체 segment 리스트(모든 [cp0,cp1]) 와 center 좌표/반경, 그리고 pair->(clID,lineID) 사전
        if not hasattr(self, "_seg_cp0_indices") or not hasattr(self, "_seg_cp1_indices") or not hasattr(self, "_cp_pair_to_line"):
            # cell_info: list of list -> 각 centerline(=i)에 대해 그 안의 linecells (list of [cp0,cp1])
            seg_cp0 = []
            seg_cp1 = []
            seg_centerline_id = []
            seg_line_id = []
            for cl_id, linecells in enumerate(cell_info):
                for line_id, pair in enumerate(linecells):
                    # pair expected: [cp0_global_idx, cp1_global_idx]
                    seg_cp0.append(pair[0])
                    seg_cp1.append(pair[1])
                    seg_centerline_id.append(cl_id)
                    seg_line_id.append(line_id)
            self._seg_cp0_indices = np.array(seg_cp0, dtype=int)   # (S,)
            self._seg_cp1_indices = np.array(seg_cp1, dtype=int)   # (S,)
            self._seg_centerline_id = np.array(seg_centerline_id, dtype=int)
            self._seg_line_id = np.array(seg_line_id, dtype=int)

            # pair -> (centerlineID, lineID) dict for O(1) lookup
            # key: (cp0, cp1)
            cp_pair_to_line = {}
            for i, (c0, c1) in enumerate(zip(self._seg_cp0_indices, self._seg_cp1_indices)):
                cp_pair_to_line[(int(c0), int(c1))] = (int(self._seg_centerline_id[i]), int(self._seg_line_id[i]))
            self._cp_pair_to_line = cp_pair_to_line

            # bounding sphere precompute (center & radius) for each segment (optional filter)
            # midpoint, half-length -> radius = half-length + margin
            p0_all = cp_all_np[self._seg_cp0_indices]
            p1_all = cp_all_np[self._seg_cp1_indices]
            seg_mid_all = (p0_all + p1_all) * 0.5           # (S,3)
            seg_half_len = np.linalg.norm(p1_all - p0_all, axis=1) * 0.5
            margin = getattr(self, "SEGMENT_RADIUS_MARGIN", 5.0)  # mm 단위 margin, 필요시 설정
            self._seg_midpoints = seg_mid_all
            self._seg_radius = seg_half_len + margin

        # --- 2) candidate pairs: neighbor_cp_indices -> cp0, cp1
        cp0_idxs = np.asarray(neighbor_cp_indices, dtype=int)
        cp1_idxs = cp0_idxs + 1

        # 안전: cp1_idxs가 cp_all 범위 초과하는 경우 배제
        max_idx = cp_all_np.shape[0] - 1
        valid_mask_range = (cp0_idxs >= 0) & (cp0_idxs <= max_idx) & (cp1_idxs >= 0) & (cp1_idxs <= max_idx)
        if not np.all(valid_mask_range):
            cp0_idxs = cp0_idxs[valid_mask_range]
            cp1_idxs = cp1_idxs[valid_mask_range]
            if cp0_idxs.size == 0:
                return None, None, self.ERROR_LESS_THAN_4

        # --- 3) bounding-sphere prefilter (optional, reduces lookups)
        # compute midpoints of candidate pairs (vectorized)
        cp0_pts = cp_all_np[cp0_idxs]
        cp1_pts = cp_all_np[cp1_idxs]
        candidate_mid = (cp0_pts + cp1_pts) * 0.5   # (K,3)

        # quick filter: compare candidate_mid to all segment midpoints? that would be heavy.
        # Instead: we only need to decide if pair (cp0,cp1) exists in segments; but still distance used later.
        # So do simple check: compute distance from tv to candidate_mid (vectorized)
        dists_to_mid = np.linalg.norm(candidate_mid - tv[np.newaxis,:], axis=1)  # (K,)

        # If you want extra prefilter threshold (e.g. skip very far pairs), you can set:
        PREFILTER_DIST = getattr(self, "NEAR_LINE_PREFILTER_DIST", None)
        if PREFILTER_DIST is not None:
            keep_mask = dists_to_mid <= PREFILTER_DIST
            if not np.any(keep_mask):
                return None, None, self.ERROR_LESS_THAN_4
            cp0_idxs = cp0_idxs[keep_mask]
            cp1_idxs = cp1_idxs[keep_mask]
            candidate_mid = candidate_mid[keep_mask]
            dists_to_mid = dists_to_mid[keep_mask]

        # --- 4) Lookup mapping (pair -> centerlineID, lineID) for only the candidate pairs
        found_infos = []
        for i, (c0, c1, mid, dist) in enumerate(zip(cp0_idxs, cp1_idxs, candidate_mid, dists_to_mid)):
            key = (int(c0), int(c1))
            mapping = self._cp_pair_to_line.get(key, None)
            if mapping is None:
                # (c0,c1) 쌍이 없을 수 있음 -> 로그 남기고 continue
                # print(f"{[c0,c1]} 을 포함하는 linecell이 없어요.")
                continue
            centerlineIdx, lineIdx = mapping
            found_infos.append({
                "CenterlineID": int(centerlineIdx),
                "LineID": int(lineIdx),
                "Mid": list(mid),
                "Distance": float(dist),
                "CP0": cp_all_np[c0].tolist(),
                "CP1": cp_all_np[c1].tolist(),
                "Weight": 0.0
            })

        # --- 5) error 처리: 필요한 개수보다 적으면 원래대로 다시 시도하게 함
        if len(found_infos) < NEEDED:
            # 원래 로직을 따름(외부에서 재시도 처리하므로 여기선 에러 반환)
            # print(f"ERROR : Number of neighbors(LineCell) are less than {NEEDED}.(Try ({try_no})")
            return None, None, self.ERROR_LESS_THAN_4

        # --- 6) 거리 순 정렬 및 weight 계산 (기존 로직과 동일)
        found_infos_sorted = sorted(found_infos, key=lambda x: x['Distance'])
        dist_list = [found_infos_sorted[i]["Distance"] for i in range(NEEDED)]
        sum_of_distance = sum(dist_list[:NEEDED])
        neighbor_points_ordered = []
        for i in range(NEEDED):
            found_infos_sorted[i]["Weight"] = dist_list[i] / sum_of_distance if sum_of_distance != 0 else 0.0
            if found_infos_sorted[i]["CP0"] not in neighbor_points_ordered:
                neighbor_points_ordered.append(found_infos_sorted[i]["CP0"])
            if found_infos_sorted[i]["CP1"] not in neighbor_points_ordered:
                neighbor_points_ordered.append(found_infos_sorted[i]["CP1"])

        return found_infos_sorted[:NEEDED], neighbor_points_ordered, self.NO_ERROR
# class CCommandExtractingCLLinkColon(CCommandExtractingCLLink) :
#     def __init__(self, objName : str, skeleton : algSkeletonGraph.CSkeleton, clInPath : str, patientId : str):
#         super().__init__(objName, skeleton, clInPath, patientId)
#         self.SPHERE_RADIUS = 40.0
#     def clear(self) :
#         super().clear()
#     def init(self, saveFullPath : str) -> bool:
#         return super().init(saveFullPath)
#     def process(self) : 
#         super().process()
        

# print ("ok ..")

