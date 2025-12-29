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
    - VesselRemodelingBlock
Input
    - "InputPath"           : niftiPath
Output
    - "OutputPath"          : save path that include remodeled nifti file
Property
    - "Active"
    - "AddVesselName"
    - "AddByPassVesselName"
'''
class CVesselRemodeling() :
    def __init__(self) -> None:
        # input your code
        self.m_inputPath = ""
        self.m_outputPath = ""
        self.m_listVesselName = []
        self.m_listByPassVesselName = []
    def process(self) :
        for vesselName in self.m_listVesselName :
            self._stricture(vesselName)
        for vesselName in self.m_listByPassVesselName :
            self._bypass(vesselName)
    def clear(self) :
        self.m_inputPath = ""
        self.m_outputPath = ""
        self.m_listVesselName.clear()
        self.m_listByPassVesselName.clear()

    def add_vessel(self, niftiName : str) :
        self.m_listVesselName.append(niftiName)
    def add_bypass_vessel(self, niftiName : str) :
        self.m_listByPassVesselName.append(niftiName)
    

    # protected
    def _stricture(self, niftiName : str) :
        inputFullPath = os.path.join(self.InputPath, niftiName)
        outputFullPath = os.path.join(self.OutputPath, niftiName)

        if os.path.exists(inputFullPath) == False :
            print(f"not found stricture {niftiName}")
            return
        
        algRemoveStricture = scoBufferAlg.CAlgRemoveStricture()
        mask, self.m_origin, self.m_spacing, self.m_direction = scoBuffer.CScoBuffer3D.create_instance(inputFullPath, (2, 1, 0), "uint8", "uint8", 1, 0)
        algRemoveStricture.process(mask)
        self.__save_nifti(outputFullPath, algRemoveStricture.RemovedStrictureMask)
        print(f"saved removed stricture {niftiName}")
        algRemoveStricture.clear()
    def _dilation(self, niftiName : str) :
        inputFullPath = os.path.join(self.InputPath, niftiName)
        outputFullPath = os.path.join(self.OutputPath, niftiName)

        if os.path.exists(inputFullPath) == False :
            print(f"not found dilation {niftiName}")
            return
        
        mask, self.m_origin, self.m_spacing, self.m_direction = scoBuffer.CScoBuffer3D.create_instance(inputFullPath, (2, 1, 0), "uint8", "uint8", 1, 0)
        mask.dilation(3)
        self.__save_nifti(outputFullPath, mask)
        print(f"saved dilation {niftiName}")
        mask.clear()
    def _bypass(self, niftiName : str) :
        inputFullPath = os.path.join(self.InputPath, niftiName)
        outputFullPath = os.path.join(self.OutputPath, niftiName)

        if os.path.exists(inputFullPath) == False :
            print(f"not found bypass {niftiName}")
            return
        
        mask, self.m_origin, self.m_spacing, self.m_direction = scoBuffer.CScoBuffer3D.create_instance(inputFullPath, (2, 1, 0), "uint8", "uint8", 255, 0)
        self.__save_nifti(outputFullPath, mask)
        print(f"saved bypass {niftiName}")
        mask.clear()


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
    def OutputPath(self) :
        return self.m_outputPath
    @OutputPath.setter
    def OutputPath(self, outputPath : str) :
        self.m_outputPath = outputPath
        if not os.path.exists(outputPath) :
            os.makedirs(outputPath)

    

    






