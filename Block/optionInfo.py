import sys
import os
import numpy as np
import pickle 
import copy

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
solutionPath = os.path.dirname(fileAbsPath)
sys.path.append(fileAbsPath)
sys.path.append(solutionPath)

import AlgUtil.algLinearMath as algLinearMath
# import example_vtk.frameworkVTK as frameworkVTK


import json

'''
Pass
'''
class CPass :
    def __init__(self):
        self.m_name = ""
        self.m_in = ""
        self.m_triOpt = 0
    def clear(self) :
        self.m_name = ""
        self.m_in = ""
        self.m_triOpt = 0

    @property
    def Name(self) -> str :
        return self.m_name
    @Name.setter
    def Name(self, name : str) :
        self.m_name = name
    @property
    def In(self) -> str :
        return self.m_in
    @In.setter
    def In(self, _in : str) :
        self.m_in = _in
    @property
    def TriOpt(self) -> int :
        return self.m_triOpt
    @TriOpt.setter
    def TriOpt(self, triOpt : int) :
        self.m_triOpt = triOpt




'''
recon param 
CReconParam <- CReconParamSingle
            <- CReconParamRange
            <- CReconParamRangeSharpness
'''
class CReconParam : 
    def __init__(self):
        self.m_type = ""
        self.m_contour = 10
        self.m_algorithm = ""
    def clear(self) :
        self.m_type = ""
        self.m_contour = 10
        self.m_algorithm = ""

    @property
    def Type(self) -> str :
        return self.m_type
    @Type.setter
    def Type(self, type : str) :
        self.m_type = type
    @property
    def Contour(self) -> int :
        return self.m_contour
    @Contour.setter
    def Contour(self, contour : int) :
        self.m_contour = contour
    @property
    def Algorithm(self) -> str :
        return self.m_algorithm
    @Algorithm.setter
    def Algorithm(self, algorithm : str) :
        self.m_algorithm = algorithm
class CReconParamSingle(CReconParam) :
    def __init__(self):
        super().__init__()
        # input your code
        self.m_param = None
        self.m_gaussian = 0
        self.m_resamplingFactor = 0
    def clear(self) :
        # input your code
        self.m_param = None
        self.m_gaussian = 0
        self.m_resamplingFactor = 0
        super().clear()

    @property
    def Param(self) -> list :
        return self.m_param
    @Param.setter
    def Param(self, param : list) :
        self.m_param = param
    @property
    def Gaussian(self) -> int :
        return self.m_gaussian
    @Gaussian.setter
    def Gaussian(self, gaussian : int) :
        self.m_gaussian = gaussian
    @property
    def ResamplingFactor(self) -> int :
        return self.m_resamplingFactor
    @ResamplingFactor.setter
    def ResamplingFactor(self, resamplingFactor : int) :
        self.m_resamplingFactor = resamplingFactor
class CReconParamRange(CReconParam) :
    def __init__(self):
        super().__init__()
        # input your code
        self.m_iter = 0
        self.m_relaxRange = None
        self.m_deciRange = None
        self.m_gaussian = 0
        self.m_resamplingFactor = 0
    def clear(self) :
        # input your code
        self.m_iter = 0
        self.m_relaxRange = None
        self.m_deciRange = None
        self.m_gaussian = 0
        self.m_resamplingFactor = 0
        super().clear()
    
    @property
    def Iter(self) -> int :
        return self.m_iter
    @Iter.setter
    def Iter(self, iter : int) :
        self.m_iter = iter
    @property
    def RelaxRange(self) -> list :
        return self.m_relaxRange
    @RelaxRange.setter
    def RelaxRange(self, relaxRange : list) :
        self.m_relaxRange = relaxRange
    @property
    def DeciRange(self) -> list :
        return self.m_deciRange
    @DeciRange.setter
    def DeciRange(self, deciRange : list) :
        self.m_deciRange = deciRange
    @property
    def Gaussian(self) -> int :
        return self.m_gaussian
    @Gaussian.setter
    def Gaussian(self, gaussian : int) :
        self.m_gaussian = gaussian
    @property
    def ResamplingFactor(self) -> int :
        return self.m_resamplingFactor
    @ResamplingFactor.setter
    def ResamplingFactor(self, resamplingFactor : int) :
        self.m_resamplingFactor
