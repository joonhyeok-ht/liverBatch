'''
File : checkIntegrity.py
Version : 2024_10_14
'''

# 241010 : 새로운 폴더 구조 반영. 
#       option.json만 사용하고 .data는 이미 확정된 option.json을 변환한 것이므로 사용하지 않음.
# 241014 : .data도 사용할 수 있도록 함. json 경로 대신 data를 사용.

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
    - "OptionPath"  : path for option.json
    - "EAPPath"     : Early arterial phase nifti path
    - "PPPath"      : Portal phase nifti path
    - "OutputPath   : path for 'check.csv'
    - "MaskCopyPath": mask copy path
Output
    - "check.csv"
        [PatientID] ["Excluded" or "EmptyData"] ["Nifti File Name"]
Information (Stomach)
    Input
        PatientID_1
            01_DICOM
                AP-Mask
                PP-Mask
            02_SAVE
                01_BLENDER_SAVE
                02_PNEUMO_SAVE
        PatientID_2
        ...
        PatientID_3
        ...        
    OutPut
        check.csv
'''

class CCheckIntegrity :
    # m_jsonFileName = "option.json"
    m_checkFileName = "Integrity_Check.csv"

    def __init__(self) -> None:
        self.m_patientID = ""
        # self.m_optionPath = ""
        self.m_jsonData = None
        self.m_eapPath = ""
        self.m_ppPath = ""
        self.m_outputPath = ""
        self.m_maskCpyPath = ""
        self.progress_callback  = None
        self.is_interrupted = lambda: False

    def process(self) -> bool :
        if self.m_patientID =='' :
            print(f"empty patientID")
            return False
        
        if self.m_jsonData == None :
            print(f"not valid json data.")
            return False

        if not os.path.exists(self.m_eapPath) :
            print(f"not found EAP_Path : {self.m_eapPath}")
            return False
        if not os.path.exists(self.m_ppPath) :
            print(f"not found PP_Path : {self.m_ppPath}")
            return False
        if not os.path.exists(self.m_outputPath) :
            print(f"not found Output_Path : {self.m_outputPath}")
            return False
        if not os.path.exists(self.m_maskCpyPath) :
            print(f"not found Mask_Copy_Path : {self.m_maskCpyPath}")
            return False
        
        
        self.m_checkFileName = os.path.join(self.m_outputPath, self.m_checkFileName)
        if os.path.exists(self.m_checkFileName):
            with open(self.m_checkFileName, 'w', newline='', encoding='utf-8') as f:
                pass
        

        self.m_listJsonNiftiName = []

        maskKey = "MaskInfo"
        m_listMask = []

        if maskKey in self.m_jsonData :
            m_listMask = self.m_jsonData[maskKey]
            for index, maskInfo in enumerate(m_listMask):
                maskNameExceptExt = maskInfo['name']
                self.m_listJsonNiftiName.append(maskNameExceptExt)
                
        self.m_csvFile = open(self.m_checkFileName, 'a', newline='')
        self.m_csvWr = csv.writer(self.m_csvFile)     

        self._copy_mask()
        surcess = self._check_integrity(self.m_patientID)
        if not surcess:
            return False
        
        self._clear()

        print(f"{self.m_patientID} CheckIntegrity Done")
        return True
    
    def _clear(self) :
        self.m_csvFile.close()
        if os.path.exists(self.m_maskCpyPath):
            # os.remove(self.m_maskCpyPath)
            shutil.rmtree(self.m_maskCpyPath)

    def _copy_mask(self) -> None :
        ## copy mask file (eap,pp mask file들을 지정된 폴더로 복사)
        copy_tree(self.m_eapPath, self.m_maskCpyPath)
        copy_tree(self.m_ppPath, self.m_maskCpyPath)
    
    def _check_zero_data_file(self, nifti : str) -> bool :
        nifti_path = os.path.join(self.m_maskCpyPath, nifti)
        sitk_img = sitk.ReadImage(nifti_path)
        np_img = sitk.GetArrayViewFromImage(sitk_img)
        zInx, yInx, xInx = np.where(np_img > 0)
        if len(zInx) == 0 and len(yInx) == 0 and len(xInx) == 0 :
            return False
        return True
    
    def _check_integrity(self, patientID) -> bool :
        niftiFiles = os.listdir(self.m_maskCpyPath)
        for i, nifti in enumerate(niftiFiles):
            if self.is_interrupted():
                return False
            
            if nifti == '.DS_Store':
                continue
            #step1 : check excluded file
            if nifti.split('.')[0] not in self.m_listJsonNiftiName:
                self.m_csvWr.writerow([patientID,"Excluded", nifti])
            #step2 : check zero data file (TP_ only)
            # if "TP_" in nifti:
            #     check = self._check_zero_data_file(nifti)
            #     if check == False:
            #         self.m_csvWr.writerow([patientID, "EmptyData", nifti])
            #         print(f"empty data {nifti}")
            #step2 : check zero data file (all of nifti files)
            
            check = self._check_zero_data_file(nifti)
            if check == False:
                self.m_csvWr.writerow([patientID, "EmptyData", nifti])
                print(f"empty data {nifti}")
                
            self.progress_callback(int(i / len(niftiFiles) * 99), "Check Integrity ...")
        
        self.progress_callback(100, "Check Integrity ...")
        return True

    @property
    def PatientID(self) :
        return self.m_patientID
    @PatientID.setter
    def PatientID(self, patientID : str) :
        self.m_patientID = patientID
    @property
    def EAPPath(self) :
        return self.m_eapPath
    @EAPPath.setter
    def EAPPath(self, eapPath : str) :
        self.m_eapPath = eapPath   
    @property
    def PPPath(self) :
        return self.m_ppPath
    @PPPath.setter
    def PPPath(self, ppPath : str) :
        self.m_ppPath = ppPath 
    @property
    def OutputPath(self) :
        return self.m_outputPath
    @OutputPath.setter
    def OutputPath(self, outputPath : str) :
        self.m_outputPath = outputPath  
    @property
    def MaskCopyPath(self) :
        return self.m_maskCpyPath
    @MaskCopyPath.setter
    def MaskCopyPath(self, maskCpyPath : str) :
        self.m_maskCpyPath = maskCpyPath

if __name__ == "__main__" :
    parser = ap.ArgumentParser()

    parser.add_argument('--patient_id', type=str, default='')
    # parser.add_argument('--option_path', type=str, default='')
    parser.add_argument('--eap_path', type=str, default='')
    parser.add_argument('--pp_path', type=str, default='')
    parser.add_argument('--out_path', type=str, default='')
    parser.add_argument('--cpy_path', type=str, default='')

    args = parser.parse_args()
    # print(args)
    checkIntegrity = CCheckIntegrity()
    checkIntegrity.PatientID = args.patient_id
    # checkIntegrity.OptionPath = args.option_path
    checkIntegrity.EAPPath = args.eap_path
    checkIntegrity.PPPath = args.pp_path
    checkIntegrity.OutputPath = args.out_path
    checkIntegrity.MaskCopyPath = args.cpy_path
    
    with open("./option.json", 'r') as fp :
        checkIntegrity.m_jsonData = json.load(fp)
    
    result = checkIntegrity.process()
    if result :
        print("CheckIntegrity -> PASS")
    else : 
        print("CheckIntegrity -> FAIL")