import sys
import os
import numpy as np
import json

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
solutionPath = os.path.dirname(fileAbsPath)
sys.path.append(fileAbsPath)
sys.path.append(solutionPath)

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage

import optionInfo as optionInfo
import multiProcessTask as multiProcessTask



class CNiftiInfo :
    def __init__(self, maskInfo : optionInfo.CMaskInfo) -> None:
        self.m_maskInfo = maskInfo

        self.m_maskCC = 0.0
        self.m_vertex = None
        self.m_fullPath = ""
        self.m_bValid = False
    def clear(self) :
        self.m_maskInfo = None

        self.m_maskCC = 0.0
        self.m_vertex = None
        self.m_fullPath = ""
        self.m_bValid = False

    @property
    def MaskInfo(self) -> optionInfo.CMaskInfo :
        return self.m_maskInfo
    @property
    def MaskCC(self) -> float :
        return self.m_maskCC
    @MaskCC.setter
    def MaskCC(self, maskCC : float) :
        self.m_maskCC = maskCC
    @property
    def Vertex(self) -> np.ndarray :
        return self.m_vertex
    @Vertex.setter
    def Vertex(self, vertex : np.ndarray) :
        self.m_vertex = vertex
    @property
    def FullPath(self) -> str :
        return self.m_fullPath
    @FullPath.setter
    def FullPath(self, fullPath : str) :
        self.m_fullPath = fullPath
    @property
    def Valid(self) -> bool :
        return self.m_bValid
    @Valid.setter
    def Valid(self, bValid : bool) :
        self.m_bValid = bValid

class CPhaseInfo() :
    def __init__(self) -> None :
        self.m_phase = ""
        self.m_origin = None
        self.m_spacing = None
        self.m_direction = None
        self.m_size = None
        self.m_offset = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0])
    def clear(self) :
        self.m_phase = ""
        self.m_origin = None
        self.m_spacing = None
        self.m_direction = None
        self.m_size = None
        self.m_offset = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0])
    
    def is_valid(self) -> bool :
        if self.m_origin is None :
            return False
        else :
            return True

    @property
    def Phase(self) -> str :
        return self.m_phase
    @Phase.setter
    def Phase(self, phase : str) :
        self.m_phase = phase
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
    def Offset(self) -> np.ndarray :
        return self.m_offset
    @Offset.setter
    def Offset(self, offset : np.ndarray) :
        self.m_offset = offset        


