import sys
import os
# import torch
# from torch.autograd import Variable
import numpy as np
import math
# from scipy import ndimage
from scipy.ndimage import binary_erosion
import SimpleITK as sitk
# from sklearn.decomposition import PCA


fileAbsPath = os.path.abspath(os.path.dirname(__file__))
algorithmPath = os.path.dirname(fileAbsPath)
sys.path.append(fileAbsPath)
sys.path.append(algorithmPath)

# import algLinearMath
# import algGeometry
import Algorithm.scoUtil as scoUtil
import Algorithm.scoBuffer as scoBuffer
import Algorithm.scoBufferAlg as scoBufferAlg


class CAlgImage :
    @staticmethod
    def create_np(shape, type = np.uint32) :
        npImg = np.zeros(shape, dtype=type)
        return npImg
    @staticmethod
    def get_vertex_from_nifti(niftiPath : str) -> tuple :
        """
        return (vertex, origin, spacing, direction, size)
        """
        sitkImg = scoUtil.CScoUtilSimpleITK.load_image(niftiPath, None)
        npImg = scoUtil.CScoUtilSimpleITK.sitkImg_to_npImg(sitkImg, "uint8").transpose((2, 1, 0))
        vertex = np.array(np.where(npImg > 0), dtype=np.int32).transpose()

        origin = sitkImg.GetOrigin()
        spacing = sitkImg.GetSpacing()
        direction = sitkImg.GetDirection()
        size = sitkImg.GetSize()
        return (vertex, origin, spacing, direction, size)
    @staticmethod
    def get_np_from_nifti(niftiPath : str) -> tuple :
        """
        return (npImg, origin, spacing, direction, size)
        """
        sitkImg = scoUtil.CScoUtilSimpleITK.load_image(niftiPath, None)
        npImg = scoUtil.CScoUtilSimpleITK.sitkImg_to_npImg(sitkImg, "uint8").transpose((2, 1, 0))

        origin = sitkImg.GetOrigin()
        spacing = sitkImg.GetSpacing()
        direction = sitkImg.GetDirection()
        size = sitkImg.GetSize()
        return (npImg, origin, spacing, direction, size)
    @staticmethod
    def get_vertex_from_np(npImg : np.ndarray, dtype=np.float32) -> np.ndarray :
        vertex = np.array(np.where(npImg > 0), dtype=dtype).transpose()
        return vertex
    @staticmethod
    def get_vertex_from_np_value(npImg : np.ndarray, value, dtype=np.float32) -> np.ndarray :
        coord = np.where(npImg == value)
        if coord[0].size == 0 :
            return None
        vertex = np.array(coord, dtype=dtype).transpose()
        return vertex
    @staticmethod
    def get_vertex_by_line(npImg : np.ndarray, start : np.ndarray, end : np.ndarray, value, dtype=np.float32) -> np.ndarray :
        start = start.reshape(3,)
        end = end.reshape(3,)

        delta = np.abs(end - start)
        step = np.sign(end - start)
        error = delta / 2
        position = start.copy()

        line = []
        for _ in range(delta.max()):
            condition = (error >= delta).astype(int)
            error -= delta * condition
            position += step * condition
            line.append(position.copy())  # Ensure position is appended as a new copy
            error += delta

        line = np.array(line, dtype=dtype)
        validMask = npImg[tuple(line.T)] == value
        validPos = line[validMask].astype(dtype)

        if validPos.shape[0] == 0 :
            return None
        return validPos
    @staticmethod
    def get_sitk_from_np(npImg : np.ndarray, origin, spacing, direction) :
        sitkImg = scoUtil.CScoUtilSimpleITK.npImg_to_sitkImg(npImg.transpose((2, 1, 0)))
        sitkImg.SetOrigin(origin)
        sitkImg.SetSpacing(spacing)
        sitkImg.SetDirection(direction)
        return sitkImg
    @staticmethod
    def get_np_from_sitk(sitkImg, dtype=np.float32) -> tuple :
        """
        dtype : np.uint8 (default)
        return (npImg, origin, spacing, direction, size)
        """
        npImg = scoUtil.CScoUtilSimpleITK.sitkImg_to_npImg(sitkImg, dtype).transpose((2, 1, 0))
        origin = sitkImg.GetOrigin()
        spacing = sitkImg.GetSpacing()
        direction = sitkImg.GetDirection()
        size = sitkImg.GetSize()
        return (npImg, origin, spacing, direction, size)
    

    @staticmethod
    def resampling_sitkimg(
        sitkImg, 
        newOrigin, newSpacing, newDirection,
        sitkIntp = sitk.sitkNearestNeighbor
        ) :
        originalSize = sitkImg.GetSize()
        originalSpacing = sitkImg.GetSpacing()

        newSize = [
            int(round(originalSize[i] * (originalSpacing[i] / newSpacing[i])))
            for i in range(3)
        ]
  
        # Resample filter 초기화
        resampler = sitk.ResampleImageFilter()
        resampler.SetOutputSpacing(newSpacing)
        resampler.SetSize(newSize)
        resampler.SetOutputDirection(newDirection)
        resampler.SetOutputOrigin(newOrigin)
        resampler.SetTransform(sitk.Transform())
        # resampler.SetInterpolator(sitk.sitkLinear)
        resampler.SetInterpolator(sitkIntp)
        
        # Resampling 실행
        resampledImg = resampler.Execute(sitkImg)
        return resampledImg
    @staticmethod
    def resampling_sitkimg_with_mat(
        sitkImg, 
        targetOrigin, targetSpacing, targetDirection, targetSize, sitkPixelID,
        sitkIntp = sitk.sitkNearestNeighbor,
        npPhyMat = None
        ) :
        """
        sitkPixelID : sitkImg.GetPixelID()
        sitkIntp : sitk.sitkNearestNeighbor, sitk.sitkLinear
        return : resampledSitkImg
        """
        if npPhyMat is not None :
            rotScaleMatrix = npPhyMat[:3, :3].flatten()
            transVector = npPhyMat[:3, 3]

            transform = sitk.AffineTransform(3)
            transform.SetMatrix(rotScaleMatrix.tolist())
            transform.SetTranslation(transVector.tolist())
        else :
            transform = sitk.Transform()

        resampledSitkImg = sitk.Resample(
            sitkImg,
            targetSize,
            transform,
            sitkIntp,
            targetOrigin,
            targetSpacing,
            targetDirection,
            0,
            sitkPixelID,
        )
        return resampledSitkImg
    
    # resampling을 통해 미세조정을 수행한다. 
    # 즉 미세조정 offset이 필요하다. 

    


    @staticmethod
    def save_nifti_from_np(
        niftiFullPath : str, 
        npImg : np.ndarray,
        origin : tuple, spacing : tuple, direction : tuple,
        transpose : tuple
        ) :
        sitkImg = scoUtil.CScoUtilSimpleITK.npImg_to_sitkImg(npImg.transpose(transpose))
        sitkImg.SetOrigin(origin)
        sitkImg.SetSpacing(spacing)
        sitkImg.SetDirection(direction)
        scoUtil.CScoUtilSimpleITK.save_nifti(niftiFullPath, sitkImg)
    
    @staticmethod
    def set_clear(npImg : np.ndarray, value) :
        npImg[:, :, :] = value
    @staticmethod
    def set_value(npImg : np.ndarray, voxelInx : np.ndarray, value) :
        voxelInx = voxelInx.T
        npImg[voxelInx[0], voxelInx[1], voxelInx[2]] = value
    @staticmethod
    def get_value(npImg : np.ndarray, voxelInx : np.ndarray) -> np.ndarray :
        voxelInx = voxelInx.T
        value = npImg[voxelInx[0], voxelInx[1], voxelInx[2]]
        return value.astype(np.uint8)
    
    
    @staticmethod
    def get_removed_stricture_voxel_index(npImg : np.ndarray) -> np.ndarray :
        mask = scoBuffer.CScoBuffer3D(npImg.shape, "uint8")
        mask.NpImg = npImg
        algRemoveStricture = scoBufferAlg.CAlgRemoveStricture()
        algRemoveStricture.process(mask)
        mask = algRemoveStricture.RemovedStrictureMask
        inx = mask.get_voxel_inx_with_greater(0)
        return np.array(inx, dtype=np.int32).transpose()
    @staticmethod
    def get_removed_stricture_voxel_index_from_nifti(niftiFullPath : str) -> np.ndarray :
        mask, origin, spacing, direction = scoBuffer.CScoBuffer3D.create_instance(niftiFullPath, (2, 1, 0), "uint8", "uint8", 1, 0)
        algRemoveStricture = scoBufferAlg.CAlgRemoveStricture()
        algRemoveStricture.process(mask)
        mask = algRemoveStricture.RemovedStrictureMask
        inx = mask.get_voxel_inx_with_greater(0)
        return np.array(inx, dtype=np.int32).transpose()
    @staticmethod
    def get_removed_stricture_voxel_index_from_vertex(vertex : np.ndarray, shape) -> np.ndarray :
        npImg = CAlgImage.create_np(shape, np.uint8)
        CAlgImage.set_clear(npImg, 0)
        CAlgImage.set_value(npImg, vertex, 1)
        return CAlgImage.get_removed_stricture_voxel_index(npImg)
    @staticmethod
    def get_surface_np(npImg : np.ndarray) -> np.ndarray :
        npBinary = npImg > 0
        npEroded = binary_erosion(npBinary)
        npSurface = (npBinary & ~npEroded).astype(np.uint8)
        npSurface[npSurface == 1] = 255
        return npSurface
    @staticmethod
    def get_cc(npImg : np.ndarray, spacing : list) :
        voxelCnt = CAlgImage.get_vertex_from_np(npImg, np.int32).shape[0]
        return spacing[0] * spacing[1] * spacing[2] * voxelCnt * 0.001
    
    @staticmethod
    def trans_coord_aview_to_np(npSize : tuple, aViewSagi : int, aViewCoronal : int, aViewAxial : int) -> tuple :
        """
        ret : (x, y, z) of npImg
        """
        maxX = npSize[0] - 1
        maxY = npSize[1] - 1
        maxZ = npSize[2] - 1

        coordX = maxX - aViewSagi + 1
        coordY = aViewCoronal - 1
        coordZ = maxZ - aViewAxial + 1

        return (coordX, coordY, coordZ)
    @staticmethod
    def trans_coord_np_to_aview(npSize : tuple, x : int, y : int, z : int) -> tuple :
        """
        ret : (sagittal, coronal, axial)
        """
        maxX = npSize[0] - 1
        maxY = npSize[1] - 1
        maxZ = npSize[2] - 1

        sag = maxX - x + 1
        coronal = y + 1
        axial = maxZ - z + 1

        return (sag, coronal, axial)



    def __init__(self) -> None:
        pass

