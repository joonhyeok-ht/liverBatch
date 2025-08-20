import sys
import os
import numpy as np
import shutil
import multiprocessing

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAlgorithmPath = os.path.join(fileAbsPath, "Algorithm") 
fileAlgUtilPath = os.path.join(fileAbsPath, "AlgUtil")
fileBlockPath = os.path.join(fileAbsPath, "Block")
sys.path.append(fileAbsPath)
sys.path.append(fileAlgorithmPath)
sys.path.append(fileAlgUtilPath)
sys.path.append(fileBlockPath)


import Block.centerline as centerline


# class CCommonPipelineCL() :
#     def __init__(self) -> None:
#         try:
#         # PyInstaller로 패키징된 실행 파일의 경우
#             self.fileAbsPath = sys._MEIPASS
#             self.fileAbsPath = "."
#         except AttributeError:
#             # 개발 환경에서
#             self.fileAbsPath = os.path.abspath(os.path.dirname(__file__))

#     # override
#     def init(self) :
#         jsonPath = os.path.join(self.fileAbsPath, "option.json")
#         self.m_optionInfo = optionInfo.COptionInfoSingle(jsonPath)
#     def process(self) :
#         if self.m_optionInfo.Ready == False :
#             print("not found option.json")
#             return
        
#         dataRootPath = self.m_optionInfo.DataRootPath

#         listPatientID = os.listdir(dataRootPath)
#         for patientID in listPatientID :
#             fullPath = os.path.join(dataRootPath, patientID)
#             if os.path.isdir(fullPath) == False :
#                 continue
#             if patientID == ".DS_Store" : 
#                 continue
#             self._patient_pipeline(patientID)
#     def clear(self) :
#         # input your code 
#         print("visited clear")


#     def _patient_pipeline(self, patientID : str) :
#         self.__pipeline(patientID)

        
#     # private
#     def __pipeline(self, patientID : str) :
#         passInst = self.m_optionInfo.find_pass(optionInfo.COptionInfo.s_processCLName)
#         if passInst is None :
#             print(f"not found pass : {optionInfo.COptionInfo.s_processCLName}")
#             return 
        
#         patientFullPath = os.path.join(self.m_optionInfo.DataRootPath, patientID)
#         maskFullPath = os.path.join(patientFullPath, "Mask")
#         outputDataRoot = os.path.join(self.fileAbsPath, os.path.basename(self.m_optionInfo.DataRootPath))
#         outputPatientFullPath = os.path.join(outputDataRoot, patientID)
#         phaseInfoFileName = "phaseInfo"
#         self.m_patientBlenderFullPath = os.path.join(outputPatientFullPath, optionInfo.COptionInfo.get_blender_name(passInst.In, patientID))

#         if os.path.exists(self.m_patientBlenderFullPath) == False :
#             print(f"not found blender file : {self.m_patientBlenderFullPath}")
#             return

#         niftiContainerBlock = niftiContainer.CNiftiContainerTerritory()
#         niftiContainerBlock.InputOptionInfo = self.m_optionInfo
#         niftiContainerBlock.InputPath = maskFullPath
#         niftiContainerBlock.process()

#         fileLoadPhaseInfoBlock = niftiContainer.CFileLoadPhaseInfo()
#         fileLoadPhaseInfoBlock.InputNiftiContainer = niftiContainerBlock
#         fileLoadPhaseInfoBlock.InputPath = outputPatientFullPath
#         fileLoadPhaseInfoBlock.InputFileName = phaseInfoFileName
#         fileLoadPhaseInfoBlock.process()

#         self.__init_cl(niftiContainerBlock, outputPatientFullPath)

#         iCLInfoCnt = self.m_optionInfo.get_centerlineinfo_count()
#         for i in range(0, iCLInfoCnt) :
#             centerlineBlock = centerline.CCenterline()
#             centerlineBlock.InputOptionInfo = self.m_optionInfo
#             centerlineBlock.InputNiftiContainer = niftiContainerBlock
#             centerlineBlock.InputCLInfoIndex = i
#             centerlineBlock.InputPath = self.m_clInPath
#             centerlineBlock.OutputPath = self.m_clOutPath
#             centerlineBlock.process()
#             centerlineBlock.clear()
        
#         self.__end_cl(passInst, outputDataRoot, outputPatientFullPath, patientID)
#         niftiContainerBlock.clear()

#     def __init_cl(
#             self, 
#             niftiContainerBlock : niftiContainer.CNiftiContainer,
#             outputPatientFullPath : str
#             ) :
#         # in : stl 파일
#         # out : json 파일 
#         self.m_clInPath = optionInfo.COptionInfo.pass_in_path(optionInfo.COptionInfo.s_processCLName)
#         self.m_clInPath = os.path.join(outputPatientFullPath, self.m_clInPath)
#         self.m_clOutPath = optionInfo.COptionInfo.pass_out_path(optionInfo.COptionInfo.s_processCLName)
#         self.m_clOutPath = os.path.join(outputPatientFullPath, self.m_clOutPath)

