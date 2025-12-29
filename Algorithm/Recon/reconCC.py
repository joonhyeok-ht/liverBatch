import numpy as np
import matplotlib.pyplot as plt
import os, sys
import matplotlib.patches as patches
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import scoUtil
import scoData
import scoReg
import scoMath
import scoRenderObj
import scoSkeleton
import scoSkeletonVM
import scoBuffer
import scoBufferAlg

import reconInterface


'''
Name
    - ReconWithCCBlock
Input
    - "InputPath"       : folder including nifti files
    - "InputPhyInfo"    : physical info json path of nifti files (with physicalInfo)
Output
    - "OutputPath"      : the folder to copy recon files
    - "DebugCC"         : output csv file including stl and mask cc
Property
    - "Active"          : 0 or 1
    - "AddReconParam"   : [iterCnt, relaxation, decimation, anchorCC]
    - "AddNiftiFile     : nifti file name
global
    - "Debug"           : 0 or 1 
'''

class CReconParam :
    def __init__(self) -> None:
        self.m_type = 0.0
        self.m_iterCnt = 0
        self.m_relaxation = 0.0
        self.m_decimation = 0.0
        self.m_anchorCC = 0.0
    

    @property
    def Type(self) -> float:
        return self.m_type
    @Type.setter
    def Type(self, type : float) :
        self.m_type = type
    @property
    def IterCnt(self) -> int:
        return self.m_iterCnt
    @IterCnt.setter
    def IterCnt(self, iterCnt : int) :
        self.m_iterCnt = iterCnt
    @property
    def Relaxation(self) -> float:
        return self.m_relaxation
    @Relaxation.setter
    def Relaxation(self, relaxation : float) :
        self.m_relaxation = relaxation
    @property
    def Decimation(self) -> float:
        return self.m_decimation
    @Decimation.setter
    def Decimation(self, decimation : float) :
        self.m_decimation = decimation
    @property
    def AnchorCC(self) -> float:
        return self.m_anchorCC
    @AnchorCC.setter
    def AnchorCC(self, anchorCC : float) :
        self.m_anchorCC = anchorCC
class CReconTable :
    def __init__(self) -> None:
        self.m_table = []
    def clear(self) :
        self.m_table.clear()

    def add_recon_param(self, reconParam : CReconParam) :
        reconParam.Type = self.get_recon_param_count()
        self.m_table.append(reconParam)
    def get_recon_param_count(self) -> int :
        return len(self.m_table)
    def get_recon_param(self, index : int) -> CReconParam :
        return self.m_table[index]
    def get_recon_param_with_mask_cc(self, maskCC : float) -> CReconParam :
        tableCnt = self.get_recon_param_count()

        if tableCnt == 1 :
            return self.m_table[0]
        
        if maskCC < self.m_table[0].AnchorCC :
            return self.m_table[0]
        elif maskCC >= self.m_table[-1].AnchorCC :
            return self.m_table[-1]
        
        retReconParam = CReconParam()
        retReconParam.Type = self.m_table[-1].Type
        retReconParam.IterCnt = self.m_table[-1].IterCnt
        retReconParam.Relaxation = self.m_table[-1].Relaxation
        retReconParam.Decimation = self.m_table[-1].Decimation
        
        for index in range(0, tableCnt - 1) :
            reconParam0 = self.m_table[index]
            reconParam1 = self.m_table[index + 1]
            if maskCC >= reconParam0.AnchorCC and maskCC < reconParam1.AnchorCC :
                t = self.get_factor(reconParam0.AnchorCC, reconParam1.AnchorCC, maskCC)
                retReconParam.Type = self.get_interp(reconParam0.Type, reconParam1.Type, t)
                retReconParam.IterCnt = int(self.get_interp(reconParam0.IterCnt, reconParam1.IterCnt, t) + 0.5)
                retReconParam.Relaxation = self.get_interp(reconParam0.Relaxation, reconParam1.Relaxation, t)
                retReconParam.Decimation = self.get_interp(reconParam0.Decimation, reconParam1.Decimation, t)
                return retReconParam
        return retReconParam
    def get_factor(self, minVal, maxVal, val) :
        totalLen = maxVal - minVal
        delta = val - minVal
        return delta / totalLen
    def get_interp(self, minVal, maxVal, factor : float) :
        totalLen = maxVal - minVal
        return minVal + totalLen * factor