class CReconParamRangeSharpness(CReconParam) :
    def __init__(self):
        super().__init__()
        # input your code
        self.m_iter = 0
        self.m_deciRange = None
        self.m_sharpnessAngleRange = None
        self.m_sharpnessNormalAngleRange = None
    def clear(self) :
        # input your code
        self.m_iter = 0
        self.m_deciRange = None
        self.m_sharpnessAngleRange = None
        self.m_sharpnessNormalAngleRange = None
        super().clear()
    
    @property
    def Iter(self) -> int :
        return self.m_iter
    @Iter.setter
    def Iter(self, iter : int) :
        self.m_iter = iter
    @property
    def DeciRange(self) -> list :
        return self.m_deciRange
    @DeciRange.setter
    def DeciRange(self, deciRange : list) :
        self.m_deciRange = deciRange
    @property
    def SharpnessAngleRange(self) -> list :
        return self.m_sharpnessAngleRange
    @SharpnessAngleRange.setter
    def SharpnessAngleRange(self, sharpnessAngleRange : list) :
        self.m_sharpnessAngleRange = sharpnessAngleRange
    @property
    def SharpnessNormalAngleRange(self) -> list :
        return self.m_sharpnessNormalAngleRange
    @SharpnessNormalAngleRange.setter
    def SharpnessNormalAngleRange(self, sharpnessNormalAngleRange : list) :
        self.m_sharpnessNormalAngleRange = sharpnessNormalAngleRange

'''
centerline param
'''
class CCenterlineParam :
    def __init__(self):
        self.m_type = ""
        self.m_advancementRatio = 1.0
        self.m_resamplingLength = 1.0
        self.m_smoothingIter = 10
        self.m_smoothingFactor = 0.1
    def clear(self) :
        self.m_type = ""
        self.m_advancementRatio = 1.0
        self.m_resamplingLength = 1.0
        self.m_smoothingIter = 10
        self.m_smoothingFactor = 0.1
    
    @property
    def Type(self) -> str : 
        return self.m_type
    @Type.setter
    def Type(self, type : str) :
        self.m_type = type
    @property
    def AdvancementRatio(self) -> float : 
        return self.m_advancementRatio
    @AdvancementRatio.setter
    def AdvancementRatio(self, advancementRatio : float) :
        self.m_advancementRatio = advancementRatio
    @property
    def ResamplingLength(self) -> float : 
        return self.m_resamplingLength
    @ResamplingLength.setter
    def ResamplingLength(self, resamplingLength : float) :
        self.m_resamplingLength = resamplingLength
    @property
    def SmoothingIter(self) -> int : 
        return self.m_smoothingIter
    @SmoothingIter.setter
    def SmoothingIter(self, smoothingIter : int) :
        self.m_smoothingIter = smoothingIter
    @property
    def SmoothingFactor(self) -> float : 
        return self.m_smoothingFactor
    @SmoothingFactor.setter
    def SmoothingFactor(self, smoothingFactor : float) :
        self.m_smoothingFactor = smoothingFactor


'''
MaskInfo
CMaskInfo <- CMaskInfoRange
'''
class CMaskInfo :
    def __init__(self):
        self.m_name = ""
        self.m_phase = ""
        self.m_reconType = ""
        self.m_strictureMode = 0
        self.m_blenderName = ""
    def clear(self) :
        self.m_name = ""
        self.m_phase = ""
        self.m_reconType = ""
        self.m_strictureMode = 0
        self.m_blenderName = ""

    @property
    def Name(self) -> str : 
        return self.m_name
    @Name.setter
    def Name(self, name : str) :
        self.m_name = name
    @property
    def Phase(self) -> str : 
        return self.m_phase
    @Phase.setter
    def Phase(self, phase : str) :
        self.m_phase = phase
    @property
    def ReconType(self) -> str : 
        return self.m_reconType
    @ReconType.setter
    def ReconType(self, reconType : str) :
        self.m_reconType = reconType
    @property
    def StrictureMode(self) -> int : 
        return self.m_strictureMode
    @StrictureMode.setter
    def StrictureMode(self, strictureMode : int) :
        self.m_strictureMode = strictureMode
    @property
    def BlenderName(self) -> str : 
        return self.m_blenderName
    @BlenderName.setter
    def BlenderName(self, blenderName : str) :
        self.m_blenderName = blenderName
class CMaskInfoRange(CMaskInfo) :
    def __init__(self):
        super().__init__()
        # input your code
        self.m_blenderOption = None
    def clear(self) :
        # input your code
        self.m_blenderOption = None
        super().clear()

    def get_blender_option_count(self) -> int :
        return len(self.m_blenderOption)
    def get_blender_option(self, inx : int) -> str :
        return self.m_blenderOption[inx]

    @property
    def BlenderOption(self) -> list : 
        return self.m_blenderOption
    @BlenderOption.setter
    def BlenderOption(self, blenderOption : list) :
        self.m_blenderOption = blenderOption



