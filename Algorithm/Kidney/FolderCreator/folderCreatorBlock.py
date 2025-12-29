import numpy as np
from scipy import optimize
import matplotlib.pyplot as plt
import SimpleITK as sitk
import cv2
import os, sys
import matplotlib.patches as patches
import json

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
sys.path.append("/home/pipeline")
sys.path.append("/home/pipeline/Algorithm")
sys.path.append("/home/pipeline/Algorithm/Kidney/FolderCreator")

import scoUtil
import scoData
import scoReg
import scoMath
import scoRenderObj
import scoSkeleton
import scoSkeletonVM
import scoBuffer
import scoBufferAlg

import block
import blockKidney
import folderCreator


'''
Name
    - KidneyServiceFolderCreatorBlock
Input
    - "DicomPath"           : input dicom folder that include phase folders
    - "MaskPath"            : input mask folder
Output
    - "PatientRootPath"     : patientID가 포함된 output folder
Property
    - "Active"
'''

class CBlockFolderCreator(block.CBlock) :
    def __init__(self, globalInfo : dict) -> None:
        super().__init__(globalInfo)

    def process(self)  -> bool :
        if super().process() == False :
            print("----- Skip FolderCreatorBlock -----")
            return False
        
        # input your code
        print("----- Start FolderCreatorBlock -----")

        self.m_yourCode.process()

        print("----- Completed FolderCreatorBlock -----")

        return True
    def clear(self) :
        super().clear()
    def init_port(self) :
        self.m_yourCode = folderCreator.CFolderCreator()
        
        self._add_input_key("DicomPath", self.dicom_path)
        self._add_input_key("MaskPath", self.mask_path)
        self._add_input_key("PatientRootPath", self.patient_root_path)

        # global
        createFolderNameCount = self.get_global_info("CreateFolderNameCount")
        for index in range(0, createFolderNameCount) :
            folderName = self.get_global_info(f"CreateFolderName[{index}]")
            self.m_yourCode.add_folder_name(folderName)
    def const_output(self, outputKey : str, value) :
        pass
    def property(self, propertyKey : str, value) :
        super().property(propertyKey, value)
        # input your code

    def dicom_path(self, param) :
        self.m_yourCode.DicomPath = param
    def mask_path(self, param) :
        self.m_yourCode.MaskPath = param
    def patient_root_path(self, param) :
        self.m_yourCode.PatientRootPath = param


# if __name__ == '__main__' :
#     block = CBlockFolderCreator()
#     block.process()

# print("clear ~~")




