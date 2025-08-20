import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

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


import data as data


class CUserData :
    def __init__(self, data : data.CData, userDataKey : str):
        # input your code
        self.m_userDataKey = userDataKey
        self.m_data = data
    def clear(self) :
        # input your code
        self.m_userDataKey = ""
        self.m_data = None

    def load_patient(self) -> bool :
        if self.Data is None :
            return False
        if self.Data.OptionInfo is None :
            return False
        if self.Data.DataInfo.PatientPath == "" :
            return False
        if self.Data.DataInfo.PatientID == "" :
            return False
        
        # dataRootPath = self.Data.OptionInfo.DataRootPath
        # patientID = self.Data.DataInfo.PatientID
        # patientMaskFullPath = os.path.join(dataRootPath, os.path.join(patientID, "Mask"))
        # if os.path.exists(patientMaskFullPath) == False :
        #     print("not found patient mask folder")
        #     return False
        
        return True
    
    
    # override
    def override_recon(self, patientID : str, outputPath : str) :
        pass
    def override_clean(self, patientID : str, outputPath : str) :
        pass
    

    @property
    def UserDataKey(self) -> str :
        return self.m_userDataKey
    @property
    def Data(self) -> data.CData :
        return self.m_data
    @property
    def PatientID(self) -> str :
        return self.Data.DataInfo.PatientID
    @property
    def PatientMaskFullPath(self) -> str :
        dataRootPath = self.Data.OptionInfo.DataRootPath
        patientID = self.PatientID
        return os.path.join(dataRootPath, os.path.join(patientID, "Mask"))


    

if __name__ == '__main__' :
    pass


# print ("ok ..")