'''
RegistrationInfo
'''
class CRegistrationInfo :
    def __init__(self):
        self.m_target = ""
        self.m_src = ""
        self.m_rigidAABB = 0
    def clear(self) :
        self.m_target = ""
        self.m_src = ""
        self.m_rigidAABB = 0

    @property
    def Target(self) -> str : 
        return self.m_target
    @Target.setter
    def Target(self, target : str) :
        self.m_target = target
    @property
    def Src(self) -> str : 
        return self.m_src
    @Src.setter
    def Src(self, src : str) :
        self.m_src = src
    @property
    def RigidAABB(self) -> int : 
        return self.m_rigidAABB
    @RigidAABB.setter
    def RigidAABB(self, rigidAABB : int) :
        self.m_rigidAABB = rigidAABB


'''
SegmentInfo
'''
class CSegmentInfo :
    def __init__(self):
        self.m_type = ""
        self.m_organ = ""
        self.m_listVesselInfo = []
    def clear(self) :
        self.m_type = ""
        self.m_organ = ""
        self.m_listVesselInfo.clear()


    def add_vesselinfo(self, wholeVessel : str, childVesselStartNumber : int, childVesselEndNumber : int, dilationIter : int = 1, noiseSegCnt : int = 27) :
        self.m_listVesselInfo.append((wholeVessel, childVesselStartNumber, childVesselEndNumber, dilationIter, noiseSegCnt))
    def get_vesselinfo_count(self) -> int :
        return len(self.m_listVesselInfo)
    def get_vesselinfo_whole_vessel(self, inx : int) -> str :
        return self.m_listVesselInfo[inx][0]
    def get_vesselinfo_child_start(self, inx : int) -> int :
        return self.m_listVesselInfo[inx][1]
    def get_vesselinfo_child_end(self, inx : int) -> int :
        return self.m_listVesselInfo[inx][2]
    def get_vesselinfo_dilation_iter(self, inx : int) -> int :
        return self.m_listVesselInfo[inx][3]
    def get_vesselinfo_noise_seg_count(self, inx : int) -> int :
        return self.m_listVesselInfo[inx][4]


    @property
    def Type(self) -> str : 
        '''
        type : mask, blender, centerline
        '''
        return self.m_type
    @Type.setter
    def Type(self, type : str) :
        '''
        type : mask, blender, centerline
        '''
        self.m_type = type
    @property
    def Organ(self) -> str : 
        return self.m_organ
    @Organ.setter
    def Organ(self, organ : str) :
        self.m_organ = organ

    



'''
** MeshLib Option **

MeshBoolean
'''
class CMeshBoolean :
    def __init__(self):
        self.m_operator = "subtraction"
        self.m_blenderName0 = ""
        self.m_blenderName1 = ""
        self.m_fillHole = 0
        self.m_blenderName = ""
    def clear(self) :
        self.m_operator = "subtraction"
        self.m_blenderName0 = ""
        self.m_blenderName1 = ""
        self.m_fillHole = 0
        self.m_blenderName = ""

    @property
    def Operator(self) -> str : 
        return self.m_operator
    @Operator.setter
    def Operator(self, operator : str) :
        self.m_operator = operator
    @property
    def BlenderName0(self) -> str : 
        return self.m_blenderName0
    @BlenderName0.setter
    def BlenderName0(self, blenderName0 : str) :
        self.m_blenderName0 = blenderName0
    @property
    def BlenderName1(self) -> str : 
        return self.m_blenderName1
    @BlenderName1.setter
    def BlenderName1(self, blenderName1 : str) :
        self.m_blenderName1 = blenderName1
    @property
    def FillHole(self) -> int : 
        return self.m_fillHole
    @FillHole.setter
    def FillHole(self, fillHole : int) :
        self.m_fillHole = fillHole
    @property
    def BlenderName(self) -> str : 
        return self.m_blenderName
    @BlenderName.setter
    def BlenderName(self, blenderName : str) :
        self.m_blenderName = blenderName
   


