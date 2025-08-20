import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import copy
import SimpleITK as sitk

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

import data as data

import userData as userData

import command.commandRecon as commandRecon


class CUserDataCommon(userData.CUserData) :
    s_userDataKey = "Common"


    def __init__(self, data : data.CData, mediator):
        super().__init__(data, CUserDataCommon.s_userDataKey)
        # input your code
        self.m_mediator = mediator
    def clear(self) :
        # input your code
        self.m_mediator = None
        super().clear()

    def load_patient(self) -> bool :
        if super().load_patient() == False :
            return False
        # input your code
        
        return True
    

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
    


    

    @property
    def Data(self) -> data.CData :
        return self.m_data

    

if __name__ == '__main__' :
    pass


# print ("ok ..")