class CNiftiContainer() :
    def __init__(self) -> None:
        # input your code 
        self.m_inputPath = ""
        self.m_inputOptionInfo = None
        self.m_listNiftiInfo = []
        self.m_listPhaseInfo = []
    def clear(self) :
        # input your code
        for phaseInfo in self.m_listPhaseInfo :
            phaseInfo.clear()
        self.m_listPhaseInfo.clear()

        for niftiInfo in self.m_listNiftiInfo :
            niftiInfo.clear()
        self.m_listNiftiInfo.clear()

        self.m_inputPath = ""
        self.m_inputOptionInfo = None
    def process(self) :
        if self.InputPath == "" :
            #print("niftiContainer : not setting input path")
            return 
        if self.InputOptionInfo is None :
            #print("niftiContainer : not setting input option info")
            return 

        listTmp = []
        iMaskCnt = self.InputOptionInfo.get_maskinfo_count()
        if iMaskCnt == 0 :
            #print("not found mask info")
            return

        for inx in range(0, iMaskCnt) :
            maskInfo = self.InputOptionInfo.get_maskinfo(inx)
            niftiInfo = CNiftiInfo(maskInfo)
            niftiInfo.FullPath = os.path.join(self.InputPath, f"{maskInfo.Name}.nii.gz")
            
            if os.path.exists(niftiInfo.FullPath) == True :
                niftiInfo.Valid = True
            else :
                niftiInfo.Valid = False
                #print(f"not found {niftiInfo.MaskInfo.Name}")

            self.m_listNiftiInfo.append(niftiInfo)
            listTmp.append(niftiInfo.MaskInfo.Phase)

        # phase info
        listPhase = list(set(listTmp))
        for phase in listPhase :
            phaseInfo = CPhaseInfo()
            phaseInfo.Phase = phase
            self.m_listPhaseInfo.append(phaseInfo)

            listNiftiInfo = self.find_nifti_info_list_by_phase(phase)
            if len(listNiftiInfo) == 0 :
                #print(f"not found phaseInfo : {phaseInfo.Phase}")
                continue

            bCheck = False
            for niftiInfo in listNiftiInfo :
                if niftiInfo.Valid == True :
                    niftiFullPath = niftiInfo.FullPath
                    npImg, origin, spacing, direction, size = algImage.CAlgImage.get_np_from_nifti(niftiFullPath)
                    phaseInfo.Origin = origin
                    phaseInfo.Spacing = spacing
                    phaseInfo.Direction = direction
                    phaseInfo.Size = size
                    #print(f"setting phaseInfo : {phaseInfo.Phase} --> {phaseInfo.Origin}, {phaseInfo.Spacing}, {phaseInfo.Direction}, {phaseInfo.Size}")
                    bCheck = True
                    break
            if bCheck == False :
                #print(f"not found phaseInfo : {phaseInfo.Phase}")
                pass


    def get_nifti_info_count(self) -> int :
        return len(self.m_listNiftiInfo)
    def get_nifti_info(self, inx : int) -> CNiftiInfo :
        return self.m_listNiftiInfo[inx]
    def find_nifti_info_list_by_name(self, maskName : str) -> list :
        retList = []
        for niftiInfo in self.m_listNiftiInfo :
            if niftiInfo.MaskInfo.Name == maskName :
                retList.append(niftiInfo)
        if len(retList) == 0 :
            return None
        return retList
    def find_nifti_info_list_by_phase(self, phase : str) -> list :
        retList = []
        for niftiInfo in self.m_listNiftiInfo :
            if niftiInfo.MaskInfo.Phase == phase :
                retList.append(niftiInfo)
        if len(retList) == 0 :
            return None
        return retList
    def find_nifti_info_list_by_stricture_mode(self, strictureMode : int) -> list :
        retList = []
        for niftiInfo in self.m_listNiftiInfo :
            if niftiInfo.MaskInfo.StrictureMode == strictureMode :
                retList.append(niftiInfo)
        if len(retList) == 0 :
            return None
        return retList
    def find_nifti_info_by_blender_name(self, blenderName : str) -> CNiftiInfo :
        for niftiInfo in self.m_listNiftiInfo :
            if niftiInfo.MaskInfo.BlenderName == blenderName :
                return niftiInfo
        return None

    def get_phase_info_count(self) -> int :
        return len(self.m_listPhaseInfo)
    def get_phase_info(self, inx : int) -> CPhaseInfo :
        return self.m_listPhaseInfo[inx]
    def find_phase_info(self, phase : str) -> CPhaseInfo :
        for phaseInfo in self.m_listPhaseInfo :
            if phaseInfo.Phase == phase :
                return phaseInfo
        return None
    

    # protected


    @property
    def InputPath(self) -> str :
        return self.m_inputPath
    @InputPath.setter
    def InputPath(self, inputPath : str) :
        self.m_inputPath = inputPath
    @property
    def InputOptionInfo(self) -> optionInfo.COptionInfo :
        return self.m_inputOptionInfo
    @InputOptionInfo.setter
    def InputOptionInfo(self, optionInfo : optionInfo.COptionInfo) :
        self.m_inputOptionInfo = optionInfo
    @property
    def ListNiftiInfo(self) -> list :
        return self.m_listNiftiInfo
    @property
    def ListPhaseInfo(self) -> list :
        return self.m_listPhaseInfo
    

