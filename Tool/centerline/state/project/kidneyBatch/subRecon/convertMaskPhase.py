'''
File : convertMaskPhase.py
Version : 2025_07_03

'''

import os
import sys
import numpy as np
import cv2
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

'''
Name
    - CConvertMaskPhase 
Input
    - "TargetMask"        : the path including Skin or Abdominal nifti files
    - "SrcMask"        : the path for "Diaphragm.nii.gz"
Output
    - "Cyst_exo_new.nii.gz
'''
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algVTK as algVTK

import Block.niftiContainer as niftiContainer

class CConvertMaskPhase() :
    TAG = "CConvertMaskPhase"
    def __init__(self) -> None :
        self.m_inputNiftiContainer = None
        self.m_maskCpyPath = ""
        self.m_tumorPhase = ""
    def clear(self) :
        self.m_inputNiftiContainer = None
        self.m_maskCpyPath = ""
        self.m_tumorPhase = ""
    def process(self) -> bool:
        if self.m_inputNiftiContainer == None :
            print(f"inputNiftiContatiner is None. Return.")
            return False
        if not os.path.exists(self.m_maskCpyPath) :
            print(f"Not exist MaskCpyPath. Return.")
            return False
        
        flist = os.listdir(self.m_maskCpyPath) 
        if "Cyst_exo.nii.gz" in flist and self.m_tumorPhase != "DP" :
            # TODO :  cyst_exo가 있고, Tumor phase가 dp가 아닌 경우, cyst의 phase 정보를 얻어오고 새로운 마스크 생성
            # tumor phase의 phase info
            # cyst phase의 phase info
            tumorPhaseInfo = self.m_inputNiftiContainer.find_phase_info(self.m_tumorPhase)
            cystPhaseInfo = self.m_inputNiftiContainer.find_phase_info("DP")
            cystFullPath = os.path.join(self.m_maskCpyPath, "Cyst_exo.nii.gz")
            npImg, origin, scaling, direction, size = algImage.CAlgImage.get_np_from_nifti(cystFullPath)
            sitkImgCystExo = algImage.CAlgImage.get_sitk_from_np(npImg, origin, scaling, direction)
            resampledCystExo = self.get_mergeinfo_resampling_vertex(tumorPhaseInfo, cystPhaseInfo, sitkImgCystExo)

            print(f"---")
        
    def get_mergeinfo_resampling_vertex(self, targetPhaseInfo : niftiContainer.CPhaseInfo, srcPhaseInfo : niftiContainer.CPhaseInfo, sitkImg) -> np.ndarray :
        # if srcInx >= self.get_mergeinfo_count() :
        #     return None
        # if targetInx >= self.get_mergeinfo_count() :
        #     return None

        #src : Cyst_exo
        #tartget : Tumor_exo

        if srcPhaseInfo is None or targetPhaseInfo is None :
            return None
        
        resamplingTrans = self.get_mergeinfo_resampling_mat(targetPhaseInfo, srcPhaseInfo)
        # sitkImg = self.get_mergeinfo_sitk(srcInx)
        if sitkImg is None :
            return None

        resamplingSitkImg = algImage.CAlgImage.resampling_sitkimg_with_mat(
            sitkImg, 
            targetPhaseInfo.Origin, targetPhaseInfo.Spacing, targetPhaseInfo.Direction, targetPhaseInfo.Size, 
            sitkImg.GetPixelID(), sitk.sitkNearestNeighbor, 
            resamplingTrans
            )
        resNiftiFullPath = os.path.join(self.m_maskCpyPath, "Cyst_exo_new.nii.gz")
        npImg, origin, scaling, direction, size = algImage.CAlgImage.get_np_from_sitk(resamplingSitkImg, np.uint8)
        algImage.CAlgImage.save_nifti_from_np(resNiftiFullPath, npImg, origin, scaling, direction, (2, 1, 0))
        return algImage.CAlgImage.get_vertex_from_np(npImg, np.int32)     
    
    def get_mergeinfo_resampling_mat(self, targetPhaseInfo : niftiContainer.CPhaseInfo, srcPhaseInfo : niftiContainer.CPhaseInfo) -> np.ndarray :
        
        if srcPhaseInfo is None or targetPhaseInfo is None :
            return None
        
        targetOffsetMat = algLinearMath.CScoMath.translation_mat4(targetPhaseInfo.Offset)
        srcOffsetMat = algLinearMath.CScoMath.translation_mat4(srcPhaseInfo.Offset)
        srcOffsetMat = algLinearMath.CScoMath.inv_mat4(srcOffsetMat)
        trans = algLinearMath.CScoMath.mul_mat4_mat4(srcOffsetMat, targetOffsetMat)
        return trans
    @property
    def InputNiftiContainer(self) -> niftiContainer.CNiftiContainer :
        return self.m_inputNiftiContainer
    @InputNiftiContainer.setter
    def InputNiftiContainer(self, inputNiftiContainer : niftiContainer.CNiftiContainer) :
        self.m_inputNiftiContainer = inputNiftiContainer    
    @property
    def MaskCpyPath(self) :
        return self.m_maskCpyPath
    @MaskCpyPath.setter
    def MaskCpyPath(self, path : str) :
        self.m_maskCpyPath = path
    @property
    def TumorPhase(self) -> str:
        return self.m_tumorPhase
    @TumorPhase.setter
    def TumorPhase(self, phase : str) :
        self.m_tumorPhase = phase

if __name__=='__main__' :
    
    convertMaskPhase = CConvertMaskPhase()
    convertMaskPhase.process()