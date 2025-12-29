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
from abc import abstractmethod

import open3d as o3d
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering

from skimage.morphology import skeletonize
# from skimage.morphology import skeletonize, skeletonize_3d
from skimage import data
from skimage.util import invert

import json



class CSkelCenterLine : 
    def __init__(self, jsonFullPath : str, niftiFullPath : str, outputFullPath : str) -> None:
        self.m_jsonFullPath = jsonFullPath
        self.m_niftiFullPath = niftiFullPath
        self.m_outputFullPath = outputFullPath
        self.m_curveSkelPath = ""
        self.m_outputFullPathRaw = ""


    def process(self) :
        with open(self.m_jsonFullPath, "r") as fp :
            self.m_dicMultiLabelingInfo = json.load(fp)

        if self.m_dicMultiLabelingInfo is None :
            print("json 파일을 찾을 수 없습니다.")
            return False
        
        self.m_curveSkelPath = self.m_dicMultiLabelingInfo["CurveSkelPath"]
        self.m_outputFullPathRaw = os.path.join(self.m_outputFullPath, "rawimage")
        scoUtil.CScoUtilOS.create_directory(self.m_outputFullPathRaw)

        terminalCmd = f"rm -f {self.m_outputFullPathRaw}/*.*"
        os.system(terminalCmd)

        self.nifti_to_slice_png(self.m_niftiFullPath, self.m_outputFullPathRaw)

        print("successed extracting png")
        print("*"*30)

        self.create_shell_file(self.m_outputFullPath)
        self.exe_shell_script()
        print("successed extracting skeleton")
        print("*"*30)


    def nifti_to_slice_png(self, niftiFilePath, pngPath) :
        scoUtil.CScoUtilOS.create_directory(pngPath)

        sitkImg = scoUtil.CScoUtilSimpleITK.load_image(niftiFilePath, None)
        npImg = scoUtil.CScoUtilSimpleITK.sitkImg_to_npImg(sitkImg, "uint8")
        npImg[npImg > 0] = 255

        sliceCnt = npImg.shape[0]
        for i in range(0, sliceCnt) :
            fileName = "{0:04d}.png".format(i)
            fullPath = os.path.join(pngPath, fileName)
            cv2.imwrite(fullPath, npImg[i])
    def create_shell_file(self, outputFullPath) :
        '''
        #!/bin/bash
        th=1e-12
        ./curve_skel /Users/scosco/Desktop/scosco/hutom/Project/VesselSegment/Project/CurveSkel/demo_files/OutFileFormat_S1_ArteryMain ${th} 1
        '''
        self.m_curveSkelShellFullPath = os.path.join(outputFullPath, "skeleton.sh")
        with open(self.m_curveSkelShellFullPath, "w") as fp :
            comm = "#!/bin/bash \n\nth=1e-12 \n\n "
            exe = os.path.join(self.m_curveSkelPath, "curve_skel")
            param0 = outputFullPath
            param1 = "${th}"
            param2 = "1"
            skelComm = "{0} {1} {2} {3}\n".format(exe, param0, param1, param2)
            fp.write(comm)
            fp.write(skelComm)
    def exe_shell_script(self) :
        nowWorkDir = os.getcwd()
        os.chdir(os.path.dirname(self.m_curveSkelShellFullPath))
        terminalCmd = "sh skeleton.sh"
        os.system(terminalCmd)
        os.chdir(nowWorkDir)

class CRegionGrowingOnPlane :
    def __init__(self) -> None:
        self.m_listVoxelInx = []
        self.m_th = 1.0

    def init_mask_img(self, npMaskImg : np.ndarray) :
        '''
        npMaskImg
            - order : x, y, z
        '''
        self.m_npMaskImg = npMaskImg
        self.m_npVisit = np.zeros(self.m_npMaskImg.shape, dtype='bool')
    def init_voxel_info(self, voxelInx : tuple, plane : scoMath.CScoPlane) :
        self.m_voxelInx = voxelInx
        self.m_plane = plane

    def process(self, th : float) : 
        self.m_listVoxelInx.clear()
        self.m_th = th

        self.clear_visit()
        self.region_growing(self.m_voxelInx)
    

    def region_growing(self, voxelInx : tuple) :
        tmpQueue = []
        tmpQueue.append(voxelInx)
        self.check_visit(voxelInx, True)

        while True :
            if len(tmpQueue) == 0 :
                break

            voxelInx = tmpQueue.pop(0)
            self.m_listVoxelInx.append(voxelInx)

            xCnt, yCnt, zCnt = self.m_npMaskImg.shape

            for zOffset in range(-1, 2) :
                for yOffset in range(-1, 2) :
                    for xOffset in range(-1, 2) :
                        nowVoxelInx = (voxelInx[0] + xOffset, voxelInx[1] + yOffset, voxelInx[2] + zOffset)

                        if nowVoxelInx[0] < 0 or nowVoxelInx[0] >= xCnt :
                            continue
                        if nowVoxelInx[1] < 0 or nowVoxelInx[1] >= yCnt :
                            continue
                        if nowVoxelInx[2] < 0 or nowVoxelInx[2] >= zCnt :
                            continue

                        if self.m_npMaskImg[nowVoxelInx] == 0 :
                            continue
                        if self.is_visit(nowVoxelInx) == True :
                            continue
                        dist = self.m_plane.get_dist(scoMath.CScoVec3(nowVoxelInx[0], nowVoxelInx[1], nowVoxelInx[2]))
                        if dist > self.m_th :
                            continue
                        
                        tmpQueue.append(nowVoxelInx)
                        self.check_visit(nowVoxelInx, True)

    # visit member 
    def clear_visit(self) :
        self.m_npVisit[:, :, :] = False
    def check_visit(self, voxelInx : tuple, bVisit : bool) :
        self.m_npVisit[voxelInx] = bVisit
    def is_visit(self, voxelInx : tuple) :
        return self.m_npVisit[voxelInx]
    
    @property
    def ListVoxelInx(self) :
        return self.m_listVoxelInx


