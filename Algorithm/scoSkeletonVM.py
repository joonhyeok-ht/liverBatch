import matplotlib.pyplot as plt
import SimpleITK as sitk
import cv2
import numpy as np
import os
import open3d as o3d
import open3d.core
import open3d.visualization

import networkx as nx

import scoUtil
import scoMath
import scoBuffer
import scoSkeleton
import scoSplineSkeleton
import scoData
from abc import abstractmethod


class CScoSkelVM :
    def __init__(self, skel : scoSkeleton.CScoSkel) -> None:
        self.m_skel = skel

    def clear(self) :
        self.m_skel = None

    
    @property
    def Skel(self) :
        return self.m_skel
    


class CScoSkelVMGraph(CScoSkelVM) :
    eRootMode_EndPoint = 0
    eRootMode_Branch = 1

    s_minVesselCoordCnt = 10


    def __init__(self, skel : scoSkeleton.CScoSkel) -> None:
        super().__init__(skel)

        # input your code
        self.init_graph()

    def clear(self) :
        # input your code 

        super().clear()

    def init_graph(self) :
        self.m_graph = nx.Graph()
        self.m_graph.clear()
        self.m_listGraphNode = []
        self.m_rootGraphNodeInx = -1
        self.init_build_graph()
    def init_build_graph(self) :
        self.m_listGraphNode += self.m_skel.m_listEndPoint
        self.m_listGraphNode += self.m_skel.m_listBranchGroup
        self.m_listGraphNode += self.m_skel.m_listVesselSeg

        # add graph node 
        for inx, graphNode in enumerate(self.m_listGraphNode) :
            self.m_graph.add_nodes_from([(inx, {"inst" : graphNode})])

        for vesselSegInx in range(0, self.Skel.VesselSegCount) :
            vesselSeg = self.Skel.ListVesselSeg[vesselSegInx]
            vesselSegGraphInx = self.get_graph_node_inx(vesselSeg)

            # vesselType이 distal과 connection만 graph에 연결하도록 한다.
            if vesselSeg.SegmentType == scoSkeleton.CScoSkelSegment.eSegmentType_Distal :
                endPointInx = vesselSeg.get_endpoint_inx(0)
                endPoint = self.Skel.ListEndPoint[endPointInx]
                endPointGraphInx = self.get_graph_node_inx(endPoint)
                branchInx = vesselSeg.get_branch_inx(0)
                branch = self.Skel.ListBranchGroup[branchInx]
                branchGraphInx = self.get_graph_node_inx(branch)
                self.m_graph.add_edge(vesselSegGraphInx, endPointGraphInx)
                self.m_graph.add_edge(vesselSegGraphInx, branchGraphInx)
            elif vesselSeg.SegmentType == scoSkeleton.CScoSkelSegment.eSegmentType_Connection :
                # connection type은 반드시 branch가 2개여야만 한다. 
                for i in range(0, 2) :
                    branchInx = vesselSeg.get_branch_inx(i)
                    branch = self.Skel.ListBranchGroup[branchInx]
                    branchGraphInx = self.get_graph_node_inx(branch)
                    self.m_graph.add_edge(vesselSegGraphInx, branchGraphInx)

    def process(self, rootNiftiFullPath : str, rootMode = 0) :
        """
        rootMode : eRootMode_EndPoint , EndPoint를 우선으로 하여 Root를 찾는다. 
                 : eRootMode_Branch , Branch를 우선으로 하여 Root를 찾는다. 
        """
        sitkImg = scoUtil.CScoUtilSimpleITK.load_image(rootNiftiFullPath, None)
        npMaskImg = scoUtil.CScoUtilSimpleITK.sitkImg_to_npImg(sitkImg, "uint8").transpose((2, 1, 0))  # order : x, y, z
        self.m_bufRootMask = scoBuffer.CScoBuffer3D(npMaskImg.shape, "uint8")

        xInx, yInx, zInx = np.where(npMaskImg > 0)
        self.m_bufRootMask.all_set_voxel(0)
        self.m_bufRootMask.set_voxel((xInx, yInx, zInx), 255)

        if rootMode == self.eRootMode_EndPoint :
            rootInx = self.find_root_node_with_endpoint()
            if rootInx == -1 :
                rootInx = self.find_root_node_with_branch_sco()
        else :
            rootInx = self.find_root_node_with_branch_sco()
            if rootInx == -1 :
                rootInx = self.find_root_node_with_endpoint()

        # rootInx = self.find_root_node_with_endpoint()
        # if rootInx == -1 :
        #     rootInx = self.find_root_node_with_branch(False)
        #     if rootInx == -1 :
        #         rootInx = self.find_root_node_with_branch(True)

        if rootInx == -1 :
            print("SkelVMGraph Error : not found root index")
            return

        self.RootGraphNodeInx = rootInx
    

    # get member
    def get_graph_node_inx(self, node) :
        return self.m_listGraphNode.index(node)
    def get_graph_node(self, inx : int) :
        return self.m_listGraphNode[inx]
    def get_shortest_path(self, srcGraphNodeInx : int, targetGraphNodeInx : int) :
        return nx.shortest_path(self.m_graph, srcGraphNodeInx, targetGraphNodeInx)
    
    def is_path_including(self, srcGraphNodeInx : int, targetGraphNodeInx : int, findGraphNodeInx : int) :
        pathList = self.get_shortest_path(srcGraphNodeInx, targetGraphNodeInx)

        if findGraphNodeInx in pathList :
            return True
        
        return False
    def is_voxel_inx_in_mask(self, voxelInx : tuple, bufMask : scoBuffer.CScoBuffer3D) :
        mask = bufMask.get_voxel(voxelInx)
        ret = mask > 0
        return ret
    

    # protected
    def find_root_node_with_endpoint(self) :
        listEndPoint = []

        for endPoint in self.Skel.ListEndPoint :
            endPointVoxelInx = scoSkeleton.CScoSkel.convert_vec3_to_voxel_index(endPoint.Coord)
            if self.is_voxel_inx_in_mask(endPointVoxelInx, self.m_bufRootMask) == True :
                listEndPoint.append(endPoint)
        
        # EndPoint가 Root Vessel에 없을 경우 
        if len(listEndPoint) == 0 :
            return -1
        
        listEndPoint.sort(key = lambda x : -x.Coord.Z)
        return self.get_graph_node_inx(listEndPoint[0])
    def find_root_node_with_branch_sco(self) :
        listRootVesselSeg = []
        # 상위 가장 긴 vessel segment를 얻어온다.
        for vesselSeg in self.m_skel.ListVesselSeg :
            if self.is_vessel_seg_in_mask(vesselSeg, self.m_bufRootMask) == True :
                listRootVesselSeg.append(vesselSeg)
        vesselCoordCnt = len(listRootVesselSeg)
        if vesselCoordCnt == 0 :
            return -1
        listRootVesselSeg.sort(key = lambda x : -x.CoordCount)

        # root vesselSeg를 추출한다. 
        rootVesselSeg = None
        if vesselCoordCnt == 1 :
            rootVesselSeg = listRootVesselSeg[0]
        else :
            listTmp = []
            for vesselSeg in listRootVesselSeg :
                if vesselSeg.CoordCount >= self.s_minVesselCoordCnt :
                    listTmp.append(vesselSeg)
            if len(listTmp) == 0 :
                rootVesselSeg = listRootVesselSeg[0]
            elif len(listTmp) == 1 :
                rootVesselSeg = listTmp[0]
            else :
                # 상위 2개만 가지고 판단한다. 여기에서는 문제가 생길 수 있으므로 주시하도록 한다.
                vessel0 = listTmp[0]
                vessel1 = listTmp[1]
                radiusAver0 = self.get_radius_average(vessel0)
                radiusAver1 = self.get_radius_average(vessel1)
                if radiusAver0 > radiusAver1 :
                    rootVesselSeg = vessel0
                else :
                    rootVesselSeg = vessel1
        
        # rootVesselSeg에 연결된 branch를 얻어온다. 
        listRootBranch = []
        for branchInx in rootVesselSeg.m_listBranchInx :
            branch = self.m_skel.ListBranchGroup[branchInx]
            listRootBranch.append(branch)
        
        if len(listRootBranch) == 0 :
            return -1
        listRootBranch.sort(key = lambda x : -x.get_real_branch_coord().Z)
        return self.get_graph_node_inx(listRootBranch[0])

    def find_root_node_with_branch(self, bConn : bool) :
        listRootBranch = None
        if bConn == True :
            listRootBranch = self.find_conn_branch_in_root()
        else :
            listRootBranch = self.find_branch_in_root()
        if listRootBranch is None :
            return -1
        listRootBranch.sort(key = lambda x : -x.get_real_branch_coord().Z)
        return self.get_graph_node_inx(listRootBranch[0])
    def find_branch_in_root(self) :
        listRootBranch = []
        for branch in self.m_skel.ListBranchGroup :
            if self.is_branch_in_mask(branch, self.m_bufRootMask) == True :
                listRootBranch.append(branch)

        if len(listRootBranch) == 0 :
            return None
        else :
            return listRootBranch
    def find_conn_branch_in_root(self) :
        listRootBranch = []
        listBranchFlag = [False for branch in self.m_skel.ListBranchGroup]
        for vesselSeg in self.m_skel.ListVesselSeg :
            if self.is_vessel_seg_in_mask(vesselSeg, self.m_bufRootMask) == True :
                for inx in range(0, vesselSeg.BranchInxCount) :
                    branchInx = vesselSeg.get_branch_inx(inx)
                    if listBranchFlag[branchInx] == True :
                        continue

                    listBranchFlag[branchInx] = True
                    listRootBranch.append(self.m_skel.ListBranchGroup[branchInx])

        if len(listRootBranch) == 0 :
            return None
        else :
            return listRootBranch
    def is_branch_in_mask(self, branch : scoSkeleton.CScoSkelBranch, bufMask : scoBuffer.CScoBuffer3D) :
        for coordInx in range(0, branch.BranchCount) :
            coord = branch.get_branch_coord(coordInx)
            voxelInx = scoSkeleton.CScoSkel.convert_vec3_to_voxel_index(coord)
            if self.is_voxel_inx_in_mask(voxelInx, bufMask) == True :
                return True
        return False
    def is_vessel_seg_in_mask(self, vesselSeg : scoSkeleton.CScoSkelSegment, bufMask : scoBuffer.CScoBuffer3D) :
        for coord in vesselSeg.ListCoord :
            voxelInx = scoSkeleton.CScoSkel.convert_vec3_to_voxel_index(coord)
            if self.is_voxel_inx_in_mask(voxelInx, bufMask) == True :
                return True
        return False
    
    def find_root_node_with_vessel_segment(self) :
        listRootBranch = self.find_branch_in_root()
        if listRootBranch is None :
            return -1
        rootVesselSegInx = self.find_root_vessel_segment(listRootBranch)
        return self.get_graph_node_inx(self.m_skel.ListVesselSeg[rootVesselSegInx])
    def find_root_vessel_segment(self, listRootBranch : list) :
        maxZ = -1
        maxZConnSegInx = -1
        for branch in listRootBranch : 
            for connSegInx in range(0, branch.ConnSegInxCount) :
                connSeg = self.m_skel.ListVesselSeg[connSegInx]
                if connSeg.SegmentType == scoSkeleton.CScoSkelSegment.eSegmentType_None or \
                connSeg.SegmentType == scoSkeleton.CScoSkelSegment.eSegmentType_Disconnected :
                    continue

                z = self.get_max_z_of_vessel_segment(connSeg)
                if maxZ < z :
                    maxZ = z
                    maxZConnSegInx = connSegInx
        return maxZConnSegInx
    def get_max_z_of_vessel_segment(self, vesselSegment : scoSkeleton.CScoSkelSegment) :
        listVesselSegEndPoint = vesselSegment.get_end_point()

        if listVesselSegEndPoint is None :
            return -1
        if len(listVesselSegEndPoint) == 1 :
            return listVesselSegEndPoint[0].Z
        else :
            maxZ = -1
            for endPoint in listVesselSegEndPoint :
                if maxZ < endPoint.Z :
                    maxZ = endPoint.Z
            return maxZ
    def get_radius_average(self, vesselSeg) :
        vesselSegInx = self.m_skel.ListVesselSeg.index(vesselSeg)
        iCnt = vesselSeg.CoordCount

        midInx = int(iCnt / 2)
        preInx = midInx - 1
        nextInx = midInx + 1

        _, preRadius = self.m_skel.get_radius(vesselSegInx, preInx)
        _, midRadius = self.m_skel.get_radius(vesselSegInx, midInx)
        _, nextRadius = self.m_skel.get_radius(vesselSegInx, nextInx)

        return (preRadius + midRadius + nextRadius) / 3.0


    @property
    def RootGraphNodeInx(self) :
        return self.m_rootGraphNodeInx
    @RootGraphNodeInx.setter
    def RootGraphNodeInx(self, inx : int) :
        self.m_rootGraphNodeInx = inx
    @property
    def RootMask(self) :
        return self.m_bufRootMask




