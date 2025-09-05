import numpy as np
import SimpleITK as sitk
import os, sys
import open3d as o3d
import open3d.visualization
#from matplotlib.patches import Rectangle
#import pickle

sys.path.append(os.path.dirname(__file__))
import scoUtil
import scoMath
import scoBuffer


class CRegTransform :
    """
    desc : src에서 target으로 이동되는 physical 좌표계에서의 offset을 구한다.
    """
    @staticmethod
    def create_buffer3d(sitkImg) -> tuple :
        """
        return (CScoBuffer3D, origin, spacing, direction)
        """
        npImg = scoUtil.CScoUtilSimpleITK.sitkImg_to_npImg(sitkImg, "uint8").transpose((2, 1, 0))
        mask = scoBuffer.CScoBuffer3D(npImg.shape, "uint8")
        mask.all_set_voxel(0)
        
        xInx, yInx, zInx = np.where(npImg > 0)
        mask.set_voxel((xInx, yInx, zInx), 1)
        return mask
    @staticmethod
    def get_aabb_with_mask(mask : scoBuffer.CScoBuffer3D) -> scoMath.CScoAABB:
        xInx, yInx, zInx = mask.get_voxel_inx_with_greater(0)
        npArr = np.array(
            [
                xInx, yInx, zInx
            ]
        )
        _min = np.min(npArr, axis=1)
        _max = np.max(npArr, axis=1)
        minV = scoMath.CScoVec3(_min[0], _min[1], _min[2])
        maxV = scoMath.CScoVec3(_max[0], _max[1], _max[2])
        aabb = scoMath.CScoAABB()
        aabb.make_min_max(minV, maxV)
        return aabb
    
    
    def __init__(self) -> None:
        self.m_diceScore = 0
        self.m_offsetX = 0
        self.m_offsetY = 0
        self.m_offsetZ = 0
        self.m_matTargetPhy = scoMath.CScoMat4()
    def process(self, srcNiftiFullPath : str, targetNiftiFullPath : str) :
        sitkTarget = scoUtil.CScoUtilSimpleITK.load_image(targetNiftiFullPath, None)
        targetOrigin = sitkTarget.GetOrigin()
        targetDirection = sitkTarget.GetDirection()
        targetSpacing = sitkTarget.GetSpacing()
        targetSize = sitkTarget.GetSize()

        self.m_matTargetPhy = scoMath.CScoMath.get_mat_with_spacing_direction_origin(targetSpacing, targetDirection, targetOrigin)

        # src loading & resampling 
        sitkSrc = scoUtil.CScoUtilSimpleITK.load_image(srcNiftiFullPath, None)
        sitkSrc = sitk.Resample(
                    sitkSrc,
                    targetSize,
                    sitk.Transform(),
                    sitk.sitkNearestNeighbor,
                    targetOrigin,
                    targetSpacing,
                    targetDirection,
                    0,
                    sitkTarget.GetPixelID(),
                )
        self.m_targetMask = CRegTransform.create_buffer3d(sitkTarget)
        self.m_srcMask = CRegTransform.create_buffer3d(sitkSrc)
        self._gradient_descent()


    # protected
    def _gradient_descent(self) :
        self.m_diceScore = 0
        self.m_offsetX = 0
        self.m_offsetY = 0
        self.m_offsetZ = 0

        maxOffsetX = self.m_offsetX
        maxOffsetY = self.m_offsetY
        maxOffsetZ = self.m_offsetZ
        maxDiceScore = self.DiceScore

        bUpdate = True
        iIterCnt = 0

        srcAABB = CRegTransform.get_aabb_with_mask(self.m_srcMask)
        npSrcCrop = self.m_srcMask.get_crop(srcAABB.Min, srcAABB.Max)

        while bUpdate == True and iIterCnt < 1000 :
            anchorDiceScore = maxDiceScore
            anchorOffsetX = maxOffsetX
            anchorOffsetY = maxOffsetY
            anchorOffsetZ = maxOffsetZ
            bUpdate = False

            for offsetZ in range(-1, 2) :
                nowOffsetZ = anchorOffsetZ + offsetZ
                for offsetY in range(-1, 2) :
                    nowOffsetY = anchorOffsetY + offsetY
                    for offsetX in range(-1, 2) :
                        nowOffsetX = anchorOffsetX + offsetX
                        minV = scoMath.CScoVec3(srcAABB.Min.X + nowOffsetX, srcAABB.Min.Y + nowOffsetY, srcAABB.Min.Z + nowOffsetZ)
                        maxV = scoMath.CScoVec3(srcAABB.Max.X + nowOffsetX, srcAABB.Max.Y + nowOffsetY, srcAABB.Max.Z + nowOffsetZ)
                        nowDiceScore = self.m_targetMask.get_dice_score(npSrcCrop, minV, maxV)
                        if nowDiceScore > maxDiceScore :
                            if offsetX == 0 and offsetY == 0 and offsetZ == 0 :
                                continue
                            maxDiceScore = nowDiceScore
                            maxOffsetX = nowOffsetX
                            maxOffsetY = nowOffsetY
                            maxOffsetZ = nowOffsetZ

                            bUpdate = True
            iIterCnt += 1

        self.m_offsetX = maxOffsetX
        self.m_offsetY = maxOffsetY
        self.m_offsetZ = maxOffsetZ  
        self.m_diceScore = maxDiceScore
    

    @property
    def DiceScore(self) :
        return self.m_diceScore
    @property
    def OffsetX(self) :
        return self.m_offsetX
    @property
    def OffsetY(self) :
        return self.m_offsetY
    @property
    def OffsetZ(self) :
        return self.m_offsetZ
    @property
    def MatTargetPhy(self) :
        return self.m_matTargetPhy





