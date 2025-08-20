import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import copy
import SimpleITK as sitk

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

import command.commandRecon as commandRecon


class CUserDataColon(userData.CUserData) :
    s_userDataKey = "Colon"
    s_colonCTName = "colon-0"
    s_colonMRName = "colon-MR"


    def __init__(self, data : data.CData, mediator):
        super().__init__(data, CUserDataColon.s_userDataKey)
        # input your code
        self.m_mediator = mediator
        self.m_mergeTargetInx = -1  # ct
        self.m_mergeSrcInx = -1     # mr
        self.m_mergeClinfoInx = -1

        # [(maskInfo, phaseInfo, reconParamSingle, npImg, sitkImg), .. ]
        self.m_listMergeInfo = []
    def clear(self) :
        # input your code
        self.m_mediator = None
        self.m_mergeTargetInx = -1  # ct
        self.m_mergeSrcInx = -1     # mr
        self.m_mergeClinfoInx = -1
        self.m_listMergeInfo.clear()
        super().clear()

    def load_patient(self) -> bool :
        if super().load_patient() == False :
            return False
        # input your code
        optionInfoInst = self.Data.OptionInfo
        iCnt = optionInfoInst.get_centerlineinfo_count()
        if iCnt == 0 :
            return

        self._init_merge()
        
        return True
    

    # override
    def override_recon(self, patientID : str, outputPath : str) :
        cmd = commandRecon.CCommandReconDevelopColon(self.m_mediator)
        cmd.InputData = self.Data
        cmd.InputPatientID = patientID
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

        cmd = commandRecon.CCommandReconDevelopClean(self.m_mediator)
        cmd.InputData = self.Data
        cmd.InputPatientID = patientID
        cmd.InputBlenderScritpFileName = blenderScritpFileName
        cmd.InputSaveBlenderName = saveBlenderName
        cmd.OutputPath = outputPath
        cmd.process()
    

    # protected
    def _init_merge(self) :
        optionInfoInst = self.Data.OptionInfo
        iCnt = optionInfoInst.get_centerlineinfo_count()
        self.m_mergeClinfoInx = iCnt

        # [(maskInfo, phaseInfo, reconParamSingle, npImg, sitkImg), .. ]
        for inx in range(0, iCnt) :
            clinfo = optionInfoInst.get_centerlineinfo(inx)
            blenderName = clinfo.get_input_blender_name()

            maskInfo = optionInfoInst.find_maskinfo_by_blender_name(blenderName)
            if maskInfo is None :
                print(f"not found maskInfo : {blenderName}")
                self.m_listMergeInfo.append((None, None, None, None, None))
                continue

            phase = maskInfo.Phase
            reconType = maskInfo.ReconType

            phaseInfo = self.Data.PhaseInfoContainer.find_phaseinfo(phase)
            reconParam = optionInfoInst.find_recon_param(reconType)

            maskFullPath = self.PatientMaskFullPath
            niftiFullPath = os.path.join(maskFullPath, f"{maskInfo.Name}.nii.gz")

            if os.path.exists(niftiFullPath) == False :
                print(f"not found nifti file : {maskInfo.Name}")
                self.m_listMergeInfo.append((None, None, None, None, None))
                continue
            npImg, origin, scaling, direction, size = algImage.CAlgImage.get_np_from_nifti(niftiFullPath)
            sitkImg = algImage.CAlgImage.get_sitk_from_np(npImg, origin, scaling, direction)

            self.m_listMergeInfo.append((maskInfo, phaseInfo, reconParam, npImg, sitkImg))

        if self.get_mergeinfo_maskinfo(0) is not None and self.get_mergeinfo_maskinfo(1) is not None :
            self.MergeTargetInx = 0
            self.MergeSrcInx = 1

        dataInst = self.Data

        file = "clDataInfo.pkl"
        clInPath = dataInst.get_cl_in_path()
        clOutPath = dataInst.get_cl_out_path()
        pklFullPath = os.path.join(clInPath, file)
        if os.path.exists(pklFullPath) == False :
            return

        dataInfo = data.CData.load_inst(pklFullPath)
        if self.MergeClinfoInx >= dataInfo.get_info_count() :
            return
        
        clInfo = dataInfo.get_clinfo(self.MergeClinfoInx)
        clParam = dataInfo.get_clparam(self.MergeClinfoInx)
        reconParam = dataInfo.get_reconparam(self.MergeClinfoInx)

        dataInst.DataInfo.add_info(clInfo, clParam, reconParam)
        dataInst.attach_skeleton()

        self.m_mediator.load_vessel_key(self.MergeClinfoInx, 0)

        clOutput = clInfo.OutputName
        clOutputFullPath = os.path.join(clOutPath, f"{clOutput}.json")
        if os.path.exists(clOutputFullPath) == False :
            return
        
        dataInst.set_skeleton(self.MergeClinfoInx, clOutputFullPath)
        self.m_mediator.load_cl_key(self.MergeClinfoInx)
        self.m_mediator.load_br_key(self.MergeClinfoInx)
        self.m_mediator.load_ep_key(self.MergeClinfoInx)

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

    # [(maskInfo, phaseInfo, reconParamSingle, npImg, sitkImg), .. ]
    def get_mergeinfo_count(self) -> int :
        return len(self.m_listMergeInfo)
    def get_mergeinfo_maskinfo(self, inx : int) -> optionInfo.CMaskInfo :
        return self.m_listMergeInfo[inx][0]
    def get_mergeinfo_phaseinfo(self, inx : int) -> niftiContainer.CPhaseInfo :
        return self.m_listMergeInfo[inx][1]
    def get_mergeinfo_reconparam(self, inx : int) -> optionInfo.CReconParamSingle :
        return self.m_listMergeInfo[inx][2]
    def get_mergeinfo_npimg(self, inx : int) -> np.ndarray :
        return self.m_listMergeInfo[inx][3]
    def get_mergeinfo_sitk(self, inx : int) :
        return self.m_listMergeInfo[inx][4]
    def get_mergeinfo_physical_mat(self, inx : int) -> np.ndarray :
        if inx >= self.get_mergeinfo_count() :
            return None
        phaseInfo = self.get_mergeinfo_phaseinfo(inx)
        if phaseInfo is None :
            return None
        return algVTK.CVTK.get_vtk_phy_matrix_with_spacing(phaseInfo.Origin, phaseInfo.Spacing, phaseInfo.Direction, phaseInfo.Offset)
    def get_mergeinfo_resampling_mat(self, targetInx : int, srcInx : int) -> np.ndarray :
        if srcInx >= self.get_mergeinfo_count() :
            return None
        if targetInx >= self.get_mergeinfo_count() :
            return None
        
        srcPhaseInfo = self.get_mergeinfo_phaseinfo(srcInx)
        targetPhaseInfo = self.get_mergeinfo_phaseinfo(targetInx)

        if srcPhaseInfo is None or targetPhaseInfo is None :
            return None
        
        targetOffsetMat = algLinearMath.CScoMath.translation_mat4(targetPhaseInfo.Offset)
        srcOffsetMat = algLinearMath.CScoMath.translation_mat4(srcPhaseInfo.Offset)
        srcOffsetMat = algLinearMath.CScoMath.inv_mat4(srcOffsetMat)
        trans = algLinearMath.CScoMath.mul_mat4_mat4(srcOffsetMat, targetOffsetMat)
        return trans
    def get_mergeinfo_vertex(self, inx : int) -> np.ndarray :
        if inx >= self.get_mergeinfo_count() :
            return None
        npImg = self.get_mergeinfo_npimg(inx)
        if npImg is None :
            return None
        return algImage.CAlgImage.get_vertex_from_np(npImg, np.int32)
    def get_mergeinfo_resampling_vertex(self, targetInx : int, srcInx : int) -> np.ndarray :
        if srcInx >= self.get_mergeinfo_count() :
            return None
        if targetInx >= self.get_mergeinfo_count() :
            return None
        
        srcPhaseInfo = self.get_mergeinfo_phaseinfo(srcInx)
        targetPhaseInfo = self.get_mergeinfo_phaseinfo(targetInx)
        if srcPhaseInfo is None or targetPhaseInfo is None :
            return None
        
        resamplingTrans = self.get_mergeinfo_resampling_mat(targetInx, srcInx)
        sitkImg = self.get_mergeinfo_sitk(srcInx)
        if sitkImg is None :
            return None

        resamplingSitkImg = algImage.CAlgImage.resampling_sitkimg_with_mat(
            sitkImg, 
            targetPhaseInfo.Origin, targetPhaseInfo.Spacing, targetPhaseInfo.Direction, targetPhaseInfo.Size, 
            sitkImg.GetPixelID(), sitk.sitkNearestNeighbor, 
            resamplingTrans
            )
        npImg, origin, scaling, direction, size = algImage.CAlgImage.get_np_from_sitk(resamplingSitkImg, np.uint8)
        return algImage.CAlgImage.get_vertex_from_np(npImg, np.int32)
    

    @property
    def Data(self) -> data.CData :
        return self.m_data
    @property
    def MergeTargetInx(self) -> int :
        return self.m_mergeTargetInx
    @MergeTargetInx.setter
    def MergeTargetInx(self, targetInx : int) :
        self.m_mergeTargetInx = targetInx
    @property
    def MergeSrcInx(self) -> int :
        return self.m_mergeSrcInx
    @MergeSrcInx.setter
    def MergeSrcInx(self, srcInx : int) :
        self.m_mergeSrcInx = srcInx
    @property
    def MergeClinfoInx(self) -> int :
        return self.m_mergeClinfoInx