class CMaskInfo :
    def __init__(self) -> None:
        self.m_maskPath = ""
        self.m_stlPath = ""
        self.m_maskCC = 0.0
        self.m_stlCC = 0.0
        self.m_reconParam = None


    @property
    def ReconParam(self) -> float:
        return self.m_reconParam
    @ReconParam.setter
    def ReconParam(self, reconParam : CReconParam) :
        self.m_reconParam = reconParam
    @property
    def MaskPath(self) -> str:
        return self.m_maskPath
    @MaskPath.setter
    def MaskPath(self, maskPath : str) :
        self.m_maskPath = maskPath
    @property
    def STLPath(self) -> str:
        return self.m_stlPath
    @STLPath.setter
    def STLPath(self, stlPath : str) :
        self.m_stlPath = stlPath
    @property
    def MaskCC(self) -> float:
        return self.m_maskCC
    @MaskCC.setter
    def MaskCC(self, maskCC : float) :
        self.m_maskCC = maskCC
    @property
    def STLCC(self) -> float:
        return self.m_stlCC
    @STLCC.setter
    def STLCC(self, stlCC : float) :
        self.m_stlCC = stlCC


class CReconWithCC(reconInterface.CReconInterface) :
    def __init__(self) -> None:
        super().__init__()
        # input your code
        self.dbg_cc = ""
        self.dbg = 0
        self.m_reconTable = CReconTable()
        self.m_listNiftiName = []
        self.m_listMaskInfo = []
    def process(self) :
        super().process()
        # input your code 
        for niftiFileName in self.m_listNiftiName :
            self._init_mask_info(niftiFileName)
        for maskInfo in self.m_listMaskInfo :
            self._recon_mask_info(maskInfo)
        self._dbg_cc(self.dbg_cc)
    def clear(self) :
        # input your code
        self.m_listNiftiName.clear()
        self.m_listMaskInfo.clear()
        self.m_reconTable.clear()
        super().clear()


    def set_debug(self, dbg : int) :
        self.dbg = dbg
    def add_recon_param(
            self, 
            iterCnt : int,
            relaxation : float,
            decimation : float,
            anchorCC : float
            ) :
        reconParam = CReconParam()
        reconParam.IterCnt = iterCnt
        reconParam.Relaxation = relaxation
        reconParam.Decimation = decimation
        reconParam.AnchorCC = anchorCC
        self.m_reconTable.add_recon_param(reconParam)
    def add_nifti_file(self, niftiFileName : str) :
        self.m_listNiftiName.append(niftiFileName)


    @property
    def DbgCC(self) -> str :
        return self.dbg_cc
    @DbgCC.setter
    def DbgCC(self, dbg_cc : str) :
        self.dbg_cc = dbg_cc


    # protected
    def _init_mask_info(self, niftiFileName : str) :
        bRet, niftiFullPath, stlFullPath = reconInterface.CReconInterface.get_nifti_stl_full_path(self.InputPath, niftiFileName, self.OutputPath)
        if bRet == False :
            print(f"not found {niftiFileName}")
            return
        
        maskInfo = CMaskInfo()
        maskInfo.MaskPath = niftiFullPath
        maskInfo.STLPath = stlFullPath
        maskInfo.MaskCC = scoUtil.CScoUtilSimpleITK.get_nifti_cc(niftiFullPath, "uint8")
        self.m_listMaskInfo.append(maskInfo)
    def _recon_mask_info(self, maskInfo : CMaskInfo) :
        reconParam = self.m_reconTable.get_recon_param_with_mask_cc(maskInfo.MaskCC)
        maskInfo.ReconParam = reconParam

        iterCnt = reconParam.IterCnt
        relaxation = reconParam.Relaxation
        decimation = reconParam.Decimation

        niftiFileName = scoUtil.CScoUtilOS.get_file_name(maskInfo.MaskPath)

        if self._exist_physical_info(niftiFileName) == True :
            self._recon_with_phy(niftiFileName, maskInfo.MaskPath, maskInfo.STLPath, iterCnt, relaxation, decimation, 0)
        else :
            self._recon(maskInfo.MaskPath, maskInfo.STLPath, iterCnt, relaxation, decimation, 0)
    def _get_error(self, maskCC : float, stlCC : float) :
        fRet = maskCC - stlCC
        if fRet < 0.0 :
            fRet = -fRet
        fRet = fRet / maskCC
        return fRet
    def _dbg_cc(self, csvFullPath : str) :
        if self.dbg == 0 :
            return
        for maskInfo in self.m_listMaskInfo :
            stlCC = scoUtil.CScoUtilVTK.get_stl_volume(maskInfo.STLPath, "mm")
            maskInfo.STLCC = stlCC

        listColumn = ["ReconType", "MaskCC", "STLCC", "Error"]
        listRow = []
        listIndex = []

        for maskInfo in self.m_listMaskInfo :
            fileName = maskInfo.STLPath.split(".")[0]
            fileName = fileName.split("/")[-1]
            listIndex.append(fileName)

            listTmp = []
            listTmp.append(maskInfo.ReconParam.Type)
            listTmp.append(maskInfo.MaskCC)
            listTmp.append(maskInfo.STLCC)
            listTmp.append(self._get_error(maskInfo.MaskCC, maskInfo.STLCC))
            listRow.append(listTmp)
    
        df = pd.DataFrame(listRow, columns=listColumn, index=listIndex)
        df.to_csv(csvFullPath)




