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

from PySide6.QtCore import Qt, QItemSelectionModel, QModelIndex
from PySide6.QtWidgets import QApplication, QMainWindow, QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QTableView, QMessageBox
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
import Block.meshDecimation as meshDecimation

import vtkObjInterface as vtkObjInterface

import data as data

import userData as userData

import command.commandRecon as commandRecon
import ui.uiDragDrop as uiDragDrop



class CUIPhaseAppend :
    def __init__(self, phase : str) :
        self.m_styleSheetBtn = """
QPushButton {
                border: 2px solid #5F6368;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                border-color: #1A73E8;
            }
"""
        self.m_phase = phase
        self.m_mainLayout = QVBoxLayout()

        label = QLabel(self.m_phase)
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.m_mainLayout.addWidget(label)

        self.m_lbFile = uiDragDrop.CUIDragDropListWidget((".nii.gz", ".zip"))
        self.m_mainLayout.addWidget(self.m_lbFile)

        btn = QPushButton("Clear List")
        btn.setStyleSheet(self.m_styleSheetBtn)
        btn.clicked.connect(self._on_btn_clear)
        self.m_mainLayout.addWidget(btn)
    def clear(self) :
        self.m_lbFile.clear()

    def get_fullpath_count(self) -> int :
        return len(self.m_lbFile.m_listFullPath)
    def get_fullpath(self, inx : int) -> str :
        return self.m_lbFile.m_listFullPath[inx]
    def get_file_cont(self) -> int :
        return len(self.m_lbFile.m_listFile)
    def get_file(self, inx : int) -> str :
        return self.m_lbFile.m_listFile[inx]


    # event
    def _on_btn_clear(self) :
        # self.m_phase = ""
        self.m_lbFile.clear()


    # property
    @property
    def Phase(self) -> str :
        return self.m_phase
    @property
    def MainLayout(self) -> QVBoxLayout :
        return self.m_mainLayout


class CDlgIndividualReconInfo(QDialog) :
    def __init__(self, parent=None, listPhase=None) :
        super().__init__(parent)
        self.setWindowTitle("Individual Recon Info")
        self.resize(800, 150) 

        self.m_styleSheetBtn = """
QPushButton {
                border: 2px solid #5F6368;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                border-color: #1A73E8;
            }
"""

        self.m_listPhaseInfo = []

        mainLayout = QVBoxLayout()

        lbPhaseLayout = QHBoxLayout()
        for phase in listPhase :
            phaseinfo = CUIPhaseAppend(phase)
            self.m_listPhaseInfo.append(phaseinfo)
            lbPhaseLayout.addLayout(phaseinfo.MainLayout)
        mainLayout.addLayout(lbPhaseLayout)


        # ok, cancel 
        buttonBox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        mainLayout.addWidget(buttonBox)
        self.setLayout(mainLayout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        mainLayout.addWidget(line)

        lastUI = line
        mainLayout.setAlignment(lastUI, Qt.AlignmentFlag.AlignTop)

    
    @property
    def PhaseInfo(self) -> dict :
        '''
        ret
            - key -> phase : str
            - value -> listFullPath : list (nii.gz or zip)
                       
        '''
        retDict = {}
        for phaseinfo in self.m_listPhaseInfo :
            phase = phaseinfo.Phase
            listFullPath = []
            for inx in range(0, phaseinfo.get_fullpath_count()) :
                fullPath = phaseinfo.get_fullpath(inx)
                listFullPath.append(fullPath)
            retDict[phase] = listFullPath
        return retDict
    

    

if __name__ == '__main__' :
    pass


# print ("ok ..")

