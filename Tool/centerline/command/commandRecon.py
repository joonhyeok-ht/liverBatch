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
import Block.nonRigidRegistration as nonRigidRegistration
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
    ProgramPath : 프로그램 폴더 반환, 프로그램 실행파일은 반드시 option 파일과 동일 경로에 있어야 된다. d
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
        self.m_inputPatientID = ""
        self.m_inputBlenderScritpFileName = ""
        self.m_inputSaveBlenderName = ""
    def clear(self) :
        # input your code
        self.m_inputPatientID = ""
        self.m_inputBlenderScritpFileName = ""
        self.m_inputSaveBlenderName = ""
        super().clear()
    def process(self) :
        super().process()
        # input your code


    # protected 


    @property
    def InputPatientID(self) -> str :
        return self.m_inputPatientID
    @InputPatientID.setter
    def InputPatientID(self, inputPatientID : str) :
        self.m_inputPatientID = inputPatientID
    @property
    def InputBlenderScritpFileName(self) -> str :
        return self.m_inputBlenderScritpFileName
    @InputBlenderScritpFileName.setter
    def InputBlenderScritpFileName(self, inputBlenderScritpFileName : str) :
        self.m_inputBlenderScritpFileName = inputBlenderScritpFileName
    @property
    def InputSaveBlenderName(self) -> str :
        return self.m_inputSaveBlenderName
    @InputSaveBlenderName.setter
    def InputSaveBlenderName(self, inputSaveBlenderName : str) :
        self.m_inputSaveBlenderName = inputSaveBlenderName

    @property
    def ProgramPath(self) -> str :
        return os.path.dirname(self.InputData.DataInfo.OptionFullPath)
    @property
    def DataRootPath(self) -> str :
        return self.InputData.OptionInfo.DataRootPath
    @property
    def BlenderExe(self) -> str :
        return self.OptionInfo.BlenderExe
    @property
    def ScriptFullPath(self) -> str :
        return os.path.join(self.ProgramPath, f"{self.InputBlenderScritpFileName}.py")
    @property
    def PatientPath(self) -> str :
        return os.path.join(self.DataRootPath, self.InputPatientID)
        

