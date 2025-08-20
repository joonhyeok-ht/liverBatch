import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import SimpleITK as sitk

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileStatePath = os.path.dirname(fileAbsPath)
fileAppPath = os.path.dirname(fileStatePath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileStatePath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algVTK as algVTK
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algMeshLib as algMeshLib

import Block.optionInfo as optionInfo

import command.curveInfo as curveInfo

import data as data

import userData as userData



class CDragProcess : 
    def __init__(self, mediator) :
        self.m_mediator = mediator
        self.m_app = mediator.m_mediator
        self.m_startX = 0
        self.m_startY = 0
        self.m_endX = 0
        self.m_endY = 0
    def clear(self) :
        self.m_mediator = None
        self.m_startX = 0
        self.m_startY = 0
        self.m_endX = 0
        self.m_endY = 0


    def click(self, clickX : int, clickY : int) :
        self.m_startX = clickX
        self.m_startY = clickY
        self.m_endX = clickX
        self.m_endY = clickY
    def click_with_shift(self, clickX : int, clickY : int) :
        pass
    def release(self, clickX : int, clickY : int) :
        self.m_endX = clickX
        self.m_endY = clickY
    def move(self, clickX : int, clickY : int) :
        self.m_endX = clickX
        self.m_endY = clickY
        

    

if __name__ == '__main__' :
    pass


# print ("ok ..")

