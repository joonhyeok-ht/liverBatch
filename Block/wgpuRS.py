import math
import time
import sys
import numpy as np
import wgpu


WORKGROUP_SIZE_X = 8
WORKGROUP_SIZE_Y = 8
WORKGROUP_SIZE_Z = 4


def align_to(value, alignment):
    return ((value + alignment - 1) // alignment) * alignment


shaderCode = f"""
@group(0) @binding(0)
var mask_tex: texture_3d<u32>;

@group(0) @binding(1)
var dilated_tex: texture_storage_3d<r32uint, read_write>;

@group(0) @binding(2)
var ret_tex: texture_storage_3d<r32uint, write>;

fn local_idx(x: u32, y: u32, z: u32) -> u32 {{
    return x * 25u + y * 5u + z;
}}

@compute
@workgroup_size({WORKGROUP_SIZE_X}, {WORKGROUP_SIZE_Y}, {WORKGROUP_SIZE_Z})
fn pass1_dilation(@builtin(global_invocation_id) gid: vec3<u32>) {{
    let dims = textureDimensions(mask_tex);

    let x = gid.x;
    let y = gid.y;
    let z = gid.z;

    if (x >= dims.x || y >= dims.y || z >= dims.z) {{
        return;
    }}

    var found = false;

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
                    found = true;
                }}
            }}
        }}
    }}

    let coord = vec3<i32>(i32(x), i32(y), i32(z));

    if (found) {{
        textureStore(dilated_tex, coord, vec4<u32>(1u, 0u, 0u, 0u));
    }} else {{
        textureStore(dilated_tex, coord, vec4<u32>(0u, 0u, 0u, 0u));
    }}
}}

@compute
@workgroup_size({WORKGROUP_SIZE_X}, {WORKGROUP_SIZE_Y}, {WORKGROUP_SIZE_Z})
fn pass2_filter_and_compose(@builtin(global_invocation_id) gid: vec3<u32>) {{
    let dims = textureDimensions(mask_tex);

    let x = gid.x;
    let y = gid.y;
    let z = gid.z;

    if (x >= dims.x || y >= dims.y || z >= dims.z) {{
        return;
    }}

    let coord = vec3<i32>(i32(x), i32(y), i32(z));

    let maskV = textureLoad(mask_tex, coord, 0).r;
    let dilatedV = textureLoad(dilated_tex, coord).r;

    if (maskV > 0u) {{
        textureStore(ret_tex, coord, vec4<u32>(255u, 0u, 0u, 0u));
        return;
    }}

    if (dilatedV == 0u) {{
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
                        "access": wgpu.StorageTextureAccess.read_write,
                        "format": wgpu.TextureFormat.r32uint,
                        "view_dimension": wgpu.TextureViewDimension.d3,
                    },
                },
                {
                    "binding": 2,
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

        self.pipelineDilation = self.device.create_compute_pipeline(
            layout=self.pipelineLayout,
            compute={
                "module": self.shader,
                "entry_point": "pass1_dilation",
            },
        )

        self.pipelineFilterCompose = self.device.create_compute_pipeline(
            layout=self.pipelineLayout,
            compute={
                "module": self.shader,
                "entry_point": "pass2_filter_and_compose",
            },
        )

        self.maxGroupsPerDim = self.device.limits[
            "max-compute-workgroups-per-dimension"
        ]

        self.preparedShape = (0, 0, 0)

        self.width = None
        self.height = None
        self.depth = None

        self.alignedBytesPerRow = None
        self.paddedWidth = None
        self.outputBufferSize = None

        self.outputBuffer = None

        self.maskTexture = None
        self.dilatedTexture = None
        self.retTexture = None

        self.bindGroup = None

        self.cpuPaddedInput = None

    def _prepare_resources(self, width: int, height: int, depth: int):
        shape = (width, height, depth)

        if self.preparedShape == shape:
            return

        bytesPerPixel = 4

        rawBytesPerRow = width * bytesPerPixel
        alignedBytesPerRow = align_to(rawBytesPerRow, 256)
        paddedWidth = alignedBytesPerRow // bytesPerPixel

        outputBufferSize = depth * height * alignedBytesPerRow

        self.outputBuffer = self.device.create_buffer(
            size=outputBufferSize,
            usage=(
                wgpu.BufferUsage.COPY_DST |
                wgpu.BufferUsage.MAP_READ
            ),
        )

        self.maskTexture = self.device.create_texture(
            size=(width, height, depth),
            dimension=wgpu.TextureDimension.d3,
            format=wgpu.TextureFormat.r32uint,
            usage=(
                wgpu.TextureUsage.COPY_DST |
                wgpu.TextureUsage.TEXTURE_BINDING
            ),
        )

        self.dilatedTexture = self.device.create_texture(
            size=(width, height, depth),
            dimension=wgpu.TextureDimension.d3,
            format=wgpu.TextureFormat.r32uint,
            usage=(
                wgpu.TextureUsage.STORAGE_BINDING
            ),
        )

        self.retTexture = self.device.create_texture(
            size=(width, height, depth),
            dimension=wgpu.TextureDimension.d3,
            format=wgpu.TextureFormat.r32uint,
            usage=(
                wgpu.TextureUsage.STORAGE_BINDING |
                wgpu.TextureUsage.COPY_SRC
            ),
        )

        self.bindGroup = self.device.create_bind_group(
            layout=self.bindGroupLayout,
            entries=[
                {
                    "binding": 0,
                    "resource": self.maskTexture.create_view(),
                },
                {
                    "binding": 1,
                    "resource": self.dilatedTexture.create_view(),
                },
                {
                    "binding": 2,
                    "resource": self.retTexture.create_view(),
                },
            ],
        )

        self.cpuPaddedInput = np.empty(
            (depth, height, paddedWidth),
            dtype=np.uint32,
        )

        self.preparedShape = shape

        self.width = width
        self.height = height
        self.depth = depth

        self.alignedBytesPerRow = alignedBytesPerRow
        self.paddedWidth = paddedWidth
        self.outputBufferSize = outputBufferSize

    def process_np(self, maskNp: np.ndarray, bProfile: bool = True) -> np.ndarray:
        def tic():
            return time.perf_counter()

        def log(name, t0, t1):
            if bProfile:
                print(
                    f"[PROFILE] {name:<35}: {(t1 - t0) * 1000:.3f} ms",
                    file=sys.__stdout__,
                    flush=True,
                )

        tAll0 = tic()

        assert maskNp.ndim == 3

        t0 = tic()

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

        voxelCount = width * height * depth

        self._prepare_resources(width, height, depth)

        t1 = tic()
        log("shape / dispatch / prepare", t0, t1)

        if bProfile:
            print(f"[PROFILE] shape: {maskNp.shape}", file=sys.__stdout__, flush=True)
            print(f"[PROFILE] voxel_count: {voxelCount}", file=sys.__stdout__, flush=True)
            print(
                f"[PROFILE] dispatch: ({dispatchX}, {dispatchY}, {dispatchZ})",
                file=sys.__stdout__,
                flush=True,
            )

        t0 = tic()

        maskU32 = maskNp.astype(np.uint32, copy=False)

        inputZyx = np.transpose(maskU32, (2, 1, 0))

        self.cpuPaddedInput[:, :, :width] = inputZyx

        t1 = tic()
        log("CPU preprocess / padding", t0, t1)

        t0 = tic()

        self.device.queue.write_texture(
            {
                "texture": self.maskTexture,
                "mip_level": 0,
                "origin": (0, 0, 0),
            },
            self.cpuPaddedInput,
            {
                "offset": 0,
                "bytes_per_row": self.alignedBytesPerRow,
                "rows_per_image": height,
            },
            (width, height, depth),
        )

        encoder = self.device.create_command_encoder()

        computePass = encoder.begin_compute_pass()

        computePass.set_pipeline(self.pipelineDilation)
        computePass.set_bind_group(0, self.bindGroup)
        computePass.dispatch_workgroups(
            dispatchX,
            dispatchY,
            dispatchZ,
        )

        computePass.set_pipeline(self.pipelineFilterCompose)
        computePass.set_bind_group(0, self.bindGroup)
        computePass.dispatch_workgroups(
            dispatchX,
            dispatchY,
            dispatchZ,
        )

        computePass.end()

        encoder.copy_texture_to_buffer(
            {
                "texture": self.retTexture,
                "mip_level": 0,
                "origin": (0, 0, 0),
            },
            {
                "buffer": self.outputBuffer,
                "offset": 0,
                "bytes_per_row": self.alignedBytesPerRow,
                "rows_per_image": height,
            },
            (width, height, depth),
        )

        self.device.queue.submit([encoder.finish()])
        self.device.queue.on_submitted_work_done_sync()

        t1 = tic()
        log("write_texture / 2-pass / download", t0, t1)

        t0 = tic()

        self.outputBuffer.map_sync(
            wgpu.MapMode.READ,
            0,
            self.outputBufferSize,
        )

        outputData = self.outputBuffer.read_mapped(
            0,
            self.outputBufferSize,
        )

        outputNpPadded = np.frombuffer(
            outputData,
            dtype=np.uint32,
        ).reshape(depth, height, self.paddedWidth)

        outputNpPadded = outputNpPadded.copy()

        self.outputBuffer.unmap()

        outputZyx = outputNpPadded[:, :, :width]
        outputXyz = np.transpose(outputZyx, (2, 1, 0))

        retNp = outputXyz.astype(np.uint8)

        t1 = tic()
        log("readback / reshape / uint8", t0, t1)

        tAll1 = tic()
        log("TOTAL process_np", tAll0, tAll1)

        return retNp