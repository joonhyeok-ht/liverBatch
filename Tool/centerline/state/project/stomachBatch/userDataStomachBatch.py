import sys
import os
import json
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


class CUserDataStomach(userData.CUserData) :
    s_userDataKey = "StomachBatch"


    def __init__(self, data : data.CData, mediator):
        super().__init__(data, CUserDataStomach.s_userDataKey)
        # input your code
        self.m_mediator = mediator
        self.m_currPatientID = ""

        self.m_apPath = ""
        self.m_ppPath = ""
        self.m_dpPath = ""
        self.m_tumorPhase = ""   # tumor가 있는 phase. (value : 'AP', 'DP', 'PP')
        self.m_targetKidney = ""  # 정합의 기준(target)이 되는  
        self.m_srcKidney = [] # 정합의 Src가 되는 kidney 

    def clear(self) :
        # input your code

        super().clear()

    def load_patient(self) -> bool :
        jsonPath = self.Data.DataInfo.OptionFullPath
        if jsonPath == "" :
            return False
        # with open(jsonPath, 'r') as fp :
        #     self.m_jsonData = json.load(fp)
        # self.m_listReconParam = self.m_jsonData["ReconParam"]
        
        return True
    
    def get_recon_param_count(self) -> int:
        if self.m_listReconParam is not None :
            return len(self.m_listReconParam)
        return 0
    def get_recon_param_iter_cnt(self, index : int) -> str:
        reconParamInfo = self.m_listReconParam[index]
        return reconParamInfo["iterCnt"]
    def get_recon_param_relaxation(self, index : int) -> str:
        reconParamInfo = self.m_listReconParam[index]
        return reconParamInfo["relaxation"]
    def get_recon_param_decimation(self, index : int) -> str:
        reconParamInfo = self.m_listReconParam[index]
        return reconParamInfo["decimation"]
    def get_recon_param_anchor_cc(self, index : int) -> str:
        reconParamInfo = self.m_listReconParam[index]
        return reconParamInfo["anchorCC"]
    @property
    def Data(self) -> data.CData :
        return self.m_data
    @property
    def TumorPhase(self) -> str :
        return self.m_tumorPhase
    @property
    def TargetKidney(self) -> str :
        return self.m_targetKidney
    @property
    def SrcKidney(self) -> list :
        return self.m_srcKidney
    @property
    def PatientID(self) -> str :
        return self.m_currPatientID
    @PatientID.setter
    def PatientID(self, id : str) -> str :
        self.m_currPatientID = id

if __name__ == '__main__' :
    pass


# print ("ok ..")

