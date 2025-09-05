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
outputPath = r'{outExportPath}'
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


class CCommandExportCL(CCommandExportInterface) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_index = -1
    def clear(self) :
        # input your code
        self.m_inputIndex = -1
        super().clear()
    def process(self) :
        super().process()

        print("-- Start Blender Export --")

        if self.InputIndex == -1 :
            print("not setting inputIndex")
            return
        
        self.m_clInPath = self.InputData.get_cl_in_path()
        self.m_clOutPath = self.InputData.get_cl_out_path()

        if os.path.exists(self.m_clInPath) == False :
            print("not found clInPath")
            return
        if os.path.exists(self.m_clOutPath) == False :
            print("not found clInPath")
            return
        
        clCnt = self.InputData.DataInfo.get_info_count()
        if self.InputIndex >= clCnt :
            print("invalid inputIndex")
            return 
        
        clInfo = self.InputData.DataInfo.get_clinfo(self.InputIndex)
        reconParam = self.InputData.DataInfo.get_reconparam(self.InputIndex)

        inputKey = clInfo.InputKey
        if inputKey == "nifti" :
            print("not support inputKey : nifti")
        elif inputKey == "blenderName" :
            self.__inputkey_blenderName(clInfo)
        elif inputKey == "voxelize" :
            self.__inputkey_voxelize(clInfo, reconParam)
        else :
            print("invalide value cl inputKey")

        print("-- End Blender Export --")

    
    def __inputkey_blenderName(
            self,
            clInfo : optionInfo.CCenterlineInfo
            ) :
        # export -> load polydata 
        blenderName = clInfo.get_input_blender_name()
        tmpStr = f"'{blenderName}'"
        scriptFullPath = os.path.join(self.m_clInPath, f"tmpScript.py")
        self.export_from_blender(scriptFullPath, tmpStr, self.m_clInPath)
    def __inputkey_voxelize(
            self,
            clInfo : optionInfo.CCenterlineInfo,
            reconParam : optionInfo.CReconParamSingle
            ) :
        phaseInfoFullPath = os.path.join(self.InputData.DataInfo.PatientPath, "phaseInfo.json")
        if os.path.exists(phaseInfoFullPath) == False :
            print(f"not found phaseInfo.jon")
            return
        
        phaseInfoContainer = self.InputData.PhaseInfoContainer

        self.__inputkey_blenderName(clInfo)
        blenderName = clInfo.get_input_blender_name()
        exportedFullPath = os.path.join(self.m_clInPath, f"{blenderName}.stl")

        if os.path.exists(exportedFullPath) == False :
            print(f"centerline-voxelized : not found voxelized stl {blenderName}")
            return None
        polyData = algVTK.CVTK.load_poly_data_stl(exportedFullPath)

        maskInfo = self.OptionInfo.find_maskinfo_by_blender_name(blenderName)
        phase = maskInfo.Phase
        phaseInfoInst = phaseInfoContainer.find_phaseinfo(phase)
        
        npImg, origin, spacing, direction, size = algVTK.CVTK.poly_data_voxelize(polyData, phaseInfoInst.Spacing, 1.0)
        npImg = npImg.astype(np.uint8)
        npImg[npImg > 0] = 255

        print(f"voxelize origin : {origin}")
        print(f"voxelize spacing : {spacing}")
        print(f"voxelize direction : {direction}")
        print(f"voxelize size : {size}")

        niftiFullPath = os.path.join(self.m_clInPath, f"{blenderName}.nii.gz")
        algImage.CAlgImage.save_nifti_from_np(niftiFullPath, npImg, origin, spacing, direction, (2, 1, 0))

        contour = reconParam.Contour
        algorithm = reconParam.Algorithm
        param = reconParam.Param
        gaussian = reconParam.Gaussian
        resampling = reconParam.ResamplingFactor
        offset = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0])
        
        polyData = reconstruction.CReconstruction.reconstruction_nifti(niftiFullPath, origin, spacing, direction, offset, contour, param, algorithm , gaussian, resampling, bFlip=False)
        polyVertex = algVTK.CVTK.poly_data_get_vertex(polyData)
        polyIndex = algVTK.CVTK.poly_data_get_triangle_index(polyData)
        polyData = algVTK.CVTK.create_poly_data_triangle(polyVertex, polyIndex)

        # replace 
        algVTK.CVTK.save_poly_data_stl(exportedFullPath, polyData)


    @property
    def InputIndex(self) -> int :
        return self.m_inputIndex
    @InputIndex.setter
    def InputIndex(self, inputIndex : int) :
        self.m_inputIndex = inputIndex


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

