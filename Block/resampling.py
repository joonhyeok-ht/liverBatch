import sys
import os
import numpy as np
import SimpleITK as sitk

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
solutionPath = os.path.dirname(fileAbsPath)
sys.path.append(fileAbsPath)
sys.path.append(solutionPath)

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage

import multiProcessTask as multiProcessTask
import niftiContainer as niftiContainer
import optionInfo as optionInfo

        
class CResamplingToPhase(multiProcessTask.CMultiProcessTask) :
    def __init__(self) :
        super().__init__()
        self.m_inputOptionInfo = None
        self.m_inputPhase = None
        self.m_inputMaskPath = ""
        self.m_outputMaskPath = ""
    def clear(self) :
        self.m_inputOptionInfo = None
        self.m_inputPhase = None
        self.m_inputMaskPath = ""
        self.m_outputMaskPath = ""
        super().clear()
    def process(self) :
        if self.InputOptionInfo is None :
            print("resampling : not setting input option info")
            return
        if self.InputPhase is None :
            print("resampling : not setting input phase")
            return
        if self.InputMaskPath == "" :
            print("stricture : not setting input mask path")
            return 
        if self.OutputMaskPath == "" :
            print("stricture : not setting output mask path")
            return 
        
        if not os.path.exists(self.InputMaskPath) :
            os.makedirs(self.InputMaskPath)
        if not os.path.exists(self.OutputMaskPath) :
            os.makedirs(self.OutputMaskPath)
        
        listParam = []
        iCnt = self.InputOptionInfo.get_resampling_phase_count()
        for inx in range(0, iCnt) :
            inMaskName, outMaskName, targetPhase = self.InputOptionInfo.get_resampling_phase(inx)
            srcPhase = self.InputOptionInfo.find_phase_of_mask(inMaskName)

            inMaskFullPath = os.path.join(self.InputMaskPath, f"{inMaskName}.nii.gz")
            outMaskFullPath = os.path.join(self.OutputMaskPath, f"{outMaskName}.nii.gz")

            if os.path.exists(inMaskFullPath) == False :
                print(f"skip resampling : {inMaskName}")
                continue
            targetPhaseInfo = self.InputPhase.find_phaseinfo(targetPhase)
            if targetPhaseInfo is None or targetPhaseInfo.is_valid() == False :
                print(f"skip resampling : {inMaskName}")
                continue
            srcPhaseInfo = self.InputPhase.find_phaseinfo(srcPhase)
            if srcPhaseInfo is None or srcPhaseInfo.is_valid() == False :
                print(f"skip resampling : {inMaskName}")
                continue

            listParam.append((inMaskFullPath, outMaskFullPath, srcPhaseInfo, targetPhaseInfo))
        
        if len(listParam) > 0 :
            super().process(self._task, listParam)


    # param (inMaskFullPath, outMaskFullPath, srcPhaseInfo, targetPhaseInfo)
    def _task(self, param : tuple) :
        inMaskFullPath = param[0]
        outMaskFullPath = param[1]
        srcPhaseInfo = param[2]
        targetPhaseInfo = param[3]

        targetOffset = targetPhaseInfo.Offset
        srcOffset = srcPhaseInfo.Offset
        targetTrans = algLinearMath.CScoMath.translation_mat4(targetOffset)
        srcTrans = algLinearMath.CScoMath.translation_mat4(srcOffset)
        srcTrans = algLinearMath.CScoMath.inv_mat4(srcTrans)
        resamplingTrans = algLinearMath.CScoMath.mul_mat4_mat4(srcTrans, targetTrans)

        npImgSrc, originSrc, scalingSrc, directionSrc, sizeSrc = algImage.CAlgImage.get_np_from_nifti(inMaskFullPath)
        sitkSrc = algImage.CAlgImage.get_sitk_from_np(npImgSrc, originSrc, scalingSrc, directionSrc)
        sitkSrcResampled = algImage.CAlgImage.resampling_sitkimg_with_mat(
            sitkSrc, 
            targetPhaseInfo.Origin, targetPhaseInfo.Spacing, targetPhaseInfo.Direction, targetPhaseInfo.Size, 
            sitkSrc.GetPixelID(), sitk.sitkNearestNeighbor, 
            resamplingTrans
            )
        
        npImgRet, originRet, scalingRet, directionRet, sizeRet = algImage.CAlgImage.get_np_from_sitk(sitkSrcResampled, np.uint8)
        algImage.CAlgImage.save_nifti_from_np(outMaskFullPath, npImgRet, originRet, scalingRet, directionRet, (2, 1, 0))
        print(f"completed resampling to phase {os.path.basename(outMaskFullPath)}")


    @property
    def InputOptionInfo(self) -> optionInfo.COptionInfo :
        return self.m_inputOptionInfo
    @InputOptionInfo.setter
    def InputOptionInfo(self, inputOptionInfo : optionInfo.COptionInfo) :
        self.m_inputOptionInfo = inputOptionInfo
    @property
    def InputPhase(self) -> niftiContainer.CPhase :
        return self.m_inputPhase
    @InputPhase.setter
    def InputPhase(self, inputPhase : niftiContainer.CPhase) :
        self.m_inputPhase = inputPhase
    @property
    def InputMaskPath(self) -> str :
        return self.m_inputMaskPath
    @InputMaskPath.setter
    def InputMaskPath(self, inputMaskPath : str) :
        self.m_inputMaskPath = inputMaskPath

    @property
    def OutputMaskPath(self) -> str :
        return self.m_outputMaskPath
    @OutputMaskPath.setter
    def OutputMaskPath(self, outputMaskPath : str) :
        self.m_outputMaskPath = outputMaskPath