class CRegistration :
    def __init__(self) :
        self.m_inputTargetFullPath = ""
        self.m_inputSrcFullPath = ""
        self.m_inputRigid = False
    def clear(self) :
        self.m_inputTargetFullPath = ""
        self.m_inputSrcFullPath = ""
        self.m_inputRigid = False
    
    def process(self) -> np.ndarray :
        if self.m_inputTargetFullPath == "" :
            return None
        if self.m_inputSrcFullPath == "" :
            return None
        if os.path.exists(self.m_inputTargetFullPath) == False or os.path.exists(self.m_inputSrcFullPath) == False :
            print("-" * 30)
            print(f"not found registration files")
            print(f"target path : {self.m_inputTargetFullPath}")
            print(f"src path : {self.m_inputSrcFullPath}")
            print("-" * 30)
            return None
        
        if self.m_inputRigid == True :
            ctVertex, ctOrigin, ctSpacing, ctDirection, ctSize = algImage.CAlgImage.get_vertex_from_nifti(self.m_inputTargetFullPath)
            mrVertex, mrOrigin, mrSpacing, mrDirection, mrSize = algImage.CAlgImage.get_vertex_from_nifti(self.m_inputSrcFullPath)
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
        reg = scoReg.CRegRigidRefinedTransform()
        reg.process(self.m_inputSrcFullPath, self.m_inputTargetFullPath, [offsetX, offsetY, offsetZ])
        diceScore = reg.DiceScore
        offsetX = reg.OffsetX
        offsetY = reg.OffsetY
        offsetZ = reg.OffsetZ

        matTargetPhy = reg.MatTargetPhy.m_npMat.copy()
        matTargetPhy = algLinearMath.CScoMath.from_mat3_to_mat4(matTargetPhy[0 : 3, 0 : 3])
        offsetV = algLinearMath.CScoMath.to_vec4([offsetX, offsetY, offsetZ, 1.0])
        phyOffsetV = algLinearMath.CScoMath.from_vec4_to_vec3(algLinearMath.CScoMath.mul_mat4_vec4(matTargetPhy, offsetV))
        phyOffsetV = phyOffsetV + rigidPhysicalOffset

        return phyOffsetV
        
    
    # private
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
class CResamplingMask :
    def __init__(self) :
        self.m_inputData = None
        self.m_inputPatientID = ""
        self.m_optionInfo = None
        '''
        key : regInfoInx : int
        value : 4x4 matrix : np.ndarray
        '''
    def clear(self) :
        self.m_inputData = None
        self.m_inputPatientID = ""
        self.m_optionInfo = None
    def process(self) :
        if self.InputData is None :
            print("resampling : not setting input data")
            return
        if self.InputPatientID == "" :
            print("resampling : not setting input patientID")
            return

        self.m_dicReg = {}
        dataInst = self.InputData
        optionInfo = self.OptionInfo
        if "ResamplingInfo" not in optionInfo.JsonData :
            print("resampling : not found option ResamplingInfo")
            return
        listResamplingInfo = optionInfo.JsonData["ResamplingInfo"]
        for resamplingInfo in listResamplingInfo :
            name = resamplingInfo["name"]
            outName = resamplingInfo["outName"]
            targetPhase = resamplingInfo["targetPhase"]
            phase = self._get_phase(name)

            regInfoInx = self._find_reginfoInx(targetPhase, phase)
            if regInfoInx == -1 :
                print("resampling : invalid resampling phase")
                continue

            trans = None
            origin = None
            scaling = None
            direction = None
            size = None
            maskPath = self._get_mask_path()
            if regInfoInx in self.m_dicReg :
                trans = self.m_dicReg[regInfoInx][0]
                origin = self.m_dicReg[regInfoInx][1]
                scaling = self.m_dicReg[regInfoInx][2]
                direction = self.m_dicReg[regInfoInx][3]
                size = self.m_dicReg[regInfoInx][4]
            else :
                regInfo = self.OptionInfo.get_reginfo(regInfoInx)
                srcMaskFile = f"{regInfo.Src}.nii.gz"
                srcMaskFullPath = os.path.join(maskPath, srcMaskFile)
                targetMaskFile = f"{regInfo.Target}.nii.gz"
                targetMaskFullPath = os.path.join(maskPath, targetMaskFile)

                regBlock = CRegistration()
                regBlock.m_inputTargetFullPath = targetMaskFullPath
                regBlock.m_inputSrcFullPath = srcMaskFullPath
                regBlock.m_inputRigid = True
                phyOffset = regBlock.process()
                if phyOffset is None :
                    print("resampling : not found landmark mask")
                    continue

                npImg, origin, scaling, direction, size = algImage.CAlgImage.get_np_from_nifti(targetMaskFullPath)
                trans = algLinearMath.CScoMath.translation_mat4(phyOffset)
                trans = algLinearMath.CScoMath.inv_mat4(trans)
                self.m_dicReg[regInfoInx] = (trans, origin, scaling, direction, size)
            
            maskFullPath = os.path.join(maskPath, f"{name}.nii.gz")
            outMaskFullPath = os.path.join(maskPath, f"{outName}.nii.gz")

            if os.path.exists(maskFullPath) == False :
                print("resampling : not found mask")
                continue

            npImgSrc, originSrc, scalingSrc, directionSrc, sizeSrc = algImage.CAlgImage.get_np_from_nifti(maskFullPath)
            sitkSrc = algImage.CAlgImage.get_sitk_from_np(npImgSrc, originSrc, scalingSrc, directionSrc)
            sitkSrcResampled = algImage.CAlgImage.resampling_sitkimg_with_mat(
                sitkSrc, 
                origin, scaling, direction, size, 
                sitkSrc.GetPixelID(), sitk.sitkNearestNeighbor, 
                trans
                )
            npImgRet, originRet, scalingRet, directionRet, sizeRet = algImage.CAlgImage.get_np_from_sitk(sitkSrcResampled, np.uint8)
            algImage.CAlgImage.save_nifti_from_np(outMaskFullPath, npImgRet, origin, scaling, direction, (2, 1, 0))
            print(f"passed resampling {name} -> {outName}")


    
    def _get_phase(self, maskName : str) -> str :
        optionInfo = self.OptionInfo
        listMaskInfo = optionInfo.find_maskinfo_list_by_name(maskName)
        if listMaskInfo is None :
            return ""
        maskInfo = listMaskInfo[0]
        return maskInfo.Phase
    def _find_reginfoInx(self, targetPhase : str, srcPhase : str) -> int :
        '''
        ret : -1, 찾을 수 없는 경우 
        '''
        optionInfo = self.OptionInfo
        regInfoInx = optionInfo.find_reginfo_inx_by_src_phase(srcPhase)
        if regInfoInx == -1 :
            return -1
        
        regInfo = optionInfo.get_reginfo(regInfoInx)
        phase = self._get_phase(regInfo.Target)
        if phase != targetPhase :
            return -1
        
        return regInfoInx
    def _get_mask_path(self) -> str :
        patientID = self.InputPatientID
        dataRootPath = self.OptionInfo.DataRootPath
        return os.path.join(dataRootPath, os.path.join(patientID, "Mask"))


    @property
    def InputData(self) -> data.CData :
        return self.m_inputData
    @InputData.setter
    def InputData(self, inputData : data.CData) :
        self.m_inputData = inputData
        self.m_optionInfo = inputData.OptionInfo
    @property
    def InputPatientID(self) -> str :
        return self.m_inputPatientID
    @InputPatientID.setter
    def InputPatientID(self, inputPatientID : str) :
        self.m_inputPatientID = inputPatientID
    @property
    def OptionInfo(self) -> optionInfo.COptionInfoSingle :
        return self.m_optionInfo


if __name__ == '__main__' :
    pass


# print ("ok ..")

