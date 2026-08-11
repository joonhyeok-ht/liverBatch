import sys
import os
import csv
import vtk
import subprocess

import command.commandExtractionCL as commandExtractionCL

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAppPath = os.path.dirname(fileAbsPath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import state.project.liver.userDataLiver as userDataLiver

import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
from vtkmodules.util import numpy_support

# import AlgUtil.algImage as algImage

# import Block.optionInfo as optionInfo
# import Block.niftiContainer as niftiContainer
# import Block.reconstruction as reconstruction

# import VtkObj.vtkObj as vtkObj

# import command.commandInterface as commandInterface
import command.commandLoadingPatient as commandLoadingPatient
import command.commandExport as commandExport
# import command.commandExtractionCL as commandExtractionCL
# import command.commandRecon as commandRecon

import data as data
import shutil
# import operation as op

# sally
import state.project.liver.makeInputFolderLiver as makeInputFolder
# import subUtils.checkIntegrityStomach as checkIntegrity
# import subUtils.predictNavel as predictNavel
# import subUtils.generateSkinScreenshot as generateSkinScreenshot
import state.project.liver.subRecon.subReconLiver as reconLiver
# import liver.subDetectOverlap.subDetectOverlapLiver as detectOverlap
import Algorithm.scoUtil as scoUtil
from Algorithm.scoReg import CRegTransform
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer
import time
import command.commandExtractingCLLink as commandExtractingCLLink
import Block.makeInputFolder as makeInputFolder


def _load_phase_info(phaseInfoPath: str) -> niftiContainer.CPhase:
    if not os.path.isfile(phaseInfoPath):
        raise FileNotFoundError(f"phaseInfo.json not found: {phaseInfoPath}")

    phaseInfoLoader = niftiContainer.CFileLoadPhaseInfo()
    phaseInfoLoader.InputPath = os.path.dirname(phaseInfoPath)
    phaseInfoLoader.InputFileName = os.path.splitext(os.path.basename(phaseInfoPath))[0]
    phaseInfoContainer = phaseInfoLoader.process()
    if phaseInfoContainer is None:
        raise RuntimeError(f"Failed to load phase information: {phaseInfoPath}")
    return phaseInfoContainer


def _get_recon_phase_map(optionInfoInst: optionInfo.COptionInfo) -> dict:
    reconPhaseMap = {}
    for reconIndex in range(optionInfoInst.get_recon_count()):
        for listIndex in range(optionInfoInst.get_recon_list_count(reconIndex)):
            _, blenderName, phase, _ = optionInfoInst.get_recon_list(reconIndex, listIndex)
            if blenderName == "":
                continue
            if blenderName in reconPhaseMap and reconPhaseMap[blenderName] != phase:
                raise ValueError(
                    f"STL '{blenderName}' is assigned to both "
                    f"'{reconPhaseMap[blenderName]}' and '{phase}'."
                )
            reconPhaseMap[blenderName] = phase
    return reconPhaseMap


def export_blender_meshes(
    blenderExe: str,
    blenderFullPath: str,
    referenceStlPath: str,
    outputPath: str,
) -> int:
    if not os.path.isfile(blenderFullPath):
        raise FileNotFoundError(f"Blender file not found: {blenderFullPath}")
    if not os.path.isdir(referenceStlPath):
        raise FileNotFoundError(f"Reference STL directory not found: {referenceStlPath}")

    referenceNames = sorted(
        os.path.splitext(fileName)[0]
        for fileName in os.listdir(referenceStlPath)
        if fileName.lower().endswith(".stl")
    )
    if not referenceNames:
        raise RuntimeError(f"No reference STL files found: {referenceStlPath}")

    os.makedirs(outputPath, exist_ok=True)
    for meshName in referenceNames:
        previousStlPath = os.path.join(outputPath, f"{meshName}.stl")
        if os.path.isfile(previousStlPath):
            os.remove(previousStlPath)

    exportScriptPath = os.path.join(fileAbsPath, "exportBlenderMeshes.py")
    command = [
        blenderExe,
        "-b",
        blenderFullPath,
        "--python",
        exportScriptPath,
        "--",
        "--reference-stl-path",
        referenceStlPath,
        "--output-path",
        outputPath,
    ]
    subprocess.run(command, check=True)

    exportedCount = sum(
        os.path.isfile(os.path.join(outputPath, f"{meshName}.stl"))
        for meshName in referenceNames
    )
    if exportedCount == 0:
        raise RuntimeError(f"Blender did not export any STL files to: {outputPath}")
    return exportedCount


def _find_blender_file(outTempPath: str, huID: str) -> str:
    candidatePaths = [
        os.path.join(outTempPath, f"{huID}.blend")
    ]
    for candidatePath in candidatePaths:
        if os.path.isfile(candidatePath):
            return candidatePath
    raise FileNotFoundError(f"Blender file not found: {candidatePaths}")


def _transform_poly_data(polyData: vtk.vtkPolyData, matrix) -> vtk.vtkPolyData:
    transform = vtk.vtkTransform()
    transform.SetMatrix(matrix.ravel().tolist())

    transformFilter = vtk.vtkTransformPolyDataFilter()
    transformFilter.SetInputData(polyData)
    transformFilter.SetTransform(transform)
    transformFilter.Update()

    transformedPolyData = vtk.vtkPolyData()
    transformedPolyData.DeepCopy(transformFilter.GetOutput())
    return transformedPolyData


def _inverse_transform_poly_data(polyData: vtk.vtkPolyData, phaseInfo) -> vtk.vtkPolyData:
    # Reconstruction applies: Flip * Offset * Origin * Direction.
    # STL viewers place vertices directly in NIfTI physical coordinates, so only
    # the graphics-specific Flip and phase Offset must be removed here.
    offsetMatrix = algLinearMath.CScoMath.translation_mat4(phaseInfo.Offset)
    flipMatrix = algLinearMath.CScoMath.scale_mat4(
        algLinearMath.CScoMath.to_vec3([1.0, -1.0, -1.0])
    )
    graphicsMatrix = algLinearMath.CScoMath.mul_mat4_mat4(flipMatrix, offsetMatrix)
    inverseGraphicsMatrix = algLinearMath.CScoMath.inv_mat4(graphicsMatrix)
    return _transform_poly_data(polyData, inverseGraphicsMatrix)


def _voxelize_poly_data_to_phase(polyData: vtk.vtkPolyData, phaseInfo):
    # vtkPolyDataToImageStencil rasterizes an axis-aligned image. Convert the
    # physical-coordinate STL back to the NIfTI reader's axis-aligned space;
    # Origin and Direction are restored in the NIfTI header when it is saved.
    physicalMatrix = algVTK.CVTK.get_phy_matrix_without_scale(
        phaseInfo.Origin,
        phaseInfo.Direction,
    )
    inversePhysicalMatrix = algLinearMath.CScoMath.inv_mat4(physicalMatrix)
    voxelizationPolyData = _transform_poly_data(polyData, inversePhysicalMatrix)

    imageSize = tuple(int(value) for value in phaseInfo.Size)
    if len(imageSize) != 3 or any(value <= 0 for value in imageSize):
        raise ValueError(f"Invalid NIfTI size for phase '{phaseInfo.Phase}': {phaseInfo.Size}")

    imageData = vtk.vtkImageData()
    imageData.SetDimensions(imageSize)
    imageData.SetOrigin(0.0, 0.0, 0.0)
    imageData.SetSpacing(phaseInfo.Spacing)
    imageData.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)
    imageData.GetPointData().GetScalars().Fill(255)

    polyToStencil = vtk.vtkPolyDataToImageStencil()
    polyToStencil.SetInputData(voxelizationPolyData)
    polyToStencil.SetOutputOrigin(imageData.GetOrigin())
    polyToStencil.SetOutputSpacing(imageData.GetSpacing())
    polyToStencil.SetOutputWholeExtent(imageData.GetExtent())
    polyToStencil.Update()

    imageStencil = vtk.vtkImageStencil()
    imageStencil.SetInputData(imageData)
    imageStencil.SetStencilData(polyToStencil.GetOutput())
    imageStencil.ReverseStencilOff()
    imageStencil.SetBackgroundValue(0)
    imageStencil.Update()

    voxelArray = numpy_support.vtk_to_numpy(
        imageStencil.GetOutput().GetPointData().GetScalars()
    )
    voxelArray = voxelArray.reshape((imageSize[2], imageSize[1], imageSize[0]))
    return voxelArray.transpose((2, 1, 0))


