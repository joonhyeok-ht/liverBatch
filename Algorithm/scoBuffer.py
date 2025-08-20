import matplotlib.pyplot as plt
#import SimpleITK as sitk
import cv2
import numpy as np
import os, sys
import open3d as o3d
import open3d.core
import open3d.visualization

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
sys.path.append(fileAbsPath)

import scoUtil
import scoMath
from abc import abstractmethod

import open3d as o3d
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering

from scipy import ndimage


class CScoBuffer3D :
    @staticmethod
    def create_instance(niftiPath : str, transpose : tuple, niftiType : str, maskType : str, maskValue, maskClearValue) -> tuple :
        """
        return (CScoBuffer3D, origin, spacing, direction)
        """
        sitkImg = scoUtil.CScoUtilSimpleITK.load_image(niftiPath, None)
        npImg = scoUtil.CScoUtilSimpleITK.sitkImg_to_npImg(sitkImg, niftiType).transpose(transpose)
        mask = CScoBuffer3D(npImg.shape, maskType)
        mask.all_set_voxel(maskClearValue)
        
        xInx, yInx, zInx = np.where(npImg > 0)
        mask.set_voxel((xInx, yInx, zInx), maskValue)

        origin = sitkImg.GetOrigin()
        spacing = sitkImg.GetSpacing()
        direction = sitkImg.GetDirection()

        npImg = None
        sitkImg = None
        return (mask, origin, spacing, direction)
    
    # @staticmethod
    # def xor(buf0 : CScoBuffer3D, buf1 : CScoBuffer3D) :



    def __init__(self, shape : tuple, type : str) :
        '''
        type : string
                ex) 'bool', 'uint8', 'int32' 등등 
        '''
        self.m_npBuf = np.zeros(shape, dtype = type)
        self.m_clearValue = 0
        
    def clear(self) :
        self.m_npBuf = None
        self.m_clearValue = 0
    def clone(self, type : str) :
        return CScoBuffer3D(self.Shape, type)


    def all_set_voxel(self, voxel) :
        self.m_npBuf[:, :, :] = voxel
        self.m_clearValue = voxel
    def set_voxel(self, voxelInx : tuple, voxel) :
        self.m_npBuf[voxelInx] = voxel
    def get_voxel(self, voxelInx : tuple) :
        return self.m_npBuf[voxelInx]
    def get_voxel_inx_with_equal(self, voxel) :
        return np.where(self.m_npBuf == voxel)
    def get_voxel_inx_with_greater(self, voxel) :
        return np.where(self.m_npBuf > voxel)
    def get_voxel_inx_with_less(self, voxel) :
        return np.where(self.m_npBuf < voxel)
    def get_line_voxel_inx(self, startVoxelInx : tuple, endVoxelInx : tuple) :
        """
        ret : (lineLen, listXInx, listYInx, listZInx)
        """
        iLen = 0
        listXInx = []
        listYInx = []
        listZInx = []

        x1 = int(startVoxelInx[0])
        y1 = int(startVoxelInx[1])
        z1 = int(startVoxelInx[2])

        x2 = int(endVoxelInx[0])
        y2 = int(endVoxelInx[1])
        z2 = int(endVoxelInx[2])

        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        dz = abs(z2 - z1)
        if (x2 > x1):
            xs = 1
        else:
            xs = -1
        if (y2 > y1):
            ys = 1
        else:
            ys = -1
        if (z2 > z1):
            zs = 1
        else:
            zs = -1
    
        # Driving axis is X-axis"
        if (dx >= dy and dx >= dz) :       
            p1 = 2 * dy - dx
            p2 = 2 * dz - dx
            while (x1 != x2):
                x1 += xs
                if (p1 >= 0):
                    y1 += ys
                    p1 -= 2 * dx
                if (p2 >= 0):
                    z1 += zs
                    p2 -= 2 * dx
                p1 += 2 * dy
                p2 += 2 * dz

                iLen += 1
                listXInx.append(x1)
                listYInx.append(y1)
                listZInx.append(z1)
        # Driving axis is Y-axis"
        elif (dy >= dx and dy >= dz) :
            p1 = 2 * dx - dy
            p2 = 2 * dz - dy
            while (y1 != y2):
                y1 += ys
                if (p1 >= 0):
                    x1 += xs
                    p1 -= 2 * dy
                if (p2 >= 0):
                    z1 += zs
                    p2 -= 2 * dy
                p1 += 2 * dx
                p2 += 2 * dz

                iLen += 1
                listXInx.append(x1)
                listYInx.append(y1)
                listZInx.append(z1)
        # Driving axis is Z-axis"
        else :       
            p1 = 2 * dy - dz
            p2 = 2 * dx - dz
            while (z1 != z2):
                z1 += zs
                if (p1 >= 0):
                    y1 += ys
                    p1 -= 2 * dz
                if (p2 >= 0):
                    x1 += xs
                    p2 -= 2 * dz
                p1 += 2 * dy
                p2 += 2 * dx

                iLen += 1
                listXInx.append(x1)
                listYInx.append(y1)
                listZInx.append(z1)
        
        return (iLen, listXInx, listYInx, listZInx)
    
    def set_sitk_img(self, sitkImg, transpose : tuple, type : str) :
        '''
        type : uint8, .. 
        '''
        self.m_npBuf = scoUtil.CScoUtilSimpleITK.sitkImg_to_npImg(sitkImg, type).transpose(transpose)
        self.m_clearValue = 0
    def get_sitk_img(
            self, 
            origin : tuple, spacing : tuple, direction : tuple,
            transpose : tuple
        ) :
        sitkImg = scoUtil.CScoUtilSimpleITK.npImg_to_sitkImg(self.m_npBuf.transpose(transpose))
        sitkImg.SetOrigin(origin)
        sitkImg.SetSpacing(spacing)
        sitkImg.SetDirection(direction)
        return sitkImg
    
    def dilation(self, connectivity : int) :
        struct2 = ndimage.generate_binary_structure(3, connectivity)
        self.m_npBuf = ndimage.binary_dilation(self.m_npBuf, structure=struct2).astype(self.m_npBuf.dtype)
    def erosion(self, connectivity : int) :
        struct2 = ndimage.generate_binary_structure(3, connectivity)
        self.m_npBuf = ndimage.binary_erosion(self.m_npBuf, structure=struct2).astype(self.m_npBuf.dtype)

    def get_crop(self, minV : scoMath.CScoVec3, maxV : scoMath.CScoVec3) -> np.ndarray :
        iMin = (int(minV.X + 0.5), int(minV.Y + 0.5), int(minV.Z + 0.5))
        iMax = (int(maxV.X + 0.5), int(maxV.Y + 0.5), int(maxV.Z + 0.5))
        return self.m_npBuf[iMin[0] : iMax[0] + 1, iMin[1] : iMax[1] + 1, iMin[2] : iMax[2] + 1]
    def get_dice_score(self, targetCrop : np.ndarray, minV : scoMath.CScoVec3, maxV : scoMath.CScoVec3) -> float :
        srcCrop = self.get_crop(minV, maxV)
        intersect = np.sum(srcCrop * targetCrop)
        fsum = np.sum(srcCrop)
        ssum = np.sum(targetCrop)
        dice = (2 * intersect ) / (fsum + ssum)
        dice = round(dice, 3)                       # for easy reading
        return dice
    def get_pcd_with_equal(self, voxel, color : tuple) :
        npCoord = np.array(self.get_voxel_inx_with_equal(voxel)).T
        return self.get_pcd(npCoord, color)
    def get_pcd_with_greater(self, voxel, color : tuple) :
        npCoord = np.array(self.get_voxel_inx_with_greater(voxel)).T
        return self.get_pcd(npCoord, color)
    def get_pcd_with_less(self, voxel, color : tuple) :
        npCoord = np.array(self.get_voxel_inx_with_less(voxel)).T
        return self.get_pcd(npCoord, color)
    def get_pcd(self, npCoord, color : tuple) :
        if npCoord.shape[0] == 0 :
            return None
        coordColor = npCoord.copy()
        # order : r, g, b  range : 0.0 ~ 1.0
        coordColor[:,0] = color[0]
        coordColor[:,1] = color[1]
        coordColor[:,2] = color[2]

        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(npCoord)
        pcd.colors = o3d.utility.Vector3dVector(coordColor)

        return pcd
    

    @property
    def Shape(self) :
        return self.m_npBuf.shape
    @property
    def ClearValue(self) :
        return self.m_clearValue
    @property
    def NpImg(self) :
        return self.m_npBuf
    @NpImg.setter
    def NpImg(self, npImg : np.ndarray) :
        self.m_npBuf = npImg

