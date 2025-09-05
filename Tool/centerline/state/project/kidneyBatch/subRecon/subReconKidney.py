import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import multiprocessing
from distutils.dir_util import copy_tree

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


import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer
import Block.originOffset as originOffset
import Block.removeStricture as removeStricture
import Block.registration as registration
import Block.reconstruction as reconstruction
import Block.meshHealing as meshHealing
import Block.meshBoolean as meshBoolean

import state.project.kidneyBatch.userDataKidneyBatch as userDataKidney
import Algorithm.Kidney.SepKidneyTumor.sepKidneyTumor2 as sepKidneyTumor2
# from Algorithm.Recon import reconCC
import createDiaphragm
import convertMaskPhase

class CSubReconKidney() :
    def __init__(self) :
        self.m_optionPath = ""
        self.m_patientID = ""
        self.m_intermediateDataPath = ""
        self.m_apPath = ""
        self.m_ppPath = ""
        self.m_dpPath = ""
        self.m_tumorPhase = ""

        self.m_userData = None
        self.m_optionInfo = None
        try:
        # PyInstaller로 패키징된 실행 파일의 경우
            self.fileAbsPath = sys._MEIPASS
            self.fileAbsPath = os.getcwd() #"."
        except AttributeError:
            # 개발 환경에서
            self.fileAbsPath = os.path.abspath(os.path.dirname(__file__))

    def init(self, optionInfo : optionInfo.COptionInfoSingle, userData : userDataKidney.CUserDataKidney) -> bool:
        if self.m_optionPath == "" :
            print(f"subReconKidney-ERROR : optionPath is Null.")
            return False        
        if self.m_intermediateDataPath == "" :
            print(f"subReconKidney-ERROR : intermediateDataPath is Null.")
            return False   
        if self.m_tumorPhase == "" :
            print(f"subReconKidney-ERROR : Tumor Phase is Null")     
        # jsonPath = os.path.join(self.fileAbsPath, "option.json")
        self.m_userData = userData
        self.m_optionInfo = optionInfo #optionInfo.COptionInfoSingle(self.m_optionPath)
        return True    
    
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
            if patientID == ".DS_Store" : 
                continue
            self._patient_pipeline(patientID)

    def clear(self) :
        # input your code
        print("visited clear")

    def _patient_pipeline(self, patientID : str) :
        self.__pipeline(patientID)
        # self.__pipeline_sub_1(patientID)

    # private
    def __pipeline(self, patientID : str) :
        print(f"Reconstruction Start! ")

        apPath = self.APPath
        ppPath = self.PPPath
        dpPath = self.DPPath
        tumorPhase = self.TumorPhase
        
        outputPatientFullPath = os.path.join(self.m_intermediateDataPath, patientID)
        outputResultFullPath = os.path.join(outputPatientFullPath, "Result")

        maskCpyPath = os.path.join(self.m_intermediateDataPath, patientID, "MaskCpy")
        outputMaskPath = os.path.join(self.m_intermediateDataPath, patientID, "Mask")
        # outputSaveStlPath = os.path.join(self.m_intermediateDataPath, patientID, "STL") "STL" 대신 "Result" 사용
        outputJson = os.path.join(self.m_intermediateDataPath, patientID, "physicalInfo.json")
        # if os.path.exists(maskCpyPath) :
        #     shutil.rmtree(maskCpyPath)
        # if os.path.exists(outputMaskPath) :
        #     shutil.rmtree(outputMaskPath)
       
        copy_tree(apPath, maskCpyPath)
        copy_tree(ppPath, maskCpyPath)
        copy_tree(dpPath, maskCpyPath)
        copy_tree(maskCpyPath, outputMaskPath)

        # if os.path.exists(outputSaveStlPath):
        #     shutil.rmtree(outputSaveStlPath)

        phaseInfoFileName = "phaseInfo"

        diaphragm = createDiaphragm.CCreateDiaphragm()
        diaphragm.InputPath = maskCpyPath
        diaphragm.OutputPath = outputMaskPath
        diaphragm.InputNiftiName = "Skin.nii.gz"
        diaphragm.process()

        # separate kidney, tumor block을 registration 이후로 옮김.
        # sepKidneyTumorBlock = sepKidneyTumor2.CSepKidneyTumor()
        # sepKidneyTumorBlock.KidneyPath = maskCpyPath
        # sepKidneyTumorBlock.TumorPhase = tumorPhase #sally
        # sepKidneyTumorBlock.SavePath = outputMaskPath
        # sepKidneyTumorBlock.process()

        niftiContainerBlock = niftiContainer.CNiftiContainerTerritory()
        niftiContainerBlock.InputOptionInfo = self.m_optionInfo
        niftiContainerBlock.InputPath = outputMaskPath #maskCpyPath 새로 생성된 Kidney와 Diaphragm의 위치를 지정.
        niftiContainerBlock.process()

        niftiContainerBlock.ListPhaseInfo

        originOffsetBlock = originOffset.COriginOffset()
        originOffsetBlock.InputOptionInfo = self.m_optionInfo
        originOffsetBlock.InputNiftiContainer = niftiContainerBlock
        originOffsetBlock.process()

        registrationBlock = registration.CRegistration()
        registrationBlock.InputOptionInfo = self.m_optionInfo
        registrationBlock.InputNiftiContainer = niftiContainerBlock
        registrationBlock.process()

        self.__update_phase_offset(self.m_optionInfo, niftiContainerBlock, registrationBlock, originOffsetBlock)
        fileSavePhaseInfoBlock = niftiContainer.CFileSavePhaseInfo()
        fileSavePhaseInfoBlock.InputNiftiContainer = niftiContainerBlock
        fileSavePhaseInfoBlock.m_outputSavePath = outputPatientFullPath
        fileSavePhaseInfoBlock.m_outputFileName = phaseInfoFileName
        fileSavePhaseInfoBlock.process()

        # registration info를 이용하여 서로 다른 phase에 있는 Tumor_exo와 Cyst_exo 의 경우 Cyst_exo의 phase를 tumor의 phase로 변환하여 새로운 cyst mask파일을 생성함.
        convertMaskPhaseBlock = convertMaskPhase.CConvertMaskPhase()
        convertMaskPhaseBlock.InputNiftiContainer = niftiContainerBlock
        convertMaskPhaseBlock.MaskCpyPath = maskCpyPath
        convertMaskPhaseBlock.TumorPhase = tumorPhase
        convertMaskPhaseBlock.process()

        sepKidneyTumorBlock = sepKidneyTumor2.CSepKidneyTumor()
        sepKidneyTumorBlock.KidneyPath = maskCpyPath
        sepKidneyTumorBlock.TumorPhase = tumorPhase #sally
        sepKidneyTumorBlock.SavePath = outputMaskPath
        sepKidneyTumorBlock.process()

        # niftiContainer 이후에 sepKidneyTumor를 수행했으므로 나중에 생긴 Kidney.nii.gz 를 niftiContainer에 등록해야함.
        kidneyPathNew = os.path.join(outputMaskPath, "Kidney.nii.gz")
        if os.path.exists(kidneyPathNew) :
            kidneyNiftiInfo = niftiContainerBlock.find_nifti_info_by_blender_name("Kidney")
            kidneyNiftiInfo.Valid = True

        removeStrictureBlock = removeStricture.CRemoveStricture()
        removeStrictureBlock.InputNiftiContainer = niftiContainerBlock
        removeStrictureBlock.process()

        reconstructionBlock = reconstruction.CReconstruction()
        reconstructionBlock.InputOptionInfo = self.m_optionInfo
        reconstructionBlock.InputNiftiContainer = niftiContainerBlock
        reconstructionBlock.OutputPath = outputResultFullPath
        reconstructionBlock.process()

        # #sally reconCC
        # reconWithCCBlock = reconCC.CReconWithCC()
        # debugCC = os.path.join(outputPatientFullPath, "CC_ReconCC_5.csv")
        # reconWithCCBlock.InputPath = maskCpyPath
        # reconWithCCBlock.InputPhyInfo = physicalInfoBlock.OutputJson
        # reconWithCCBlock.OutputPath = outputResultFullPath
        # reconWithCCBlock.DbgCC = debugCC
        # bCheckedKidney = self._set_recon_param_with_mask_path(reconWithCCBlock, maskCpyPath)
        # reconWithCCBlock.process()
        # if bCheckedKidney == True :
        #     reconWithCCBlock = reconCC.CReconWithCC()
        #     debugCC = os.path.join(outputPatientFullPath, "CC_ReconCC_6.csv")
        #     reconWithCCBlock.InputPath = outputMaskPath
        #     reconWithCCBlock.InputPhyInfo = physicalInfoBlock.OutputJson
        #     reconWithCCBlock.OutputPath = outputResultFullPath
        #     reconWithCCBlock.DbgCC = debugCC
        #     self._set_recon_param_with_kidney(reconWithCCBlock)
        #     reconWithCCBlock.process()

        meshHealingBlock = meshHealing.CMeshHealing()
        meshHealingBlock.InputPath = outputResultFullPath
        meshHealingBlock.InputOptionInfo = self.m_optionInfo
        meshHealingBlock.process()

        meshBooleanBlock = meshBoolean.CMeshBoolean()
        meshBooleanBlock.InputPath = outputResultFullPath
        meshBooleanBlock.InputOptionInfo = self.m_optionInfo
        meshBooleanBlock.process()

        # blender background 실행
        # saveAs = optionInfo.COptionInfo.get_blender_name(optionInfo.COptionInfo.s_processName, patientID)
        # option = "--new"
        # option += " --triOpt"
        # cmd = f"{self.m_optionInfo.BlenderExe} -b --python {os.path.join(self.fileAbsPath, 'blenderScriptCommonPipeline.py')} -- --patientID {patientID} --path Result --saveAs {saveAs} {option}"
        # os.system(cmd)
        # self.do_blender(patientID) #임시 주석

        niftiContainerBlock.clear()
        originOffsetBlock.clear()
        registrationBlock.clear()
        removeStrictureBlock.clear()
        reconstructionBlock.clear()
        fileSavePhaseInfoBlock.clear()
        meshHealingBlock.clear()
        meshBooleanBlock.clear()

    def __update_phase_offset(
            self, 
            optionInfoBlock : optionInfo.COptionInfo, niftiContainerBlock : niftiContainer.CNiftiContainer, 
            registrationBlock : registration.CRegistration, originOffsetBlock : originOffset.COriginOffset
            ) :
        iRegInfoCnt = optionInfoBlock.get_reginfo_count()
        for inx in range(0, iRegInfoCnt) :
            regInfo = optionInfoBlock.get_reginfo(inx)
            srcName = regInfo.Src

            listNiftiInfo = niftiContainerBlock.find_nifti_info_list_by_name(srcName)
            if listNiftiInfo is None :
                continue

            niftiInfo = listNiftiInfo[0]
            phase = niftiInfo.MaskInfo.Phase
            phaseInfo = niftiContainerBlock.find_phase_info(phase)
            if phaseInfo is None :
                continue
            phaseInfo.Offset = registrationBlock.OutputListOffset[inx]
        # move to origin offset
        iPhaseCnt = niftiContainerBlock.get_phase_info_count()
        for inx in range(0, iPhaseCnt) :
            phaseInfo = niftiContainerBlock.get_phase_info(inx)
            phaseInfo.Offset = phaseInfo.Offset - originOffsetBlock.OutputOriginOffset
    # for ReconCC
    # def _set_recon_param_with_mask_path(self, blockInst : reconCC.CReconWithCC, inputPath : str) :
    #     reconParamCnt = self.m_userData.get_recon_param_count()
    #     for inx in range(0, reconParamCnt) :
    #         iterCnt = self.m_userData.get_recon_param_iter_cnt(inx)
    #         relaxation = self.m_userData.get_recon_param_relaxation(inx)
    #         decimation = self.m_userData.get_recon_param_decimation(inx)
    #         anchorCC = self.m_userData.get_recon_param_anchor_cc(inx)
    #         blockInst.add_recon_param(iterCnt, relaxation, decimation, anchorCC)

    #     bKidneyCheck = False
    #     listPath = os.listdir(inputPath)
    #     for fileName in listPath :
    #         if fileName == ".DS_Store" : 
    #             continue
    #         if os.path.isdir(fileName) :
    #             continue
    #         ext = fileName.split('.')[-1]
    #         if ext != "gz" :
    #             continue

    #         if "Kidney" in fileName :
    #             blockInst.add_nifti_file(fileName)
    #             # if fileName == "Kidney_DL.nii.gz" or fileName == "Kidney_DR.nii.gz" :  
    #             #     bKidneyCheck = True
    #             bKidneyCheck = True  # 무조건 체크하면 될듯..sally
    #         elif "Tumor" in fileName or "Cyst" in fileName : 
    #             blockInst.add_nifti_file(fileName)
    #     return bKidneyCheck
    # # for ReconCC
    # def _set_recon_param_with_kidney(self, blockInst : reconCC.CReconWithCC) :
    #     reconParamCnt = self.m_userData.get_recon_param_count()
    #     for inx in range(0, reconParamCnt) :
    #         iterCnt = self.m_userData.get_recon_param_iter_cnt(inx)
    #         relaxation = self.m_userData.get_recon_param_relaxation(inx)
    #         decimation = self.m_userData.get_recon_param_decimation(inx)
    #         anchorCC = self.m_userData.get_recon_param_anchor_cc(inx)
    #         blockInst.add_recon_param(iterCnt, relaxation, decimation, anchorCC)
    #     blockInst.add_nifti_file("Kidney.nii.gz")

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
    def DPPath(self) -> str :
        return self.m_dpPath 
    @DPPath.setter    
    def DPPath(self, path : str) :
        self.m_dpPath = path    
    @property
    def TumorPhase(self) -> str :
        return self.m_tumorPhase
    @TumorPhase.setter    
    def TumorPhase(self, phase : str) : # 'AP', 'PP', 'DP'
        self.m_tumorPhase = phase    
    

if __name__ == '__main__' :
    pass
    # multiprocessing.freeze_support()
    # app = CSubReconKidney()
    # app.init()
    # app.process()
    # app.clear()


# print ("ok ..")

