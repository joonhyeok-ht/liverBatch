import numpy as np
from scipy import optimize
import matplotlib.pyplot as plt
import SimpleITK as sitk
import cv2
import os, sys
import matplotlib.patches as patches

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
sys.path.append("/home/pipeline")
sys.path.append("/home/pipeline/Algorithm")
sys.path.append("/home/pipeline/Algorithm/PhysicalInfo")

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
import observerVolumeCheck



'''
Name
    - ObserverVolumeCheckBlock
Input
    - "InputPhyInfo"        : conn(PhysicalInfoBlock -> OutputJson)
    - "InputSTLPath"        : stl path including reconstruction stl files
Output
    - "OutputCSV"           : csv file full path
Property
}
'''
class CBlockObserverVolumeCheck(block.CBlock) :
    def __init__(self, globalInfo : dict) -> None:
        super().__init__(globalInfo)
    def process(self)  -> bool :
        if super().process() == False :
            print("----- Skip ObserverVolumeCheckBlock -----")
            return False
        
        # input your code
        print("----- Start ObserverVolumeCheckBlock -----")

        self.m_yourCode.process()

        self.output("OutputCSV", self.m_yourCode.OutputCSV)

        print("----- Completed ObserverVolumeCheckBlock -----")

        return True
    def clear(self) :
        self.m_yourCode.clear()
        super().clear()
    def init_port(self) :
        self.m_yourCode = observerVolumeCheck.CObserverVolumeCheck()
        self._add_input_key("InputPhyInfo", self.input_phy_info)
        self._add_input_key("InputSTLPath", self.input_stl_path)
        self._add_output_key("OutputCSV")
    def const_output(self, outputKey : str, value) :
        if outputKey == "OutputCSV" :
            self.m_yourCode.OutputCSV = value
    def property(self, propertyKey : str, value) :
        super().property(propertyKey, value)
        # input your code


    def input_phy_info(self, param) :
        self.m_yourCode.InputPhyInfo = param
    def input_stl_path(self, param) :
        self.m_yourCode.InputSTLPath = param