def inverse_transform_reconstructed_stls(
    reconstructedPath: str,
    inverseTransformePath: str,
    phaseInfoPath: str,
    optionPath: str,
) -> tuple:
    """Inverse-transform reconstructed STL files using their reconstruction phase."""
    if not os.path.isdir(reconstructedPath):
        raise FileNotFoundError(f"Reconstructed STL directory not found: {reconstructedPath}")
    if not os.path.isfile(optionPath):
        raise FileNotFoundError(f"Option file not found: {optionPath}")

    optionInfoInst = optionInfo.COptionInfo(optionPath)
    phaseInfoContainer = _load_phase_info(phaseInfoPath)
    reconPhaseMap = _get_recon_phase_map(optionInfoInst)
    os.makedirs(inverseTransformePath, exist_ok=True)

    inputStlNames = sorted(
        os.path.splitext(fileName)[0]
        for fileName in os.listdir(reconstructedPath)
        if fileName.lower().endswith(".stl")
    )
    transformedCount = 0
    skippedCount = 0
    for blenderName in inputStlNames:
        phase = reconPhaseMap.get(blenderName)
        if phase is None:
            print(f"inverse transform: skipped phase mapping not found: {blenderName}.stl")
            skippedCount += 1
            continue

        inputStlPath = os.path.join(reconstructedPath, f"{blenderName}.stl")

        phaseInfo = phaseInfoContainer.find_phaseinfo(phase)
        if phaseInfo is None or not phaseInfo.is_valid():
            print(f"inverse transform: skipped invalid phase '{phase}' for {blenderName}.stl")
            skippedCount += 1
            continue

        polyData = algVTK.CVTK.load_poly_data_stl(inputStlPath)
        if polyData is None or polyData.GetNumberOfPoints() == 0:
            print(f"inverse transform: skipped invalid STL: {inputStlPath}")
            skippedCount += 1
            continue

        transformedPolyData = _inverse_transform_poly_data(polyData, phaseInfo)
        outputStlPath = os.path.join(inverseTransformePath, f"{blenderName}.stl")
        algVTK.CVTK.save_poly_data_stl(outputStlPath, transformedPolyData)

        voxelArray = _voxelize_poly_data_to_phase(transformedPolyData, phaseInfo)
        outputNiftiPath = os.path.join(inverseTransformePath, f"{blenderName}.nii.gz")
        algImage.CAlgImage.save_nifti_from_np(
            outputNiftiPath,
            voxelArray,
            tuple(phaseInfo.Origin),
            tuple(phaseInfo.Spacing),
            tuple(phaseInfo.Direction),
            (2, 1, 0),
        )
        print(
            f"inverse transform: saved {outputStlPath} and {outputNiftiPath} "
            f"(phase={phase})"
        )
        transformedCount += 1

    return transformedCount, skippedCount


