import sys
import os
import numpy as np
import vtk

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileTestPath = os.path.dirname(fileAbsPath)
fileSrcPath = os.path.join(os.path.dirname(fileTestPath), "Src")
fileAlgorithmPath = os.path.join(fileSrcPath, "Algorithm") 
fileAlgUtilPath = os.path.join(fileSrcPath, "AlgUtil")
sys.path.append(fileAbsPath)
sys.path.append(fileSrcPath)
sys.path.append(fileAlgorithmPath)
sys.path.append(fileAlgUtilPath)

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algVTK as algVTK
import AlgUtil.algSegment as algSegment
# import example_vtk.frameworkVTK as frameworkVTK

import optionInfo as optionInfo
import phaseInfo as phaseInfo


import json

class CTerritory :
    def __init__(self) -> None:
        self.m_inputOptionInfo = None
        self.m_inputPhaseInfo = None
        self.m_inputSegInx = -1
        self.m_inputOrgan = None

        self.m_reconType = ""
        self.m_organInfo = None
        self.m_matOrgan = None
        self.m_matInvOrgan = None
        self.m_queryVertex = None
    def clear(self) :
        self.m_inputOptionInfo = None
        self.m_inputPhaseInfo = None
        self.m_inputSegInx = -1
        self.m_inputOrgan = None

        self.m_reconType = ""
        self.m_organInfo = None
        self.m_matOrgan = None
        self.m_matInvOrgan = None
        self.m_queryVertex = None

        self.m_wholeVesselInfo = None
    def pre_process(self) -> bool :
        if self.InputOptionInfo is None :
            print("not setting input option info")
            return False
        if self.InputPhaseInfo is None :
            print("not setting input option info")
            return False
        if self.InputSegInx == -1 :
            print("not setting input seg inx")
            return False
        if self.InputOrgan is None :
            print("not setting organ")
            return False
        
        segInfo = self.InputOptionInfo.get_segmentinfo(self.InputSegInx)
        organBlenderName = segInfo.Organ
        organMaskInfo = self.InputOptionInfo.find_maskinfo_by_blender_name(organBlenderName)
        organMaskPhase = organMaskInfo.Phase
        phaseInfo = self.InputPhaseInfo.find_phaseinfo(organMaskPhase)
        if phaseInfo is None :
            print("territory pre : not found phase")
            return False
        
        spacing = phaseInfo.Spacing
        self.m_reconType = organMaskInfo.ReconType
        self.m_organInfo = algVTK.CVTK.poly_data_voxelize(self.m_inputOrgan, spacing, 255.0)

        self.m_matOrgan = algVTK.CVTK.get_phy_matrix(self.m_organInfo[1], self.m_organInfo[2], self.m_organInfo[3])
        self.m_matInvOrgan = algLinearMath.CScoMath.inv_mat4(self.m_matOrgan)
        self.m_queryVertex = algImage.CAlgImage.get_vertex_from_np(self.m_organInfo[0], np.int32)
        
        return True
    def process(self, wholeVertex : np.ndarray, subVertex : np.ndarray) -> vtk.vtkPolyData :
        '''
        wholeVertex : must be physical coord
        subVertex : must be physical coord 
        '''
        wholeVertex = algLinearMath.CScoMath.mul_mat4_vec3(self.m_matInvOrgan, wholeVertex)
        subVertex = algLinearMath.CScoMath.mul_mat4_vec3(self.m_matInvOrgan, subVertex)

        segmentProcess = algSegment.CSegmentBasedVoxelProcess()
        segmentProcess.add_anchor(wholeVertex, 1)
        segmentProcess.add_anchor(subVertex, 2)
        segmentProcess.process(self.m_queryVertex)
        territoryVertex = segmentProcess.get_query_vertex_with_seg_index(2)

        # inputNiftiFullPath = os.path.join(self.OutputPath, f"{territoryName}.nii.gz")
        origin = self.m_organInfo[1]
        spacing = self.m_organInfo[2]
        direction = self.m_organInfo[3]
        offset = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0])

        inputNiftiFullPath = os.path.join(fileAbsPath, "territory.nii.gz")
        npImg = algImage.CAlgImage.create_np(self.m_organInfo[4], np.uint8)
        algImage.CAlgImage.set_clear(npImg, 0)
        algImage.CAlgImage.set_value(npImg, territoryVertex, 255)
        algImage.CAlgImage.save_nifti_from_np(inputNiftiFullPath, npImg, origin, spacing, direction, (2, 1, 0))

        reconParam = self.InputOptionInfo.find_recon_param(self.m_reconType)
        contour = reconParam.Contour
        algorithm = reconParam.Algorithm
        param = reconParam.Param
        gaussian = reconParam.Gaussian
        resampling = reconParam.ResamplingFactor
        polyData = CTerritory.reconstruction_nifti(inputNiftiFullPath, origin, spacing, direction, offset, contour, param, algorithm, gaussian, resampling, False)

        if os.path.exists(inputNiftiFullPath) == True:
            os.remove(inputNiftiFullPath)

        return polyData




        
        
        



        
    def _task(self, param : tuple) :
        inx = param[0]
        vesselFullPath = param[1]
        reconType = param[2]
        territoryName = param[3]

        wholeInfo = self.m_wholeVesselInfo
        spacing = wholeInfo[2]

        subVessel = algVTK.CVTK.load_poly_data_stl(vesselFullPath)
        subInfo = algVTK.CVTK.poly_data_voxelize(subVessel, spacing, 255.0)

        # wholeVertex = algImage.CAlgImage.get_vertex_from_np(wholeInfo[0], np.int32)
        subVertex = algImage.CAlgImage.get_vertex_from_np(subInfo[0], np.int32)

        matWhole = self.m_matWholeVessel
        invMatWhole = algLinearMath.CScoMath.inv_mat4(matWhole)
        matSub = algVTK.CVTK.get_phy_matrix(subInfo[1], subInfo[2], subInfo[3])
        toMatWhole = algLinearMath.CScoMath.mul_mat4_mat4(invMatWhole, matSub)
        matToOrgan = algLinearMath.CScoMath.mul_mat4_mat4(self.m_matInvOrgan, matWhole)

        subVertex = algLinearMath.CScoMath.mul_mat4_vec3(toMatWhole, subVertex)
        subVertex = np.round(subVertex).astype(np.int32)

        subMask = algImage.CAlgImage.create_np(wholeInfo[4], np.uint8)
        algImage.CAlgImage.set_clear(subMask, 0)
        algImage.CAlgImage.set_value(subMask, subVertex, 1)

        extractedWholeMask = wholeInfo[0].copy() 
        extractedWholeMask[extractedWholeMask > 0] = 1


        # process
        structure = np.ones((3, 3, 3), dtype=np.uint8)
        binaryMask = subMask > 0
        subMask = ndimage.binary_dilation(binaryMask, structure=structure, iterations=self.m_dilationIter).astype(np.uint8)
        extractedWholeMask[subMask == 1] = 0
        # removing noise
        self.__remove_noise(extractedWholeMask, self.m_noiseSegCnt)


        # territory
        extractedWholeVertex = algImage.CAlgImage.get_vertex_from_np(extractedWholeMask, np.int32)
        extractedWholeVertex = algLinearMath.CScoMath.mul_mat4_vec3(matToOrgan, extractedWholeVertex)
        subVertex = algLinearMath.CScoMath.mul_mat4_vec3(matToOrgan, subVertex)

        segmentProcess = algSegment.CSegmentBasedVoxelProcess()
        segmentProcess.add_anchor(extractedWholeVertex, 1)
        segmentProcess.add_anchor(subVertex, 2)
        segmentProcess.process(self.m_queryVertex)
        territoryVertex = segmentProcess.get_query_vertex_with_seg_index(2)

        territoryFullPath = os.path.join(self.OutputPath, f"{territoryName}.stl")

        reconParam = self.InputOptionInfo.find_recon_param(reconType)
        contour = reconParam.Contour
        algorithm = reconParam.Algorithm
        param = reconParam.Param
        gaussian = reconParam.Gaussian
        resampling = reconParam.ResamplingFactor
  
        inputNiftiFullPath = os.path.join(self.OutputPath, f"{territoryName}.nii.gz")
        npImg = algImage.CAlgImage.create_np(self.m_organInfo[4], np.uint8)
        algImage.CAlgImage.set_clear(npImg, 0)
        algImage.CAlgImage.set_value(npImg, territoryVertex, 255)
        algImage.CAlgImage.save_nifti_from_np(inputNiftiFullPath, npImg, self.m_organInfo[1], self.m_organInfo[2], self.m_organInfo[3], (2, 1, 0))
        print(f"saved territory nifti : {inputNiftiFullPath}")
        npImg = None

        territoryPolyData = reconstruction.CReconstruction.reconstruction_territory(inputNiftiFullPath, self.m_organInfo[1], self.m_organInfo[3], contour, param, algorithm, gaussian, resampling)
        algVTK.CVTK.save_poly_data_stl(territoryFullPath, territoryPolyData)

        print(f"completed territory : {territoryFullPath}")

    @property
    def InputOptionInfo(self) -> optionInfo.COptionInfo :
        return self.m_inputOptionInfo
    @InputOptionInfo.setter
    def InputOptionInfo(self, optionInfo : optionInfo.COptionInfo) :
        self.m_inputOptionInfo = optionInfo
    @property
    def InputPhaseInfo(self) -> phaseInfo.CFileLoadPhaseInfo :
        return self.m_inputPhaseInfo
    @InputPhaseInfo.setter
    def InputPhaseInfo(self, inputPhaseInfo : phaseInfo.CFileLoadPhaseInfo) :
        self.m_inputPhaseInfo = inputPhaseInfo
    @property
    def InputSegInx(self) -> int :
        return self.m_inputSegInx
    @InputSegInx.setter
    def InputSegInx(self, inputSegInx : int) :
        self.m_inputSegInx = inputSegInx
    @property
    def InputOrgan(self) -> vtk.vtkPolyData :
        return self.m_inputOrgan
    @InputOrgan.setter
    def InputOrgan(self, organ : vtk.vtkPolyData) :
        self.m_inputOrgan = organ




if __name__ == '__main__' :
    pass


# print ("ok ..")

