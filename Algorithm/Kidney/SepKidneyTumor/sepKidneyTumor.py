import numpy as np
from scipy import optimize
import matplotlib.pyplot as plt
import SimpleITK as sitk
import cv2
import os, sys
import matplotlib.patches as patches

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
dirPath = os.path.join(os.path.abspath(os.path.dirname(__file__)), "../../")
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


import blockKidney



'''
Name
    - SepKidneyTumorBlock
Input
    - "InputDP"     : kidney dp folder that include exo
Output
    - "DP"          : output folder that output separated kidney nifti
Property
    - "Active"
'''
class CSepKidneyTumor(blockKidney.CKidneyBase) :
    def __init__(self) -> None:
        super().__init__()
        self.m_kidneyPath = ""
        self.m_savePath = ""
    def process(self) :
        kidneyPath = self.m_kidneyPath
        savePath = self.m_savePath
        listExoPath = []

        listPath = os.listdir(kidneyPath)
        for path in listPath :
            if path == ".DS_Store" : 
                continue
            if os.path.isdir(path) :
                continue
            if "exo" in path :
                listExoPath.append(path)
        
        #refPath = os.path.join(kidneyPath, self.s_serviceKidney)
        refPath = self._find_kidney_full_path(kidneyPath)
        print(f"-- {refPath} --")
        if refPath is None :
            print("not found Delay Phase Kidney")
            return
        self.m_maskKidney = self.create_mask(refPath, "uint8", 0, self.eMaskID_kidney)
        self.m_maskTumor = self.m_maskKidney.clone("uint8")
        self.m_maskTumor.all_set_voxel(0)

        for exoPath in listExoPath : 
            refPath = os.path.join(kidneyPath, exoPath)
            exoMask = self.create_mask(refPath, "uint8", 0, self.eMaskID_tumor)
            self.append_mask(self.m_maskTumor, exoMask, self.eMaskID_tumor)
        self.append_mask(self.m_maskKidney, self.m_maskTumor, self.eMaskID_tumor)

        self._erode()
        self._save_nifti(self.m_savePath)
    
    
    @property
    def MaskSepTumorKidney(self) :
        return self.m_maskKidney
    @property
    def KidneyPath(self) -> str:
        return self.m_kidneyPath
    @KidneyPath.setter
    def KidneyPath(self, kidneyPath : str) :
        self.m_kidneyPath = kidneyPath
    @property
    def SavePath(self) -> str:
        return self.m_savePath
    @SavePath.setter
    def SavePath(self, savePath : str) :
        self.m_savePath = savePath

        dir = savePath
        if not os.path.exists(dir) :
            os.makedirs(dir)
    
    
    def _erode(self) :
        clearXInx = []
        clearYInx = []
        clearZInx = []
        kidneyXInx = []
        kidneyYInx = []
        kidneyZInx = []

        iCnt = 0
        inx = 0
        bFlag = False
        surfaceXInx, surfaceYInx, surfaceZInx = self.get_surface_voxel(self.m_maskTumor)

        while len(surfaceXInx) > 0 :
            clearXInx.clear()
            clearYInx.clear()
            clearZInx.clear()
            kidneyXInx.clear()
            kidneyYInx.clear()
            kidneyZInx.clear()
            for inx in range(0, len(surfaceXInx)) :
                voxelInx = (surfaceXInx[inx], surfaceYInx[inx], surfaceZInx[inx])
                surfaceType = self.get_surface_type(self.m_maskKidney, voxelInx)

                if surfaceType == self.eSurfaceType_inside :
                    kidneyXInx.append(voxelInx[0])
                    kidneyYInx.append(voxelInx[1])
                    kidneyZInx.append(voxelInx[2])
                elif surfaceType == self.eSurfaceType_ambiguous :
                    if bFlag == False :
                        clearXInx.append(voxelInx[0])
                        clearYInx.append(voxelInx[1])
                        clearZInx.append(voxelInx[2])
                    else :
                        kidneyXInx.append(voxelInx[0])
                        kidneyYInx.append(voxelInx[1])
                        kidneyZInx.append(voxelInx[2])
                else :
                    clearXInx.append(voxelInx[0])
                    clearYInx.append(voxelInx[1])
                    clearZInx.append(voxelInx[2])

            self.m_maskKidney.set_voxel((clearXInx, clearYInx, clearZInx), 0)
            self.m_maskKidney.set_voxel((kidneyXInx, kidneyYInx, kidneyZInx), self.eMaskID_kidney)
            self.m_maskTumor.set_voxel((surfaceXInx, surfaceYInx, surfaceZInx), 0)

            print(f"passed erode : {iCnt}")

            inx += 1
            iCnt += 1
            if bFlag == False :
                bFlag = True
            else :
                bFlag = False
            surfaceXInx, surfaceYInx, surfaceZInx = self.get_surface_voxel(self.m_maskTumor)
    def _save_nifti(self, savePath : str) :
        #refPath = os.path.join(self.m_kidneyPath, self.s_serviceKidney)
        refPath = self._find_kidney_full_path(self.m_kidneyPath)
        kidneyFileName = refPath.split("/")[-1]
        sitkImg = scoUtil.CScoUtilSimpleITK.load_image(refPath, None)
        origin = sitkImg.GetOrigin()
        direction = sitkImg.GetDirection()
        spacing = sitkImg.GetSpacing()
        
        sepTumorKidneyMask = self.MaskSepTumorKidney

        maskBuf = scoBuffer.CScoBuffer3D(sepTumorKidneyMask.Shape, "uint8")
        maskBuf.all_set_voxel(0)
        xVoxel, yVoxel, zVoxel = sepTumorKidneyMask.get_voxel_inx_with_greater(0)
        maskBuf.set_voxel((xVoxel, yVoxel, zVoxel), 255)
        sitkImg = maskBuf.get_sitk_img(origin, spacing, direction, (2, 1, 0))
        fullPath = os.path.join(savePath, self.s_separatedKidney)
        scoUtil.CScoUtilSimpleITK.save_nifti(fullPath, sitkImg)

        print(f"save : {fullPath}")
    def _find_kidney_full_path(self, kidneyPath : str) :
        listKidneyName = [self.s_kidneyDL, self.s_kidneyDR]
        for kidneyName in listKidneyName :
            fullPath = os.path.join(kidneyPath, kidneyName)
            if os.path.exists(fullPath) :
                return fullPath
        return None
    

    