#         if os.path.exists(self.m_clInPath) == False :
#             os.makedirs(self.m_clInPath)
#         if os.path.exists(self.m_clOutPath) == False :
#             os.makedirs(self.m_clOutPath)

#         clCnt = self.m_optionInfo.get_centerlineinfo_count()
#         for iInx in range(0, clCnt) :
#             clInfo = self.m_optionInfo.get_centerlineinfo(iInx)
#             inputKey = clInfo.InputKey
#             if inputKey == "nifti" :
#                 self.__inputkey_nifti(niftiContainerBlock, clInfo)
#             elif inputKey == "blenderName" :
#                 self.__inputkey_blenderName(clInfo)
#             elif inputKey == "voxelize" :
#                 self.__inputkey_voxelize(niftiContainerBlock, clInfo)
#             else :
#                 print("invalide value cl inputKey")
#     def __end_cl(self, passInst : optionInfo.CPass, outputDataRoot : str, outputPatientFullPath : str, patientID : str) :
#         saveAs = optionInfo.COptionInfo.get_blender_name(optionInfo.COptionInfo.s_processCLName, patientID)
#         patientBlenderFullPath = os.path.join(outputPatientFullPath, saveAs)
        
#         shutil.copy(self.m_patientBlenderFullPath, patientBlenderFullPath)

#         # blender background 실행
#         stlPath = optionInfo.COptionInfo.pass_out_path(optionInfo.COptionInfo.s_processCLName)
#         option = ""
#         if passInst.TriOpt == 1 :
#             option += "--triOpt"
#         cmd = f"{self.m_optionInfo.BlenderExe} -b {patientBlenderFullPath} --python {os.path.join(self.fileAbsPath, 'blenderScriptCommonPipeline.py')} -- --patientID {patientID} --path {stlPath} --saveAs {saveAs} {option}"
#         os.system(cmd)

#     def __inputkey_nifti(
#             self, 
#             niftiContainerBlock : niftiContainer.CNiftiContainer,
#             clInfo : optionInfo.CCenterlineInfo
#             ) :
#         blenderName = clInfo.get_input_blender_name()
#         reconType = clInfo.get_input_recon_type()

#         niftiInfo = niftiContainerBlock.find_nifti_info_by_blender_name(blenderName)
#         if niftiInfo is None :
#             print(f"centerline : not found nifti info {blenderName}")
#             return None
        
#         niftiFullPath = niftiInfo.FullPath
#         if niftiInfo.Valid == False :
#             print(f"centerline : not found nifti of {blenderName}")
#             return None
        
#         phase = niftiInfo.MaskInfo.Phase
#         phaseInfo = niftiContainerBlock.find_phase_info(phase)
#         if phaseInfo is None :
#             print(f"centerline : not found phaseInfo {phase}")
#             return None
        
#         reconParam = self.m_optionInfo.find_recon_param(reconType)
#         if reconParam is None :
#             print(f"centerline : not found reconType {reconType}")
#             return None
#         contour = reconParam.Contour
#         algorithm = reconParam.Algorithm
#         param = reconParam.Param
#         gaussian = reconParam.Gaussian
#         resampling = reconParam.ResamplingFactor
        
#         polyData = reconstruction.CReconstruction.reconstruction_nifti(niftiFullPath, phaseInfo.Origin, phaseInfo.Spacing, phaseInfo.Direction, phaseInfo.Offset, contour, param, algorithm , gaussian, resampling)
#         polyVertex = algVTK.CVTK.poly_data_get_vertex(polyData)
#         polyIndex = algVTK.CVTK.poly_data_get_triangle_index(polyData)
#         polyData = algVTK.CVTK.create_poly_data_triangle(polyVertex, polyIndex)

#         outExportFullPath = os.path.join(self.m_clInPath, f"{blenderName}.stl")
#         algVTK.CVTK.save_poly_data_stl(outExportFullPath, polyData)
#     def __inputkey_blenderName(
#             self,
#             clInfo : optionInfo.CCenterlineInfo
#             ) :
#         # export -> load polydata 
#         blenderName = clInfo.get_input_blender_name()
#         tmpStr = f"'{blenderName}'"
#         outExportFullPath = os.path.join(self.m_clInPath, f"{blenderName}.stl")
#         scriptFullPath = os.path.join(self.m_clInPath, f"tmpScript.py")
#         self.__export_from_blender(scriptFullPath, tmpStr, self.m_clInPath)
#     def __inputkey_voxelize(
#             self,
#             niftiContainerBlock : niftiContainer.CNiftiContainer,
#             clInfo : optionInfo.CCenterlineInfo) :
#         self.__inputkey_blenderName(clInfo)
#         blenderName = clInfo.get_input_blender_name()
#         reconType = clInfo.get_input_recon_type()
#         exportedFullPath = os.path.join(self.m_clInPath, f"{blenderName}.stl")