class CResamplingToMinSpacing(multiProcessTask.CMultiProcessTask) :
    def __init__(self) :
        super().__init__()
        self.m_inputOptionInfo = None
        self.m_inputMaskPath = ""
        self.m_outputMaskPath = ""
    def clear(self) :
        self.m_inputOptionInfo = None
        self.m_inputMaskPath = ""
        self.m_outputMaskPath = ""
        super().clear()
    def process(self) :
        if self.InputOptionInfo is None :
            print("resampling : not setting input option info")
            return
        if self.InputMaskPath == "" :
            print("stricture : not setting input mask path")
            return 
        if self.OutputMaskPath == "" :
            print("stricture : not setting output mask path")
            return 
        
        if not os.path.exists(self.InputMaskPath) :
            os.makedirs(self.InputMaskPath)
        if not os.path.exists(self.OutputMaskPath) :
            os.makedirs(self.OutputMaskPath)
        
        listParam = []

        iCnt = self.InputOptionInfo.get_resampling_minspacing_count()
        for inx in range(0, iCnt) :
            inMaskName, outMaskName = self.InputOptionInfo.get_resampling_minspacing(inx)

            inMaskFullPath = os.path.join(self.InputMaskPath, f"{inMaskName}.nii.gz")
            outMaskFullPath = os.path.join(self.OutputMaskPath, f"{outMaskName}.nii.gz")

            if os.path.exists(inMaskFullPath) == False :
                print(f"skip resampling : {inMaskName}")
                continue

            listParam.append((inMaskFullPath, outMaskFullPath))
        
        if len(listParam) > 0 :
            super().process(self._task, listParam)


    # param (inMaskFullPath, outMaskFullPath)
    def _task(self, param : tuple) :
        inMaskFullPath = param[0]
        outMaskFullPath = param[1]

        npImg, origin, spacing, direction, size = algImage.CAlgImage.get_np_from_nifti(inMaskFullPath)
        sitkImg = algImage.CAlgImage.get_sitk_from_np(npImg, origin, spacing, direction)
        minSpacing = min(spacing)
        newSpacing = [minSpacing, minSpacing, minSpacing]
        sitkImg = algImage.CAlgImage.resampling_sitkimg(sitkImg, origin, newSpacing, direction)
        npImg, origin, spacing, direction, size = algImage.CAlgImage.get_np_from_sitk(sitkImg, np.uint8)

        algImage.CAlgImage.save_nifti_from_np(outMaskFullPath, npImg, origin, spacing, direction, (2, 1, 0))
        print(f"completed resampling to min spacing {os.path.basename(outMaskFullPath)}")


    @property
    def InputOptionInfo(self) -> optionInfo.COptionInfo :
        return self.m_inputOptionInfo
    @InputOptionInfo.setter
    def InputOptionInfo(self, inputOptionInfo : optionInfo.COptionInfo) :
        self.m_inputOptionInfo = inputOptionInfo
    @property
    def InputMaskPath(self) -> str :
        return self.m_inputMaskPath
    @InputMaskPath.setter
    def InputMaskPath(self, inputMaskPath : str) :
        self.m_inputMaskPath = inputMaskPath

    @property
    def OutputMaskPath(self) -> str :
        return self.m_outputMaskPath
    @OutputMaskPath.setter
    def OutputMaskPath(self, outputMaskPath : str) :
        self.m_outputMaskPath = outputMaskPath









if __name__ == '__main__' :
    pass


# print ("ok ..")

