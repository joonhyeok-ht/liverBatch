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



class CCommandReconDevelopColon(commandRecon.CCommandReconDevelop) :
    '''
    Desc : common pipeline reconstruction step에서 Recon 수행
    '''

    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_inputBlenderScritpPath = ""
    def clear(self):
        # input your code
        self.m_inputBlenderScritpPath = ""
        super().clear()
    def process(self):
        super().process()
        # input your code

        # 기존 blender 파일이 있을 경우 로딩만 수행 
        # if os.path.exists(self.OutputBlenderFullPath) == True :
        #     commandRecon.CCommandReconInterface.blender_process_load(self.BlenderExe, self.OutputBlenderFullPath)
        #     return

        originMaskPath = os.path.join(self.InputData.OptionInfo.DataRootPath, self.InputPatientID)
        originMaskPath = os.path.join(originMaskPath, "Mask")
        if os.path.exists(originMaskPath) == False :
            print(f"colon recon : not found mask path - {originMaskPath}")
            return

        copiedMaskPath = os.path.join(self.OutputPatientPath, "Mask")
        if os.path.exists(copiedMaskPath) == False :
            os.makedirs(copiedMaskPath, exist_ok=True)
            # nii.gz 파일 복사
            for file in glob.glob(os.path.join(originMaskPath, "*.nii.gz")):
                shutil.copy(file, copiedMaskPath)


        niftiContainerBlock = niftiContainer.CNiftiContainerTerritory()
        niftiContainerBlock.InputOptionInfo = self.InputData.OptionInfo
        niftiContainerBlock.InputPath = copiedMaskPath
        niftiContainerBlock.process()

        phaseInfoFullPath = os.path.join(self.OutputPatientPath, f"{commandRecon.CCommandReconInterface.s_phaseInfoFileName}.json")
        if os.path.exists(phaseInfoFullPath) == True :
            fileLoadPhaseInfoBlock = niftiContainer.CFileLoadPhaseInfo()
            fileLoadPhaseInfoBlock.InputPath = self.OutputPatientPath
            fileLoadPhaseInfoBlock.InputFileName = commandRecon.CCommandReconInterface.s_phaseInfoFileName
            fileLoadPhaseInfoBlock.InputNiftiContainer = niftiContainerBlock
            fileLoadPhaseInfoBlock.process()
        else :
            originOffsetBlock = originOffset.COriginOffset()
            originOffsetBlock.InputOptionInfo = self.InputData.OptionInfo
            originOffsetBlock.InputNiftiContainer = niftiContainerBlock
            originOffsetBlock.process()

            registrationBlock = registration.CRegistration()
            registrationBlock.InputOptionInfo = self.InputData.OptionInfo
            registrationBlock.InputNiftiContainer = niftiContainerBlock
            registrationBlock.process()

            self._update_phase_offset(self.InputData.OptionInfo, niftiContainerBlock, registrationBlock, originOffsetBlock)
            fileSavePhaseInfoBlock = niftiContainer.CFileSavePhaseInfo()
            fileSavePhaseInfoBlock.InputNiftiContainer = niftiContainerBlock
            fileSavePhaseInfoBlock.m_outputSavePath = self.OutputPatientPath
            fileSavePhaseInfoBlock.m_outputFileName = commandRecon.CCommandReconInterface.s_phaseInfoFileName
            fileSavePhaseInfoBlock.process()

        removeStrictureBlock = removeStricture.CRemoveStricture()
        removeStrictureBlock.InputNiftiContainer = niftiContainerBlock
        removeStrictureBlock.process()

        reconstructionBlock = reconstruction.CReconstruction()
        reconstructionBlock.InputOptionInfo = self.InputData.OptionInfo
        reconstructionBlock.InputNiftiContainer = niftiContainerBlock
        reconstructionBlock.OutputPath = self.OutputResultPath
        reconstructionBlock.process()

        meshHealingBlock = meshHealing.CMeshHealing()
        meshHealingBlock.InputPath = self.OutputResultPath
        meshHealingBlock.InputOptionInfo = self.InputData.OptionInfo
        meshHealingBlock.process()

        meshBooleanBlock = meshBoolean.CMeshBoolean()
        meshBooleanBlock.InputPath = self.OutputResultPath
        meshBooleanBlock.InputOptionInfo = self.InputData.OptionInfo
        meshBooleanBlock.process()

        # ureter 하드코딩 임시 
        ureterMaskName = "ureter-MR"
        listMaskInfo = self.InputData.OptionInfo.find_maskinfo_list_by_name(ureterMaskName)
        listNiftiInfo = niftiContainerBlock.find_nifti_info_list_by_name(ureterMaskName)
        maskInfo = listMaskInfo[0]
        niftiInfo = listNiftiInfo[0]
        phaseInfo = niftiContainerBlock.find_phase_info(niftiInfo.MaskInfo.Phase)
        if listMaskInfo is not None and listNiftiInfo is not None and phaseInfo is not None :
            inputNiftiFullPath = niftiInfo.FullPath
            outputPath = self.OutputResultPath
            resNiftiFullPath = os.path.join(outputPath, f"{ureterMaskName}.nii.gz")

            if os.path.exists(inputNiftiFullPath) == True :
                origin = phaseInfo.Origin
                spacing = phaseInfo.Spacing
                direction = phaseInfo.Direction

                targetSize = [256, 256, 256]
                minSpacing = min(spacing)
                maxSpacing = max(spacing)
                newSpacing = (minSpacing + maxSpacing) / 2.0
                targetSpacing = [newSpacing, newSpacing, newSpacing]

                npImg, origin, spacing, direction, size = algImage.CAlgImage.get_np_from_nifti(inputNiftiFullPath)
                sitkImg = algImage.CAlgImage.get_sitk_from_np(npImg, origin, spacing, direction)

                # resampling
                resampledSitkImg =  algImage.CAlgImage.resampling_sitkimg_with_mat(
                    sitkImg, 
                    origin, targetSpacing, direction, targetSize, sitkImg.GetPixelID(), sitk.sitkNearestNeighbor,
                    None
                )
                npResImg, newOrigin, newSpacing, newDirection, newSize = algImage.CAlgImage.get_np_from_sitk(resampledSitkImg, np.uint8)
                algImage.CAlgImage.save_nifti_from_np(resNiftiFullPath, npResImg, newOrigin, newSpacing, newDirection, (2, 1, 0))

                # recon
                reconType = maskInfo.ReconType
                reconParam = self.InputData.OptionInfo.find_recon_param(reconType)
                contour = reconParam.Contour
                algorithm = reconParam.Algorithm
                param = reconParam.Param
                gaussian = reconParam.Gaussian
                resampling = reconParam.ResamplingFactor
                polyData = reconstruction.CReconstruction.reconstruction_nifti(
                    resNiftiFullPath, 
                    newOrigin, newSpacing, newDirection, phaseInfo.Offset, 
                    contour, param, algorithm, gaussian, resampling, True
                    )
                
                blenderName = maskInfo.BlenderName
                stlFullPath = os.path.join(outputPath, f"{blenderName}.stl")
                algVTK.CVTK.save_poly_data_stl(stlFullPath, polyData)
                print("completed ureter recon")
            else :
                print("not found ureter mask file")
        else :
            print("not found ureter maskinfo")

        niftiContainerBlock.clear()
        # originOffsetBlock.clear()
        # registrationBlock.clear()
        removeStrictureBlock.clear()
        reconstructionBlock.clear()
        # fileSavePhaseInfoBlock.clear()
        meshHealingBlock.clear()
        meshBooleanBlock.clear()

        self._process_blender()
    def process_resampling(self) :
        originMaskPath = os.path.join(self.InputData.OptionInfo.DataRootPath, self.InputPatientID)
        originMaskPath = os.path.join(originMaskPath, "Mask")
        if os.path.exists(originMaskPath) == False :
            print(f"colon recon : not found mask path - {originMaskPath}")
            return
        
        copiedMaskPath = os.path.join(self.OutputPatientPath, "Mask")
        if os.path.exists(copiedMaskPath) == False :
            os.makedirs(copiedMaskPath, exist_ok=True)
        # nii.gz 파일 복사
        for file in glob.glob(os.path.join(originMaskPath, "*.nii.gz")):
            shutil.copy(file, copiedMaskPath)
        
        niftiContainerBlock = niftiContainer.CNiftiContainerTerritory()
        niftiContainerBlock.InputOptionInfo = self.InputData.OptionInfo
        niftiContainerBlock.InputPath = copiedMaskPath
        niftiContainerBlock.process()

        phaseInfoFullPath = os.path.join(self.OutputPatientPath, f"{commandRecon.CCommandReconInterface.s_phaseInfoFileName}.json")
        if os.path.exists(phaseInfoFullPath) == True :
            fileLoadPhaseInfoBlock = niftiContainer.CFileLoadPhaseInfo()
            fileLoadPhaseInfoBlock.InputPath = self.OutputPatientPath
            fileLoadPhaseInfoBlock.InputFileName = commandRecon.CCommandReconInterface.s_phaseInfoFileName
            fileLoadPhaseInfoBlock.InputNiftiContainer = niftiContainerBlock
            fileLoadPhaseInfoBlock.process()
        else :
            originOffsetBlock = originOffset.COriginOffset()
            originOffsetBlock.InputOptionInfo = self.InputData.OptionInfo
            originOffsetBlock.InputNiftiContainer = niftiContainerBlock
            originOffsetBlock.process()

            registrationBlock = registration.CRegistration()
            registrationBlock.InputOptionInfo = self.InputData.OptionInfo
            registrationBlock.InputNiftiContainer = niftiContainerBlock
            registrationBlock.process()

            self._update_phase_offset(self.InputData.OptionInfo, niftiContainerBlock, registrationBlock, originOffsetBlock)
            fileSavePhaseInfoBlock = niftiContainer.CFileSavePhaseInfo()
            fileSavePhaseInfoBlock.InputNiftiContainer = niftiContainerBlock
            fileSavePhaseInfoBlock.m_outputSavePath = self.OutputPatientPath
            fileSavePhaseInfoBlock.m_outputFileName = commandRecon.CCommandReconInterface.s_phaseInfoFileName
            fileSavePhaseInfoBlock.process()

        resamplingBlock = resamplingB.CResamplingMask()
        resamplingBlock.InputNiftiContainer = niftiContainerBlock
        resamplingBlock.process()


    # protected
    def _process_blender(self) :
        blenderExe = self.BlenderExe
        scriptFullPath = os.path.join(self.InputBlenderScritpPath, f"{self.InputBlenderScritpFileName}.py")
        inputPath = self.OutputResultPath
        outputPath = self.OutputPatientPath
        saveName = self.InputSaveBlenderName
        commandRecon.CCommandReconInterface.blender_process(blenderExe, scriptFullPath, self.InputData.DataInfo.OptionFullPath, inputPath, outputPath, saveName, False)
    

    @property
    def InputBlenderScritpPath(self) -> str :
        return self.m_inputBlenderScritpPath
    @InputBlenderScritpPath.setter
    def InputBlenderScritpPath(self, inputBlenderScritpPath : str) :
        self.m_inputBlenderScritpPath = inputBlenderScritpPath