class CNiftiContainerTerritory(CNiftiContainer) : 
    def __init__(self):
        super().__init__()
        # input your code
    def clear(self) :
        # input your code
        super().clear()
    def process(self) :
        if self.InputPath == "" :
            #print("niftiContainer : not setting input path")
            return 
        if self.InputOptionInfo is None :
            #print("niftiContainer : not setting input option info")
            return 
        super().process()
        # input your code
        
        iSegInfoCnt = self.InputOptionInfo.get_segmentinfo_count()
        for inx in range(0, iSegInfoCnt) :
            segInfo = self.InputOptionInfo.get_segmentinfo(inx)
            self._process_segment_info(segInfo)
            


    def _process_segment_info(self, segInfo : optionInfo.CSegmentInfo) -> bool :
        organName = segInfo.Organ
        organMaskInfo = self.InputOptionInfo.find_maskinfo_list_by_name(organName)
        if organMaskInfo is None :
            #print(f"not found organ : {organName}")
            return
        organMaskInfo = organMaskInfo[0]

        vesselInfoCnt = segInfo.get_vesselinfo_count()
        for inx in range(0, vesselInfoCnt) :
            wholeVesselName = segInfo.get_vesselinfo_whole_vessel(inx)
            childStartInx = segInfo.get_vesselinfo_child_start(inx)
            childEndInx = segInfo.get_vesselinfo_child_end(inx)
            wholeVesselMaskInfo = self.InputOptionInfo.find_maskinfo_list_by_name(wholeVesselName)
            if wholeVesselMaskInfo is None :
                #print(f"not found whole vessel : {wholeVesselName}")
                continue
            wholeVesselMaskInfo = wholeVesselMaskInfo[0]

            for childInx in range(childStartInx, childEndInx + 1) :
                # vessel segment 
                vesselName = f"{wholeVesselName}{childInx}"
                phase = wholeVesselMaskInfo.Phase
                reconType = wholeVesselMaskInfo.ReconType
                strictureMode = wholeVesselMaskInfo.StrictureMode
                vesselBlenderName = wholeVesselMaskInfo.BlenderName

                maskInfo = optionInfo.CMaskInfo()
                maskInfo.Name = vesselName
                maskInfo.Phase = phase
                maskInfo.ReconType = reconType
                maskInfo.StrictureMode = strictureMode
                maskInfo.BlenderName = vesselName
                self.InputOptionInfo.m_listMaskInfo.append(maskInfo)
                
                niftiInfo = CNiftiInfo(maskInfo)
                niftiInfo.FullPath = os.path.join(self.InputPath, f"{maskInfo.Name}.nii.gz")
                
                if os.path.exists(niftiInfo.FullPath) == True :
                    niftiInfo.Valid = True
                else :
                    niftiInfo.Valid = False
                    #print(f"not found {niftiInfo.MaskInfo.Name}")
                self.m_listNiftiInfo.append(niftiInfo)

                # organ name
                name = f"{organName}_{vesselName}"
                phase = organMaskInfo.Phase
                reconType = organMaskInfo.ReconType
                strictureMode = organMaskInfo.StrictureMode
                blenderName = name
                # blenderName = f"{blenderName}_{vesselBlenderName}"

                maskInfo = optionInfo.CMaskInfo()
                maskInfo.Name = name
                maskInfo.Phase = phase
                maskInfo.ReconType = reconType
                maskInfo.StrictureMode = strictureMode
                maskInfo.BlenderName = blenderName
                self.InputOptionInfo.m_listMaskInfo.append(maskInfo)

                niftiInfo = CNiftiInfo(maskInfo)
                niftiInfo.FullPath = os.path.join(self.InputPath, f"{name}.nii.gz")
                self.m_listNiftiInfo.append(niftiInfo) 
        return True