class CScoSkelVMReorder(CScoSkelVMGraph) :
    def __init__(self, skel: scoSkeleton.CScoSkel) -> None:
        super().__init__(skel)

    def process(self, rootNiftiFullPath : str, rootMode : int) :
        super().process(rootNiftiFullPath, rootMode)
        # input your code
        self.reorder()
    def clear(self) :
        # input your code 

        super().clear()

    
    def reorder(self) :
        listVesselSegFlag = [False for vesselSeg in self.Skel.ListVesselSeg]

        for vesselSegInx, vesselSeg in enumerate(self.Skel.ListVesselSeg) :
            if vesselSeg.SegmentType == scoSkeleton.CScoSkelSegment.eSegmentType_None or \
            vesselSeg.SegmentType == scoSkeleton.CScoSkelSegment.eSegmentType_Disconnected :
                listVesselSegFlag[vesselSegInx] = True
                continue

            vesselSegGraphInx = self.get_graph_node_inx(vesselSeg)
            listPath = self.get_shortest_path(self.RootGraphNodeInx, vesselSegGraphInx)
            if len(listPath) == 0 :
                continue

            for graphInx in listPath :
                graphNode = self.get_graph_node(graphInx)

                if graphNode.Type == scoSkeleton.CScoSkelNode.eVoxelTypeEndPoint or \
                graphNode.Type == scoSkeleton.CScoSkelNode.eVoxelTypeBranch or \
                graphNode.Type == scoSkeleton.CScoSkelNode.eVoxelTypeNone :
                    parentGraphNodeInx = graphInx
                    continue

                vesselSegInx = self.Skel.get_vessel_seg_inx(graphNode)
                vesselSeg = graphNode

                if listVesselSegFlag[vesselSegInx] == True :
                    continue

                # Branch-Branch
                if vesselSeg.SegmentType == scoSkeleton.CScoSkelSegment.eSegmentType_Connection :
                    parentBranch = self.get_graph_node(parentGraphNodeInx)
                    parentBranchInx = self.Skel.get_branch_group_inx(parentBranch)

                    if vesselSeg.get_branch_inx(0) != parentBranchInx :
                        vesselSeg.reorder()
                # Branch-EndPoint or EndPoint - Branch
                elif vesselSeg.SegmentType == scoSkeleton.CScoSkelSegment.eSegmentType_Distal :
                    parentGraphNode = self.get_graph_node(parentGraphNodeInx)

                    if parentGraphNode.Type == scoSkeleton.CScoSkelNode.eVoxelTypeEndPoint and \
                    vesselSeg.get_conn_voxel_type(0) !=  scoSkeleton.CScoSkelNode.eVoxelTypeEndPoint :
                        vesselSeg.reorder()
                    elif parentGraphNode.Type == scoSkeleton.CScoSkelNode.eVoxelTypeBranch and \
                    vesselSeg.get_conn_voxel_type(0) != scoSkeleton.CScoSkelNode.eVoxelTypeBranch :
                        vesselSeg.reorder()

                listVesselSegFlag[vesselSegInx] = True





