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


    
class CCommandTerritoryDefault(commandInterface.CCommand) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_inputWholeVertex = None
        self.m_inputSubVertex = None
        self.m_inputPolyData = None
        self.m_inputVoxelizeSpacing = None

        self.m_terriPolyData = None
    def clear(self) :
        # input your code
        self.m_inputWholeVertex = None
        self.m_inputSubVertex = None
        self.m_inputPolyData = None
        self.m_inputVoxelizeSpacing = None

        self.m_terriPolyData = None

        super().clear()
    def process(self) :
        super().process()

        if self.InputWholeVertex is None :
            return
        if self.InputSubVertex is None :
            return
        if self.InputPolyData is None :
            return
        if self.InputVoxelizeSpacing is None :
            return

        print("-- Start Do Territory --")
        
        wholeVertex = self.InputWholeVertex
        subVertex = self.InputSubVertex
        self.m_terriPolyData = self._do_territory(wholeVertex, subVertex)
        
        print("-- End Do Territory --")
    

    def _do_territory(self, wholeVertex : np.ndarray, subVertex : np.ndarray) -> vtk.vtkPolyData :
        '''
        wholeVertex : must be physical coord
        subVertex : must be physical coord 
        '''
        organInfo = algVTK.CVTK.poly_data_voxelize(self.InputPolyData, self.InputVoxelizeSpacing, 255.0)
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
    def InputWholeVertex(self) -> np.ndarray :
        return self.m_inputWholeVertex
    @InputWholeVertex.setter
    def InputWholeVertex(self, inputWholeVertex : np.ndarray) :
        self.m_inputWholeVertex = inputWholeVertex
    @property
    def InputSubVertex(self) -> np.ndarray :
        return self.m_inputSubVertex
    @InputSubVertex.setter
    def InputSubVertex(self, inputSubVertex : np.ndarray) :
        self.m_inputSubVertex = inputSubVertex
    @property
    def InputPolyData(self) -> vtk.vtkPolyData :
        return self.m_inputPolyData
    @InputPolyData.setter
    def InputPolyData(self, inputPolyData : vtk.vtkPolyData) :
        self.m_inputPolyData = inputPolyData
    @property
    def InputVoxelizeSpacing(self) -> tuple :
        return self.m_inputVoxelizeSpacing
    @InputVoxelizeSpacing.setter
    def InputVoxelizeSpacing(self, spacing : tuple) :
        self.m_inputVoxelizeSpacing = spacing
    
    @property
    def OutputTerriPolyData(self) -> vtk.vtkPolyData :
        return self.m_terriPolyData


