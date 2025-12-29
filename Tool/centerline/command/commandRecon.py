import sys
import os
import numpy as np
import shutil
import SimpleITK as sitk

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
import Block.originOffset as originOffset
import Block.removeStricture as removeStricture
import Block.registration as registration
import Block.reconstruction as reconstruction
import Block.meshHealing as meshHealing
import Block.meshBoolean as meshBoolean

import data as data

import commandInterface as commandInterface
# import territory as territory



class CCommandReconInterface(commandInterface.CCommand) :
    '''
    Desc : Reconstruction Step의 Command들을 정의 

    ## input ##
    InputPatientID : patientID
    InputBlenderScriptFileName : 실행해야 할 blender script 파일명 (ex : blenderScriptRecon, 확장자 제외)
    InputSaveBlenderName : 저장되는 blender 파일명 (ex : 0058HV)

    ## output ##
    blender file 

    ## property ##
    ProgramPath : 프로그램 폴더 반환, 프로그램 실행파일은 반드시 option 파일과 동일 경로에 있어야 된다. 
    DataRootPath : mask를 포함하는 PatientID 상위 폴더의 절대 경로
    BlenderExe : option 파일 내에 정의된 BlenderExe
    ScriptFullPath : blender가 실행해야 할 script 파일의 절대 경로 
    PatientPath : mask를 포함하는 PatientID 폴더의 절대 경로
    '''

    @staticmethod
    def _remove_path(path : str) :
        if os.path.exists(path) == False :
            return
        try :
            shutil.rmtree(path)
        except OSError as e:
            print(f"Error: {e}")
    @staticmethod
    def blender_process_load(blenderExe : str, blenderFullPath : str) :
        cmd = f"{blenderExe} {blenderFullPath}"
        os.system(cmd)
    @staticmethod
    def blender_process(blenderExe : str, scriptFullPath : str, optionFullPath : str, inputPath : str, outputPath : str, saveName : str, bBackground : bool = False) :
        saveName = f"{saveName}.blend"
        if bBackground == False :
            cmd = f"{blenderExe} --python {scriptFullPath} -- --optionFullPath {optionFullPath} --inputPath {inputPath} --outputPath {outputPath} --saveName {saveName}"
        else :
            cmd = f"{blenderExe} -b --python {scriptFullPath} -- --optionFullPath {optionFullPath} --inputPath {inputPath} --outputPath {outputPath} --saveName {saveName}"
        os.system(cmd)
    @staticmethod
    def blender_process_load_script(blenderExe : str, blenderFullPath : str, scriptFullPath : str, optionFullPath : str, inputPath : str, outputPath : str, saveName : str, bBackground : bool = False) :
        saveName = f"{saveName}.blend"
        blenderFullPath = os.path.join(outputPath, saveName)
        if bBackground == False :
            cmd = f"{blenderExe} {blenderFullPath} --python {scriptFullPath} -- --optionFullPath {optionFullPath} --inputPath {inputPath} --outputPath {outputPath} --saveName {saveName}"
        else :
            cmd = f"{blenderExe} -b {blenderFullPath} --python {scriptFullPath} -- --optionFullPath {optionFullPath} --inputPath {inputPath} --outputPath {outputPath} --saveName {saveName}"
        os.system(cmd)

    s_phaseInfoFileName = "phaseInfo"


    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_inputBlenderScritpFullPath = ""
        # self.m_inputSaveBlenderName = ""
    def clear(self) :
        # input your code
        self.m_inputBlenderScritpFullPath = ""
        # self.m_inputSaveBlenderName = ""
        super().clear()
    def process(self) :
        super().process()
        # input your code


    # protected 
    # @property
    # def InputSaveBlenderName(self, saveBlenderName : str) :
    #     return self.m_inputSaveBlenderName 
    # @InputSaveBlenderName.setter
    # def InputSaveBlenderName(self, saveBlenderName : str) :
    #     self.m_inputSaveBlenderName = saveBlenderName
    @property
    def InputBlenderScritpFullPath(self) -> str :
        return self.m_inputBlenderScritpFullPath
    @InputBlenderScritpFullPath.setter
    def InputBlenderScritpFullPath(self, inputBlenderScritpFullPath : str) :
        self.m_inputBlenderScritpFullPath = inputBlenderScritpFullPath
    
    @property
    def PhaseInfoFullPath(self) -> str :
        return os.path.join(self.InputData.OutputPatientPath, f"{CCommandReconInterface.s_phaseInfoFileName}.json")
    

    # @property
    # def ProgramPath(self) -> str :
    #     return self.InputData.OptionInfoPath
    # @property
    # def DataRootPath(self) -> str :
    #     return self.InputData.OptionInfo.DataRootPath
    # @property
    # def BlenderExe(self) -> str :
    #     return self.OptionInfo.BlenderExe
        