def transform_reconstructed_stls_to_phase(
    reconstructedPath: str,
    outputPath: str,
    phaseInfoPath: str,
    targetPhase: str = "PP",
) -> tuple:
    """Transform every reconstructed STL into the target phase's physical space."""
    if not os.path.isdir(reconstructedPath):
        raise FileNotFoundError(f"Reconstructed STL directory not found: {reconstructedPath}")

    phaseInfoContainer = _load_phase_info(phaseInfoPath)
    targetPhaseInfo = phaseInfoContainer.find_phaseinfo(targetPhase)
    if targetPhaseInfo is None or not targetPhaseInfo.is_valid():
        raise ValueError(f"Invalid target phase: {targetPhase}")

    os.makedirs(outputPath, exist_ok=True)
    targetSuffix = targetPhase.lower()
    transformedCount = 0
    skippedCount = 0

    inputStlNames = sorted(
        os.path.splitext(fileName)[0]
        for fileName in os.listdir(reconstructedPath)
        if fileName.lower().endswith(".stl")
    )
    for blenderName in inputStlNames:
        inputStlPath = os.path.join(reconstructedPath, f"{blenderName}.stl")
        polyData = algVTK.CVTK.load_poly_data_stl(inputStlPath)
        if polyData is None or polyData.GetNumberOfPoints() == 0:
            print(f"target phase transform: skipped invalid STL: {inputStlPath}")
            skippedCount += 1
            continue

        # Reconstructed meshes already share the registered graphics space.
        # Removing the target phase's Flip/Offset places every mesh in that
        # target NIfTI phase's physical coordinate system.
        transformedPolyData = _inverse_transform_poly_data(polyData, targetPhaseInfo)
        outputStlPath = os.path.join(
            outputPath,
            f"{blenderName}_{targetSuffix}.stl",
        )
        algVTK.CVTK.save_poly_data_stl(outputStlPath, transformedPolyData)
        print(
            f"target phase transform: saved {outputStlPath} "
            f"(target phase={targetPhase})"
        )
        transformedCount += 1

    return transformedCount, skippedCount



