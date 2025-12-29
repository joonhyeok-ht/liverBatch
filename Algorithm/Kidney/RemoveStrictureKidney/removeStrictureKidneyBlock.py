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
sys.path.append("/home/pipeline/Algorithm/Kidney/RemoveStrictureKidney")

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
import removeStrictureKidney


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

class CBlockRemoveStrictureKidney(block.CBlock) :
    def __init__(self, globalInfo : dict) -> None:
        super().__init__(globalInfo)

    def process(self)  -> bool :
        if super().process() == False :
            print("----- Skip RemoveStrictureKidneyBlock -----")
            return False
        
        # input your code
        print("----- Start RemoveStrictureKidneyBlock -----")

        self.m_yourCode.process()

        self.output("Output", self.m_yourCode.Output)

        print("----- Completed RemoveStrictureKidneyBlock -----")

        return True
    def clear(self) :
        self.m_yourCode.clear()
        super().clear()
    def init_port(self) :
        self.m_yourCode = removeStrictureKidney.CRemoveStrictureKidney()
        
        self._add_input_key("Input", self.input_mask_path)

        self._add_output_key("Output")
    def const_output(self, outputKey : str, value) :
        if outputKey == "Output" :
            self.m_yourCode.Output = value
    def property(self, propertyKey : str, value) :
        super().property(propertyKey, value)
        # input your code
        if propertyKey == "AddNiftiFile" :
            self.m_yourCode.add_nifti_file(value)

    def input_mask_path(self, param) :
        self.m_yourCode.Input = param


# if __name__ == '__main__' :
#     block = CBlockFolderCreator()
#     block.process()

# print("clear ~~")




