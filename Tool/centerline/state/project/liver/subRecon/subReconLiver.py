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
import Block.resampling as resamplingB
import Block.reconstruction as reconstruction
import Block.meshHealing as meshHealing
import Block.meshBoolean as meshBoolean
import command.commandRecon as commandRecon
import glob

# from Algorithm.Recon import reconCC
from liver.subUtils import createDiaphragm
from liver.subUtils import clipUnderUmbilicusPolyLiver

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
        self.m_organList = ["Gallbladder", "Pancreas", "Spleen", "Stomach", "Liver"]
        
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
        if self.m_optionInfo.Ready == False :
            print("not found option.json")
            return
        
        dataRootPath = self.m_optionInfo.DataRootPath

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
        #print(f"Reconstruction Start! ")
        apPath = self.APPath
        ppPath = self.PPPath
        hvpPath = self.HVPPath
        mrPath = self.MRPath
        
        outputPatientFullPath = os.path.join(self.m_intermediateDataPath, patientID)
        if os.path.exists(outputPatientFullPath):
            shutil.rmtree(outputPatientFullPath)
        outputResultFullPath = os.path.join(outputPatientFullPath, "Result")
        maskCpyPath = os.path.join(self.m_intermediateDataPath, patientID, "MaskCpy")
        outputMaskPath = os.path.join(self.m_intermediateDataPath, patientID, "Mask")
        
        # if os.path.exists(maskCpyPath) :
        #     shutil.rmtree(maskCpyPath)
        # if os.path.exists(outputMaskPath) :
        #     shutil.rmtree(outputMaskPath)
        
        copy_tree(apPath, maskCpyPath)
        copy_tree(ppPath, maskCpyPath)
        copy_tree(hvpPath, maskCpyPath)
        copy_tree(mrPath, maskCpyPath)
        copy_tree(maskCpyPath, outputMaskPath)
        #self.CopiedMaskPath = maskCpyPath


        # 기존 blender 파일이 있을 경우 로딩만 수행 
        if os.path.exists(self.PatientBlenderFullPath) == True :
            commandRecon.CCommandReconInterface.blender_process_load(self.OptionInfo.BlenderExe, self.PatientBlenderFullPath)
            return

        # originMaskPath = self.MaskPath
        # if os.path.exists(originMaskPath) == False :
        #     print(f"colon recon : not found mask path - {originMaskPath}")
        #     return

        # copiedMaskPath = self.CopiedMaskPath
        # if os.path.exists(copiedMaskPath) == False :
        #     os.makedirs(copiedMaskPath, exist_ok=True)
        #     # nii.gz 파일 복사
        #     for file in glob.glob(os.path.join(originMaskPath, "*.nii.gz")):
        #         shutil.copy(file, copiedMaskPath)
        
        phase = None
        phaseInfoFullPath = os.path.join(outputPatientFullPath, "phaseInfo.json")
        if os.path.exists(phaseInfoFullPath) == True :
            fileLoadPhaseInfoBlock = niftiContainer.CFileLoadPhaseInfo()
            fileLoadPhaseInfoBlock.InputPath = self.InputData.OutputPatientPath
            fileLoadPhaseInfoBlock.InputFileName = commandRecon.CCommandReconInterface.s_phaseInfoFileName
            phase = fileLoadPhaseInfoBlock.process()
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
            #self.progress_callback(self.ProgressValue)
            
            # if not self.update_progress_value(14):
            #     return False
            
            self._update_phase_offset(self.InputData.OptionInfo, registrationBlock, originOffsetBlock, phase)
            fileSavePhaseInfoBlock = niftiContainer.CFileSavePhaseInfo()
            fileSavePhaseInfoBlock.InputPhase = phase
            fileSavePhaseInfoBlock.OutputSavePath = self.InputData.OutputPatientPath
            fileSavePhaseInfoBlock.OutputFileName = commandRecon.CCommandReconInterface.s_phaseInfoFileName
            fileSavePhaseInfoBlock.process()
            if not self.update_progress_value(2, "Resampling..."):
                return False

        resamplingToPhaseBlock = resamplingB.CResamplingToPhase()
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
        # if not self.update_progress_value(2):
        #     return False

        resamplingToMinSpacingBlock = resamplingB.CResamplingToMinSpacing()
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
        # if not self.update_progress_value(2):
        #     return False

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
        
        # if not self.update_progress_value(26):
        #     return False

        reconstructionBlock = reconstruction.CReconstruction()
        reconstructionBlock.InputOptionInfo = self.InputData.OptionInfo
        reconstructionBlock.InputMaskPath = maskCpyPath # self.CopiedMaskPath
        reconstructionBlock.InputPhase = phase
        reconstructionBlock.OutputPath = self.ResultPath
        reconstructionBlock.progress_callback = lambda p, s="": self.progress_callback(
            self.ProgressValue + int((45 / self.TotalPatientCnt) * (p / 100.0)),
            s
        )
        reconstructionBlock.is_interrupted = self.is_interrupted
        reconstructionBlock.process()
        self.ProgressValue += int(45 / self.TotalPatientCnt)
        # if not self.update_progress_value(45):
        #     return False

        meshHealingBlock = meshHealing.CMeshHealing()
        meshHealingBlock.InputPath = self.ResultPath
        meshHealingBlock.InputOptionInfo = self.InputData.OptionInfo
        meshHealingBlock.process()
        if not self.update_progress_value(1):
            return False

        meshBooleanBlock = meshBoolean.CMeshBoolean()
        meshBooleanBlock.InputPath = self.ResultPath
        meshBooleanBlock.InputOptionInfo = self.InputData.OptionInfo
        meshBooleanBlock.process()
        if not self.update_progress_value(1):
            return False

        removeStrictureBlock.clear()
        reconstructionBlock.clear()
        meshHealingBlock.clear()
        meshBooleanBlock.clear()

        # phaseInfoFileName = "phaseInfo"

        # diaphragm = createDiaphragm.CCreateDiaphragm()
        # diaphragm.InputPath = maskCpyPath
        # diaphragm.OutputPath = outputMaskPath
        # diaphragm.InputNiftiName = "Skin.nii.gz"
        # diaphragm.process()
        
        # niftiContainerBlock = niftiContainer.CNiftiContainerTerritory()
        # niftiContainerBlock.InputOptionInfo = self.m_optionInfo
        # niftiContainerBlock.InputPath = outputMaskPath 
        # niftiContainerBlock.process()
        # self.ProgressValue += int(1 / self.TotalPatientCnt)
        # self.progress_callback(self.ProgressValue)
        
        # self._update_organ_phase(niftiContainerBlock)

        # originOffsetBlock = originOffset.COriginOffset()
        # originOffsetBlock.InputOptionInfo = self.m_optionInfo
        # originOffsetBlock.InputNiftiContainer = niftiContainerBlock
        # originOffsetBlock.process()
        # self.ProgressValue += int(1 / self.TotalPatientCnt)
        # self.progress_callback(self.ProgressValue, "Registration ...")
        
        # registrationBlock = registration.CRegistration()
        # registrationBlock.InputOptionInfo = self.m_optionInfo
        # registrationBlock.InputNiftiContainer = niftiContainerBlock
        # registrationBlock.process()
        # self.ProgressValue += int(14 / self.TotalPatientCnt)
        # self.progress_callback(self.ProgressValue)
        # if self.is_interrupted():
        #     return False

        # self.__update_phase_offset(self.m_optionInfo, niftiContainerBlock, registrationBlock, originOffsetBlock)
        # fileSavePhaseInfoBlock = niftiContainer.CFileSavePhaseInfo()
        # fileSavePhaseInfoBlock.InputNiftiContainer = niftiContainerBlock
        # fileSavePhaseInfoBlock.m_outputSavePath = outputPatientFullPath
        # fileSavePhaseInfoBlock.m_outputFileName = phaseInfoFileName
        # fileSavePhaseInfoBlock.process()
        # self.ProgressValue += int(2 / self.TotalPatientCnt)
        # self.progress_callback(self.ProgressValue, "Remove Stricture ...")
        
        # removeStrictureBlock = removeStricture.CRemoveStricture()
        # removeStrictureBlock.InputNiftiContainer = niftiContainerBlock
        # removeStrictureBlock.process()
        # self.ProgressValue += int(28 / self.TotalPatientCnt)
        # self.progress_callback(self.ProgressValue, "Reconstruction ...")
        # if self.is_interrupted():
        #     return False
        
        # reconstructionBlock = reconstruction.CReconstruction()
        # reconstructionBlock.InputOptionInfo = self.m_optionInfo
        # reconstructionBlock.InputNiftiContainer = niftiContainerBlock
        # reconstructionBlock.OutputPath = outputResultFullPath
        # reconstructionBlock.process()
        # self.ProgressValue += int(48 / self.TotalPatientCnt)
        # self.progress_callback(self.ProgressValue)
        # if self.is_interrupted():
        #     return False
        
        # clippingCls = clipUnderUmbilicusPolyLiver.CClipUnderUmbilicusPoly()
        # clippingCls.InputStlPath = outputResultFullPath
        # clippingCls.InputNiftiContainer = niftiContainerBlock
        # clippingCls.InputSliceID = self.InputSliceID
        # clippingCls.process()
        # self.ProgressValue += int(1 / self.TotalPatientCnt)
        # self.progress_callback(self.ProgressValue)

        # meshHealingBlock = meshHealing.CMeshHealing()
        # meshHealingBlock.InputPath = outputResultFullPath
        # meshHealingBlock.InputOptionInfo = self.m_optionInfo
        # meshHealingBlock.process()
        # self.ProgressValue += int(1 / self.TotalPatientCnt)
        # self.progress_callback(self.ProgressValue)
        
        # meshBooleanBlock = meshBoolean.CMeshBoolean()
        # meshBooleanBlock.InputPath = outputResultFullPath
        # meshBooleanBlock.InputOptionInfo = self.m_optionInfo
        # meshBooleanBlock.process()
        # self.ProgressValue += int(1 / self.TotalPatientCnt)
        # self.progress_callback(self.ProgressValue)

        # niftiContainerBlock.clear()
        # originOffsetBlock.clear()
        # registrationBlock.clear()
        # removeStrictureBlock.clear()
        # reconstructionBlock.clear()
        # fileSavePhaseInfoBlock.clear()
        # meshHealingBlock.clear()
        # meshBooleanBlock.clear()
        
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

