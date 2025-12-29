import numpy as np
import matplotlib.pyplot as plt
import os, sys
import matplotlib.patches as patches
import json

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


'''
Name
    - GDOffsetBlock  (gradient descent offset)
Input
    - "InputSrcPath"        : the folder including src nifti files
    - "InputTargetPath"     : the folder including target nifti files
Output
    - "OutputOffset"        : offset in physical coord [X, Y, Z]
Property
    - "Active"
    - "AddSrcNiftiFile"        
    - "AddTargetNiftiFile"
'''

class CGDOffset :
    def __init__(self) -> None:
        self.m_inputSrcPath = ""
        self.m_inputTargetPath = ""
        self.m_outputOffset = []
        self.m_listSrcNiftiFile = []
        self.m_listTargetNiftiFile = []
    def clear(self) :
        self.m_inputSrcPath = ""
        self.m_inputTargetPath = ""
        self.m_outputOffset.clear()
        self.m_listSrcNiftiFile.clear()
        self.m_listTargetNiftiFile.clear()
    def process(self) :
        srcFullPath = self.__get_valid_nifti_full_path(self.InputSrcPath, self.m_listSrcNiftiFile)
        targetFullPath = self.__get_valid_nifti_full_path(self.InputTargetPath, self.m_listTargetNiftiFile)

        if srcFullPath == "" or targetFullPath == "":
            print("not found file")
            self.m_outputOffset.append(0.0)
            self.m_outputOffset.append(0.0)
            self.m_outputOffset.append(0.0)
            return
        
        regTransform = scoReg.CRegTransform()
        regTransform.process(srcFullPath, targetFullPath)
        diceScore = regTransform.DiceScore
        offsetX = regTransform.OffsetX
        offsetY = regTransform.OffsetY
        offsetZ = regTransform.OffsetZ
        matTargetPhy = regTransform.MatTargetPhy
        print(f"diceScore:{diceScore}, offsetX:{offsetX}, offsetY:{offsetY}, offsetZ:{offsetZ}")

        # target -> physical로 offset 변경 
        # src는 내부적으로 target으로 resampling 되기 때문에 offset은 target 기준이 된다. 
        matTargetPhy.set_translate(0, 0, 0)
        offsetV = scoMath.CScoVec3(offsetX, offsetY, offsetZ)
        phyOffsetV = scoMath.CScoMath.mul_mat4_vec3(matTargetPhy, offsetV)
        self.m_outputOffset.append(phyOffsetV.X)
        self.m_outputOffset.append(phyOffsetV.Y)
        self.m_outputOffset.append(phyOffsetV.Z)
    
    def add_src_nifti_file(self, niftiFile : str) :
        self.m_listSrcNiftiFile.append(niftiFile)
    def add_target_nifti_file(self, niftiFile : str) :
        self.m_listTargetNiftiFile.append(niftiFile)


    # private
    def __get_valid_nifti_full_path(self, path : str, listNiftiFile : list) :
        for niftiFile in listNiftiFile :
            fullPath = os.path.join(path, niftiFile)
            if os.path.exists(fullPath) == False :
                continue
            return fullPath
        return ""


    @property
    def InputSrcPath(self) :
        return self.m_inputSrcPath
    @InputSrcPath.setter
    def InputSrcPath(self, inputSrcPath : str) :
        self.m_inputSrcPath = inputSrcPath
    @property
    def InputTargetPath(self) :
        return self.m_inputTargetPath
    @InputTargetPath.setter
    def InputTargetPath(self, inputTargetPath : str) :
        self.m_inputTargetPath = inputTargetPath
    @property
    def OutputOffset(self) :
        return self.m_outputOffset
    @OutputOffset.setter
    def OutputOffset(self, outputOffset : str) :
        self.m_outputOffset = outputOffset



    
    

    






