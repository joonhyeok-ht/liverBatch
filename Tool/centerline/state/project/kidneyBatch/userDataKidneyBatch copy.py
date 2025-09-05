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


class CUserDataKidney(userData.CUserData) :
    s_userDataKey = "KidneyBatch"


    def __init__(self, data : data.CData, mediator):
        super().__init__(data, CUserDataKidney.s_userDataKey)
        # input your code
        self.m_mediator = mediator
        self.m_currPatientID = ""

        self.m_apPath = ""
        self.m_ppPath = ""
        self.m_dpPath = ""
        self.m_tumorPhase = ""   # tumor가 있는 phase. (value : 'AP', 'DP', 'PP')
        self.m_targetKidney = ""  # 정합의 기준(target)이 되는 kidney 
        self.m_srcKidney = [] # 정합의 Src가 되는 kidney 

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
        # if self.Data.DataInfo.PatientID == "" :
        #     return False
        if self.m_currPatientID == "" :
            return False
        patientID = self.m_currPatientID
        
        dataRootPath = self.Data.OptionInfo.DataRootPath
        # patientID = self.Data.DataInfo.PatientID 없음.
        self.m_maskPath = os.path.join(dataRootPath, patientID, "02_SAVE", "01_MASK")
        self.m_apPath = os.path.join(self.m_maskPath, "Mask_AP")
        self.m_ppPath = os.path.join(self.m_maskPath, "Mask_PP")
        self.m_dpPath = os.path.join(self.m_maskPath, "Mask_DP")
        
        ## Tumor의 phase 찾기
        self._get_tumor_phase_with_kidney_name()
        
        return True
    def _get_tumor_phase_with_kidney_name(self) :
        tumor_phase = ""
        target_kidney = "" # 정합의 기준이 되는 Kidney name
        tumor = "Tumor_" 
        phaseMaskList = []
        list_ap = os.listdir(self.m_apPath)
        list_pp = os.listdir(self.m_ppPath)
        list_dp = os.listdir(self.m_dpPath)
        phaseMaskList.append({'phase':'AP', 'files': list_ap})
        phaseMaskList.append({'phase':'PP', 'files': list_pp})
        phaseMaskList.append({'phase':'DP', 'files': list_dp})
        findFlag = False
        for phaseMask in phaseMaskList :
            for mask in phaseMask['files'] :
                if tumor in mask :
                    tumor_phase = phaseMask['phase']
                    findFlag = True
                    break
            if findFlag :
                for mask in phaseMask['files'] :
                    if 'Kidney' in mask :
                        target_kidney = mask
                        break
        directionAndExtention = target_kidney.split(f"_{tumor_phase[0]}")[1]  # "Kidney_AL.nii.gz" -> "L.nii.gz"
        phases = ['AP','PP','DP']
        phases.remove(tumor_phase)
        srcs = []  # registration시 src가 되는 kidney 
        srcs.append(f"Kidney_{phases[0][0]}{directionAndExtention}")
        srcs.append(f"Kidney_{phases[1][0]}{directionAndExtention}")
        print(f"Tumor Phase : {tumor_phase}, Target Kidney : {target_kidney}, Src Kidney : {srcs}")   
        
        self.m_tumorPhase = tumor_phase
        self.m_targetKidney = target_kidney
        self.m_srcKidney = srcs
        
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

