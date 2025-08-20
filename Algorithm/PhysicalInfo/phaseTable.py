import numpy as np
import matplotlib.pyplot as plt
import os, sys
import matplotlib.patches as patches
import json

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))


class CPhaseTable :
    '''
    dicPhaseTable = {
        "PhaseName" : {
            "RegOffset" : [X, Y, Z]
            "NiftiList" : [
                ..
            ]
        }
        ..
    }
    '''
    def __init__(self) -> None:
        self.m_dicTable = {}
    def clear(self) :
        for phaseName, phaseInfo in self.m_dicTable.items() :
            phaseInfo["RegOffset"].clear()
            phaseInfo["NiftiList"].clear()
        self.m_dicTable.clear()
    
    def set_reg_offset(self, key : str, regOffset : list) :
        phaseInfo = self.__get_phase_info(key)
        phaseInfo["RegOffset"][0] = regOffset[0]
        phaseInfo["RegOffset"][1] = regOffset[1]
        phaseInfo["RegOffset"][2] = regOffset[2]
    def get_reg_offset(self, key : str) :
        if key in self.m_dicTable :
            return self.m_dicTable[key]["RegOffset"]
        return [0, 0, 0]
    def add_nitfi_file(self, key : str, niftiFile : str) :
        phaseInfo = self.__get_phase_info(key)
        phaseInfo["NiftiList"].append(niftiFile)
    def get_phase_name_from_nifti_file(self, niftiFile : str) :
        for phaseName, phaseInfo in self.m_dicTable.items() :
            if niftiFile in phaseInfo["NiftiList"] :
                return phaseName
        return ""

    def print(self) :
        print(self.m_dicTable)


    # private
    def __get_phase_info(self, key : str) :
        if key in self.m_dicTable :
            return self.m_dicTable[key]
        else :
            phaseInfo = {}
            phaseInfo["RegOffset"] = [0, 0, 0]
            phaseInfo["NiftiList"] = []
            self.m_dicTable[key] = phaseInfo
            return phaseInfo




    






