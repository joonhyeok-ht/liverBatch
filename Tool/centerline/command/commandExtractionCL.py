import sys
import os
import platform
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

import commandInterface as commandInterface
# import territory as territory


class CCommandExtractionCL(commandInterface.CCommand) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_inputIndex = -1
        self.m_inputVTPName = ""
        self.m_inputCellID = -1
        self.m_inputEn = 0
        self.m_captureMode = False
        try :
        # PyInstaller로 패키징된 실행 파일의 경우
            self.fileAbsPath = sys._MEIPASS
            self.fileAbsPath = "."
        except AttributeError :
            # 개발 환경에서
            self.fileAbsPath = os.path.abspath(os.path.dirname(__file__))
    def clear(self) :
        # input your code
        self.m_inputIndex = -1
        self.m_inputVTPName = ""
        self.m_inputCellID = -1
        self.m_inputEn = 0
        self.m_captureMode = False
        super().clear()
    def process(self) :
        super().process()

        if self.InputIndex == -1 :
            return
        if self.InputVTPName == "" :
            return
        if self.InputCellID == -1 :
            return
        
        file = self.InputData.OutputPatientPath
        file = os.path.join(file, f"{data.CData.s_fileName}.json")
        if os.path.exists(file) == False :
            print(f"not found {os.path.basename(file)}")
            return
        index = self.InputIndex
        vtpName = self.InputVTPName
        cellID = self.InputCellID
        en = self.InputEn
        print("-- Start Extraction Centerline --")

        # 이 부분은 내 환경임 
        # shPath = "/Users/hutom/Desktop/solution/project/anaconda/Solution/UnitTestPrev/CommonPipeline_10/processCL.sh"
        optionPath = self.InputData.OptionInfoPath
        shPath = os.path.join(optionPath, self.OptionInfo.CL)
        print(f"clPath : {shPath}")
        print(f"--file : {file}")
        print(f"--index : {str(index)}")
        # result = subprocess.run([shPath], capture_output=True, text=True)
        if platform.system() != "Windows" : # Darwin or Linux
            result = subprocess.run([shPath, "--file", file, "--index", str(index), "--vtp", vtpName, "--cellID", str(cellID), "--en", str(en)], capture_output=self.CaptureMode, text=self.CaptureMode)
        else : #Windows
            bat = os.path.abspath(os.path.join(optionPath, self.OptionInfo.CL))
            cmd = ["cmd", "/c", bat,
                "--file", file,
                "--index", str(index),
                "--vtp", vtpName,
                "--cellID", str(cellID),
                "--en", str(en)]           
            print(f"(WIndows) cmd : {cmd}")
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="cp949", errors="replace")
        if self.CaptureMode == True :
            print(result.stdout)
            print(result.stderr)
        # else :
            # result = subprocess.run([shPath, "--file", file, "--index", str(index), "--vtp", vtpName, "--cellID", str(cellID), "--en", str(en)], capture_output=False, text=False)
        print(f"-- End Extraction Centerline --")


    @property
    def InputIndex(self) -> int :
        return self.m_inputIndex
    @InputIndex.setter
    def InputIndex(self, inputIndex : int) :
        self.m_inputIndex = inputIndex
    @property
    def InputVTPName(self) -> str :
        return self.m_inputVTPName
    @InputVTPName.setter
    def InputVTPName(self, inputVTPName : str) :
        self.m_inputVTPName = inputVTPName
    @property
    def InputCellID(self) -> int :
        return self.m_inputCellID
    @InputCellID.setter
    def InputCellID(self, inputCellID : int) :
        self.m_inputCellID = inputCellID
    @property
    def InputEn(self) -> int :
        return self.m_inputEn
    @InputEn.setter
    def InputEn(self, inputEn : int) :
        self.m_inputEn = inputEn
    @property
    def CaptureMode(self) -> bool :
        return self.m_captureMode
    @CaptureMode.setter
    def CaptureMode(self, captureMode : bool) :
        self.m_captureMode = captureMode








if __name__ == '__main__' :
    pass


# print ("ok ..")

