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


class CVTKObj() :
    def __init__(self) -> None:
        self.m_keyType = "interface"
        self.m_mapper = vtk.vtkPolyDataMapper()
        self.m_actor = vtk.vtkActor()
        self.m_actor.SetMapper(self.m_mapper)
        self.m_pos = None
        self.m_color = None
        self.m_bVisibility = True
        self.m_opacity = 1.0
    def clear(self) :
        self.m_keyType = "interface"
        self.m_mapper = None
        self.m_actor = None
        self.m_color = None
        self.m_pos = None
        self.m_bVisibility = True
        self.m_opacity = 1.0

    
    @property
    def Key(self) -> str :
        return self.Actor.GetObjectName()
    @Key.setter
    def Key(self, key : str) :
        self.Actor.SetObjectName(key)
    @property
    def KeyType(self) -> str :
        return self.m_keyType
    @KeyType.setter
    def KeyType(self, keyType : str) :
        self.m_keyType = keyType
    @property
    def Actor(self) -> vtk.vtkActor :
        return self.m_actor
    
    @property
    def Pos(self) -> np.ndarray :
        return self.m_pos
    @Pos.setter
    def Pos(self, pos : np.ndarray) :
        self.m_pos = pos.copy()
        self.Actor.SetPosition(pos[0, 0], pos[0, 1], pos[0, 2])
    @property
    def Color(self) -> np.ndarray :
        return self.m_color
    @Color.setter
    def Color(self, color : np.ndarray) :
        self.m_color = color.copy()
        self.Actor.GetProperty().SetColor(color[0, 0], color[0, 1], color[0, 2])
    @property
    def Visibility(self) -> bool :
        return self.m_bVisibility
    @Visibility.setter
    def Visibility(self, bVisibility : bool) :
        self.m_bVisibility = bVisibility
        self.Actor.SetVisibility(int(bVisibility))
    @property
    def Opacity(self) -> float :
        return self.m_opacity
    @Opacity.setter
    def Opacity(self, opacity : float) :
        self.m_opacity = opacity
        self.Actor.GetProperty().SetOpacity(opacity)





    
    

    # protected


    # private
    




if __name__ == '__main__' :
    pass


# print ("ok ..")

