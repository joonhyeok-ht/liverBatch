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



class CPhaseInfo() :
    def __init__(self) :
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

class CPhase :
    def __init__(self) :
        self.m_listPhaseInfo = []
    def clear(self) :
        for phaseInfo in self.m_listPhaseInfo :
            phaseInfo.clear()
    
    def get_phaseinfo_count(self) -> int :
        return len(self.m_listPhaseInfo)
    def get_phaseinfo(self, inx : int) -> CPhaseInfo :
        if inx >= self.get_phaseinfo_count() : 
            return None
        return self.m_listPhaseInfo[inx]
    def add_phaseinfo(self, phaseinfo : CPhaseInfo) :
        self.m_listPhaseInfo.append(phaseinfo)
    def find_phaseinfo(self, phaseName : str) -> CPhaseInfo :
        for phaseInfo in self.m_listPhaseInfo :
            if phaseInfo.Phase == phaseName :
                return phaseInfo
        return None


class CFileSavePhaseInfo :
    def __init__(self):
        self.m_inputPhase = None
        self.m_outputSavePath = ""
        self.m_outputFileName = ""
    def clear(self) :
        self.m_inputPhase = None
        self.m_outputSavePath = ""
        self.m_outputFileName = ""
    def process(self) :
        if self.InputPhase is None :
            print("file save phaseInfo : not setting niftiContainer")
            return
         
        iPhaseCnt = self.InputPhase.get_phaseinfo_count()
        if iPhaseCnt == 0 :
            print("file save phaseInfo : nonexistent phase")
            return
        
        if os.path.exists(self.OutputSavePath) == False :
            os.makedirs(self.OutputSavePath)
        
        retList = []
        for i in range(0, iPhaseCnt) :
            dicEle = {}
            phaseinfo = self.InputPhase.get_phaseinfo(i)
            dicEle["Phase"] = phaseinfo.Phase
            dicEle["Origin"] = phaseinfo.Origin
            dicEle["Spacing"] = phaseinfo.Spacing
            dicEle["Direction"] = phaseinfo.Direction
            dicEle["Size"] = phaseinfo.Size
            dicEle["Offset"] = [float(phaseinfo.Offset[0, 0]), float(phaseinfo.Offset[0, 1]), float(phaseinfo.Offset[0, 2])]
            retList.append(dicEle)

        jsonFullPath = os.path.join(self.OutputSavePath, f"{self.OutputFileName}.json")
        with open(jsonFullPath, "w", encoding="utf-8") as fp:
            json.dump(retList, fp, ensure_ascii=False, indent=4)
        print(f"file save phaseInfo : completed save {self.OutputFileName}")
        

    @property
    def InputPhase(self) -> CPhase :
        return self.m_inputPhase
    @InputPhase.setter
    def InputPhase(self, inputPhase : CPhase) :
        self.m_inputPhase = inputPhase
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
    def __init__(self) :
        self.m_inputPath = ""
        self.m_inputFileName = ""
    def clear(self) :
        self.m_inputPath = ""
        self.m_inputFileName = ""
    def process(self) -> CPhase :
        if self.InputPath == "" :
            print("file load phaseInfo : not setting input path")
            return
        if self.InputFileName == "" :
            print("file load phaseInfo : not setting input filename")
            return
        
        jsonFullPath = os.path.join(self.InputPath, f"{self.InputFileName}.json")
        if os.path.exists(jsonFullPath) == False :
            print(f"file load phaseInfo : not found {jsonFullPath}")
            return
        
        jsonData = None
        with open(jsonFullPath, 'r', encoding="utf-8") as fp :
            jsonData = json.load(fp)
        
        phaseInst = CPhase()
        for phaseInfo in jsonData :
            phase = phaseInfo["Phase"]
            origin = phaseInfo["Origin"]
            spacing = phaseInfo["Spacing"]
            direction = phaseInfo["Direction"]
            size = phaseInfo["Size"]
            offset = phaseInfo["Offset"]

            phaseinfo = CPhaseInfo()
            phaseinfo.Phase = phase
            phaseinfo.Origin = origin
            phaseinfo.Spacing = spacing
            phaseinfo.Direction = direction
            phaseinfo.Size = size
            phaseinfo.Offset = algLinearMath.CScoMath.to_vec3([offset[0], offset[1], offset[2]])
            phaseInst.add_phaseinfo(phaseinfo)
            
        print(f"file load phaseInfo : completed loading {self.InputFileName}")
        return phaseInst


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



if __name__ == '__main__' :
    pass


# print ("ok ..")