class CNiftiContainerRange(multiProcessTask.CMultiProcessTask) :
    def __init__(self) -> None:
        super().__init__()
        # input your code 
        self.m_inputPath = ""
        self.m_inputOptionInfo = None

        self.m_niftiContainer = CNiftiContainer()
    def clear(self) :
        # input your code
        self.m_niftiContainer.clear()
        self.m_niftiContainer = None

        self.m_inputPath = ""
        self.m_inputOptionInfo = None

        super().clear()
    def process(self) :
        if self.InputPath == "" :
            #print("niftiContainer : not setting input path")
            return 
        if self.InputOptionInfo is None :
            #print("niftiContainer : not setting input option info")
            return 
        
        self.m_niftiContainer.InputPath = self.InputPath
        self.m_niftiContainer.InputOptionInfo = self.InputOptionInfo

        listTmp = []
        iMaskCnt = self.InputOptionInfo.get_maskinfo_count()
        if iMaskCnt == 0 :
            #print("niftiContainer : not found mask info")
            return
        
        for inx in range(0, iMaskCnt) :
            maskInfo = self.InputOptionInfo.get_maskinfo(inx)
            niftiInfo = CNiftiInfo(maskInfo)
            niftiInfo.FullPath = os.path.join(self.InputPath, f"{niftiInfo.MaskInfo.Name}.nii.gz")

            if os.path.exists(niftiInfo.FullPath) == True :
                niftiInfo.Valid = True
            else :
                niftiInfo.Valid = False
                #print(f"not found {niftiInfo.MaskInfo.Name}")
            
            self.OutputNiftiContainer.ListNiftiInfo.append(niftiInfo)
            listTmp.append(niftiInfo.MaskInfo.Phase)
        
        listPhase = list(set(listTmp))
        for phase in listPhase :
            phaseInfo = CPhaseInfo()
            phaseInfo.Phase = phase
            self.OutputNiftiContainer.ListPhaseInfo.append(phaseInfo)

            listNiftiInfo = self.OutputNiftiContainer.find_nifti_info_list_by_phase(phase)
            if len(listNiftiInfo) == 0 :
                #print(f"not found phaseInfo : {phaseInfo.Phase}")
                continue

            bCheck = False
            for niftiInfo in listNiftiInfo :
                if niftiInfo.Valid == True :
                    niftiFullPath = niftiInfo.FullPath
                    npImg, origin, spacing, direction, size = algImage.CAlgImage.get_np_from_nifti(niftiFullPath)
                    phaseInfo.Origin = origin
                    phaseInfo.Spacing = spacing
                    phaseInfo.Direction = direction
                    phaseInfo.Size = size
                    #print(f"setting phaseInfo : {phaseInfo.Phase} --> {phaseInfo.Origin}, {phaseInfo.Spacing}, {phaseInfo.Direction}, {phaseInfo.Size}")
                    bCheck = True
                    break
            if bCheck == False :
                #print(f"not found phaseInfo : {phaseInfo.Phase}")
                pass
        
        listParam = []
        paramCnt = 0
        for targetInx, niftiInfo in enumerate(self.OutputNiftiContainer.ListNiftiInfo) :
            niftiFullPath = niftiInfo.FullPath
            if niftiInfo.Valid == True :
                listParam.append((paramCnt, niftiFullPath))
                self.add_target_index(targetInx)
                paramCnt += 1
            else :
                pass
                #print(f"not found {niftiFullPath}")
        
        if paramCnt == 0 :
            #print("not existing nifti files")
            return
        
        self._alloc_shared_list(self.get_target_index_count())
        super().process(self._task, listParam)

        listNiftiInfo = self.get_shared_list()
        for inx, niftiInfo in enumerate(listNiftiInfo) :
            targetInx = self.get_target_index(inx)

            # [niftiVertex, cc]
            vertex = niftiInfo[0]
            maskCC = niftiInfo[1]

            niftiInfo = self.OutputNiftiContainer.get_nifti_info(targetInx)
            niftiInfo.Vertex = vertex
            niftiInfo.MaskCC = maskCC
        listNiftiInfo.clear()
    

    # protected
    def _task(self, param : tuple) :
        inx = param[0]
        niftiFullPath = param[1]
        
        npImg, origin, spacing, direction, size = algImage.CAlgImage.get_np_from_nifti(niftiFullPath)
        vertex = algImage.CAlgImage.get_vertex_from_np(npImg, np.int32)
        maskCC = algImage.CAlgImage.get_cc(npImg, spacing)
        self.m_sharedList[inx] = [vertex, maskCC]
        #print(f"loaded nifti {niftiFullPath}")


    @property
    def InputPath(self) -> str :
        return self.m_inputPath
    @InputPath.setter
    def InputPath(self, inputPath : str) :
        self.m_inputPath = inputPath
    @property
    def InputOptionInfo(self) -> optionInfo.COptionInfo :
        return self.m_inputOptionInfo
    @InputOptionInfo.setter
    def InputOptionInfo(self, optionInfo : optionInfo.COptionInfo) :
        self.m_inputOptionInfo = optionInfo
    @property
    def OutputNiftiContainer(self) -> CNiftiContainer :
        return self.m_niftiContainer