class CScoSkelVMCreateSplineSkel(CScoSkelVMReorder) :
    s_minRadius = 1.0

    @staticmethod
    def set_conn_node(
        skel : scoSkeleton.CScoSkel, splineSkel,
        vesselSeg : scoSkeleton.CScoSkelSegment, splineSeg : scoSplineSkeleton.CScoSplineSegment
        ) -> list :
        voxelInx0 = scoSkeleton.CScoSkel.convert_vec3_to_voxel_index(splineSeg.get_cp(0))
        voxelInx1 = scoSkeleton.CScoSkel.convert_vec3_to_voxel_index(splineSeg.get_cp(-1))

        # branch - branch
        if splineSeg.SegmentType == scoSkeleton.CScoSkelSegment.eSegmentType_Connection :
            branch0Inx = vesselSeg.get_branch_inx(0)
            branch1Inx = vesselSeg.get_branch_inx(1)
            branch0Node = skel.m_listBranchGroup[branch0Inx]
            branch1Node = skel.m_listBranchGroup[branch1Inx]

            listBranchVoxelInx = skel.get_conn_coord_with_candidate_branch(skel.m_npVoxelType, voxelInx0)
            if len(listBranchVoxelInx) == 2 :
                branch0 = splineSkel.ListBranchGroup[branch0Inx]
                branch1 = splineSkel.ListBranchGroup[branch1Inx]
                splineSeg.add_conn_node(branch0)
                splineSeg.add_conn_node(branch1)
                return
            
            branchCoord = scoSkeleton.CScoSkel.convert_voxel_index_to_vec3(listBranchVoxelInx[0])
            if branch0Node.in_branch_coord(branchCoord) == True:
                branch0 = splineSkel.ListBranchGroup[branch0Inx]
                splineSeg.add_conn_node(branch0)
            else :
                branch1 = splineSkel.ListBranchGroup[branch1Inx]
                splineSeg.add_conn_node(branch1)
            
            listBranchVoxelInx = skel.get_conn_coord_with_candidate_branch(skel.m_npVoxelType, voxelInx1)
            branchCoord = scoSkeleton.CScoSkel.convert_voxel_index_to_vec3(listBranchVoxelInx[0])
            if branch0Node.in_branch_coord(branchCoord) == True:
                branch0 = splineSkel.ListBranchGroup[branch0Inx]
                splineSeg.add_conn_node(branch0)
            else :
                branch1 = splineSkel.ListBranchGroup[branch1Inx]
                splineSeg.add_conn_node(branch1)
        # branch - endpoint
        elif splineSeg.SegmentType == scoSkeleton.CScoSkelSegment.eSegmentType_Distal :
            branchInx = vesselSeg.get_branch_inx(0)
            endPointInx = vesselSeg.get_endpoint_inx(0)
            branch = splineSkel.ListBranchGroup[branchInx]
            endPoint = splineSkel.ListEndPoint[endPointInx]

            listBranchVoxelInx = skel.get_conn_coord_with_candidate_branch(skel.m_npVoxelType, voxelInx0)
            if len(listBranchVoxelInx) == 1 :
                splineSeg.add_conn_node(branch)
                splineSeg.add_conn_node(endPoint)
            else :
                splineSeg.add_conn_node(endPoint)
                splineSeg.add_conn_node(branch)
        # endpoint - endpoint
        elif splineSeg.SegmentType == scoSkeleton.CScoSkelSegment.eSegmentType_Disconnected :
            endPoint0Inx = vesselSeg.get_endpoint_inx(0)
            endPoint1Inx = vesselSeg.get_endpoint_inx(1)
            endPoint0Node = skel.m_listEndPoint[endPoint0Inx]
            endPoint1Node = skel.m_listEndPoint[endPoint1Inx]

            listEndPointVoxelInx = skel.get_conn_coord_with_end_point(skel.m_npVoxelType, voxelInx0)
            if len(listEndPointVoxelInx) == 2 :
                endPoint0 = splineSkel.ListEndPoint[endPoint0Inx]
                endPoint1 = splineSkel.ListEndPoint[endPoint1Inx]
                splineSeg.add_conn_node(endPoint0)
                splineSeg.add_conn_node(endPoint1)
                return
            
            endCoord = scoSkeleton.CScoSkel.convert_voxel_index_to_vec3(listEndPointVoxelInx[0])
            if scoMath.CScoMath.equal_vec3(endPoint0Node.Coord, endCoord) == True:
                endPoint0 = splineSkel.ListEndPoint[endPoint0Inx]
                splineSeg.add_conn_node(endPoint0)
            else :
                endPoint1 = splineSkel.ListEndPoint[endPoint1Inx]
                splineSeg.add_conn_node(endPoint1)
            
            listEndPointVoxelInx = skel.get_conn_coord_with_end_point(skel.m_npVoxelType, voxelInx1)
            endCoord = scoSkeleton.CScoSkel.convert_voxel_index_to_vec3(listEndPointVoxelInx[0])
            if scoMath.CScoMath.equal_vec3(endPoint0Node.Coord, endCoord) == True:
                endPoint0 = splineSkel.ListEndPoint[endPoint0Inx]
                splineSeg.add_conn_node(endPoint0)
            else :
                endPoint1 = splineSkel.ListEndPoint[endPoint1Inx]
                splineSeg.add_conn_node(endPoint1)



    def __init__(self, skel: scoSkeleton.CScoSkel) -> None:
        super().__init__(skel)

    def process(
            self, 
            rootNiftiFullPath : str, rootMode : int,
            patient : scoData.CPatient, dataPatientType : int,
            cpInterval : int, initRadius : float
            ) :
        super().process(rootNiftiFullPath, rootMode)
        # input your code
        self.m_patient = patient
        self.m_dataPatientType = dataPatientType
        self.tmp_mask = self.m_patient.get_mask(self.m_dataPatientType)

        if self.tmp_mask is None :
            print("create spline skel : error data patient type")
            return 

        self.m_splineSkel = scoSplineSkeleton.CScoSplineSkel()
        self.m_splineSkel.m_shape = (self.m_skel.MaskImg.shape[0], self.m_skel.MaskImg.shape[1], self.m_skel.MaskImg.shape[2])

        for endPoint in self.m_skel.m_listEndPoint : 
            cloneEndPoint = endPoint.clone()
            self.m_splineSkel.ListEndPoint.append(cloneEndPoint)
        for branchGroup in self.m_skel.m_listBranchGroup : 
            cloneBranchGroup = branchGroup.clone()
            self.m_splineSkel.ListBranchGroup.append(cloneBranchGroup)
        for vesselInx, vesselSeg in enumerate(self.m_skel.m_listVesselSeg) :
            splineSegment = scoSplineSkeleton.CScoSplineSegment()
            self.m_splineSkel.ListSplineSeg.append(splineSegment)
            splineSegment.m_type = vesselSeg.m_type
            splineSegment.m_segmentType = vesselSeg.m_segmentType
            splineSegment.Name = vesselSeg.Name

            if vesselInx == 14 :
                i = 10

            if splineSegment.SegmentType == scoSkeleton.CScoSkelSegment.eSegmentType_None :
                continue

            physicalRadius = -1
            if dataPatientType == scoData.CDataPatient.eDataPatientType_Arterial :
                arterialID = scoData.CDataArterial.find_arterial_id(splineSegment.Name)
                if arterialID >= 0 :
                    physicalRadius = scoData.CDataArterial.get_arterial_max_radius(arterialID)
            elif dataPatientType == scoData.CDataPatient.eDataPatientType_Vein :
                veinID = scoData.CDataVein.find_vein_id(splineSegment.Name)
                if veinID >= 0 :
                    physicalRadius = scoData.CDataVein.get_vein_max_radius(veinID)

            # cp extraction 
            if len(vesselSeg.ListCoord) == 1 :
                coord = vesselSeg.ListCoord[0]
                cp = coord.clone()
                splineSegment.add_cp(cp)

                radius = self.get_radius(vesselInx, 0, physicalRadius)
                #_, radius = self.m_skel.get_radius(vesselInx, 0)
                splineSegment.add_radius(radius)
            else :
                for inx in range(0, len(vesselSeg.ListCoord) - 1, cpInterval) :
                    coord = vesselSeg.ListCoord[inx]
                    cp = coord.clone()
                    splineSegment.add_cp(cp)

                    radius = self.get_radius(vesselInx, inx, physicalRadius)
                    #_, radius = self.m_skel.get_radius(vesselInx, inx)
                    splineSegment.add_radius(radius)
                # added end-cp & radius
                coord = vesselSeg.ListCoord[-1]
                cp = coord.clone()
                splineSegment.add_cp(cp)

                radius = self.get_radius(vesselInx, len(vesselSeg.ListCoord) - 1, physicalRadius)
                #_, radius = self.m_skel.get_radius(vesselInx, len(vesselSeg.ListCoord) - 1)
                splineSegment.add_radius(radius)
            
            CScoSkelVMCreateSplineSkel.set_conn_node(self.m_skel, self.m_splineSkel, vesselSeg, splineSegment)

            # add first-end cp
            listConnNode = [splineSegment.get_conn_node(0), splineSegment.get_conn_node(1)]
            retCP = []
            for connNode in listConnNode :
                if isinstance(connNode, scoSkeleton.CScoSkelBranch) :
                    cp = connNode.get_real_branch_coord()
                elif isinstance(connNode, scoSkeleton.CScoSkelEndPoint) :
                    cp = connNode.Coord.clone()
                
                retCP.append(cp)
            
            splineSegment.ListCP.insert(0, retCP[0])
            splineSegment.ListCP.append(retCP[1])
            startRadius = splineSegment.get_radius(0)
            endRadius = splineSegment.get_radius(-1)
            splineSegment.ListRadius.insert(0, startRadius)
            splineSegment.ListRadius.append(endRadius)
            #if vesselInx == 42 :
            #    i = 10
            #splineSegment.refine_radius()

            # add startU, endU 
            startCP = splineSegment.get_cp(0)
            endCP = splineSegment.get_cp(1)
            startU = endCP.subtract(startCP)
            startU.normalize()
            splineSegment.StartU = startU

            startCP = splineSegment.get_cp(-2)
            endCP = splineSegment.get_cp(-1)
            endU = endCP.subtract(startCP)
            endU.normalize()
            splineSegment.EndU = endU

        self.m_splineSkel.MatPhysical = self.m_skel.MatPhysical
        
        self.m_listSegFlag = [False for seg in self.m_splineSkel.ListSplineSeg]
        self.refine_radius(initRadius)

        self.tmp_mask = None
    def clear(self) :
        # input your code 
        super().clear()


    # protected 
    def get_radius(self, vesselInx : int, vesselSubInx : int, physicalRadius : float) :
        radius = 0.0
        if physicalRadius < 0.0 :
            _, radius = self.m_skel.get_radius(vesselInx, vesselSubInx)
        else :
            _, radius = self.m_skel.get_radius_from_physical(vesselInx, vesselSubInx, physicalRadius)
            if radius > physicalRadius :
                radius = physicalRadius
        return radius
    def refine_radius(self, initRadius : float) :
        # root에 해당되는 endpoint를 구한다. 
        # segment를 추출한다.
        # refine_radius_call_stack를 호출한다. 

        if self.RootGraphNodeInx == -1 :
            print("can not found root end-point")
            return
        
        rootInx = self.RootGraphNodeInx
        rootNode = self.get_graph_node(rootInx)

        if rootNode.Type == scoSkeleton.CScoSkelNode.eVoxelTypeEndPoint :
            endPoint = rootNode
            childSplineSegInx = endPoint.ConnSegInx
            self.refine_radius_call_stack(childSplineSegInx, initRadius, True)
        elif rootNode.Type == scoSkeleton.CScoSkelNode.eVoxelTypeBranch :
            branch = rootNode
            for inx in range(0, branch.ConnSegInxCount) :
                connSegInx = branch.get_conn_seg_inx(inx)
                self.refine_radius_call_stack(connSegInx, initRadius, False)
    def refine_radius_call_stack(self, splineSegInx : int, parentRadius : float, bRoot = False) :
        self.m_listSegFlag[splineSegInx] = True

        if splineSegInx == 99 :
            i = 0

        splineSeg = self.m_splineSkel.ListSplineSeg[splineSegInx]
        if splineSeg.SegmentType == scoSkeleton.CScoSkelSegment.eSegmentType_None :
                return
        
        if bRoot == False :
            startRadius = self.start_radius(splineSeg, parentRadius)
        else :
            startRadius = self.start_radius_root(splineSeg, parentRadius)
        endRadius = self.end_radius(splineSeg)
        # endRadius는 parentRadius가 되어서는 안된다.
        if endRadius > startRadius :
            endRadius = startRadius

        for inx, radius in enumerate(splineSeg.ListRadius) :
            if radius > startRadius :
                radius = startRadius
            if radius < self.s_minRadius :
                radius = self.s_minRadius
            
            splineSeg.ListRadius[inx] = radius
        
        branch = splineSeg.ListConnNode[1]
        if branch.Type != scoSkeleton.CScoSkelNode.eVoxelTypeBranch :
            return
        
        for connSegInx in branch.ListConnSegmentIndex :
            if self.m_listSegFlag[connSegInx] == True :
                continue
            self.refine_radius_call_stack(connSegInx, endRadius)
    def start_radius(self, splineSeg : scoSplineSkeleton.CScoSplineSegment, parentRadius : float) :
        listRadius = []
        maskID = scoData.CPatient.find_mask_id(self.m_dataPatientType, splineSeg.Name)

        # 최초 5개를 가지고 온다. 
        for inx in range(0, len(splineSeg.ListRadius)) :
            voxelInx = scoSkeleton.CScoSkel.convert_vec3_to_voxel_index(splineSeg.ListCP[inx])
            dstMaskID = self.tmp_mask.get_voxel(voxelInx)
            if dstMaskID != maskID :
                continue

            radius = splineSeg.get_radius(inx)
            if radius <= parentRadius :
                listRadius.append(radius)
            
            if len(listRadius) >= 5 :
                break

        if len(listRadius) == 0 :
            return parentRadius
        listRadius.sort()

        return listRadius[0]
    def start_radius_root(self, splineSeg : scoSplineSkeleton.CScoSplineSegment, parentRadius : float) :
        # 최초 5개를 가지고 온다.
        listRadius = []
        for inx in range(0, len(splineSeg.ListRadius)) :
            radius = splineSeg.get_radius(inx)
            if radius <= parentRadius :
                listRadius.append(radius)
            
            if len(listRadius) >= 5 :
                break
        
        if len(listRadius) == 0 :
            return self.s_minRadius
        listRadius.sort()

        return listRadius[-1]
    def end_radius(self, splineSeg : scoSplineSkeleton.CScoSplineSegment) :
        # 최초 5개를 가지고 온다. 
        listRadius = []
        for inx in range(-1, -len(splineSeg.ListRadius) - 1, -1) :
            radius = splineSeg.get_radius(inx)
            listRadius.append(radius)
            
            if len(listRadius) >= 5 :
                break
        
        if len(listRadius) == 0 :
            return self.s_minRadius
        listRadius.sort()

        return listRadius[0]

    
    @property
    def SplineSkel(self) :
        return self.m_splineSkel




