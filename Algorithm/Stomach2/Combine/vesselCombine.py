import numpy as np
from scipy import optimize
import matplotlib.pyplot as plt
import SimpleITK as sitk
import cv2
import os, sys
import matplotlib.patches as patches

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

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
    - VesselCombineBlock
Input
    - "InputPath"           : niftiPath
Output
    - "OutputFile"          : combined nifti file full name
Property
    - "Active"
    - "AddVesselName"
'''
class CVesselCombine() : 
    def __init__(self) -> None : 
        # input your code
        self.m_inputPath = ""
        self.m_outputFile = ""
        self.m_listVesselName = []
        self.m_mask = None
    def process(self) :
        for vesselName in self.m_listVesselName :
            fullPath = os.path.join(self.InputPath, vesselName)
            if os.path.exists(fullPath) == False :
                print(f"not found combining nifti name : {fullPath}")
                continue
            if self.m_mask is None :
                self.m_mask, self.m_origin, self.m_spacing, self.m_direction = scoBuffer.CScoBuffer3D.create_instance(fullPath, (2, 1, 0), "uint8", "uint8", 255, 0)
            else :
                self._combine(fullPath)
        self.__save_nifti(self.OutputFile, self.m_mask)
    def clear(self) :
        self.m_inputPath = ""
        self.m_outputFile = ""
        self.m_listVesselName.clear()
        self.m_mask.clear()
        self.m_mask = None


    def add_vessel(self, niftiName : str) :
        self.m_listVesselName.append(niftiName)
    

    # protected
    def _combine(self, combiningNiftiFullPath : str) : 
        mask, self.m_origin, self.m_spacing, self.m_direction = scoBuffer.CScoBuffer3D.create_instance(combiningNiftiFullPath, (2, 1, 0), "uint8", "uint8", 255, 0)
        xInx, yInx, zInx = mask.get_voxel_inx_with_greater(0)
        self.m_mask.set_voxel((xInx, yInx, zInx), 255)


    # private
    def __save_nifti(self, niftiFullPath : str, mask : scoBuffer.CScoBuffer3D) :
        sitkImg = mask.get_sitk_img(self.m_origin, self.m_spacing, self.m_direction, (2, 1, 0))
        scoUtil.CScoUtilSimpleITK.save_nifti(niftiFullPath, sitkImg)
    

    @property
    def InputPath(self) :
        return self.m_inputPath
    @InputPath.setter
    def InputPath(self, inputPath : str) :
        self.m_inputPath = inputPath
    @property
    def OutputFile(self) :
        return self.m_outputFile
    @OutputFile.setter
    def OutputFile(self, outputFile : str) :
        self.m_outputFile = outputFile
        dir = os.path.basename(outputFile)
        if not os.path.exists(dir) :
            os.makedirs(dir)

    

    