class CFileSavePhaseInfo :
    def __init__(self):
        self.m_inputNiftiContainer = None
        self.m_outputSavePath = ""
        self.m_outputFileName = ""
    def clear(self) :
        self.m_inputNiftiContainer = None
        self.m_outputSavePath = ""
        self.m_outputFileName = ""
    def process(self) :
        if self.InputNiftiContainer is None :
            #print("file save phaseInfo : not setting niftiContainer")
            return
         
        iPhaseCnt = self.InputNiftiContainer.get_phase_info_count()
        if iPhaseCnt == 0 :
            #print("file save phaseInfo : nonexistent phase")
            return
        
        if os.path.exists(self.OutputSavePath) == False :
            os.makedirs(self.OutputSavePath)
        
        retList = []
        for i in range(0, iPhaseCnt) :
            dicEle = {}
            phaseInfo = self.InputNiftiContainer.get_phase_info(i)
            dicEle["Phase"] = phaseInfo.Phase
            dicEle["Origin"] = phaseInfo.Origin
            dicEle["Spacing"] = phaseInfo.Spacing
            dicEle["Direction"] = phaseInfo.Direction
            dicEle["Size"] = phaseInfo.Size
            dicEle["Offset"] = [float(phaseInfo.Offset[0, 0]), float(phaseInfo.Offset[0, 1]), float(phaseInfo.Offset[0, 2])]
            retList.append(dicEle)

        jsonFullPath = os.path.join(self.OutputSavePath, f"{self.OutputFileName}.json")
        with open(jsonFullPath, "w", encoding="utf-8") as fp:
            json.dump(retList, fp, ensure_ascii=False, indent=4)
        #print(f"file save phaseInfo : completed save {self.OutputFileName}")
        


    @property
    def InputNiftiContainer(self) -> CNiftiContainer :
        return self.m_inputNiftiContainer
    @InputNiftiContainer.setter
    def InputNiftiContainer(self, inputNiftiContainer : CNiftiContainer) :
        self.m_inputNiftiContainer = inputNiftiContainer
    @property
    def OutputSavePath(self) -> str :
        return self.m_outputSavePath
    @OutputSavePath.setter
    def OutputSavePath(self, outputSavePath : str) :
        self.m_outputSavePath = outputSavePath
    @property
    def OutputFileName(self) -> str :
        return self.m_outputFileName
    @OutputFileName.setter
    def OutputFileName(self, outputFileName : str) :
        self.m_outputFileName = outputFileName


