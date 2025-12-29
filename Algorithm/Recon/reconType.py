import numpy as np
import matplotlib.pyplot as plt
import os, sys
import matplotlib.patches as patches
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
dirPath = os.path.join(os.path.abspath(os.path.dirname(__file__)), "../")
sys.path.append(dirPath)

import scoUtil
import scoData
import scoReg
import scoMath
import scoRenderObj
import scoSkeleton
import scoSkeletonVM
import scoBuffer
import scoBufferAlg

import reconInterface


'''
Name
    - ReconWithTypeBlock
Input
    - "InputPath"       : folder including nifti files
    - "InputPhyInfo"    : physical info json path of nifti files (with physicalInfo)
Output
    - "OutputPath"      : the folder to copy recon files
Property
    - "Active"          : 0 or 1
    - "ReconParam"      : [key, iterCnt, relaxation, decimation]
    - "ReconGaussian"   : [key, 0 or 1]
    - "ReconAlgorithm"  : [key, "Marching" or "Flying"]
    - "ReconResamplingFactor" : [key, resamplingFactor]
    - "AddNiftiFile"    : [key, nifti file name]
'''

class CReconType() :
    def __init__(self) -> None :
        self.m_typeName = ""
        self.m_iterCnt = 0
        self.m_relaxation = 0.0
        self.m_decimation = 0.0
        self.m_gaussian = 0
        self.m_algorithm = "Marching"
        self.m_resamplingFactor = 1
        self.m_list = []
    def clear(self) :
        self.m_typeName = ""
        self.m_iterCnt = 0
        self.m_relaxation = 0.0
        self.m_decimation = 0.0
        self.m_gaussian = 0
        self.m_algorithm = "Marching"
        self.m_resamplingFactor = 1
        self.m_list.clear()

    def add_nifti_filename(self, niftiFileName : str) :
        self.m_list.append(niftiFileName)
    def get_nifti_filename_count(self) :
        return len(self.m_list)
    def get_nifti_filename(self, inx : int) :
        return self.m_list[inx]
    

    @property
    def TypeName(self) :
        return self.m_typeName
    @TypeName.setter
    def TypeName(self, typeName : str) :
        self.m_typeName = typeName
    @property
    def IterCnt(self) :
        return self.m_iterCnt
    @IterCnt.setter
    def IterCnt(self, iterCnt : int) :
        self.m_iterCnt = iterCnt
    @property
    def Relaxation(self) :
        return self.m_relaxation
    @Relaxation.setter
    def Relaxation(self, relaxation : float) :
        self.m_relaxation = relaxation
    @property
    def Decimation(self) :
        return self.m_decimation
    @Decimation.setter
    def Decimation(self, decimation : float) :
        self.m_decimation = decimation
    @property
    def Gaussian(self) :
        return self.m_gaussian
    @Gaussian.setter
    def Gaussian(self, gaussian : int) :
        self.m_gaussian = gaussian
    @property
    def Algorithm(self) :
        return self.m_algorithm
    @Algorithm.setter
    def Algorithm(self, algorithm : str) :
        self.m_algorithm = algorithm
    @property
    def ResamplingFactor(self) :
        return self.m_resamplingFactor
    @ResamplingFactor.setter
    def ResamplingFactor(self, resamplingFactor : int) :
        self.m_resamplingFactor = resamplingFactor

class CReconWithType(reconInterface.CReconInterface) :
    def __init__(self) -> None:
        super().__init__()
        # input your code 
        # key : recon type key
        # value : reconInterface.CReconType
        self.m_dicReconType = {}
    def process(self) :
        super().process()
        # input your code 
        for key, reconType in self.m_dicReconType.items() :
            self._recon_type(reconType)
    def clear(self) :
        # input your code 
        for key, reconType in self.m_dicReconType.items() :
            reconType.clear()
        self.m_dicReconType.clear()
        super().clear()


    def set_recon_param(self, reconTypeName : str, iterCnt : int, relaxation : float, decimation : float) :
        reconType = self._get_recon_type(reconTypeName)
        reconType.IterCnt = iterCnt
        reconType.Relaxation = relaxation
        reconType.Decimation = decimation
    def set_recon_gaussian(self, reconTypeName : str, gaussian : int) :
        reconType = self._get_recon_type(reconTypeName)
        reconType.Gaussian = gaussian
    def set_recon_algorithm(self, reconTypeName : str, algorithm : str) :
        reconType = self._get_recon_type(reconTypeName)
        reconType.Algorithm = algorithm
    def set_recon_resampling_factor(self, reconTypeName : str, resamplingFactor : int) :
        reconType = self._get_recon_type(reconTypeName)
        reconType.ResamplingFactor = resamplingFactor
    def add_nifti_file(self, reconTypeName : str, niftiFileName : str) :
        reconType = self._get_recon_type(reconTypeName)
        reconType.add_nifti_filename(niftiFileName)
    

    # protected
    def _get_recon_type(self, reconTypeName : str) :
        bCheck = reconTypeName in self.m_dicReconType
        if bCheck == False :
            reconType = CReconType()
            reconType.TypeName = reconTypeName
            self.m_dicReconType[reconTypeName] = reconType
        return self.m_dicReconType[reconTypeName]
    def _recon_type(self, reconType : CReconType) :
        niftiPath = self.InputPath
        outputPath = self.OutputPath

        iCnt = reconType.get_nifti_filename_count()
        for inx in range(0, iCnt) :
            niftiFileName = reconType.get_nifti_filename(inx)

            bRet, niftiFullPath, stlFullPath = reconInterface.CReconInterface.get_nifti_stl_full_path(niftiPath, niftiFileName, outputPath)
            if bRet == False :
                print(f"not found {niftiFileName}")
                continue

            iterCnt = reconType.IterCnt
            relaxation = reconType.Relaxation
            decimation = reconType.Decimation
            gaussian = reconType.Gaussian
            algorithm = reconType.Algorithm
            resamplingFactor = reconType.ResamplingFactor

            if self._exist_physical_info(niftiFileName) == True :
                self._recon_with_phy(niftiFileName, niftiFullPath, stlFullPath, iterCnt, relaxation, decimation, gaussian, algorithm, resamplingFactor)
            else :
                self._recon(niftiFullPath, stlFullPath, iterCnt, relaxation, decimation, gaussian, algorithm, resamplingFactor)
            
            print(f"completed recon {niftiFileName}")



