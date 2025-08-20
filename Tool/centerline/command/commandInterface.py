import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget
from PySide6.QtCore import Qt
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAppPath = os.path.dirname(fileAbsPath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algSegment as algSegment

import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer
import Block.reconstruction as reconstruction

import data as data
# import territory as territory


class CCommand :
    def __init__(self, mediator):
        self.m_mediator = mediator
        self.m_inputData = None
        self.m_patientBlenderFullPath = ""
    def clear(self) :
        self.m_mediator = None
        self.m_inputData = None
        self.m_patientBlenderFullPath = ""
    def process(self) :
        if self.m_inputData is None :
            print("not setting inputData")
            return
        
        # blenderName = optionInfo.COptionInfo.get_blender_name(optionInfo.COptionInfo.s_processName, self.InputData.DataInfo.PatientID)
        # self.m_patientBlenderFullPath = os.path.join(self.InputData.DataInfo.PatientPath, blenderName)


    def process_undo(self) :
        pass

    
    @property
    def OptionInfo(self) -> optionInfo.COptionInfoSingle :
        return self.InputData.OptionInfo
    @property
    def InputData(self) -> data.CData :
        return self.m_inputData
    @InputData.setter
    def InputData(self, inputData : data.CData) :
        self.m_inputData = inputData
    @property
    def PatientBlenderFullPath(self) -> str :
        return self.m_patientBlenderFullPath
    @PatientBlenderFullPath.setter
    def PatientBlenderFullPath(self, patientBlenderFullPath : str) :
        self.m_patientBlenderFullPath = patientBlenderFullPath


class CCommandContainer(CCommand) :
    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_listCmd = []
    def clear(self) :
        for cmd in self.m_listCmd :
            cmd.clear()
        self.m_listCmd.clear()
    def process(self) :
        for cmd in self.m_listCmd :
            cmd.process()
    def process_undo(self) :
        for cmd in reversed(self.m_listCmd) :
            cmd.process_undo()

    def add_cmd(self, cmd : CCommand) :
        self.m_listCmd.append(cmd)
    def get_cmd_count(self) -> int :
        return len(self.m_listCmd)
    def get_cmd(self, inx : int) -> CCommand :
        return self.m_listCmd[inx]



if __name__ == '__main__' :
    pass


# print ("ok ..")

