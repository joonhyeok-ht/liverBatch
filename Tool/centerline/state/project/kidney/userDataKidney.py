import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

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


import Block.optionInfo as optionInfo

import command.commandExport as commandExport
import command.commandRecon as commandRecon

import data as data

import userData as userData


class CUserDataKidney(userData.CUserData) :
    s_userDataKey = "Kidney"


    def __init__(self, data : data.CData, mediator):
        super().__init__(data, CUserDataKidney.s_userDataKey)
        # input your code
        self.m_mediator = mediator
        self.m_listKidney = []
        self.m_listExo = []
    def clear(self) :
        # input your code
        self.m_listKidney.clear()
        self.m_listExo.clear()
        
        super().clear()

    def load_patient(self) -> bool :
        if super().load_patient() == False :
            return False
        # input your code
        optionInfoInst = self.Data.OptionInfo
        iCnt = optionInfoInst.get_maskinfo_count()
        for inx in range(0, iCnt) :
            maskInfo = optionInfoInst.get_maskinfo(inx)
            if "Kidney" in maskInfo.Name :
                self.m_listKidney.append(maskInfo.BlenderName)
            if "exo" in maskInfo.Name :
                self.m_listExo.append(maskInfo.BlenderName)

        self._export_organ()
        
        return True

    def get_kidneyname_count(self) -> int :
        return len(self.m_listKidney)
    def get_kidneyname(self, inx : int) -> str :
        return self.m_listKidney[inx]
    def get_exoname_count(self) -> int :
        return len(self.m_listExo)
    def get_exoname(self, inx : int) -> str :
        return self.m_listExo[inx]
    

        # override
    def override_recon(self, patientID : str, outputPath : str) :
        cmd = commandRecon.CCommandReconDevelopCommon(self.m_mediator)
        cmd.InputData = self.Data
        cmd.InputPatientID = patientID
        cmd.InputBlenderScritpFileName = "blenderScriptRecon"
        cmd.InputSaveBlenderName = f"{patientID}_recon"
        cmd.OutputPath = outputPath
        cmd.process()
    def override_clean(self, patientID : str, outputPath : str) :
        blenderScritpFileName = "blenderScriptClean"
        saveBlenderName = f"{patientID}"

        outputPatientPath = os.path.join(outputPath, patientID)
        saveBlenderFullPath = os.path.join(outputPatientPath, f"{saveBlenderName}.blend")
        srcBlenderFullPath = os.path.join(outputPatientPath, f"{patientID}_recon.blend")

        if os.path.exists(srcBlenderFullPath) == False :
            print("not found recon blender file")
            return

        # 기존것은 지움
        if os.path.exists(saveBlenderFullPath) == True :
            os.remove(saveBlenderFullPath)
        # 새롭게 생성 
        shutil.copy(srcBlenderFullPath, saveBlenderFullPath)

        cmd = commandRecon.CCommandReconDevelopClean(self.m_mediator)
        cmd.InputData = self.Data
        cmd.InputPatientID = patientID
        cmd.InputBlenderScritpFileName = blenderScritpFileName
        cmd.InputSaveBlenderName = saveBlenderName
        cmd.OutputPath = outputPath
        cmd.process()
    

    # protected
    def _export_organ(self) :
        dataInst = self.Data
        terriInPath = dataInst.get_terri_in_path()
        
        commandExportInst = commandExport.CCommandExportList(self.m_mediator)
        commandExportInst.InputData = dataInst
        commandExportInst.OutputPath = terriInPath

        iCnt = self.get_kidneyname_count()
        for inx in range(0, iCnt) :
            kidneyName = self.get_kidneyname(inx)
            commandExportInst.add_blender_name(kidneyName)
        iCnt = self.get_exoname_count()
        for inx in range(0, iCnt) :
            exoName = self.get_exoname(inx)
            commandExportInst.add_blender_name(exoName)
        commandExportInst.process()
        commandExportInst.clear()
    
    
    @property
    def Data(self) -> data.CData :
        return self.m_data

    

if __name__ == '__main__' :
    pass


# print ("ok ..")