class CCommandReconDevelop(CCommandReconInterface) :
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
        self.m_outputPath = ""
        self.m_dicomePath = ""
        
    def clear(self):
        # input your code 
        self.m_outputPath = ""
        self.m_dicomePath = ""
        
        return super().clear()
    def process(self):
        super().process()
        # input your code


    # protected 
    def _update_phase_offset(
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
    def OutputPath(self) -> str :
        return self.m_outputPath
    @OutputPath.setter
    def OutputPath(self, outputPath : str) :
        self.m_outputPath = outputPath
    @property
    def OutputPatientPath(self) -> str :
        return os.path.join(self.OutputPath, self.InputPatientID)
    @property
    def OutputResultPath(self) -> str :
        return os.path.join(self.OutputPatientPath, "Result")
    @property
    def OutputBlenderFullPath(self) -> str :
        return os.path.join(self.OutputPatientPath, f"{self.InputSaveBlenderName}.blend")
    @property
    def PatientMaskPath(self) -> str :
        return os.path.join(self.PatientPath, "Mask")
    @property
    def DicomePath(self) -> str :
        return self.m_dicomePath
    @DicomePath.setter
    def DicomePath(self, dicomPath : str) :
        self.m_dicomePath = dicomPath
    

class CCommandReconDevelopCommon(CCommandReconDevelop) :
    '''
    Desc : common pipeline reconstruction step에서 Recon 수행
    '''

    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
    def clear(self):
        # input your code
        super().clear()
    def process(self):
        super().process()
        # input your code

        # 기존 blender 파일이 있을 경우 로딩만 수행 
        if os.path.exists(self.OutputBlenderFullPath) == True :
            CCommandReconInterface.blender_process_load(self.BlenderExe, self.OutputBlenderFullPath)
            return

        niftiContainerBlock = niftiContainer.CNiftiContainerTerritory()
        niftiContainerBlock.InputOptionInfo = self.InputData.OptionInfo
        niftiContainerBlock.InputPath = self.PatientMaskPath
        niftiContainerBlock.process()

        originOffsetBlock = originOffset.COriginOffset()
        originOffsetBlock.InputOptionInfo = self.InputData.OptionInfo
        originOffsetBlock.InputNiftiContainer = niftiContainerBlock
        originOffsetBlock.process()

        registrationBlock = registration.CRegistration()
        registrationBlock.InputOptionInfo = self.InputData.OptionInfo
        registrationBlock.InputNiftiContainer = niftiContainerBlock
        registrationBlock.process()

        self._update_phase_offset(self.InputData.OptionInfo, niftiContainerBlock, registrationBlock, originOffsetBlock)
        fileSavePhaseInfoBlock = niftiContainer.CFileSavePhaseInfo()
        fileSavePhaseInfoBlock.InputNiftiContainer = niftiContainerBlock
        fileSavePhaseInfoBlock.m_outputSavePath = self.OutputPatientPath
        fileSavePhaseInfoBlock.m_outputFileName = CCommandReconInterface.s_phaseInfoFileName
        fileSavePhaseInfoBlock.process()

        removeStrictureBlock = removeStricture.CRemoveStricture()
        removeStrictureBlock.InputNiftiContainer = niftiContainerBlock
        removeStrictureBlock.process()

        reconstructionBlock = reconstruction.CReconstruction()
        reconstructionBlock.InputOptionInfo = self.InputData.OptionInfo
        reconstructionBlock.InputNiftiContainer = niftiContainerBlock
        reconstructionBlock.OutputPath = self.OutputResultPath
        reconstructionBlock.process()

        meshHealingBlock = meshHealing.CMeshHealing()
        meshHealingBlock.InputPath = self.OutputResultPath
        meshHealingBlock.InputOptionInfo = self.InputData.OptionInfo
        meshHealingBlock.process()

        meshBooleanBlock = meshBoolean.CMeshBoolean()
        meshBooleanBlock.InputPath = self.OutputResultPath
        meshBooleanBlock.InputOptionInfo = self.InputData.OptionInfo
        meshBooleanBlock.process()

        niftiContainerBlock.clear()
        originOffsetBlock.clear()
        registrationBlock.clear()
        removeStrictureBlock.clear()
        reconstructionBlock.clear()
        fileSavePhaseInfoBlock.clear()
        meshHealingBlock.clear()
        meshBooleanBlock.clear()

        self._process_blender()


    # protected
    def _process_blender(self) :
        blenderExe = self.BlenderExe
        scriptFullPath = self.ScriptFullPath
        inputPath = self.OutputResultPath
        outputPath = self.OutputPatientPath
        saveName = self.InputSaveBlenderName
        CCommandReconInterface.blender_process(blenderExe, scriptFullPath, self.InputData.DataInfo.OptionFullPath, inputPath, outputPath, saveName, False)


class CCommandReconDevelopLiver(CCommandReconDevelop) :
    '''
    Desc : common pipeline reconstruction step에서 Recon 수행
    '''

    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
    def clear(self):
        # input your code
        super().clear()
    def process(self):
        super().process()
        # input your code

        # 기존 blender 파일이 있을 경우 로딩만 수행 
        if os.path.exists(self.OutputBlenderFullPath) == True :
            CCommandReconInterface.blender_process_load(self.BlenderExe, self.OutputBlenderFullPath)
            return

        warpedResultPath = os.path.join(self.OutputPatientPath, "Warped")
        self.DicomePath = os.path.join(self.OutputPatientPath, "DICOM")
        if not os.path.exists(warpedResultPath):
            os.makedirs(warpedResultPath)

        niftiContainerBlock = niftiContainer.CNiftiContainerTerritory()
        niftiContainerBlock.InputOptionInfo = self.InputData.OptionInfo
        niftiContainerBlock.InputPath = self.PatientMaskPath
        niftiContainerBlock.process()

        originOffsetBlock = originOffset.COriginOffset()
        originOffsetBlock.InputOptionInfo = self.InputData.OptionInfo
        originOffsetBlock.InputNiftiContainer = niftiContainerBlock
        originOffsetBlock.process()

        registrationBlock = registration.CRegistration()
        registrationBlock.InputOptionInfo = self.InputData.OptionInfo
        registrationBlock.InputNiftiContainer = niftiContainerBlock
        registrationBlock.process()
        
        self.__update_phase_offset(self.InputData.OptionInfo, niftiContainerBlock, registrationBlock, originOffsetBlock)
        nonRigidregistrationBlock = nonRigidRegistration.CNonRigidRegistration()
        nonRigidregistrationBlock.InputOptionInfo = self.InputData.OptionInfo
        nonRigidregistrationBlock.InputNiftiContainer = niftiContainerBlock
        nonRigidregistrationBlock.OutputPath = warpedResultPath
        nonRigidregistrationBlock.InputDicomPath = self.DicomePath
        nonRigidregistrationBlock.process()
        self._update_origin_offset_and_src_header(self.InputData.OptionInfo, niftiContainerBlock, originOffsetBlock)

        #self.__update_phase_offset(self.InputData.OptionInfo, niftiContainerBlock, registrationBlock, originOffsetBlock)
        fileSavePhaseInfoBlock = niftiContainer.CFileSavePhaseInfo()
        fileSavePhaseInfoBlock.InputNiftiContainer = niftiContainerBlock
        fileSavePhaseInfoBlock.m_outputSavePath = self.OutputPatientPath
        fileSavePhaseInfoBlock.m_outputFileName = CCommandReconInterface.s_phaseInfoFileName
        fileSavePhaseInfoBlock.process()

        removeStrictureBlock = removeStricture.CRemoveStricture()
        removeStrictureBlock.InputNiftiContainer = niftiContainerBlock
        removeStrictureBlock.process()

        reconstructionBlock = reconstruction.CReconstruction()
        reconstructionBlock.InputOptionInfo = self.InputData.OptionInfo
        reconstructionBlock.InputNiftiContainer = niftiContainerBlock
        reconstructionBlock.OutputPath = self.OutputResultPath
        reconstructionBlock.process()

        meshHealingBlock = meshHealing.CMeshHealing()
        meshHealingBlock.InputPath = self.OutputResultPath
        meshHealingBlock.InputOptionInfo = self.InputData.OptionInfo
        meshHealingBlock.process()

        meshBooleanBlock = meshBoolean.CMeshBoolean()
        meshBooleanBlock.InputPath = self.OutputResultPath
        meshBooleanBlock.InputOptionInfo = self.InputData.OptionInfo
        meshBooleanBlock.process()

        niftiContainerBlock.clear()
        originOffsetBlock.clear()
        registrationBlock.clear()
        removeStrictureBlock.clear()
        reconstructionBlock.clear()
        fileSavePhaseInfoBlock.clear()
        meshHealingBlock.clear()
        meshBooleanBlock.clear()

        self._process_blender()


    # protected
    def _process_blender(self) :
        blenderExe = self.BlenderExe
        scriptFullPath = self.ScriptFullPath
        inputPath = self.OutputResultPath
        outputPath = self.OutputPatientPath
        saveName = self.InputSaveBlenderName
        CCommandReconInterface.blender_process(blenderExe, scriptFullPath, self.InputData.DataInfo.OptionFullPath, inputPath, outputPath, saveName, False)


    def _update_origin_offset_and_src_header(self, optionInfoBlock : optionInfo.COptionInfo, niftiContainerBlock : niftiContainer.CNiftiContainer, 
                            originOffsetBlock : originOffset.COriginOffset):
        # move to origin offset
        regInfo = optionInfoBlock.get_reginfo(0)
        targetName = regInfo.Target
        targetNiftiInfo = niftiContainerBlock.find_nifti_info_list_by_name(targetName)
        targetphaseInfo = niftiContainerBlock.find_phase_info(targetNiftiInfo[0].MaskInfo.Phase)

        iPhaseCnt = niftiContainerBlock.get_phase_info_count()
        for inx in range(0, iPhaseCnt) :
            phaseInfo = niftiContainerBlock.get_phase_info(inx)
            phaseInfo.Offset = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0]) - originOffsetBlock.OutputOriginOffset
            phaseInfo.m_origin = targetphaseInfo.m_origin
            phaseInfo.m_spacing = targetphaseInfo.m_spacing
            phaseInfo.m_direction = targetphaseInfo.m_direction
            phaseInfo.m_size = targetphaseInfo.m_size
            
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


