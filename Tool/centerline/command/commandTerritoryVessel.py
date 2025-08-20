import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget
from PySide6.QtCore import Qt
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAppPath = os.path.dirname(fileAbsPath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algSegment as algSegment

import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer
import Block.reconstruction as reconstruction

import data as data
import geometry as geometry

import commandInterface as commandInterface
import curveInfo as curveInfo
# import territory as territory



class CCommandTerritoryVessel(commandInterface.CCommand) :
    s_guideMargin = 5.0


    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_inputSkeleton = None
        self.m_inputVoxelizeSpacing = None
        self.m_listCenterlineID = []
        self.m_listSubTerriPolyData = []
    def clear(self) :
        # input your code
        self.m_inputSkeleton = None
        self.m_inputVoxelizeSpacing = None
        self.m_listCenterlineID.clear()
        self.m_listSubTerriPolyData.clear()

        super().clear()
    def process(self) :
        super().process()

        if self.InputSkeleton is None :
            return
        if self.InputVoxelizeSpacing is None :
            return
        if len(self.m_listCenterlineID) == 0 :
            return

        print("-- Start Do Territory --")

        self.m_listSubTerriPolyData.clear()

        retList = self._find_cl_tree()
        for listCLID in retList :
            self._override_sub_process(listCLID)
        
        print("-- End Do Territory --")

    
    def add_cl_id(self, id : int) :
        self.m_listCenterlineID.append(id)
    def clear_cl_id(self) :
        self.m_listCenterlineID.clear()
    def get_subterri_polydata_count(self) -> int :
        return len(self.m_listSubTerriPolyData)
    def get_subterri_polydata(self, inx : int) -> vtk.vtkPolyData :
        return self.m_listSubTerriPolyData[inx]
    

    # override
    def _override_sub_process(self, listCLID : list) :
        wholeVertex = None
        subVertex = None
        wholeVertex, subVertex = self._make_whole_sub(listCLID)
        if wholeVertex is None or subVertex is None :
            return
        guidePolyData = self._create_guide_polydata(listCLID, CCommandTerritoryVessel.s_guideMargin)
        terriPolyData = self._do_territory(guidePolyData, wholeVertex, subVertex)
        self.m_listSubTerriPolyData.append(terriPolyData)

    # protected 
    def _create_guide_polydata(self, listCLID : list, newMargin : float = 5.0) -> vtk.vtkPolyData :
        vertex = None

        iCnt = self.InputSkeleton.get_centerline_count()
        for clID in listCLID :
            cl = self.InputSkeleton.get_centerline(clID)
            if vertex is None :
                vertex = cl.Vertex.copy()
            else :
                vertex = np.concatenate((vertex, cl.Vertex), axis=0)
        if vertex is None :
            return None
        
        minV = algLinearMath.CScoMath.get_min_vec3(vertex)
        maxV = algLinearMath.CScoMath.get_max_vec3(vertex)
        minV -= newMargin
        maxV += newMargin

        cubeSource = vtk.vtkCubeSource()
        centerX = (minV[0, 0] + maxV[0, 0]) / 2.0
        centerY = (minV[0, 1] + maxV[0, 1]) / 2.0
        centerZ = (minV[0, 2] + maxV[0, 2]) / 2.0
        cubeSource.SetCenter(centerX, centerY, centerZ)

        xSize = maxV[0, 0] - minV[0, 0]
        ySize = maxV[0, 1] - minV[0, 1]
        zSize = maxV[0, 2] - minV[0, 2]
        cubeSource.SetXLength(xSize)
        cubeSource.SetYLength(ySize)
        cubeSource.SetZLength(zSize)

        cubeSource.Update()
        return cubeSource.GetOutput()

    def _find_cl_tree(self) :
        '''
        ret : [[clID, ..], [clID, ..], ..]
        '''
        retListParentID = []
        for clID in self.m_listCenterlineID :
            connIDs = self.InputSkeleton.get_conn_centerline_id(clID)
            parentCLID = connIDs[0]
            if parentCLID == -1 :
                retListParentID.append(clID)
            if parentCLID not in self.m_listCenterlineID :
                retListParentID.append(clID)

        retList = []
        for clID in retListParentID :
            listRet = self.InputSkeleton.find_descendant_centerline_by_centerline_id(clID)
            listRet = [cl.ID for cl in listRet if cl.ID in self.m_listCenterlineID]
            retList.append(listRet)
        return retList
    def _find_outsideinx(self, clID) :
        connIDs = self.InputSkeleton.get_conn_centerline_id(clID)
        parentCLID = connIDs[0]
        if parentCLID == -1 :
            return 0
        
        parentCL = self.InputSkeleton.get_centerline(parentCLID)
        spherePos = parentCL.Vertex[-1]
        radius = parentCL.Radius[-1]

        cl = self.InputSkeleton.get_centerline(clID)
        dist = np.linalg.norm(cl.Vertex - spherePos, axis=1)

        outSideInx = np.where(dist > radius)[0]
        if len(outSideInx) > 0 :
            return outSideInx[0]
        return -1
    def _get_sub_nonselection_cl(self, listCenterlineID : list, clID : int) -> np.ndarray :
        '''
        desc : parent와의 비교를 통해 branch 지점의 radius 내에 있는 vertex와 외부에 있는 vertex를 구분 
        '''
        connIDs = self.InputSkeleton.get_conn_centerline_id(clID)
        parentCLID = connIDs[0]
        cl = self.InputSkeleton.get_centerline(clID)

        if parentCLID == -1 :
            return (None, cl.Vertex)
        if parentCLID not in listCenterlineID :
            return (None, cl.Vertex)
        
        outSideInx = self._find_outsideinx(clID)
        outVertex = cl.Vertex[outSideInx : -1]
        inVertex = cl.Vertex[0 : outSideInx]
        
        return (inVertex, outVertex)
    def _get_sub_selection_cl(self, listCenterlineID : list, clID : int) -> np.ndarray :
        '''
        desc : parent와의 비교를 통해 branch 지점의 radius 내에 있는 vertex와 외부에 있는 vertex를 구분 
        '''
        connIDs = self.InputSkeleton.get_conn_centerline_id(clID)
        parentCLID = connIDs[0]
        cl = self.InputSkeleton.get_centerline(clID)

        if parentCLID == -1 :
            return (None, cl.Vertex)
        if parentCLID in listCenterlineID :
            return (None, cl.Vertex)
        
        outSideInx = self._find_outsideinx(clID)
        outVertex = cl.Vertex[outSideInx : -1]
        inVertex = cl.Vertex[0 : outSideInx]
        
        return (inVertex, outVertex)
    def _make_whole_sub(self, listCLID : list, exceptCLID : int = -1) :
        wholeVertex = None
        subVertex = None
        
        iCLCnt = self.InputSkeleton.get_centerline_count()
        for inx in range(0, iCLCnt) :
            cl = self.InputSkeleton.get_centerline(inx)

            if exceptCLID == cl.ID :
                continue

            inVertex = None 
            outVertex = None
            if cl.ID in listCLID :
                inVertex, outVertex = self._get_sub_selection_cl(listCLID, cl.ID)

                if subVertex is None :
                    subVertex = outVertex[ : -1].copy()
                else :
                    subVertex = np.concatenate((subVertex, outVertex[:-1]), axis=0)
                
                if inVertex is None :
                    continue

                if wholeVertex is None :
                    wholeVertex = inVertex[ : -1].copy()
                else :
                    wholeVertex = np.concatenate((wholeVertex, inVertex[:-1]), axis=0)
            else :
                inVertex, outVertex = self._get_sub_nonselection_cl(listCLID, cl.ID)

                if wholeVertex is None :
                    wholeVertex = outVertex[ : -1].copy()
                else :
                    wholeVertex = np.concatenate((wholeVertex, outVertex[:-1]), axis=0)
                
                if inVertex is None :
                    continue
            
                if subVertex is None :
                    subVertex = inVertex[ : -1].copy()
                else :
                    subVertex = np.concatenate((subVertex, inVertex[:-1]), axis=0)

        return (wholeVertex, subVertex)
    def _do_territory(self, polyData : vtk.vtkPolyData, wholeVertex : np.ndarray, subVertex : np.ndarray) -> vtk.vtkPolyData :
        '''
        wholeVertex : must be physical coord
        subVertex : must be physical coord 
        '''
        organInfo = algVTK.CVTK.poly_data_voxelize(polyData, self.InputVoxelizeSpacing, 255.0)
        mat = algVTK.CVTK.get_phy_matrix(organInfo[1], organInfo[2], organInfo[3])
        invMat = algLinearMath.CScoMath.inv_mat4(mat)
        queryVertex = algImage.CAlgImage.get_vertex_from_np(organInfo[0], np.int32)

        wholeVertex = algLinearMath.CScoMath.mul_mat4_vec3(invMat, wholeVertex)
        subVertex = algLinearMath.CScoMath.mul_mat4_vec3(invMat, subVertex)

        segmentProcess = algSegment.CSegmentBasedVoxelProcess()
        segmentProcess.add_anchor(wholeVertex, 1)
        segmentProcess.add_anchor(subVertex, 2)
        segmentProcess.process(queryVertex)
        territoryVertex = segmentProcess.get_query_vertex_with_seg_index(2)

        # inputNiftiFullPath = os.path.join(self.OutputPath, f"{territoryName}.nii.gz")
        origin = organInfo[1]
        spacing = organInfo[2]
        direction = organInfo[3]
        offset = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0])

        inputNiftiFullPath = os.path.join(fileAbsPath, "territory.nii.gz")
        npImg = algImage.CAlgImage.create_np(organInfo[4], np.uint8)
        algImage.CAlgImage.set_clear(npImg, 0)
        algImage.CAlgImage.set_value(npImg, territoryVertex, 255)
        algImage.CAlgImage.save_nifti_from_np(inputNiftiFullPath, npImg, origin, spacing, direction, (2, 1, 0))

        contour = 127
        algorithm = "Flying"
        param = [16, 0.3, 0.0]
        gaussian = 0
        resampling = 1
        polyData = reconstruction.CReconstruction.reconstruction_nifti(inputNiftiFullPath, origin, spacing, direction, offset, contour, param, algorithm, gaussian, resampling, False)

        if os.path.exists(inputNiftiFullPath) == True:
            os.remove(inputNiftiFullPath)

        return polyData
    

    @property
    def InputSkeleton(self) -> algSkeletonGraph.CSkeleton :
        return self.m_inputSkeleton
    @InputSkeleton.setter
    def InputSkeleton(self, skeleton : algSkeletonGraph.CSkeleton) :
        self.m_inputSkeleton = skeleton
    @property
    def InputVoxelizeSpacing(self) -> tuple :
        return self.m_inputVoxelizeSpacing
    @InputVoxelizeSpacing.setter
    def InputVoxelizeSpacing(self, spacing : tuple) :
        self.m_inputVoxelizeSpacing = spacing
    
    
