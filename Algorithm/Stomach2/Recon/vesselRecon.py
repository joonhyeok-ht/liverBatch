import numpy as np
from scipy import optimize
import matplotlib.pyplot as plt
import SimpleITK as sitk
import cv2
import os, sys
import matplotlib.patches as patches

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
    - VesselReconBlock
Input
    - "InputPath"           : nifti path
Output
    - "OutputPath"          : stl path
Property
    - "Active"
    - "ReconTypeList"
'''
class CReconType :
    def __init__(self) -> None :
        self.m_typeName = ""
        self.m_iterCnt = 0
        self.m_relaxation = 0.0
        self.m_decimation = 0.0
        self.m_gaussian = 0
        self.m_list = []
    def clear(self) :
        self.m_typeName = ""
        self.m_iterCnt = 0
        self.m_relaxation = 0.0
        self.m_decimation = 0.0
        self.m_gaussian = 0
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


class CVesselRecon() :
    staticmethod
    def get_nifti_to_stl_full_path(niftiFileName : str, outputPath : str) :
        stlName = niftiFileName.split('.')[0]
        return os.path.join(outputPath, f"{stlName}.stl")
    

    def __init__(self) -> None:
        self.m_inputPath = ""
        self.m_outputPath = ""
        self.m_listReconType = []
    def process(self) :
        self.recon_type()
    def clear(self) :
        self.m_inputPath = ""
        self.m_outputPath = ""
        self.m_listReconType.clear()

    def add_recon_type(self, reconTypeName : str, dicReconType : dict) :
        param = dicReconType["param"]
        gaussian = dicReconType["gaussian"]
        listNiftiFileName = dicReconType["list"]

        reconType = CReconType()
        reconType.TypeName = reconTypeName
        reconType.IterCnt = param[0]
        reconType.Relaxation = param[1]
        reconType.Decimation = param[2]
        reconType.Gaussian = gaussian
        for niftiFileName in listNiftiFileName :
            reconType.add_nifti_filename(niftiFileName)
        self.m_listReconType.append(reconType)
    def recon_type(self) :
        for reconType in self.m_listReconType :
            self._recon_type(reconType)
    

    # protected
    def _recon_type(self, reconType : CReconType) :
        niftiPath = self.InputPath

        iCnt = reconType.get_nifti_filename_count()
        for inx in range(0, iCnt) :
            niftiFileName = reconType.get_nifti_filename(inx)
            outputPath = self.OutputPath

            niftiFullPath = os.path.join(niftiPath, niftiFileName)
            stlFullPath = CVesselRecon.get_nifti_to_stl_full_path(niftiFileName, outputPath)
            if not os.path.exists(niftiFullPath) :
                print(f"not found {niftiFileName}")
                continue

            iterCnt = reconType.IterCnt
            relaxation = reconType.Relaxation
            decimation = reconType.Decimation
            gaussian = reconType.Gaussian

            # transform matrix added 
            scoUtil.CScoUtilVTK.recon_set_param_contour(0, 10)
            scoUtil.CScoUtilVTK.recon_set_param_gaussian_stddev(1.0)
            scoUtil.CScoUtilVTK.recon_set_param_polygon_smoothing(iterCnt, relaxation, decimation)
            if gaussian == 0 :
                scoUtil.CScoUtilVTK.recon_with_param(niftiFullPath, stlFullPath)
            else :
                scoUtil.CScoUtilVTK.recon_with_param_gauss(niftiFullPath, stlFullPath)
    
    @property
    def InputPath(self) :
        return self.m_inputPath
    @InputPath.setter
    def InputPath(self, inputPath : str) :
        self.m_inputPath = inputPath
    @property
    def OutputPath(self) :
        return self.m_outputPath
    @OutputPath.setter
    def OutputPath(self, outputPath : str) :
        self.m_outputPath = outputPath
        dirPath = outputPath
        if not os.path.exists(dirPath) :
            os.makedirs(dirPath)

    
    

    