class CScoSkelNode :
    eVoxelTypeNone = 0
    eVoxelTypeVessel = 1
    eVoxelTypeEndPoint = 2
    eVoxelTypeBranch = 3


    def __init__(self) :
        self.m_type = CScoSkelNode.eVoxelTypeNone
        self.m_name = ""
        self.m_dbgPCD = None
    def clear(self) :
        self.m_type = CScoSkelNode.eVoxelTypeNone
        self.m_name = ""
        if self.m_dbgPCD is not None :
            self.m_dbgPCD = None

    def clone(self) :
        cloneInst = CScoSkelNode()
        self._clone(cloneInst)
        return cloneInst
    

    # protected
    def _clone(self, cloneInst) :
        cloneInst.m_type = self.m_type
        cloneInst.m_name = self.m_name
        cloneInst.m_dbgPCD = None


    @property
    def Type(self) :
        return self.m_type
    @property
    def Name(self) :
        return self.m_name
    @Name.setter
    def Name(self, name) :
        self.m_name = name
    @property
    def DBGPCD(self) :
        return self.m_dbgPCD
    @DBGPCD.setter
    def DBGPCD(self, pcd) :
        self.m_dbgPCD = pcd


class CScoSkelEndPoint(CScoSkelNode) :
    '''
    - m_coord
        - CScoVec3, order : x, y, z
    '''
    def __init__(self):
        super().__init__()
        self.m_type = CScoSkelNode.eVoxelTypeEndPoint
        self.m_coord = scoMath.CScoVec3(0, 0, 0)
        self.m_connSegInx = -1
        self.m_valid = False
    def clear(self) :
        self.m_coord = scoMath.CScoVec3(0, 0, 0)
        self.m_connSegInx = -1
        self.m_valid = False
        super().clear()


    def clone(self) :
        cloneInst = CScoSkelEndPoint()
        self._clone(cloneInst)
        return cloneInst
    

    # protected
    def _clone(self, cloneInst) :
        super()._clone(cloneInst)
        cloneInst.m_coord = self.m_coord.clone()
        cloneInst.m_connSegInx = self.m_connSegInx
        cloneInst.m_valid = self.m_valid


    @property
    def Coord(self) :
        return self.m_coord
    @Coord.setter
    def Coord(self, coord) :
        self.m_coord = coord
    @property
    def Valid(self) :
        return self.m_valid
    @Valid.setter
    def Valid(self, valid) :
        self.m_valid = valid
    @property
    def ConnSegInx(self) :
        return self.m_connSegInx
    @ConnSegInx.setter
    def ConnSegInx(self, connSegInx) :
        self.m_connSegInx = connSegInx
        if connSegInx >= 0 :
            self.Valid = True
    

    def dbg_process(self, radius : float, color : tuple) :
        listVec3 = [
            self.Coord
        ]
        pcd = scoRenderObj.CRenderObj.convert_scovec3_to_pcd(listVec3, color)
        geometries = o3d.geometry.TriangleMesh()

        for point in pcd.points:
            sphere = o3d.geometry.TriangleMesh.create_sphere(radius=radius) #create a small sphere to represent point
            sphere.translate(point)
            geometries += sphere

        geometries.paint_uniform_color(color)
        self.DBGPCD = geometries

class CScoSkelBranch(CScoSkelNode) :
    '''
    - m_listBranchCoord
        - CScoVec3, order : x, y, z
    - m_listConnSegmentIndex 
        - connected segment index 
    '''
    def __init__(self) :
        super().__init__()
        self.m_type = CScoSkelNode.eVoxelTypeBranch
        self.m_listBranchCoord = []
        self.m_listConnSegmentInx = []
    def clear(self) :
        self.clear_branch_coord()
        super().clear()

    def clone(self) :
        cloneInst = CScoSkelBranch()
        self._clone(cloneInst)
        return cloneInst


    def add_branch_coord(self, branchCoord : scoMath.CScoVec3) :
        self.m_listBranchCoord.append(branchCoord)
    def add_branch_coord_list(self, listBranchCoord : list) :
        self.m_listBranchCoord += listBranchCoord
    def get_branch_coord(self, inx : int) -> scoMath.CScoVec3 :
        return self.m_listBranchCoord[inx]
    def get_branch_coord_index(self, branchCoord : scoMath.CScoVec3) -> int :
        for inx, coord in enumerate(self.m_listBranchCoord) :
            if scoMath.CScoMath.equal_vec3(coord, branchCoord) == True :
                return inx
        return -1
    def in_branch_coord(self, branchCoord : scoMath.CScoVec3) -> bool:
        for coord in self.m_listBranchCoord :
            if scoMath.CScoMath.equal_vec3(coord, branchCoord) == True :
                return True
        return False
    def clear_branch_coord(self) :
        self.m_listBranchCoord.clear()
        self.m_listConnSegmentInx.clear()


    def add_conn_seg_inx(self, segInx : int) :
        self.m_listConnSegmentInx.append(segInx)
    def add_conn_seg_inx_list(self, listSegInx : list) :
        self.m_listConnSegmentInx += listSegInx
    def get_conn_seg_inx(self, inx : int) -> int :
        return self.m_listConnSegmentInx[inx]
    def in_conn_seg_inx(self, segInx : int) -> bool :
        return segInx in self.m_listConnSegmentInx
    def remove_conn_seg_inx(self, segInx : int) :
        if self.in_conn_seg_inx(segInx) == True :
            self.m_listConnSegmentInx.remove(segInx)
    
    def get_real_branch_coord(self) -> scoMath.CScoVec3 :
        """
        return : (x, y, slice) 
                 branch group을 대표하는 coord 
                 현재는 평균값을 의미하며
        """
        iCnt = len(self.ListBranchCoord)
        if iCnt == 0 :
            return (0, 0, 0)
        npArray = scoMath.CScoMath.convert_vec_to_np(self.ListBranchCoord)
        npRet = np.mean(npArray, axis=0)
        
        return scoMath.CScoVec3(npRet[0], npRet[1], npRet[2])
    

    # protected
    def _clone(self, cloneInst) :
        super()._clone(cloneInst)

        for branchCoord in self.m_listBranchCoord :
            cloneBranchCoord = branchCoord.clone()
            cloneInst.add_branch_coord(cloneBranchCoord)
        for connSegmentInx in self.m_listConnSegmentInx :
            cloneInst.add_conn_seg_inx(connSegmentInx)
    


    @property
    def ListBranchCoord(self) :
        return self.m_listBranchCoord
    @property
    def ListConnSegmentIndex(self) :
        return self.m_listConnSegmentInx
    @property
    def BranchCount(self) :
        return len(self.m_listBranchCoord)
    @property
    def ConnSegInxCount(self) :
        return len(self.m_listConnSegmentInx)
    @property
    def DBGLabel(self) :
        label = ""

        for connVesselSegInx in self.ListConnSegmentIndex :
            label += f"_{connVesselSegInx}"
        
        return label
    

    def dbg_process(self, color : tuple) :
        self.DBGPCD = scoRenderObj.CRenderObj.convert_scovec3_to_pcd(self.m_listBranchCoord, color)
    

