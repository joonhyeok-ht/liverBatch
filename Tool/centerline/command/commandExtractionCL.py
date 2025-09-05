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
from pathlib import Path

import commandInterface as commandInterface
# import territory as territory


class CCommandExtractionCL(commandInterface.CCommand) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_inputIndex = -1
        self.m_inputCellID = -1
    def clear(self) :
        # input your code
        self.m_inputIndex = -1
        self.m_inputCellID = -1
        super().clear()
    # def process(self) :
    #     super().process()

    #     print("-- Start Extraction Centerline --")
    #     file = "clDataInfo.pkl"
    #     index = self.InputIndex
    #     cellID = self.InputCellID

    #     self.m_clInPath = self.InputData.get_cl_in_path()
    #     self.m_clOutPath = self.InputData.get_cl_out_path()
    #     pklFullPath = os.path.join(self.m_clInPath, file)

    #     data.CData.save_inst(pklFullPath, self.InputData.DataInfo)

    #     # 이 부분은 내 환경임 
    #     # shPath = "/Users/hutom/Desktop/solution/project/anaconda/Solution/UnitTestPrev/CommonPipeline_10/processCL.sh"
    #     optionPath = os.path.dirname(self.InputData.DataInfo.OptionFullPath)
    #     shPath = os.path.join(optionPath, self.OptionInfo.CL)
    #     print(f"clPath : {shPath}")
    #     print(f"pklFullPath : {pklFullPath}")
    #     print(f"--index : {str(index)}")
    #     # result = subprocess.run([shPath], capture_output=True, text=True)
    #     result = subprocess.run([shPath, "--file", pklFullPath, "--index", str(index), "--cellID", str(cellID)], capture_output=True, text=True)
    #     print(result.stdout)
    #     print(result.stderr)

    #     print("-- End Extraction Centerline --")
        
    def process(self) :
        super().process()

        print("-- Start Extraction Centerline --")
        file = "clDataInfo.pkl"
        index = self.InputIndex
        cellID = self.InputCellID

        self.m_clInPath = self.InputData.get_cl_in_path()
        self.m_clOutPath = self.InputData.get_cl_out_path()
        pklFullPath = os.path.join(self.m_clInPath, file)

        # pickle 저장
        data.CData.save_inst(pklFullPath, self.InputData.DataInfo)

        # --- 이 부분을 수정 ---
        optionPath = os.path.dirname(self.InputData.DataInfo.OptionFullPath)
        batPath = os.path.join(optionPath, "processCL.bat")

        print(f"batPath : {batPath}")
        print(f"pklFullPath : {pklFullPath}")
        print(f"--index : {str(index)}")
        
        args = [
            batPath,
            "--file", pklFullPath,
            "--index", str(index),
            "--cellID", str(cellID),
        ]

        print("RUN:", args)
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        print(result.stdout)
        print(result.stderr)
        print(f"-- End Extraction Centerline --")


    @property
    def InputIndex(self) -> int :
        return self.m_inputIndex
    @InputIndex.setter
    def InputIndex(self, inputIndex : int) :
        self.m_inputIndex = inputIndex
    @property
    def InputCellID(self) -> int :
        return self.m_inputCellID
    @InputCellID.setter
    def InputCellID(self, inputCellID : int) :
        self.m_inputCellID = inputCellID






if __name__ == '__main__' :
    pass


# print ("ok ..")

