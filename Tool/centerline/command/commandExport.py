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


class CCommandExportInterface(commandInterface.CCommand) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
    def clear(self) :
        # input your code
        super().clear()
    def process(self) :
        super().process()
        # input your code


    def export_from_blender(self, scriptFullPath : str, tmpStr : str, outExportPath : str) :
        with open(scriptFullPath, 'w') as scriptFp:
            scriptFp.write(f""" 
import bpy
import os
listObjName = [{tmpStr}]
outputPath = '{outExportPath}'
for objName in listObjName :
    if objName in bpy.data.objects:
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        bpy.data.objects[objName].select_set(True)
        bpy.context.view_layer.objects.active = bpy.data.objects[objName]
        bpy.ops.export_mesh.stl(filepath=os.path.join(outputPath, objName + '.stl'), use_selection=True)
                """)

        cmd = f"{self.OptionInfo.BlenderExe} -b {self.PatientBlenderFullPath} --python {scriptFullPath}"
        os.system(cmd)


class CCommandExportList(CCommandExportInterface) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_listBlenderName = []
        self.m_outputPath = ""
    def clear(self) :
        # input your code
        self.m_listBlenderName.clear()
        self.m_outputPath = ""
        super().clear()
    def process(self) :
        super().process()
        # input your code
        if self.OutputPath == "" :
            print("not setting OutputPath")
            return
        
        iCnt = len(self.m_listBlenderName)
        if iCnt == 0 :
            return
        
        tmpStr = f"'{self.m_listBlenderName[0]}'"
        if iCnt > 1 :
            for inx in range(1, iCnt) :
                blenderName = self.m_listBlenderName[inx]
                tmpStr = self.__attach_str(tmpStr, blenderName)
        scriptFullPath = os.path.join(self.OutputPath, f"tmpScript.py")
        self.export_from_blender(scriptFullPath, tmpStr, self.OutputPath)

    def add_blender_name(self, blenderName) :
        self.m_listBlenderName.append(blenderName)


    # private
    def __attach_str(self, target : str, src : str) -> str :
        tmpStr = f", '{src}'"
        target += tmpStr
        return target


    @property
    def OutputPath(self) -> int :
        return self.m_outputPath
    @OutputPath.setter
    def OutputPath(self, outputPath : int) :
        self.m_outputPath = outputPath






if __name__ == '__main__' :
    pass


# print ("ok ..")

