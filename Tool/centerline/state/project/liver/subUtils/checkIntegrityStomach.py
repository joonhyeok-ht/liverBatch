'''
File : checkIntegrityStomach.py
Version : 2024_10_14
'''

# 241010 : 새로운 폴더 구조 반영

'''
Name
    - CheckIntegrityStomach
Input
    - "OptionPath"  : path for option.json
Output
    - "check.csv"
        [PatientID] ["Excluded" or "EmptyData"] ["Nifti File Name"]
'''

import os, sys
import argparse as ap
import json
import math
import codecs

import subUtils.checkIntegrity as checkIntegrity

class CCheckIntegrityStomach(checkIntegrity.CCheckIntegrity) :
    def __init__(self) -> None :
        super().__init__()
        self.m_listPatientID = []
        self.m_dataRootPath = ""
        self.m_optionPath = ""
        
    def process(self) -> bool :
        if self._preprocess() == False :
            return False        
        patientIDList = self._get_patient_id_list()
        for patientID in patientIDList:
            self.PatientID = patientID
            self.EAPPath = os.path.join(self.m_dataRootPath, f"{patientID}","02_SAVE/01_MASK", "MASK_AP")
            self.PPPath = os.path.join(self.m_dataRootPath, f"{patientID}","02_SAVE/01_MASK","MASK_PP")
            self.OutputPath = os.path.join(self.m_dataRootPath)
            # outputPatientPath = os.path.join(self.m_maskCopyRoot, f"{patientID}")
            # if not os.path.exists(outputPatientPath) :
                # os.mkdir(outputPatientPath)
            
            # self.MaskCopyPath = os.path.join(outputPatientPath,"MaskCpy") 
            self.MaskCopyPath = os.path.join(self.m_dataRootPath, f"{patientID}", "IntegrityCheckTemp") 
            if not os.path.exists(self.MaskCopyPath) :
                os.mkdir(self.MaskCopyPath)
            if super().process() == False :
                return False
        return True
    
  
    
    # protected
    def _preprocess(self) -> bool :
        # self.m_jsonData = CJsonUtil.loadJson(self.m_optionPath)
        with open(self.m_optionPath, 'r') as fp :
            self.m_jsonData = json.load(fp)
        if self.m_jsonData == None :
            print(f"not valid json data.")
            return False
    
        self.m_dataRootPath = self.m_jsonData["DataRootPath"]
                        
        if self._find_patient_id() == False :
            print("no patientID folders")
            return False
        
        # self.m_maskCopyRoot = f"{self.m_dataRootPath}_Out"
        self.m_maskCopyRoot = self.m_dataRootPath
        if not os.path.exists(self.m_maskCopyRoot) :
            os.makedirs(self.m_maskCopyRoot)
        
        return True
    
    def _get_patient_id_list(self) -> list :
        return self.m_listPatientID

    def _find_patient_id(self) -> bool :
        listPatientID = os.listdir(self.m_dataRootPath)
        
        for patientID in listPatientID :
            if patientID == ".DS_Store" : 
                continue
            fullPath = os.path.join(self.m_dataRootPath, patientID)
            if os.path.isdir(fullPath) == False :
                continue

            self.m_listPatientID.append(patientID)
            # self.m_csvWr.writerow([patientID,patientID, patientID])
        if len(self.m_listPatientID) == 0 :
            return False
        return True
    @property
    def OptionPath(self) :
        return self.m_optionPath
    @OptionPath.setter
    def OptionPath(self, optionPath : str) :
        self.m_optionPath = optionPath    
if __name__=='__main__' :
    # test ok (24.05.22)
    inst = CCheckIntegrityStomach()    
    inst.OptionPath = "C:/Users/hutom/Desktop/jh_test/CommonPipelines/CommonPipeline_10_0509_stomach/CommonPipeline_10_0509_stomach/option.json"
    inst.process()
    

