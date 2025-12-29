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
        
        return True
    
    
    # override
    def override_recon(self) :
        pass
    def override_clean(self, patientID : str, outputPath : str) :
        pass
    

    @property
    def UserDataKey(self) -> str :
        return self.m_userDataKey
    @property
    def Data(self) -> data.CData :
        return self.m_data


    

if __name__ == '__main__' :
    pass


# print ("ok ..")

