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
import gdOffset



'''
Name
    - GDOffsetBlock  (gradient descent offset)
Input
    - "InputSrcPath"        : the folder including src nifti files
    - "InputTargetPath"     : the folder including target nifti files
Output
    - "OutputOffset"        : offset in physical coord 
                              ex) [X, Y, Z]
Property
    - "Active"
    - "AddSrcNiftiFile"        
    - "AddTargetNiftiFile"
'''

class CBlockGDOffset(block.CBlock) :
    def __init__(self, globalInfo : dict) -> None:
        super().__init__(globalInfo)
    def process(self)  -> bool :
        if super().process() == False :
            print("----- Skip GDOffsetBlock -----")
            return False
        
        # input your code
        print("----- Start GDOffsetBlock -----")

        self.m_yourCode.process()

        self.output("OutputOffset", self.m_yourCode.OutputOffset)

        print("----- Completed GDOffsetBlock -----")

        return True
    def clear(self) :
        self.m_yourCode.clear()
        super().clear()
    def init_port(self) :
        self.m_yourCode = gdOffset.CGDOffset()

        self._add_input_key("InputSrcPath", self.input_src_path)
        self._add_input_key("InputTargetPath", self.input_target_path)
        self._add_output_key("OutputOffset")
    def const_output(self, outputKey : str, value) :
        if outputKey == "OutputOffset" :
            self.m_yourCode.OutputOffset = value
    def property(self, propertyKey : str, value) :
        super().property(propertyKey, value)
        # input your code
        if propertyKey == "AddSrcNiftiFile" :
            self.m_yourCode.add_src_nifti_file(value)
        elif propertyKey == "AddTargetNiftiFile" :
            self.m_yourCode.add_target_nifti_file(value)

    def input_src_path(self, param) :
        self.m_yourCode.InputSrcPath = param
    def input_target_path(self, param) :
        self.m_yourCode.InputTargetPath = param



