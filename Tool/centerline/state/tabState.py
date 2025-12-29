import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAppPath = os.path.dirname(fileAbsPath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import AlgUtil.algVTK as algVTK
import AlgUtil.algMeshLib as algMeshLib
import AlgUtil.algLinearMath as algLinearMath

import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer

import data as data
import operation as op

import VtkObj.vtkObjText as vtkObjText

# import territory as territory

class CRenderEntity :
    def __init__(self) :
        self.m_color = None
        self.m_mapperHL = vtk.vtkPolyDataMapper()
        self.m_actorHL = vtk.vtkActor()
        self.m_actorHL.SetMapper(self.m_mapperHL)
        self.Color = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 1.0])
    def clear(self) :
        if self.m_actorHL :
            # renderer = self.m_actorHL.GetRenderer()
            # if renderer :
            #     renderer.RemoveActor(self.m_actorHL)
            self.m_actorHL.SetMapper(None)
            self.m_actorHL = None
        if self.m_mapperHL :
            self.m_mapperHL.SetInputData(None)
            self.m_mapperHL = None
        self.m_color = None

    
    @property
    def Actor(self) -> vtk.vtkActor :
        return self.m_actorHL
    @property
    def PolyData(self) -> vtk.vtkPolyData :
        if self.m_mapperHL is not None :
            return self.m_mapperHL.GetInput()
        return None
    @PolyData.setter
    def PolyData(self, polydata : vtk.vtkPolyData) :
        # self.m_mapperHL.SetInputData(polydata)
        # self.m_mapperHL.Update()

        if polydata is None :
            polydata = vtk.vtkPolyData()
            self.m_actorHL.VisibilityOff()
        else :
            self.m_actorHL.VisibilityOn()
        self.m_mapperHL.SetInputData(polydata)
        self.m_mapperHL.Update()

    @property
    def Color(self) -> np.ndarray :
        return self.m_color
    @Color.setter
    def Color(self, color : np.ndarray) :
        self.m_color = color
        self.m_actorHL.GetProperty().SetColor(self.m_color[0, 0], self.m_color[0, 1], self.m_color[0, 2])



