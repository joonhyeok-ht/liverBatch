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

import commandInterface as commandInterface
import commandExport as commandExport
# import territory as territory


class CCommandLoadingPatient(commandInterface.CCommand) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
    def clear(self) :
        # input your code
        super().clear()
    def process(self) :
        super().process()

        if self._check_saved_data() == False :
            clInPath = self.InputData.get_cl_in_path()
            clOutPath = self.InputData.get_cl_out_path()
            terriInPath = self.InputData.get_terri_in_path()
            terriOutPath = self.InputData.get_terri_out_path()

            if os.path.exists(clInPath) == False :
                os.makedirs(clInPath)
            if os.path.exists(clOutPath) == False :
                os.makedirs(clOutPath)
            if os.path.exists(terriInPath) == False :
                os.makedirs(terriInPath)
            if os.path.exists(terriOutPath) == False :
                os.makedirs(terriOutPath)
            self._new_patient()
        else :
            self._load_patient()

    
    def _check_saved_data(self) -> bool :
        # loading CLDataInfo
        clInPath = self.InputData.get_cl_in_path()
        pklFullPath = os.path.join(clInPath, "clDataInfo.pkl")
        if os.path.exists(pklFullPath) == False :
            print("not found saved data")
            return False
        return True
    def _new_patient(self) -> bool :
        optionInfoInst = self.OptionInfo
        dataInst = self.InputData

        # vessel loading
        self._export_vessel()
        iCnt = dataInst.DataInfo.get_info_count()
        for inx in range(0, iCnt) :
            self.m_mediator.load_vessel_key(inx, 0)
        
        # skeleton create
        dataInst.create_skeleton(iCnt)

        # organ loading
        self._export_organ()
        self.m_mediator.load_organ_key()
        
        # phaseInfo loading
        return True
    def _load_patient(self) :
        optionInfoInst = self.OptionInfo
        dataInst = self.InputData

        # loading CLDataInfo
        clInPath = self.InputData.get_cl_in_path()
        clOutPath = self.InputData.get_cl_out_path()

        # pkl 파일은 write only로 processCL에서 사용한다.
        # pklFullPath = os.path.join(clInPath, "clDataInfo.pkl")

        # if os.path.exists(pklFullPath) == True :
        #     dataInfo = data.CData.load_inst(pklFullPath)
        #     dataInst.DataInfo = dataInfo

        # loading vessel
        iCnt = dataInst.DataInfo.get_info_count()
        # bSkip = True
        # for inx in range(0, iCnt) :
        #     clinfo = dataInst.DataInfo.get_clinfo(inx)
        #     blenderName = clinfo.get_input_blender_name()
        #     vesselFullPath = os.path.join(f"{clInPath}", f"{blenderName}.stl")
        #     if os.path.exists(vesselFullPath) == False :
        #         bSkip = False
        # if bSkip == False :
        self._export_vessel()
        for inx in range(0, iCnt) :
            self.m_mediator.load_vessel_key(inx, 0)
        
        # loading skeleton
        dataInst.create_skeleton(iCnt)
        bSkip = True
        for inx in range(0, iCnt) :
            clinfo = dataInst.DataInfo.get_clinfo(inx)
            clOutput = clinfo.OutputName
            clOutputFullPath = os.path.join(clOutPath, f"{clOutput}.json")
            if os.path.exists(clOutputFullPath) == False :
                continue
            dataInst.set_skeleton(inx, clOutputFullPath)
            self.m_mediator.load_cl_key(inx)
            self.m_mediator.load_br_key(inx)
            self.m_mediator.load_ep_key(inx)

        # loading organ 
        # terriInPath = self.InputData.get_terri_in_path()
        iCnt = optionInfoInst.get_segmentinfo_count()
        # bSkip = True
        # for inx in range(0, iCnt) :
        #     segmentInfoInst = optionInfoInst.get_segmentinfo(inx)
        #     blenderName = segmentInfoInst.Organ
        #     organFullPath = os.path.join(terriInPath, f"{blenderName}.stl")
        #     if os.path.exists(organFullPath) == False :
        #         bSkip = False
        # if bSkip == False :
        self._export_organ()
        self.m_mediator.load_organ_key()
    
    def _export_vessel(self) :
        dataInst = self.InputData

        iCnt = dataInst.DataInfo.get_info_count()
        for inx in range(0, iCnt) :
            commandExportInst = commandExport.CCommandExportCL(self.m_mediator)
            commandExportInst.InputData = dataInst
            commandExportInst.InputIndex = inx
            commandExportInst.PatientBlenderFullPath = self.PatientBlenderFullPath
            commandExportInst.process()
            commandExportInst.clear()
    def _export_organ(self) :
        dataInst = self.InputData
        optionInfoInst = self.OptionInfo
        terriInPath = self.InputData.get_terri_in_path()
        
        commandExportInst = commandExport.CCommandExportList(self.m_mediator)
        commandExportInst.InputData = dataInst
        commandExportInst.OutputPath = terriInPath
        commandExportInst.PatientBlenderFullPath = self.PatientBlenderFullPath
        iCnt = optionInfoInst.get_segmentinfo_count()
        for inx in range(0, iCnt) :
            segmentInfoInst = optionInfoInst.get_segmentinfo(inx)
            blenderName = segmentInfoInst.Organ
            commandExportInst.add_blender_name(blenderName)
        commandExportInst.process()
        commandExportInst.clear()



if __name__ == '__main__' :
    pass


# print ("ok ..")

