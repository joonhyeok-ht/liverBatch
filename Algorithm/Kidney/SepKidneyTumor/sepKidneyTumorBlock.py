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
sys.path.append("/home/pipeline/Algorithm/Kidney/SepKidneyTumor")

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
import sepKidneyTumor



'''
Name
    - SepKidneyTumorBlock
Input
    - "InputDP"     : kidney dp folder that include exo
Output
    - "DP"          : output folder that output separated kidney nifti
Property
    - "Active"
'''

class CBlockSepKidneyTumor(block.CBlock) :
    def __init__(self, globalInfo : dict) -> None:
        super().__init__(globalInfo)
    
    def process(self)  -> bool :
        if super().process() == False :
            print("----- Skip SepKidneyTumorBlock -----")
            return False
        
        # input your code
        print("----- Start SepKidneyTumorBlock -----")

        self.m_yourCode.process()

        self.output("DP", self.m_yourCode.SavePath)

        print("----- Completed SepKidneyTumorBlock -----")

        return True
    def clear(self) :
        super().clear()
    def init_port(self) :
        self.m_yourCode = sepKidneyTumor.CSepKidneyTumor()

        self._add_input_key("InputDP", self.input_dp)
        self._add_output_key("DP")
    def const_output(self, outputKey : str, value) :
        if outputKey == "DP" :
            self.m_yourCode.SavePath = value
    def property(self, propertyKey : str, value) :
        super().property(propertyKey, value)
        # input your code

    def input_dp(self, param) :
        self.m_yourCode.KidneyPath = param