class CCommandTerritoryVesselEnhanced(CCommandTerritoryVessel) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
    def clear(self) :
        # input your code
        super().clear()
    def process(self) :
        if self.InputSkeleton is None :
            return
        if self.InputVoxelizeSpacing is None :
            return
        if len(self.m_listCenterlineID) == 0 :
            return
        super().process()

    def _override_sub_process(self, listCLID : list) :
        wholeVertex = None
        subVertex = None
        wholeVertex, subVertex = self._make_whole_sub(listCLID)
        if wholeVertex is None or subVertex is None :
            return
        
        # enhanced 
        retTuple = self._make_grid_vertex(listCLID)
        if retTuple is not None :
            wholeGridVertex = retTuple[0]
            subGridVertex = retTuple[1]
            wholeVertex = np.concatenate((wholeVertex, wholeGridVertex), axis=0)
            subVertex = np.concatenate((subVertex, subGridVertex), axis=0)
        retTuple = self._make_grid_vertex_noncl(listCLID)
        if retTuple is not None :
            wholeGridVertex = retTuple[0]
            subGridVertex = retTuple[1]
            wholeVertex = np.concatenate((wholeVertex, wholeGridVertex), axis=0)
            subVertex = np.concatenate((subVertex, subGridVertex), axis=0)

        guidePolyData = self._create_guide_polydata(listCLID, CCommandTerritoryVessel.s_guideMargin)
        terriPolyData = self._do_territory(guidePolyData, wholeVertex, subVertex)
        self.m_listSubTerriPolyData.append(terriPolyData)

    # protected 
    def _make_grid_vertex(self, listCLID : list, exceptCLID : int = -1) -> tuple :
        gridWholeVertex = None
        gridSubVertex = None

        for clID in listCLID :
            if clID == exceptCLID : 
                continue

            connIDs = self.InputSkeleton.get_conn_centerline_id(clID)
            parentCLID = connIDs[0]
            if parentCLID == -1 :
                continue
            if parentCLID in listCLID :
                continue

            # parent branch의 radius를 보고 하위 centerline의 몇번째 point까지 영향을 미치는지 판단 
            outSideInx = self._find_outsideinx(clID)
            cl = self.InputSkeleton.get_centerline(clID)
            radius = cl.Radius[outSideInx]

            clCurve = curveInfo.CCLCurve(cl)
            mat = clCurve.get_transform(outSideInx)

            # world vertex에 추가되는 것은 반지름을 약간 크게 한다.
            # 이로 인해 branch를 막는 뚜껑 역할을 한다. 
            grid = geometry.CGrid(radius - 0.1, 10, 10)
            grid.transform(mat)
            subVertex = grid.Vertex

            tangent = -(clCurve.m_npZCoord[outSideInx])
            tangent = tangent * 0.1
            grid = geometry.CGrid(radius, 10, 10)
            grid.transform(mat)
            wholeVertex = grid.Vertex + tangent

            if gridSubVertex is None :
                gridSubVertex = subVertex.copy()
                gridWholeVertex = wholeVertex.copy()
            else :
                gridSubVertex = np.concatenate((gridSubVertex, subVertex), axis=0)
                gridWholeVertex = np.concatenate((gridWholeVertex, wholeVertex), axis=0)

        if gridWholeVertex is None :
            return None
        return (gridWholeVertex, gridSubVertex)
    def _make_grid_vertex_noncl(self, listCLID) -> tuple :
        gridWholeVertex = None
        gridSubVertex = None

        listAllCLID = self.InputSkeleton.find_descendant_centerline_by_centerline_id(listCLID[0])
        listAllCLID = [cl.ID for cl in listAllCLID]

        for clID in listAllCLID :
            cl = self.InputSkeleton.get_centerline(clID)
            # selection이 안된 clID만 처리
            if clID in listCLID :
                continue

            # parent가 선택된 것만 처리 
            connIDs = self.InputSkeleton.get_conn_centerline_id(clID)
            parentCLID = connIDs[0]
            if parentCLID == -1 :
                continue
            if parentCLID not in listCLID :
                continue

            outSideInx = self._find_outsideinx(clID)
            cl = self.InputSkeleton.get_centerline(clID)
            radius = cl.Radius[outSideInx]

            clCurve = curveInfo.CCLCurve(cl)
            mat = clCurve.get_transform(outSideInx)

            # 자신의 grid는 wholeVertex에 추가 
            grid = geometry.CGrid(radius - 0.1, 10, 10)
            grid.transform(mat)
            wholeVertex = grid.Vertex

            # parent grid는 subVertex에 추가
            tangent = -(clCurve.m_npZCoord[outSideInx])
            tangent = tangent * 0.1
            grid = geometry.CGrid(radius, 10, 10)
            grid.transform(mat)
            subVertex = grid.Vertex + tangent

            if gridSubVertex is None :
                gridSubVertex = subVertex.copy()
                gridWholeVertex = wholeVertex.copy()
            else :
                gridSubVertex = np.concatenate((gridSubVertex, subVertex), axis=0)
                gridWholeVertex = np.concatenate((gridWholeVertex, wholeVertex), axis=0)

        if gridWholeVertex is None :
            return None
        return (gridWholeVertex, gridSubVertex)