class CTabState :
    def __init__(self, mediator = None) :
        self.m_mediator = mediator
        self.m_tab = QWidget()
        self.m_listRenderEntity = []
        self.init_ui()
    def clear(self) :
        for renderEntity in self.m_listRenderEntity :
            renderEntity.clear()
        self.m_listRenderEntity.clear()
        self.m_tab = None
    def init_ui(self) :
        pass

    def process_init(self) :
        pass
    def process(self) :
        pass
    def process_end(self) :
        pass


    def get_btn_stylesheet(self) -> str :
        return self.m_mediator.m_styleSheetBtn
    def get_main_widget(self) -> QWidget :
        return self.m_mediator.m_mainWidget
    def get_data(self) -> data.CData :
        return self.m_mediator.Data
    def get_optioninfo(self) -> optionInfo.COptionInfo :
        dataInst = self.get_data()
        return dataInst.OptionInfo
    def get_phase(self) -> niftiContainer.CPhase :
        dataInst = self.get_data()
        return dataInst.Phase
    def get_clinfo_index(self) -> int :
        dataInst = self.get_data()
        return dataInst.CLInfoIndex
    
    # render entity
    def add_render_entity(self, renderEntity : CRenderEntity) :
        '''
        desc
            rendering 객체를 등록하고 화면에 보이게 만든다. 
        '''
        if renderEntity in self.m_listRenderEntity :
            return
        self.m_mediator.get_viewercl_renderer().AddActor(renderEntity.Actor)
        self.m_listRenderEntity.append(renderEntity)
    def remove_render_entity(self, renderEntity : CRenderEntity) :
        '''
        desc
            rendering 객체를 제거하고 비가시화 한다. 
        '''
        if renderEntity in self.m_listRenderEntity :
            self.m_mediator.get_viewercl_renderer().RemoveActor(renderEntity.Actor)
            self.m_listRenderEntity.remove(renderEntity)
    def clear_render_entity(self) :
        '''
        desc
            모든 rendering 객체를 제거하고 비가시화 한다. 
        '''
        for renderEntity in self.m_listRenderEntity :
            self.m_mediator.get_viewercl_renderer().RemoveActor(renderEntity.Actor)
        self.m_listRenderEntity.clear()
    def get_render_entity_count(self) -> int :
        return len(self.m_listRenderEntity)
    def get_render_entity(self, inx : int) -> CRenderEntity :
        return self.m_listRenderEntity[inx]


    # mediator message
    def clicked_mouse_lb(self, clickX, clickY) :
        pass
    def clicked_mouse_lb_shift(self, clickX, clickY) :
        pass
    def release_mouse_lb(self) :
        pass
    def clicked_mouse_rb(self, clickX, clickY) :
        pass
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        pass
    def release_mouse_rb(self) :
        pass
    def mouse_move(self, clickX, clickY) :
        pass
    def mouse_move_lb(self, clickX, clickY) :
        pass
    def mouse_move_rb(self, clickX, clickY) :
        pass
    def key_press(self, keyCode : str) :
        pass
    def key_press_with_ctrl(self, keyCode : str) : 
        pass
    def changed_project_type(self) :
        pass


    def remove_path(self, path : str) :
        if os.path.exists(path) == False :
            return
        try :
            shutil.rmtree(path)
        except OSError as e:
            print(f"Error: {e}")
    def get_meshlib(self, vtkMeshInst : vtk.vtkPolyData) :
        npVertex = algVTK.CVTK.poly_data_get_vertex(vtkMeshInst)
        npIndex = algVTK.CVTK.poly_data_get_triangle_index(vtkMeshInst)
        meshLibInst = algMeshLib.CMeshLib.meshlib_create(npVertex, npIndex)
        return meshLibInst
    def get_vtkmesh(self, meshlibInst) -> vtk.vtkPolyData :
        npVertex = algMeshLib.CMeshLib.meshlib_get_vertex(meshlibInst)
        npIndex = algMeshLib.CMeshLib.meshlib_get_index(meshlibInst)
        vtkMesh = algVTK.CVTK.create_poly_data_triangle(npVertex, npIndex)
        return vtkMesh


    # protected 
    def _init_cl_label(self) :
        dataInst = self.get_data()
        clinfoInx = self.get_clinfo_index()

        skelinfo = dataInst.get_skelinfo(clinfoInx)
        skeleton = skelinfo.Skeleton

        labelColor = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            iCLInx = int(cl.get_vertex_count() / 2)
            pos = cl.get_vertex(iCLInx)
            activeCamera = self.m_mediator.get_active_camera()
            clName = cl.Name

            key = data.CData.make_key(data.CData.s_textType, 0, cl.ID)
            vtkText = vtkObjText.CVTKObjText(activeCamera, pos, clName, 1.0)
            vtkText.KeyType = data.CData.s_textType
            vtkText.Key = key
            vtkText.Color = labelColor
            dataInst.add_vtk_obj(vtkText)
        
        self.m_mediator.ref_key_type(data.CData.s_textType)
    def _clear_cl_label(self) :
        dataInst = self.get_data()
        clinfoInx = self.get_clinfo_index()

        skelinfo = dataInst.get_skelinfo(clinfoInx)
        skeleton = skelinfo.Skeleton

        self.m_mediator.remove_key_type(data.CData.s_textType)
    def _update_cl_label(self,  clKey : str) :
        dataInst = self.get_data()
        clinfoInx = self.get_clinfo_index()
        
        skelinfo = dataInst.get_skelinfo(clinfoInx)
        skeleton = skelinfo.Skeleton

        keyType, groupID, clID = data.CData.get_keyinfo(clKey)
        cl = skeleton.get_centerline(clID)

        textKey = data.CData.make_key(data.CData.s_textType, 0, cl.ID)
        textObj = dataInst.find_obj_by_key(textKey)
        if textObj is not None :
            textObj.Text = cl.Name


    @property
    def Tab(self) -> QWidget :
        return self.m_tab
        
    





if __name__ == '__main__' :
    pass


# print ("ok ..")

