import sys
import os
import numpy as np
import shutil
import glob
import vtk
import subprocess
import copy
import SimpleITK as sitk
import datetime as dt
from pathlib import Path

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
import Block.makeInputFolder as makeInputFolder

import data as data

import userData as userData

import command.commandRecon as commandRecon
import commandReconCommon as commandReconCommon


class CUserDataCommon(userData.CUserData) :
    s_intermediatePathAlias = "OutTemp"


    def __init__(self, datainst : data.CData, mediator) :
        super().__init__(datainst, mediator)
        # input your code

        self.m_resPath = ""
        self.m_scriptPath = ""
        self.m_reconScriptFullPath = ""
        self.m_cleanScriptFullPath = ""

        self.m_movingBlenderPath = ""
        self.m_outputTempPath = ""
        self.m_outputTempPatientPath = ""
        self.m_localReconBlenderFullPath = ""
        self.m_localCleanBlenderFullPath = ""
        self.m_outputReconBlenderFullPath = ""
        self.m_outputCleanBlenderFullPath = ""

        self.m_makeInputFolder = makeInputFolder.CMakeInputFolder()

        self.MovingBlenderPath = ""
    def clear(self) :
        # input your code
        self.m_resPath = ""
        self.m_scriptPath = ""
        self.m_reconScriptFullPath = ""
        self.m_cleanScriptFullPath = ""

        self.m_movingBlenderPath = ""
        self.m_outputTempPath = ""
        self.m_outputTempPatientPath = ""
        self.m_localReconBlenderFullPath = ""
        self.m_localCleanBlenderFullPath = ""
        self.m_outputReconBlenderFullPath = ""
        self.m_outputCleanBlenderFullPath = ""

        self.m_makeInputFolder.clear()

        super().clear()

    def set_patient_zippath(self, zipPath : str) :
        self.MakeInputFolder.clear()
        self.MakeInputFolder.ZipPath = zipPath
        self.MakeInputFolder.process()

        dataRootPath = self.MakeInputFolder.DataRootPath
        patientID = self.MakeInputFolder.PatientID
        datainst = self.Data

        self.m_outputTempPath = ""
        self.m_outputTempPatientPath = ""

        if self.MakeInputFolder.Ready == True :
            # datainst refresh 
            self.m_outputTempPath = os.path.join(os.path.dirname(dataRootPath), CUserDataCommon.s_intermediatePathAlias)
            self.m_outputTempPatientPath = os.path.join(self.m_outputTempPath, patientID)
            if os.path.exists(self.m_outputTempPath) == False :
                os.makedirs(self.m_outputTempPath, exist_ok=True)

            datainst.PatientID = patientID
            datainst.OutputPath = self.m_outputTempPath
            self.MovingBlenderPath = self.MakeInputFolder.BlenderSavePath
            
        else :
            datainst.PatientID = ""
            datainst.OutputPath = ""
            self.MovingBlenderPath = ""
            return
        
        self._refresh_optioninfo()
    

    # override
    def override_changed_optioninfo(self) :
        if self.Data.OptionInfo is None :
            optioninfoPath = ""
        else :
            optioninfoPath = self.Data.OptionInfoPath

        self.m_resPath = os.path.join(optioninfoPath, "Res")
        self.m_scriptPath = os.path.join(self.m_resPath, "common")
        self.m_reconScriptFullPath = os.path.join(self.m_scriptPath, "blenderScriptRecon.py")
        self.m_individualReconScriptFullPath = os.path.join(self.m_scriptPath, "blenderScriptIndRecon.py")
        self.m_cleanScriptFullPath = os.path.join(self.m_scriptPath, "blenderScriptClean.py")

        self.MakeInputFolder.clear()

        self.m_movingBlenderPath = ""
        self.m_outputTempPath = ""
        self.m_outputTempPatientPath = ""
        self.m_localReconBlenderFullPath = ""
        self.m_localCleanBlenderFullPath = ""
        self.m_outputReconBlenderFullPath = ""
        self.m_outputCleanBlenderFullPath = ""
    def override_recon(self) :
        # 기존에 존재할 경우 blender 로딩만 수행 
        if os.path.exists(self.m_outputReconBlenderFullPath) == True :
            userData.CUserData.blender_process_load(self.Data.OptionInfo.BlenderExe, self.m_outputReconBlenderFullPath)
            return
        
        datainst = self.Data
        optioninfo = datainst.OptionInfo
        folderinfo = self.MakeInputFolder

        # dataRoot의 Mask를 OutTemp로 복사
        copiedMaskPath = os.path.join(datainst.OutputPatientPath, "Mask")
        if os.path.exists(self.OutputReconBlenderFullPath) == False :
            folderinfo.copy_mask(copiedMaskPath)
        reconStlPath = os.path.join(datainst.OutputPatientPath, "Result")
        blendSavePath = datainst.OutputPatientPath

        # recon 수행 
        cmd = commandReconCommon.CCommandReconDevelopCommon(self.m_mediator)
        cmd.InputData = self.Data
        cmd.InputMaskPath = copiedMaskPath
        cmd.OutputPath = reconStlPath
        cmd.process()

        # blender 수행 
        blenderExe = optioninfo.BlenderExe
        scriptFullPath = self.m_reconScriptFullPath
        saveName = os.path.basename(self.m_localReconBlenderFullPath)
        saveName = saveName.split('.')[0]
        userData.CUserData.blender_process(blenderExe, scriptFullPath, optioninfo.m_jsonPath, reconStlPath, blendSavePath, saveName, False)

        # save blender folder로 move 
        if self.m_movingBlenderPath != "" :
            shutil.move(self.m_localReconBlenderFullPath, self.m_movingBlenderPath)
    def override_individual_recon(self, phaseinfo : dict) :
        datainst = self.Data
        optioninfo = datainst.OptionInfo
        folderinfo = self.MakeInputFolder

        tmpMaskPath = os.path.join(datainst.OutputPatientPath, "tmpMask")
        self._copy_phaseinfo(tmpMaskPath, phaseinfo)

        # targetMaskPath -> dataRoot Mask로 복사
        # dataRoot Mask -> OutTemp로 복사
        # optioninfo refresh
        copiedMaskPath = os.path.join(datainst.OutputPatientPath, "IndividualMask")
        for phase, _ in phaseinfo.items() :
            targetMaskPath = os.path.join(tmpMaskPath, phase)
            folderinfo.copy_target_mask(targetMaskPath, phase, copiedMaskPath)

        if os.path.exists(tmpMaskPath) == True :
            shutil.rmtree(tmpMaskPath)

        self._refresh_optioninfo()
        reconStlPath = os.path.join(datainst.OutputPatientPath, "IndividualResult")
        blendSavePath = os.path.dirname(self.OutputReconBlenderFullPath)

        cmd = commandReconCommon.CCommandReconDevelopCommon(self.m_mediator)
        cmd.InputData = self.Data
        cmd.InputMaskPath = copiedMaskPath
        cmd.OutputPath = reconStlPath
        cmd.process()

        # blender 수행 
        blenderExe = optioninfo.BlenderExe
        scriptFullPath = self.m_individualReconScriptFullPath
        saveName = os.path.basename(self.OutputReconBlenderFullPath)
        saveName = saveName.split('.')[0]
        userData.CUserData.blender_process_load_script(blenderExe, self.OutputReconBlenderFullPath, scriptFullPath, optioninfo.m_jsonPath, reconStlPath, blendSavePath, saveName, False)
        
        # remove input, output folders
        if os.path.exists(copiedMaskPath) == True :
            shutil.rmtree(copiedMaskPath)
        if os.path.exists(reconStlPath) == True :
            shutil.rmtree(reconStlPath)
    def override_clean(self) :
        pass
        # # 기존것은 지움
        # if os.path.exists(self.m_outputCleanBlenderFullPath) == True :
        #     os.remove(self.m_outputCleanBlenderFullPath)
        # # 새롭게 생성 
        # shutil.copy(self.m_outputReconBlenderFullPath, self.m_localCleanBlenderFullPath)

        # cmd = commandRecon.CCommandReconDevelopClean(self.m_mediator)
        # cmd.InputData = self.Data
        # cmd.InputBlenderScritpFullPath = self.m_cleanScriptFullPath
        # cmd.PatientBlenderFullPath = self.m_localCleanBlenderFullPath
        # cmd.process()

        # if self.m_movingBlenderPath != "" :
        #     shutil.move(self.m_localCleanBlenderFullPath, self.m_movingBlenderPath)
    def override_load_centerline(self) :
        pass


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
            # phaseFullPath = os.path.join(maskPath, phase)
            # maskList = os.listdir(phaseFullPath)
            # if len(maskList) == 0 :
            #     continue

            # maskList = [f.split('.')[0] for f in maskList]

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
        datainst = self.Data
        optioninfo = datainst.OptionInfo

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

        saveName = f"{patientID}"
        self.m_localCleanBlenderFullPath = os.path.join(self.OutputTempPatientPath, f"{saveName}.blend")
        if self.m_movingBlenderPath == "" :
            self.m_outputCleanBlenderFullPath = self.m_localCleanBlenderFullPath
        else :
            self.m_outputCleanBlenderFullPath = os.path.join(self.m_movingBlenderPath, f"{saveName}.blend")
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
    def MakeInputFolder(self) -> makeInputFolder.CMakeInputFolder :
        return self.m_makeInputFolder
    

if __name__ == '__main__' :
    pass


# print ("ok ..")