class CScoSkelSegment(CScoSkelNode) :
    '''
    - m_listBranchCoord
        - CScoVec3, order : x, y, z

    - 연결된 노드를 인덱스로 관리
        - first branch index
        - second branch index
        - endpoint index
        - segType 
            - 0 : None
            - 1 : DistalType
                - branch0 index : valid
                - endpoint0 index : valid
                - branch1 index : -1
            - 2 : ConnectedType
                - branch0 index : valid
                - branch1 index : valid
                - endpoint0 index : -1
            - 3 : DisconnectedType
                - endpoint0 index
                - endpoint1 index

    - re-order
        - reverse listCoord
        - exchange first and second if ConnectedType
    - add spline curve
    '''

    eSegmentType_None = 0
    eSegmentType_Distal = 1
    eSegmentType_Connection = 2
    eSegmentType_Disconnected = 3


    def __init__(self) :
        super().__init__()
        self.m_type = CScoSkelNode.eVoxelTypeVessel
        self.m_segmentType = CScoSkelSegment.eSegmentType_None
        self.m_listCoord = []
        self.m_listBranchInx = []
        self.m_listEndPointInx = []
        self.m_listConnVoxelType = []
    def clear(self) :
        self.m_listCoord.clear()
        self.m_listBranchInx.clear()
        self.m_listEndPointInx.clear()
        self.m_listConnVoxelType.clear()
        self.m_segmentType = CScoSkelSegment.eSegmentType_None
        super().clear()
    

    def add_coord(self, coord : scoMath.CScoVec3) :
        self.m_listCoord.append(coord)
    def add_coord_list(self, listCoord : list) :
        self.m_listCoord += listCoord
    def get_coord(self, inx : int) -> scoMath.CScoVec3 :
        return self.m_listCoord[inx]
    def in_coord(self, v : scoMath.CScoVec3) -> bool:
        for coord in self.m_listCoord :
            if scoMath.CScoMath.equal_vec3(v, coord) == True :
                return True
        return False
    def get_end_point(self) -> list:
        """
        desc : 해당 segment의 양 끝점을 list type으로 리턴한다
               만약 segment의 길이가 2 이상이 아니라면 None이 리턴된다.
        ret : [firstCoord, endCoord] or
              [first-end Coord] or
              None
        """
        if self.CoordCount == 0 :
            return None
        elif self.CoordCount == 1 :
            return [self.m_listCoord[0]]

        return [self.m_listCoord[0], self.m_listCoord[-1]]
    def get_center_coord(self) -> scoMath.CScoVec3 :
        inx = int(self.CoordCount * 0.5)
        return self.m_listCoord[inx]
    
    def add_branch_inx(self, branchInx : int) :
        self.m_listBranchInx.append(branchInx)
        self.m_listConnVoxelType.append(CScoSkelNode.eVoxelTypeBranch)
        self.check_segment_type()
    def get_branch_inx(self, inx : int) -> int :
        return self.m_listBranchInx[inx]
    
    def add_endpoint_inx(self, endPointInx : int) :
        self.m_listEndPointInx.append(endPointInx)
        self.m_listConnVoxelType.append(CScoSkelNode.eVoxelTypeEndPoint)
        self.check_segment_type()
    def get_endpoint_inx(self, inx : int) -> int :
        return self.m_listEndPointInx[inx]
    
    def get_conn_voxel_type(self, inx : int) -> int :
        return self.m_listConnVoxelType[inx]
    
    def check_segment_type(self) :
        if self.BranchInxCount == 2 and self.EndPointInxCount == 0 :
            self.m_segmentType = self.eSegmentType_Connection
        elif self.BranchInxCount == 1 and self.EndPointInxCount == 1 :
            self.m_segmentType = self.eSegmentType_Distal
        elif self.BranchInxCount == 0 and self.EndPointInxCount == 2 :
            self.m_segmentType = self.eSegmentType_Disconnected
        else :
            self.m_segmentType = self.eSegmentType_None
    
    def reorder(self) :
        self.m_listCoord.reverse()
        self.m_listConnVoxelType.reverse()

        if self.BranchInxCount == 2 :
            self.m_listBranchInx.reverse()
        elif self.EndPointInxCount == 2 :
            self.m_listEndPointInx.reverse()

    def dbg_process(self, color : tuple) :
        self.DBGPCD = scoRenderObj.CRenderObj.convert_scovec3_to_pcd(self.ListCoord, color)

    
    @property
    def SegmentType(self) :
        return self.m_segmentType
    @property
    def ListCoord(self) :
        return self.m_listCoord
    @property
    def CoordCount(self) :
        return len(self.m_listCoord)
    @property
    def BranchInxCount(self) :
        return len(self.m_listBranchInx)
    @property
    def EndPointInxCount(self) :
        return len(self.m_listEndPointInx)
    @property
    def ConnVoxelTypeCount(self) :
        return len(self.m_listConnVoxelType)
    @property
    def DBGLabel(self) :
        label = f"({self.CoordCount})"

        for branchInx in self.m_listBranchInx :
            label += f"_B{branchInx}"
        for endInx in self.m_listEndPointInx :
            label += f"_E{endInx}"
        
        return label




