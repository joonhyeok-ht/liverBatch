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
import wgpuRS as wgpuRS

import math
import wgpu

import gc

WORKGROUP_SIZE_X = 8
WORKGROUP_SIZE_Y = 8
WORKGROUP_SIZE_Z = 4

def align_to(value, alignment):
    return ((value + alignment - 1) // alignment) * alignment

shaderCode = f"""
@group(0) @binding(0)
var mask_tex: texture_3d<u32>;

@group(0) @binding(1)
var ret_tex: texture_storage_3d<r32uint, write>;

fn local_idx(x: u32, y: u32, z: u32) -> u32 {{
    return x * 25u + y * 5u + z;
}}

fn has_dilated_neighbor(x: u32, y: u32, z: u32, dims: vec3<u32>) -> bool {{
    for (var dx: i32 = -1; dx <= 1; dx++) {{
        for (var dy: i32 = -1; dy <= 1; dy++) {{
            for (var dz: i32 = -1; dz <= 1; dz++) {{
                let nx = i32(x) + dx;
                let ny = i32(y) + dy;
                let nz = i32(z) + dz;

                if (
                    nx < 0 || ny < 0 || nz < 0 ||
                    nx >= i32(dims.x) ||
                    ny >= i32(dims.y) ||
                    nz >= i32(dims.z)
                ) {{
                    continue;
                }}

                let v = textureLoad(
                    mask_tex,
                    vec3<i32>(nx, ny, nz),
                    0
                ).r;

                if (v > 0u) {{
                    return true;
                }}
            }}
        }}
    }}

    return false;
}}

@compute
@workgroup_size({WORKGROUP_SIZE_X}, {WORKGROUP_SIZE_Y}, {WORKGROUP_SIZE_Z})
fn pass_filter_and_compose(@builtin(global_invocation_id) gid: vec3<u32>) {{
    let dims = textureDimensions(mask_tex);

    let x = gid.x;
    let y = gid.y;
    let z = gid.z;

    if (x >= dims.x || y >= dims.y || z >= dims.z) {{
        return;
    }}

    let coord = vec3<i32>(i32(x), i32(y), i32(z));
    let maskV = textureLoad(mask_tex, coord, 0).r;

    if (maskV > 0u) {{
        textureStore(ret_tex, coord, vec4<u32>(255u, 0u, 0u, 0u));
        return;
    }}

    let dilatedV = has_dilated_neighbor(x, y, z, dims);

    if (!dilatedV) {{
        textureStore(ret_tex, coord, vec4<u32>(0u, 0u, 0u, 0u));
        return;
    }}

    if (
        x < 2u || y < 2u || z < 2u ||
        x + 2u >= dims.x ||
        y + 2u >= dims.y ||
        z + 2u >= dims.z
    ) {{
        textureStore(ret_tex, coord, vec4<u32>(255u, 0u, 0u, 0u));
        return;
    }}

    var occ: array<u32, 125>;
    var visited: array<u32, 125>;
    var stack: array<u32, 125>;

    for (var k: u32 = 0u; k < 125u; k++) {{
        occ[k] = 0u;
        visited[k] = 0u;
    }}

    for (var lx: u32 = 0u; lx < 5u; lx++) {{
        for (var ly: u32 = 0u; ly < 5u; ly++) {{
            for (var lz: u32 = 0u; lz < 5u; lz++) {{
                let gx = x + lx - 2u;
                let gy = y + ly - 2u;
                let gz = z + lz - 2u;

                let li = local_idx(lx, ly, lz);

                let v = textureLoad(
                    mask_tex,
                    vec3<i32>(i32(gx), i32(gy), i32(gz)),
                    0
                ).r;

                if (v > 0u) {{
                    occ[li] = 1u;
                }}
            }}
        }}
    }}

    var blobCount: u32 = 0u;

    for (var start: u32 = 0u; start < 125u; start++) {{
        if (occ[start] == 0u || visited[start] == 1u) {{
            continue;
        }}

        blobCount = blobCount + 1u;

        if (blobCount > 1u) {{
            textureStore(ret_tex, coord, vec4<u32>(0u, 0u, 0u, 0u));
            return;
        }}

        var sp: u32 = 0u;
        stack[sp] = start;
        sp = sp + 1u;
        visited[start] = 1u;

        loop {{
            if (sp == 0u) {{
                break;
            }}

            sp = sp - 1u;
            let cur = stack[sp];

            let cx = cur / 25u;
            let rem = cur - cx * 25u;
            let cy = rem / 5u;
            let cz = rem - cy * 5u;

            for (var dx: i32 = -1; dx <= 1; dx++) {{
                for (var dy: i32 = -1; dy <= 1; dy++) {{
                    for (var dz: i32 = -1; dz <= 1; dz++) {{
                        if (dx == 0 && dy == 0 && dz == 0) {{
                            continue;
                        }}

                        let nx = i32(cx) + dx;
                        let ny = i32(cy) + dy;
                        let nz = i32(cz) + dz;

                        if (
                            nx < 0 || ny < 0 || nz < 0 ||
                            nx >= 5 || ny >= 5 || nz >= 5
                        ) {{
                            continue;
                        }}

                        let ni = local_idx(u32(nx), u32(ny), u32(nz));

                        if (occ[ni] == 1u && visited[ni] == 0u) {{
                            visited[ni] = 1u;
                            stack[sp] = ni;
                            sp = sp + 1u;
                        }}
                    }}
                }}
            }}
        }}
    }}

    textureStore(ret_tex, coord, vec4<u32>(255u, 0u, 0u, 0u));
}}
"""



class wgpuRemoveStricture:
    def __init__(self):
        self.adapter = wgpu.gpu.request_adapter_sync(
            power_preference="high-performance"
        )

        self.device = self.adapter.request_device_sync()

        self.shader = self.device.create_shader_module(
            code=shaderCode
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
            ]
        )

        self.pipelineLayout = self.device.create_pipeline_layout(
            bind_group_layouts=[self.bindGroupLayout]
        )

        self.pipelineFilterCompose = self.device.create_compute_pipeline(
            layout=self.pipelineLayout,
            compute={
                "module": self.shader,
                "entry_point": "pass_filter_and_compose",
            },
        )

        self.maxGroupsPerDim = self.device.limits[
            "max-compute-workgroups-per-dimension"
        ]

    def process(self, maskNp: np.ndarray) -> np.ndarray:
        assert maskNp.ndim == 3

        width, height, depth = maskNp.shape

        dispatchX = math.ceil(width / WORKGROUP_SIZE_X)
        dispatchY = math.ceil(height / WORKGROUP_SIZE_Y)
        dispatchZ = math.ceil(depth / WORKGROUP_SIZE_Z)

        if (
            dispatchX > self.maxGroupsPerDim or
            dispatchY > self.maxGroupsPerDim or
            dispatchZ > self.maxGroupsPerDim
        ):
            raise RuntimeError(
                f"Dispatch too large: "
                f"({dispatchX}, {dispatchY}, {dispatchZ})"
            )

        bytesPerPixel = 4

        inputRawBytesPerRow = width * bytesPerPixel
        inputAlignedBytesPerRow = align_to(inputRawBytesPerRow, 256)
        inputPaddedWidth = inputAlignedBytesPerRow // bytesPerPixel

        outputRawBytesPerRow = width * bytesPerPixel
        outputAlignedBytesPerRow = align_to(outputRawBytesPerRow, 256)
        outputPaddedWidth = outputAlignedBytesPerRow // bytesPerPixel
        outputBufferSize = depth * height * outputAlignedBytesPerRow

        inputU32 = maskNp.astype(np.uint32, copy=False)

        inputZyx = np.transpose(inputU32, (2, 1, 0))

        inputPadded = np.zeros(
            (depth, height, inputPaddedWidth),
            dtype=np.uint32,
        )
        inputPadded[:, :, :width] = inputZyx

        del maskNp
        del inputZyx
        del inputU32
        gc.collect()

        maskTexture = self.device.create_texture(
            size=(width, height, depth),
            dimension=wgpu.TextureDimension.d3,
            format=wgpu.TextureFormat.r32uint,
            usage=(
                wgpu.TextureUsage.COPY_DST |
                wgpu.TextureUsage.TEXTURE_BINDING
            ),
        )
        retTexture = self.device.create_texture(
            size=(width, height, depth),
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

        bindGroup = self.device.create_bind_group(
            layout=self.bindGroupLayout,
            entries=[
                {
                    "binding": 0,
                    "resource": maskTexture.create_view(),
                },
                {
                    "binding": 1,
                    "resource": retTexture.create_view(),
                },
            ],
        )

        self.device.queue.write_texture(
            {
                "texture": maskTexture,
                "mip_level": 0,
                "origin": (0, 0, 0),
            },
            inputPadded,
            {
                "offset": 0,
                "bytes_per_row": inputAlignedBytesPerRow,
                "rows_per_image": height,
            },
            (width, height, depth),
        )
        
        del inputPadded
        gc.collect()

        encoder = self.device.create_command_encoder()
        computePass = encoder.begin_compute_pass()

        computePass.set_pipeline(self.pipelineFilterCompose)
        computePass.set_bind_group(0, bindGroup)
        computePass.dispatch_workgroups(
            dispatchX,
            dispatchY,
            dispatchZ,
        )

        computePass.end()

        encoder.copy_texture_to_buffer(
            {
                "texture": retTexture,
                "mip_level": 0,
                "origin": (0, 0, 0),
            },
            {
                "buffer": outputBuffer,
                "offset": 0,
                "bytes_per_row": outputAlignedBytesPerRow,
                "rows_per_image": height,
            },
            (width, height, depth),
        )

        self.device.queue.submit([encoder.finish()])
        self.device.queue.on_submitted_work_done_sync()

        outputBuffer.map_sync(
            wgpu.MapMode.READ,
            0,
            outputBufferSize,
        )

        outputData = outputBuffer.read_mapped(
            0,
            outputBufferSize,
        )

        outputNpPadded = np.frombuffer(
            outputData,
            dtype=np.uint32,
        ).reshape(depth, height, outputPaddedWidth)

        outputNpPadded = outputNpPadded.copy()

        outputBuffer.unmap()

        outputZyx = outputNpPadded[:, :, :width]
        outputXyz = np.transpose(outputZyx, (2, 1, 0))

        retNp = outputXyz.astype(np.uint8)
        
        del outputNpPadded
        del outputZyx
        del outputXyz
        del bindGroup
        del maskTexture
        del retTexture
        del outputBuffer
        gc.collect()
        return retNp

#multiProcessTask.CMultiProcessTaskProgress
class CRemoveStricture() :
    def __init__(self) -> None:
        super().__init__()
        # input your code
        self.m_gpuRemoveStricture = wgpuRemoveStricture()
        self.m_inputOptionInfo = None 
        self.m_inputMaskPath = ""
        self.m_outputMaskPath = ""
    def clear(self) :
        # input your code
        self.m_inputMaskPath = ""
        self.m_outputMaskPath = ""
        self.m_inputOptionInfo = None
        super().clear()
    def process(self) :
        if self.InputOptionInfo is None :
            print("stricture : not setting input option info")
            return 
        if self.InputMaskPath == "" :
            print("stricture : not setting input mask path")
            return 
        if self.OutputMaskPath == "" :
            print("stricture : not setting output mask path")
            return 
        
        listParam = []
        paramCnt = 0
        iStrictureCnt = self.InputOptionInfo.get_stricture_count()
        for iInx in range(0, iStrictureCnt) :
            inMask, outMask = self.InputOptionInfo.get_stricture(iInx)
            inputMaskFullPath = os.path.join(self.InputMaskPath, f"{inMask}.nii.gz")
            outputMaskFullPath = os.path.join(self.OutputMaskPath, f"{outMask}.nii.gz")

            if os.path.exists(inputMaskFullPath) == False :
                continue

            listParam.append((paramCnt, inputMaskFullPath, outputMaskFullPath))
            paramCnt += 1
        
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
                        progress_callback(percent, f"Remove Stricture...")
                    except TypeError:
                        progress_callback(percent)

                if is_interrupted and is_interrupted():
                    print("!!!!!!!!!!!!!!!!!!!!!!!!!!", file=sys.__stdout__, flush=True)
                    return False
    # param (inx, inputMaskFullPath, outputMaskFullPath)
    def _task(self, param : tuple) :
        inx = param[0]
        inputMaskFullPath = param[1]
        outputMaskFullPath = param[2]

        npImg, origin, spacing, direction, size = algImage.CAlgImage.get_np_from_nifti(inputMaskFullPath)
        npImg = self.m_gpuRemoveStricture.process(npImg)
        
        algImage.CAlgImage.save_nifti_from_np(outputMaskFullPath, npImg, origin, spacing, direction, (2, 1, 0))
        del npImg

    @property
    def InputOptionInfo(self) -> optionInfo.COptionInfo :
        return self.m_inputNiftiContainer
    @InputOptionInfo.setter
    def InputOptionInfo(self, inputNiftiContainer : optionInfo.COptionInfo) :
        self.m_inputNiftiContainer = inputNiftiContainer
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

