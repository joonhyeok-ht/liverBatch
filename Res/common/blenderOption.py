'''
'''

import os, sys
import json
import re


class COptionInfo :
    @staticmethod
    def generate_strings(input_str) :
        # 정규식을 사용하여 숫자 범위와 문자 부분 추출
        match = re.search(r'([a-zA-Z0-9_]+)\[(\d+),(\d+)\]', input_str)
        if match:
            prefix = match.group(1)  # 문자 부분 추출
            start = int(match.group(2))  # 시작 숫자
            end = int(match.group(3))    # 끝 숫자
            
            # 숫자 범위에 따른 문자열 생성
            result = [f"{prefix}{num}" for num in range(start, end + 1)]
            return result
        else:
            return None
        

    def __init__(self):
        self.m_jsonData = None
        self.m_dataRootPath = ""
        self.m_dicDecimation = {}
        self.m_dicDecimationByRatio = {}
        self.m_dicRemesh = {}
        self.m_listMeshCleanup = []
        self.m_listSamrtUV = []
    def process(self, fullPath : str) -> bool :
        if os.path.exists(fullPath) == False: 
            print(f"not valid Option_Path : {fullPath}")
            return False
        # json initialize 
        with open(fullPath, 'r') as fp :
            self.m_jsonData = json.load(fp)
        
        self.m_dataRootPath = self.m_jsonData["DataRootPath"]
        self.m_decimation = self.m_jsonData["Blender"]["Decimation"]
        self.m_decimationByRatio = self.m_jsonData["Blender"]["DecimationByRatio"]
        self.m_remesh = self.m_jsonData["Blender"]["Remesh"]
        self.m_meshCleanup = self.m_jsonData["Blender"]["MeshCleanUp"]
        self.m_smartUV = self.m_jsonData["Blender"]["SmartUV"]

        self.m_voxelSize = self.m_remesh["VoxelSize"]

        self._update_dictionary_type(self.m_dicDecimation, self.m_decimation)
        self._update_dictionary_type(self.m_dicDecimationByRatio, self.m_decimationByRatio)
        self._update_dictionary_type(self.m_dicRemesh, self.m_remesh["RemeshList"])
        self._update_list_type(self.m_listMeshCleanup, self.m_meshCleanup)
        self._update_list_type(self.m_listSamrtUV, self.m_smartUV)
        
        return True
    
    def _update_dictionary_type(self, outputDic : dict, srcDict : dict) :
        for key, value in srcDict.items() :
            listRet = COptionInfo.generate_strings(key)
            if listRet is None :
                outputDic[key] = value
            else :
                for subKey in listRet :
                    outputDic[subKey] = value
    def _update_list_type(self, outList : list, srcList : list) :
        for key in srcList :
            listRet = COptionInfo.generate_strings(key)
            if listRet is None :
                outList.append(key)
            else :
                for subKey in listRet :
                    outList.append(subKey)
    
    @property
    def DataRootPath(self) -> str :
        return self.m_dataRootPath
    @property
    def Decimation(self) -> dict :
        return self.m_dicDecimation
    @property
    def DecimationByRatio(self) -> dict :
        return self.m_dicDecimationByRatio
    @property
    def Remesh(self) -> dict :
        return self.m_dicRemesh
    @property
    def CleanUp(self) -> list :
        return self.m_listMeshCleanup
    @property
    def SmartUV(self) -> list :
        return self.m_listSamrtUV
    @property
    def VoxelSize(self) :
        return self.m_voxelSize