class CCommandReconDevelopColon(CCommandReconDevelop) :
    '''
    Desc : common pipeline reconstruction step에서 Recon 수행
    '''

    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
    def clear(self):
        # input your code
        super().clear()
    def process(self):
        super().process()
        # input your code

        # 기존 blender 파일이 있을 경우 로딩만 수행 
        if os.path.exists(self.OutputBlenderFullPath) == True :
            CCommandReconInterface.blender_process_load(self.BlenderExe, self.OutputBlenderFullPath)
            return

        niftiContainerBlock = niftiContainer.CNiftiContainerTerritory()
        niftiContainerBlock.InputOptionInfo = self.InputData.OptionInfo
        niftiContainerBlock.InputPath = self.PatientMaskPath
        niftiContainerBlock.process()

        originOffsetBlock = originOffset.COriginOffset()
        originOffsetBlock.InputOptionInfo = self.InputData.OptionInfo
        originOffsetBlock.InputNiftiContainer = niftiContainerBlock
        originOffsetBlock.process()

        registrationBlock = registration.CRegistration()
        registrationBlock.InputOptionInfo = self.InputData.OptionInfo
        registrationBlock.InputNiftiContainer = niftiContainerBlock
        registrationBlock.process()

        self._update_phase_offset(self.InputData.OptionInfo, niftiContainerBlock, registrationBlock, originOffsetBlock)
        fileSavePhaseInfoBlock = niftiContainer.CFileSavePhaseInfo()
        fileSavePhaseInfoBlock.InputNiftiContainer = niftiContainerBlock
        fileSavePhaseInfoBlock.m_outputSavePath = self.OutputPatientPath
        fileSavePhaseInfoBlock.m_outputFileName = CCommandReconInterface.s_phaseInfoFileName
        fileSavePhaseInfoBlock.process()

        removeStrictureBlock = removeStricture.CRemoveStricture()
        removeStrictureBlock.InputNiftiContainer = niftiContainerBlock
        removeStrictureBlock.process()

        reconstructionBlock = reconstruction.CReconstruction()
        reconstructionBlock.InputOptionInfo = self.InputData.OptionInfo
        reconstructionBlock.InputNiftiContainer = niftiContainerBlock
        reconstructionBlock.OutputPath = self.OutputResultPath
        reconstructionBlock.process()

        meshHealingBlock = meshHealing.CMeshHealing()
        meshHealingBlock.InputPath = self.OutputResultPath
        meshHealingBlock.InputOptionInfo = self.InputData.OptionInfo
        meshHealingBlock.process()

        meshBooleanBlock = meshBoolean.CMeshBoolean()
        meshBooleanBlock.InputPath = self.OutputResultPath
        meshBooleanBlock.InputOptionInfo = self.InputData.OptionInfo
        meshBooleanBlock.process()

        # ureter 하드코딩 임시 
        ureterMaskName = "ureter-MR"
        listMaskInfo = self.InputData.OptionInfo.find_maskinfo_list_by_name(ureterMaskName)
        listNiftiInfo = niftiContainerBlock.find_nifti_info_list_by_name(ureterMaskName)
        maskInfo = listMaskInfo[0]
        niftiInfo = listNiftiInfo[0]
        phaseInfo = niftiContainerBlock.find_phase_info(niftiInfo.MaskInfo.Phase)
        if listMaskInfo is not None and listNiftiInfo is not None and phaseInfo is not None :
            inputNiftiFullPath = niftiInfo.FullPath
            outputPath = self.OutputResultPath
            resNiftiFullPath = os.path.join(outputPath, f"{ureterMaskName}.nii.gz")

            if os.path.exists(inputNiftiFullPath) == True :
                origin = phaseInfo.Origin
                spacing = phaseInfo.Spacing
                direction = phaseInfo.Direction

                targetSize = [256, 256, 256]
                minSpacing = min(spacing)
                maxSpacing = max(spacing)
                newSpacing = (minSpacing + maxSpacing) / 2.0
                targetSpacing = [newSpacing, newSpacing, newSpacing]

                npImg, origin, spacing, direction, size = algImage.CAlgImage.get_np_from_nifti(inputNiftiFullPath)
                sitkImg = algImage.CAlgImage.get_sitk_from_np(npImg, origin, spacing, direction)

                # resampling
                resampledSitkImg =  algImage.CAlgImage.resampling_sitkimg_with_mat(
                    sitkImg, 
                    origin, targetSpacing, direction, targetSize, sitkImg.GetPixelID(), sitk.sitkNearestNeighbor,
                    None
                )
                npResImg, newOrigin, newSpacing, newDirection, newSize = algImage.CAlgImage.get_np_from_sitk(resampledSitkImg, np.uint8)
                algImage.CAlgImage.save_nifti_from_np(resNiftiFullPath, npResImg, newOrigin, newSpacing, newDirection, (2, 1, 0))

                # recon
                reconType = maskInfo.ReconType
                reconParam = self.InputData.OptionInfo.find_recon_param(reconType)
                contour = reconParam.Contour
                algorithm = reconParam.Algorithm
                param = reconParam.Param
                gaussian = reconParam.Gaussian
                resampling = reconParam.ResamplingFactor
                polyData = reconstruction.CReconstruction.reconstruction_nifti(
                    resNiftiFullPath, 
                    newOrigin, newSpacing, newDirection, phaseInfo.Offset, 
                    contour, param, algorithm, gaussian, resampling, True
                    )
                
                blenderName = maskInfo.BlenderName
                stlFullPath = os.path.join(outputPath, f"{blenderName}.stl")
                algVTK.CVTK.save_poly_data_stl(stlFullPath, polyData)
                print("completed ureter recon")
            else :
                print("not found ureter mask file")
        else :
            print("not found ureter maskinfo")

        niftiContainerBlock.clear()
        originOffsetBlock.clear()
        registrationBlock.clear()
        removeStrictureBlock.clear()
        reconstructionBlock.clear()
        fileSavePhaseInfoBlock.clear()
        meshHealingBlock.clear()
        meshBooleanBlock.clear()

        self._process_blender()


    # protected
    def _process_blender(self) :
        blenderExe = self.BlenderExe
        scriptFullPath = self.ScriptFullPath
        inputPath = self.OutputResultPath
        outputPath = self.OutputPatientPath
        saveName = self.InputSaveBlenderName
        CCommandReconInterface.blender_process(blenderExe, scriptFullPath, self.InputData.DataInfo.OptionFullPath, inputPath, outputPath, saveName, False)

        



class CCommandReconDevelopClean(CCommandReconDevelop) :
    '''
    Desc : common pipeline reconstruction step에서 Clean 수행
    '''

    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
    def clear(self):
        # input your code
        super().clear()
    def process(self):
        super().process()
        # input your code
        self._process_blender()


    # protected
    def _process_blender(self) : 
        blenderExe = self.BlenderExe
        scriptFullPath = self.ScriptFullPath
        inputPath = self.OutputPatientPath
        outputPath = self.OutputPatientPath
        saveName = self.InputSaveBlenderName
        blenderFullPath = os.path.join(outputPath, f"{saveName}.blend")
        CCommandReconInterface.blender_process_load_script(blenderExe, blenderFullPath, scriptFullPath, self.InputData.DataInfo.OptionFullPath, inputPath, outputPath, saveName, False)

        

if __name__ == '__main__' :
    pass


# print ("ok ..")