class CCommandReconDevelopCleanColon(commandRecon.CCommandReconDevelop) :
    '''
    Desc : common pipeline reconstruction step에서 Clean 수행
    '''

    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
    def clear(self):
        # input your code
        super().clear()
    def process(self):
        super().process()
        # input your code
        self._process_blender()


    # protected
    def _process_blender(self) : 
        blenderExe = self.BlenderExe
        scriptFullPath = os.path.join(self.InputBlenderScritpPath, f"{self.InputBlenderScritpFileName}.py")
        inputPath = self.OutputPatientPath
        outputPath = self.OutputPatientPath
        saveName = self.InputSaveBlenderName
        blenderFullPath = os.path.join(outputPath, f"{saveName}.blend")
        commandRecon.CCommandReconInterface.blender_process_load_script(blenderExe, blenderFullPath, scriptFullPath, self.InputData.DataInfo.OptionFullPath, inputPath, outputPath, saveName, False)


    @property
    def InputBlenderScritpPath(self) -> str :
        return self.m_inputBlenderScritpPath
    @InputBlenderScritpPath.setter
    def InputBlenderScritpPath(self, inputBlenderScritpPath : str) :
        self.m_inputBlenderScritpPath = inputBlenderScritpPath
    

if __name__ == '__main__' :
    pass


# print ("ok ..")