class CCommandTerritory(commandInterface.CCommand) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_inputSkeleton = None
        self.m_inputCLMask = None
        self.m_inputTerriInfo = None
        self.m_listCenterlineID = []

        self.m_terriPolyData = None
    def clear(self) :
        # input your code
        self.m_inputSkeleton = None
        self.m_inputCLMask = None
        self.m_inputTerriInfo = None
        self.m_listCenterlineID.clear()

        self.m_terriPolyData = None

        super().clear()
    def process(self) :
        super().process()

        if self.InputSkeleton is None :
            return
        if self.InputTerriInfo is None :
            return
        if len(self.m_listCenterlineID) == 0 :
            return

        print("-- Start Do Territory --")

        retList = self.m_listCenterlineID
        retListCLID = retList
        # retListCLID = []
        # for clID in retList :
        #     self._attach_descendant_centerlineID(retListCLID, clID)
        if len(retListCLID) == 0 :
            return
        
        wholeVertex = None
        subVertex = None
        wholeVertex, subVertex = self._make_whole_sub(retListCLID)
        if wholeVertex is None or subVertex is None :
            return
        
        self.m_terriPolyData = self._do_territory(wholeVertex, subVertex)
        
        print("-- End Do Territory --")

    
    def add_cl_id(self, id : int) :
        self.m_listCenterlineID.append(id)
    def clear_cl_id(self) :
        self.m_listCenterlineID.clear()
    

    # protected 
    def _make_whole_sub(self, listCLID : list, exceptCLID : int = -1) :
        wholeVertex = []
        subVertex = []
        
        iCLCnt = self.InputSkeleton.get_centerline_count()
        for inx in range(0, iCLCnt) :
            cl = self.InputSkeleton.get_centerline(inx)
            if cl.ID == exceptCLID :
                continue

            iVertexCnt = cl.get_vertex_count()
            if cl.ID in listCLID :
                for vertexInx in range(0, iVertexCnt) :
                    vertex = cl.get_vertex(vertexInx)
                    if self.InputCLMask.get_flag(cl, vertexInx) == True :
                        vertex = vertex.reshape(-1)
                        subVertex.append(vertex)
            else :
                for vertexInx in range(0, iVertexCnt) :
                    vertex = cl.get_vertex(vertexInx)
                    if self.InputCLMask.get_flag(cl, vertexInx) == True :
                        vertex = vertex.reshape(-1)
                        wholeVertex.append(vertex)
        wholeVertex = np.array(wholeVertex)
        if len(subVertex) > 0 :
            subVertex = np.array(subVertex)
        else :
            subVertex = None
        return (wholeVertex, subVertex)
    # def _attach_descendant_centerlineID(self, outListID : list, clID : int) :
    #     retListCL = self.InputSkeleton.find_descendant_centerline_by_centerline_id(clID)
    #     if retListCL is None :
    #         return
    #     retListID = [cl.ID for cl in retListCL]
    #     outListID += [id for id in retListID if id not in outListID]
    #     return outListID
    
    def _do_territory(self, wholeVertex : np.ndarray, subVertex : np.ndarray) -> vtk.vtkPolyData :
        '''
        wholeVertex : must be physical coord
        subVertex : must be physical coord 
        '''
        terriInfo = self.InputTerriInfo
        wholeVertex = algLinearMath.CScoMath.mul_mat4_vec3(terriInfo.InvMat, wholeVertex)
        subVertex = algLinearMath.CScoMath.mul_mat4_vec3(terriInfo.InvMat, subVertex)

        segmentProcess = algSegment.CSegmentBasedVoxelProcess()
        segmentProcess.add_anchor(wholeVertex, 1)
        segmentProcess.add_anchor(subVertex, 2)
        segmentProcess.process(terriInfo.QueryVertex)
        territoryVertex = segmentProcess.get_query_vertex_with_seg_index(2)

        # inputNiftiFullPath = os.path.join(self.OutputPath, f"{territoryName}.nii.gz")
        origin = terriInfo.OrganInfo[1]
        spacing = terriInfo.OrganInfo[2]
        direction = terriInfo.OrganInfo[3]
        offset = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0])

        inputNiftiFullPath = os.path.join(fileAbsPath, "territory.nii.gz")
        npImg = algImage.CAlgImage.create_np(terriInfo.OrganInfo[4], np.uint8)
        algImage.CAlgImage.set_clear(npImg, 0)
        algImage.CAlgImage.set_value(npImg, territoryVertex, 255)
        algImage.CAlgImage.save_nifti_from_np(inputNiftiFullPath, npImg, origin, spacing, direction, (2, 1, 0))

        reconParam = self.OptionInfo.find_recon_param(terriInfo.ReconType)
        contour = reconParam.Contour
        algorithm = reconParam.Algorithm
        param = reconParam.Param
        gaussian = reconParam.Gaussian
        resampling = reconParam.ResamplingFactor
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
    def InputTerriInfo(self) -> data.CTerritoryInfo :
        return self.m_inputTerriInfo
    @InputTerriInfo.setter
    def InputTerriInfo(self, inputTerriInfo : data.CTerritoryInfo) :
        self.m_inputTerriInfo = inputTerriInfo
    @property
    def InputCLMask(self) :
        return self.m_inputCLMask
    @InputCLMask.setter
    def InputCLMask(self, inputCLMask) :
        self.m_inputCLMask = inputCLMask
    
    @property
    def OutputTerriPolyData(self) -> vtk.vtkPolyData :
        return self.m_terriPolyData


class CCommandTerritoryKnife(CCommandTerritory) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_inputKnifeCLID = -1
        self.m_inputKnifeIndex = -1
    def clear(self) :
        # input your code
        self.m_inputKnifeCLID = -1
        self.m_inputKnifeIndex = -1
        super().clear()
    def process(self) :
        if self.InputSkeleton is None :
            return
        if self.InputTerriInfo is None :
            return
        if len(self.m_listCenterlineID) == 0 :
            return
        if self.InputKnifeCLID == -1 :
            return
        if self.InputKnifeIndex == -1 :
            return
        
        print("-- Start Do Territory --")

        retList = self.m_listCenterlineID
        retListCLID = retList
        # retListCLID = []
        # for clID in retList :
        #     self._attach_descendant_centerlineID(retListCLID, clID)
        if len(retListCLID) == 0 :
            return
        
        wholeVertex = None
        subVertex = None
        wholeVertex, subVertex = self._make_whole_sub(retListCLID, self.InputKnifeCLID)

        # knifed clID 
        cl = self.InputSkeleton.get_centerline(self.InputKnifeCLID)
        iVertexCnt = cl.get_vertex_count()
        # wholeVertex
        for vertexInx in range(0, self.InputKnifeIndex) :
            if self.InputCLMask.get_flag(cl, vertexInx) == False :
                continue

            vertex = cl.get_vertex(vertexInx)
            wholeVertex = np.concatenate((wholeVertex, vertex), axis=0)
        # subVertex
        for vertexInx in range(self.InputKnifeIndex, iVertexCnt) :
            if self.InputCLMask.get_flag(cl, vertexInx) == False :
                continue

            vertex = cl.get_vertex(vertexInx)
            if subVertex is None :
                subVertex = vertex.copy()
            else :
                subVertex = np.concatenate((subVertex, vertex), axis=0)
        
        self.m_terriPolyData = self._do_territory(wholeVertex, subVertex)
        
        print("-- End Do Territory --")
        
    
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


if __name__ == '__main__' :
    pass


# print ("ok ..")

