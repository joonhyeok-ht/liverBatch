import os
import sys

import bpy


def _get_argument(argumentName: str) -> str:
    if "--" not in sys.argv:
        raise ValueError("Blender script arguments were not provided.")

    scriptArguments = sys.argv[sys.argv.index("--") + 1:]
    if argumentName not in scriptArguments:
        raise ValueError(f"Missing argument: {argumentName}")
    argumentIndex = scriptArguments.index(argumentName)
    return scriptArguments[argumentIndex + 1]


def _export_selected_stl(outputStlPath: str):
    if bpy.app.version >= (4, 0, 0):
        bpy.ops.wm.stl_export(
            filepath=outputStlPath,
            export_selected_objects=True,
        )
    else:
        if not bpy.context.preferences.addons.get("io_mesh_stl"):
            bpy.ops.preferences.addon_enable(module="io_mesh_stl")
        bpy.ops.export_mesh.stl(
            filepath=outputStlPath,
            use_selection=True,
        )


def run():
    referenceStlPath = _get_argument("--reference-stl-path")
    outputPath = _get_argument("--output-path")
    os.makedirs(outputPath, exist_ok=True)

    meshNames = sorted(
        os.path.splitext(fileName)[0]
        for fileName in os.listdir(referenceStlPath)
        if fileName.lower().endswith(".stl")
    )

    exportedCount = 0
    for meshName in meshNames:
        meshObject = bpy.data.objects.get(meshName)
        if meshObject is None or meshObject.type != "MESH":
            print(f"Blender export: mesh not found: {meshName}")
            continue

        bpy.ops.object.select_all(action="DESELECT")
        meshObject.select_set(True)
        bpy.context.view_layer.objects.active = meshObject

        outputStlPath = os.path.join(outputPath, f"{meshName}.stl")
        if os.path.isfile(outputStlPath):
            os.remove(outputStlPath)
        _export_selected_stl(outputStlPath)
        print(f"Blender export: saved {outputStlPath}")
        exportedCount += 1

    print(f"Blender export: completed {exportedCount}/{len(meshNames)} meshes")


if __name__ == "__main__":
    run()