class CCommandTerritoryVesselKnife(CCommandTerritoryVesselEnhanced) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_inputKnifeCLID = -1
        self.m_inputKnifeIndex = -1
        self.m_inputTangent = None
    def clear(self) :
        # input your code
        self.m_inputKnifeCLID = -1
        self.m_inputKnifeIndex = -1
        self.m_inputTangent = None
        super().clear()
    def process(self) :
        if self.InputKnifeCLID == -1 :
            return
        if self.InputKnifeIndex == -1 :
            return
        if self.InputTangent is None :
            return
        if self.InputSkeleton is None :
            return
        if self.InputVoxelizeSpacing is None :
            return
        if len(self.m_listCenterlineID) == 0 :
            return
        
        super().process()

    
    # protected
    def _override_sub_process(self, listCLID : list) :
        wholeVertex = None
        subVertex = None
        wholeVertex, subVertex = self._make_whole_sub(listCLID, self.InputKnifeCLID)
        
        # enhanced 
        retTuple = self._make_grid_vertex(listCLID, self.InputKnifeCLID)
        if retTuple is not None :
            wholeGridVertex = retTuple[0]
            subGridVertex = retTuple[1]
            if wholeVertex is None :
                wholeVertex = wholeGridVertex.copy()
            else :
                wholeVertex = np.concatenate((wholeVertex, wholeGridVertex), axis=0)
            if subVertex is None :
                subVertex = subGridVertex.copy()
            else :
                subVertex = np.concatenate((subVertex, subGridVertex), axis=0)
        retTuple = self._make_grid_vertex_noncl(listCLID)
        if retTuple is not None :
            wholeGridVertex = retTuple[0]
            subGridVertex = retTuple[1]
            if wholeVertex is None :
                wholeVertex = wholeGridVertex.copy()
            else :
                wholeVertex = np.concatenate((wholeVertex, wholeGridVertex), axis=0)
            if subVertex is None :
                subVertex = subGridVertex.copy()
            else :
                subVertex = np.concatenate((subVertex, subGridVertex), axis=0)
        
        # knifed cl을 wholeVertex, subVertex에 추가
        if self.InputKnifeCLID in listCLID :
            knifeCL = self.InputSkeleton.get_centerline(self.InputKnifeCLID)
            radius = knifeCL.Radius[self.InputKnifeIndex]
            wholeVertex = np.concatenate((wholeVertex, knifeCL.Vertex[ : self.InputKnifeIndex]), axis=0)
            if subVertex is None :
                subVertex = knifeCL.Vertex[self.InputKnifeIndex : ].copy()
            else :
                subVertex = np.concatenate((subVertex, knifeCL.Vertex[self.InputKnifeIndex : ]), axis=0)

            xCoord, yCoord, zCoord = curveInfo.CCLCurve.calc_coord_by_tangent(self.InputTangent, algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0]))
            mat = curveInfo.CCLCurve.calc_mat(xCoord, yCoord, zCoord, knifeCL.Vertex[self.InputKnifeIndex].reshape(-1, 3))

            grid = geometry.CGrid(radius - 0.1, 10, 10)
            grid.transform(mat)
            subVertex = np.concatenate((subVertex, grid.Vertex), axis=0)

            clCurve = curveInfo.CCLCurve(knifeCL)
            tangent = -(clCurve.m_npZCoord[self.InputKnifeIndex])
            tangent = tangent * 0.1
            moving = knifeCL.Vertex[self.InputKnifeIndex] + tangent
            mat = curveInfo.CCLCurve.calc_mat(xCoord, yCoord, zCoord, moving)
            grid = geometry.CGrid(radius, 10, 10)
            grid.transform(mat)
            wholeVertex = np.concatenate((wholeVertex, grid.Vertex), axis=0)

        guidePolyData = self._create_guide_polydata(listCLID, CCommandTerritoryVessel.s_guideMargin)
        terriPolyData = self._do_territory(guidePolyData, wholeVertex, subVertex)
        self.m_listSubTerriPolyData.append(terriPolyData)
    

    @property
    def InputKnifeCLID(self) -> int :
        return self.m_inputKnifeCLID
    @InputKnifeCLID.setter
    def InputKnifeCLID(self, inputKnifeCLID : int) :
        self.m_inputKnifeCLID = inputKnifeCLID
    @property
    def InputKnifeIndex(self) -> int :
        return self.m_inputKnifeIndex
    @InputKnifeIndex.setter
    def InputKnifeIndex(self, inputKnifeIndex : int) :
        self.m_inputKnifeIndex = inputKnifeIndex
    @property
    def InputTangent(self) -> np.ndarray :
        return self.m_inputTangent
    @InputTangent.setter
    def InputTangent(self, inputTangent : np.ndarray) :
        self.m_inputTangent = inputTangent




if __name__ == '__main__' :
    pass


# print ("ok ..")

