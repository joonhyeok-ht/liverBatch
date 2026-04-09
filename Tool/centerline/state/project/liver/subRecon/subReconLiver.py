import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
from distutils.dir_util import copy_tree
import time

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


import Block.niftiContainer as niftiContainer
import Block.originOffset as originOffset
import Block.removeStricture as removeStricture
import Block.registration as registration
import Block.resampling as resampling
import Block.reconstruction as reconstruction
import Block.meshHealing as meshHealing
import Block.meshBoolean as meshBoolean
import Block.meshDecimation as meshDecimation
import Block.nonRigidRegistration as nonRigidRegistration
import command.commandRecon as commandRecon
from subUtils import clipUnderUmbilicusPoly
import glob
# from Algorithm.Recon import reconCC

class CSubReconLiver(commandRecon.CCommandRecon) :
    def __init__(self) :
        self.m_optionPath = ""
        self.m_patientID = ""
        self.m_intermediateDataPath = ""
        self.m_apPath = ""
        self.m_ppPath = ""
        self.m_hvpPath = ""
        self.m_mrPath = ""
        self.m_tumorPhase = ""
        self.m_userData = None
        self.m_optionInfo = None
        self.progress_callback  = lambda x, y="": x
        self.is_interrupted = lambda: False
        self.m_total_patient_cnt = 0
        self.m_progress_val = 0
        self.m_inputSliceID = 0
        self.m_folderInfo = None
        self.m_maskCpyPath = ""
        self.m_resultPath = ""
        self.m_organList = ["Gallbladder", "Pancreas", "Spleen", "Stomach", "Liver"]
        self.m_registrationMethod = "rigid"
        
        try:
        # PyInstaller로 패키징된 실행 파일의 경우
            self.fileAbsPath = sys._MEIPASS
            self.fileAbsPath = os.getcwd() #"."
        except AttributeError:
            # 개발 환경에서
            self.fileAbsPath = os.path.abspath(os.path.dirname(__file__))

    # def init(self, optionInfo : optionInfo.COptionInfoSingle, userData) -> bool:
    #     if self.m_optionPath == "" :
    #         print(f"subReconStomach-ERROR : optionPath is Null.")
    #         return False        
    #     if self.m_intermediateDataPath == "" :
    #         print(f"subReconStomach-ERROR : intermediateDataPath is Null.")
    #         return False   
    #     # if self.m_tumorPhase == "" :
    #     #     print(f"subReconStomach-ERROR : Tumor Phase is Null")     
    #     # jsonPath = os.path.join(self.fileAbsPath, "option.json")
    #     self.m_userData = userData
    #     self.m_optionInfo = optionInfo #optionInfo.COptionInfoSingle(self.m_optionPath)
    #     return True    
    
    def process(self) :      
        dataRootPath = self.m_folderInfo.DataRootPath

        listPatientID = os.listdir(dataRootPath)

        for patientID in listPatientID :
            fullPath = os.path.join(dataRootPath, patientID)
            if os.path.isdir(fullPath) == False :
                continue
            else:
                self.TotalPatientCnt += 1
                
        success = True
        self.progress_callback(self.ProgressValue)
        for patientID in listPatientID :
            fullPath = os.path.join(dataRootPath, patientID)
            if os.path.isdir(fullPath) == False :
                continue
            if patientID == ".DS_Store" : 
                continue
            success = self._patient_pipeline(patientID)
            if not success:
                return False
            
        self.progress_callback(int(100))
        
        return True

    def clear(self) :
        # input your code
        print("visited clear")

    def _patient_pipeline(self, patientID : str) :
        return self.__pipeline(patientID)
        # self.__pipeline_sub_1(patientID)

    # private
    def __pipeline(self, patientID : str) :
        if self.m_maskCpyPath == "":
            maskCpyPath = os.path.join(self.m_intermediateDataPath, "MaskCpy")
            self._copy_mask(maskCpyPath)
        else:
            maskCpyPath = self.m_maskCpyPath
        if self.m_resultPath == "":
            resultPath = os.path.join(self.m_intermediateDataPath, "Result")
        else:
            resultPath = self.m_resultPath
        
        #self.OptionInfo.reload()

        self.InputMaskPath = maskCpyPath
        
        phase = None
        phaseInfoFullPath = os.path.join(self.m_intermediateDataPath, "phaseInfo.json")
        
        # phase = self._create_phase()
        # originOffsetBlock = originOffset.COriginOffset()
        # originOffsetBlock.InputOptionInfo = self.InputData.OptionInfo
        # originOffsetBlock.InputPhase = phase
        # originOffsetBlock.process()
        # print("originOffsetBlock offset !!!!!!!!!!!!", file=sys.__stdout__, flush=True)
        # print(originOffsetBlock.OutputOriginOffset, file=sys.__stdout__, flush=True)
        if os.path.exists(phaseInfoFullPath) == True :
            fileLoadPhaseInfoBlock = niftiContainer.CFileLoadPhaseInfo()
            fileLoadPhaseInfoBlock.InputPath = self.InputData.OutputPatientPath
            fileLoadPhaseInfoBlock.InputFileName = commandRecon.CCommandReconInterface.s_phaseInfoFileName
            phase = fileLoadPhaseInfoBlock.process()
            
            originOffsetBlock = originOffset.COriginOffset()
            originOffsetBlock.InputOptionInfo = self.InputData.OptionInfo
            originOffsetBlock.InputPhase = phase
            originOffsetBlock.process()
            if not self.update_progress_value(17):
                return False

        else :
            phase = self._create_phase()
            originOffsetBlock = originOffset.COriginOffset()
            originOffsetBlock.InputOptionInfo = self.InputData.OptionInfo
            originOffsetBlock.InputPhase = phase
            originOffsetBlock.process()
            if not self.update_progress_value(1, "Registration..."):
                return False

            registrationBlock = registration.CRegistration()
            registrationBlock.InputOptionInfo = self.InputData.OptionInfo
            registrationBlock.InputMaskPath = maskCpyPath #self.CopiedMaskPath
            
            registrationBlock.progress_callback = lambda p, s="": self.progress_callback(
                self.ProgressValue + int((14 / self.TotalPatientCnt) * (p / 100.0)),
                s
            )
            registrationBlock.is_interrupted = self.is_interrupted
            registrationBlock.process()
            
            self.ProgressValue += int(14 / self.TotalPatientCnt)
            
            self._update_phase_offset(self.InputData.OptionInfo, registrationBlock, originOffsetBlock, phase)
            fileSavePhaseInfoBlock = niftiContainer.CFileSavePhaseInfo()
            fileSavePhaseInfoBlock.InputPhase = phase
            fileSavePhaseInfoBlock.OutputSavePath = self.InputData.OutputPatientPath
            fileSavePhaseInfoBlock.OutputFileName = commandRecon.CCommandReconInterface.s_phaseInfoFileName
            fileSavePhaseInfoBlock.process()
            if not self.update_progress_value(2):
                return False
            
        resamplingToPhaseBlock = resampling.CResamplingToPhase()
        resamplingToPhaseBlock.InputOptionInfo = self.InputData.OptionInfo
        resamplingToPhaseBlock.InputMaskPath = maskCpyPath # self.CopiedMaskPath
        resamplingToPhaseBlock.InputPhase = phase
        resamplingToPhaseBlock.OutputMaskPath = maskCpyPath # self.CopiedMaskPath
        resamplingToPhaseBlock.progress_callback = lambda p, s="": self.progress_callback(
            self.ProgressValue + int((2 / self.TotalPatientCnt) * (p / 100.0)),
            s
        )
        resamplingToPhaseBlock.is_interrupted = self.is_interrupted
        resamplingToPhaseBlock.process()
        self.ProgressValue += int(2 / self.TotalPatientCnt)
        resamplingToMinSpacingBlock = resampling.CResamplingToMinSpacing()
        resamplingToMinSpacingBlock.InputMaskPath = maskCpyPath # self.CopiedMaskPath
        resamplingToMinSpacingBlock.InputOptionInfo = self.InputData.OptionInfo
        resamplingToMinSpacingBlock.OutputMaskPath = maskCpyPath # self.CopiedMaskPath
        resamplingToMinSpacingBlock.progress_callback = lambda p, s="": self.progress_callback(
            self.ProgressValue + int((4 / self.TotalPatientCnt) * (p / 100.0)),
            s
        )
        resamplingToMinSpacingBlock.is_interrupted = self.is_interrupted
        
        resamplingToMinSpacingBlock.process()
        self.ProgressValue += int(4 / self.TotalPatientCnt)

        removeStrictureBlock = removeStricture.CRemoveStricture()
        removeStrictureBlock.InputOptionInfo = self.OptionInfo
        removeStrictureBlock.InputMaskPath = maskCpyPath # self.CopiedMaskPath
        removeStrictureBlock.OutputMaskPath = maskCpyPath # self.CopiedMaskPath
        removeStrictureBlock.progress_callback = lambda p, s="": self.progress_callback(
            self.ProgressValue + int((26 / self.TotalPatientCnt) * (p / 100.0)),
            s
        )
        removeStrictureBlock.is_interrupted = self.is_interrupted
        removeStrictureBlock.process()
        self.ProgressValue += int(26 / self.TotalPatientCnt)
        
        if self.m_registrationMethod == "non-rigid":
            dataRootPath = self.m_folderInfo.DataRootPath
            inputDicomPath = os.path.join(dataRootPath, patientID, "01_DICOM")
                
            print("start non rigid registration", file=sys.__stdout__, flush=True)
            nonRigidregistrationBlock = nonRigidRegistration.CNonRigidRegistration()
            nonRigidregistrationBlock.InputOptionInfo = self.OptionInfo
            nonRigidregistrationBlock.InputPhase = phase
            nonRigidregistrationBlock.InputDicomPath = inputDicomPath
            nonRigidregistrationBlock.OutputPath = maskCpyPath
            nonRigidregistrationBlock.OriginOffsetBlock = originOffsetBlock
            nonRigidregistrationBlock.process()

            # self.InputData.OptionInfo
            # self.reset_warped_mask_name()
            
        reconstructionBlock = reconstruction.CReconstruction()
        reconstructionBlock.InputOptionInfo = self.InputData.OptionInfo
        reconstructionBlock.InputMaskPath = maskCpyPath # self.CopiedMaskPath
        reconstructionBlock.InputPhase = phase
        reconstructionBlock.OutputPath = resultPath
        reconstructionBlock.progress_callback = lambda p, s="": self.progress_callback(
            self.ProgressValue + int((45 / self.TotalPatientCnt) * (p / 100.0)),
            s
        )
        reconstructionBlock.is_interrupted = self.is_interrupted
        reconstructionBlock.process()
        

        clippingCls = clipUnderUmbilicusPoly.CClipUnderUmbilicusPoly()
        clippingCls.InputStlPath = resultPath
        clippingCls.InputOptionInfo = self.OptionInfo
        clippingCls.InputMaskPath = maskCpyPath
        clippingCls.InputPhase = phase
        clippingCls.InputSliceID = self.InputSliceID
        clippingCls.process()
        
        self.ProgressValue += int(45 / self.TotalPatientCnt)
        meshHealingBlock = meshHealing.CMeshHealing()
        meshHealingBlock.InputPath = resultPath
        meshHealingBlock.InputOptionInfo = self.InputData.OptionInfo
        meshHealingBlock.process()
        if not self.update_progress_value(1):
            return False

        meshBooleanBlock = meshBoolean.CMeshBoolean()
        meshBooleanBlock.InputPath = resultPath
        meshBooleanBlock.InputOptionInfo = self.InputData.OptionInfo
        meshBooleanBlock.process()
        meshDecimationBlok = meshDecimation.CMeshDecimation()
        meshDecimationBlok.InputPath = resultPath
        meshDecimationBlok.InputOptionInfo = self.InputData.OptionInfo
        meshDecimationBlok.process()
        if not self.update_progress_value(1):
            return False

        removeStrictureBlock.clear()
        reconstructionBlock.clear()
        meshHealingBlock.clear()
        meshBooleanBlock.clear()

        
        return True
    
    def update_progress_value(self, progressVal, s = ""):
        self.ProgressValue += int(progressVal / self.TotalPatientCnt)
        self.progress_callback(self.ProgressValue, s)
        if self.is_interrupted():
            return False
        return True

    def _update_organ_phase(self, niftiContainerBlock):
        iNiftiInfoCnt = niftiContainerBlock.get_nifti_info_count()
        for inx in range(0, iNiftiInfoCnt):
            niftiInfo = niftiContainerBlock.get_nifti_info(inx)
            if not niftiInfo.Valid:
                continue
            
            if niftiInfo.MaskInfo.Name in self.m_organList:
                if str(niftiInfo.MaskInfo.Name)+str(".nii.gz") not in os.listdir(self.APPath) and str(niftiInfo.MaskInfo.Name)+str(".nii.gz") in os.listdir(self.PPPath):
                    niftiInfo.MaskInfo.Phase = "PP"
                    

    # def __update_phase_offset(
    #         self, 
    #         optionInfoBlock : optionInfo.COptionInfo, niftiContainerBlock : niftiContainer.CNiftiContainer, 
    #         registrationBlock : registration.CRegistration, originOffsetBlock : originOffset.COriginOffset
    #         ) :
    #     iRegInfoCnt = optionInfoBlock.get_reginfo_count()
    #     for inx in range(0, iRegInfoCnt) :
    #         regInfo = optionInfoBlock.get_reginfo(inx)
    #         srcName = regInfo.Src

    #         listNiftiInfo = niftiContainerBlock.find_nifti_info_list_by_name(srcName)
    #         if listNiftiInfo is None :
    #             continue

    #         niftiInfo = listNiftiInfo[0]
    #         phase = niftiInfo.MaskInfo.Phase
    #         phaseInfo = niftiContainerBlock.find_phase_info(phase)
    #         if phaseInfo is None :
    #             continue
    #         phaseInfo.Offset = registrationBlock.OutputListOffset[inx]
    #     # move to origin offset
    #     iPhaseCnt = niftiContainerBlock.get_phase_info_count()
    #     for inx in range(0, iPhaseCnt) :
    #         phaseInfo = niftiContainerBlock.get_phase_info(inx)
    #         phaseInfo.Offset = phaseInfo.Offset - originOffsetBlock.OutputOriginOffset

    # protected
    def _copy_mask(self, copiedMaskPath) :
        dataRootPath = self.m_folderInfo.DataRootPath
        patientID = self.InputData.PatientID
        patientPath = os.path.join(dataRootPath, patientID)
        maskPath = os.path.join("02_SAVE", "01_MASK")

        if os.path.exists(copiedMaskPath) == False :
            os.makedirs(copiedMaskPath, exist_ok=True)

        for phase in ["AP", "PP", "DP", "MR"] :
            maskFullPath = os.path.join(patientPath, maskPath, phase)
            if os.path.exists(maskFullPath) == False :
                print(f"not found path : {maskFullPath}")
                continue
            for file in glob.glob(os.path.join(maskFullPath, "*.nii.gz")):
                shutil.copy(file, copiedMaskPath)


    @property
    def OptionPath(self) -> str:
        return self.m_optionPath
    @OptionPath.setter
    def OptionPath(self, path : str) :
        self.m_optionPath = path
    @property
    def PatientID(self) -> str :
        return self.m_patientID
    @PatientID.setter
    def PatientID(self, id : str) :
        self.m_patientID = id
    @property
    def IntermediateDataPath(self) -> str:
        return self.m_intermediateDataPath
    @IntermediateDataPath.setter
    def IntermediateDataPath(self, path : str) :
        self.m_intermediateDataPath = path
    @property
    def APPath(self) -> str :
        return self.m_apPath 
    @APPath.setter    
    def APPath(self, path : str) :
        self.m_apPath = path
    @property
    def PPPath(self) -> str :
        return self.m_ppPath 
    @PPPath.setter    
    def PPPath(self, path : str) :
        self.m_ppPath = path    
    @property
    def HVPPath(self) -> str :
        return self.m_hvpPath 
    @HVPPath.setter    
    def HVPPath(self, path : str) :
        self.m_hvpPath = path    
    @property
    def MRPath(self) -> str :
        return self.m_mrPath 
    @MRPath.setter    
    def MRPath(self, path : str) :
        self.m_mrPath = path    
    @property
    def TumorPhase(self) -> str :
        return self.m_tumorPhase
    @TumorPhase.setter    
    def TumorPhase(self, phase : str) : # 'AP', 'PP', 'DP'
        self.m_tumorPhase = phase    
    @property
    def ProgressValue(self) -> int :
        return self.m_progress_val
    @ProgressValue.setter    
    def ProgressValue(self, value : int) : # 'AP', 'PP', 'DP'
        self.m_progress_val = value    
    @property
    def TotalPatientCnt(self) -> int :
        return self.m_total_patient_cnt
    @TotalPatientCnt.setter    
    def TotalPatientCnt(self, m_total_patient_cnt : int) : # 'AP', 'PP', 'DP'
        self.m_total_patient_cnt = m_total_patient_cnt    
    @property
    def InputSliceID(self) :
        return self.m_inputSliceID
    @InputSliceID.setter
    def InputSliceID(self, inputSliceID : int) :
        self.m_inputSliceID = inputSliceID

if __name__ == '__main__' :
    pass
    # multiprocessing.freeze_support()
    # app = CsubReconStomach()
    # app.init()
    # app.process()
    # app.clear()


# print ("ok ..")

