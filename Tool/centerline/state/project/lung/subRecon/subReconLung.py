import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import multiprocessing

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


class CSubReconLung() :
    def __init__(self, mediator) :
        self.m_mediator = mediator
        try:
        # PyInstaller로 패키징된 실행 파일의 경우
            self.fileAbsPath = sys._MEIPASS
            self.fileAbsPath = os.getcwd() #"."
        except AttributeError:
            # 개발 환경에서
            self.fileAbsPath = os.path.abspath(os.path.dirname(__file__))
        self.m_optionPath = ""
        self.m_intermediateDataPath = ""
        self.m_optionInfo = None
    def init(self) -> bool:
        if self.m_optionPath == "" :
            print(f"subReconLung-ERROR : optionPath is Null.")
            return False        
        if self.m_intermediateDataPath == "" :
            print(f"subReconLung-ERROR : intermediateDataPath is Null.")
            return False        
        # jsonPath = os.path.join(self.fileAbsPath, "option.json")
        self.m_optionInfo = optionInfo.COptionInfoSingle(self.m_optionPath)
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

    def do_blender(self, patientID : str) :
        # blender background 실행
        saveAs = f"{patientID}.blend" #optionInfo.COptionInfo.get_blender_name(optionInfo.COptionInfo.s_processName, patientID)
        option = "--new"
        option += " --triOpt"
        cmd = f"{self.m_optionInfo.BlenderExe} -b --python {os.path.join(self.fileAbsPath, 'blenderScriptCommonPipeline.py')} -- --patientID {patientID} --optionPath {self.m_optionPath} --intermediatePath {self.m_intermediateDataPath} --path Result --saveAs {saveAs} {option}"
        os.system(cmd)  

    def _patient_pipeline(self, patientID : str) :
        self.__pipeline(patientID)
        # self.__pipeline_sub_1(patientID)

    # private
    def __pipeline(self, patientID : str) :
        # passInst = self.m_optionInfo.find_pass(optionInfo.COptionInfo.s_processName)
        # if passInst is None :
        #     print(f"not found pass : {optionInfo.COptionInfo.s_processName}")
        #     return 
        print(f"Reconstruction Start! ")
        ## 마스크 파일 복사
        patientFullPath = os.path.join(self.m_optionInfo.DataRootPath, patientID)
        self.m_maskCpyPath = os.path.join(self.m_intermediateDataPath, patientID, "Mask")
        if os.path.exists(self.m_maskCpyPath) == True :
            shutil.rmtree(self.m_maskCpyPath)
        os.makedirs(self.m_maskCpyPath)
        mask_ap_path = os.path.join(patientFullPath, "02_SAVE", "01_MASK", "AP")  #원본 마스크 폴더
        mask_files = os.listdir(mask_ap_path)
        for file_name in mask_files :
            source_file = os.path.join(mask_ap_path, file_name)
            destination_file = os.path.join(self.m_maskCpyPath, file_name)
            # 파일인지 확인 후 복사
            if os.path.isfile(source_file):
                shutil.copy2(source_file, destination_file)
        # outputDataRoot = os.path.join(fileAbsPath, os.path.basename(self.m_optionInfo.DataRootPath))
        outputPatientFullPath = os.path.join(self.m_intermediateDataPath, patientID)
        outputResultFullPath = os.path.join(outputPatientFullPath, "Result")
        phaseInfoFileName = "phaseInfo"

        niftiContainerBlock = niftiContainer.CNiftiContainerTerritory()
        niftiContainerBlock.InputOptionInfo = self.m_optionInfo
        niftiContainerBlock.InputPath = self.m_maskCpyPath
        niftiContainerBlock.process()

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

        removeStrictureBlock = removeStricture.CRemoveStricture()
        removeStrictureBlock.InputNiftiContainer = niftiContainerBlock
        removeStrictureBlock.process()

        reconstructionBlock = reconstruction.CReconstruction()
        reconstructionBlock.InputOptionInfo = self.m_optionInfo
        reconstructionBlock.InputNiftiContainer = niftiContainerBlock
        reconstructionBlock.OutputPath = outputResultFullPath
        reconstructionBlock.process()

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
        self.do_blender(patientID)

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
    @property
    def OptionPath(self) -> str:
        return self.m_optionPath
    @OptionPath.setter
    def OptionPath(self, path : str) :
        self.m_optionPath = path
    @property
    def IntermediateDataPath(self) -> str:
        return self.m_intermediateDataPath
    @IntermediateDataPath.setter
    def IntermediateDataPath(self, path : str) :
        self.m_intermediateDataPath = path
        

if __name__ == '__main__' :
    pass
    # multiprocessing.freeze_support()
    # app = CSubReconLung()
    # app.init()
    # app.process()
    # app.clear()


# print ("ok ..")

