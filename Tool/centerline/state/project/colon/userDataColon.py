import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import copy
import SimpleITK as sitk
from scipy.spatial import KDTree

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileStateProjectPath = os.path.dirname(fileAbsPath)
fileStatePath = os.path.dirname(fileStateProjectPath)
fileAppPath = os.path.dirname(fileStatePath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileStateProjectPath)
sys.path.append(fileStatePath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


from Algorithm import scoReg

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algVTK as algVTK
import AlgUtil.algGeometry as algGeometry

import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer

import data as data

import userData as userData

import command.commandExport as commandExport
import command.commandRecon as commandRecon
import command.objInfo as objInfo
import commandReconColon as commandReconColon

import VtkObj.vtkObjVertex as vtkObjVertex

import vtkObjInterface as vtkObjInterface


class CColonMergeInfo :
    def __init__(self) :
        self.m_origin = None
        self.m_spacing = None
        self.m_direction = None
        self.m_size = None
        self.m_phaseOffset = None
        self.m_reconParam = None
        self.m_clinfoInx = -1
        self.m_clinfo = None
        self.m_decimation = -1
        self.m_mergeBlenderName = ""
    def clear(self) :
        self.m_origin = None
        self.m_spacing = None
        self.m_direction = None
        self.m_size = None
        self.m_phaseOffset = None
        self.m_reconParam = None
        self.m_clinfoInx = -1
        self.m_clinfo = None
        self.m_decimation = -1
        self.m_mergeBlenderName = ""


    def set_clinfo(self, clinfoInx : int, clinfo : optionInfo.CCenterlineInfo) :
        self.m_clinfoInx = clinfoInx
        self.m_clinfo = clinfo
    def get_physical_mat(self) -> np.ndarray :
        return algVTK.CVTK.get_vtk_phy_matrix_with_spacing(self.Origin, self.Spacing, self.Direction, self.PhaseOffset)
    def translate_plane(self, plane : np.ndarray, voxelPt : np.ndarray) -> np.ndarray :
        phyMat = self.get_physical_mat()
        invPhyMat = algLinearMath.CScoMath.inv_mat4(phyMat)

        invRotMat = invPhyMat.copy()
        invRotMat[:3, 3] = 0.0

        normalTransMat = algLinearMath.CScoMath.inv_mat4(invRotMat)
        normalTransMat = normalTransMat.T

        n_phy = plane[:3]
        d_phy = plane[3]

        # voxel normal 계산
        n_vox = normalTransMat[:3, :3] @ n_phy
        n_vox /= np.linalg.norm(n_vox)

        # voxel offset(d) 계산
        d_vox = -np.dot(n_vox, voxelPt[0])

        # 최종 plane 반환
        return np.hstack([n_vox, d_vox])


    @property
    def Origin(self) :
        return self.m_origin
    @Origin.setter
    def Origin(self, origin) :
        self.m_origin = origin
    @property
    def Spacing(self) :
        return self.m_spacing
    @Spacing.setter
    def Spacing(self, spacing) :
        self.m_spacing = spacing
    @property
    def Direction(self) :
        return self.m_direction
    @Direction.setter
    def Direction(self, direction) :
        self.m_direction = direction
    @property
    def Size(self) :
        return self.m_size
    @Size.setter
    def Size(self, size) :
        self.m_size = size
    @property
    def PhaseOffset(self) -> np.ndarray :
        return self.m_phaseOffset
    @PhaseOffset.setter
    def PhaseOffset(self, phaseOffset : np.ndarray) :
        self.m_phaseOffset = phaseOffset
    @property
    def ReconParam(self) -> optionInfo.CReconParam :
        return self.m_reconParam
    @ReconParam.setter
    def ReconParam(self, reconParam : optionInfo.CReconParam) :
        self.m_reconParam = reconParam
    @property
    def ClinfoInx(self) -> int :
        return self.m_clinfoInx
    @property
    def Clinfo(self) -> optionInfo.CCenterlineInfo :
        return self.m_clinfo
    @property
    def Decimation(self) -> int :
        return self.m_decimation
    @Decimation.setter
    def Decimation(self, decimation : int) :
        self.m_decimation = decimation
    @property
    def MergeBlenderName(self) -> str :
        return self.m_mergeBlenderName
    @MergeBlenderName.setter
    def MergeBlenderName(self, mergeBlenderName : str) :
        self.m_mergeBlenderName = mergeBlenderName

class CColonMergeInfoRes :
    def __init__(
            self,
            npImg : np.ndarray, colonKey : str, clinfoInx : int
            ) :
        self.m_npImg = npImg
        self.m_npVertex = algImage.CAlgImage.get_vertex_from_np(self.m_npImg, np.int32)
        self.m_colonKey = colonKey
        self.m_clinfoInx = clinfoInx

        self.m_npPhyVertex = None
        self.m_colonMaskKey = ""

        # self.m_kdTree = None
    def clear(self) :
        self.m_npImg = None
        self.m_npVertex = None
        self.m_colonKey = ""
        self.m_clinfoInx = -1

        self.m_npPhyVertex = None
        self.m_colonMaskKey = ""

        # self.m_kdTree = None

    
    def set_mask_info(self, npPhyVertex : np.ndarray, colonMaskKey : str) :
        self.m_npPhyVertex = npPhyVertex
        self.m_colonMaskKey = colonMaskKey
        # self.m_kdTree = KDTree(self.m_npPhyVertex)
    def find_phy_inside_index(self, pt : np.ndarray, radius : float) -> list :
        '''
        desc 
            - pt를 기준으로 radius 반경 이내에 physical vertex들의 인덱스를 리턴
            - pt는 반드시 npPhyVertex와 같은 좌표계여야만 한다. 
        '''
        pt = pt.reshape(-1)
        indices = self.m_kdTree.query_ball_point(pt, r=radius)
        if len(indices) > 0 :
            return indices
        else :
            return None


    
    @property
    def Img(self) -> np.ndarray :
        return self.m_npImg
    @property
    def Vertex(self) -> np.ndarray :
        return self.m_npVertex
    @property
    def PhyVertex(self) -> np.ndarray :
        return self.m_npPhyVertex
    @property
    def ColonKey(self) -> str :
        return self.m_colonKey
    @property
    def ColonMaskKey(self) -> str :
        return self.m_colonMaskKey
    @property
    def CLInfoInx(self) -> int :
        return self.m_clinfoInx


class CUserDataColon(userData.CUserData) :
    s_userDataKey = "Colon"

    '''
    groupID 0 --> ct colon
    groupID 1 --> mr colon
    '''
    s_colonType = "MergeColon"
    s_colonMaskType = "MergeMask"
    s_colonDummy = "Colon_Dummy_Test_Ver3.obj"


    def __init__(self, data : data.CData, mediator):
        super().__init__(data, CUserDataColon.s_userDataKey)
        # input your code
        self.m_mediator = mediator
        self.m_colonMergeInfo = CColonMergeInfo()
        self.m_listColonMergeInfoRes = []
        self.m_mergeCLInfoInx = -1
        self.m_dummyObjInfo = None
    def clear(self) :
        # input your code
        self.m_mediator = None
        self.m_colonMergeInfo.clear()
        for colonMergeInfoRes in self.m_listColonMergeInfoRes :
            colonMergeInfoRes.clear()
        self.m_listColonMergeInfoRes.clear()
        self.m_mergeCLInfoInx = -1

        if self.m_dummyObjInfo is not None :
            self.m_dummyObjInfo.clear()
        self.m_dummyObjInfo = None

        super().clear()

    def load_patient(self) -> bool :
        if super().load_patient() == False :
            return False
        # input your code
        self._init_merge()
        
        return True
    

    # override
    def override_recon(self, patientID : str, outputPath : str) :
        cmd = commandReconColon.CCommandReconDevelopColon(self.m_mediator)
        cmd.InputData = self.Data
        cmd.InputPatientID = patientID
        cmd.InputBlenderScritpPath = self.get_res_path()
        cmd.InputBlenderScritpFileName = "blenderScriptRecon"
        cmd.InputSaveBlenderName = f"{patientID}_recon"
        cmd.OutputPath = outputPath
        cmd.process()
    def override_clean(self, patientID : str, outputPath : str) :
        blenderScritpFileName = "blenderScriptClean"
        saveBlenderName = f"{patientID}"

        outputPatientPath = os.path.join(outputPath, patientID)
        saveBlenderFullPath = os.path.join(outputPatientPath, f"{saveBlenderName}.blend")
        srcBlenderFullPath = os.path.join(outputPatientPath, f"{patientID}_recon.blend")

        if os.path.exists(srcBlenderFullPath) == False :
            print("not found recon blender file")
            return

        # 기존것은 지움
        if os.path.exists(saveBlenderFullPath) == True :
            os.remove(saveBlenderFullPath)
        # 새롭게 생성 
        shutil.copy(srcBlenderFullPath, saveBlenderFullPath)

        cmd = commandReconColon.CCommandReconDevelopCleanColon(self.m_mediator)
        cmd.InputData = self.Data
        cmd.InputPatientID = patientID
        cmd.InputBlenderScritpPath = self.get_res_path()
        cmd.InputBlenderScritpFileName = blenderScritpFileName
        cmd.InputSaveBlenderName = saveBlenderName
        cmd.OutputPath = outputPath
        cmd.process()
    def resampling_mask(self, patientID : str, outputPath : str) :
        cmd = commandReconColon.CCommandReconDevelopColon(self.m_mediator)
        cmd.InputData = self.Data
        cmd.InputPatientID = patientID
        cmd.OutputPath = outputPath
        cmd.process_resampling()
    

    def get_merge_path(self) -> str :
        dataInst = self.Data
        patientPath = dataInst.DataInfo.PatientPath
        clPath = os.path.join(patientPath, "MergeInfo")
        return clPath
    def get_merge_in_path(self) -> str :
        clInPath = os.path.join(self.get_merge_path(), "in")
        return clInPath
    def get_merge_out_path(self) -> str :
        clOutPath = os.path.join(self.get_merge_path(), "out")
        return clOutPath
    def get_res_path(self) -> str :
        dataInst = self.Data
        resPath = os.path.dirname(dataInst.DataInfo.OptionFullPath)
        resPath = os.path.join(resPath, "Res")
        resPath = os.path.join(resPath, "colon")
        return resPath

    def get_mergeinfo(self) -> CColonMergeInfo :
        return self.m_colonMergeInfo
    def get_mergeinfo_res_count(self) -> int :
        return len(self.m_listColonMergeInfoRes)
    def get_mergeinfo_res(self, inx : int) -> CColonMergeInfoRes :
        return self.m_listColonMergeInfoRes[inx]


    # protected
    def _init_merge(self) :
        optionInfoInst = self.Data.OptionInfo
        if "ColonMergeInfo" not in optionInfoInst.JsonData :
            print("failed merge colon : not found colon merge info")
            return
        maskPath = os.path.join(self.Data.DataInfo.PatientPath, "Mask")
        if os.path.exists(maskPath) == False :
            print("failed merge colon : not found copied mask path")
            return
        
        self.__export_merge()
        self.__init_merge_ct_colon()
        self.__init_merge_mr_colon()
        self.__init_centerline()
        self.__init_dummy()

    

    # private
    def __find_resampled_out_name(self, name : str) -> str :
        '''
        ret : "", option에 정의되지 않음 
        '''
        optionInfoInst = self.Data.OptionInfo
        if "ResamplingInfo" not in optionInfoInst.JsonData :
            return ""
        
        resamplingInfo = optionInfoInst.JsonData["ResamplingInfo"]
        for inst in resamplingInfo :
            maskName = inst["name"]
            if maskName == name :
                outMaskName = inst["outName"]
                return outMaskName
        return ""
    def __get_ct_colon_mask_name(self) -> str :
        optionInfoInst = self.Data.OptionInfo
        colonMergeInfo = optionInfoInst.JsonData["ColonMergeInfo"]
        ctColonName = colonMergeInfo["CTColonName"]
        return ctColonName
    def __get_mr_colon_mask_name(self) -> str :
        '''
        desc : resampling 된 rectum mask를 얻어온다. 
        ret : "", resampling된 mask name이 option에 정의되지 않음 
        '''
        optionInfoInst = self.Data.OptionInfo
        colonMergeInfo = optionInfoInst.JsonData["ColonMergeInfo"]
        mrColonName = colonMergeInfo["MRColonName"]
        return mrColonName
    def __get_merge_colon_blender_name(self) -> str :
        optionInfoInst = self.Data.OptionInfo
        colonMergeInfo = optionInfoInst.JsonData["ColonMergeInfo"]
        mergeBlenderName = colonMergeInfo["MergeBlenderName"]
        return mergeBlenderName
    def __get_blender_name(self, name : str) -> str :
        '''
        ret : "", 해당 name이 option에 정의되지 않음
        '''
        optionInfoInst = self.Data.OptionInfo

        maskInfo = optionInfoInst.find_maskinfo_list_by_name(name)
        if maskInfo is None :
            return ""
        maskInfo = maskInfo[0]
        return maskInfo.BlenderName
    def __get_phase_offset(self, name : str) -> np.ndarray :
        '''
        name : mask name
        ret : None , name에 해당하는 phase가 존재하지 않거나 해당 name이 없음
        '''
        optionInfoInst = self.Data.OptionInfo

        maskInfo = optionInfoInst.find_maskinfo_list_by_name(name)
        if maskInfo is None :
            return None
        maskInfo = maskInfo[0]

        reconType = maskInfo.ReconType
        phase = maskInfo.Phase
        phaseInfo = self.Data.PhaseInfoContainer.find_phaseinfo(phase)
        if phaseInfo is None :
            return None
        
        return phaseInfo.Offset
    def __find_recon_param(self, name : str) -> optionInfo.CReconParam :
        optionInfoInst = self.Data.OptionInfo

        maskInfo = optionInfoInst.find_maskinfo_list_by_name(name)
        if maskInfo is None :
            return None
        
        maskInfo = maskInfo[0]
        return optionInfoInst.find_recon_param(maskInfo.ReconType)
    def __find_centerlineinfo(self, name : str) -> tuple :
        '''
        name : mask name
        ret : (clinfoInx, clinfoInst)
              None -> name에 해당되는 clinfo를 찾을 수 없음 
        '''
        optionInfoInst = self.Data.OptionInfo
        blenderName = self.__get_blender_name(name)
        if blenderName == "" :
            return None

        iCnt = optionInfoInst.get_centerlineinfo_count()
        for inx in range(0, iCnt) :
            clinfo = optionInfoInst.get_centerlineinfo(inx)
            if blenderName == clinfo.get_input_blender_name() :
                return (inx, clinfo)
        return None
    def __get_colon_decimation(self, blenderName : str) -> int :
        '''
        ret : "", option에 정의되지 않음 
        '''
        optionInfoInst = self.Data.OptionInfo
        if "Blender" not in optionInfoInst.JsonData :
            return -1
        if "Decimation" not in optionInfoInst.JsonData["Blender"] :
            return -1
        dicDecimation = optionInfoInst.JsonData["Blender"]["Decimation"]

        for name, triCnt in dicDecimation.items() :
            if name == blenderName :
                return triCnt
        return -1
    def __export_merge(self) :
        patientID = self.Data.DataInfo.PatientID
        outputPatientPath = self.Data.DataInfo.PatientPath
        patientBlenderFullPath = os.path.join(outputPatientPath, f"{patientID}_recon.blend")
        mergeInPath = self.get_merge_in_path()

        if os.path.exists(mergeInPath) == False :
            os.makedirs(mergeInPath)
            os.makedirs(self.get_merge_out_path())

        ctColonName = self.__get_ct_colon_mask_name()
        mrColonName = self.__get_mr_colon_mask_name()
        ctColonBlenderName = self.__get_blender_name(ctColonName)
        mrColonBlenderName = self.__get_blender_name(mrColonName)

        if ctColonBlenderName == "" or mrColonBlenderName == "" :
            print("export merge error : not found blender name")
            return

        commandExportInst = commandExport.CCommandExportList(self.m_mediator)
        commandExportInst.InputData = self.Data
        commandExportInst.OutputPath = mergeInPath
        commandExportInst.PatientBlenderFullPath = patientBlenderFullPath
        commandExportInst.add_blender_name(ctColonBlenderName)
        commandExportInst.add_blender_name(mrColonBlenderName)
        commandExportInst.process()
        commandExportInst.clear()
    def __init_merge_ct_colon(self) :
        optionInfoInst = self.Data.OptionInfo
        maskPath = os.path.join(self.Data.DataInfo.PatientPath, "Mask")

        ctColonName = self.__get_ct_colon_mask_name()
        if ctColonName == "" :
            print("failed merge ct colon : not found ct colon name")
            return
        ctMaskFullPath = os.path.join(maskPath, f"{ctColonName}.nii.gz")
        if os.path.exists(ctMaskFullPath) == False :
            print(f"failed merge ct colon : not found {ctColonName}.nii.gz")
            return
        blenderName = self.__get_blender_name(ctColonName)
        if blenderName == "" :
            print(f"failed merge ct colon : not found {blenderName} of {ctColonName}")
            return

        mergeInPath = self.get_merge_in_path()
        
        npImg, origin, spacing, direction, size = algImage.CAlgImage.get_np_from_nifti(ctMaskFullPath)

        phaseOffset = self.__get_phase_offset(ctColonName)
        if phaseOffset is None :
            print(f"failed merge ct colon : not found phase offset")
            return
    
        reconParam = self.__find_recon_param(ctColonName)
        if reconParam is None :
            print(f"failed merge ct colon : not found recon param")
            return
        
        ret = self.__find_centerlineinfo(ctColonName) 
        if ret is None :
            print(f"failed merge ct colon : not found clinfo")
            return
        
        
        stlFullPath = os.path.join(mergeInPath, f"{blenderName}.stl")
        if os.path.exists(stlFullPath) == False :
            print(f"failed merge ct colon : not found {blenderName}.stl")
            return
        polydata = algVTK.CVTK.load_poly_data_stl(stlFullPath)
        colonKey = data.CData.make_key(CUserDataColon.s_colonType, 0, 0)
        obj = vtkObjInterface.CVTKObjInterface()
        obj.KeyType = CUserDataColon.s_colonType
        obj.Key = colonKey
        obj.Color = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 1.0])
        obj.Opacity = 0.2
        obj.PolyData = polydata
        self.Data.add_vtk_obj(obj)

        decimation = self.__get_colon_decimation(blenderName)
        mergeBlenderName = self.__get_merge_colon_blender_name()

        self.m_colonMergeInfo.Origin = origin
        self.m_colonMergeInfo.Spacing = spacing
        self.m_colonMergeInfo.Direction = direction
        self.m_colonMergeInfo.Size = size
        self.m_colonMergeInfo.PhaseOffset = phaseOffset
        self.m_colonMergeInfo.ReconParam = reconParam
        self.m_colonMergeInfo.Decimation = decimation
        self.m_colonMergeInfo.MergeBlenderName = mergeBlenderName
        self.m_colonMergeInfo.set_clinfo(ret[0], ret[1])
        
        res = CColonMergeInfoRes(npImg, colonKey, ret[0])

        mat = self.m_colonMergeInfo.get_physical_mat()
        vertex = algLinearMath.CScoMath.mul_mat4_vec3(mat, res.Vertex)
        obj = vtkObjVertex.CVTKObjVertex(vertex)
        obj.Key = data.CData.make_key(CUserDataColon.s_colonMaskType, 0, 0)
        obj.KeyType = CUserDataColon.s_colonMaskType
        obj.Color = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 1.0])
        self.Data.add_vtk_obj(obj)
        res.set_mask_info(vertex, obj.Key)

        self.m_listColonMergeInfoRes.append(res)
    def __init_merge_mr_colon(self) :
        optionInfoInst = self.Data.OptionInfo
        maskPath = os.path.join(self.Data.DataInfo.PatientPath, "Mask")

        mrColonName = self.__get_mr_colon_mask_name()
        if mrColonName == "" :
            print("failed merge mr colon : not found mr colon name")
            return
        mrResampledColonName = self.__find_resampled_out_name(mrColonName)
        if mrResampledColonName == "" :
            print("failed merge mr colon : not found resampled mr colon name")
            return
        mrMaskFullPath = os.path.join(maskPath, f"{mrResampledColonName}.nii.gz")
        if os.path.exists(mrMaskFullPath) == False :
            print(f"failed merge mr colon : not found {mrResampledColonName}.nii.gz")
            return
        blenderName = self.__get_blender_name(mrColonName)
        if blenderName == "" :
            print(f"failed merge mr colon : not found {blenderName} of {mrColonName}")
            return
        
        ret = self.__find_centerlineinfo(mrColonName) 
        if ret is None :
            print(f"failed merge mr colon : not found clinfo")
            return

        mergeInPath = self.get_merge_in_path()
        npImg, origin, spacing, direction, size = algImage.CAlgImage.get_np_from_nifti(mrMaskFullPath)

        stlFullPath = os.path.join(mergeInPath, f"{blenderName}.stl")
        if os.path.exists(stlFullPath) == False :
            print(f"failed merge ct colon : not found {blenderName}.stl")
            return
        polydata = algVTK.CVTK.load_poly_data_stl(stlFullPath)
        colonKey = data.CData.make_key(CUserDataColon.s_colonType, 1, 0)
        obj = vtkObjInterface.CVTKObjInterface()
        obj.KeyType = CUserDataColon.s_colonType
        obj.Key = colonKey
        obj.Color = algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0])
        obj.Opacity = 0.3
        obj.PolyData = polydata
        self.Data.add_vtk_obj(obj)

        res = CColonMergeInfoRes(npImg, colonKey, ret[0])

        mat = self.m_colonMergeInfo.get_physical_mat()
        vertex = algLinearMath.CScoMath.mul_mat4_vec3(mat, res.Vertex)
        obj = vtkObjVertex.CVTKObjVertex(vertex)
        obj.Key = data.CData.make_key(CUserDataColon.s_colonMaskType, 1, 0)
        obj.KeyType = CUserDataColon.s_colonMaskType
        obj.Color = algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0])
        self.Data.add_vtk_obj(obj)
        res.set_mask_info(vertex, obj.Key)

        self.m_listColonMergeInfoRes.append(res)
    def __init_centerline(self) :
        dataInst = self.Data
        optionInfoInst = self.Data.OptionInfo
        self.m_mergeCLInfoInx = optionInfoInst.get_centerlineinfo_count()
        iCLCnt = self.m_mergeCLInfoInx

        file = "clDataInfo.pkl"
        clInPath = dataInst.get_cl_in_path()
        clOutPath = dataInst.get_cl_out_path()
        pklFullPath = os.path.join(clInPath, file)
        if os.path.exists(pklFullPath) == False :
            return

        dataInfo = data.CData.load_inst(pklFullPath)
        if iCLCnt >= dataInfo.get_info_count() :
            return
        
        clInfo = dataInfo.get_clinfo(iCLCnt)
        clParam = dataInfo.get_clparam(iCLCnt)
        reconParam = dataInfo.get_reconparam(iCLCnt)

        dataInst.DataInfo.add_info(clInfo, clParam, reconParam)
        dataInst.attach_skeleton()

        self.m_mediator.load_vessel_key(iCLCnt, 0)

        clOutput = clInfo.OutputName
        clOutputFullPath = os.path.join(clOutPath, f"{clOutput}.json")
        if os.path.exists(clOutputFullPath) == False :
            return
        
        dataInst.set_skeleton(iCLCnt, clOutputFullPath)
        self.m_mediator.load_cl_key(iCLCnt)
        self.m_mediator.load_br_key(iCLCnt)
        self.m_mediator.load_ep_key(iCLCnt)
    def __init_dummy(self) :
        dummyPath = self.get_res_path()
        dummyFullPathPath = os.path.join(dummyPath, CUserDataColon.s_colonDummy)
        
        self.m_dummyObjInfo = objInfo.CObjInfo()
        if self.m_dummyObjInfo.load(dummyFullPathPath) == False :
            self.m_dummyObjInfo = None
    

    @property
    def Data(self) -> data.CData :
        return self.m_data
    @property
    def MergeCLInfoInx(self) -> int : 
        return self.m_mergeCLInfoInx
    @property
    def DummyObjInfo(self) -> objInfo.CObjInfo :
        return self.m_dummyObjInfo




if __name__ == '__main__' :
    pass


# print ("ok ..")