class CRegRigidRefinedTransform(CRegTransform) :
    """
    desc : aabb rigid transform + refined transform
    """
    @staticmethod
    def calc_aabb_center(aabb : scoMath.CScoAABB) -> scoMath.CScoVec3 :
        center = aabb.Min.add(aabb.Max)
        center = scoMath.CScoMath.mul_vec3_scalar(center, 0.5)
        return center
    

    def __init__(self) -> None:
        super().__init__()
    def process(self, srcNiftiFullPath : str, targetNiftiFullPath : str, rigidPhysicalOffset : list) :
        sitkTarget = scoUtil.CScoUtilSimpleITK.load_image(targetNiftiFullPath, None)
        targetOrigin = sitkTarget.GetOrigin()
        targetDirection = sitkTarget.GetDirection()
        targetSpacing = sitkTarget.GetSpacing()
        targetSize = sitkTarget.GetSize()

        self.m_matTargetPhy = scoMath.CScoMath.get_mat_with_spacing_direction_origin(targetSpacing, targetDirection, targetOrigin)

        # src loading & resampling 
        rigidPhysicalOffset = [-offset for offset in rigidPhysicalOffset]
        transform = sitk.TranslationTransform(3, rigidPhysicalOffset)
        sitkSrc = scoUtil.CScoUtilSimpleITK.load_image(srcNiftiFullPath, None)
        sitkSrc = sitk.Resample(
                    sitkSrc,
                    targetSize,
                    transform,
                    sitk.sitkNearestNeighbor,
                    targetOrigin,
                    targetSpacing,
                    targetDirection,
                    0,
                    sitkTarget.GetPixelID(),
                )
        self.m_targetMask = CRegTransform.create_buffer3d(sitkTarget)
        self.m_srcMask = CRegTransform.create_buffer3d(sitkSrc)
        self.m_srcAABB = CRegTransform.get_aabb_with_mask(self.m_srcMask)

        self._gradient_descent()


    # protected
    def _gradient_descent(self) :
        self.m_diceScore = 0
        self.m_offsetX = 0.0
        self.m_offsetY = 0.0
        self.m_offsetZ = 0.0

        maxOffsetX = self.m_offsetX
        maxOffsetY = self.m_offsetY
        maxOffsetZ = self.m_offsetZ
        maxDiceScore = self.DiceScore

        bUpdate = True
        iIterCnt = 0

        srcAABB = self.m_srcAABB
        npSrcCrop = self.m_srcMask.get_crop(srcAABB.Min, srcAABB.Max)

        while bUpdate == True and iIterCnt < 1000 :
            anchorDiceScore = maxDiceScore
            anchorOffsetX = maxOffsetX
            anchorOffsetY = maxOffsetY
            anchorOffsetZ = maxOffsetZ
            bUpdate = False

            for offsetZ in range(-1, 2) :
                nowOffsetZ = anchorOffsetZ + offsetZ
                for offsetY in range(-1, 2) :
                    nowOffsetY = anchorOffsetY + offsetY
                    for offsetX in range(-1, 2) :
                        nowOffsetX = anchorOffsetX + offsetX
                        minV = scoMath.CScoVec3(srcAABB.Min.X + nowOffsetX, srcAABB.Min.Y + nowOffsetY, srcAABB.Min.Z + nowOffsetZ)
                        maxV = scoMath.CScoVec3(srcAABB.Max.X + nowOffsetX, srcAABB.Max.Y + nowOffsetY, srcAABB.Max.Z + nowOffsetZ)
                        nowDiceScore = self.m_targetMask.get_dice_score(npSrcCrop, minV, maxV)
                        if nowDiceScore > maxDiceScore :
                            if offsetX == 0 and offsetY == 0 and offsetZ == 0 :
                                continue
                            maxDiceScore = nowDiceScore
                            maxOffsetX = nowOffsetX
                            maxOffsetY = nowOffsetY
                            maxOffsetZ = nowOffsetZ

                            bUpdate = True
            iIterCnt += 1

        self.m_offsetX = maxOffsetX
        self.m_offsetY = maxOffsetY
        self.m_offsetZ = maxOffsetZ  
        self.m_diceScore = maxDiceScore
    

    @property
    def DiceScore(self) :
        return self.m_diceScore
    @property
    def OffsetX(self) :
        return self.m_offsetX
    @property
    def OffsetY(self) :
        return self.m_offsetY
    @property
    def OffsetZ(self) :
        return self.m_offsetZ
    @property
    def MatTargetPhy(self) :
        return self.m_matTargetPhy



