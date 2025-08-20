import numpy as np
from scipy import optimize
import matplotlib.pyplot as plt
import SimpleITK as sitk
import cv2
import os, sys
import matplotlib.patches as patches
import json
import shutil
from distutils.dir_util import copy_tree

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
dirPath = os.path.join(os.path.abspath(os.path.dirname(__file__)), "../../")
sys.path.append(dirPath)

import scoUtil
import scoData
import scoReg
import scoMath
import scoRenderObj
import scoSkeleton
import scoSkeletonVM
import scoBuffer
import scoBufferAlg




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

class CFolderCreator :
    def __init__(self) -> None:
        self.m_dicomPath = ""
        self.m_maskPath = ""
        self.m_patientRootPath = ""
        self.m_listCreateFolderName = []
    
    def process(self) :
        # create output folder
        for path in self.m_listCreateFolderName :
            fullPath = os.path.join(self.m_patientRootPath, path)
            if not os.path.exists(fullPath) :
                os.makedirs(fullPath)

        self.__copy_dicom()
        self.__copy_mask()

    
    def add_folder_name(self, folderName : str) :
        self.m_listCreateFolderName.append(folderName)


    @property
    def DicomPath(self) -> str :
        return self.m_dicomPath
    @DicomPath.setter
    def DicomPath(self, dicomPath : str) :
        self.m_dicomPath = dicomPath
    @property
    def MaskPath(self) -> str :
        return self.m_maskPath
    @MaskPath.setter
    def MaskPath(self, maskPath : str) :
        self.m_maskPath = maskPath
    @property
    def PatientRootPath(self) -> str :
        return self.m_patientRootPath
    @MaskPath.setter
    def PatientRootPath(self, patientRootPath : str) :
        self.m_patientRootPath = patientRootPath
        

    # private
    def __copy_dicom(self) :
        print("-- copy dicom --")
        if not os.path.exists(self.m_dicomPath) :
            print("not found dicom path")
            return
        #inputPath = os.path.join(self.m_dicomPath, "*")
        inputPath = self.m_dicomPath
        outputPath = os.path.join(self.m_patientRootPath, self.m_listCreateFolderName[0])
        copy_tree(inputPath, outputPath)
        #terminalCmd = f"cp -r {inputPath} {outputPath}"
        #os.system(terminalCmd)
    def __copy_mask(self) :
        print("-- copy mask --")
        #inputPath = os.path.join(self.m_maskPath, "*.*")
        inputPath = self.m_maskPath
        outputPath = os.path.join(self.m_patientRootPath, self.m_listCreateFolderName[1])
        copy_tree(inputPath, outputPath)
        #terminalCmd = f"cp -rf {inputPath} {outputPath}"
        #os.system(terminalCmd)
    def __copy_mask_with_json(self) :
        with open(self.s_blockTypeFileName, 'r') as fp :
            listNiftiFileName = json.load(fp)["reconFileNames"]

        print("-- copy mask with json --")        
        for niftiFileName in listNiftiFileName :
            inputPath = os.path.join(self.m_maskPath, niftiFileName)
            outputPath = os.path.join(self.m_patientRootPath, self.m_listCreateFolderName[1])
            shutil.copy(inputPath, outputPath)
            #terminalCmd = f"cp -rf {inputPath} {outputPath}"
            #os.system(terminalCmd)




