import sys
import os
import numpy as np
import SimpleITK as sitk

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
solutionPath = os.path.dirname(fileAbsPath)
sys.path.append(fileAbsPath)
sys.path.append(solutionPath)

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage

import multiProcessTask as multiProcessTask
import niftiContainer as niftiContainer
import optionInfo as optionInfo

import math
import wgpu

import gc

WORKGROUP_SIZE_X = 8
WORKGROUP_SIZE_Y = 8
WORKGROUP_SIZE_Z = 4


def align_to(value, alignment):
    return ((value + alignment - 1) // alignment) * alignment


resampleShaderCode = f"""
struct Params {{
    inputOrigin: vec4<f32>,
    inputSpacing: vec4<f32>,
    outputOrigin: vec4<f32>,
    outputSpacing: vec4<f32>,

    inputDir0: vec4<f32>,
    inputDir1: vec4<f32>,
    inputDir2: vec4<f32>,

    outputDir0: vec4<f32>,
    outputDir1: vec4<f32>,
    outputDir2: vec4<f32>,
    
    phyMat0: vec4<f32>,
    phyMat1: vec4<f32>,
    phyMat2: vec4<f32>,
    phyMat3: vec4<f32>,
}};

@group(0) @binding(0)
var inputTex: texture_3d<u32>;

@group(0) @binding(1)
var outputTex: texture_storage_3d<r32uint, write>;

@group(0) @binding(2)
var<uniform> params: Params;

fn mat3_mul_vec3(
    r0: vec4<f32>,
    r1: vec4<f32>,
    r2: vec4<f32>,
    v: vec3<f32>
) -> vec3<f32> {{
    return vec3<f32>(
        dot(r0.xyz, v),
        dot(r1.xyz, v),
        dot(r2.xyz, v)
    );
}}

@compute
@workgroup_size({WORKGROUP_SIZE_X}, {WORKGROUP_SIZE_Y}, {WORKGROUP_SIZE_Z})
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {{
    let outputDims = textureDimensions(outputTex);
    let inputDims = textureDimensions(inputTex);

    if (
        gid.x >= outputDims.x ||
        gid.y >= outputDims.y ||
        gid.z >= outputDims.z
    ) {{
        return;
    }}

    let outputIndex = vec3<f32>(
        f32(gid.x),
        f32(gid.y),
        f32(gid.z)
    );

    let outputOffset = vec3<f32>(
        outputIndex.x * params.outputSpacing.x,
        outputIndex.y * params.outputSpacing.y,
        outputIndex.z * params.outputSpacing.z
    );

    let physicalPoint =
        params.outputOrigin.xyz +
        mat3_mul_vec3(
            params.outputDir0,
            params.outputDir1,
            params.outputDir2,
            outputOffset
        );

    let inputPhysicalPoint = vec3<f32>(
        dot(params.phyMat0, vec4<f32>(physicalPoint, 1.0)),
        dot(params.phyMat1, vec4<f32>(physicalPoint, 1.0)),
        dot(params.phyMat2, vec4<f32>(physicalPoint, 1.0))
    );

    let inputPhysicalOffset = inputPhysicalPoint - params.inputOrigin.xyz;

    // SimpleITK direction은 보통 orthonormal이므로 inverse(direction) = transpose(direction)
    let inputContinuous = vec3<f32>(
        dot(
            vec3<f32>(
                params.inputDir0.x,
                params.inputDir1.x,
                params.inputDir2.x
            ),
            inputPhysicalOffset
        ) / params.inputSpacing.x,

        dot(
            vec3<f32>(
                params.inputDir0.y,
                params.inputDir1.y,
                params.inputDir2.y
            ),
            inputPhysicalOffset
        ) / params.inputSpacing.y,

        dot(
            vec3<f32>(
                params.inputDir0.z,
                params.inputDir1.z,
                params.inputDir2.z
            ),
            inputPhysicalOffset
        ) / params.inputSpacing.z
    );

    let ix = i32(round(inputContinuous.x));
    let iy = i32(round(inputContinuous.y));
    let iz = i32(round(inputContinuous.z));

    let outputCoord = vec3<i32>(
        i32(gid.x),
        i32(gid.y),
        i32(gid.z)
    );

    if (
        ix < 0 || iy < 0 || iz < 0 ||
        ix >= i32(inputDims.x) ||
        iy >= i32(inputDims.y) ||
        iz >= i32(inputDims.z)
    ) {{
        textureStore(outputTex, outputCoord, vec4<u32>(0u, 0u, 0u, 0u));
        return;
    }}

    let value = textureLoad(
        inputTex,
        vec3<i32>(ix, iy, iz),
        0
    ).r;

    textureStore(outputTex, outputCoord, vec4<u32>(value, 0u, 0u, 0u));
}}
"""


class wgpuResampling:
    def __init__(self):
        self.adapter = wgpu.gpu.request_adapter_sync(
            power_preference="high-performance"
        )

        self.device = self.adapter.request_device_sync()

        self.shader = self.device.create_shader_module(
            code=resampleShaderCode
        )

        self.bindGroupLayout = self.device.create_bind_group_layout(
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
                    "storage_texture": {
                        "access": wgpu.StorageTextureAccess.write_only,
                        "format": wgpu.TextureFormat.r32uint,
                        "view_dimension": wgpu.TextureViewDimension.d3,
                    },
                },
                {
                    "binding": 2,
                    "visibility": wgpu.ShaderStage.COMPUTE,
                    "buffer": {
                        "type": wgpu.BufferBindingType.uniform
                    },
                },
            ]
        )

        self.pipelineLayout = self.device.create_pipeline_layout(
            bind_group_layouts=[self.bindGroupLayout]
        )

        self.pipeline = self.device.create_compute_pipeline(
            layout=self.pipelineLayout,
            compute={
                "module": self.shader,
                "entry_point": "main",
            },
        )

        self.maxGroupsPerDim = self.device.limits[
            "max-compute-workgroups-per-dimension"
        ]

    def _make_params_np(
        self,
        inputOrigin,
        inputSpacing,
        inputDirection,
        outputOrigin,
        outputSpacing,
        outputDirection,
        npPhyMat=None,
    ):
        inputDirection = np.asarray(inputDirection, dtype=np.float32).reshape(3, 3)
        outputDirection = np.asarray(outputDirection, dtype=np.float32).reshape(3, 3)
        
        if npPhyMat is None:
            npPhyMat = np.eye(4, dtype=np.float32)
        else:
            npPhyMat = np.asarray(npPhyMat, dtype=np.float32).reshape(4, 4)

        params = np.array(
            [
                inputOrigin[0], inputOrigin[1], inputOrigin[2], 0.0,
                inputSpacing[0], inputSpacing[1], inputSpacing[2], 0.0,
                outputOrigin[0], outputOrigin[1], outputOrigin[2], 0.0,
                outputSpacing[0], outputSpacing[1], outputSpacing[2], 0.0,

                inputDirection[0, 0], inputDirection[0, 1], inputDirection[0, 2], 0.0,
                inputDirection[1, 0], inputDirection[1, 1], inputDirection[1, 2], 0.0,
                inputDirection[2, 0], inputDirection[2, 1], inputDirection[2, 2], 0.0,

                outputDirection[0, 0], outputDirection[0, 1], outputDirection[0, 2], 0.0,
                outputDirection[1, 0], outputDirection[1, 1], outputDirection[1, 2], 0.0,
                outputDirection[2, 0], outputDirection[2, 1], outputDirection[2, 2], 0.0,
                    
                npPhyMat[0, 0], npPhyMat[0, 1], npPhyMat[0, 2], npPhyMat[0, 3],
                npPhyMat[1, 0], npPhyMat[1, 1], npPhyMat[1, 2], npPhyMat[1, 3],
                npPhyMat[2, 0], npPhyMat[2, 1], npPhyMat[2, 2], npPhyMat[2, 3],
                npPhyMat[3, 0], npPhyMat[3, 1], npPhyMat[3, 2], npPhyMat[3, 3],
            ],
            dtype=np.float32,
        )

        return params

    def process(
        self,
        inputNp: np.ndarray,
        inputOrigin,
        inputSpacing,
        inputDirection,
        outputOrigin,
        outputSpacing,
        outputDirection,
        outputSize=None,
        npPhyMat=None,
    ) -> np.ndarray:
        assert inputNp.ndim == 3

        inputWidth, inputHeight, inputDepth = inputNp.shape

        if outputSize == None:
            outputSize = [
                int(round(inputNp.shape[i] * (inputSpacing[i] / outputSpacing[i])))
                for i in range(3)
            ]

        outputWidth, outputHeight, outputDepth = map(int, outputSize)

        dispatchX = math.ceil(outputWidth / WORKGROUP_SIZE_X)
        dispatchY = math.ceil(outputHeight / WORKGROUP_SIZE_Y)
        dispatchZ = math.ceil(outputDepth / WORKGROUP_SIZE_Z)

        if (
            dispatchX > self.maxGroupsPerDim or
            dispatchY > self.maxGroupsPerDim or
            dispatchZ > self.maxGroupsPerDim
        ):
            raise RuntimeError(
                f"Dispatch too large: ({dispatchX}, {dispatchY}, {dispatchZ})"
            )

        bytesPerPixel = 4

        inputRawBytesPerRow = inputWidth * bytesPerPixel
        inputAlignedBytesPerRow = align_to(inputRawBytesPerRow, 256)
        inputPaddedWidth = inputAlignedBytesPerRow // bytesPerPixel

        outputRawBytesPerRow = outputWidth * bytesPerPixel
        outputAlignedBytesPerRow = align_to(outputRawBytesPerRow, 256)
        outputPaddedWidth = outputAlignedBytesPerRow // bytesPerPixel
        outputBufferSize = outputDepth * outputHeight * outputAlignedBytesPerRow

        inputU32 = inputNp.astype(np.uint32, copy=False)

        inputZyx = np.transpose(inputU32, (2, 1, 0))

        inputPadded = np.zeros(
            (inputDepth, inputHeight, inputPaddedWidth),
            dtype=np.uint32,
        )
        inputPadded[:, :, :inputWidth] = inputZyx
        
        del inputNp
        del inputZyx
        del inputU32
        gc.collect()
        

        inputTexture = self.device.create_texture(
            size=(inputWidth, inputHeight, inputDepth),
            dimension=wgpu.TextureDimension.d3,
            format=wgpu.TextureFormat.r32uint,
            usage=(
                wgpu.TextureUsage.COPY_DST |
                wgpu.TextureUsage.TEXTURE_BINDING
            ),
        )

        outputTexture = self.device.create_texture(
            size=(outputWidth, outputHeight, outputDepth),
            dimension=wgpu.TextureDimension.d3,
            format=wgpu.TextureFormat.r32uint,
            usage=(
                wgpu.TextureUsage.STORAGE_BINDING |
                wgpu.TextureUsage.COPY_SRC
            ),
        )

        outputBuffer = self.device.create_buffer(
            size=outputBufferSize,
            usage=(
                wgpu.BufferUsage.COPY_DST |
                wgpu.BufferUsage.MAP_READ
            ),
        )

        paramsNp = self._make_params_np(
            inputOrigin=inputOrigin,
            inputSpacing=inputSpacing,
            inputDirection=inputDirection,
            outputOrigin=outputOrigin,
            outputSpacing=outputSpacing,
            outputDirection=outputDirection,
            npPhyMat=npPhyMat,
        )

        paramsBuffer = self.device.create_buffer_with_data(
            data=paramsNp,
            usage=wgpu.BufferUsage.UNIFORM,
        )

        bindGroup = self.device.create_bind_group(
            layout=self.bindGroupLayout,
            entries=[
                {
                    "binding": 0,
                    "resource": inputTexture.create_view(),
                },
                {
                    "binding": 1,
                    "resource": outputTexture.create_view(),
                },
                {
                    "binding": 2,
                    "resource": {
                        "buffer": paramsBuffer,
                    },
                },
            ],
        )

        self.device.queue.write_texture(
            {
                "texture": inputTexture,
                "mip_level": 0,
                "origin": (0, 0, 0),
            },
            inputPadded,
            {
                "offset": 0,
                "bytes_per_row": inputAlignedBytesPerRow,
                "rows_per_image": inputHeight,
            },
            (inputWidth, inputHeight, inputDepth),
        )

        encoder = self.device.create_command_encoder()

        computePass = encoder.begin_compute_pass()
        computePass.set_pipeline(self.pipeline)
        computePass.set_bind_group(0, bindGroup)
        computePass.dispatch_workgroups(dispatchX, dispatchY, dispatchZ)
        computePass.end()

        encoder.copy_texture_to_buffer(
            {
                "texture": outputTexture,
                "mip_level": 0,
                "origin": (0, 0, 0),
            },
            {
                "buffer": outputBuffer,
                "offset": 0,
                "bytes_per_row": outputAlignedBytesPerRow,
                "rows_per_image": outputHeight,
            },
            (outputWidth, outputHeight, outputDepth),
        )

        self.device.queue.submit([encoder.finish()])
        self.device.queue.on_submitted_work_done_sync()

        outputBuffer.map_sync(
            wgpu.MapMode.READ,
            0,
            outputBufferSize,
        )

        try:
            outputData = outputBuffer.read_mapped(
                0,
                outputBufferSize,
            )

            outputNpPadded = np.frombuffer(
                outputData,
                dtype=np.uint32,
            ).reshape(outputDepth, outputHeight, outputPaddedWidth)

            outputZyx = outputNpPadded[:, :, :outputWidth]
            outputXyz = np.transpose(outputZyx, (2, 1, 0))

            outputNp = outputXyz.astype(np.uint8, copy=True)

        finally:
            outputBuffer.unmap()

        return outputNp
        