class CCommandRecon(CCommandReconInterface) :
    '''
    Desc : 개발 단계에서의 Reconstruction Step command의 추상 클래스 

    
    ## property ##
    OutputPath : patientID 폴더들의 상위 폴더, 이곳에 recon의 결과들이 저장된다.
    OutputPatientPath : patientID 폴더, 이곳에 recon의 결과물이 저장된다.
    OutputResultPath : patientID 폴더내의 'Result' 폴더, 이곳에 recon의 결과물이 저장된다. 
    OutputBlenderFullPath : patientID의 recon된 blender 파일의 절대 경로를 반환 
    PatientMaskPath : patientID의 nifti 파일들이 저장 된 폴더 
    '''
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
    def clear(self) :
        # input your code 
        return super().clear()
    def process(self) :
        super().process()
        # input your code


    # protected 
    def _create_phase(self) -> niftiContainer.CPhase :
        optioninfo = self.OptionInfo
        listPhase = optioninfo.get_phase_list()

        phaseInst = niftiContainer.CPhase()

        for phase in listPhase :
            listMask = optioninfo.get_phase_mask_list(phase)
            for mask in listMask :
                maskFullPath = os.path.join(self.CopiedMaskPath, f"{mask}.nii.gz")
                if os.path.exists(maskFullPath) == False :
                    continue

                _, origin, spacing, direction, size = algImage.CAlgImage.get_np_from_nifti(maskFullPath)
                phaseInfo = niftiContainer.CPhaseInfo()
                phaseInfo.Origin = origin
                phaseInfo.Spacing = spacing
                phaseInfo.Direction = direction
                phaseInfo.Size = size
                phaseInfo.Phase = phase
                phaseInst.add_phaseinfo(phaseInfo)
                break
        return phaseInst
    def _update_phase_offset(
            self, 
            optionInfoBlock : optionInfo.COptionInfo,
            registrationBlock : registration.CRegistration,
            originOffsetBlock : originOffset.COriginOffset,
            phase : niftiContainer.CPhase
        ) :
        iRegInfoCnt = optionInfoBlock.get_registrationinfo_count()
        for regInx in range(0, iRegInfoCnt) :
            _, srcMaskName, _ = optionInfoBlock.get_registrationinfo(regInx)

            srcPhase = optionInfoBlock.find_phase_of_mask(srcMaskName)
            phaseInfo = phase.find_phaseinfo(srcPhase)
            if phaseInfo is None :
                continue

            phaseInfo.Offset = registrationBlock.OutputListOffset[regInx]
        
        iPhaseCnt = phase.get_phaseinfo_count()
        for phaseInx in range(0, iPhaseCnt) :
            phaseInfo = phase.get_phaseinfo(phaseInx)
            phaseInfo.Offset = phaseInfo.Offset - originOffsetBlock.OutputOriginOffset
        

    @property
    def MaskPath(self) -> str :
        optioninfo = self.OptionInfo
        patientID = self.InputData.PatientID
        patientPath = os.path.join(patientID, "Mask")
        return os.path.join(optioninfo.DataRootPath, patientPath)
    @property
    def CopiedMaskPath(self) -> str :
        outputPatientPath = self.InputData.OutputPatientPath
        fullPath = os.path.join(outputPatientPath, "Mask")
        return fullPath
    @property
    def ResultPath(self) -> str :
        outputPatientPath = self.InputData.OutputPatientPath
        fullPath = os.path.join(outputPatientPath, "Result")
        return fullPath
    

class CCommandReconDevelopClean(CCommandReconInterface) :
    '''
    Desc : common pipeline reconstruction step에서 Clean 수행
    '''

    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
    def clear(self) :
        # input your code
        super().clear()
    def process(self) :
        super().process()
        # input your code
        self._process_blender()


    # protected
    def _process_blender(self) : 
        blenderExe = self.OptionInfo.BlenderExe
        scriptFullPath = self.InputBlenderScritpFullPath
        inputPath = self.InputData.OutputPatientPath
        outputPath = self.InputData.OutputPatientPath

        patientID = self.InputData.PatientID
        saveName = f"{patientID}"
        blenderFullPath = os.path.join(outputPath, f"{saveName}.blend")

        CCommandReconInterface.blender_process_load_script(blenderExe, blenderFullPath, scriptFullPath, self.InputData.OptionInfo.m_jsonPath, inputPath, outputPath, saveName, False)

        

if __name__ == '__main__' :
    pass


# print ("ok ..")

