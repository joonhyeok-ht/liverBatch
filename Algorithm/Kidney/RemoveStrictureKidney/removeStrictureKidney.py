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

import blockKidney


'''
Name
    - RemoveStrictureKidneyBlock
Input
    - "Input"       : input mask folder
Output
    - "Output"      : output mask folder
Property
    - "Active"
    - "AddNiftiFile" : nifti file
'''

class CRemoveStrictureKidney :
    def __init__(self) -> None:
        self.m_input = ""
        self.m_output = ""
        self.m_listNiftiFile = []
    def process(self) :
        for reconType in self.m_listNiftiFile :
            self.__stricture(reconType)
    def clear(self) :
        self.m_input = ""
        self.m_output = ""
        self.m_listNiftiFile.clear()

    def add_nifti_file(self, niftiFile : str) :
        self.m_listNiftiFile.append(niftiFile)


    @property
    def Input(self) -> str :
        return self.m_input
    @Input.setter
    def Input(self, inputPath : str) :
        self.m_input = inputPath
    @property
    def Output(self) -> str :
        return self.m_output
    @Output.setter
    def Output(self, outputPath : str) :
        self.m_output = outputPath
        

    # private
    def __stricture(self, niftiFileName : str) :
        inputFullPath = os.path.join(self.Input, niftiFileName)
        outputFullPath = os.path.join(self.Output, niftiFileName)
        if os.path.exists(inputFullPath) == False :
            print(f"not found stricture {niftiFileName}")
            return

        algRemoveStricture = scoBufferAlg.CAlgRemoveStricture()
        mask, self.m_origin, self.m_spacing, self.m_direction = scoBuffer.CScoBuffer3D.create_instance(inputFullPath, (2, 1, 0), "uint8", "uint8", 1, 0)
        algRemoveStricture.process(mask)

        xVoxel, _, _ = algRemoveStricture.RemovedStrictureMask.get_voxel_inx_with_greater(0)
        print(f"stricture mask count : {len(xVoxel)}, {outputFullPath}")

        self.__save_nifti(outputFullPath, algRemoveStricture.RemovedStrictureMask)
        print(f"saved removed stricture {niftiFileName}")
        algRemoveStricture.clear()
    def __save_nifti(self, niftiFullPath : str, mask : scoBuffer.CScoBuffer3D) :
        sitkImg = mask.get_sitk_img(self.m_origin, self.m_spacing, self.m_direction, (2, 1, 0))
        scoUtil.CScoUtilSimpleITK.save_nifti(niftiFullPath, sitkImg)





