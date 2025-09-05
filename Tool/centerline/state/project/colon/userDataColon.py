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

import Block.optionInfo as optionInfo

import command.curveInfo as curveInfo

import data as data

import userData as userData


class CUserDataColon(userData.CUserData) :
    s_userDataKey = "Colon"
    s_colonCTName = "colon-0"
    s_colonMRName = "colon-MR"


    def __init__(self, data : data.CData, mediator):
        super().__init__(data, CUserDataColon.s_userDataKey)
        # input your code
        self.m_mediator = mediator
        self.m_colonCLInfoInx = -1
        self.m_colonMRInfoInx = -1
        self.m_arteryCLInfoInx = -1
    def clear(self) :
        # input your code
        self.m_mediator = None
        self.m_colonCLInfoInx = -1
        self.m_colonMRInfoInx = -1
        self.m_arteryCLInfoInx = -1
        super().clear()

    def load_patient(self) -> bool :
        if super().load_patient() == False :
            return False
        # input your code
        optionInfoInst = self.Data.OptionInfo
        iCnt = optionInfoInst.get_centerlineinfo_count()
        if iCnt == 0 :
            return

        self._init_territory()
        self._init_merge()
        self._init_closing()
        
        return True
    

    # protected
    def _init_territory(self) :
        optionInfoInst = self.Data.OptionInfo
        iCnt = optionInfoInst.get_centerlineinfo_count()
        for inx in range(0, iCnt) :
            clInfo = optionInfoInst.get_centerlineinfo(inx)
            blenderName = clInfo.get_input_blender_name()
            if blenderName == "colon-0" :
                self.m_colonCLInfoInx = inx
            if blenderName == "colon-MR" :
                self.m_colonMRInfoInx = inx
            if blenderName == "artery-all" :
                self.m_arteryCLInfoInx = inx
    def _init_merge(self) :
        optionInfoInst = self.Data.OptionInfo
        iCnt = optionInfoInst.get_centerlineinfo_count()

        listMaskInfo = optionInfoInst.find_maskinfo_list_by_name(CUserDataColon.s_colonCTName)
        if listMaskInfo is None : 
            print("not found ct colon maskInfo")
            return False
        ctPhase = listMaskInfo[0].Phase
        ctReconType = listMaskInfo[0].ReconType

        listMaskInfo = optionInfoInst.find_maskinfo_list_by_name(CUserDataColon.s_colonMRName)
        if listMaskInfo is None : 
            print("not found mr colon maskInfo")
            return False
        mrPhase = listMaskInfo[0].Phase

        maskFullPath = self.PatientMaskFullPath
        ctNiftiFullPath = os.path.join(maskFullPath, f"{CUserDataColon.s_colonCTName}.nii.gz")
        mrNiftiFullPath = os.path.join(maskFullPath, f"{CUserDataColon.s_colonMRName}.nii.gz")
        npImgCT, originCT, scalingCT, directionCT, sizeCT = algImage.CAlgImage.get_np_from_nifti(ctNiftiFullPath)
        npImgMR, originMR, scalingMR, directionMR, sizeMR = algImage.CAlgImage.get_np_from_nifti(mrNiftiFullPath)

        ctPhaseInfo = self.Data.PhaseInfoContainer.find_phaseinfo(ctPhase)
        mrPhaseInfo = self.Data.PhaseInfoContainer.find_phaseinfo(mrPhase)
        phyMatCT = algVTK.CVTK.get_vtk_phy_matrix_with_spacing(originCT, scalingCT, directionCT, ctPhaseInfo.Offset)
        phyMatMR = algVTK.CVTK.get_vtk_phy_matrix_with_spacing(originMR, scalingMR, directionMR, mrPhaseInfo.Offset)

        ctOffsetMat = algLinearMath.CScoMath.translation_mat4(ctPhaseInfo.Offset)
        mrOffsetMat = algLinearMath.CScoMath.translation_mat4(mrPhaseInfo.Offset)
        mrOffsetMat = algLinearMath.CScoMath.inv_mat4(mrOffsetMat)
        trans = algLinearMath.CScoMath.mul_mat4_mat4(mrOffsetMat, ctOffsetMat)

        sitkMR = algImage.CAlgImage.get_sitk_from_np(npImgMR, originMR, scalingMR, directionMR)
        sitkCT = algImage.CAlgImage.get_sitk_from_np(npImgCT, originCT, scalingCT, directionCT)

        sitkMRResampled = algImage.CAlgImage.resampling_sitkimg_with_mat(
            sitkMR, 
            originCT, scalingCT, directionCT, sizeCT, 
            sitkMR.GetPixelID(), sitk.sitkNearestNeighbor, 
            trans
            )
        sitkCTResampled = algImage.CAlgImage.resampling_sitkimg_with_mat(
            sitkCT, 
            originCT, scalingCT, directionCT, sizeCT, 
            sitkMR.GetPixelID(), sitk.sitkNearestNeighbor, 
            None
            )
        
        npImgMR, originMR, scalingMR, directionMR, sizeMR = algImage.CAlgImage.get_np_from_sitk(sitkMRResampled, np.uint8)
        npVertexMR = algImage.CAlgImage.get_vertex_from_np(npImgMR, np.int32)
        npImgCT, originCT, scalingCT, directionCT, sizeCT = algImage.CAlgImage.get_np_from_sitk(sitkCTResampled, np.uint8)
        npVertexCT = algImage.CAlgImage.get_vertex_from_np(npImgCT, np.int32)

        self.m_npImgColon = npImgCT
        self.m_colonOrigin = originCT
        self.m_colonScaling = scalingCT
        self.m_colonDirection = directionCT
        self.m_colonOffset = ctPhaseInfo.Offset
        self.m_colonImgSize = sizeCT
        self.m_colonCTVertex = npVertexCT
        self.m_colonMRVertex = npVertexMR
        self.m_colonReconParam = self.Data.OptionInfo.find_recon_param(ctReconType)
        self.m_phyMatColon = algVTK.CVTK.get_vtk_phy_matrix_with_spacing(originCT, scalingCT, directionCT, ctPhaseInfo.Offset)
    def _init_closing(self) :
        pass
    

    @property
    def Data(self) -> data.CData :
        return self.m_data
    @property
    def ColonCLInfoInx(self) -> int :
        return self.m_colonCLInfoInx
    @property
    def ColonMRInfoInx(self) -> int :
        return self.m_colonMRInfoInx
    @property
    def ArteryCLInfoInx(self) -> int :
        return self.m_arteryCLInfoInx
    
    @property
    def ImgColon(self) -> np.ndarray :
        return self.m_npImgColon
    @property
    def ColonOrigin(self) :
        return self.m_colonOrigin
    @property
    def ColonScaling(self) :
        return self.m_colonScaling
    @property
    def ColonDirection(self) :
        return self.m_colonDirection
    @property
    def ColonOffset(self) -> np.ndarray :
        return self.m_colonOffset
    @property
    def ColonImgSize(self) :
        return self.m_colonImgSize
    @property
    def ColonCTVertex(self) -> np.ndarray :
        return self.m_colonCTVertex
    @property
    def ColonMRVertex(self) -> np.ndarray :
        return self.m_colonMRVertex
    @property
    def ColonReconParam(self) -> optionInfo.CReconParamRange :
        return self.m_colonReconParam
    @property
    def ColonPhyMat(self) -> np.ndarray :
        return self.m_phyMatColon

    

if __name__ == '__main__' :
    pass


# print ("ok ..")

