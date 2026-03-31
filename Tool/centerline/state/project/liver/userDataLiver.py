import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import copy
import SimpleITK as sitk
from pathlib import Path
import subRecon.subReconLiver as reconLiver
import progressWindow as PW
from PySide6.QtWidgets import QDialog, QMessageBox

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


import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algVTK as algVTK

import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer
import Block.makeInputFolder as makeInputFolder

import data as data

import userData as userData

import command.commandRecon as commandRecon
import commandReconCommon as commandReconCommon

import liver.subDetectOverlap.subDetectOverlapLiver as detectOverlap

class CUserDataLiver(userData.CUserData) :
    s_userDataKey = "Liver"
    s_intermediatePathAlias = "OutTemp"

    def __init__(self, data : data.CData, mediator):
        super().__init__(data, CUserDataLiver.s_userDataKey)
        # input your code
        self.m_mediator = mediator
        
        self.m_resPath = ""
        self.m_scriptPath = ""
        self.m_reconScriptFullPath = ""
        self.m_cleanScriptFullPath = ""
        self.m_remodelingSaveScriptFullPath = ""

        self.m_movingBlenderPath = ""
        self.m_outputTempPath = ""
        self.m_outputTempPatientPath = ""
        self.m_localReconBlenderFullPath = ""
        self.m_localCleanBlenderFullPath = ""
        self.m_outputOverlapBlenderFullPath = ""
        self.m_outputReconBlenderFullPath = ""
        self.m_outputCleanBlenderFullPath = ""
        self.m_registrationMethod = ""
        
        try:
            # PyInstaller로 패키징된 실행 파일의 경우
            self.fileAbsPath = sys._MEIPASS
            self.fileAbsPath = "."
        except AttributeError:
            # 개발 환경에서
            self.fileAbsPath = os.path.abspath(os.path.dirname(__file__))

        self.m_makeInputFolder = makeInputFolder.CMakeInputFolder()

        self.MovingBlenderPath = ""
    def clear(self) :
        # input your code
        self.m_mediator = None
        # input your code
        self.m_resPath = ""
        self.m_scriptPath = ""
        self.m_reconScriptFullPath = ""
        self.m_cleanScriptFullPath = ""
        self.m_remodelingSaveScriptFullPath = ""

        self.m_movingBlenderPath = ""
        self.m_outputTempPath = ""
        self.m_outputTempPatientPath = ""
        self.m_localReconBlenderFullPath = ""
        self.m_localCleanBlenderFullPath = ""
        self.m_outputOverlapBlenderFullPath = ""
        self.m_outputReconBlenderFullPath = ""
        self.m_outputCleanBlenderFullPath = ""
        self.m_registrationMethod = ""

        self.m_makeInputFolder.clear()

        super().clear()
        
        
    def _generate_progress_window(self, instance):
        dialog = PW.ProgressWindow(self.m_mediator, instance)
        result = dialog.exec()

        if result == QDialog.Accepted:
            QMessageBox.information(self.m_mediator, "Done", "작업이 완료되었습니다!")
            return True
        elif result == QDialog.Rejected:
            QMessageBox.warning(self.m_mediator, "Canceled", "작업이 취소되었습니다.")
            return False
        

    def set_patient_zippath(self, zipPath : str) :
        self.MakeInputFolder.clear()
        self.MakeInputFolder.ZipPath = zipPath
        self.MakeInputFolder.process()

        dataRootPath = self.MakeInputFolder.DataRootPath
        patientID = self.MakeInputFolder.PatientID
        dataInst = self.Data

        self.m_outputTempPath = ""
        self.m_outputTempPatientPath = ""

        if self.MakeInputFolder.Ready == True :
            # dataInst refresh 
            self.m_outputTempPath = os.path.join(os.path.dirname(dataRootPath), CUserDataLiver.s_intermediatePathAlias)
            self.m_outputTempPatientPath = os.path.join(self.m_outputTempPath, patientID)
            if os.path.exists(self.m_outputTempPath) == False :
                os.makedirs(self.m_outputTempPath, exist_ok=True)

            dataInst.PatientID = patientID
            dataInst.OutputPath = self.m_outputTempPath
            self.MovingBlenderPath = self.MakeInputFolder.BlenderSavePath
            
        else :
            dataInst.PatientID = ""
            dataInst.OutputPath = ""
            self.MovingBlenderPath = ""
            return
        
        self._refresh_optioninfo()

    def load_patient(self) -> bool :
        if super().load_patient() == False :
            return False
        # input your code
        
        return True
    

    # override
    def override_changed_optioninfo(self) :
        super().override_changed_optioninfo()

        # input your code
        if self.Data.OptionInfo is None :
            optioninfoPath = ""
        else :
            optioninfoPath = self.Data.OptionInfoPath

        self.m_resPath = os.path.join(optioninfoPath, "Res")
        self.m_commonPath = os.path.join(self.m_resPath, "common")
        self.m_scriptPath = os.path.join(self.m_resPath, "liver_batch")
        self.m_reconScriptFullPath = os.path.join(self.m_scriptPath, "bspRecon.py")
        self.m_individualReconScriptFullPath = os.path.join(self.m_scriptPath, "bspIndRecon.py")
        self.m_cleanScriptFullPath = os.path.join(self.m_scriptPath, "bspClean.py")
        self.m_remodelingSaveScriptFullPath = os.path.join(self.m_scriptPath, "bspRemodelingImport.py")
        #self.m_cleanScriptFullPath = os.path.join(self.m_commonPath, "bsmClean.py")

        self.MakeInputFolder.clear()

        self.m_movingBlenderPath = ""
        self.m_outputTempPath = ""
        self.m_outputTempPatientPath = ""
        self.m_localReconBlenderFullPath = ""
        self.m_localCleanBlenderFullPath = ""
        self.m_outputReconBlenderFullPath = ""
        self.m_outputOverlapBlenderFullPath = ""
        self.m_outputCleanBlenderFullPath = ""
    def override_recon(self, inputSliceID) :
        dataInst = self.Data
        optioninfo = dataInst.OptionInfo
        
        # print("get_phase_list()!", file=sys.__stdout__, flush=True)
        # print(optioninfo.get_phase_list(), file=sys.__stdout__, flush=True)
        folderInfo = self.MakeInputFolder

        # dataRoot의 Mask를 OutTemp로 복사
        copiedMaskPath = os.path.join(dataInst.OutputPatientPath, "Mask")
        if os.path.exists(self.OutputReconBlenderFullPath) == False :
            folderInfo.copy_mask(copiedMaskPath)
        reconStlPath = os.path.join(dataInst.OutputPatientPath, "Result")
        blendSavePath = dataInst.OutputPatientPath

        # recon 수행 
        reconInst = reconLiver.CSubReconLiver()
        if self.m_registrationMethod == "non-rigid":
            reconInst.m_registrationMethod = self.m_registrationMethod
        reconInst.InputSliceID = inputSliceID
        reconInst.m_folderInfo = folderInfo
        reconInst.IntermediateDataPath = dataInst.OutputPatientPath
        reconInst.InputData = self.Data
        success = self._generate_progress_window(reconInst)
        reconInst.clear()
        if not success:
            return

        # blender 수행 
        '''
        param
            - "InputPath"       : import 할 mesh file들이 있는 folder  
            - "SaveFullPath"    : 저장 할 blend 파일명의 전체 경로
        '''
        dicParam = {
            "InputPath" : reconStlPath,
            "SaveFullPath" : self.m_localReconBlenderFullPath
        }
        optionFullPath = self._blender_script_param(dicParam)
        scriptFullPath = self.m_reconScriptFullPath

        # blenderExe = optioninfo.BlenderExe
        
        #self.m_reconScriptFullPath = os.path.join(self.fileAbsPath, 'blenderScriptLiver.py')
        # saveName = os.path.basename(self.m_localReconBlenderFullPath)
        # saveName = saveName.split('.')[0]
        #userData.CUserData.blender_process(blenderExe, scriptFullPath, dataInst.PatientID, "Basic", optioninfo.m_jsonPath, reconStlPath, blendSavePath, saveName, False)
        #userData.CUserData.blender_process(blenderExe, scriptFullPath, dataInst.PatientID, "Basic", optioninfo.m_jsonPath, reconStlPath, blendSavePath, saveName, False)
        self.blender_process(None, scriptFullPath, optionFullPath, False)

        # save blender folder로 move 
        if self.m_movingBlenderPath != "" :
            shutil.move(self.m_localReconBlenderFullPath, self.m_movingBlenderPath)
    def override_overlap(self):
        reconBlenderFullPath = self.m_outputReconBlenderFullPath
        if os.path.exists(reconBlenderFullPath) == False :
            print("not found blender file")
            return
        
        datainst = self.Data
        
        # 원본 blender는 복사 후 rename 
        shutil.copy2(reconBlenderFullPath, self.OutputOverlapBlenderFullPath)
        overlapBlenderFullPath = self.OutputOverlapBlenderFullPath

        listBlenderName = ["Artery", "Vein", "Portal", "Duct"]

        # blender 파일에서 listBlenderName 목록에 대해서만 clean 수행 
        # param 설정 
        '''
        param
            - "ListMeshName"    : clean-up 할 mesh name, None or 원소가 없다면 전체를 clean-up 한다.
            - "SaveFullPath"    : 저장 할 blend 파일명의 전체 경로, None or "" 라면 덮어쓴다. 
        '''
        dicParam = {
            "ListMeshName" : listBlenderName,
            "SaveFullPath" : None
        }
        scriptFullPath = self.m_cleanScriptFullPath
        optionFullPath = self._blender_script_param(dicParam)
        self.blender_process(overlapBlenderFullPath, scriptFullPath, optionFullPath, True)

        # export 
        exportPath = os.path.join(datainst.OutputPatientPath, "Overlap")
        self.blender_exporter(overlapBlenderFullPath, listBlenderName, exportPath)

        # overlap
        overlapinst = detectOverlap.CSubDetectOverlap()
        overlapinst.StlPath = exportPath
        overlapinst.LogPath = datainst.OutputPatientPath
        overlapinst.process()

        # import
        '''
        param
            - "StlPath"         : stl 파일들이 저장되어 있는 folder path, 없다면 "" 또는 None을 입력 
            - "ListStlFullPath  : stl파일들의 전체 경로를 저장한 list, 없다면 None을 입력 
        
        desc 
            - 기존 내용에 추가적으로 stl 파일들을 import 한다. 
        '''
        dicParam = {
            "StlPath" : exportPath,
            "ListStlFullPath" : None
        }
        scriptPath = os.path.join(self.ResPath, "common")
        scriptFullPath = os.path.join(scriptPath, "bsmImportStl.py")
        optionFullPath = self._blender_script_param(dicParam)
        self.blender_process(overlapBlenderFullPath, scriptFullPath, optionFullPath, False)

        # clear 
        if os.path.exists(exportPath) == True :
            shutil.rmtree(exportPath)
            
            
        
    def override_clean(self) :
        overlapBlenderFullPath = self.OutputOverlapBlenderFullPath
        if os.path.exists(overlapBlenderFullPath) == False :
            return
        
        datainst = self.Data

        # 원본 blender는 복사 후 rename 
        shutil.copy2(overlapBlenderFullPath, self.OutputCleanBlenderFullPath)
        cleanBlenderFullPath = self.OutputCleanBlenderFullPath

        # blender 파일에 대해 import 수행 
        listStlPath = self._find_stl_path_from_out(datainst.OutputPatientPath)
        if len(listStlPath) > 0 :
            '''
            param
                - "StlPath"         : stl 파일들이 저장되어 있는 folder path, 없다면 "" 또는 None을 입력 
                - "ListStlFullPath  : stl파일들의 전체 경로를 저장한 list, 없다면 None을 입력 
            
            desc 
                - 기존 내용에 추가적으로 stl 파일들을 import 한다. 
            '''
            dicParam = {
                "StlPath" : None,
                "ListStlFullPath" : listStlPath
            }
            scriptPath = os.path.join(self.ResPath, "common")
            scriptFullPath = os.path.join(scriptPath, "bsmImportStl.py")
            optionFullPath = self._blender_script_param(dicParam)
            self.blender_process(cleanBlenderFullPath, scriptFullPath, optionFullPath, True)

        # blender 파일에 대해 clean 수행  
        # param 설정 
        '''
        param
            - "ListMeshName"    : clean-up 할 mesh name, None or 원소가 없다면 전체를 clean-up 한다.
            - "SaveFullPath"    : 저장 할 blend 파일명의 전체 경로, None or "" 라면 덮어쓴다. 
        '''
        dicParam = {
            "ListMeshName" : None,
            "SaveFullPath" : None
        }
        scriptFullPath = self.m_cleanScriptFullPath
        optionFullPath = self._blender_script_param(dicParam)
        self.blender_process(cleanBlenderFullPath, scriptFullPath, optionFullPath, False)
    
    def remodeling_blender_save(self, outputFolderPath):
        dataInst = self.Data
        outputFullPath =  os.path.join(outputFolderPath, f"{dataInst.PatientID}.blend")
        if os.path.exists(self.OutputCleanBlenderFullPath) == False :
            return

        # 원본 blender는 복사 후 rename 
        shutil.copy2(self.OutputCleanBlenderFullPath, outputFullPath)
        reconStlPath = dataInst.get_terri_out_path()
        
        '''
        param
            - "StlPath"    : remodeling된 stl 파일들이 저장되어 있는 folder path
            - "SaveFullPath"    : 저장 할 blend 파일명의 전체 경로
        '''
        dicParam = {
            "StlPath" : reconStlPath,
            "SaveFullPath" : outputFullPath
        }
        scriptFullPath = self.m_remodelingSaveScriptFullPath
        optionFullPath = self._blender_script_param(dicParam)
        self.blender_process(outputFullPath, scriptFullPath, optionFullPath, False)
    
    

    # protected
    def _refresh_optioninfo(self) :
        if self.MakeInputFolder.Ready == False :
            return
        optioninfo = self.Data.OptionInfo
        if optioninfo is None :
            return
        folderInfo = self.MakeInputFolder

        dataRootPath = self.MakeInputFolder.DataRootPath
        optioninfo.DataRootPath = dataRootPath
        
        
        maskPath = folderInfo.MaskPath
        p = Path(maskPath)
        phaseList = [f.name for f in p.iterdir() if f.is_dir()]

        phaseMaskList = []
        for phase in phaseList :
            phaseFullPath = Path(maskPath) / phase
            if not phaseFullPath.is_dir() :
                continue

            maskList = [
                f.name[:-7]
                for f in phaseFullPath.iterdir()
                if f.is_file() and f.name.endswith(".nii.gz")
            ]

            if not maskList :
                continue

            phaseMaskList.append({'phase': phase, 'files': maskList})

        '''
        key : maskName
        value : phase
        '''
        dicMaskPhase = {}
        for maskinfo in phaseMaskList :
            phase = maskinfo['phase']
            listMask = maskinfo['files']
            for maskName in listMask :
                dicMaskPhase[maskName] = phase

        # optioninfo mask의 phase refresh
        iCnt = optioninfo.get_recon_count()
        for reconInx in range(0, iCnt) :
            listCnt = optioninfo.get_recon_list_count(reconInx)
            for listInx in range(0, listCnt) :
                maskName, _, _, _ = optioninfo.get_recon_list(reconInx, listInx)
                phase = ""
                if maskName in dicMaskPhase :
                    phase = dicMaskPhase[maskName]
                optioninfo.set_recon_phase(maskName, phase)

        self._post_refresh_optioninfo()
    def _post_refresh_optioninfo(self) :
        dataInst = self.Data
        optioninfo = dataInst.OptionInfo
        
        # ResamplingToPhase 
        iCnt = optioninfo.get_resampling_phase_count()
        for inx in range(0, iCnt) :
            _, outMaskName, phase = optioninfo.get_resampling_phase(inx)
            optioninfo.set_recon_phase(outMaskName, phase)
        # ResamplingToMinSpacing 
        iCnt = optioninfo.get_resampling_minspacing_count()
        for inx in range(0, iCnt) :
            inMaskName, outMaskName = optioninfo.get_resampling_minspacing(inx)
            inPhase = optioninfo.find_phase_of_mask(inMaskName)
            optioninfo.set_recon_phase(outMaskName, inPhase)
        # Stricture 
        iCnt = optioninfo.get_stricture_count()
        for inx in range(0, iCnt) :
            inMaskName, outMaskName = optioninfo.get_stricture(inx)
            inPhase = optioninfo.find_phase_of_mask(inMaskName)
            optioninfo.set_recon_phase(outMaskName, inPhase)

        optioninfo.process_phase_alignment()
        
    def override_load_centerline(self) :
        pass
    def override_individual_recon(self, phaseinfo : dict) :
        dataInst = self.Data
        optioninfo = dataInst.OptionInfo
        folderinfo = self.MakeInputFolder

        tmpMaskPath = os.path.join(dataInst.OutputPatientPath, "tmpMask")
        self._copy_phaseinfo(tmpMaskPath, phaseinfo)

        # targetMaskPath -> dataRoot Mask로 복사
        # dataRoot Mask -> OutTemp로 복사
        # optioninfo refresh
        copiedMaskPath = os.path.join(dataInst.OutputPatientPath, "IndividualMask")
        for phase, _ in phaseinfo.items() :
            targetMaskPath = os.path.join(tmpMaskPath, phase)
            folderinfo.copy_target_mask(targetMaskPath, phase, copiedMaskPath)
            

        if os.path.exists(tmpMaskPath) == True :
            shutil.rmtree(tmpMaskPath)

        self._refresh_optioninfo()
        reconStlPath = os.path.join(dataInst.OutputPatientPath, "IndividualResult")


        # recon 수행 
        reconInst = reconLiver.CSubReconLiver()
        reconInst.m_folderInfo = self.MakeInputFolder
        reconInst.IntermediateDataPath = dataInst.OutputPatientPath
        reconInst.InputData = self.Data
        reconInst.m_resultPath = reconStlPath
        reconInst.m_maskCpyPath = copiedMaskPath
        success = self._generate_progress_window(reconInst)
        reconInst.clear()
        if not success:
            return

        '''
        param
            - "InputPath"       : import 할 mesh file들이 있는 folder  
        '''
        dicParam = {
            "InputPath" : reconStlPath
        }
        scriptFullPath = self.m_individualReconScriptFullPath
        optionFullPath = self._blender_script_param(dicParam)
        self.blender_process(self.OutputReconBlenderFullPath, scriptFullPath, optionFullPath, False)
 
        # remove input, output folders
        if os.path.exists(copiedMaskPath) == True :
            shutil.rmtree(copiedMaskPath)
        if os.path.exists(reconStlPath) == True :
            shutil.rmtree(reconStlPath)

    @property
    def Data(self) -> data.CData :
        return self.m_data
    @property
    def MovingBlenderPath(self) -> str :
        return self.m_movingBlenderPath
    @MovingBlenderPath.setter
    def MovingBlenderPath(self, movingBlenderPath : str) :
        folderInfo = self.MakeInputFolder
        patientID = folderInfo.PatientID

        self.m_movingBlenderPath = movingBlenderPath

        # saveName = f"{patientID}_recon_{timestr}"
        saveName = f"{patientID}_recon"
        self.m_localReconBlenderFullPath = os.path.join(self.OutputTempPatientPath, f"{saveName}.blend")
        if self.m_movingBlenderPath == "" :
            self.m_outputReconBlenderFullPath = self.m_localReconBlenderFullPath
        else :
            self.m_outputReconBlenderFullPath = os.path.join(self.m_movingBlenderPath, f"{saveName}.blend")
        
        saveName = f"{patientID}_overlap"
        dirPath = os.path.dirname(self.m_outputReconBlenderFullPath)
        self.m_outputOverlapBlenderFullPath = os.path.join(dirPath, f"{saveName}.blend")

        saveName = f"{patientID}_clean"
        dirPath = os.path.dirname(self.m_outputReconBlenderFullPath)
        self.m_outputCleanBlenderFullPath = os.path.join(dirPath, f"{saveName}.blend")
    @property
    def OutputTempPath(self) -> str :
        return self.m_outputTempPath
    @property
    def OutputTempPatientPath(self) -> str :
        return self.m_outputTempPatientPath
    @property
    def OutputReconBlenderFullPath(self) -> str :
        return self.m_outputReconBlenderFullPath
    @property
    def OutputCleanBlenderFullPath(self) -> str :
        return self.m_outputCleanBlenderFullPath
    @property
    def OutputOverlapBlenderFullPath(self) -> str :
        return self.m_outputOverlapBlenderFullPath
    @property
    def MakeInputFolder(self) -> makeInputFolder.CMakeInputFolder :
        return self.m_makeInputFolder
    @property
    def Data(self) -> data.CData :
        return self.m_data

    

if __name__ == '__main__' :
    pass


# print ("ok ..")

