# subSkelEditLung.py
# 25.06.18 

import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import datetime as dt
import json
from collections import OrderedDict
from scipy.spatial import KDTree

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

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
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algSkeletonGraph as algSkeletonGraph

import VtkObj.vtkObjLine as vtkObjLine
import VtkObj.vtkObjSphere as vtkObjSphere

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
                print(f"ERROR : listCPNode[{idx}].CPIDAll = {cpnode.CPIDAll} : Wrong ID")
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
    
class CSubSkelEditLung :
    
    def __init__(self, objName : str, skeleton : algSkeletonGraph.CSkeleton, clInPath : str):
        self.NEEDED_LINE_CNT = 4
        self.FIRST_GET_CNT = 14
        self.SPHERE_RADIUS = 10.0

        # Error-Code 
        self.NO_ERROR = 1
        self.ERROR_LESS_THAN_4 = 2

        self.m_objName = objName
        self.m_clInPath = clInPath
        self.m_polyData = None
        self.m_skeleton = skeleton
        self.m_saveFullPath = ""
        
        self.m_outJson = None
        self.m_listCenterline = []    
        self.m_cpNodeAllInst = None    
        self.m_cpNodeAllInstReady = False   

    def clear(self) :
        self.m_polyData = None
        self.m_skeleton = None
    def init(self, saveFullPath : str) -> bool:
        self.m_saveFullPath = saveFullPath

        clInFullPath = os.path.join(self.m_clInPath, f"{self.m_objName}.stl")
        if not os.path.exists(clInFullPath) :
            print(f"{clInFullPath} is not exist.")
            return False
        if self.m_skeleton == None :
            print(f"skeleton is None.")
            return False
        self.m_polyData = algVTK.CVTK.load_poly_data_stl(clInFullPath)
        
        self.init_json()
        return True

    def process(self) :
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
        normal_generator.ComputePointNormalsOn()  # or ComputeCellNormalsOn()
        normal_generator.Update()

        polydata = normal_generator.GetOutput()
        # polydata_normals = polydata.GetPointData().GetNormals()
        # if polydata_normals:
        #     for i in range(polydata.GetNumberOfPoints()):
        #         normal = polydata_normals.GetTuple(i)
        #         print(f"Point {i} normal: {normal}")
        polydata_normals = algVTK.CVTK.poly_data_get_normal(polydata)
        npCenterlinePoints, neighbor_points, neighbor_lines = self.find_neighbors(vertex, polydata_normals, listCenterline, listCenterlineByDepth, brokenLoopCLList)

        # 파일이름 받아서 저장하기
        with open(self.m_saveFullPath, "w", encoding="utf-8") as fp:
            json.dump(self.m_outJson, fp, ensure_ascii=False, indent="\t")
            print(f"centerlinedata.json dump done.")

    def init_json(self) :
        self.m_outJson = OrderedDict()
        self.m_outJson["Object"]={}
        self.m_outJson["Object"]["Name"] = self.m_objName
        self.m_outJson["Object"]["Date"] = dt.datetime.now().strftime("%m%d_%H%M%S")
        self.m_outJson["Object"]["DESC"] = f"centerline data"        
        self.m_outJson["Vertices"] = []
        self.m_outJson["CenterlinePoints"] = []
        self.m_outJson["Centerlines"] = []
        self.m_outJson["Hierarchy"] = []
        self.m_outJson["Neighbors"] = []
        self.m_outJson["CenterlineLabels"] = []
        self.m_outJson["CenterlineRadius"] = []
        self.m_outJson["BrokenLoopCPIndex"] = []

    def check_outside_centerline_point(self, skeleton, polydata) :
        print(f"Check if the centerline points are inside the mesh ->")
        outside_list = []
        for cl_inx in range(0, skeleton.get_centerline_count()) :
            skeletonCenterline = skeleton.get_centerline(cl_inx)
            for index, vert in enumerate(skeletonCenterline.Vertex):
                pos = np.array([vert])
                if not self._is_point_inside_mesh(pos[0], polydata) :
                    print(f"cl_pos[{index}] (in cl[{cl_inx}]) is not in Mesh")
                    outside_list.append([cl_inx, index, vert])
        print(f"Check Done.")
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
                            print(f"[]Info]Broken Loop Centerline(in Tree) : CL {cl.ID}")
                            broken_loop_cl_list.append(cl.ID)  #뒷단에서 이 cl의 마지막 cp를 끊어진cl리스트에 등록하게 됨.
                    hierarchy_list.append([hierarchy[0], cl.ID])
            else :
                print(f"not found centerline in depth. Stop. depth = {depth}")
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
                dicCLIDAndLevel[centerline.ID] = level
        
        print(f"Centerline Count : {len(listCenterline)}")

        ## 모든 centerline의 점을 하나의 리스트로 모으기.
        vertCntSum = 0
        centerline_line_info_all = []
        if self.m_cpNodeAllInst == None :
            self.m_cpNodeAllInst = CCPNodeAll()
        for inx, centerline in enumerate(listCenterline) :
            vertexCnt = centerline.get_vertex_count()
            vertex = centerline.Vertex
            radius = centerline.Radius            
            #--------------------------------------------
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

            #--------------------------------------------            
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
            
        print(f"brokenLoopCLCPIdxList : {brokenLoopCLCPIdxList}")    
        print(f"brokenLoopCLCPIdxAllList : {brokenLoopCLCPIdxAllList}") 

        ## CP들을 하나로 모으기
        npCenterlinePoints = np.concatenate(retCenterlineVert, axis=0)
        npCenterlineRadius = np.concatenate(retCenterlineRadius, axis=0)

        self.m_outJson["CenterlinePoints"] = npCenterlinePoints.tolist()
        self.m_outJson["CenterlineRadius"] = npCenterlineRadius.tolist()
        self.m_outJson["Centerlines"] = centerline_line_info_all
        self.m_outJson["BrokenLoopCPIndex"] = brokenLoopCpIdxList

        print("Number of Centerline Points : ", len(npCenterlinePoints))

        print("kd-tree build start")
        tree = KDTree(npCenterlinePoints)

        ret_neighbor_points = []
        ret_neighbor_line_info = None

        neighbors_info_list = []
        
        for vertidx, vert in enumerate(polyVertex):
            # print(f"VertIdx : [{vertidx}]")
            self.CURR_SPHERE_POSITION = np.array([vert])
        
            neighbor_cp_idx_list = self.__find_near_centerline_points5(tree, npCenterlinePoints, vert, self.m_cpNodeAllInst)
            try_no = 1
            neighbor_line_info, neighbor_points_ordered, errors = self.__get_near_lines4(vert, neighbor_cp_idx_list, npCenterlinePoints, centerline_line_info_all, try_no)
            if errors == self.ERROR_LESS_THAN_4:  
                    print(f"FINAL-ERROR~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~vertidx:{vertidx}")
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


        self.m_outJson["Neighbors"] = neighbors_info_list
       
        print(f"end of find_neighbors()")

        return npCenterlinePoints, ret_neighbor_points, ret_neighbor_line_info
    
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

        # print(f"neighbor_cpid_list_next[] = {neighbor_cpid_list_next}")
        # print(f"neighbor_cpid_list_prev[] = {neighbor_cpid_list_prev}")
        # print(f"최근접 CP Index : {nearest_pos_idx}")
        # endpoint인경우 backward최소 5개 필요 중간에br만나는 경우 고려
        # br인경우 중복제외 주변 점 가져오기
        # 모든 방향에서 br만나는 경우 고려해야함.
        merged_neighbor_list = list(set(neighbor_cpid_list_next + neighbor_cpid_list_prev))
        # print(f"merged_neighbor_list[] = {merged_neighbor_list}")
        return merged_neighbor_list
    def __get_near_lines4(self, target_vertex, neighbor_cp_indices : list, cp_all : np.ndarray, cell_info : list, try_no) -> list:
        ## neighbor_cp_indices 는 서로 연결되어 있는 근접 cp들이다.
        
        ## cp index를 보고 line 정보를 가져오기
        neighbor_line_info_list = []
        tv = target_vertex
        
        for cnt in range(len(neighbor_cp_indices)) : # 기존: len(neighbor_cp_indices)-1
            cp0_idx = neighbor_cp_indices[cnt]
            cp1_idx = cp0_idx + 1 #neighbor_cp_indices[cnt+1]
            # if cp0_idx > cp1_idx: # 간혹 최근거리점이 라인의 맨끝점인 경우에 [1199, 1198, 1197,..] 순으로 들어오게 되므로 라인 인덱스를 만들기 위해 작은 인덱스와 큰인덱스를 바꿈
            #     tmp = cp0_idx
            #     cp0_idx = cp1_idx
            #     cp1_idx = tmp
            cp0 = cp_all.tolist()[cp0_idx]
            cp1 = cp_all.tolist()[cp1_idx]
            
            lineIdx = -1
            centerlineIdx = -1
            findLineIdxFlag = False
            distance = -1
            for centerlineID, linecells in enumerate(cell_info): #한 centerline의 line들
                if [cp0_idx, cp1_idx] in linecells :
                    lineIdx = linecells.index([cp0_idx, cp1_idx])
                    centerlineIdx = centerlineID
                    # print(f"centerlineIdx = {centerlineIdx}  lineIdx = {lineIdx}")
                    # 중점 구해서 target과의 거리 구하기
                    npcp0 = np.array(cp0)
                    npcp1 = np.array(cp1)
                    mid = npcp0 + (npcp1 - npcp0) / 2
                    # print("(npcp0, npcp1)", npcp0, " , ", npcp1)
                    # print("mid = ", mid)
                    distance = np.sqrt(np.sum((tv - mid)**2))
                    # print("distance = ", distance)
                    
                    neighbor_line_info_list.append({"CenterlineID":centerlineIdx, "LineID":lineIdx, "Mid": list(mid), 
                                                    "Distance":distance, "CP0":cp0, "CP1":cp1, "Weight":0.0})
                    findLineIdxFlag = True
                    break
            # if findLineIdxFlag :
            #     print(f"{[cp0_idx, cp1_idx]} in linecellIdx[{lineIdx}] CLIdx: {centerlineIdx} 거리: {distance}")
            # else :
            #     print(f"{[cp0_idx, cp1_idx]} 을 포함하는 linecell이 없어요.")
        
        ## TODO :  데이터가 4개 미만인 경우 다시 처리해야함... 바깥 루틴에서 하는게 나을듯함.
        if len(neighbor_line_info_list) < self.NEEDED_LINE_CNT:
            print(f"ERROR : Number of neighbors(LineCell) are less than {self.NEEDED_LINE_CNT}.(Try ({try_no})")
            return None, None, self.ERROR_LESS_THAN_4
        
        ## Distance 순서로 정렬
        neighbor_line_info_list_ordered = sorted(neighbor_line_info_list , key= lambda x: x['Distance'])

        ## 4개의 데이터(거리순)만 weight를 계산
        dist = []
        for idx in range(0, self.NEEDED_LINE_CNT):
            dist.append(neighbor_line_info_list_ordered[idx]["Distance"])

        # print("dist : ", dist) #dist :  [23.03919868772847, 25.04589174051102, 28.638913967248786, 30.638016890164252]
        sum_of_distance = dist[0] + dist[1] + dist[2] + dist[3]
        # print("sum_of_distance : ", sum_of_distance) #sum_of_distance :  107.36202128565253
        
        neighbor_points_ordered = []
        for idx in range(0, self.NEEDED_LINE_CNT):
            neighbor_line_info_list_ordered[idx]["Weight"] = dist[idx] / sum_of_distance
            
            ##화면에 표시하기 위해 거리순 점 저장
            if neighbor_line_info_list_ordered[idx]["CP0"] not in neighbor_points_ordered:
                neighbor_points_ordered.append(neighbor_line_info_list_ordered[idx]["CP0"])
            if neighbor_line_info_list_ordered[idx]["CP1"] not in neighbor_points_ordered:
                neighbor_points_ordered.append(neighbor_line_info_list_ordered[idx]["CP1"])

        # print("neighbor_line_info_list_orderd = \n", neighbor_line_info_list_ordered[:self.NEEDED_LINE_CNT])       

        ## 출력값 =>
        ##      npCenterlinePoints : centerline의 모든 점을 한꺼번에 모아놓음
        ##      newpos_dict : 해당 vertex의 이웃점들을 index:(x,y,z) 형태의 dict로 출력
        ##      neighbor_line_info_list_ordered : 해당 vertex의 이웃점들로 구성된 라인정보를 출력
        return neighbor_line_info_list_ordered[:self.NEEDED_LINE_CNT], neighbor_points_ordered, self.NO_ERROR    
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
    
    def _find_near_centerline_points2(self, tree : KDTree, cl_all : list, cp_all : np.ndarray, radius_all : np.ndarray, target_vertex : np.ndarray, vertidx : int, vertex_normal : np.ndarray) :    
        ### vertex에서 이웃한 점들 찾기 -> dot범위내로거르기->최단거리점 기준 주변점 4개 더가져오기
        ### 리턴하는 점들은 연속되는 점들임.

        ret_cp_idx_list = []
        ret_cp_idx_and_pos_dict = {}
        
        ## 1. 이웃점들 찾기(거리순)
        distances, neighbor_idx = tree.query(target_vertex, k=self.FIRST_GET_CNT)

        ## 2. dot으로 거르기
        newpos_dict, cp_idx_list, newpos_list = self.__check_neighbors(cp_all, neighbor_idx, target_vertex, vertex_normal)
        

        ## 3.1 dot으로 걸러진 점들 중에서 최근접점 찾기
        if len(cp_idx_list) > 0 :
            print(f"===========> Case [0]  vert_idx: {vertidx}")
            ret_cp_idx_list, ret_cp_idx_and_pos_dict = self.__find_near_points_sub_case1(neighbor_idx, cp_idx_list, cp_all)
        
        ## 3.2 dot으로 걸러진 점들이 하나도 없다면 Sphere범위 내에서 다시 이웃점을 가져오기
        else : #len(cp_idx_list) < 1 :
            print(f"===========> Case [1]  vert_idx: {vertidx}")
            spherePolyData = algVTK.CVTK.create_poly_data_sphere(algLinearMath.CScoMath.to_vec3(target_vertex), self.SPHERE_RADIUS) # TODO :제대로 생성되는지 확인하기
            # self.vtk_render_add_sphere_alpha(self.m_render, np.array([target_vertex]), self.SPHERE_RADIUS , algLinearMath.CScoMath.to_vec3(self.RAINBOW_COL[3]) , 0.4)
            input_cp_idx = []
            for inx, clpos in enumerate(cp_all):
                if self._is_point_inside_mesh(clpos, spherePolyData) == True:
                    input_cp_idx.append(inx)
            newpos_dict, cp_idx_list, newpos_list = self.__check_neighbors(cp_all, input_cp_idx, target_vertex, vertex_normal, angle1=-0.7, angle2=-1.0) #구 안의 점들은 더 좁은 범위로 거름.-0.8은 너무 좁음
            
            ## Sphere범위내의 dot으로 걸러진 점들(=cp_idx_list)이 있으면 그점들에서 target vert의 최근접점을 하나 찾고 주변 6개 점을 더 가져옴
            if len(cp_idx_list) > 0:
                print(f"===========> Case [1]-1  vert_idx: {vertidx}")
                ret_cp_idx_list, ret_cp_idx_and_pos_dict = self.__find_near_points_sub_case2(target_vertex, cp_idx_list, cp_all)  #기존코드: 963-ok, 3213-bad
                # ret_cp_idx_list, ret_cp_idx_and_pos_dict = self.__find_near_points_sub_case4(neighbor_idx, cp_all)  #뉴코드: 963-bad, 3213-ok  04/25에 전달한 첫버전
                
            ## 최근접점이 없다면 KDTree결과를 리턴함( 혈관끝의 vertex 인 경우에는 주변 cp들과의 dot값이 음수가 안나올수도 있으므로 최단거리 점들을 리턴함.) 
            # else: # Method-0000   04/25에 전달한 첫버전
            #     print(f"===========> Case [1]-2  vert_idx: {vertidx}")
            #     ret_cp_idx_list, ret_cp_idx_and_pos_dict = self.__find_near_points_sub_case4(neighbor_idx, cp_all)
            else: # Method-0001   -> Method-0000과 거의 결과 비슷
                cp_in_sphere = []
                for idx in input_cp_idx : #input_cp_idx = 스피어 내부의 cp들의 인덱스
                    clpos = np.array(cp_all[idx].tolist())
                    cp_in_sphere.append(clpos)
                tree_for_sphere = KDTree(cp_in_sphere)
                new_distances, new_indices = tree_for_sphere.query(target_vertex, k=self.FIRST_GET_CNT)
                
                print(f"===========> Case [1]-2  vert_idx: {vertidx}")
                print(f"스피어내부점 인덱스 input_cp_idx = {input_cp_idx}")
                print(f"최단거리점들 인덱스 tree_for_sphere_query result : indices {new_indices}")
                ## new_indices는 실제cp의 인덱스가 아니므로 변환을 해줘야함.(아래)
                result_indices = []
                for idx in new_indices:
                    result_indices.append(input_cp_idx[idx])
                print(f"근접점리스트 결과 : {result_indices}")

                # ret_cp_idx_list, ret_cp_idx_and_pos_dict = self.__find_near_points_sub_case3(neighbor_idx, cp_all)  
                ret_cp_idx_list, ret_cp_idx_and_pos_dict = self.__find_near_points_sub_case4(result_indices, cp_all)
    
        return ret_cp_idx_list, ret_cp_idx_and_pos_dict
    
    def _get_near_lines3(self, target_vertex, neighbor_cp_indices : list, cp_all : np.ndarray, cell_info : list, try_no) -> list:
        ## 중요!! neighbor_cp_indices 에 연속된 점들이 들어 있다는 전제하에 동작되는 함수임. 
        
        ## cp index를 보고 line 정보를 가져오기
        neighbor_line_info_list = []
        tv = target_vertex
        
        for cnt in range(len(neighbor_cp_indices)-1) :
            cp0_idx = neighbor_cp_indices[cnt]
            cp1_idx = neighbor_cp_indices[cnt+1]
            # if cp0_idx > cp1_idx: # 간혹 최근거리점이 라인의 맨끝점인 경우에 [1199, 1198, 1197,..] 순으로 들어오게 되므로 라인 인덱스를 만들기 위해 작은 인덱스와 큰인덱스를 바꿈
            #     tmp = cp0_idx
            #     cp0_idx = cp1_idx
            #     cp1_idx = tmp
            cp0 = cp_all.tolist()[cp0_idx]
            cp1 = cp_all.tolist()[cp1_idx]
            
            lineIdx = -1
            centerlineIdx = -1
            for centerlineID, linecells in enumerate(cell_info): #한 centerline의 line들
                if [cp0_idx, cp1_idx] in linecells :
                    lineIdx = linecells.index([cp0_idx, cp1_idx])
                    centerlineIdx = centerlineID
                    # print(f"centerlineIdx = {centerlineIdx}  lineIdx = {lineIdx}")
                    # 중점 구해서 target과의 거리 구하기
                    npcp0 = np.array(cp0)
                    npcp1 = np.array(cp1)
                    mid = npcp0 + (npcp1 - npcp0) / 2
                    # print("(npcp0, npcp1)", npcp0, " , ", npcp1)
                    # print("mid = ", mid)
                    distance = np.sqrt(np.sum((tv - mid)**2))
                    # print("distance = ", distance)
                    
                    neighbor_line_info_list.append({"CenterlineID":centerlineIdx, "LineID":lineIdx, "Mid": list(mid), 
                                                    "Distance":distance, "CP0":cp0, "CP1":cp1, "Weight":0.0})
                    break
        # print("neighbor_line_info_list = \n")
        # for info in neighbor_line_info_list:
        #     print(info)
        
        ## TODO :  데이터가 4개 미만인 경우 다시 처리해야함... 바깥 루틴에서 하는게 나을듯함.
        if len(neighbor_line_info_list) < self.NEEDED_LINE_CNT:
            print(f"ERROR : Number of neighbors(LineCell) are less than {self.NEEDED_LINE_CNT}.(Try ({try_no})")
            return None, None, self.ERROR_LESS_THAN_4
        
        ## Distance 순서로 정렬
        neighbor_line_info_list_ordered = sorted(neighbor_line_info_list , key= lambda x: x['Distance'])

        ## 4개의 데이터(거리순)만 weight를 계산
        dist = []
        for idx in range(0, self.NEEDED_LINE_CNT):
            dist.append(neighbor_line_info_list_ordered[idx]["Distance"])

        # print("dist : ", dist) #dist :  [23.03919868772847, 25.04589174051102, 28.638913967248786, 30.638016890164252]
        sum_of_distance = dist[0] + dist[1] + dist[2] + dist[3]
        # print("sum_of_distance : ", sum_of_distance) #sum_of_distance :  107.36202128565253
        
        neighbor_points_ordered = []
        for idx in range(0, self.NEEDED_LINE_CNT):
            neighbor_line_info_list_ordered[idx]["Weight"] = dist[idx] / sum_of_distance
            
            ##화면에 표시하기 위해 거리순 점 저장
            if neighbor_line_info_list_ordered[idx]["CP0"] not in neighbor_points_ordered:
                neighbor_points_ordered.append(neighbor_line_info_list_ordered[idx]["CP0"])
            if neighbor_line_info_list_ordered[idx]["CP1"] not in neighbor_points_ordered:
                neighbor_points_ordered.append(neighbor_line_info_list_ordered[idx]["CP1"])

        # print("neighbor_line_info_list_orderd = \n", neighbor_line_info_list_ordered[:self.NEEDED_LINE_CNT])       

        ## 출력값 =>
        ##      npCenterlinePoints : centerline의 모든 점을 한꺼번에 모아놓음
        ##      newpos_dict : 해당 vertex의 이웃점들을 index:(x,y,z) 형태의 dict로 출력
        ##      neighbor_line_info_list_ordered : 해당 vertex의 이웃점들로 구성된 라인정보를 출력
        return neighbor_line_info_list_ordered[:self.NEEDED_LINE_CNT], neighbor_points_ordered, self.NO_ERROR
    
    def __check_neighbors(self,cp_all, neighbor_idx, target_vertex, vertex_normal, angle1=-0.5, angle2=-1.0):
        ### neighbor_idx 는 KDTree최단거리점들이거나 Sphere내의 점들인 두가지 경우임.
        newpos_list = []
        for idx in neighbor_idx:
            clpos = np.array(cp_all[idx].tolist())
            vec_tmp = clpos - target_vertex
            vec_tmp_dist = np.linalg.norm(vec_tmp) ## vec_tmp길이
            vec_tmp_norm = vec_tmp / vec_tmp_dist  ## normalize
            dot = np.dot(vertex_normal, vec_tmp_norm)

            # print(f"---pos : {clpos}, normal : {vertex_normal}")
            # print(f"---vec_tmp : {vec_tmp}")                
            # print(f"---vec_tmp_norm : {vec_tmp_norm}")
            # print(f"---vert_new : {vert_new}")
            
            # if dot < -0.5 and dot >= -1.0:  # 120도에서 240도 사이 ##TUNING-POINT
            if dot < angle1 and dot >= angle2 :
                # print(f"---dot : {dot} Use")
                newpos_list.append([idx, dot, cp_all[idx].tolist()])
                # newpos_dict[idx] = tuple(cp_all[idx].tolist())
                # cp_idx_list.append(idx)
            # else :
            #     print(f"+++dot : {dot} NotUse")
        ##dot기준 오름차순정렬    
        sorted_newpos_list = sorted(newpos_list, key=lambda point: point[1])
        newpos_dict = {}
        cp_idx_list = []
        for idx, item in enumerate(sorted_newpos_list) :
            # if idx == (self.NEEDED_LINE_CNT+1) :
            #     break
            newpos_dict[item[0]] = tuple(item[2])
            cp_idx_list.append(item[0])
            
        return newpos_dict, cp_idx_list, newpos_list
    def __find_near_points_sub_case1(self, neighbor_idx, cp_idx_list, cp_all) :
        
        ret_cp_idx_list = []
        ret_cp_idx_and_pos_dict = {}
    
        ## 최근접점 찾기 (neighbor_idx는 최소거리부터 들어 있으므로 cp_idx_list와 교차되는 첫 점이 최근접점이 됨)
        nearest_pos_idx = -1
        for n_idx in neighbor_idx:
            if n_idx in cp_idx_list :
                nearest_pos_idx = n_idx
                break
        ## 최근접점(KDTree결과와순차비교)이 있으면 전후로 12개데이터 가져오기
        if nearest_pos_idx != -1:
            ##최근접점이 센터라인의 맨 끝점(양끝모두)인 경우 최근접점 기준으로 3개 데이터를 더 가져올수가 없게 되므로, 
            # 아예 최근접점 기준으로 이전 6개 데이터를 가져오고, 이후 6개를 가져오도록 함. 이렇게 하면 이후의 
            # 3개 데이터를 못가져오더라도 안정적으로 라인인덱스 4개를 취할 수 있음.
            for index in range(-6, 6): #TUNING-POINT 전후 12개데이터
                real_idx = (nearest_pos_idx + index)
                if real_idx >= 0 and real_idx < len(cp_all) : #실제 점 인덱스는 유효범위내여야함
                    ret_cp_idx_list.append(real_idx)
            # print(f"ret_cp_idx_list(case1) : {ret_cp_idx_list}")
            for idx in ret_cp_idx_list:
                    pos = tuple(cp_all[idx].tolist())
                    ret_cp_idx_and_pos_dict[idx] = pos
        else : # sphere범위내의 적정 dot값을 가지고 점들이지만 KDTree와는 겹치지 않는 점들인 경우임. cp_idx_list 내에서 가장 근거리점을 하나 찾고 주변 6개점을 가져오기
            # __find_near_points_sub_case2()에서 구현하기로 함. 그러므로 여기 도달하면 안됨.
            print(f"------------------------------>CRITICAL-ERROR 1: Not implemented Case. Check the logic~!!!")

        return ret_cp_idx_list, ret_cp_idx_and_pos_dict
    def __find_near_points_sub_case2(self, target_vertex, cp_idx_list, cp_all) :
        ret_cp_idx_list = []
        ret_cp_idx_and_pos_dict = {}

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

        ## 최근접점(KDTree결과와순차비교)이 있으면 전후로 6개데이터 가져오기
        if nearest_pos_idx != -1:
            for index in range(-3, 3): #TUNING-POINT 전후 6개데이터
                real_idx = (nearest_pos_idx + index)
                if real_idx >= 0 and real_idx < len(cp_all) : #실제 점 인덱스는 유효범위내여야함
                    ret_cp_idx_list.append(real_idx)
            # print(f"ret_cp_idx_list(case2) : {ret_cp_idx_list}")
            for idx in ret_cp_idx_list:
                    pos = tuple(cp_all[idx].tolist())
                    ret_cp_idx_and_pos_dict[idx] = pos
        
        return ret_cp_idx_list, ret_cp_idx_and_pos_dict
    
    def __find_near_points_sub_case4(self, neighbor_idx, cp_all) :
        
        ret_cp_idx_list = []
        ret_cp_idx_and_pos_dict = {}
    
        ## 최근접점 설정 (neighbor_idx는 최소거리부터 들어 있으므로 최근접점 인덱스는 0임)
        nearest_pos_idx = neighbor_idx[0]   #sally : __find_near_points_sub_case3 코드에서 이부분만 수정함. 버그였음.
        
        ## 최근접점 전후로 12개데이터 가져오기
        
        ##최근접점이 센터라인의 맨 끝점(양끝모두)인 경우 최근접점 기준으로 3개 데이터를 더 가져올수가 없게 되므로, 
        # 아예 최근접점 기준으로 이전 6개 데이터를 가져오고, 이후 6개를 가져오도록 함. 이렇게 하면 이후의 
        # 3개 데이터를 못가져오더라도 안정적으로 라인인덱스 4개를 취할 수 있음.
        for index in range(-6, 6): #TUNING-POINT 전후 12개데이터
            real_idx = (nearest_pos_idx + index)
            if real_idx >= 0 and real_idx < len(cp_all) : #실제 점 인덱스는 유효범위내여야함
                ret_cp_idx_list.append(real_idx)
        # print(f"ret_cp_idx_list(case3) : {ret_cp_idx_list}")
        for idx in ret_cp_idx_list:
                pos = tuple(cp_all[idx].tolist())
                ret_cp_idx_and_pos_dict[idx] = pos
        
        return ret_cp_idx_list, ret_cp_idx_and_pos_dict
    
if __name__ == '__main__' :
    pass


# print ("ok ..")

