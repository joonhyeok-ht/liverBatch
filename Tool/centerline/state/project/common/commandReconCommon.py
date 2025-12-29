import sys
import os
import numpy as np
import shutil
import glob
import vtk
import subprocess
import copy
import SimpleITK as sitk
import math
from collections import Counter

from PySide6.QtCore import Qt, QItemSelection, QItemSelectionModel
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTreeView, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QListWidgetItem, QMessageBox, QAbstractItemView
from PySide6.QtGui import QStandardItemModel, QStandardItem
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileStateProjectPath = os.path.dirname(fileAbsPath)
fileStatePath = os.path.dirname(fileStateProjectPath)
fileAppPath = os.path.dirname(fileStatePath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileStateProjectPath)
sys.path.append(fileStatePath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algVTK as algVTK

import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer
import Block.originOffset as originOffset
import Block.removeStricture as removeStricture
import Block.registration as registration
import Block.resampling as resamplingB
import Block.reconstruction as reconstruction
import Block.meshHealing as meshHealing
import Block.meshBoolean as meshBoolean

import vtkObjInterface as vtkObjInterface

import data as data

import userData as userData

import command.commandRecon as commandRecon



class CCommandReconDevelopCommon(commandRecon.CCommandRecon) :
    '''
    Desc : common pipeline reconstruction step에서 Recon 수행
    '''

    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
    def clear(self):
        # input your code
        super().clear()
    def process(self) :
        super().process()
        # input your code

        # 기존 blender 파일이 있을 경우 로딩만 수행 
        if os.path.exists(self.PatientBlenderFullPath) == True :
            commandRecon.CCommandReconInterface.blender_process_load(self.OptionInfo.BlenderExe, self.PatientBlenderFullPath)
            return

        originMaskPath = self.MaskPath
        if os.path.exists(originMaskPath) == False :
            print(f"colon recon : not found mask path - {originMaskPath}")
            return

        copiedMaskPath = self.CopiedMaskPath
        if os.path.exists(copiedMaskPath) == False :
            os.makedirs(copiedMaskPath, exist_ok=True)
            # nii.gz 파일 복사
            for file in glob.glob(os.path.join(originMaskPath, "*.nii.gz")):
                shutil.copy(file, copiedMaskPath)
        
        phase = None

        phaseInfoFullPath = self.PhaseInfoFullPath
        if os.path.exists(phaseInfoFullPath) == True :
            fileLoadPhaseInfoBlock = niftiContainer.CFileLoadPhaseInfo()
            fileLoadPhaseInfoBlock.InputPath = self.InputData.OutputPatientPath
            fileLoadPhaseInfoBlock.InputFileName = commandRecon.CCommandReconInterface.s_phaseInfoFileName
            phase = fileLoadPhaseInfoBlock.process()
        else :
            phase = self._create_phase()
            originOffsetBlock = originOffset.COriginOffset()
            originOffsetBlock.InputOptionInfo = self.InputData.OptionInfo
            originOffsetBlock.InputPhase = phase
            originOffsetBlock.process()

            registrationBlock = registration.CRegistration()
            registrationBlock.InputOptionInfo = self.InputData.OptionInfo
            registrationBlock.InputMaskPath = self.CopiedMaskPath
            registrationBlock.process()

            self._update_phase_offset(self.InputData.OptionInfo, registrationBlock, originOffsetBlock, phase)
            fileSavePhaseInfoBlock = niftiContainer.CFileSavePhaseInfo()
            fileSavePhaseInfoBlock.InputPhase = phase
            fileSavePhaseInfoBlock.OutputSavePath = self.InputData.OutputPatientPath
            fileSavePhaseInfoBlock.OutputFileName = commandRecon.CCommandReconInterface.s_phaseInfoFileName
            fileSavePhaseInfoBlock.process()

        resamplingToPhaseBlock = resamplingB.CResamplingToPhase()
        resamplingToPhaseBlock.InputOptionInfo = self.InputData.OptionInfo
        resamplingToPhaseBlock.InputMaskPath = self.CopiedMaskPath
        resamplingToPhaseBlock.InputPhase = phase
        resamplingToPhaseBlock.OutputMaskPath = self.CopiedMaskPath
        resamplingToPhaseBlock.process()

        resamplingToMinSpacingBlock = resamplingB.CResamplingToMinSpacing()
        resamplingToMinSpacingBlock.InputMaskPath = self.CopiedMaskPath
        resamplingToMinSpacingBlock.InputOptionInfo = self.InputData.OptionInfo
        resamplingToMinSpacingBlock.OutputMaskPath = self.CopiedMaskPath
        resamplingToMinSpacingBlock.process()

        removeStrictureBlock = removeStricture.CRemoveStricture()
        removeStrictureBlock.InputOptionInfo = self.OptionInfo
        removeStrictureBlock.InputMaskPath = self.CopiedMaskPath
        removeStrictureBlock.OutputMaskPath = self.CopiedMaskPath
        removeStrictureBlock.process()

        reconstructionBlock = reconstruction.CReconstruction()
        reconstructionBlock.InputOptionInfo = self.InputData.OptionInfo
        reconstructionBlock.InputMaskPath = self.CopiedMaskPath
        reconstructionBlock.InputPhase = phase
        reconstructionBlock.OutputPath = self.ResultPath
        reconstructionBlock.process()

        meshHealingBlock = meshHealing.CMeshHealing()
        meshHealingBlock.InputPath = self.ResultPath
        meshHealingBlock.InputOptionInfo = self.InputData.OptionInfo
        meshHealingBlock.process()

        meshBooleanBlock = meshBoolean.CMeshBoolean()
        meshBooleanBlock.InputPath = self.ResultPath
        meshBooleanBlock.InputOptionInfo = self.InputData.OptionInfo
        meshBooleanBlock.process()

        removeStrictureBlock.clear()
        reconstructionBlock.clear()
        meshHealingBlock.clear()
        meshBooleanBlock.clear()

        self._process_blender()
    def process_resampling(self) :
        originMaskPath = self.MaskPath
        if os.path.exists(originMaskPath) == False :
            print(f"colon recon : not found mask path - {originMaskPath}")
            return

        copiedMaskPath = self.CopiedMaskPath
        if os.path.exists(copiedMaskPath) == False :
            os.makedirs(copiedMaskPath, exist_ok=True)
            # nii.gz 파일 복사
            for file in glob.glob(os.path.join(originMaskPath, "*.nii.gz")):
                shutil.copy(file, copiedMaskPath)
        
        phase = None

        phaseInfoFullPath = self.PhaseInfoFullPath
        if os.path.exists(phaseInfoFullPath) == True :
            fileLoadPhaseInfoBlock = niftiContainer.CFileLoadPhaseInfo()
            fileLoadPhaseInfoBlock.InputPath = self.InputData.OutputPatientPath
            fileLoadPhaseInfoBlock.InputFileName = commandRecon.CCommandReconInterface.s_phaseInfoFileName
            phase = fileLoadPhaseInfoBlock.process()
        else :
            phase = self._create_phase()
            originOffsetBlock = originOffset.COriginOffset()
            originOffsetBlock.InputOptionInfo = self.InputData.OptionInfo
            originOffsetBlock.InputPhase = phase
            originOffsetBlock.process()

            registrationBlock = registration.CRegistration()
            registrationBlock.InputOptionInfo = self.InputData.OptionInfo
            registrationBlock.InputMaskPath = self.CopiedMaskPath
            registrationBlock.process()

            self._update_phase_offset(self.InputData.OptionInfo, registrationBlock, originOffsetBlock, phase)
            fileSavePhaseInfoBlock = niftiContainer.CFileSavePhaseInfo()
            fileSavePhaseInfoBlock.InputPhase = phase
            fileSavePhaseInfoBlock.OutputSavePath = self.InputData.OutputPatientPath
            fileSavePhaseInfoBlock.OutputFileName = commandRecon.CCommandReconInterface.s_phaseInfoFileName
            fileSavePhaseInfoBlock.process()

        resamplingToPhaseBlock = resamplingB.CResamplingToPhase()
        resamplingToPhaseBlock.InputOptionInfo = self.InputData.OptionInfo
        resamplingToPhaseBlock.InputMaskPath = self.CopiedMaskPath
        resamplingToPhaseBlock.InputPhase = phase
        resamplingToPhaseBlock.OutputMaskPath = self.CopiedMaskPath
        resamplingToPhaseBlock.process()

        resamplingToMinSpacingBlock = resamplingB.CResamplingToMinSpacing()
        resamplingToMinSpacingBlock.InputMaskPath = self.CopiedMaskPath
        resamplingToMinSpacingBlock.InputOptionInfo = self.InputData.OptionInfo
        resamplingToMinSpacingBlock.OutputMaskPath = self.CopiedMaskPath
        resamplingToMinSpacingBlock.process()


    # protected
    def _process_blender(self) :
        blenderExe = self.OptionInfo.BlenderExe
        scriptFullPath = self.InputBlenderScritpFullPath
        inputPath = self.ResultPath
        outputPath = self.InputData.OutputPatientPath

        patientID = self.InputData.PatientID
        saveName = f"{patientID}_recon"
        commandRecon.CCommandReconInterface.blender_process(blenderExe, scriptFullPath, self.InputData.OptionInfo.m_jsonPath, inputPath, outputPath, saveName, False)


# class CCommandReconDevelopCleanColon(commandRecon.CCommandReconDevelop) :
#     '''
#     Desc : common pipeline reconstruction step에서 Clean 수행
#     '''

#     def __init__(self, mediator) :
#         super().__init__(mediator)
#         # input your code
#     def clear(self):
#         # input your code
#         super().clear()
#     def process(self):
#         super().process()
#         # input your code
#         self._process_blender()


#     # protected
#     def _process_blender(self) : 
#         blenderExe = self.BlenderExe
#         scriptFullPath = os.path.join(self.InputBlenderScritpPath, f"{self.InputBlenderScritpFileName}.py")
#         inputPath = self.OutputPatientPath
#         outputPath = self.OutputPatientPath
#         saveName = self.InputSaveBlenderName
#         blenderFullPath = os.path.join(outputPath, f"{saveName}.blend")
#         commandRecon.CCommandReconInterface.blender_process_load_script(blenderExe, blenderFullPath, scriptFullPath, self.InputData.DataInfo.OptionFullPath, inputPath, outputPath, saveName, False)


#     @property
#     def InputBlenderScritpPath(self) -> str :
#         return self.m_inputBlenderScritpPath
#     @InputBlenderScritpPath.setter
#     def InputBlenderScritpPath(self, inputBlenderScritpPath : str) :
#         self.m_inputBlenderScritpPath = inputBlenderScritpPath
    

if __name__ == '__main__' :
    pass


# print ("ok ..")

