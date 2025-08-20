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


class CCom :
    def __init__(self, mediator):
        '''
        desc 
            component interface
        mediator 
            tabState interface
        '''
        self.m_mediator = mediator
    def clear(self) :
        self.m_mediator = None

    
    # event override 
    def ready(self) -> bool :
        return True
    def process_init(self) :
        pass
    def process_end(self) :
        pass


    # protected
    def _get_renderer(self) -> vtk.vtkRenderer :
        return self.App.get_viewercl_renderer()
    def _get_data(self) -> data.CData :
        return self.m_mediator.get_data()
    def _get_clinfoinx(self) -> int :
        return self.m_mediator.get_clinfo_index()
    def _get_skeleton(self) -> algSkeletonGraph.CSkeleton :
        clinfoinx = self._get_clinfoinx()
        skeleton = self._get_data().get_skeleton(clinfoinx)
        return skeleton

    
    @property
    def App(self) : 
        return self.m_mediator.m_mediator
    @property
    def OptionInfo(self) -> optionInfo.COptionInfoSingle :
        return self._get_data().OptionInfo


if __name__ == '__main__' :
    pass


# print ("ok ..")