'''
CenterlineInfo
'''
class CCenterlineInfo : 
    def __init__(self):
        self.m_centerlineType = ""
        self.m_inputKey = ""
        self.m_treeRootKey = ""
        self.m_findCell = ""
        self.m_outputName = ""

        self.m_input = {}
        self.m_input["blenderName"] = ""
        self.m_input["reconType"] = ""

        self.m_treeRoot = {}
        self.m_treeRoot["maskName"] = ""
        self.m_treeRoot["blenderName"] = ""
        self.m_treeRoot["axis"] = ""
        self.m_treeRoot["nnPos"] = [0.0, 0.0, 0.0]
    def clear(self) :
        self.m_centerlineType = ""
        self.m_inputKey = ""
        self.m_treeRootKey = ""
        self.m_findCell = ""
        self.m_outputName = ""

        self.m_input = {}
        self.m_input["blenderName"] = ""
        self.m_input["reconType"] = ""

        self.m_treeRoot = {}
        self.m_treeRoot["maskName"] = ""
        self.m_treeRoot["blenderName"] = ""
        self.m_treeRoot["axis"] = ""
        self.m_treeRoot["nnPos"] = [0.0, 0.0, 0.0]

    def get_input_blender_name(self) -> str :
        return self.m_input["blenderName"]
    def get_input_recon_type(self) -> str :
        return self.m_input["reconType"]
    
    def get_treeroot_mask_name(self) -> str :
        return self.m_treeRoot["maskName"]
    def get_treeroot_blender_name(self) -> str :
        return self.m_treeRoot["blenderName"]
    def get_treeroot_axis(self) -> str :
        return self.m_treeRoot["axis"]
    def get_treeroot_nnpos(self) -> np.ndarray :
        return algLinearMath.CScoMath.to_vec3(self.m_treeRoot["nnPos"])


    @property
    def CenterlineType(self) -> str : 
        return self.m_centerlineType
    @CenterlineType.setter
    def CenterlineType(self, centerlineType : str) :
        self.m_centerlineType = centerlineType
    @property
    def InputKey(self) -> str : 
        return self.m_inputKey
    @InputKey.setter
    def InputKey(self, inputKey : str) :
        self.m_inputKey = inputKey
    @property
    def TreeRootKey(self) -> str : 
        return self.m_treeRootKey
    @TreeRootKey.setter
    def TreeRootKey(self, treeRootKey : str) :
        self.m_treeRootKey = treeRootKey
    @property
    def FindCell(self) -> str : 
        return self.m_findCell
    @FindCell.setter
    def FindCell(self, findCell : str) :
        self.m_findCell = findCell
    @property
    def OutputName(self) -> str : 
        return self.m_outputName
    @OutputName.setter
    def OutputName(self, outputName : str) :
        self.m_outputName = outputName
    @property
    def Input(self) -> dict : 
        return self.m_input
    @Input.setter
    def Input(self, input : dict) :
        self.m_input = input
    @property
    def TreeRoot(self) -> dict : 
        return self.m_treeRoot
    @TreeRoot.setter
    def TreeRoot(self, treeRoot : dict) :
        self.m_treeRoot = treeRoot


'''
MetricInfo
'''
class CMetricInfo :
    def __init__(self):
        self.m_type = ""
        self.m_listParam = []
    def clear(self) :
        self.m_type = ""
        self.m_listParam.clear()

    def add_param(self, param) :
        self.m_listParam.append(param)
    def get_param_count(self) -> int :
        return len(self.m_listParam)
    def get_param(self, inx : int) :
        return self.m_listParam[inx]
    

    @property
    def Type(self) -> str : 
        return self.m_type
    @Type.setter
    def Type(self, type : str) :
        self.m_type = type

    



