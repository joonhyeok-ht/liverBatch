import numpy as np
import matplotlib.pyplot as plt
import os, sys
import matplotlib.patches as patches
import pandas as pd
import json

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import scoUtil
import scoData
import scoReg
import scoMath
import scoRenderObj
import scoSkeleton
import scoSkeletonVM
import scoBuffer
import scoBufferAlg


'''
Name
    - 
Input
    - "InputPath"       : folder including nifti files
    - "InputPhyInfo"    : physical info json path of nifti files 
Output
    - "OutputPath"      : the folder to copy recon files
Property
    - "Active"          : 0 or 1
    - "Algorithm"       : selected recon algorithm
                          "Marching" -> Marching Cube
                          "Flying" -> Flying Edge3D
    - "ResamplingFactor": subpixel count 
                          ex) 1(default), 2, 3, ..
'''

"""
physicalInfo.json 예시

{
	"Center" : [0, 0, 0],
	"NiftiList" : {
		"Aorta.nii.gz" : {
			"shape" : [512, 512, 326],
			"origin" : [0, 0, 0],
			"spacing" : [1, 1, 1],
			"direction" : [1, 0, 0, 0, 1, 0, 0, 0, 1],
            "RegOffset" : [0, 0, 0],
            "Volume" : 78.5645
		},
		..
	}
}
"""