class CResamplingToPhase() :
    def __init__(self) :
        self.m_wgpuResample = wgpuResampling()
        self.m_inputOptionInfo = None
        self.m_inputPhase = None
        self.m_inputMaskPath = ""
        self.m_outputMaskPath = ""
    def clear(self) :
        self.m_inputOptionInfo = None
        self.m_inputPhase = None
        self.m_inputMaskPath = ""
        self.m_outputMaskPath = ""
    def process(self) :
        if self.InputOptionInfo is None :
            print("resampling : not setting input option info")
            return
        if self.InputPhase is None :
            print("resampling : not setting input phase")
            return
        if self.InputMaskPath == "" :
            print("stricture : not setting input mask path")
            return 
        if self.OutputMaskPath == "" :
            print("stricture : not setting output mask path")
            return 
        
        if not os.path.exists(self.InputMaskPath) :
            os.makedirs(self.InputMaskPath)
        if not os.path.exists(self.OutputMaskPath) :
            os.makedirs(self.OutputMaskPath)
        
        listParam = []
        iCnt = self.InputOptionInfo.get_resampling_phase_count()
        for inx in range(0, iCnt) :
            inMaskName, outMaskName, targetPhase = self.InputOptionInfo.get_resampling_phase(inx)
            srcPhase = self.InputOptionInfo.find_phase_of_mask(inMaskName)

            inMaskFullPath = os.path.join(self.InputMaskPath, f"{inMaskName}.nii.gz")
            outMaskFullPath = os.path.join(self.OutputMaskPath, f"{outMaskName}.nii.gz")

            if os.path.exists(inMaskFullPath) == False :
                print(f"skip resampling : {inMaskName} os.path.exists(inMaskFullPath) == False", file=sys.__stdout__, flush=True)
                continue
            targetPhaseInfo = self.InputPhase.find_phaseinfo(targetPhase)
            if targetPhaseInfo is None or targetPhaseInfo.is_valid() == False :
                print(f"skip resampling : {inMaskName} targetPhaseInfo is None", file=sys.__stdout__, flush=True)
                continue
            srcPhaseInfo = self.InputPhase.find_phaseinfo(srcPhase)
            if srcPhaseInfo is None or srcPhaseInfo.is_valid() == False :
                print(f"skip resampling : {inMaskName} srcPhaseInfo is None", file=sys.__stdout__, flush=True)
                continue

            listParam.append((inMaskFullPath, outMaskFullPath, srcPhaseInfo, targetPhaseInfo))
        
        if len(listParam) > 0 :
            for i in range(len(listParam)):
                self._task(listParam[i])

    def _task(self, param : tuple) :
        inMaskFullPath = param[0]
        outMaskFullPath = param[1]
        srcPhaseInfo = param[2]
        targetPhaseInfo = param[3]
        
        targetOffset = targetPhaseInfo.Offset
        srcOffset = srcPhaseInfo.Offset
        targetTrans = algLinearMath.CScoMath.translation_mat4(targetOffset)
        srcTrans = algLinearMath.CScoMath.translation_mat4(srcOffset)
        srcTrans = algLinearMath.CScoMath.inv_mat4(srcTrans)
        resamplingTrans = algLinearMath.CScoMath.mul_mat4_mat4(srcTrans, targetTrans)
        
        ############
            
        npImg, origin, spacing, direction, size = algImage.CAlgImage.get_np_from_nifti(
            inMaskFullPath
        )

        resampledNpImg = self.m_wgpuResample.process(
            inputNp=npImg,
            inputOrigin=origin,
            inputSpacing=spacing,
            inputDirection=direction,
            outputOrigin=targetPhaseInfo.Origin,
            outputSpacing=targetPhaseInfo.Spacing,
            outputDirection=targetPhaseInfo.Direction,
            outputSize=targetPhaseInfo.Size,
            npPhyMat = resamplingTrans
        )

        algImage.CAlgImage.save_nifti_from_np(
            outMaskFullPath,
            resampledNpImg,
            targetPhaseInfo.Origin,
            targetPhaseInfo.Spacing,
            targetPhaseInfo.Direction,
            (2, 1, 0),
        )

        #print(f"completed resampling to phase {os.path.basename(outMaskFullPath)}" ,file=sys.__stdout__, flush=True)


    @property
    def InputOptionInfo(self) -> optionInfo.COptionInfo :
        return self.m_inputOptionInfo
    @InputOptionInfo.setter
    def InputOptionInfo(self, inputOptionInfo : optionInfo.COptionInfo) :
        self.m_inputOptionInfo = inputOptionInfo
    @property
    def InputPhase(self) -> niftiContainer.CPhase :
        return self.m_inputPhase
    @InputPhase.setter
    def InputPhase(self, inputPhase : niftiContainer.CPhase) :
        self.m_inputPhase = inputPhase
    @property
    def InputMaskPath(self) -> str :
        return self.m_inputMaskPath
    @InputMaskPath.setter
    def InputMaskPath(self, inputMaskPath : str) :
        self.m_inputMaskPath = inputMaskPath

    @property
    def OutputMaskPath(self) -> str :
        return self.m_outputMaskPath
    @OutputMaskPath.setter
    def OutputMaskPath(self, outputMaskPath : str) :
        self.m_outputMaskPath = outputMaskPath



