import sys
import os
import csv
import vtk

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
import time
import command.commandExtractingCLLink as commandExtractingCLLink
import Block.makeInputFolder as makeInputFolder



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
    '''
    mask 정합, resample하여 저장하는 코드는 removestricture 끄고 non rigid registration (NRR) 켜서 NRR 코드에서 저장하도록 되어있음
    
    blender, centerline 만드는 코드는 removestructre 키고 non rigid 끄고 해야 됨 그리고 main 코드 아래 blender scipt 관련된 코드 주석 풀어야 함
    '''
    
    directory_path = "./test"
    option_path = "./option.json"
    #m_optionInfo = optionInfo.COptionInfoSingle(option_path)
    huID_set = set()


    
    for item in ["SCH"]:
        t0 = time.time()
        huID = item
        huID_path = os.path.join(directory_path, huID)
        
        rootpath = ""
        huid = ""
        
        mkInputFold = makeInputFolder.CMakeInputFolder()
        mkInputFold.ZipPath = huID_path  # "D:\\jys\\StomachKidney_newfolder\\zippath"
        m_data = data.CData()
        
        
        optionInfoInst = optionInfo.COptionInfo(option_path)
        m_data.OptionInfo = optionInfoInst
        m_data.UserData  = userDataLiver.CUserDataLiver(m_data, None)
        userdata = m_data.UserData
        userdata.set_patient_zippath(huID_path)
        
        result = mkInputFold.process()
        
        if os.path.isdir(huID_path) and str(huID) != "__pycache__":
            # huID_set.add(huID)
            m_outputPath = os.path.join(huID_path, "OutTemp")
            
            # temp_path = os.path.join(os.path.dirname(option_path), "tmp.json")
            # target_str = '"DataRootPath"'
            # new_data_root_path = root_path.replace("\\", "\\\\").replace("/", "\\\\")
            # m_optionInfo.m_dataRootPath = new_data_root_path
            # with open(option_path, "r", encoding="utf-8") as org_file, open(
            #     temp_path, "w", encoding="utf-8"
            # ) as temp_file:
            #     for line in org_file:
            #         # DataRootPath 부분 찾아서 새로운 패스로 바꿈
            #         if target_str in line:
            #             # line = line.replace(target_str, replacement_string)
            #             line = f'\t"DataRootPath" : "{new_data_root_path}",\n'
            #         temp_file.write(line)

            # os.replace(temp_path, option_path)
            
            # if os.path.exists(m_outputPath):
            #     pass
            # else:
            #     os.makedirs(m_outputPath)

            print(f"start recon {huID}")
            
            reconInst = reconLiver.CSubReconLiver() 
            reconInst.InputSliceID = 400
            reconInst.PatientID = huID
            reconInst.m_folderInfo = mkInputFold
            reconInst.InputData = m_data
            reconInst.IntermediateDataPath = m_outputPath

            success = reconInst.process()
            

# print ("ok ..")



if __name__ == "__main__":
    run()
