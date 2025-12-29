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



class CVTKObjText(vtkObj.CVTKObj) :
    def __init__(self, activeCamera, pos : np.ndarray, text : str, scale : float = 1.0) -> None:
        super().__init__()
        # input your code
        self.m_text = text
        self.m_vectorText = vtk.vtkVectorText()
        self.m_vectorText.SetText(text)

        self.m_mapper = vtk.vtkPolyDataMapper()
        self.m_mapper.SetInputConnection(self.m_vectorText.GetOutputPort())

        self.m_actor = vtk.vtkFollower()
        self.m_actor.SetMapper(self.m_mapper)
        self.m_actor.SetScale(scale, scale, scale)
        self.m_actor.SetPosition(pos[0, 0] + 2.0, pos[0, 1], pos[0, 2])
        self.m_actor.SetCamera(activeCamera)
    def clear(self) :
        # input your code
        self.m_text = ""
        super().clear()

    
    @property
    def Text(self) -> str :
        return self.m_text
    @Text.setter
    def Text(self, text : str) :
        self.m_text = text
        self.m_vectorText.SetText(text)
        self.m_mapper.SetInputConnection(self.m_vectorText.GetOutputPort())



    





if __name__ == '__main__' :
    pass


# print ("ok ..")