class CScoSkelVMLabelingWithOps(CScoSkelVMReorder) :
    def __init__(self, skel: scoSkeleton.CScoSkel, patient : scoData.CPatient, dataPatientType : int) -> None:
        super().__init__(skel)
        #input your code
        self.m_patient = patient
        self.m_dataPatientType = dataPatientType
    def process(self, rootNiftiFullPath : str, rootMode : int) :
        super().process(rootNiftiFullPath, rootMode)
        # input your code

        if self.m_dataPatientType == scoData.CDataPatient.eDataPatientType_None :
            print("labeling : patient data type error")
            return

        self.tmp_mask = self.m_patient.get_mask(self.m_dataPatientType)
        for vesselSegment in self.m_skel.ListVesselSeg :
            self.set_labeling_vessel_segment(vesselSegment)
        #self.set_labeling_vessel_segment(self.m_skel.ListVesselSeg[128])
        self.tmp_mask = None
    def clear(self) :
        # input your code 

        super().clear()


    def get_labeling(self, maskInx : int) :
        return scoData.CPatient.get_labeling_name(self.m_dataPatientType, maskInx)
    """
    vessel segment가 어느 mask 영역에 포함되는가?
        - vesselID가 오직 1개만 검출될 경우 labeling 적용 
        - vesselID가 여러개 검출될 경우
            - 숫자가 낮은 vesselID는 무시
            - 그 외는 포함 percentage에 따라 가장 높은것의 labeling을 적용 
    """
    def set_labeling_vessel_segment(self, vesselSegment : scoSkeleton.CScoSkelSegment) :
        # key : mask value
        # value : mask count
        dic = {}

        coordCnt = len(vesselSegment.ListCoord)

        for coordInx in range(0, coordCnt) :
            coord = vesselSegment.ListCoord[coordInx]
            voxelInx = scoSkeleton.CScoSkel.convert_vec3_to_voxel_index(coord)
            voxel = self.tmp_mask.get_voxel(voxelInx)

            if voxel in dic :
                dic[voxel] += 1
            else :
                dic[voxel] = 1

        maskCnt = len(dic)
        retMaskID = -1
        if maskCnt == 0:
            pass
        elif len(dic) == 1 :
            for key, cnt in dic.items() :
                retMaskID = key
        else :
            maxMaskID = -1000
            maxMaskIDCnt = -1000
            # count가 가장 큰 maskID를 선택한다.
            for maskID, cnt in dic.items() :
                if cnt > maxMaskIDCnt :
                    maxMaskID = maskID
                    maxMaskIDCnt = cnt
            retMaskID = maxMaskID
        
        if retMaskID == -1 :
            vesselSegment.Name = ""
        else :
            vesselSegment.Name = self.get_labeling(retMaskID)