'''
COptionInfo <- COptionInfoSingle
            <- COptionInfoRange
'''
class COptionInfo() :
    def __init__(self, jsonPath : str) -> None :
        self.m_jsonPath = jsonPath
        self.m_jsonData = None

        self.m_dataRootPath = ""
        self.m_cl = ""

        self.m_reconParamList = None
        self.m_centerlineParamList = None

        self.m_maskInfo = None
        self.m_registrationInfo = None
        self.m_centerlineInfo = None
        self.m_segmentInfo = None

        self.m_meshHealing = None
        self.m_meshBoolean = None

        self.m_metricInfo = None

        self.m_blenderExe = ""
        self.m_bReady = False

        with open(self.m_jsonPath, 'r') as fp :
            self.m_jsonData = json.load(fp)
        if self.m_jsonData is None or len(self.m_jsonData) == 0 :
            print(f"not found {self.m_jsonPath}")
            return
        
        # param info
        self.m_dataRootPath = self.m_jsonData["DataRootPath"]
        if "CL" in self.m_jsonData.keys():
            self.m_cl = self.m_jsonData["CL"]
        else:
            self.m_cl = ""
            
        self.m_reconParamList = self.m_jsonData["ReconParamList"]
        if "CenterlineParamList" in self.m_jsonData :
            self.m_centerlineParamList = self.m_jsonData["CenterlineParamList"]
        else :
            self.m_centerlineParamList = None

        # instance info
        self.m_maskInfo = self.m_jsonData["MaskInfo"]
        if "RegistrationInfo" in self.m_jsonData :
            self.m_registrationInfo = self.m_jsonData["RegistrationInfo"]
        else :
            self.m_registrationInfo = None
        if "CenterlineInfo" in self.m_jsonData :
            self.m_centerlineInfo = self.m_jsonData["CenterlineInfo"]
        else :
            self.m_centerlineInfo = None
        if "SegmentInfo" in self.m_jsonData :
            self.m_segmentInfo = self.m_jsonData["SegmentInfo"]
        else : 
            self.m_segmentInfo = None
        
        # meshlib info
        if "MeshLib" in self.m_jsonData :
            if "MeshHealing" in self.m_jsonData["MeshLib"] :
                self.m_meshHealing = self.m_jsonData["MeshLib"]["MeshHealing"]
            if "MeshBoolean" in self.m_jsonData["MeshLib"] :
                self.m_meshBoolean = self.m_jsonData["MeshLib"]["MeshBoolean"]
        
        if "MetricInfo" in self.m_jsonData :
            self.m_metricInfo = self.m_jsonData["MetricInfo"]
        

        self.m_blenderExe = self.m_jsonData["Blender"]["BlenderExe"]

        # instance initialize
        self.m_listReconParam = []
        self.m_listCenterlineParam = []
        self.m_listMaskInfo = []
        self.m_listRegistrationInfo = []
        self.m_listSegmentInfo = []
        self.m_listCenterlineInfo = []
        self.m_listMeshBoolean = []
        self.m_listMetricInfo = []

        self._init_recon_param()
        self._init_centerline_param()
        self._init_mask_info()
        self._init_registration_info()
        self._init_segment_info()
        self._init_centerline_info()
        self._init_mesh_boolean()
        self._init_metric_info()

        self.m_bReady = True
    def clear(self) :
        for reconParam in self.m_listReconParam :
            reconParam.clear()
        self.m_listReconParam.clear()
        for centerlineParam in self.m_listCenterlineParam :
            centerlineParam.clear()
        self.m_listCenterlineParam.clear()
        for maskInfo in self.m_listMaskInfo :
            maskInfo.clear()
        self.m_listMaskInfo.clear()
        for regInfo in self.m_listRegistrationInfo :
            regInfo.clear()
        self.m_listRegistrationInfo.clear()
        for segInfo in self.m_listSegmentInfo :
            segInfo.clear()
        self.m_listSegmentInfo.clear()
        for centerlineInfo in self.m_listCenterlineInfo :
            centerlineInfo.clear()
        self.m_listCenterlineInfo.clear()
        for meshBoolean in self.m_listMeshBoolean :
            meshBoolean.clear()
        self.m_listMeshBoolean.clear()
        for metricInfo in self.m_listMetricInfo :
            metricInfo.clear()
        self.m_listMetricInfo.clear()

        self.m_jsonPath = ""
        self.m_jsonData = None

        self.m_dataRootPath = ""
        self.m_reconParamList = None
        self.m_centerlineParamList = None

        self.m_maskInfo = None
        self.m_registrationInfo = None
        self.m_segmentInfo = None
        self.m_centerlineInfo = None

        self.m_meshHealing = None
        self.m_meshBoolean = None
        self.m_metricInfo = None

        self.m_blenderExe = ""
        self.m_bReady = False

    def get_recon_param_count(self) -> int :
        return len(self.m_listReconParam)
    def get_recon_param(self, inx : int) -> CReconParam :
        return self.m_listReconParam[inx]
    def find_recon_param(self, reconType : str) -> CReconParam :
        iReconParamCnt = self.get_recon_param_count()
        for inx in range(0, iReconParamCnt) :
            reconParam = self.get_recon_param(inx)
            if reconParam.Type == reconType :
                return reconParam
        return None
    def get_centerline_param_count(self) -> int :
        return len(self.m_listCenterlineParam)
    def get_centerline_param(self, inx : int) -> CCenterlineParam :
        return self.m_listCenterlineParam[inx]
    def find_centerline_param(self, centerlineType : str) -> CCenterlineParam :
        iCenterlineParamCnt = self.get_centerline_param_count()
        for inx in range(0, iCenterlineParamCnt) :
            centerlineParam = self.get_centerline_param(inx)
            if centerlineParam.Type == centerlineType :
                return centerlineParam
        return None
    def get_maskinfo_count(self) -> int :
        return len(self.m_listMaskInfo)
    def get_maskinfo(self, inx : int) -> CMaskInfo :
        return self.m_listMaskInfo[inx]
    def find_maskinfo_list_by_name(self, name : str) -> list :
        retList = []
        iMaskInfoCnt = self.get_maskinfo_count()
        for inx in range(0, iMaskInfoCnt) :
            maskInfo = self.get_maskinfo(inx)
            if maskInfo.Name == name :
                retList.append(maskInfo)
        if len(retList) == 0 :
            return None
        return retList
    def find_maskinfo_by_blender_name(self, blenderName : str) -> CMaskInfo :
        iMaskInfoCnt = self.get_maskinfo_count()
        for inx in range(0, iMaskInfoCnt) :
            maskInfo = self.get_maskinfo(inx)
            if maskInfo.BlenderName == blenderName :
                return maskInfo
        return None
    def get_reginfo_count(self) -> int :
        return len(self.m_listRegistrationInfo)
    def get_reginfo(self, inx : int) -> CRegistrationInfo :
        return self.m_listRegistrationInfo[inx]
    def find_reginfo_inx_by_src_phase(self, srcPhase : str) :
        '''
        ret : -1 -> srcPhase가 존재하지 않음 
        '''
        regInfoCnt = self.get_reginfo_count()
        for inx in range(0, regInfoCnt) :
            regInfo = self.get_reginfo(inx)
            maskInfo = self.find_maskinfo_list_by_name(regInfo.Src)
            if maskInfo is None :
                continue
            maskInfo = maskInfo[0]
            if maskInfo.Phase == srcPhase :
                return inx
        return -1
    def get_segmentinfo_count(self) -> int :
        return len(self.m_listSegmentInfo)
    def get_segmentinfo(self, inx : int) -> CSegmentInfo :
        return self.m_listSegmentInfo[inx]
    def get_centerlineinfo_count(self) -> int :
        return len(self.m_listCenterlineInfo)
    def get_centerlineinfo(self, inx : int) -> CCenterlineInfo :
        return self.m_listCenterlineInfo[inx]
    def find_centerlineinfo_by_type(self, type : str) -> CCenterlineInfo :
        iCenterlineInfoCnt = self.get_centerlineinfo_count()
        for inx in range(0, iCenterlineInfoCnt) :
            centerlineInfo = self.get_centerlineinfo(inx)
            if centerlineInfo.CenterlineType == type :
                return centerlineInfo
        return None
    def get_mesh_healing_count(self) -> int :
        if self.m_meshHealing is None :
            return 0
        else :
            return len(self.m_meshHealing)
    def get_mesh_healing(self, inx : int) -> str :
        return self.m_meshHealing[inx]
    def get_mesh_boolean_count(self) -> int :
        return len(self.m_listMeshBoolean)
    def get_mesh_boolean(self, inx : int) -> CMeshBoolean :
        return self.m_listMeshBoolean[inx]
    
    def get_metricinfo_count(self) -> int :
        return len(self.m_listMetricInfo)
    def get_metricinfo(self, inx : int) -> CMetricInfo :
        return self.m_listMetricInfo[inx]
    
    def is_rigid_reg_by_phase(self, phaseName : str) -> bool :
        if self.m_registrationInfo is None :
            return False
        
        regInfoCnt = self.get_reginfo_count()
        for inx in range(0, regInfoCnt) :
            regInfo = self.get_reginfo(inx)
            srcMaskName = regInfo.Src

            retList = self.find_maskinfo_list_by_name(srcMaskName)
            if retList is None :
                continue

            maskInfo = retList[0]
            if maskInfo.Phase == phaseName and regInfo.RigidAABB > 0 :
                return True
        return False
    

    # override
    def _init_recon_param(self) :
        pass
    def _init_centerline_param(self) :
        if self.m_centerlineParamList is None :
            return
        for centerlineType, value in self.m_centerlineParamList.items() :
            centerlineParam = CCenterlineParam()
            centerlineParam.Type = centerlineType
            centerlineParam.AdvancementRatio = value["advancementRatio"]
            centerlineParam.ResamplingLength = value["resamplingLength"]
            centerlineParam.SmoothingIter = value["smoothingIter"]
            centerlineParam.SmoothingFactor = value["smoothingFactor"]
            self.m_listCenterlineParam.append(centerlineParam)
    def _init_mask_info(self) :
        pass
    def _init_registration_info(self) :
        if self.m_registrationInfo is None :
            return
        for regInfo in self.m_registrationInfo :
            regInfoInst = CRegistrationInfo()
            regInfoInst.Target = regInfo["Target"]
            regInfoInst.Src = regInfo["Src"]
            regInfoInst.RigidAABB = regInfo["RigidAABB"]
            self.m_listRegistrationInfo.append(regInfoInst)
    def _init_segment_info(self) :
        if self.m_segmentInfo is None :
            return
        for segInfo in self.m_segmentInfo :
            organ = segInfo["organ"]
            _type = ""
            if "type" in segInfo :
                _type = segInfo["type"]
            for vesselInfo in segInfo["vesselInfo"] :
                wholeVessel = vesselInfo["wholeVessel"]
                childVesselStart = vesselInfo["childVessel"][0]
                childVesselEnd = vesselInfo["childVessel"][1]
                if "dilationIter" in vesselInfo :    
                    dilationIter = vesselInfo["dilationIter"]
                else :
                    dilationIter = 1
                if "noiseSegCnt" in vesselInfo :
                    noiseSegCnt = vesselInfo["noiseSegCnt"]
                else :
                    noiseSegCnt = 27

                segInfoInst = CSegmentInfo()
                segInfoInst.Type = _type
                segInfoInst.Organ = organ
                segInfoInst.add_vesselinfo(wholeVessel, childVesselStart, childVesselEnd, dilationIter, noiseSegCnt)
                self.m_listSegmentInfo.append(segInfoInst)
    def _init_centerline_info(self) :
        if self.m_centerlineInfo is None :
            return
        for centerlineInfo in self.m_centerlineInfo :
            centerlineInfoInst = CCenterlineInfo()
            centerlineInfoInst.CenterlineType = centerlineInfo["centerlineType"]
            centerlineInfoInst.InputKey = centerlineInfo["inputKey"]
            centerlineInfoInst.TreeRootKey = centerlineInfo["treeRootKey"]
            centerlineInfoInst.OutputName = centerlineInfo["outputName"]
            centerlineInfoInst.Input = centerlineInfo["input"]
            centerlineInfoInst.FindCell = centerlineInfo["findCell"]
            centerlineInfoInst.TreeRoot = centerlineInfo["treeRoot"]
            self.m_listCenterlineInfo.append(centerlineInfoInst)
    def _init_mesh_boolean(self) :
        if self.m_meshBoolean is None :
            return
        for meshBoolean in self.m_meshBoolean :
            meshBooleanInst = CMeshBoolean()
            meshBooleanInst.Operator = meshBoolean["operator"]
            meshBooleanInst.BlenderName0 = meshBoolean["blenderName0"]
            meshBooleanInst.BlenderName1 = meshBoolean["blenderName1"]
            meshBooleanInst.FillHole = meshBoolean["fillHole"]
            meshBooleanInst.BlenderName = meshBoolean["blenderName"]
            self.m_listMeshBoolean.append(meshBooleanInst)
    def _init_metric_info(self) :
        if self.m_metricInfo is None :
            return
        for metricInfo in self.m_metricInfo :
            type = metricInfo["type"]
            if type == "CrossCheck" :
                param0 = metricInfo["anchorMaskName"]
                param1 = metricInfo["targetMaskName"]
                metricInfoInst = CMetricInfo()
                metricInfoInst.Type = type
                metricInfoInst.add_param(param0)
                metricInfoInst.add_param(param1)
                self.m_listMetricInfo.append(metricInfoInst)

    @property
    def Ready(self) -> bool :
        return self.m_bReady
    @property
    def DataRootPath(self) -> str :
        return self.m_dataRootPath
    @property
    def CL(self) -> str :
        return self.m_cl
    @property
    def BlenderExe(self) -> str :
        return self.m_blenderExe