def find_closest_cell_id(a: vtk.vtkPolyData, b: vtk.vtkPolyData):
    """
    Returns:
        a_cell_id: a에서 b와 가장 가까운 cell id
        b_cell_id: 그때 b에서 가장 가까운 cell id
        dist2: 제곱거리 (world unit^2)
        closest_on_b: b 위의 최근접점 (x,y,z)
        query_point: a에서 사용한 cell center (x,y,z)
    """
    if a is None or b is None:
        raise ValueError("a/b is None")
    if a.GetNumberOfCells() == 0 or b.GetNumberOfCells() == 0:
        raise ValueError("a/b has no cells")

    # b에 대한 locator (cell 기반 최근접 탐색)
    locator = vtk.vtkStaticCellLocator()  # vtkCellLocator도 OK
    locator.SetDataSet(b)
    locator.BuildLocator()

    cell = vtk.vtkGenericCell()
    closest = [0.0, 0.0, 0.0]
    dist2 = vtk.mutable(0.0)
    sub_id = vtk.mutable(0)
    b_cell_id = vtk.mutable(0)

    min_dist2 = float("inf")
    best_a_cell_id = -1
    best_b_cell_id = -1
    best_closest_on_b = None
    best_query_point = None

    # a의 각 cell center를 query로 사용
    for cid in range(a.GetNumberOfCells()):
        a.GetCell(cid, cell)
        pts = cell.GetPoints()
        n = pts.GetNumberOfPoints()
        if n == 0:
            continue

        cx = cy = cz = 0.0
        for i in range(n):
            x, y, z = pts.GetPoint(i)
            cx += x; cy += y; cz += z
        query = (cx / n, cy / n, cz / n)

        locator.FindClosestPoint(query, closest, b_cell_id, sub_id, dist2)

        d2 = float(dist2)
        if d2 < min_dist2:
            min_dist2 = d2
            best_a_cell_id = cid
            best_b_cell_id = int(b_cell_id)
            best_closest_on_b = tuple(closest)
            best_query_point = query

    return best_a_cell_id

def _changed_input_path(inputPath) -> str:
    rootpath = ""
    huid = ""
    mkInputFold = makeInputFolder.CMakeInputFolder()
    mkInputFold.ZipPath = inputPath  # "D:\\jys\\StomachKidney_newfolder\\zippath"
    mkInputFold.FolderMode = mkInputFold.eMode_Liver
    result = mkInputFold.process()
    if result == True:
        rootpath = mkInputFold.get_data_root_path()
        huid = mkInputFold.PatientID
        print(f"Making Input Folder Done. RootPath={rootpath}")

    return rootpath, huid

def save_for_graphics(dataInst, skeleton, blenderPath):
    clOutPath = dataInst.get_cl_out_path()
    clInPath = dataInst.get_cl_in_path()
    #clInfo = dataInst.OptionInfo.get_centerlineinfo(dataInst.CLInfoIndex)

    blenderName = "Portal"
    outputFileName = "Portal"
    outputFullPath = os.path.join(clOutPath, f"Centerline_{outputFileName}.json")
    # if polydata != None and skeleton != None :
    if skeleton != None :
        editInst = commandExtractingCLLink.CCommandExtractingCLLink(blenderName, skeleton, clInPath, dataInst.DataInfo.PatientID)
        if editInst.init(outputFullPath, commandExtractingCLLink.CCommandExtractingCLLink.MODE_VESSEL) :
            editInst.process()
        print("save for graphics done!")
        shutil.move(outputFullPath, blenderPath)
    else :
        print(f"_on_btn_save_centerline_info_for_graphics() : skeleton is None!")
        
    
            


def _command_extraction_cl(skelInfoPath, stlPath , dataInst) :
    clOutPath = skelInfoPath + "/out"
    clInPath = skelInfoPath + "/in"
    portalPath = stlPath + "/Portal.stl"
    tpPath = stlPath + "/Tumor.stl"
    
    if os.path.exists(clInPath) == False :
        os.makedirs(clInPath)
    if os.path.exists(clOutPath) == False :
        os.makedirs(clOutPath)

        # vessel의 min-max 추출 및 정육면체 생성
    vesselPolyData = algVTK.CVTK.load_poly_data_stl(portalPath)
    TPPolyData = algVTK.CVTK.load_poly_data_stl(tpPath)
    vtpFullPath = os.path.join(clInPath, "Portal.vtp")
    algVTK.CVTK.save_poly_data_vtp(vtpFullPath, vesselPolyData)
    
    cmd = commandExtractionCL.CCommandExtractionCL(None)
    cmd.InputData = dataInst
    cmd.InputIndex = 0
    cmd.InputAdvancementRatio = 1.001
    cmd.InputCellID = find_closest_cell_id(vesselPolyData, TPPolyData)
    cmd.process()

    clOutput = "Portal"
    clOutputFullPath = os.path.join(clOutPath, f"{clOutput}.json")
    if os.path.exists(clOutputFullPath) == False :
        print(f"not found skelinfo : {clOutputFullPath}")
        return
    
    skeleton = algSkeletonGraph.CSkeleton()
    skeleton.load(clOutputFullPath)
    
    return skeleton

