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

        if self.InputData is None :
            return

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
        
        userdata = self.InputData.UserData
        if userdata is not None :
            userdata.override_load_centerline()

    
    def _check_saved_data(self) -> bool :
        # loading CLDataInfo
        outputPatientPath = self.InputData.OutputPatientPath
        saveFullPath = os.path.join(outputPatientPath, f"{data.CData.s_fileName}.json")
        if os.path.exists(saveFullPath) == False :
            return False
        return True
    def _new_patient(self) -> bool :
        optionInfoInst = self.OptionInfo
        dataInst = self.InputData

        # dataInst setting from optionInfo
        # skelinfo setting
        iCLCnt = optionInfoInst.get_centerline_count()
        for clInx in range(0, iCLCnt) :
            ret = optionInfoInst.get_centerline_info(clInx) 
            advancementRatio = ret[0]
            resamplingLength = ret[1]
            smoothingIter = ret[2]
            smoothingFactor = ret[3]

            iListCnt = optionInfoInst.get_centerline_list_count(clInx)
            for listInx in range(0, iListCnt) :
                blenderName, jsonName = optionInfoInst.get_centerline_list(clInx, listInx)

                skelInfo = data.CSkelInfo()
                skelInfo.AdvancementRatio = advancementRatio
                skelInfo.ResamplingLength = resamplingLength
                skelInfo.SmoothingIter = smoothingIter
                skelInfo.SmoothingFactor = smoothingFactor
                skelInfo.BlenderName = blenderName
                skelInfo.JsonName = jsonName
                dataInst.add_skelinfo(skelInfo)
        
        iTerriCnt = optionInfoInst.get_target_territory_list_count()
        for terriInx in range(0, iTerriCnt) :
            blenderName = optionInfoInst.get_target_territory_list(terriInx)

            terriInfo = data.CTerritoryInfo()
            terriInfo.BlenderName = blenderName
            dataInst.add_terriinfo(terriInfo)
        
        # export
        self._export_data()
        # add vtkobj
        self._add_vtkobj()

        return True
    def _load_patient(self) :
        optionInfoInst = self.OptionInfo
        dataInst = self.InputData

        outputPatientPath = dataInst.OutputPatientPath
        saveFullPath = os.path.join(outputPatientPath, f"{data.CData.s_fileName}.json")
        dataInst.load(saveFullPath)

        # export
        self._export_data()
        # add vtkobj
        self._add_vtkobj()
        # add skeleton vtkobj
        self._add_skeleton_vtkobj()

    def _export_data(self) :
        dataInst = self.InputData

        # vessel 
        commandExportInst = commandExport.CCommandExportList(self.m_mediator)
        commandExportInst.InputData = dataInst
        commandExportInst.OutputPath = dataInst.get_cl_in_path()
        commandExportInst.PatientBlenderFullPath = self.PatientBlenderFullPath
        iCnt = dataInst.get_skelinfo_count()
        for inx in range(0, iCnt) :
            skelinfo = dataInst.get_skelinfo(inx)
            commandExportInst.add_blender_name(skelinfo.BlenderName)
        commandExportInst.process()
        commandExportInst.clear()

        # organ
        commandExportInst = commandExport.CCommandExportList(self.m_mediator)
        commandExportInst.InputData = dataInst
        commandExportInst.OutputPath = dataInst.get_terri_in_path()
        commandExportInst.PatientBlenderFullPath = self.PatientBlenderFullPath
        iCnt = dataInst.get_terriinfo_count()
        for inx in range(0, iCnt) :
            terriinfo = dataInst.get_terriinfo(inx)
            commandExportInst.add_blender_name(terriinfo.BlenderName)
        commandExportInst.process()
        commandExportInst.clear()
    
    def _add_vtkobj(self) :
        dataInst = self.InputData

        iCnt = dataInst.get_skelinfo_count()
        for inx in range(0, iCnt) :
            self.m_mediator.add_vessel_obj(inx, 0)
        self.m_mediator.add_organ_obj()
    def _add_skeleton_vtkobj(self) :
        dataInst = self.InputData
        clOutPath = self.InputData.get_cl_out_path()

        iCnt = dataInst.get_skelinfo_count()
        for inx in range(0, iCnt) :
            skelinfo = dataInst.get_skelinfo(inx)

            jsonFullPath = os.path.join(clOutPath, f"{skelinfo.JsonName}.json")
            if os.path.exists(jsonFullPath) == False :
                continue

            skeleton = algSkeletonGraph.CSkeleton()
            skeleton.load(jsonFullPath)
            skelinfo.Skeleton = skeleton

            self.m_mediator.add_skeleton_obj(inx)








if __name__ == '__main__' :
    pass


# print ("ok ..")