class CReconInterface() :
    eAlgorithmMarching = "Marching"
    eAlgorithmFlying = "Flying"


    staticmethod
    def get_nifti_to_stl_full_path(niftiFileName : str, outputPath : str) :
        stlName = niftiFileName.split('.')[0]
        return os.path.join(outputPath, f"{stlName}.stl")
    staticmethod
    def get_nifti_stl_full_path(niftiPath : str, niftiFileName : str, outputPath : str) :
        """
        ret (IsExisted(bool), niftiFullPath, stlFullPath)
        """
        niftiFullPath = os.path.join(niftiPath, niftiFileName)
        stlFullPath = CReconInterface.get_nifti_to_stl_full_path(niftiFileName, outputPath)
        if not os.path.exists(niftiFullPath) :
            return (False, niftiFullPath, stlFullPath)
        
        return (True, niftiFullPath, stlFullPath)
    staticmethod
    def get_mat4_except_scale(direction, origin) -> scoMath.CScoMat4 :
        matRot = scoMath.CScoMat4()
        matTrans = scoMath.CScoMat4()

        matRot.rot_from_row(direction)
        matTrans.set_translate(origin[0], origin[1], origin[2])

        matRet = scoMath.CScoMath.mul_mat4(matTrans, matRot)
        return matRet
    

    def __init__(self) -> None:
        super().__init__()    
        # input your code 
        self.m_inputPath = ""
        self.m_inputPhyInfo = ""
        self.m_outputPath = ""
        self.m_json = None
    def process(self) :
        # json loading
        if self.InputPhyInfo != "" :
            if os.path.exists(self.InputPhyInfo) == True :
                with open(self.InputPhyInfo, 'r') as fp :
                    self.m_json = json.load(fp)
    def clear(self) :
        self.m_inputPath = ""
        self.m_inputPhyInfo = ""
        self.m_outputPath = ""
        if self.m_json != None :
            self.m_json.clear()


    @property
    def InputPath(self) -> str :
        return self.m_inputPath
    @InputPath.setter
    def InputPath(self, inputPath : str) :
        self.m_inputPath = inputPath
    @property
    def InputPhyInfo(self) -> str :
        return self.m_inputPhyInfo
    @InputPhyInfo.setter
    def InputPhyInfo(self, inputPhyInfo : str) :
        self.m_inputPhyInfo = inputPhyInfo
    @property
    def OutputPath(self) -> str :
        return self.m_outputPath
    @OutputPath.setter
    def OutputPath(self, outputPath : str) :
        self.m_outputPath = outputPath
        dirPath = outputPath
        if not os.path.exists(dirPath) :
            os.makedirs(dirPath)

    # protected
    def _exist_physical_info(self, niftiFileName : str) -> bool :
        if self.m_json == None :
            return False
        dicNiftiList = self.m_json["NiftiList"]
        if niftiFileName in dicNiftiList :
            return True
        return False
    def _get_vtk_matrix(self, niftiFileName : str) -> scoMath.CScoMat4 :
        if self._exist_physical_info(niftiFileName) == False :
            matScale = scoMath.CScoMat4()
            matScale.set_scale(1, -1, -1)
            return matScale
        dicNiftiInfo = self.m_json["NiftiList"][niftiFileName]
        listCenter = self.m_json["Center"]
        listShape = dicNiftiInfo["shape"]
        listOrigin = dicNiftiInfo["origin"]
        listSpacing = dicNiftiInfo["spacing"]
        listDirection = dicNiftiInfo["direction"]
        listRegOffset = dicNiftiInfo["RegOffset"]

        matPhy = CReconInterface.get_mat4_except_scale(listDirection, listOrigin)
        matRegOffset = scoMath.CScoMat4()
        matRegOffset.set_translate(listRegOffset[0], listRegOffset[1], listRegOffset[2])
        matPhy = scoMath.CScoMath.mul_mat4(matRegOffset, matPhy)

        matOriOffset = scoMath.CScoMat4()
        matOriOffset.set_translate(-listCenter[0], -listCenter[1], -listCenter[2])
        matVTK = scoMath.CScoMath.mul_mat4(matOriOffset, matPhy)

        matScale = scoMath.CScoMat4()
        matScale.set_scale(1, -1, -1)
        matVTK = scoMath.CScoMath.mul_mat4(matScale, matVTK)

        # matVTK = CReconInterface.get_mat4_except_scale(listDirection, listOrigin)

        # print(listRegOffset)
        # matVTK.print()

        return matVTK
    def _recon(
            self, 
            niftiFullPath, stlFullPath, 
            iterCnt : int, relaxation : float, decimation : float,
            gaussian : int,
            algorithm = "Marching", resamplingFactor = 1
            ) :
        scoUtil.CScoUtilVTK.recon_set_param_contour(0, 10)
        scoUtil.CScoUtilVTK.recon_set_param_gaussian_stddev(1.0)
        scoUtil.CScoUtilVTK.recon_set_param_polygon_smoothing(iterCnt, relaxation, decimation)

        bGauss = False
        if gaussian == 1 :
            bGauss = True

        if algorithm == self.eAlgorithmMarching :
            scoUtil.CScoUtilVTK.recon_with_param(niftiFullPath, stlFullPath, bGauss, resamplingFactor)
        elif algorithm == self.eAlgorithmFlying :    
            scoUtil.CScoUtilVTK.recon_flying_with_param(niftiFullPath, stlFullPath, bGauss, resamplingFactor)
        else :
            print("not support recon algorithm")
    def _recon_with_phy(
            self, niftiFileName,
            niftiFullPath, stlFullPath,
            iterCnt : int, relaxation : float, decimation : float,
            gaussian : int,
            algorithm = "Marching", resamplingFactor = 1
            ) :
        vtkMat = self._get_vtk_matrix(niftiFileName)
        scoUtil.CScoUtilVTK.recon_set_param_contour(0, 10)
        scoUtil.CScoUtilVTK.recon_set_param_gaussian_stddev(1.0)
        scoUtil.CScoUtilVTK.recon_set_param_polygon_smoothing(iterCnt, relaxation, decimation)
        bGauss = False
        if gaussian == 1 :
            bGauss = True
        
        if algorithm == self.eAlgorithmMarching :
            scoUtil.CScoUtilVTK.recon_with_param_phy(niftiFullPath, stlFullPath, bGauss, vtkMat.m_npMat, resamplingFactor)
        elif algorithm == self.eAlgorithmFlying :    
            scoUtil.CScoUtilVTK.recon_flying_with_param_phy(niftiFullPath, stlFullPath, bGauss, vtkMat.m_npMat, resamplingFactor)
        else :
            print("not support recon algorithm")



