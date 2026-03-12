import sys
import os
import numpy as np

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
solutionPath = os.path.dirname(fileAbsPath)
sys.path.append(fileAbsPath)
sys.path.append(solutionPath)

import AlgUtil.algImage as algImage

import multiProcessTask as multiProcessTask
import optionInfo as optionInfo

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


def relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(x, 0.0)


def minpool_nd(x: np.ndarray, kernel_size=3, pad_mode="edge") -> np.ndarray:
    """
    N-D min pooling (2D/3D 모두 가능)
    x: (...), float array
    kernel_size: int 또는 각 축별 tuple
    """
    x = np.asarray(x, dtype=np.float32)

    if isinstance(kernel_size, int):
        kernel_size = (kernel_size,) * x.ndim
    if len(kernel_size) != x.ndim:
        raise ValueError("kernel_size length must match x.ndim")

    pad_width = [(k // 2, k // 2) for k in kernel_size]
    x_pad = np.pad(x, pad_width, mode=pad_mode)

    windows = sliding_window_view(x_pad, kernel_size)
    # windows shape:
    # x.shape + kernel_size
    reduce_axes = tuple(range(x.ndim, windows.ndim))
    return windows.min(axis=reduce_axes)


def maxpool_nd(x: np.ndarray, kernel_size=3, pad_mode="edge") -> np.ndarray:
    """
    N-D max pooling (2D/3D 모두 가능)
    """
    x = np.asarray(x, dtype=np.float32)

    if isinstance(kernel_size, int):
        kernel_size = (kernel_size,) * x.ndim
    if len(kernel_size) != x.ndim:
        raise ValueError("kernel_size length must match x.ndim")

    pad_width = [(k // 2, k // 2) for k in kernel_size]
    x_pad = np.pad(x, pad_width, mode=pad_mode)

    windows = sliding_window_view(x_pad, kernel_size)
    reduce_axes = tuple(range(x.ndim, windows.ndim))
    return windows.max(axis=reduce_axes)


def soft_skeleton(
    I: np.ndarray,
    k: int,
    kernel_size=3,
    pad_mode="edge",
    clip_output=True,
    exact_paper=False,
) -> np.ndarray:
    """
    NumPy 구현의 soft-skeleton

    Parameters
    ----------
    I : np.ndarray
        입력 마스크/확률맵. 보통 [0, 1] 범위 float.
        2D, 3D 모두 가능.
    k : int
        반복 횟수
    kernel_size : int or tuple
        min/max pooling 윈도우 크기. 논문 취지상 보통 3 사용.
    pad_mode : str
        np.pad mode
    clip_output : bool
        결과를 [0, 1]로 클리핑할지 여부
    exact_paper : bool
        True면 논문의 "for i <- 0 to k do"를 그대로 따라
        총 (k+1)번 반복.
        False면 일반적으로 많이 쓰는 k번 반복.

    Returns
    -------
    S : np.ndarray
        soft skeleton
    """
    I = np.asarray(I, dtype=np.float32).copy()

    # 초기 단계:
    # I' <- maxpool(minpool(I))
    # S  <- ReLU(I - I')
    I_open = maxpool_nd(minpool_nd(I, kernel_size, pad_mode), kernel_size, pad_mode)
    S = relu(I - I_open)

    n_iter = k + 1 if exact_paper else k

    for _ in range(n_iter):
        # I <- minpool(I)
        I = minpool_nd(I, kernel_size, pad_mode)

        # I' <- maxpool(minpool(I))
        I_open = maxpool_nd(minpool_nd(I, kernel_size, pad_mode), kernel_size, pad_mode)

        # S <- S + (1 - S) o ReLU(I - I')
        delta = relu(I - I_open)
        S = S + (1.0 - S) * delta

    if clip_output:
        S = np.clip(S, 0.0, 1.0)

    return S

def _remove_stricture_task_worker(param: tuple):
    inx = param[0]
    inputMaskFullPath = param[1]
    outputMaskFullPath = param[2]

    npImg, origin, spacing, direction, size = algImage.CAlgImage.get_np_from_nifti(inputMaskFullPath)
    vertex = algImage.CAlgImage.get_vertex_from_np(npImg, np.int32)

    vesselVertex = algImage.CAlgImage.get_removed_stricture_voxel_index_from_vertex(vertex, size)
    algImage.CAlgImage.set_clear(npImg, 0)
    algImage.CAlgImage.set_value(npImg, vesselVertex, 255)
    algImage.CAlgImage.save_nifti_from_np(outputMaskFullPath, npImg, origin, spacing, direction, (2, 1, 0))

    print(f"completed removed stricture vessel {outputMaskFullPath}")

def crop_nonzero_bbox(vol, margin=3):
    nz = np.argwhere(vol > 0)
    if len(nz) == 0:
        return vol.copy(), (slice(0, vol.shape[0]), slice(0, vol.shape[1]), slice(0, vol.shape[2]))

    mins = np.maximum(nz.min(axis=0) - margin, 0)
    maxs = np.minimum(nz.max(axis=0) + margin + 1, vol.shape)

    slc = tuple(slice(mins[d], maxs[d]) for d in range(vol.ndim))
    return vol[slc].copy(), slc



if __name__ == "__main__":
    # mask = np.zeros((15, 15), dtype=np.float32)
    # mask[3:12, 6:9] = 1.0
    # mask[7:10, 3:12] = 1.0

    # print(mask)
    
    # S = soft_skeleton(mask, k=10, kernel_size=3)

    # print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    # print(S)
    
    npImg, origin, spacing, direction, size = algImage.CAlgImage.get_np_from_nifti("Vein.nii.gz")
    vertex = algImage.CAlgImage.get_vertex_from_np(npImg, np.int32)

    vesselVertex = algImage.CAlgImage.get_removed_stricture_voxel_index_from_vertex(vertex, size)
    algImage.CAlgImage.set_clear(npImg, 0)
    algImage.CAlgImage.set_value(npImg, vesselVertex, 1)
    
    cropped, slc = crop_nonzero_bbox(npImg, margin=5)

    S3 = soft_skeleton(cropped, k=10, kernel_size=3)
    
    algImage.CAlgImage.save_nifti_from_np("Vein_skel.nii.gz", cropped, origin, spacing, direction, (2, 1, 0))