class COptionInfoSingle(COptionInfo) :
    def __init__(self, jsonPath):
        super().__init__(jsonPath)
        # input your code
    def clear(self) :
        # input your code
        super().clear()
    
    # override
    def _init_recon_param(self) :
        for reconType, value in self.m_reconParamList.items() :
            reconParam = CReconParamSingle()
            reconParam.Type = reconType
            reconParam.Contour = value["contour"]
            reconParam.Param = value["param"]
            reconParam.Gaussian = value["gaussian"]
            reconParam.Algorithm = value["algorithm"]
            reconParam.ResamplingFactor = value["resampling factor"]
            self.m_listReconParam.append(reconParam)
    def _init_mask_info(self) :
        for maskInfo in self.m_maskInfo :
            maskInfoInst = CMaskInfo()
            maskInfoInst.Name = maskInfo["name"]
            maskInfoInst.Phase = maskInfo["phase"]
            maskInfoInst.ReconType = maskInfo["reconType"]
            maskInfoInst.StrictureMode = maskInfo["strictureMode"]
            maskInfoInst.BlenderName = maskInfo["blenderName"]
            self.m_listMaskInfo.append(maskInfoInst)
class COptionInfoRange(COptionInfo) :
    def __init__(self, jsonPath):
        super().__init__(jsonPath)
        # input your code
    def clear(self) :
        # input your code
        super().clear()

    # override
    def _init_recon_param(self) :
        for reconType, value in self.m_reconParamList.items() :
            algorithm = value["algorithm"]
            reconParam = None
            if algorithm == "MarchingSharpness" or algorithm == "MarchingSharpnessPro" :
                reconParam = CReconParamRangeSharpness()
                reconParam.Type = reconType
                reconParam.Contour = value["contour"]
                reconParam.Iter = value["iter"]
                reconParam.DeciRange = value["deciRange"]
                reconParam.SharpnessAngleRange = value["sharpnessAngleRange"]
                reconParam.SharpnessNormalAngleRange = value["sharpnessNormalAngleRange"]
                reconParam.Algorithm = value["algorithm"]
            else :
                reconParam = CReconParamRange()
                reconParam.Type = reconType
                reconParam.Contour = value["contour"]
                reconParam.Iter = value["iter"]
                reconParam.RelaxRange = value["relaxRange"]
                reconParam.DeciRange = value["deciRange"]
                reconParam.Gaussian = value["gaussian"]
                reconParam.Algorithm = value["algorithm"]
                reconParam.ResamplingFactor = value["resampling factor"]
            self.m_listReconParam.append(reconParam)
    def _init_mask_info(self) :
        for maskInfo in self.m_maskInfo :
            maskInfoInst = CMaskInfoRange()
            maskInfoInst.Name = maskInfo["name"]
            maskInfoInst.Phase = maskInfo["phase"]
            maskInfoInst.ReconType = maskInfo["reconType"]
            maskInfoInst.StrictureMode = maskInfo["strictureMode"]
            maskInfoInst.BlenderName = maskInfo["blenderName"]
            maskInfoInst.BlenderOption = maskInfo["blenderOption"]
            self.m_listMaskInfo.append(maskInfoInst)




