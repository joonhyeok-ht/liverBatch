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
sys.path.append("/home/pipeline/Algorithm/Recon")

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
import reconCC



'''
Name
    - ReconWithCCBlock
Input
    - "InputPath"       : folder including nifti files
    - "InputPhyInfo"    : physical info json path of nifti files (with physicalInfo)
Output
    - "OutputPath"      : the folder to copy recon files
    - "DebugCC"         : output csv file including stl and mask cc
Property
    - "Active"          : 0 or 1
    - "AddReconParam"   : [iterCnt, relaxation, decimation, anchorCC]
    - "AddNiftiFile     : nifti file name
global
    - "Debug"           : 0 or 1 
'''
class CBlockReconWithCC(block.CBlock) :
    def __init__(self, globalInfo : dict) -> None:
        super().__init__(globalInfo)
    def process(self)  -> bool :
        if super().process() == False :
            print("----- Skip ReconWithCCBlock -----")
            return False
        
        # input your code
        print("----- Start ReconWithCCBlock -----")

        self.m_yourCode.process()

        self.output("OutputPath", self.m_yourCode.OutputPath)
        self.output("DebugCC", self.m_yourCode.DbgCC)

        print("----- Completed ReconWithCCBlock -----")

        return True
    def clear(self) :
        self.m_yourCode.clear()
        super().clear()
    def init_port(self) :
        self.m_yourCode = reconCC.CReconWithCC()

        self._add_input_key("InputPath", self.input_path)
        self._add_input_key("InputPhyInfo", self.input_phy_info)

        self._add_output_key("OutputPath")
        self._add_output_key("DebugCC")

        # global
        dbg = self.get_global_info("Debug")
        self.m_yourCode.set_debug(dbg)
    def const_output(self, outputKey : str, value) :
        if outputKey == "OutputPath" :
            self.m_yourCode.OutputPath = value
        elif outputKey == "DebugCC" :
            self.m_yourCode.DbgCC = value
    def property(self, propertyKey : str, value) :
        super().property(propertyKey, value)
        # input your code
        if propertyKey == "AddReconParam" :
            self.m_yourCode.add_recon_param(value[0], value[1], value[2], value[3])
        elif propertyKey == "AddNiftiFile" :
            self.m_yourCode.add_nifti_file(value)
    

    def input_path(self, param) :
        self.m_yourCode.InputPath = param
    def input_phy_info(self, param) :
        self.m_yourCode.InputPhyInfo = param