# def _resampling_task_worker(param: tuple):
#     inMaskFullPath = param[0]
#     outMaskFullPath = param[1]
#     srcPhaseInfo = param[2]
#     targetPhaseInfo = param[3]

#     targetOffset = targetPhaseInfo.Offset
#     srcOffset = srcPhaseInfo.Offset
#     targetTrans = algLinearMath.CScoMath.translation_mat4(targetOffset)
#     srcTrans = algLinearMath.CScoMath.translation_mat4(srcOffset)
#     srcTrans = algLinearMath.CScoMath.inv_mat4(srcTrans)
#     resamplingTrans = algLinearMath.CScoMath.mul_mat4_mat4(srcTrans, targetTrans)

#     npImgSrc, originSrc, scalingSrc, directionSrc, sizeSrc = algImage.CAlgImage.get_np_from_nifti(inMaskFullPath)
#     sitkSrc = algImage.CAlgImage.get_sitk_from_np(npImgSrc, originSrc, scalingSrc, directionSrc)
#     sitkSrcResampled = algImage.CAlgImage.resampling_sitkimg_with_mat(
#         sitkSrc, 
#         targetPhaseInfo.Origin, targetPhaseInfo.Spacing, targetPhaseInfo.Direction, targetPhaseInfo.Size, 
#         sitkSrc.GetPixelID(), sitk.sitkNearestNeighbor, 
#         resamplingTrans
#         )
    
#     npImgRet, originRet, scalingRet, directionRet, sizeRet = algImage.CAlgImage.get_np_from_sitk(sitkSrcResampled, np.uint8)
#     algImage.CAlgImage.save_nifti_from_np(outMaskFullPath, npImgRet, originRet, scalingRet, directionRet, (2, 1, 0))
#     print(f"completed resampling to phase {os.path.basename(outMaskFullPath)}", file=sys.__stdout__, flush=True)

def run():
    directory_path = "C:/Users/hutom/Desktop/jh_test/data/liver/dpversion"
    option_path = os.path.abspath("./option.json")

    for item in ["LIVER0238"]:
        t0 = time.time()
        huID = item
        huID_path = os.path.join(directory_path, huID)

        if os.path.isdir(huID_path) and str(huID) != "__pycache__":
            outTempPath = os.path.join(huID_path, "OutTemp", huID)
            resultPath = os.path.join(outTempPath, "Result")
            blenderFullPath = _find_blender_file(outTempPath, huID)
            reconstructedPath = os.path.join(outTempPath, "BlenderResult")
            inverseTransformePath = os.path.join(outTempPath, "InverseTransformed")
            phaseInfoPath = os.path.join(outTempPath, "phaseInfo.json")

            optionInfoInst = optionInfo.COptionInfo(option_path)
            exportedCount = export_blender_meshes(
                optionInfoInst.BlenderExe,
                blenderFullPath,
                resultPath,
                reconstructedPath,
            )
            transformedCount, skippedCount = inverse_transform_reconstructed_stls(
                reconstructedPath,
                inverseTransformePath,
                phaseInfoPath,
                option_path,
            )
            # ppTransformedCount, ppSkippedCount = transform_reconstructed_stls_to_phase(
            #     reconstructedPath,
            #     inverseTransformePath,
            #     phaseInfoPath,
            #     "PP",
            #)
            elapsedTime = time.time() - t0
            # print(
            #     f"{huID}: Blender exported={exportedCount}, "
            #     f"inverse transformed={transformedCount}, "
            #     f"skipped={skippedCount}, "
            #     f"PP transformed={ppTransformedCount}, "
            #     f"PP skipped={ppSkippedCount}, elapsed={elapsedTime:.2f}s"
            # )
            

# print ("ok ..")



if __name__ == "__main__":
    run()