#         if os.path.exists(exportedFullPath) == False :
#             print(f"centerline-voxelized : not found voxelized stl {blenderName}")
#             return None
#         polyData = algVTK.CVTK.load_poly_data_stl(exportedFullPath)

#         niftiInfo = niftiContainerBlock.find_nifti_info_by_blender_name(blenderName)
#         if niftiInfo is None :
#             print(f"centerline-voxelized : not found nifti info {blenderName}")
#             return None
        
#         phase = niftiInfo.MaskInfo.Phase
#         phaseInfo = niftiContainerBlock.find_phase_info(phase)
#         if phaseInfo is None :
#             print(f"centerline-voxelized : not found phaseInfo {phase}")
#             return None
        
#         npImg, origin, spacing, direction, size = algVTK.CVTK.poly_data_voxelize(polyData, phaseInfo.Spacing, 1.0)
#         npImg = npImg.astype(np.uint8)
#         npImg[npImg > 0] = 255

#         print(f"voxelize origin : {origin}")
#         print(f"voxelize spacing : {spacing}")
#         print(f"voxelize direction : {direction}")
#         print(f"voxelize size : {size}")

#         niftiFullPath = os.path.join(self.m_clInPath, f"{blenderName}.nii.gz")
#         algImage.CAlgImage.save_nifti_from_np(niftiFullPath, npImg, origin, spacing, direction, (2, 1, 0))

#         reconParam = self.m_optionInfo.find_recon_param(reconType)
#         if reconParam is None :
#             print(f"centerline : not found reconType {reconType}")
#             return None
#         contour = reconParam.Contour
#         algorithm = reconParam.Algorithm
#         param = reconParam.Param
#         gaussian = reconParam.Gaussian
#         resampling = reconParam.ResamplingFactor
#         offset = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0])
        
#         polyData = reconstruction.CReconstruction.reconstruction_nifti(niftiFullPath, origin, spacing, direction, offset, contour, param, algorithm , gaussian, resampling, bFlip=False)
#         polyVertex = algVTK.CVTK.poly_data_get_vertex(polyData)
#         polyIndex = algVTK.CVTK.poly_data_get_triangle_index(polyData)
#         polyData = algVTK.CVTK.create_poly_data_triangle(polyVertex, polyIndex)

#         # replace 
#         algVTK.CVTK.save_poly_data_stl(exportedFullPath, polyData)

#     def __export_from_blender(self, scriptFullPath : str, tmpStr : str, outExportPath : str) :
#         with open(scriptFullPath, 'w') as scriptFp:
#             scriptFp.write(f""" 
# import bpy
# import os
# listObjName = [{tmpStr}]
# outputPath = '{outExportPath}'
# for objName in listObjName :
#     if objName in bpy.data.objects:
#         bpy.ops.object.mode_set(mode='OBJECT')
#         bpy.ops.object.select_all(action='DESELECT')
#         bpy.data.objects[objName].select_set(True)
#         bpy.context.view_layer.objects.active = bpy.data.objects[objName]
#         bpy.ops.export_mesh.stl(filepath=os.path.join(outputPath, objName + '.stl'), use_selection=True)
#                 """)

#         cmd = f"{self.m_optionInfo.BlenderExe} -b {self.m_patientBlenderFullPath} --python {scriptFullPath}"
#         os.system(cmd)


def find_param(args : list, paramName : str) :
    try:
        inx = args.index(paramName)
        return args[inx + 1]
    except ValueError:
        print(f"not found param : {paramName}")
    return None
def exist_param(args : list, paramName : str) -> bool :
    try:
        inx = args.index(paramName)
        return True
    except ValueError:
        print(f"not found param : {paramName}")
    return False


import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Process input file and index.")
    parser.add_argument('--file', type=str, help='The file to process')
    parser.add_argument('--index', type=int, help='The index value')
    parser.add_argument('--cellID', type=int, help='start cellID')
    return parser.parse_args()


if __name__ == '__main__' :
    args = parse_args()

    if args.index is None :
        multiprocessing.freeze_support()
        # app = CCommonPipelineCL()
        # app.init()
        # app.process()
        # app.clear()
    else :
        print(f"파일: {args.file}")
        print(f"인덱스: {args.index}")
        print(f"cellID: {args.cellID} {type(args.cellID)}")

        clPkl = centerline.CCenterlineWithPklStartCellID()
        clPkl.InputPklFullPath = args.file
        clPkl.InputIndex = args.index
        clPkl.InputCellID = args.cellID

        clPkl.process()


print ("ok ..")

