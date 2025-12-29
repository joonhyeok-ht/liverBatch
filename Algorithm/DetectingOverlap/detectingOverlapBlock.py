import numpy as np
from scipy import optimize
import matplotlib.pyplot as plt
import SimpleITK as sitk
import cv2
import os, sys
import matplotlib.patches as patches

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append("/home/pipeline")
sys.path.append("/home/pipeline/Algorithm")
sys.path.append("/home/pipeline/Algorithm/DetectingOverlap")

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
import Algorithm.DetectingOverlap.detectingOverlap as detectingOverlap



'''
Name
    - DetectingOveralpBlock
Input
    - "InputPath"       : overlap 검출 대상인 stl 파일들이 저장 된 폴더 
Output
    - "OutputPath"      : zz_overlap_xxxx.stl 파일들이 저장 될 폴더 
    - "OutputJsonPath"  : log가 기록 될 json 파일의 full 경로를 넣는다.  세팅하지 않는다면 log는 기록되지 않는다. 
Property
    - "Active"          : 0 or 1
    - "AddSrcStlFile"   : overlap 검출 대상인 src stl file name 추가 
    - "TargetStlFile"   : overlap 검출 대상인 target stl file name 추가
'''

class CBlockDetectingOverlap(block.CBlock) :
    def __init__(self, globalInfo : dict) -> None:
        super().__init__(globalInfo)
    def process(self)  -> bool :
        if super().process() == False :
            print("----- Skip DetectingOverlapBlock -----")
            return False
        
        # input your code
        print("----- Start DetectingOverlapBlock -----")

        self.m_yourCode.process()

        self.output("OutputPath", self.m_yourCode.OutputPath)
        self.output("OutputJsonPath", self.m_yourCode.OutputJsonPath)

        print("----- Completed DetectingOverlapBlock -----")

        return True
    def clear(self) :
        self.m_yourCode.clear()
        super().clear()
    def init_port(self) :
        self.m_yourCode = detectingOverlap.CDetectingOverlap()

        self._add_input_key("InputPath", self.input_path)

        self._add_output_key("OutputPath")
        self._add_output_key("OutputJsonPath")
    def const_output(self, outputKey : str, value) :
        if outputKey == "OutputPath" :
            self.m_yourCode.OutputPath = value
        elif outputKey == "OutputJsonPath" :
            self.m_yourCode.OutputJsonPath = value
    def property(self, propertyKey : str, value) :
        super().property(propertyKey, value)
        # input your code
        if propertyKey == "AddSrcStlFile" :
            self.m_yourCode.add_src_stl_filename(value)
        elif propertyKey == "TargetStlFile" :
            self.m_yourCode.TargetStlFile = value
    

    def input_path(self, param) :
        self.m_yourCode.InputPath = param



