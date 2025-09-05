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

import data as data

import userData as userData


class CUserDataLung(userData.CUserData) :
    s_userDataKey = "Lung"


    def __init__(self, data : data.CData, mediator):
        super().__init__(data, CUserDataLung.s_userDataKey)
        # input your code
        self.m_mediator = mediator
        self.m_currPatientID = ''
        
    def clear(self) :
        # input your code

        super().clear()

    def load_patient(self) -> bool :
        # if super().load_patient() == False :
        #     return False
        if self.Data is None :
            return False
        if self.Data.OptionInfo is None :
            return False
        if self.Data.DataInfo.PatientPath == "" :
            return False
        if self.Data.DataInfo.PatientID == "" :
            return False
        
        dataRootPath = self.Data.OptionInfo.DataRootPath
        patientID = self.Data.DataInfo.PatientID
        patientMaskFullPath = os.path.join(dataRootPath, patientID, "02_SAVE", "01_MASK", "AP")
        if os.path.exists(patientMaskFullPath) == False :
            print("CUserDataLung : not found patient mask folder")
            return False
        print(f"userDataLung - PatientMaskFullPath : {patientMaskFullPath}")
        # input your code
       
        return True
    
    @property
    def Data(self) -> data.CData :
        return self.m_data

    

if __name__ == '__main__' :
    pass


# print ("ok ..")

