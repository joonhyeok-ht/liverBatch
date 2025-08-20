import sys
import os
import numpy as np
import multiprocessing

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAlgorithmPath = os.path.join(fileAbsPath, "Algorithm") 
fileAlgUtilPath = os.path.join(fileAbsPath, "AlgUtil")
fileBlockPath = os.path.join(fileAbsPath, "Block")
sys.path.append(fileAbsPath)
sys.path.append(fileAlgorithmPath)
sys.path.append(fileAlgUtilPath)
sys.path.append(fileBlockPath)


import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer
import Block.originOffset as originOffset
import Block.removeStricture as removeStricture
import Block.registration as registration
import Block.reconstruction as reconstruction
import Block.meshHealing as meshHealing
import Block.meshBoolean as meshBoolean


class CCommonPipeline() :
    def __init__(self) -> None:
        try:
        # PyInstaller로 패키징된 실행 파일의 경우
            self.fileAbsPath = sys._MEIPASS
            self.fileAbsPath = "."
        except AttributeError:
            # 개발 환경에서
            self.fileAbsPath = os.path.abspath(os.path.dirname(__file__))

    # override
    def init(self) :
        jsonPath = os.path.join(self.fileAbsPath, "option.json")
        self.m_optionInfo = optionInfo.COptionInfoSingle(jsonPath)
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
        passInst = self.m_optionInfo.find_pass(optionInfo.COptionInfo.s_processName)
        if passInst is None :
            print(f"not found pass : {optionInfo.COptionInfo.s_processName}")
            return 

        patientFullPath = os.path.join(self.m_optionInfo.DataRootPath, patientID)
        maskFullPath = os.path.join(patientFullPath, "Mask")
        outputDataRoot = os.path.join(self.fileAbsPath, os.path.basename(self.m_optionInfo.DataRootPath))
        outputPatientFullPath = os.path.join(outputDataRoot, patientID)
        outputResultFullPath = os.path.join(outputPatientFullPath, "Result")
        phaseInfoFileName = "phaseInfo"

        niftiContainerBlock = niftiContainer.CNiftiContainerTerritory()
        niftiContainerBlock.InputOptionInfo = self.m_optionInfo
        niftiContainerBlock.InputPath = maskFullPath
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
        saveAs = optionInfo.COptionInfo.get_blender_name(optionInfo.COptionInfo.s_processName, patientID)
        option = "--new"
        if passInst.TriOpt == 1 :
            option += " --triOpt"
        cmd = f"{self.m_optionInfo.BlenderExe} -b --python {os.path.join(self.fileAbsPath, 'blenderScriptCommonPipeline.py')} -- --patientID {patientID} --path Result --saveAs {saveAs} {option}"
        os.system(cmd)

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


if __name__ == '__main__' :
    multiprocessing.freeze_support()
    app = CCommonPipeline()
    app.init()
    app.process()
    app.clear()


print ("ok ..")