class CScoSkel :
    eSkelType_none = 0
    eSkelType_skel = 1
    eSkelType_skimage = 2
    eSkelType_kimimaro = 3

    @staticmethod
    def convert_vec3_to_voxel_index(v : scoMath.CScoVec3) -> tuple :
        return (int(v.X + 0.5), int(v.Y + 0.5), int(v.Z + 0.5))
    @staticmethod
    def convert_voxel_index_to_vec3(voxelInx : tuple) -> scoMath.CScoVec3 :
        return scoMath.CScoVec3(voxelInx[0], voxelInx[1], voxelInx[2])
    @staticmethod
    def convert_voxel_index_list_to_vec3_list(listVoxelInx : list) -> scoMath.CScoVec3 :
        retList = []

        for voxelInx in listVoxelInx :
            v = CScoSkel.convert_voxel_index_to_vec3(voxelInx)
            retList.append(v)
        return retList
    

    def __init__(self) :
        self.m_type = self.eSkelType_none
        self.m_sitkImg = None           # x, y, z
        self.m_npImg = None             # x, y, z to (2, 1, 0)
        self.m_npVoxelType = None       # x, y, z to (2, 1, 0)
        self.m_npVisitedVoxel = None    # x, y, z to (2, 1, 0)
        self.m_skeletonPCD = None
        
        self.m_listCandidateBranchPt = []
        self.m_listCandidateConnCnt = []
        self.m_listCandidateBranchSegConn = []

        self.m_listSkeletonCoord = []   # list(CScoVec3, ..)
        self.m_listBranchGroup = []     # list(CScoSkelBranch, ..)
        self.m_listVesselSeg = []       # list(CScoSkelSegment, ..)
        self.m_listEndPoint = []        # list(CScoSkelEndPoint, ..)

        self.m_regionGrowing = CRegionGrowingOnPlane()
        self.m_matPhysical = scoMath.CScoMat4()
    def clear(self) :
        self.m_type = self.eSkelType_none
        self.m_sitkImg = None
        self.m_npImg = None
        self.m_npVoxelType = None
        self.m_npVisitedVoxel = None
        self.m_skeletonPCD = None

        self.m_listCandidateBranchPt.clear()
        self.m_listCandidateConnCnt.clear()
        self.m_listCandidateBranchSegConn.clear()

        self.m_listSkeletonCoord.clear()
        self.m_listBranchGroup.clear()
        self.m_listVesselSeg.clear()
        self.m_listEndPoint.clear()

        self.m_matPhysical.identity()


    def process_with_skel(self, niftiFullPath : str, skeletonFullPath : str) :
        self.m_type = self.eSkelType_skel
        self.m_sitkImg = scoUtil.CScoUtilSimpleITK.load_image(niftiFullPath, None)
        self.m_npMaskImg = scoUtil.CScoUtilSimpleITK.sitkImg_to_npImg(self.m_sitkImg, "uint8").transpose((2, 1, 0))  # order : x, y, z
        self.m_npImg = np.zeros(self.m_npMaskImg.shape, dtype='uint8')
        self.m_npVoxelType = np.zeros(self.m_npMaskImg.shape, dtype='uint8')
        self.m_npVisitedVoxel = np.zeros(self.m_npMaskImg.shape, dtype='bool')

        xCnt = self.m_npImg.shape[0]
        yCnt = self.m_npImg.shape[1]
        zCnt = self.m_npImg.shape[2]
        self.m_listSkeletonCoord, xInx, yInx, zInx = self.get_coord_from_skel_txt(skeletonFullPath, xCnt, yCnt, zCnt)
        self.m_npImg[(xInx, yInx, zInx)] = 1
        self.m_npVoxelType[(xInx, yInx, zInx)] = CScoSkelNode.eVoxelTypeVessel

        # classify voxel type
        self.process_classify_voxel_type()
        # create branch group
        self.process_make_branch_group()
        # find the segmentation coord list
        self.process_extraction_segment()
        self.connect_branch_and_vessel()
        self.connect_endpoint_and_vessel()
        self.process_physical_matrix()
        # render pcd 
        #self.dbg_pcd_render()
        self.dbg_process()
    def process_with_skimage(self, niftiFullPath : str) :
        self.m_type = self.eSkelType_skimage
        self.m_sitkImg = scoUtil.CScoUtilSimpleITK.load_image(niftiFullPath, None)
        self.m_npMaskImg = scoUtil.CScoUtilSimpleITK.sitkImg_to_npImg(self.m_sitkImg, "uint8").transpose((2, 1, 0))  # order : x, y, z
        self.m_npImg = np.zeros(self.m_npMaskImg.shape, dtype='uint8')
        self.m_npVoxelType = np.zeros(self.m_npMaskImg.shape, dtype='uint8')
        self.m_npVisitedVoxel = np.zeros(self.m_npMaskImg.shape, dtype='bool')

        xCnt = self.m_npImg.shape[0]
        yCnt = self.m_npImg.shape[1]
        zCnt = self.m_npImg.shape[2]
        skeleton = skeletonize(self.m_npMaskImg)
        shape = skeleton.shape
        # added 1 voxel padding
        skeleton[0, :, :] = 0
        skeleton[shape[0] - 1, :, :] = 0
        skeleton[:, 0, :] = 0
        skeleton[:, shape[1] - 1, :] = 0
        skeleton[:, :, 0] = 0
        skeleton[:, :, shape[2] - 1] = 0

        tmpCoord = np.array(np.where(skeleton > 0)).T
        self.m_listSkeletonCoord = []
        xInx = []
        yInx = []
        zInx = []
        for inx in range(0, tmpCoord.shape[0]) :
            x = tmpCoord[inx][0]
            y = tmpCoord[inx][1]
            z = tmpCoord[inx][2]
            self.m_listSkeletonCoord.append(scoMath.CScoVec3(x, y, z))
            xInx.append(x)
            yInx.append(y)
            zInx.append(z)
        
        self.m_npImg[(xInx, yInx, zInx)] = 1
        self.m_npVoxelType[(xInx, yInx, zInx)] = CScoSkelNode.eVoxelTypeVessel

        # classify voxel type
        self.process_classify_voxel_type()
        # create branch group
        self.process_make_branch_group()
        # find the segmentation coord list
        self.process_extraction_segment()
        self.connect_branch_and_vessel()
        self.connect_endpoint_and_vessel()
        self.process_physical_matrix()
        # render pcd 
        #self.dbg_pcd_render()
        self.dbg_process()
    def process_with_kimimaro(self, niftiFullPath : str) :
        self.m_type = self.eSkelType_kimimaro
        self.m_sitkImg = scoUtil.CScoUtilSimpleITK.load_image(niftiFullPath, None)
        self.m_npMaskImg = scoUtil.CScoUtilSimpleITK.sitkImg_to_npImg(self.m_sitkImg, "uint8").transpose((2, 1, 0))  # order : x, y, z
        self.m_npImg = np.zeros(self.m_npMaskImg.shape, dtype='uint8')
        self.m_npVoxelType = np.zeros(self.m_npMaskImg.shape, dtype='uint8')
        self.m_npVisitedVoxel = np.zeros(self.m_npMaskImg.shape, dtype='bool')

        xCnt = self.m_npImg.shape[0]
        yCnt = self.m_npImg.shape[1]
        zCnt = self.m_npImg.shape[2]
        skeleton = skeletonize(self.m_npMaskImg)
        shape = skeleton.shape
        # added 1 voxel padding
        skeleton[0, :, :] = 0
        skeleton[shape[0] - 1, :, :] = 0
        skeleton[:, 0, :] = 0
        skeleton[:, shape[1] - 1, :] = 0
        skeleton[:, :, 0] = 0
        skeleton[:, :, shape[2] - 1] = 0

        tmpCoord = np.array(np.where(skeleton > 0)).T
        self.m_listSkeletonCoord = []
        xInx = []
        yInx = []
        zInx = []
        for inx in range(0, tmpCoord.shape[0]) :
            x = tmpCoord[inx][0]
            y = tmpCoord[inx][1]
            z = tmpCoord[inx][2]
            self.m_listSkeletonCoord.append(scoMath.CScoVec3(x, y, z))
            xInx.append(x)
            yInx.append(y)
            zInx.append(z)
        
        self.m_npImg[(xInx, yInx, zInx)] = 1
        self.m_npVoxelType[(xInx, yInx, zInx)] = CScoSkelNode.eVoxelTypeVessel

        # classify voxel type
        self.process_classify_voxel_type()
        # create branch group
        self.process_make_branch_group()
        # find the segmentation coord list
        self.process_extraction_segment()
        self.connect_branch_and_vessel()
        self.connect_endpoint_and_vessel()
        self.process_physical_matrix()
        # render pcd 
        #self.dbg_pcd_render()
        self.dbg_process()


    def process_classify_voxel_type(self) :
        self.m_listCandidateBranchPt.clear()
        self.m_listCandidateConnCnt.clear()
        for coord in self.m_listSkeletonCoord :
            voxelInx = self.convert_vec3_to_voxel_index(coord)
            connCnt = self.get_conn(self.m_npImg, voxelInx)
            # Branch
            if connCnt > 2 :
                self.m_listCandidateBranchPt.append(coord)
                self.m_listCandidateConnCnt.append(connCnt)
                self.m_npVoxelType[voxelInx] = CScoSkelNode.eVoxelTypeBranch
            # EndPoint
            elif connCnt == 1 :
                endPoint = CScoSkelEndPoint()
                endPoint.Coord = coord
                self.m_listEndPoint.append(endPoint)
                self.m_npVoxelType[voxelInx] = CScoSkelNode.eVoxelTypeEndPoint
    def process_make_branch_group(self) :
        self.clear_visit()
        for candidateBranchPt in self.m_listCandidateBranchPt :
            voxelInx = self.convert_vec3_to_voxel_index(candidateBranchPt)
            if self.is_visited(voxelInx) == True :
                continue

            # 현재 branch coord를 방문함
            retListBranchVoxelInx = self.process_make_branch_group_with_coord(voxelInx)
            retListConnSegVoxelInx = self.process_find_branch_group_conn_seg(retListBranchVoxelInx)
            branch = CScoSkelBranch()
            # 1:1 대응
            self.m_listBranchGroup.append(branch)
            self.m_listCandidateBranchSegConn.append(retListConnSegVoxelInx)

            branch.add_branch_coord_list(self.convert_voxel_index_list_to_vec3_list(retListBranchVoxelInx))
        
        self.m_listCandidateBranchPt.clear()
    def process_make_branch_group_with_coord(self, voxelInx : tuple) -> list :
        retListBranchGroup = []

        self.m_npVisitedVoxel[voxelInx] = True
        retListBranchGroup.append(voxelInx)

        listTmp = self.get_conn_coord_with_candidate_branch(self.m_npVoxelType, voxelInx)
        print("check callstack")

        # child 
        for childVoxelInx in listTmp :
            if self.is_visited(childVoxelInx) == False and self.is_coord_type(childVoxelInx, CScoSkelNode.eVoxelTypeBranch) == True :
                retListBranchGroup += self.process_make_branch_group_with_coord(childVoxelInx)
        
        return retListBranchGroup
    def process_find_branch_group_conn_seg(self, listBranchVoxelInx : list) -> list:
        retList = []

        for branchVoxelInx in listBranchVoxelInx :
            segVoxelInxList = self.get_conn_coord_with_seg_vessel(self.m_npVoxelType, branchVoxelInx)
            for segVoxelInx in segVoxelInxList :
                # 중복이 될 수 있으므로 한번 더 check 해야 된다. 
                if segVoxelInx not in retList :
                    retList.append(segVoxelInx)
        return retList
    
    def process_extraction_segment(self) :
        self.clear_visit()
        self.check_visit_end_point()
        self.check_visit_branch_group()

        # endpoint 기반 segment 추출
        # 만약 endPoint만 있다면 해당 endPoint를 무효화 시킨다. 
        for endPointInx, endPoint in enumerate(self.m_listEndPoint) :
            retListSegVoxelInx = self.process_segmentation_tracking(self.convert_vec3_to_voxel_index(endPoint.Coord))
            if len(retListSegVoxelInx) > 0 :
                segVessel = CScoSkelSegment()
                segVessel.add_coord_list(self.convert_voxel_index_list_to_vec3_list(retListSegVoxelInx))
                self.m_listVesselSeg.append(segVessel)

                # conn
                segVesselInx = len(self.m_listVesselSeg) - 1
                segVessel.add_endpoint_inx(endPointInx)
                endPoint.ConnSegInx = segVesselInx
        # branch group 기반 segment 추출
        for branchInx, branch in enumerate(self.m_listBranchGroup) :
            listConnSegVoxelInx = self.m_listCandidateBranchSegConn[branchInx]
            for connSegVoxelInx in listConnSegVoxelInx :
                if self.is_visited(connSegVoxelInx) == False :
                    retListSegVoxelInx = []
                    retListSegVoxelInx.append(connSegVoxelInx)
                    retListSegVoxelInx += self.process_segmentation_tracking(connSegVoxelInx)

                    segVessel = CScoSkelSegment()
                    segVessel.add_coord_list(self.convert_voxel_index_list_to_vec3_list(retListSegVoxelInx))
                    self.m_listVesselSeg.append(segVessel)
        
    def process_segmentation_tracking(self, voxelInx : tuple) :
        retList = []
        while True :
            self.m_npVisitedVoxel[voxelInx] = True
            listVoxelInx = self.process_segmentation_tracking_with_coord(voxelInx)

            # segment가 끝났음을 의미한다.
            if len(listVoxelInx) == 0 :
                break
            else :
                retList += listVoxelInx

            voxelInx = listVoxelInx[0]
        
        return retList
    def process_segmentation_tracking_with_coord(self, voxelInx : tuple) :
        
        listVoxelInx = self.get_conn_coord_with_vessel(self.m_npVoxelType, voxelInx)
        retListVoxelInx = []

        # 대상으로 voxelInx에서 vessel type만 추출한다.
        for voxelInx in listVoxelInx :
            if self.m_npVisitedVoxel[voxelInx] == True :
                continue

            voxelType = self.m_npVoxelType[voxelInx]
            # 조건문이 거짓이라면 무언가가 잘못 된 것이다. 
            assert(voxelType == CScoSkelNode.eVoxelTypeVessel), "segment vessel 추출 중 무언가가 잘못되었다."
            if voxelType == CScoSkelNode.eVoxelTypeVessel :
                retListVoxelInx.append(voxelInx)
        
        return retListVoxelInx
    def connect_branch_and_vessel(self) :
        for branchInx, branch in enumerate(self.m_listBranchGroup) :
            listConnVesselSeg = self.m_listCandidateBranchSegConn[branchInx]

            for connVesselSegVoxelInx in listConnVesselSeg :
                vesselSegInx = self.find_vessel_segment(connVesselSegVoxelInx)
                vesselSeg = self.m_listVesselSeg[vesselSegInx]
                if vesselSegInx >= 0 :
                    branch.add_conn_seg_inx(vesselSegInx)
                    vesselSeg.add_branch_inx(branchInx)
        
        self.m_listCandidateBranchSegConn.clear()
        self.m_listCandidateConnCnt.clear()
    def connect_endpoint_and_vessel(self) :
        for endPointInx, endPoint in enumerate(self.m_listEndPoint) :
            if endPoint.Valid == True :
                continue

            voxelInx = self.convert_vec3_to_voxel_index(endPoint.Coord)
            listVesselVoxelInx = self.get_conn_coord_with_seg_vessel(self.m_npVoxelType, voxelInx)
            iCnt = len(listVesselVoxelInx)

            if iCnt != 1 :
                continue

            vesselSegInx = self.find_vessel_segment(listVesselVoxelInx[0])
            if vesselSegInx == -1 :
                continue

            vesselSeg = self.m_listVesselSeg[vesselSegInx]
            vesselSeg.add_endpoint_inx(endPointInx)
            endPoint.ConnSegInx = vesselSegInx
    def process_physical_matrix(self) :
        spacing = self.m_sitkImg.GetSpacing()
        direction = self.m_sitkImg.GetDirection()
        origin = self.m_sitkImg.GetOrigin()
        self.m_matPhysical = scoMath.CScoMath.get_mat_with_spacing_direction_origin(spacing, direction, origin)

    # get member 
    def get_branch_group_inx(self, node : CScoSkelNode) :
        return self.ListBranchGroup.index(node)
    def get_end_point_inx(self, node : CScoSkelNode) :
        return self.ListEndPoint.index(node)
    def get_vessel_seg_inx(self, node : CScoSkelNode) :
        return self.ListVesselSeg.index(node)
    def get_vessel_seg_point(self, vesselSegInx : int, vesselSegSubInx : int) -> scoMath.CScoVec3 :
        vesselSegment = self.m_listVesselSeg[vesselSegInx]
        return vesselSegment.get_coord(vesselSegSubInx)
    def get_adjacent_point(self, vesselSegInx : int, vesselSegSubInx : int) -> list :
        vesselSeg = self.m_listVesselSeg[vesselSegInx]
        totalCnt = vesselSeg.CoordCount
        listP = []

        # 5-point extraction
        if totalCnt > 1 :
            for tmpInx in range(vesselSegSubInx - 2, vesselSegSubInx + 3) :
                tmpInx = max(0, tmpInx)
                tmpInx = min(totalCnt - 1, tmpInx)
                coord = vesselSeg.get_coord(tmpInx)
                listP.append(coord)
            return listP
        
        coord = vesselSeg.get_coord(0)
        # 1-point extraction
        #   - branch - vessel - branch
        #   - branch - vessel - endPoint
        if vesselSeg.SegmentType == CScoSkelSegment.eSegmentType_Connection :
            branchInx0 = vesselSeg.get_branch_inx(0)
            branchInx1 = vesselSeg.get_branch_inx(1)
            branch0 = self.m_listBranchGroup[branchInx0]
            branch1 = self.m_listBranchGroup[branchInx1]
            b0 = branch0.get_real_branch_coord()
            b1 = branch1.get_real_branch_coord()
            listP.append(b0)
            listP.append(b0)
            listP.append(coord)
            listP.append(b1)
            listP.append(b1)
        elif vesselSeg.SegmentType == CScoSkelSegment.eSegmentType_Distal :
            branchInx = vesselSeg.get_branch_inx(0)
            branch = self.m_listBranchGroup[branchInx]
            endPointInx = vesselSeg.get_endpoint_inx(0)
            endPoint = self.m_listEndPoint[endPointInx]
            p0 = branch.get_real_branch_coord()
            p1 = endPoint.Coord
            listP.append(p0)
            listP.append(p0)
            listP.append(coord)
            listP.append(p1)
            listP.append(p1)
        elif vesselSeg.SegmentType == CScoSkelSegment.eSegmentType_Disconnected :
            endPointInx0 = vesselSeg.get_endpoint_inx(0)
            endPoint0 = self.m_listEndPoint[endPointInx0]
            endPointInx1 = vesselSeg.get_endpoint_inx(1)
            endPoint1 = self.m_listEndPoint[endPointInx1]
            p0 = endPoint0.Coord
            p1 = endPoint1.Coord
            listP.append(p0)
            listP.append(p0)
            listP.append(coord)
            listP.append(p1)
            listP.append(p1)
            
        return listP
    def get_plane(self, vesselSegInx : int, vesselSegSubInx : int) -> scoMath.CScoPlane :
        listP = self.get_adjacent_point(vesselSegInx, vesselSegSubInx)
        
        startU = listP[0].subtract(listP[1])
        #startU = listP[1].subtract(listP[0])
        endU = listP[4].subtract(listP[3])
        spline = scoMath.CScoSpline()
        spline.add_cp(listP[1])
        spline.add_cp(listP[2])
        spline.add_cp(listP[3])
        spline.process_U(startU, endU)

        p0 = spline.get_point(0.9)
        p1 = spline.get_point(1.0)
        p2 = spline.get_point(1.1)

        dir0 = p1.subtract(p0)
        dir1 = p2.subtract(p1)
        view = p1.add(dir0.add(dir1))
        normal = view.subtract(p1).normalize()

        plane = scoMath.CScoPlane()
        plane.m_point = p1.clone()
        plane.m_normal = normal.clone()
        plane.m_d =  -p1.dot(plane.Normal)

        return plane
    def get_voxelInx_on_plane(self, vesselSegInx : int, vesselSegSubInx : int, rangeDist : float) -> tuple :
        pt = self.get_vessel_seg_point(vesselSegInx, vesselSegSubInx)
        plane = self.get_plane(vesselSegInx, vesselSegSubInx)

        self.m_regionGrowing.init_mask_img(self.MaskImg)
        self.m_regionGrowing.init_voxel_info(self.convert_vec3_to_voxel_index(pt), plane)
        self.m_regionGrowing.process(rangeDist)
        
        return (plane, self.m_regionGrowing.ListVoxelInx)
    def get_radius(self, vesselInx : int, vesselSubInx : int) :
        circleFitting = scoMath.CCircleFitting()
        plane, listVoxelInx = self.get_voxelInx_on_plane(vesselInx, vesselSubInx, 0.5)
        radius = circleFitting.process(plane, listVoxelInx)
        return (plane, radius)
    def get_physical_radius(self, vesselInx : int, vesselSubInx : int) :
        plane, radius = self.get_radius(vesselInx, vesselSubInx)
        phyPlane = scoMath.CScoMath.transform_plane(plane, self.MatPhysical)
        matPlane = scoMath.CScoMath.get_plane_mat(plane)
        center = plane.Point
        p0 = center.add(scoMath.CScoMath.mul_vec3_scalar(matPlane.get_x_axis(), radius))
        p1 = center.add(scoMath.CScoMath.mul_vec3_scalar(matPlane.get_y_axis(), radius))

        phyCenter = scoMath.CScoMath.mul_mat4_vec3(self.MatPhysical, center)
        phyP0 = scoMath.CScoMath.mul_mat4_vec3(self.MatPhysical, p0)
        phyP1 = scoMath.CScoMath.mul_mat4_vec3(self.MatPhysical, p1)
        phyCenter = scoMath.CScoVec3(phyCenter.X, phyCenter.Y, phyCenter.Z)
        phyP0 = scoMath.CScoVec3(phyP0.X, phyP0.Y, phyP0.Z)
        phyP1 = scoMath.CScoVec3(phyP1.X, phyP1.Y, phyP1.Z)

        radius0 = (phyP0.subtract(phyCenter)).length()
        radius1 = (phyP1.subtract(phyCenter)).length()
        return (phyPlane, (radius0 + radius1) / 2.0)
    def get_radius_from_physical(self, vesselInx : int, vesselSubInx : int, phyRadius : float) :
        plane = self.get_plane(vesselInx, vesselSubInx)
        phyPlane = scoMath.CScoMath.transform_plane(plane, self.MatPhysical)

        matPhyPlane = scoMath.CScoMath.get_plane_mat(phyPlane)

        center = phyPlane.Point
        p0 = center.add(scoMath.CScoMath.mul_vec3_scalar(matPhyPlane.get_x_axis(), phyRadius))
        p1 = center.add(scoMath.CScoMath.mul_vec3_scalar(matPhyPlane.get_y_axis(), phyRadius))

        matInvPhysical = self.MatPhysical.inverse()
        center = scoMath.CScoMath.mul_mat4_vec3(matInvPhysical, center)
        p0 = scoMath.CScoMath.mul_mat4_vec3(matInvPhysical, p0)
        p1 = scoMath.CScoMath.mul_mat4_vec3(matInvPhysical, p1)
        center = scoMath.CScoVec3(center.X, center.Y, center.Z)
        p0 = scoMath.CScoVec3(p0.X, p0.Y, p0.Z)
        p1 = scoMath.CScoVec3(p1.X, p1.Y, p1.Z)

        radius0 = (p0.subtract(center)).length()
        radius1 = (p1.subtract(center)).length()
        return (plane, (radius0 + radius1) / 2.0)


    @property
    def MaskImg(self) :
        return self.m_npMaskImg
    @property
    def SitkImg(self) :
        return self.m_sitkImg
    @property
    def MatPhysical(self) :
        return self.m_matPhysical
    @property
    def ListBranchGroup(self) :
        return self.m_listBranchGroup
    @property
    def BranchGroupCount(self) :
        return len(self.m_listBranchGroup)
    @property
    def ListVesselSeg(self) :
        return self.m_listVesselSeg
    @property
    def VesselSegCount(self) :
        return len(self.m_listVesselSeg)
    @property
    def ListEndPoint(self) :
        return self.m_listEndPoint
    @property
    def EndPointCount(self) :
        return len(self.m_listEndPoint)
    


    # protected 
    def voxel_index_to_xyz(self, voxelIndex, xCnt, yCnt) :

        tmpIndex = voxelIndex

        z = int(tmpIndex / (xCnt * yCnt))
        tmpIndex -= int(z * (yCnt * xCnt))
        y = int(tmpIndex / xCnt)
        tmpIndex -= int(y * xCnt)
        x = tmpIndex

        return (x, y, z)
    def get_coord_from_skel_txt(self, txtFilePath, xCnt, yCnt, zCnt) -> tuple:
        '''
        ret : (list<CScoVec3), listXInx, listYInx, listZInx)
        '''

        fp = open(txtFilePath, "r")
        data = fp.readlines()
        fp.close()

        dataList = data[0].split(" ")
        listCoord = []
        listXInx = []
        listYInx = []
        listZInx = []

        for strData in dataList :
            num = int(strData)
            if num != -1 :
                x, y, z = self.voxel_index_to_xyz(num, xCnt, yCnt)

                # 1 voxel padding
                if x > 0 and x < xCnt - 1 :
                    if y > 0 and y < yCnt - 1 :
                        if z > 0 and z < zCnt - 1 :
                            listXInx.append(x)
                            listYInx.append(y)
                            listZInx.append(z)
                            listCoord.append(scoMath.CScoVec3(x, y, z))
        return (listCoord, listXInx, listYInx, listZInx)
    

    def extract_coord(self, listVoxelInx : list, voxelInx : tuple) :
        coordTmp = np.array(
            [
                voxelInx,
                [-1, -1, -1],
                [0, 0, 0]
            ],
            dtype="int32"
        )

        retListCoord = []
        for tmp in listVoxelInx :
            coordTmp[2] = np.array(tmp)
            coord = np.sum(coordTmp, axis = 0)
            retListCoord.append(tuple(coord))

        return retListCoord
    def get_conn(self, arr : np.ndarray, voxelInx : tuple) :
        ret = int(np.sum(arr[voxelInx[0] - 1 : voxelInx[0] + 2, voxelInx[1] - 1 : voxelInx[1] + 2, voxelInx[2] - 1 : voxelInx[2] + 2]))

        # remove the count at the now coord
        return ret - 1
    def get_conn_coord_with_vessel(self, arr : np.ndarray, voxelInx : tuple) :
        arrSearchingRange = arr[voxelInx[0] - 1 : voxelInx[0] + 2, voxelInx[1] - 1 : voxelInx[1] + 2, voxelInx[2] - 1 : voxelInx[2] + 2]
        listVoxelInx = np.array(np.where(arrSearchingRange > CScoSkelNode.eVoxelTypeNone)).T
        retListVoxelInx = self.extract_coord(listVoxelInx, voxelInx)
        return retListVoxelInx
    def get_conn_coord_with_candidate_branch(self, arr : np.ndarray, voxelInx : tuple) :
        arrSearchingRange = arr[voxelInx[0] - 1 : voxelInx[0] + 2, voxelInx[1] - 1 : voxelInx[1] + 2, voxelInx[2] - 1 : voxelInx[2] + 2]
        listVoxelInx = np.array(np.where(arrSearchingRange == CScoSkelNode.eVoxelTypeBranch)).T
        retListVoxelInx = self.extract_coord(listVoxelInx, voxelInx)
        return retListVoxelInx
    def get_conn_coord_with_seg_vessel(self, arr : np.ndarray, voxelInx : tuple) :
        arrSearchingRange = arr[voxelInx[0] - 1 : voxelInx[0] + 2, voxelInx[1] - 1 : voxelInx[1] + 2, voxelInx[2] - 1 : voxelInx[2] + 2]
        listVoxelInx = np.array(np.where(arrSearchingRange == CScoSkelNode.eVoxelTypeVessel)).T
        retListVoxelInx = self.extract_coord(listVoxelInx, voxelInx)
        return retListVoxelInx
    def get_conn_coord_with_end_point(self, arr : np.ndarray, voxelInx : tuple) :
        arrSearchingRange = arr[voxelInx[0] - 1 : voxelInx[0] + 2, voxelInx[1] - 1 : voxelInx[1] + 2, voxelInx[2] - 1 : voxelInx[2] + 2]
        listVoxelInx = np.array(np.where(arrSearchingRange == CScoSkelNode.eVoxelTypeEndPoint)).T
        retListVoxelInx = self.extract_coord(listVoxelInx, voxelInx)
        return retListVoxelInx
    
    
    def is_coord_type(self, voxelInx : tuple, type : int) :
        voxelType = self.m_npVoxelType[voxelInx]

        if voxelType == type :
            return True
        
        return False
    def is_visited(self, voxelInx : tuple) :
        if self.m_npVisitedVoxel[voxelInx] == True :
            return True

        return False
    def clear_visit(self) :
        self.m_npVisitedVoxel[:,:,:] = False
    def check_visit_end_point(self) :
        self.m_npVisitedVoxel[self.m_npVoxelType == CScoSkelNode.eVoxelTypeEndPoint] = True
    def check_visit_branch_group(self) :
        self.m_npVisitedVoxel[self.m_npVoxelType == CScoSkelNode.eVoxelTypeBranch] = True

    def find_vessel_segment(self, connSegVoxelInx : tuple) -> bool :
        coord = self.convert_voxel_index_to_vec3(connSegVoxelInx)
        for inx, vesselSeg in enumerate(self.m_listVesselSeg) :
            if vesselSeg.in_coord(coord) == True :
                return inx
        return -1


    def dbg_process(self) :
        for endPoint in self.m_listEndPoint :
            endPoint.dbg_process(1.0, (0, 1, 0))
        for branch in self.m_listBranchGroup :
            branch.dbg_process((1, 0, 1))
        for vesselSeg in self.m_listVesselSeg :
            vesselSeg.dbg_process((0, 0, 1))
    def dbg_render_end_point(self) :
        # render
        pcdList = []
        for endPoint in self.m_listEndPoint :
            pcdList.append(endPoint.DBGPCD)

        open3d.visualization.draw_geometries(pcdList)
    def dbg_render_branch(self) :
        # render
        pcdList = []
        for branch in self.m_listBranchGroup :
            pcdList.append(branch.DBGPCD)

        open3d.visualization.draw_geometries(pcdList)
    def dbg_render_vessel_segment(self) :
        # render
        pcdList = []
        for vesselSeg in self.m_listVesselSeg :
            pcdList.append(vesselSeg.DBGPCD)

        open3d.visualization.draw_geometries(pcdList)
    def dbg_render_all_segment(self) :
        pcdList = []

        for endPoint in self.m_listEndPoint :
            pcdList.append(endPoint.DBGPCD)
        for branch in self.m_listBranchGroup :
            pcdList.append(branch.DBGPCD)
        for vesselSeg in self.m_listVesselSeg :
            pcdList.append(vesselSeg.DBGPCD)
        
        open3d.visualization.draw_geometries(pcdList)

