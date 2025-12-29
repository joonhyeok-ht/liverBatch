import sys
import os
import numpy as np
import vtk

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileToolPath = os.path.dirname(fileAbsPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage

import vtkObj as vtkObj



'''
unsigned char mask image
'''
class CVTKObjMaskImage(vtkObj.CVTKObj) :
    @staticmethod
    def create_vtk_image(width : int, height : int) -> vtk.vtkImageData :
        vtkImage = vtk.vtkImageData()
        vtkImage.SetDimensions(width, height, 1)  # [X, Y, Z]
        vtkImage.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)

        # numpy 데이터를 VTK 이미지로 복사
        for y in range(0, height):
            for x in range(0, width):
                vtkImage.SetScalarComponentFromFloat(x, y, 0, 0, 0)  

        return vtkImage 
    @staticmethod
    def set_vtk_image(vtkImg : vtk.vtkImageData, npImg : np.ndarray, value : np.uint8) :
        inx = np.where(npImg > 0)
        coord = list(zip(inx[0], inx[1]))

        for tmp in coord :
            x = tmp[0]
            y = tmp[1]
            vtkImg.SetScalarComponentFromFloat(x, y, 0, 0, value)


    def __init__(self, width : int, height : int) -> None:
        super().__init__()
        # input your code
        self.m_width = width
        self.m_height = height
        self.m_vtkImg = CVTKObjMaskImage.create_vtk_image(width, height)
        self.m_npImg = None

        self.m_lookupTable = vtk.vtkLookupTable()
        self.m_lookupTable.SetNumberOfTableValues(256)
        self.m_lookupTable.SetRange(0, 255)

        self.m_mapper = vtk.vtkImageMapToColors()
        self.m_mapper.SetInputData(self.m_vtkImg)
        self.m_mapper.SetLookupTable(self.m_lookupTable)
        self.m_mapper.Update()

        self.m_actor = vtk.vtkImageActor()
        self.m_actor.GetMapper().SetInputConnection(self.m_mapper.GetOutputPort())
    def clear(self) :
        # input your code
        self.m_width = 0
        self.m_height = 0
        self.m_vtkImg = None
        self.m_lookupTable = None
        self.m_npImg = None
        super().clear()

    def clear_lookup_table_value(self, color : np.ndarray, alpha : float) :
        for inx in range(0, 256):
            self.m_lookupTable.SetTableValue(inx, color[0, 0], color[0, 1], color[0, 2], alpha)
    def add_lookup_table(self, inx : int, color : np.ndarray, alpha : float) :
        self.m_lookupTable.SetTableValue(inx, color[0, 0], color[0, 1], color[0, 2], alpha)
    def build_lookup_table(self) :
        self.m_lookupTable.Build()
    def set_np(self, npImg : np.ndarray, value : float) :
        self.m_npImg = npImg
        CVTKObjMaskImage.set_vtk_image(self.m_vtkImg, npImg, value)
        self.update()
    def clear_value(self, value : float) :
        # numpy 데이터를 VTK 이미지로 복사
        for y in range(0, self.m_height):
            for x in range(0, self.m_width):
                self.m_vtkImg.SetScalarComponentFromFloat(x, y, 0, 0, value)
        self.update()


    def update(self) :
        self.m_vtkImg.Modified()
        self.m_mapper.Update()


    
    @property
    def Width(self) -> int :
        return self.m_width
    @property
    def Height(self) -> int :
        return self.m_height
    @property
    def NpImg(self) -> np.ndarray :
        return self.m_npImg
    @property
    def VTKImg(self) -> vtk.vtkImageData :
        return self.m_vtkImg


if __name__ == '__main__' :
    pass


# print ("ok ..")

