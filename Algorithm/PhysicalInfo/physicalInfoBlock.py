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
import physicalInfo



'''
Name
    - PhysicalInfoBlock
Input
Output
    - "OutputJson"          : json file full path
Property
    - "Active"
    - "PhaseTable"
    - "AddNiftiPath"
    - "AddForceNiftiPath"
}
'''
class CBlockPhysicalInfo(block.CBlock) :
    def __init__(self, globalInfo : dict) -> None:
        super().__init__(globalInfo)
    def process(self)  -> bool :
        if super().process() == False :
            print("----- Skip PhysicalInfoBlock -----")
            return False
        
        # input your code
        print("----- Start PhysicalInfoBlock -----")

        self.m_yourCode.process()

        self.output("OutputJson", self.m_yourCode.OutputJson)

        print("----- Completed PhysicalInfoBlock -----")

        return True
    def clear(self) :
        self.m_yourCode.clear()
        super().clear()
    def init_port(self) :
        self.m_yourCode = physicalInfo.CPhysicalInfo()

        self._add_output_key("OutputJson")
    def const_output(self, outputKey : str, value) :
        if outputKey == "OutputJson" :
            self.m_yourCode.OutputJson = value
    def property(self, propertyKey : str, value) :
        super().property(propertyKey, value)
        # input your code
        if propertyKey == "AddNiftiPath" :
            self.m_yourCode.add_nifti_path(value)
        elif propertyKey == "AddForceNiftiPath" :
            self.m_yourCode.add_force_nifti_path(value)
        elif propertyKey == "PhaseTable" :
            self.m_yourCode.PhaseTable = value



