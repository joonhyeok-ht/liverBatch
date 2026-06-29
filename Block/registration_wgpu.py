import sys
import os
import math
import numpy as np
import wgpu

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
solutionPath = os.path.dirname(fileAbsPath)
sys.path.append(fileAbsPath)
sys.path.append(solutionPath)

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algVTK as algVTK
import AlgUtil.algImage as algImage
import AlgUtil.algGeometry as algGeometry

from Algorithm import scoMath

import resampling_wgpu as resampling_wgpu
import multiProcessTask as multiProcessTask
import optionInfo as optionInfo

from collections import deque
import multiprocessing as mp

from collections import defaultdict

import time

DICE_WORKGROUP_SIZE = 64


def align_to(value, alignment):
    return ((value + alignment - 1) // alignment) * alignment


rigidRefinedDiceShaderCode = f"""
struct DiceParams {{
    cropMinAndVoxelCount: vec4<i32>,
    anchorOffset: vec4<i32>,
    targetSize: vec4<i32>,
}};

@group(0) @binding(0)
var targetTex: texture_3d<u32>;

@group(0) @binding(1)
var srcCropTex: texture_3d<u32>;

@group(0) @binding(2)
var<storage, read_write> sums: array<atomic<u32>>;

@group(0) @binding(3)
var<uniform> params: DiceParams;

@compute
@workgroup_size({DICE_WORKGROUP_SIZE}, 1, 1)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {{
    let linear = i32(gid.x);
    let candidate = i32(gid.y);
    let voxelCount = params.cropMinAndVoxelCount.w;

    if (linear >= voxelCount || candidate >= 27) {{
        return;
    }}

    let cropDims = textureDimensions(srcCropTex);
    let cropWidth = i32(cropDims.x);
    let cropHeight = i32(cropDims.y);
    let cropArea = cropWidth * cropHeight;

    let z = linear / cropArea;
    let rem = linear - z * cropArea;
    let y = rem / cropWidth;
    let x = rem - y * cropWidth;

    let srcValue = textureLoad(srcCropTex, vec3<i32>(x, y, z), 0).r;

    let oz = candidate / 9 - 1;
    let oy = (candidate - (oz + 1) * 9) / 3 - 1;
    let ox = candidate - (oz + 1) * 9 - (oy + 1) * 3 - 1;

    let targetCoord = vec3<i32>(
        params.cropMinAndVoxelCount.x + x + params.anchorOffset.x + ox,
        params.cropMinAndVoxelCount.y + y + params.anchorOffset.y + oy,
        params.cropMinAndVoxelCount.z + z + params.anchorOffset.z + oz
    );

    var targetValue: u32 = 0u;
    if (
        targetCoord.x >= 0 && targetCoord.y >= 0 && targetCoord.z >= 0 &&
        targetCoord.x < params.targetSize.x &&
        targetCoord.y < params.targetSize.y &&
        targetCoord.z < params.targetSize.z
    ) {{
        targetValue = textureLoad(targetTex, targetCoord, 0).r;
    }}

    let base = u32(candidate * 3);
    atomicAdd(&sums[base + 0u], srcValue * targetValue);
    atomicAdd(&sums[base + 1u], targetValue);
    atomicAdd(&sums[base + 2u], srcValue);
}}
"""


class WgpuRigidRefinedTransform:
    """
    wgpu replacement for scoReg.CRegRigidRefinedTransform.
    Keeps the same public properties used by CRegistration.
    """
    def __init__(self) -> None:
        self.m_diceScore = 0.0
        self.m_offsetX = 0.0
        self.m_offsetY = 0.0
        self.m_offsetZ = 0.0
        self.m_matTargetPhy = scoMath.CScoMat4()

        try:
            self.m_wgpuResample = resampling_wgpu.wgpuResampling()
            self.device = self.m_wgpuResample.device
            self.maxGroupsPerDim = self.device.limits[
                "max-compute-workgroups-per-dimension"
            ]

            self.diceShader = self.device.create_shader_module(
                code=rigidRefinedDiceShaderCode
            )
            self._create_dice_pipeline()
        except Exception as exc:
            raise RuntimeError(
                f"wgpu registration failed while initializing GPU resources: {exc}"
            ) from exc

    def _create_dice_pipeline(self):
        self.diceBindGroupLayout = self.device.create_bind_group_layout(
            entries=[
                {
                    "binding": 0,
                    "visibility": wgpu.ShaderStage.COMPUTE,
                    "texture": {
                        "sample_type": wgpu.TextureSampleType.uint,
                        "view_dimension": wgpu.TextureViewDimension.d3,
                    },
                },
                {
                    "binding": 1,
                    "visibility": wgpu.ShaderStage.COMPUTE,
                    "texture": {
                        "sample_type": wgpu.TextureSampleType.uint,
                        "view_dimension": wgpu.TextureViewDimension.d3,
                    },
                },
                {
                    "binding": 2,
                    "visibility": wgpu.ShaderStage.COMPUTE,
                    "buffer": {
                        "type": wgpu.BufferBindingType.storage,
                    },
                },
                {
                    "binding": 3,
                    "visibility": wgpu.ShaderStage.COMPUTE,
                    "buffer": {
                        "type": wgpu.BufferBindingType.uniform,
                    },
                },
            ]
        )
        pipelineLayout = self.device.create_pipeline_layout(
            bind_group_layouts=[self.diceBindGroupLayout]
        )
        self.dicePipeline = self.device.create_compute_pipeline(
            layout=pipelineLayout,
            compute={
                "module": self.diceShader,
                "entry_point": "main",
            },
        )

    def _make_texture_from_np(self, npImg: np.ndarray):
        width, height, depth = npImg.shape
        bytesPerPixel = 4
        rawBytesPerRow = width * bytesPerPixel
        alignedBytesPerRow = align_to(rawBytesPerRow, 256)
        paddedWidth = alignedBytesPerRow // bytesPerPixel

        inputU32 = (npImg > 0).astype(np.uint32, copy=False)
        inputZyx = np.transpose(inputU32, (2, 1, 0))
        inputPadded = np.zeros((depth, height, paddedWidth), dtype=np.uint32)
        inputPadded[:, :, :width] = inputZyx

        texture = self.device.create_texture(
            size=(width, height, depth),
            dimension=wgpu.TextureDimension.d3,
            format=wgpu.TextureFormat.r32uint,
            usage=(
                wgpu.TextureUsage.COPY_DST |
                wgpu.TextureUsage.TEXTURE_BINDING
            ),
        )
        self.device.queue.write_texture(
            {
                "texture": texture,
                "mip_level": 0,
                "origin": (0, 0, 0),
            },
            inputPadded,
            {
                "offset": 0,
                "bytes_per_row": alignedBytesPerRow,
                "rows_per_image": height,
            },
            (width, height, depth),
        )
        return texture

    def _make_translation_matrix(self, rigidPhysicalOffset):
        npPhyMat = np.eye(4, dtype=np.float32)
        npPhyMat[0, 3] = -float(rigidPhysicalOffset[0])
        npPhyMat[1, 3] = -float(rigidPhysicalOffset[1])
        npPhyMat[2, 3] = -float(rigidPhysicalOffset[2])
        return npPhyMat

    def _resample_src_to_target(
        self,
        srcNp,
        srcOrigin,
        srcSpacing,
        srcDirection,
        targetOrigin,
        targetSpacing,
        targetDirection,
        targetSize,
        rigidPhysicalOffset,
    ):
        try:
            return self.m_wgpuResample.process(
                srcNp,
                srcOrigin,
                srcSpacing,
                srcDirection,
                targetOrigin,
                targetSpacing,
                targetDirection,
                outputSize=targetSize,
                npPhyMat=self._make_translation_matrix(rigidPhysicalOffset),
            )
        except Exception as exc:
            raise RuntimeError(f"wgpu registration failed during src resampling: {exc}") from exc

    def _evaluate_dice_candidates(
        self,
        targetTexture,
        srcCropTexture,
        targetShape,
        cropMin,
        cropShape,
        anchorOffset,
    ):
        voxelCount = int(cropShape[0] * cropShape[1] * cropShape[2])
        dispatchX = math.ceil(voxelCount / DICE_WORKGROUP_SIZE)
        dispatchY = 27
        if dispatchX > self.maxGroupsPerDim:
            raise RuntimeError(
                f"wgpu registration failed: dice dispatch too large ({dispatchX}, {dispatchY}, 1)"
            )

        sumsNp = np.zeros(27 * 3, dtype=np.uint32)
        sumsBuffer = self.device.create_buffer_with_data(
            data=sumsNp,
            usage=(
                wgpu.BufferUsage.STORAGE |
                wgpu.BufferUsage.COPY_SRC
            ),
        )
        readBufferSize = sumsNp.nbytes
        readBuffer = self.device.create_buffer(
            size=readBufferSize,
            usage=(
                wgpu.BufferUsage.COPY_DST |
                wgpu.BufferUsage.MAP_READ
            ),
        )
        paramsNp = np.array(
            [
                int(cropMin[0]), int(cropMin[1]), int(cropMin[2]), voxelCount,
                int(anchorOffset[0]), int(anchorOffset[1]), int(anchorOffset[2]), 0,
                int(targetShape[0]), int(targetShape[1]), int(targetShape[2]), 0,
            ],
            dtype=np.int32,
        )
        paramsBuffer = self.device.create_buffer_with_data(
            data=paramsNp,
            usage=wgpu.BufferUsage.UNIFORM,
        )
        bindGroup = self.device.create_bind_group(
            layout=self.diceBindGroupLayout,
            entries=[
                {
                    "binding": 0,
                    "resource": targetTexture.create_view(),
                },
                {
                    "binding": 1,
                    "resource": srcCropTexture.create_view(),
                },
                {
                    "binding": 2,
                    "resource": {
                        "buffer": sumsBuffer,
                    },
                },
                {
                    "binding": 3,
                    "resource": {
                        "buffer": paramsBuffer,
                    },
                },
            ],
        )

        encoder = self.device.create_command_encoder()
        computePass = encoder.begin_compute_pass()
        computePass.set_pipeline(self.dicePipeline)
        computePass.set_bind_group(0, bindGroup)
        computePass.dispatch_workgroups(dispatchX, dispatchY, 1)
        computePass.end()
        encoder.copy_buffer_to_buffer(
            sumsBuffer,
            0,
            readBuffer,
            0,
            readBufferSize,
        )
        self.device.queue.submit([encoder.finish()])
        self.device.queue.on_submitted_work_done_sync()

        readBuffer.map_sync(wgpu.MapMode.READ, 0, readBufferSize)
        try:
            outputData = readBuffer.read_mapped(0, readBufferSize)
            sums = np.frombuffer(outputData, dtype=np.uint32).copy().reshape(27, 3)
        finally:
            readBuffer.unmap()

        diceScores = []
        for candidate in range(27):
            intersect = int(sums[candidate, 0])
            targetSum = int(sums[candidate, 1])
            srcSum = int(sums[candidate, 2])
            denom = targetSum + srcSum
            if denom == 0:
                diceScores.append(0.0)
            else:
                diceScores.append(round((2 * intersect) / denom, 3))
        return diceScores

    def _gradient_descent(self, targetNp, srcNp):
        self.m_diceScore = 0.0
        self.m_offsetX = 0.0
        self.m_offsetY = 0.0
        self.m_offsetZ = 0.0

        srcInx = np.where(srcNp > 0)
        if srcInx[0].size == 0:
            return

        srcMin = np.array(
            [np.min(srcInx[0]), np.min(srcInx[1]), np.min(srcInx[2])],
            dtype=np.int32,
        )
        srcMax = np.array(
            [np.max(srcInx[0]), np.max(srcInx[1]), np.max(srcInx[2])],
            dtype=np.int32,
        )
        srcCrop = srcNp[
            srcMin[0]:srcMax[0] + 1,
            srcMin[1]:srcMax[1] + 1,
            srcMin[2]:srcMax[2] + 1,
        ]
        if srcCrop.size == 0 or np.sum(srcCrop) == 0:
            return

        targetTexture = self._make_texture_from_np(targetNp)
        srcCropTexture = self._make_texture_from_np(srcCrop)
        targetShape = np.array(targetNp.shape, dtype=np.int32)
        cropShape = np.array(srcCrop.shape, dtype=np.int32)

        maxOffset = np.array([0, 0, 0], dtype=np.int32)
        maxDiceScore = 0.0
        bUpdate = True
        iIterCnt = 0

        while bUpdate == True and iIterCnt < 1000:
            anchorOffset = maxOffset.copy()
            bUpdate = False
            diceScores = self._evaluate_dice_candidates(
                targetTexture=targetTexture,
                srcCropTexture=srcCropTexture,
                targetShape=targetShape,
                cropMin=srcMin,
                cropShape=cropShape,
                anchorOffset=anchorOffset,
            )

            candidateInx = 0
            for offsetZ in range(-1, 2):
                nowOffsetZ = int(anchorOffset[2]) + offsetZ
                for offsetY in range(-1, 2):
                    nowOffsetY = int(anchorOffset[1]) + offsetY
                    for offsetX in range(-1, 2):
                        nowOffsetX = int(anchorOffset[0]) + offsetX
                        minV = srcMin + np.array(
                            [nowOffsetX, nowOffsetY, nowOffsetZ],
                            dtype=np.int32,
                        )
                        maxV = srcMax + np.array(
                            [nowOffsetX, nowOffsetY, nowOffsetZ],
                            dtype=np.int32,
                        )

                        if not (
                            minV[0] >= 0 and 0 <= maxV[0] < targetShape[0] and
                            minV[1] >= 0 and 0 <= maxV[1] < targetShape[1] and
                            minV[2] >= 0 and 0 <= maxV[2] < targetShape[2]
                        ):
                            candidateInx += 1
                            continue

                        nowDiceScore = diceScores[candidateInx]
                        if nowDiceScore > maxDiceScore:
                            if offsetX == 0 and offsetY == 0 and offsetZ == 0:
                                candidateInx += 1
                                continue
                            maxDiceScore = nowDiceScore
                            maxOffset = np.array(
                                [nowOffsetX, nowOffsetY, nowOffsetZ],
                                dtype=np.int32,
                            )
                            bUpdate = True

                        candidateInx += 1
            iIterCnt += 1

        self.m_offsetX = float(maxOffset[0])
        self.m_offsetY = float(maxOffset[1])
        self.m_offsetZ = float(maxOffset[2])
        self.m_diceScore = maxDiceScore

    def process(self, srcNiftiFullPath: str, targetNiftiFullPath: str, rigidPhysicalOffset: list):
        targetNp, targetOrigin, targetSpacing, targetDirection, targetSize = algImage.CAlgImage.get_np_from_nifti(
            targetNiftiFullPath
        )
        srcNp, srcOrigin, srcSpacing, srcDirection, srcSize = algImage.CAlgImage.get_np_from_nifti(
            srcNiftiFullPath
        )

        self.m_matTargetPhy = scoMath.CScoMath.get_mat_with_spacing_direction_origin(
            targetSpacing,
            targetDirection,
            targetOrigin,
        )

        if np.where(targetNp > 0)[0].size == 0 or np.where(srcNp > 0)[0].size == 0:
            return

        resampledSrcNp = self._resample_src_to_target(
            srcNp=srcNp,
            srcOrigin=srcOrigin,
            srcSpacing=srcSpacing,
            srcDirection=srcDirection,
            targetOrigin=targetOrigin,
            targetSpacing=targetSpacing,
            targetDirection=targetDirection,
            targetSize=targetSize,
            rigidPhysicalOffset=rigidPhysicalOffset,
        )
        self._gradient_descent(targetNp, resampledSrcNp)

    @property
    def DiceScore(self):
        return self.m_diceScore

    @property
    def OffsetX(self):
        return self.m_offsetX

    @property
    def OffsetY(self):
        return self.m_offsetY

    @property
    def OffsetZ(self):
        return self.m_offsetZ

    @property
    def MatTargetPhy(self):
        return self.m_matTargetPhy


class CRegistration() :
    @staticmethod
    def get_rigid_physical_offset(targetInfo, srcInfo):
        targetVertex = targetInfo[0]
        targetOrigin = targetInfo[1]
        targetSpacing = targetInfo[2]
        targetDirection = targetInfo[3]

        srcVertex = srcInfo[0]
        srcOrigin = srcInfo[1]
        srcSpacing = srcInfo[2]
        srcDirection = srcInfo[3]

        targetMatPhysical = algVTK.CVTK.get_phy_matrix(targetOrigin, targetSpacing, targetDirection)
        srcMatPhysical = algVTK.CVTK.get_phy_matrix(srcOrigin, srcSpacing, srcDirection)

        targetAABB = algGeometry.CScoAABB()
        targetAABB.init_with_vertex(targetVertex)
        srcAABB = algGeometry.CScoAABB()
        srcAABB.init_with_vertex(srcVertex)

        targetMin = algLinearMath.CScoMath.mul_mat4_vec3(targetMatPhysical, targetAABB.Min)
        targetMax = algLinearMath.CScoMath.mul_mat4_vec3(targetMatPhysical, targetAABB.Max)
        targetAABB.init_with_min_max(targetMin, targetMax)

        srcMin = algLinearMath.CScoMath.mul_mat4_vec3(srcMatPhysical, srcAABB.Min)
        srcMax = algLinearMath.CScoMath.mul_mat4_vec3(srcMatPhysical, srcAABB.Max)
        srcAABB.init_with_min_max(srcMin, srcMax)

        targetCenter = targetAABB.Center
        srcCenter = srcAABB.Center
        retOffset = targetCenter - srcCenter

        return retOffset
    
    
    
    def __init__(self) -> None :
        super().__init__()
        # input your code 
        self.m_inputOptionInfo = None
        self.m_inputMaskPath = ""
        self.m_outputListOffset = defaultdict(lambda: np.empty((0, 3), dtype=float))
    def clear(self) :
        # input your code
        self.m_inputOptionInfo = None
        self.m_inputMaskPath = ""
        if self.m_outputListOffset is not None :
            self.m_outputListOffset.clear()
        super().clear()
    
    def process(self):
        if self.InputOptionInfo is None:
            print("reg : not found optionInfo")
            return False
        if self.InputMaskPath == "":
            print("reg : not setting input mask path")
            return False

        listParam = []
        paramCnt = 0

        iRegInfoCnt = self.InputOptionInfo.get_registrationinfo_count()
        for inx in range(0, iRegInfoCnt):
            targetMaskName, srcMaskName, rigidAABB = self.InputOptionInfo.get_registrationinfo(inx)

            targetFullPath = os.path.join(self.InputMaskPath, f"{targetMaskName}.nii.gz")
            srcFullPath = os.path.join(self.InputMaskPath, f"{srcMaskName}.nii.gz")

            listParam.append((paramCnt, targetFullPath, srcFullPath, rigidAABB))
            paramCnt += 1

        if paramCnt == 0:
            print("passed registration")
            return True

        if paramCnt == 0 :
            #print("passed removed vessel stricture")
            return
        
        
        progress_callback=getattr(self, "progress_callback", None)
        is_interrupted=getattr(self, "is_interrupted", None)
        done = 0
        if len(listParam) > 0 :
            #super().process(self._task, listParam)
            for i in range(len(listParam)):
                self._task(listParam[i])
                
                done += 1
                if progress_callback:
                    percent = int(done * 100 / len(listParam))
                    # progress_callback 시그니처가 (value) 인지 (value, status)인지 둘 다 대응
                    try:
                        progress_callback(percent, f"Registration...")
                    except TypeError:
                        progress_callback(percent)

                if is_interrupted and is_interrupted():
                    print("!!!!!!!!!!!!!!!!!!!!!!!!!!", file=sys.__stdout__, flush=True)
                    return False

        return True

    
    def _task(self, param : tuple) :
        inx = param[0]
        targetFullPath = param[1]
        srcFullPath = param[2]
        rigidAABB = param[3]

        if os.path.exists(targetFullPath) == False or os.path.exists(srcFullPath) == False :
            print("-" * 30)
            print(f"not found registration files")
            print(f"target path : {targetFullPath}")
            print(f"src path : {srcFullPath}")
            print("-" * 30)
            self.m_outputListOffset[inx] = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0])
        else :
            if rigidAABB == 1 :
                ctVertex, ctOrigin, ctSpacing, ctDirection, ctSize = algImage.CAlgImage.get_vertex_from_nifti(targetFullPath)
                mrVertex, mrOrigin, mrSpacing, mrDirection, mrSize = algImage.CAlgImage.get_vertex_from_nifti(srcFullPath)
                rigidPhysicalOffset = self.__get_rigid_physical_offset(
                    (ctVertex, ctOrigin, ctSpacing, ctDirection),
                    (mrVertex, mrOrigin, mrSpacing, mrDirection)
                )

                offsetX = float(rigidPhysicalOffset[0, 0])
                offsetY = float(rigidPhysicalOffset[0, 1])
                offsetZ = float(rigidPhysicalOffset[0, 2])
            else :
                offsetX = 0.0
                offsetY = 0.0
                offsetZ = 0.0
                rigidPhysicalOffset = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0])
            reg = WgpuRigidRefinedTransform()
            reg.process(srcFullPath, targetFullPath, [offsetX, offsetY, offsetZ])
            diceScore = reg.DiceScore
            offsetX = reg.OffsetX
            offsetY = reg.OffsetY
            offsetZ = reg.OffsetZ

            matTargetPhy = reg.MatTargetPhy.m_npMat.copy()
            matTargetPhy = algLinearMath.CScoMath.from_mat3_to_mat4(matTargetPhy[0 : 3, 0 : 3])
            offsetV = algLinearMath.CScoMath.to_vec4([offsetX, offsetY, offsetZ, 1.0])
            phyOffsetV = algLinearMath.CScoMath.from_vec4_to_vec3(algLinearMath.CScoMath.mul_mat4_vec4(matTargetPhy, offsetV))
            phyOffsetV = phyOffsetV + rigidPhysicalOffset

            self.m_outputListOffset[inx] = phyOffsetV
            #print(f"completed registration {srcFullPath}")

    def __get_rigid_physical_offset(self, targetInfo : tuple, srcInfo : tuple) -> np.ndarray :
        targetVertex = targetInfo[0]
        targetOrigin = targetInfo[1]
        targetSpacing = targetInfo[2]
        targetDirection = targetInfo[3]

        srcVertex = srcInfo[0]
        srcOrigin = srcInfo[1]
        srcSpacing = srcInfo[2]
        srcDirection = srcInfo[3]

        targetMatPhysical = algVTK.CVTK.get_phy_matrix(targetOrigin, targetSpacing, targetDirection)
        srcMatPhysical = algVTK.CVTK.get_phy_matrix(srcOrigin, srcSpacing, srcDirection)

        targetAABB = algGeometry.CScoAABB()
        targetAABB.init_with_vertex(targetVertex)
        srcAABB = algGeometry.CScoAABB()
        srcAABB.init_with_vertex(srcVertex)

        targetMin = algLinearMath.CScoMath.mul_mat4_vec3(targetMatPhysical, targetAABB.Min)
        targetMax = algLinearMath.CScoMath.mul_mat4_vec3(targetMatPhysical, targetAABB.Max)
        targetAABB.init_with_min_max(targetMin, targetMax)

        srcMin = algLinearMath.CScoMath.mul_mat4_vec3(srcMatPhysical, srcAABB.Min)
        srcMax = algLinearMath.CScoMath.mul_mat4_vec3(srcMatPhysical, srcAABB.Max)
        srcAABB.init_with_min_max(srcMin, srcMax)

        targetCenter = targetAABB.Center
        srcCenter = srcAABB.Center
        retOffset = targetCenter - srcCenter

        return retOffset
    

    @property
    def InputOptionInfo(self) -> optionInfo.COptionInfo :
        return self.m_inputOptionInfo
    @InputOptionInfo.setter
    def InputOptionInfo(self, inputOptionInfo : optionInfo.COptionInfo) :
        self.m_inputOptionInfo = inputOptionInfo
    @property
    def InputMaskPath(self) -> str :
        return self.m_inputMaskPath
    @InputMaskPath.setter
    def InputMaskPath(self, inputMaskPath : str) :
        self.m_inputMaskPath = inputMaskPath
    @property
    def OutputListOffset(self) -> list :
        return self.m_outputListOffset


if __name__ == '__main__' :
    pass


# print ("ok ..")

