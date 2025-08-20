import numpy as np
from scipy import optimize
import matplotlib.pyplot as plt
import SimpleITK as sitk
import cv2
import os, sys
import matplotlib.patches as patches

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


class CReconType :
    def __init__(self) -> None:
        self.m_typeName = ""
        self.m_iterCnt = 0
        self.m_relaxation = 0.0
        self.m_decimation = 0.0
        self.m_gaussian = 0
        self.m_strictureMode = 0
        self.m_list = []
    def clear(self) :
        self.m_typeName = ""
        self.m_iterCnt = 0
        self.m_relaxation = 0.0
        self.m_decimation = 0.0
        self.m_gaussian = 0
        self.m_strictureMode = 0
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
    def StrictureMode(self) :
        return self.m_strictureMode
    @StrictureMode.setter
    def StrictureMode(self, strictureMode : int) :
        self.m_strictureMode = strictureMode


class CKidneyBase() :
    eMaskID_kidney = 100
    eMaskID_tumor = 1

    eSurfaceType_outside = 0
    eSurfaceType_inside = 1
    eSurfaceType_ambiguous = 2


    s_separatedKidney = "Kidney.nii.gz"
    s_kidneyDL = "Kidney_DL.nii.gz"
    s_kidneyDR = "Kidney_DR.nii.gz"

    s_listKidney = [
        "Kidney_AR.nii.gz",
        "Kidney_AL.nii.gz",
        "Kidney_PR.nii.gz",
        "Kidney_PL.nii.gz",
        "Kidney_DR.nii.gz",
        "Kidney_DL.nii.gz"
    ]
    s_listKidneySep = [
        s_separatedKidney
    ]

    s_listAP = [
        "Kidney_AR.nii.gz",
        "Kidney_AL.nii.gz",
        "Renal_artery.nii.gz",
        "Aorta.nii.gz",
        "Psoas_muscle.nii.gz"
    ]
    s_listPP = [
        "Kidney_PR.nii.gz",
        "Kidney_PL.nii.gz",
        "Renal_vein.nii.gz",
        "IVC.nii.gz",
        "Bone.nii.gz",
        "Abdominal_wall.nii.gz",
        "Skin.nii.gz",
        "Liver.nii.gz",
        "Gallbladder.nii.gz",
        "Spleen.nii.gz",
        "Pancreas.nii.gz"
    ]
    s_listDP = [
        "Kidney_DR.nii.gz",
        "Kidney_DL.nii.gz",
        "Ureter.nii.gz",
        "POI-Ureter.nii.gz",
        "POI-Hilum.nii.gz"
    ]


    @staticmethod
    def create_mask(refPath : str, type : str, clearValue, voxel) -> scoBuffer.CScoBuffer3D :
        sitkImg = scoUtil.CScoUtilSimpleITK.load_image(refPath, None)
        npImg = scoUtil.CScoUtilSimpleITK.sitkImg_to_npImg(sitkImg, type).transpose((2, 1, 0))
        mask = scoBuffer.CScoBuffer3D(npImg.shape, type)
        mask.all_set_voxel(clearValue)

        xInx, yInx, zInx = np.where(npImg > 0)
        mask.set_voxel((xInx, yInx, zInx), voxel)
        return mask
    @staticmethod
    def load_mask(fullPath : str, mask : scoBuffer.CScoBuffer3D, type : str, voxel) :
        sitkImg = scoUtil.CScoUtilSimpleITK.load_image(fullPath, None)
        npImg = scoUtil.CScoUtilSimpleITK.sitkImg_to_npImg(sitkImg, type).transpose((2, 1, 0))
        xInx, yInx, zInx = np.where(npImg > 0)
        mask.set_voxel((xInx, yInx, zInx), voxel)
    @staticmethod
    def append_mask(dstMask : scoBuffer.CScoBuffer3D, srcMask : scoBuffer.CScoBuffer3D, voxel) :
        xInx, yInx, zInx = srcMask.get_voxel_inx_with_greater(0)
        dstMask.set_voxel((xInx, yInx, zInx), voxel)
    @staticmethod
    def find_files(listOutPath : list, listSrcPath : list, listDstPath : list) :
        for srcPath in listSrcPath :
            if srcPath in listDstPath :
                listOutPath.append(srcPath)


    def __init__(self) -> None :
        pass
    def process(self) -> None :
        pass
    

    def get_surface_voxel(self, mask : scoBuffer.CScoBuffer3D) :
        xInx, yInx, zInx = mask.get_voxel_inx_with_greater(0)

        surfaceXInx = []
        surfaceYInx = []
        surfaceZInx = []

        for inx, _ in enumerate(xInx) :
            voxelInx = (xInx[inx], yInx[inx], zInx[inx])
            if self.is_tumor_surface(mask, voxelInx) == True :
                surfaceXInx.append(voxelInx[0])
                surfaceYInx.append(voxelInx[1])
                surfaceZInx.append(voxelInx[2])
        
        return (surfaceXInx, surfaceYInx, surfaceZInx)
    def get_surface_type(self, mask : scoBuffer.CScoBuffer3D, voxelInx : tuple) :
        """
        ret
            0 : outside surface
            1 : inside surface
            2 : ambiguous surface
        """
        list0 = []
        list1 = []
        list100 = []
        for z in range(voxelInx[2] - 1, voxelInx[2] + 2) :
            for y in range(voxelInx[1] - 1, voxelInx[1] + 2) :
                for x in range(voxelInx[0] - 1, voxelInx[0] + 2) :
                    voxel = mask.get_voxel((x, y, z))
                    if voxel == 0 :
                        list0.append(0)
                    elif voxel == 1 :
                        list1.append(1)
                    else :
                        list100.append(100)

        len0 = len(list0)
        len100 = len(list100)
        if len0 > 0 and len100 > 0 :
            return self.eSurfaceType_ambiguous
        elif len0 > 0 :
            return self.eSurfaceType_outside
        else :
            return self.eSurfaceType_inside
    def is_tumor_surface(self, mask : scoBuffer.CScoBuffer3D, voxelInx : tuple) :
        ret = int(np.sum(mask.m_npBuf[voxelInx[0] - 1 : voxelInx[0] + 2, voxelInx[1] - 1 : voxelInx[1] + 2, voxelInx[2] - 1 : voxelInx[2] + 2]))
        if ret < 27 :
            return True
        return False
    def is_exo(self, maskKidney : scoBuffer.CScoBuffer3D, maskCyst : scoBuffer.CScoBuffer3D) :
        maskTmp = maskKidney.clone("uint8")
        maskTmp.all_set_voxel(0)
        xInx, yInx, zInx = maskKidney.get_voxel_inx_with_greater(0)
        maskTmp.set_voxel((xInx, yInx, zInx), self.eMaskID_kidney)

        xInx, yInx, zInx = maskCyst.get_voxel_inx_with_greater(0)
        maskTmp.set_voxel((xInx, yInx, zInx), self.eMaskID_tumor)

        surX, surY, surZ = self.get_surface_voxel(maskCyst)
        for inx in range(0, len(surX)) :
            voxelInx = (surX[inx], surY[inx], surZ[inx])
            surfaceType = self.get_surface_type(maskTmp, voxelInx)
            if surfaceType == self.eSurfaceType_outside or surfaceType == self.eSurfaceType_ambiguous :
                return True
        return False
    


