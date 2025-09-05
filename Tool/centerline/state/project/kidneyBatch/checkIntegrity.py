'''
File : checkIntegrity.py
Version : 2025_03_28
'''

# 241010 : 새로운 폴더 구조 반영. 
#       option.json만 사용하고 .data는 이미 확정된 option.json을 변환한 것이므로 사용하지 않음.
# 241014 : .data도 사용할 수 있도록 함. json 경로 대신 json data를 사용.
# 241101 : lung 에 적용하기 위해 phase 한개로 수정
# 250328 : 

import argparse as ap
import csv
import json
import numpy as np
import os
import shutil
import SimpleITK as sitk
import sys
from distutils.dir_util import copy_tree

tmpPath = os.path.abspath(os.path.dirname(__file__))
sys.path.append(tmpPath)

'''
Name
    - CheckIntegrity
Input
    - "PatientID"   : patient ID
    - "APPath"     : Early arterial phase nifti path
    - "OutputPath   : path for 'check.csv'
    - "MaskCopyPath": mask copy path
Output
    - "check.csv"
        [PatientID] ["Excluded" or "EmptyData"] ["Nifti File Name"]
'''

class CCheckIntegrity :
    s_checkFileName = "check.csv"

    def __init__(self) -> None:
        self.m_optionPath = ""
        self.m_patientID = ""
        # self.m_maskCpyPath = ""

        self.m_dataRootPath = ""
        self.m_jsonData = None
        self.m_apMaskPath = ""
        self.m_csvOutputPath = ""
        

    def _init(self) -> bool:
        if os.path.exists(self.m_optionPath) == False :
            print(f"CheckIntegrity - ERROR : option.json not exists!")
            return False
        ## Recon시 마스크를 카피하게 되어있어 아래 폴더는 현시점에 존재하지 않음. 원본 마스크를 검사하는 형태로 감.
        # if os.path.exists(self.m_maskCpyPath) == False :
        #     print(f"CheckIntegrity - ERROR : {self.m_maskCpyPath} not exists!")
        #     return False
        # option에서 DataRootPath 가져옴
        with open(self.m_optionPath, 'r') as jsonfile :
            jd = json.load(jsonfile)
            self.m_dataRootPath = jd["DataRootPath"]
            patient_path = os.path.join(self.m_dataRootPath, self.m_patientID)
            if os.path.exists(patient_path) == False :
                print(f"CheckIntegrity - ERROR : {patient_path} not exists!")
                return False

            # ap path, jsonData setting
            self.m_apMaskPath= os.path.join(self.m_dataRootPath, self.m_patientID, "02_SAVE", "01_MASK", "AP")
            self.m_csvOutputPath = os.path.join(self.m_dataRootPath, "check.csv") 
            
            self.m_jsonData = jd     
            return True        

            
    def process(self) -> bool :
        if self._init() == False :
            return False
        
        self.m_listJsonNiftiName = []
        self.m_csvFile = open(self.m_csvOutputPath, 'w', newline='')
        self.m_csvWr = csv.writer(self.m_csvFile)
        self.m_excludedList = []
        self.m_emptyList = []
        
        maskKey = "MaskInfo"

        if maskKey in self.m_jsonData :
            list_mask_info = self.m_jsonData[maskKey]
            for mask_info in list_mask_info:
                mask_name = mask_info['name']
                self.m_listJsonNiftiName.append(mask_name)
                

        result = self._check_integrity(self.m_patientID) 
        self.m_csvFile.close()

        
        print(f"{self.m_patientID} CheckIntegrity Done")
        return result
   
    
    def _check_zero_data_file(self, nifti : str) -> bool :
        nifti_path = os.path.join(self.m_apMaskPath, nifti)
        sitk_img = sitk.ReadImage(nifti_path)
        np_img = sitk.GetArrayViewFromImage(sitk_img)
        zInx, yInx, xInx = np.where(np_img > 0)
        if len(zInx) == 0 and len(yInx) == 0 and len(xInx) == 0 :
            return False
        return True
    
    def _check_integrity(self, patientID) -> bool :
        niftiFiles = os.listdir(self.m_apMaskPath)
        
        for nifti in niftiFiles:
            if nifti == '.DS_Store':
                continue
            #step1 : check excluded file
            niftiname = nifti.split('.')[0]
            # print(f"niftiname = {niftiname}")
            if niftiname not in self.m_listJsonNiftiName:
                print(f"excluded {niftiname}")
                self.m_csvWr.writerow([patientID,"Excluded", niftiname])
                self.m_excludedList.append(niftiname)
            
            #step2 : check zero data file (all of nifti files)
            check = self._check_zero_data_file(niftiname)
            if check == False:
                self.m_csvWr.writerow([patientID, "EmptyData", niftiname])
                print(f"empty data {niftiname}")
                self.m_emptyList.append(niftiname)

        if len(self.m_excludedList) == 0 and len(self.m_emptyList) == 0 :
            return True
        else :
            return False

    @property
    def OptionPath(self) :
        return self.m_optionPath
    @OptionPath.setter
    def OptionPath(self, path : str) :
        self.m_optionPath = path
    @property
    def PatientID(self) : 
        return self.m_patientID
    @PatientID.setter
    def PatientID(self, id : str) :
        self.m_patientID = id


if __name__ == "__main__" :    
    pass
    # checkIntegrity = CCheckIntegrity()
    # result = checkIntegrity.process()
    # if result :
    #     print("CheckIntegrity -> PASS")
    # else : 
    #     print("CheckIntegrity -> FAIL")