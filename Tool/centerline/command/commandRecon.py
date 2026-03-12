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
    '''

    @staticmethod
    def remove_path(path : str) :
        if os.path.exists(path) == False :
            return
        try :
            shutil.rmtree(path)
        except OSError as e:
            print(f"Error: {e}")


    s_phaseInfoFileName = "phaseInfo"


    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
    def clear(self) :
        # input your code
        super().clear()
    def process(self) :
        super().process()
        # input your code


    # protected 
    @property
    def PhaseInfoFullPath(self) -> str :
        return os.path.join(self.InputData.OutputPatientPath, f"{CCommandReconInterface.s_phaseInfoFileName}.json")
        

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
        self.m_inputMaskPath = ""
        self.m_outputPath = ""
    def clear(self) :
        # input your code 
        self.m_inputMaskPath = ""
        self.m_outputPath = ""
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
                maskFullPath = os.path.join(self.InputMaskPath, f"{mask}.nii.gz")
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
    def InputMaskPath(self) -> str :
        return self.m_inputMaskPath
    @InputMaskPath.setter
    def InputMaskPath(self, inputMaskPath : str) :
        self.m_inputMaskPath = inputMaskPath
    @property
    def OutputPath(self) -> str :
        return self.m_outputPath
    @OutputPath.setter
    def OutputPath(self, outputPath : str) :
        self.m_outputPath = outputPath
    

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

        blenderFullPath = self.PatientBlenderFullPath
        saveName = os.path.basename(blenderFullPath)
        saveName = saveName.split('.')[0]

        CCommandReconInterface.blender_process_load_script(blenderExe, blenderFullPath, scriptFullPath, self.InputData.OptionInfo.m_jsonPath, inputPath, outputPath, saveName, False)

        

if __name__ == '__main__' :
    pass


# print ("ok ..")