class CCLDataInfo :
    def __init__(self) :
        self.m_optionFullPath = ""
        self.m_patientPath = ""
        self.m_patientID = ""
        self.m_list = []
    def clear(self) :  
        self.m_optionFullPath = ""
        self.m_patientPath = ""
        self.m_patientID = ""
        self.m_list.clear()

    def add_info(self, clInfo : CCenterlineInfo, clParam : CCenterlineParam, reconParam : CReconParamSingle) :
        if clInfo is not None :
            self.m_list.append((copy.deepcopy(clInfo), copy.deepcopy(clParam), copy.deepcopy(reconParam)))
        else :
            self.m_list.append((None, None, None))
    def get_info_count(self) -> int :
        return len(self.m_list)
    def get_clinfo(self, inx : int) -> CCenterlineInfo :
        return self.m_list[inx][0]
    def get_clparam(self, inx : int) -> CCenterlineParam :
        return self.m_list[inx][1]
    def get_reconparam(self, inx : int) -> CReconParamSingle :
        return self.m_list[inx][2]


    @property
    def OptionFullPath(self) -> str :
        return self.m_optionFullPath
    @OptionFullPath.setter
    def OptionFullPath(self, optionFullPath : str) :
        self.m_optionFullPath = optionFullPath
    @property
    def PatientPath(self) -> str :
        return self.m_patientPath
    @PatientPath.setter
    def PatientPath(self, patientPath : str) :
        self.m_patientPath = patientPath
        self.m_patientID = os.path.basename(patientPath)
    @property
    def PatientID(self) -> str :
        return self.m_patientID



if __name__ == '__main__' :
    pass


# print ("ok ..")