class CResamplingToMinSpacing() :
    def __init__(self) :
        self.m_wgpuResample = wgpuResampling()
        self.m_inputOptionInfo = None
        self.m_inputMaskPath = ""
        self.m_outputMaskPath = ""
    def clear(self) :
        self.m_inputOptionInfo = None
        self.m_inputMaskPath = ""
        self.m_outputMaskPath = ""
    def process(self) :
        if self.InputOptionInfo is None :
            print("resampling : not setting input option info")
            return
        if self.InputMaskPath == "" :
            print("stricture : not setting input mask path")
            return 
        if self.OutputMaskPath == "" :
            print("stricture : not setting output mask path")
            return 
        
        if not os.path.exists(self.InputMaskPath) :
            os.makedirs(self.InputMaskPath)
        if not os.path.exists(self.OutputMaskPath) :
            os.makedirs(self.OutputMaskPath)
        
        listParam = []

        iCnt = self.InputOptionInfo.get_resampling_minspacing_count()
        for inx in range(0, iCnt) :
            inMaskName, outMaskName = self.InputOptionInfo.get_resampling_minspacing(inx)

            inMaskFullPath = os.path.join(self.InputMaskPath, f"{inMaskName}.nii.gz")
            outMaskFullPath = os.path.join(self.OutputMaskPath, f"{outMaskName}.nii.gz")

            if os.path.exists(inMaskFullPath) == False :
                #print(f"skip resampling : {inMaskName}")
                continue

            listParam.append((inMaskFullPath, outMaskFullPath))
        
        
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
                        progress_callback(percent, f"Min Spacing")
                    except TypeError:
                        progress_callback(percent)

                if is_interrupted and is_interrupted():
                    return False


    # param (inMaskFullPath, outMaskFullPath)
    def _task(self, param : tuple) :
        inMaskFullPath = param[0]
        outMaskFullPath = param[1]

        npImg, origin, spacing, direction, size = algImage.CAlgImage.get_np_from_nifti(
            inMaskFullPath
        )

        minSpacing = min(spacing)

        newSpacing = [
            minSpacing,
            minSpacing,
            minSpacing,
        ]

        resampledNpImg = self.m_wgpuResample.process(
            inputNp=npImg,
            inputOrigin=origin,
            inputSpacing=spacing,
            inputDirection=direction,
            outputOrigin=origin,
            outputSpacing=newSpacing,
            outputDirection=direction,
        )

        algImage.CAlgImage.save_nifti_from_np(
            outMaskFullPath,
            resampledNpImg,
            origin,
            newSpacing,
            direction,
            (2, 1, 0),
        )

        # print(f"pre resampled mask: {inMaskFullPath}", file=sys.__stdout__, flush=True)
        # print(
        #     f"completed resampling to min spacing {os.path.basename(outMaskFullPath)}",
        #     file=sys.__stdout__,
        #     flush=True,
        # )


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
    def OutputMaskPath(self) -> str :
        return self.m_outputMaskPath
    @OutputMaskPath.setter
    def OutputMaskPath(self, outputMaskPath : str) :
        self.m_outputMaskPath = outputMaskPath


if __name__ == '__main__' :
    pass


# print ("ok ..")

