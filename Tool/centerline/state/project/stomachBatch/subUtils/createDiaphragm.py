'''
File : createDiaphragm.py
Version : 2024_08_29

origin from 'https://github.com/hutom-io/mi_opeartion_ray_service/blob/main/mask_to_blend_lib/utils/cover.py'
first modified by jys (24.05.21)
'''

import os
import numpy as np
import cv2
import SimpleITK as sitk


'''
Name
    - CCreateDiaphragm  
Input
    - "InputPath"        : the path including Skin or Abdominal nifti files
    - "OutputPath"        : the path for "Diaphragm.nii.gz"
Output
    - "Diaphragm.nii.gz in OutputPath
'''
class CCreateDiaphragm() :
    m_niftiDiaphragmName = "Diaphragm.nii.gz"
    
    TAG = "CCreateDiaphragm"
    def __init__(self) -> None :
        self.m_inputPath = ""  # Skin.nii.gz or Abdominal_wall.nii.gz folder path
        self.m_outputPath = ""  # Diaphragm.nii.gz folder path
        self.m_inputNiftiName = ""
        
    def clear(self) :
        self.m_inputPath = ""
        self.m_outputPath = ""
        self.m_inputNiftiName = ""

    def process(self) -> bool:
        if not os.path.exists(self.m_inputPath) :
            print(f"{self.TAG}-ERROR : {self.m_inputPath} is not exist.")
            return False
        
        if not os.path.exists(self.m_outputPath) :
            print(f"{self.TAG}-ERROR : {self.m_outputPath} is not exist.")
            return False
        
        input_nifti_path = os.path.join(self.m_inputPath, self.m_inputNiftiName)
        if not os.path.exists(input_nifti_path) :
            print(f"{self.TAG}-ERROR : {self.m_inputNiftiName} is not exist.")
            return False
        
        self.TopCover(self.m_inputPath, self.m_outputPath)
        
        #print(f"{self.TAG} : {self.m_niftiDiaphragmName} is created.")
        return True
        
    def findZ(self, array) -> int:
        for idx, arr in enumerate(reversed(array)):
            if np.any(np.array(arr) == 255):
                return idx

    def niftiLoader(self, path, returnImage=False):
        try:
            raw = sitk.ReadImage(path)
            gt = sitk.GetArrayFromImage(raw)
        except:
            raise True

        shape = gt.shape
        spacing = raw.GetSpacing()
        origin = raw.GetOrigin()
        direction = raw.GetDirection()

        if returnImage:
            return shape, spacing, origin, direction, gt
        else:
            return shape, spacing, origin, direction

    def niftiSave(self, path, array, spacing, origin, direction):
        result_image = sitk.GetImageFromArray(array)
        result_image.SetSpacing(spacing)
        result_image.SetOrigin(origin)
        result_image.SetDirection(direction)

        sitk.WriteImage(result_image, path)

    def TopCover(self, inputPath, outputPath):
        shape,spacing,origin,direction,imgArr = self.niftiLoader(os.path.join(inputPath,self.m_inputNiftiName), returnImage=True)
        
        zIndex=self.findZ(imgArr) + 1
        imgArr[0:-(zIndex)] = 0
        
        sliceData = imgArr[shape[0]-(zIndex)]
        contours, _ = cv2.findContours(sliceData, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(sliceData, contours, -1, 255, thickness=cv2.FILLED)
        imgArr[shape[0]-(zIndex)] = sliceData
        
        savePath = os.path.join(outputPath, self.m_niftiDiaphragmName)
        self.niftiSave(savePath, imgArr, spacing, origin, direction)
        # logger.info(f'TOP COVER  : {extractPath}/Diaphragm.nii.gz')
    
    @property
    def InputPath(self) :
        return self.m_inputPath
    @InputPath.setter
    def InputPath(self, inputPath : str) :
        self.m_inputPath = inputPath
    @property
    def OutputPath(self) :
        return self.m_outputPath
    @OutputPath.setter
    def OutputPath(self, outputPath : str) :
        self.m_outputPath = outputPath
    @property
    def InputNiftiName(self) :
        return self.m_inputNiftiName
    @InputNiftiName.setter
    def InputNiftiName(self, niftiInputName : str) :
        self.m_inputNiftiName = niftiInputName

if __name__=='__main__' :
    
    createDiaphragm = CCreateDiaphragm()
    createDiaphragm.InputPath = "./" #"D:\\jys\\stomach_win\\data\\input\\01011ug_129\\01_DICOM\PP\\Mask"
    createDiaphragm.OutputPath = createDiaphragm.InputPath
    createDiaphragm.InputNiftiName = "Abdominal_wall_01014urk_11.nii.gz"
    createDiaphragm.process()