class CFileLoadPhaseInfo :
    def __init__(self):
        self.m_inputNiftiContainer = None
        self.m_inputPath = ""
        self.m_inputFileName = ""
    def clear(self) :
        self.m_inputNiftiContainer = None
        self.m_inputPath = ""
        self.m_inputFileName = ""
    def process(self) :
        if self.InputNiftiContainer is None :
            #print("file load phaseInfo : not setting niftiContainer")
            return
        if self.InputPath == "" :
            #print("file load phaseInfo : not setting input path")
            return
        if self.InputFileName == "" :
            #print("file load phaseInfo : not setting input filename")
            return
        
        jsonFullPath = os.path.join(self.InputPath, f"{self.InputFileName}.json")
        if os.path.exists(jsonFullPath) == False :
            #print(f"file load phaseInfo : not found {jsonFullPath}")
            return
        
        jsonData = None
        with open(jsonFullPath, 'r') as fp :
            jsonData = json.load(fp)
        
        for phaseInfo in jsonData :
            phase = phaseInfo["Phase"]
            origin = phaseInfo["Origin"]
            spacing = phaseInfo["Spacing"]
            direction = phaseInfo["Direction"]
            size = phaseInfo["Size"]
            offset = phaseInfo["Offset"]

            phaseInfo = self.InputNiftiContainer.find_phase_info(phase)
            if phaseInfo is None :
                phaseInfo = CPhaseInfo()
                self.InputNiftiContainer.ListPhaseInfo.append(phaseInfo)
            phaseInfo.Phase = phase
            phaseInfo.Origin = origin
            phaseInfo.Spacing = spacing
            phaseInfo.Direction = direction
            phaseInfo.Size = size
            phaseInfo.Offset = algLinearMath.CScoMath.to_vec3([offset[0], offset[1], offset[2]])
            
        #print(f"file load phaseInfo : completed loading {self.InputFileName}")
        


    @property
    def InputNiftiContainer(self) -> CNiftiContainer :
        return self.m_inputNiftiContainer
    @InputNiftiContainer.setter
    def InputNiftiContainer(self, inputNiftiContainer : CNiftiContainer) :
        self.m_inputNiftiContainer = inputNiftiContainer
    @property
    def InputPath(self) -> str :
        return self.m_inputPath
    @InputPath.setter
    def InputPath(self, inputPath : str) :
        self.m_inputPath = inputPath
    @property
    def InputFileName(self) -> str :
        return self.m_inputFileName
    @InputFileName.setter
    def InputFileName(self, inputFileName : str) :
        self.m_inputFileName = inputFileName


class CPhaseInfoContainer :
    def __init__(self):
        self.m_inputFullPath = ""

        self.m_dicPhaseInfo = {}
    def clear(self) :
        self.m_inputFullPath = ""

        for phase, phaseInfo in self.m_dicPhaseInfo.items() :
            phaseInfo.clear()
        self.m_dicPhaseInfo.clear()
    def process(self) :
        jsonFullPath = self.InputFullPath
        if os.path.exists(jsonFullPath) == False :
            #print(f"file load phaseInfo : not found {jsonFullPath}")
            return
        
        jsonData = None
        with open(jsonFullPath, 'r') as fp :
            jsonData = json.load(fp)
        
        for phaseInfo in jsonData :
            phase = phaseInfo["Phase"]
            origin = phaseInfo["Origin"]
            spacing = phaseInfo["Spacing"]
            direction = phaseInfo["Direction"]
            size = phaseInfo["Size"]
            offset = phaseInfo["Offset"]

            phaseInfoInst = CPhaseInfo()
            phaseInfoInst.Phase = phase
            phaseInfoInst.Origin = origin
            phaseInfoInst.Spacing = spacing
            phaseInfoInst.Direction = direction
            phaseInfoInst.Size = size
            phaseInfoInst.Offset = algLinearMath.CScoMath.to_vec3([offset[0], offset[1], offset[2]])
            self.m_dicPhaseInfo[phase] = phaseInfoInst

    def find_phaseinfo(self, phase : str) -> CPhaseInfo :
        if phase in self.m_dicPhaseInfo :
            return self.m_dicPhaseInfo[phase]
        return None
    def get_phaseinfo_count(self) -> int :
        return len(self.m_dicPhaseInfo)


    @property
    def InputFullPath(self) -> str :
        return self.m_inputFullPath
    @InputFullPath.setter
    def InputFullPath(self, inputFullPath : str) :
        self.m_inputFullPath = inputFullPath





if __name__ == '__main__' :
    pass


# #print ("ok ..")

