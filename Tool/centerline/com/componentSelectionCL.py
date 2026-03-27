import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
from matplotlib import cm

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget
from PySide6.QtCore import Qt
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
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algSegment as algSegment

import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer
import Block.reconstruction as reconstruction

import vtkObjInterface as vtkObjInterface
import VtkObj.vtkObjText as vtkObjText

import data as data
import operation as operation
import component as component
from collections import deque
from collections import defaultdict

from typing import Dict, List, Optional, Set, Tuple
import matplotlib.pyplot as plt

from itertools import combinations
# import territory as territory


class CComDrag(component.CCom) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        self.m_startX = 0
        self.m_startY = 0
        self.m_endX = 0
        self.m_endY = 0
        self.m_bDrag = False
    def clear(self) :
        self.m_startX = 0
        self.m_startY = 0
        self.m_endX = 0
        self.m_endY = 0
        self.m_bDrag = False
        super().clear()


    # override
    def click(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        self.m_startX = clickX
        self.m_startY = clickY
        self.m_endX = clickX
        self.m_endY = clickY
        return True
    def click_with_shift(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        self.m_startX = clickX
        self.m_startY = clickY
        self.m_endX = clickX
        self.m_endY = clickY
        return True
    def release(self, clickX : int, clickY : int) :
        self.m_endX = clickX
        self.m_endY = clickY
        return True
    def move(self, clickX : int, clickY : int, listExceptKeyType=None) :
        self.m_endX = clickX
        self.m_endY = clickY
        return True
    

    @property
    def Drag(self) -> bool :
        return self.m_bDrag
    

class CComDragFindCL(CComDrag) :
    def __init__(self, mediator) :
        '''
        desc 
            find dragged centerline
        '''
        super().__init__(mediator)
        # input your code
        self.m_inputOPDragSelCL = None
        self.m_rt = None
        self.m_actorRt = self._create_rt_actor()
    def clear(self) :
        # input your code
        self.m_inputOPDragSelCL = None
        super().clear()

    def ready(self) -> bool :
        if self.InputOPDragSelCL is None :
            return False
        return True
    def process_init(self) :
        super().process_init()
        # input your code
    def process_end(self) :
        # input your code
        super().process_end()
    def click(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        
        super().click(clickX, clickY, listExceptKeyType)
        self.InputOPDragSelCL.process_reset()
        renderer = self._get_renderer()
        renderer.AddActor2D(self.m_actorRt)
        self._update_rt_actor()

        self.m_bDrag = True
        return True
    def click_with_shift(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        
        super().click_with_shift(clickX, clickY, listExceptKeyType)
        renderer = self._get_renderer()
        renderer.AddActor2D(self.m_actorRt)
        self._update_rt_actor()

        self.m_bDrag = True
        return True
    def release(self, clickX : int, clickY : int) :
        if self.ready() == False :
            return False
        if self.Drag == False :
            return False

        renderer = self._get_renderer()
        renderer.RemoveActor2D(self.m_actorRt)
        self.m_bDrag = False
        return True
    def move(self, clickX : int, clickY : int, listExceptKeyType=None) :
        if self.ready() == False :
            return
        if self.Drag == False :
            return False
        
        super().move(clickX, clickY, listExceptKeyType)
        self._update_rt_actor()
        return True
    

    def find_selection_clid(self) -> list :
        '''
        ret : [clID0, clID1, .. ]
        '''
        xmin, xmax = sorted([self.m_startX, self.m_endX])
        ymin, ymax = sorted([self.m_startY, self.m_endY])

        npPt = self.App.project_points_to_display(self._get_skeleton().m_listKDTreeAnchor)
        inside = ((npPt[:,0] >= xmin) & (npPt[:,0] <= xmax) & (npPt[:,1] >= ymin) & (npPt[:,1] <= ymax))
        selectedIndex = np.where(inside)[0]

        listID = set()
        for inx in selectedIndex :
            listID.add(self._get_skeleton().m_listKDTreeAnchorID[inx])
        
        listID = list(listID)
        if len(listID) == 0 :
            return None
        return listID
    

    # protected
    def _create_rt_actor(self) :
        self.m_rt = vtk.vtkPoints()
        self.m_rt.SetNumberOfPoints(4)
        for i in range(4):
            self.m_rt.SetPoint(i, 0, 0, 0)

        rect_poly = vtk.vtkPolyData()
        rect_poly.SetPoints(self.m_rt)

        rect_cells = vtk.vtkCellArray()
        rect_cells.InsertNextCell(5)
        for i in [0, 1, 2, 3, 0]:
            rect_cells.InsertCellPoint(i)
        rect_poly.SetLines(rect_cells)

        mapper = vtk.vtkPolyDataMapper2D()
        mapper.SetInputData(rect_poly)

        actor = vtk.vtkActor2D()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.3, 1.0, 0.3)
        actor.GetProperty().SetLineWidth(2.0)
        return actor
    def _update_rt_actor(self) :
        x0 = self.m_startX
        y0 = self.m_startY
        x1 = self.m_endX
        y1 = self.m_endY
        self.m_rt.SetPoint(0, x0, y0, 0)
        self.m_rt.SetPoint(1, x1, y0, 0)
        self.m_rt.SetPoint(2, x1, y1, 0)
        self.m_rt.SetPoint(3, x0, y1, 0)
        self.m_rt.Modified()
    

    @property
    def InputOPDragSelCL(self) -> operation.COperationDragSelectionCL :
        return self.m_inputOPDragSelCL
    @InputOPDragSelCL.setter
    def InputOPDragSelCL(self, opCL : operation.COperationDragSelectionCL) :
        self.m_inputOPDragSelCL = opCL

    

class CComDragSelCL(CComDragFindCL) :
    def __init__(self, mediator):
        '''
        desc 
            hier selection centerline component
        '''
        super().__init__(mediator)
        # input your code
        self.m_inputUIRBSelSingle = None
        self.m_inputUIRBSelDescendant = None
    def clear(self) :
        # input your code
        self.m_inputUIRBSelSingle = None
        self.m_inputUIRBSelDescendant = None
        super().clear()

    
    # event override 
    def ready(self) -> bool :
        if super().ready() == False :
            return False
        if self.InputUIRBSelSingle is None :
            return False
        if self.InputUIRBSelDescendant is None :
            return False
        return True
    def process_init(self) :
        super().process_init()
        # input your code
    def process_end(self) :
        # input your code
        super().process_end()
    def release(self, clickX : int, clickY : int) :
        if self.ready() == False :
            return False
        if self.Drag == False :
            return False
        
        super().release(clickX, clickY)

        if self.InputUIRBSelSingle.isChecked() : 
            self.InputOPDragSelCL.ChildSelectionMode = False
        elif self.InputUIRBSelDescendant.isChecked() :
            self.InputOPDragSelCL.ChildSelectionMode = True

        clinfoInx = self._get_clinfoinx()
        listCLID = self.find_selection_clid()
        listKey = []
        if listCLID is not None :
            for clID in listCLID :
                pickingKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, clID)
                listKey.append(pickingKey)
            self.InputOPDragSelCL.add_selection_keys(listKey)
            self.InputOPDragSelCL.process()

        return True


    # protected


    @property
    def InputUIRBSelSingle(self) :
        return self.m_inputUIRBSelSingle
    @InputUIRBSelSingle.setter
    def InputUIRBSelSingle(self, inputUIRBSelSingle) :
        self.m_inputUIRBSelSingle = inputUIRBSelSingle
    @property
    def InputUIRBSelDescendant(self) :
        return self.m_inputUIRBSelDescendant
    @InputUIRBSelDescendant.setter
    def InputUIRBSelDescendant(self, inputUIRBSelDescendant) :
        self.m_inputUIRBSelDescendant = inputUIRBSelDescendant



class CComDragSelCLLabel(CComDragSelCL) :
    def __init__(self, mediator) :
        '''
        desc 
            selection centerline labeling component
        '''
        super().__init__(mediator)
        # input your code
    def clear(self) :
        # input your code
        super().clear()

    
    # event override 
    def process_init(self) :
        if self.ready() == False :
            return
        super().process_init()
        # input your code
        self._init_cl_label()
    def process_end(self) :
        if self.ready() == False :
            return
        # input your code
        self._clear_cl_label()
        super().process_end()

    
    # command
    def command_label_name(self, labelName : str) -> bool :
        if self.ready() == False :
            return False
        
        # selection clID 얻어옴
        # 해당 cl에 대해 labelName setting 
        listCLID = self.InputOPDragSelCL.get_all_selection_cl()
        if listCLID is None : 
            return False
        
        skeleton = self._get_skeleton()
        clinfoinx = self._get_clinfoinx()

        for clID in listCLID :
            cl = skeleton.get_centerline(clID)
            cl.Name = labelName
            clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoinx, clID)
            self._update_cl_label(clKey)
        return True
    

    def _init_cl_label(self) :
        dataInst = self._get_data()
        clinfoInx = self._get_clinfoinx()
        skeleton = self._get_skeleton()

        labelColor = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            iCLInx = int(cl.get_vertex_count() / 2)
            pos = cl.get_vertex(iCLInx)
            activeCamera = self.App.get_active_camera()
            clName = cl.Name

            key = data.CData.make_key(data.CData.s_textType, 0, cl.ID)
            vtkText = vtkObjText.CVTKObjText(activeCamera, pos, clName, 1.0)
            vtkText.KeyType = data.CData.s_textType
            vtkText.Key = key
            vtkText.Color = labelColor
            dataInst.add_vtk_obj(vtkText)
        
        self.App.ref_key_type(data.CData.s_textType)
    def _clear_cl_label(self) :
        self.App.remove_key_type(data.CData.s_textType)
    def _update_cl_label(self,  clKey : str) :
        dataInst = self._get_data()
        clinfoInx = self._get_clinfoinx()
        skeleton = self._get_skeleton()

        keyType, groupID, clID = data.CData.get_keyinfo(clKey)
        cl = skeleton.get_centerline(clID)

        textKey = data.CData.make_key(data.CData.s_textType, 0, cl.ID)
        textObj = dataInst.find_obj_by_key(textKey)
        if textObj is not None :
            textObj.Text = cl.Name



class CComDragSelCLTP(CComDrag) :
    '''
    desc
        tp를 통해 centerline을 선택한다.. 
        반드시 add_tpinfo를 등록한 후에 사용한다. 등록 안할 시 동작 안함 
    '''
    s_tpColorCnt = 100
    s_tpVesselKeyType = "TPVessel"
    s_tpRadius = 2.0
    s_pickingDepth = 1000.0
    s_textGroupID = 10000


    def __init__(self, mediator) :
        '''
        desc 
            selection centerline component
        '''
        super().__init__(mediator)
        # input your code
        '''
        value : {tpName, pos : np.ndarray}
        '''
        self.m_listTPInfo = []
        '''
        key : tpVesselObj Key
        value : clID
        '''
        self.m_dicMatching = {}
        self.m_colors = np.array([cm.get_cmap("hsv", CComDragSelCLTP.s_tpColorCnt)(i)[:3] for i in range(CComDragSelCLTP.s_tpColorCnt)])

        self.m_pickingKey = ""
        self.m_anchorObj = None
        self.m_ratio = 0.0

        self.m_comDragFindCL = CComDragFindCL(mediator)
    def clear(self) :
        # input your code
        self.m_pickingKey = ""
        self.m_anchorObj = None
        self.m_ratio = 0.0

        self.m_listTPInfo.clear()
        self.m_dicMatching.clear()
        self.m_colors = None

        self.m_comDragFindCL.clear()
        super().clear()


    # tp와 매칭중인 cl에 대해 label을 

    
    # event override 
    def ready(self) -> bool :
        if self.get_tpinfo_count() == 0 :
            return False
        if self.m_comDragFindCL.ready() == False :
            return False
        return True
    def process_init(self) :
        if self.ready() == False :
            return
        super().process_init()
        # input your code
        self._init_tp_obj()
        self._init_matching_tp_cl()
        self.m_comDragFindCL.process_init()
        self._refresh_cl_text()
    def process_end(self) :
        if self.ready() == False :
            return
        # input your code
        self.m_comDragFindCL.process_end()
        self._clear_matching_tp_cl()
        self._clear_tp_obj()
        self._clear_cl_color()
        super().process_end()
    def click(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        
        super().click(clickX, clickY, listExceptKeyType)

        key = self.App.picking(clickX, clickY, listExceptKeyType)
        if key == "" :
            self.m_bDrag = True
            return self.m_comDragFindCL.click(clickX, clickY, listExceptKeyType)
        keyType = data.CData.get_type_from_key(key)
        if keyType != CComDragSelCLTP.s_tpVesselKeyType :
            return False
        
        self.m_pickingKey = key
        dataInst = self._get_data()
        self.m_anchorObj = dataInst.find_obj_by_key(self.m_pickingKey)

        self.m_comDragFindCL.InputOPDragSelCL.process_reset()

        clickedPoint = self.App.picking_intersected_point(clickX, clickY, listExceptKeyType)
        if clickedPoint is not None :
            cameraInfo = self.App.get_active_camerainfo()
            cameraPos = cameraInfo[3]
            dist = algLinearMath.CScoMath.vec3_len(clickedPoint - cameraPos)
            self.m_ratio = dist / CComDragSelCLTP.s_pickingDepth

        self.m_bDrag = True
        return True
    def click_with_shift(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        
        super().click_with_shift(clickX, clickY, listExceptKeyType)
        self.m_comDragFindCL.click_with_shift(clickX, clickY, listExceptKeyType)
        self.m_bDrag = True
        return True
    def release(self, clickX : int, clickY : int) :
        if self.ready() == False :
            return False
        if self.Drag == False :
            return False
        
        if self.m_pickingKey == "" :
            clinfoinx = self._get_clinfoinx()
            self.m_comDragFindCL.release(clickX, clickY)
            listCLID = self.m_comDragFindCL.find_selection_clid()
            if listCLID is not None :
                listValidCLKey = []
                for clID in listCLID :
                    if self._exist_matching_by_clID(clID) == True :
                        continue
                    clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoinx, clID)
                    listValidCLKey.append(clKey)
                self.m_comDragFindCL.InputOPDragSelCL.add_selection_keys(listValidCLKey)
                self.m_comDragFindCL.InputOPDragSelCL.process()
        else :
            self.m_pickingKey = ""
            self.m_anchorObj = None
            self._refresh_cl_text()
        self.m_bDrag = False
        return True
    def move(self, clickX : int, clickY : int, listExceptKeyType=None) :
        if self.ready() == False :
            return False
        if self.Drag == False :
            return False
        
        super().move(clickX, clickY, listExceptKeyType)

        if self.m_pickingKey == "" :
            self.m_comDragFindCL.move(clickX, clickY, listExceptKeyType)
            return True
        else :
            cameraInfo = self.App.get_active_camerainfo()
            cameraPos = cameraInfo[3]
            self._clear_matching(self.m_anchorObj.Key)

            clickedPoint = self.App.picking_intersected_point(clickX, clickY, listExceptKeyType)
            if clickedPoint is not None :
                dist = algLinearMath.CScoMath.vec3_len(clickedPoint - cameraPos)
                self.m_ratio = dist / CComDragSelCLTP.s_pickingDepth
                # 이 부분에서 centerline도 감지 
                key = self.App.picking(clickX, clickY, listExceptKeyType)
                if key != "" and data.CData.get_type_from_key(key) == data.CData.s_skelTypeCenterline :
                    '''
                    # 기존 matching 정보 갱신
                        - anchorObj에 matching된 cl이 있다면 제거
                        - 현재 key의 cl을 anchorObj와 matching 
                    '''
                    clID = data.CData.get_id_from_key(key)
                    if self._exist_matching_by_clID(clID) == False : 
                        self._set_matching(self.m_anchorObj.Key, clID)

            worldStart, pNearStart, pFarStart= self.App.get_world_from_mouse(clickX, clickY, CComDragSelCLTP.s_pickingDepth)
            dist = algLinearMath.CScoMath.vec3_len(worldStart - cameraPos)
            moveVec = cameraPos + (worldStart - cameraPos) * self.m_ratio
            self.m_anchorObj.Pos = moveVec

            pos = self.m_anchorObj.Pos.copy()
            pos[0, 1] = pos[0, 1] + CComDragSelCLTP.s_tpRadius
            textObj = self._get_text_obj(self.m_anchorObj.Key)
            textObj.Pos = pos

            # tpinfo update
            tpID = data.CData.get_id_from_key(self.m_anchorObj.Key)
            tpName = self.get_tpinfo_name(tpID)
            tpPos = self.m_anchorObj.Pos
            self.set_tpinfo(tpID, tpName, tpPos)
        return True
    

    def add_tpinfo(self, tpName : str, tpPos : np.ndarray) :
        dic = {}
        dic[tpName] = tpPos
        self.m_listTPInfo.append(dic)
    def get_tpinfo_count(self) -> int :
        return len(self.m_listTPInfo)
    def get_tpinfo_name(self, inx : int) -> str :
        dic = self.m_listTPInfo[inx]
        tpName = list(dic.keys())[0]
        return tpName
    def get_tpinfo_pos(self, inx : int) -> np.ndarray :
        dic = self.m_listTPInfo[inx]
        pos = list(dic.values())[0]
        return pos
    def get_tpinfo(self, inx : int) -> tuple :
        '''
        ret : (tpName, pos : np.ndarray)
        '''
        dic = self.m_listTPInfo[inx]
        tpName = list(dic.keys())[0]
        pos = list(dic.values())[0]
        return (tpName, pos)
    def set_tpinfo(self, inx : int, name : str, pos : np.ndarray) :
        dic = self.m_listTPInfo[inx]
        dic[name] = pos.copy()
    def get_tp_color(self, inx : int) -> np.ndarray :
        mappedIndex = inx % CComDragSelCLTP.s_tpColorCnt
        return self.m_colors[mappedIndex].reshape(-1, 3)
    def get_label_cl_list(self) -> list :
        '''
        desc
            CSkeletonCenterline 인스턴스가 담긴 리스트를 반환
            해당 centerline은 TP와 매칭은 안됐지만 Name이 기록 된 cl이다. 
        ret : [cl0, cl1, ..]
        '''
        retList = []
        skeleton = self._get_skeleton()
        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            if cl.Name == "" :
                continue
            if self._exist_matching_by_clID(cl.ID) == True :
                continue
            retList.append(cl)
        
        if len(retList) == 0 :
            return None
        return retList


    

    def command_label_name(self, labelName : str) -> bool :
        if self.ready() == False :
            return False
        
        # selection clID 얻어옴
        # 해당 cl에 대해 labelName setting 
        listCLID = self.m_comDragFindCL.InputOPDragSelCL.get_all_selection_cl()
        if listCLID is None : 
            return False
        
        skeleton = self._get_skeleton()
        clinfoinx = self._get_clinfoinx()

        for clID in listCLID :
            cl = skeleton.get_centerline(clID)
            cl.Name = labelName
            # clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoinx, clID)
        self._refresh_cl_text()
        return True
    

    # protected
    def _init_tp_obj(self) :
        dataInst = self._get_data()
        activeCamera = self.App.get_active_camera()
        keyType = CComDragSelCLTP.s_tpVesselKeyType

        for id in range(0, self.get_tpinfo_count()) :
            tpPolyData = algVTK.CVTK.create_poly_data_sphere(
                algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0]), 
                CComDragSelCLTP.s_tpRadius
            )
            label = self.get_tpinfo_name(id)
            pos = self.get_tpinfo_pos(id).copy()
            color = self.get_tp_color(id)

            # tpObj
            key = data.CData.make_key(keyType, 0, id)
            tpVesselObj = vtkObjInterface.CVTKObjInterface()
            tpVesselObj.KeyType = keyType
            tpVesselObj.Key = key
            tpVesselObj.Color = color
            tpVesselObj.Opacity = 0.5
            tpVesselObj.PolyData = tpPolyData
            tpVesselObj.Pos = pos
            dataInst.add_vtk_obj(tpVesselObj)

            # tpTextObj
            pos[0, 1] = pos[0, 1] + CComDragSelCLTP.s_tpRadius
            textKey = data.CData.make_key(data.CData.s_textType, 0, id)
            vtkText = vtkObjText.CVTKObjText(activeCamera, pos, label, 2.0)
            vtkText.KeyType = data.CData.s_textType
            vtkText.Key = textKey
            vtkText.Color = color
            dataInst.add_vtk_obj(vtkText)
        self.App.ref_key_type(CComDragSelCLTP.s_tpVesselKeyType)
        self.App.ref_key_type(data.CData.s_textType)
    def _init_matching_tp_cl(self) :
        dataInst = self._get_data()
        skeleton = self._get_skeleton()
        clinfoinx = self._get_clinfoinx()
        keyType = CComDragSelCLTP.s_tpVesselKeyType

        for id in range(0, self.get_tpinfo_count()) :
            pos = self.get_tpinfo_pos(id)
            color = self.get_tp_color(id)
            label = self.get_tpinfo_name(id)

            cl = skeleton.find_nearest_centerline(pos)
            clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoinx, cl.ID)
            clObj = dataInst.find_obj_by_key(clKey)
            clObj.CL.Name = label
            clObj.Color = color

            tpVesselKey = data.CData.make_key(keyType, 0, id)
            self.m_dicMatching[tpVesselKey] = cl.ID
    def _clear_tp_obj(self) :
        self.App.remove_key_type(CComDragSelCLTP.s_tpVesselKeyType)
        self.App.remove_key_type(data.CData.s_textType)
    def _clear_matching_tp_cl(self) :
        self.m_dicMatching.clear()
    def _clear_cl_color(self) :
        dataInst = self._get_data()
        clinfoInx = self._get_clinfoinx()
        skeleton = self._get_skeleton()

        color = None
        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            if inx == skeleton.RootCenterline.ID :
                color = dataInst.RootCLColor
            else :
                color = dataInst.s_clColor

            clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, inx)
            clObj = dataInst.find_obj_by_key(clKey)
            clObj.Color = color
    def _get_text_obj(self, tpVesselKey : str) :
        dataInst = self._get_data()
        tpID = data.CData.get_id_from_key(tpVesselKey)
        textKey = data.CData.make_key(data.CData.s_textType, 0, tpID)
        textObj = dataInst.find_obj_by_key(textKey)
        return textObj
    
    def _clear_matching(self, tpVesselObjKey : str) :
        dataInst = self._get_data()
        clinfoInx = self._get_clinfoinx()
        skeleton = self._get_skeleton()

        clID = self.m_dicMatching[tpVesselObjKey]
        if clID != -1 :
            color = None
            if clID == skeleton.RootCenterline.ID :
                color = dataInst.RootCLColor
            else :
                color = dataInst.s_clColor
            clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, clID)
            clObj = dataInst.find_obj_by_key(clKey)
            clObj.Color = color
            clObj.CL.Name = ""
        self.m_dicMatching[tpVesselObjKey] = -1
    def _set_matching(self, tpVesselObjKey : str, clID : int) :
        dataInst = self._get_data()
        clinfoInx = self._get_clinfoinx()

        id = dataInst.get_id_from_key(tpVesselObjKey)
        label = self.get_tpinfo_name(id)
        color = self.get_tp_color(id)

        clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, clID)
        clObj = dataInst.find_obj_by_key(clKey)
        clObj.Color = color
        clObj.CL.Name = label
        self.m_dicMatching[tpVesselObjKey] = clID
    def _exist_matching_by_clID(self, clID : int) -> bool :
        if clID in self.m_dicMatching.values() :
            return True
        return False 

    def _refresh_cl_text(self) :
        self.App.remove_key_type_groupID(data.CData.s_textType, CComDragSelCLTP.s_textGroupID)

        dataInst = self._get_data()
        skeleton = self._get_skeleton()
        clinfoinx = self._get_clinfoinx()
        iCnt = skeleton.get_centerline_count()

        for clID in range(0, iCnt) :
            cl = skeleton.get_centerline(clID)
            if cl.Name == "" :
                continue
            if self._exist_matching_by_clID(clID) == True :
                continue

            iCLInx = int(cl.get_vertex_count() / 2)
            pos = cl.get_vertex(iCLInx)
            activeCamera = self.App.get_active_camera()

            key = data.CData.make_key(data.CData.s_textType, CComDragSelCLTP.s_textGroupID, clID)

            vtkText = vtkObjText.CVTKObjText(activeCamera, pos, cl.Name, 1.0)
            vtkText.KeyType = data.CData.s_textType
            vtkText.Key = key
            vtkText.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
            dataInst.add_vtk_obj(vtkText)
        self.App.ref_key_type(data.CData.s_textType)
            


    @property
    def InputOPDragSelCL(self) -> operation.COperationDragSelectionCL :
        return self.m_comDragFindCL.InputOPDragSelCL
    @InputOPDragSelCL.setter
    def InputOPDragSelCL(self, opCL : operation.COperationDragSelectionCL) :
        self.m_comDragFindCL.InputOPDragSelCL = opCL

class CComDragSkelCL(CComDrag) :
    def __init__(self, mediator) :
        '''
        desc 
            find dragged centerline 
        '''
        super().__init__(mediator)
        # input your code
        self.m_inputSkeleton = None
        self.m_inputSkelGroupID = -1
        self.m_opDragToggleCL = operation.COperationDragSelectionCLToggle(self.App)
        self.m_rt = None
        self.m_actorRt = self._create_rt_actor()
        self.m_enSkeleton = False
    def clear(self) :
        # input your code
        self.m_inputSkeleton = None
        self.m_inputSkelGroupID = -1
        self.m_opDragToggleCL = None
        self.m_enSkeleton = False
        super().clear()

    def ready(self) -> bool :
        if self.InputSkeleton is None :
            return False 
        if self.InputSkelGroupID == -1 :
            return False
        if self.m_opDragToggleCL is None : 
            return False
        return True
    def process_init(self) :
        if self.ready() == False :
            return False
        
        super().process_init()
        # input your code
        self.m_opDragToggleCL.Skeleton = self.InputSkeleton
    def process_end(self) :
        if self.ready() == False :
            return False
        
        if self.m_enSkeleton:
            self.m_opDragToggleCL.process_reset_for_en()    
        else:
            self.m_opDragToggleCL.process_reset()
        # input your code
        super().process_end()
        
    def click(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        
        super().click(clickX, clickY, listExceptKeyType)
        if self.m_enSkeleton:
            self.m_opDragToggleCL.process_reset_for_en()    
        else:
            self.m_opDragToggleCL.process_reset()
        renderer = self._get_renderer()
        renderer.AddActor2D(self.m_actorRt)
        self._update_rt_actor()

        self.m_bDrag = True
        return True
    def click_with_shift(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        
        super().click_with_shift(clickX, clickY, listExceptKeyType)
        renderer = self._get_renderer()
        renderer.AddActor2D(self.m_actorRt)
        self._update_rt_actor()

        self.m_bDrag = True
        return True
    def release(self, clickX : int, clickY : int) :
        if self.ready() == False :
            return False
        if self.Drag == False :
            return False

        renderer = self._get_renderer()
        renderer.RemoveActor2D(self.m_actorRt)

        listCLID = self._find_selection_clid()
        listKey = []
        if listCLID is not None :
            for clID in listCLID :
                pickingKey = data.CData.make_key(data.CData.s_skelTypeCenterline, self.InputSkelGroupID, clID)
                listKey.append(pickingKey)
            self.m_opDragToggleCL.add_toggle_selection_keys(listKey)
            self.m_opDragToggleCL.process()
        self.m_bDrag = False
        return True
    def move(self, clickX : int, clickY : int, listExceptKeyType=None) :
        if self.ready() == False :
            return
        if self.Drag == False :
            return False
        
        super().move(clickX, clickY, listExceptKeyType)
        self._update_rt_actor()
        return True

    def get_selection_clid(self) -> list :
        return self.m_opDragToggleCL.get_all_selection_cl()
    def get_selection_cl(self) -> list :
        retListCLID = self.get_selection_clid()
        skeleton = self.InputSkeleton
        return [skeleton.get_centerline(clid) for clid in retListCLID]
    
    def set_toggle_selection_clid(self, listCLID : list) :
        listKey = []
        for clid in listCLID :
            key = data.CData.make_key(data.CData.s_skelTypeCenterline, self.InputSkelGroupID, clid)
            listKey.append(key)

        self.m_opDragToggleCL.process_reset_for_en()
        if len(listKey) > 0 :
            childMode = self.m_opDragToggleCL.ChildSelectionMode
            self.m_opDragToggleCL.ChildSelectionMode = False
            self.m_opDragToggleCL.add_toggle_selection_keys(listKey)
            self.m_opDragToggleCL.process()
            self.m_opDragToggleCL.ChildSelectionMode = childMode
            

    def _centerline_contrib(self, cl, alpha: float, beta:float = 1.5) -> float:
        """
        굵고 긴 cl
        edge의 local contribution = radius^alpha * length
        - radius/length가 0 또는 음수면 0으로 처리
        """
        q1 = np.percentile(cl.Radius, 25)
        q2 = np.percentile(cl.Radius, 50)
        q3 = np.percentile(cl.Radius, 75)
        
        r = np.mean([q1, q2, q3])
        l = len(cl.Radius)
        if r <= 0.0 or l <= 0.0:
            return 0.0
        return (r ** alpha) * (l ** beta)

    
    def _overlap_ratio(self, path: List[int], union_set: Set[int]) -> float:
        """
        overlap_ratio = |path ∩ union| / |path|
        """
        if not path:
            return 1.0
        inter = sum(1 for x in path if x in union_set)
        return inter / float(len(path))
        
        
    def angle_between_vectors_rad(self, v1, v2):
        v1 = np.asarray(v1, dtype=float)
        v2 = np.asarray(v2, dtype=float)

        # 길이 0 벡터 방지
        n1 = np.linalg.norm(v1)
        n2 = np.linalg.norm(v2)
        if n1 == 0 or n2 == 0:
            raise ValueError("Zero-length vector is not allowed")

        cos_theta = np.dot(v1, v2) / (n1 * n2)
        cos_theta = np.clip(cos_theta, -1.0, 1.0)  # 수치 안정성

        theta_rad = np.arccos(cos_theta)
        return theta_rad

    def angle_between_lines_rad(self, p1, p2, p3, p4):
        """
        line1: p1 -> p2
        line2: p3 -> p4
        return: angle in radians
        """
        v1 = p2 - p1
        v2 = p4 - p3

        return self.angle_between_vectors_rad(v1, v2)
    
    def calculate_angle_radian(self, cl1, cl2):
        angle = self.angle_between_lines_rad(
            cl1.Vertex[0], cl1.Vertex[1],
            cl2.Vertex[0], cl2.Vertex[1]
        )
        
        return angle
    
    def calculate_angle_radian_parent_child(self, parentCl, childCl):
        if np.linalg.norm(parentCl.Vertex[-2]-childCl.Vertex[1]) < 0.3:
            return 1.0
        
        if parentCl.Vertex.shape[0]>4 and childCl.Vertex.shape[0]>4:
            angle = self.angle_between_lines_rad(
                parentCl.Vertex[-5], parentCl.Vertex[-3],
                childCl.Vertex[2], childCl.Vertex[4]
            )
        elif parentCl.Vertex.shape[0]>4:
            angle = self.angle_between_lines_rad(
                parentCl.Vertex[-5], parentCl.Vertex[-3],
                childCl.Vertex[0], childCl.Vertex[1]
            )
        elif childCl.Vertex.shape[0]>4:
            angle = self.angle_between_lines_rad(
                parentCl.Vertex[-2], parentCl.Vertex[-1],
                childCl.Vertex[2], childCl.Vertex[4]
            )  
        else:
            angle = self.angle_between_lines_rad(
                parentCl.Vertex[-2], parentCl.Vertex[-1],
                childCl.Vertex[0], childCl.Vertex[-1]
            )
        return angle
        
        # if childCl.Vertex.shape[0] > 2:
        #     angle1 = self.angle_between_lines_rad(
        #         parentCl.Vertex[-2], parentCl.Vertex[-1],
        #         childCl.Vertex[0], childCl.Vertex[1]
        #     )
        #     angle2 = self.angle_between_lines_rad(
        #         parentCl.Vertex[-2], parentCl.Vertex[-1],
        #         childCl.Vertex[1], childCl.Vertex[2]
        #     )        
        #     return (angle1+angle2)/2
        # else:
        #     angle = self.angle_between_lines_rad(
        #         parentCl.Vertex[-2], parentCl.Vertex[-1],
        #         childCl.Vertex[0], childCl.Vertex[1]
        #     )
        #     return angle
    
        
        
        # pPivotIdx = parentCl.Vertex.shape[0]//2
        # cPivotIdx = childCl.Vertex.shape[0]//2
        
        # # pPivotIdx = (parentCl.Vertex.shape[0]//3)*2
        # # cPivotIdx = childCl.Vertex.shape[0]//3
        
        # if childCl.Vertex.shape[0] > 5 and parentCl.Vertex.shape[0] > 5:
        #     angle = self.angle_between_lines_rad(
        #         parentCl.Vertex[pPivotIdx-1], parentCl.Vertex[pPivotIdx+1],
        #         childCl.Vertex[cPivotIdx-1], childCl.Vertex[cPivotIdx+1]
        #     )
        #     return angle
        # elif childCl.Vertex.shape[0] > 5:
        #     angle = self.angle_between_lines_rad(
        #         parentCl.Vertex[0], parentCl.Vertex[-1],
        #         childCl.Vertex[cPivotIdx-1], childCl.Vertex[cPivotIdx+1]
        #     )
        #     return angle
        # elif parentCl.Vertex.shape[0] > 5:
        #     angle = self.angle_between_lines_rad(
        #         parentCl.Vertex[pPivotIdx-1], parentCl.Vertex[pPivotIdx+1],
        #         childCl.Vertex[0], childCl.Vertex[-1]
        #     )
        #     return angle
        # else:
        #     angle = self.angle_between_lines_rad(
        #         parentCl.Vertex[0], parentCl.Vertex[-1],
        #         childCl.Vertex[0], childCl.Vertex[-1]
        #     )
        #     return angle


    def get_representative_radius(self, cl):
        if len(cl.Radius) < 7:
            representativeR = np.mean([np.percentile(cl.Radius, 40),
                                  np.percentile(cl.Radius, 50)])
        else:
            r1 = np.partition(cl.Radius, -4)[-4]
            r2 = np.partition(cl.Radius, -6)[-6]
            representativeR = np.mean([r1, r2])
            #representativeR = np.mean([cl.Radius[3], cl.Radius[4]])
        
        return representativeR
    
            
    def extract_main_centerline(self, startCLIDs, skeleton, segments):
        AngleRadianThreshold = 0.5 # 28도
        MaxAngleThreshold = 1.2 # 70도
        RadiusRatioThreshold = 0.25
        RelativaRadiusRatioThreshold = 0.16
        
        visited = set()
        queue = deque([])
        for clID in startCLIDs:
            visited.add(clID)
            queue.append(clID)
        
        while queue:
            id = queue.popleft()
            cl = skeleton.get_centerline(id)
            parentCLID, listChildCLID = skeleton.get_conn_centerline_id(id)
            parentR = self.get_representative_radius(cl)
    
            relativeRadiusAngle = {}
            for CID in listChildCLID:
                if CID in visited:
                    continue
                
                childCL = skeleton.get_centerline(CID)
                childR = self.get_representative_radius(childCL)

                if cl.Name in segments and childCL.Name in segments and childCL.Name == cl.Name:
                    # 분지지점에서 centerline이 작게 생기는 경우는 이전 
                    if childCL.Vertex.shape[0] < 5 and (1-childR/parentR) < RadiusRatioThreshold and not childCL.is_leaf():
                        queue.append(CID)
                        visited.add(CID)
                        continue
                    
                    # 이전 대비 상대 angle, 상대 radius
                    relativeRadiusAngle[CID] = ((1-childR/parentR), self.calculate_angle_radian_parent_child(cl, childCL))
                else:
                    queue.append(CID)
                    visited.add(CID)
                        
            # angle 조건 우선
            sortedAngleCID = sorted(list(relativeRadiusAngle.keys()), key=lambda x : relativeRadiusAngle[x][1])
            sortedRadiusCID = sorted(list(relativeRadiusAngle.keys()), key=lambda x : relativeRadiusAngle[x][0])
            
            if len(relativeRadiusAngle.keys()) >1:
                if relativeRadiusAngle[sortedAngleCID[0]][1] < AngleRadianThreshold:
                    if abs(relativeRadiusAngle[sortedAngleCID[0]][0]-relativeRadiusAngle[sortedAngleCID[1]][0]) < RelativaRadiusRatioThreshold:
                        queue.append(sortedAngleCID[0])
                        visited.add(sortedAngleCID[0])
                    else:
                        if relativeRadiusAngle[sortedRadiusCID[0]][1] < MaxAngleThreshold:
                            queue.append(sortedRadiusCID[0])
                            visited.add(sortedRadiusCID[0])
                else:
                    if abs(relativeRadiusAngle[sortedRadiusCID[1]][0]-relativeRadiusAngle[sortedRadiusCID[0]][0]) > RelativaRadiusRatioThreshold:
                        if relativeRadiusAngle[sortedRadiusCID[0]][0] < RelativaRadiusRatioThreshold:
                            queue.append(sortedRadiusCID[0])
                            visited.add(sortedRadiusCID[0])
                        else:
                            pass
                    else:
                        pass
            else:
                for CID in relativeRadiusAngle.keys():
                    if relativeRadiusAngle[CID][1] < AngleRadianThreshold:
                        queue.append(CID)
                        visited.add(CID)
                    else:
                        pass
                    
        return visited
        
    
    def build_backbone_by_angle_based_depth(
        self,
        skeleton,
        segments,
        order: int = 0
    ):
        
        AngleRadianThreshold = 0.5 # 28도
        RadiusRatioThreshold = 0.25
        RelativaRadiusRatioThreshold = 0.16
        
        if skeleton == None:
            return
        
        rootClId = skeleton.RootCenterline.ID
        rootCl = skeleton.RootCenterline
        
        startDepth = 0
        queue = deque([(rootClId, startDepth)])
        visited = set()
        visited.add(rootClId)
        
        depthToClID = defaultdict(set)
        segToDepthToClID = defaultdict(lambda : defaultdict(set))
        segToRadiusClID =  defaultdict(list)

        while queue:
            id, depth = queue.popleft()
            cl = skeleton.get_centerline(id)
            parentCLID, listChildCLID = skeleton.get_conn_centerline_id(id)
            parentR = self.get_representative_radius(cl)
    
            depthToClID[depth].add(id)
            segToDepthToClID[cl.Name][depth].add(id)
            
            ################ test
            segToRadiusClID[cl.Name].append((parentR, cl.ID))
            
            relativeRadiusAngle = {}
            for CID in listChildCLID:
                if CID in visited:
                    continue
                visited.add(CID)
                childCL = skeleton.get_centerline(CID)
                childR = self.get_representative_radius(childCL)

                if cl.Name in segments and childCL.Name in segments and childCL.Name == cl.Name:
                    # 분지지점에서 centerline이 작게 생기는 경우는 이전 
                    if childCL.Vertex.shape[0] < 5 and (1-childR/parentR) < RadiusRatioThreshold and not childCL.is_leaf():
                        queue.append((CID, depth))
                        continue
                    # 이전 대비 상대 angle, 상대 radius
                    #relativeRadiusAngle[CID] = ((1-childR/parentR), self.calculate_angle_radian_parent_child(cl, childCL))
                    queue.append((CID, depth+1))
                else:
                    queue.append((CID, depth))
                        
            # # angle 조건 우선
            # sortedAngleCID = sorted(list(relativeRadiusAngle.keys()), key=lambda x : relativeRadiusAngle[x][1])
            # sortedRadiusCID = sorted(list(relativeRadiusAngle.keys()), key=lambda x : relativeRadiusAngle[x][0])
            
            # if len(relativeRadiusAngle.keys()) >1:
            #     #if abs(relativeRadiusAngle[sortedCID[0]][0]-relativeRadiusAngle[sortedCID[1]][0]) < RelativaRadiusRatioThreshold:
            #     if relativeRadiusAngle[sortedAngleCID[0]][1] < AngleRadianThreshold:
            #         if abs(relativeRadiusAngle[sortedAngleCID[0]][0]-relativeRadiusAngle[sortedAngleCID[1]][0]) < RelativaRadiusRatioThreshold:
            #             queue.append((sortedAngleCID[0], depth))
            #             for i in range(1, len(sortedAngleCID)):
            #                 queue.append((sortedAngleCID[i], depth+1))
            #         else:
            #             queue.append((sortedRadiusCID[0], depth))
            #             for i in range(1, len(sortedRadiusCID)):
            #                 queue.append((sortedRadiusCID[i], depth+1))
                        
            #     else:
            #         if abs(relativeRadiusAngle[sortedRadiusCID[1]][0]-relativeRadiusAngle[sortedRadiusCID[0]][0]) > RelativaRadiusRatioThreshold:
            #             if relativeRadiusAngle[sortedRadiusCID[0]][0] < RelativaRadiusRatioThreshold:
            #                 queue.append((sortedRadiusCID[0], depth))
            #                 for i in range(1, len(sortedRadiusCID)):
            #                     queue.append((sortedRadiusCID[i], depth+1))
            #             else:
            #                 for i in range(len(sortedAngleCID)):
            #                     queue.append((sortedAngleCID[i], depth+1))
            #         else:
            #             for i in range(len(sortedRadiusCID)):
            #                 queue.append((sortedRadiusCID[i], depth+1))
            # else:
            #     for CID in relativeRadiusAngle.keys():
            #         # if relativeRadiusAngle[CID][0] < RadiusRatioThreshold:
            #         #     queue.append((CID, depth))
            #         if relativeRadiusAngle[CID][1] < AngleRadianThreshold:
            #             queue.append((CID, depth))
            #         else:
            #             queue.append((CID, depth+1))
        
        
        ##################### test 1
        outputClID = set()
        majorRatio = min(0.4 + 0.1*order, 1)
        
        for segment in segToRadiusClID.keys():
            segToRadiusClID[segment].sort(key = lambda x : -x[0])
            
        for segment in segToRadiusClID.keys():
            if segment not in segments:
                outputClID.update(set([cl[1] for cl in segToRadiusClID[segment]]))
            else:
                end = int(len(segToRadiusClID[segment])*majorRatio)
                for i in range(end):
                    outputClID.add(segToRadiusClID[segment][i][1])
                    
        outputClID.update(depthToClID[0])
            
        newSkeleton = algSkeletonGraph.CSkeleton()
        
        cidMapper = {}
        #self.m_inputSkeleton.m_listCenterline[clID] = cl
        rootcenterlineID = 0
        for centerlineID in outputClID:
            centerline = skeleton.get_centerline(centerlineID)
            _centerline = algSkeletonGraph.CSkeletonCenterline(len(newSkeleton.m_listCenterline))
            cidMapper[_centerline.ID] = centerline.ID
            
            _centerline.Name = centerline.Name
            _centerline.Vertex = centerline.Vertex.copy()
            _centerline.Radius = centerline.Radius.copy()
            newSkeleton.m_listCenterline.append(_centerline)
            if self.m_inputSkeleton.m_rootCenterline.ID == centerline.ID:
                rootcenterlineID = _centerline.ID
        
        for cl in newSkeleton.ListCenterline :
            newSkeleton.init_conn_centerline(cl)
        # leaf centerline
        newSkeleton.extract_leaf_centerline()

        newSkeleton.build_graph()
        newSkeleton.build_kd_tree()
        newSkeleton.build_tree(rootcenterlineID)
        
        majorLeafCnt = newSkeleton.get_leaf_centerline_count()
        
        startClIdForMainVesselExtraction = set()
        newOutputClID = set()
        
        for lid in range(majorLeafCnt):
            if newSkeleton.get_leaf_centerline(lid).get_conn(0) is not None or newSkeleton.get_leaf_centerline(lid).get_conn(1) is not None:
                parentCLID, _ = skeleton.get_conn_centerline_id(cidMapper[newSkeleton.get_leaf_centerline(lid).ID])
                if parentCLID == -1:
                    continue
                _, eqOrderClIDs = skeleton.get_conn_centerline_id(parentCLID)
                if len(set(eqOrderClIDs) & outputClID) >= 2:
                    continue
                else:
                    startClIdForMainVesselExtraction.add(parentCLID)
                    for id_ in eqOrderClIDs:
                        outputClID.discard(id_)
                    
            else:
                pass
        
        additionalMainVessel = self.extract_main_centerline(startClIdForMainVesselExtraction, skeleton, segments)
        
        for ClID in additionalMainVessel:
            outputClID.add(ClID)
            
        return outputClID
        
    def _check_minor_score(self, skeleton):
        RadiusRatioThreshold = 0.25
        #     score = score + self._centerline_contrib(cl, 2.0)
        
        
        if len(self.m_opDragToggleCL.m_listSelectionKey) != 1:
            return 0
        
        for clKey in self.m_opDragToggleCL.m_listSelectionKey:
            id = data.CData.get_id_from_key(clKey)
            cl = skeleton.get_centerline(id)
            
            cl = skeleton.get_centerline(id)
            parentCLID, listChildCLID = skeleton.get_conn_centerline_id(id)
            parentR = np.mean([np.percentile(cl.Radius, 40),
                                np.percentile(cl.Radius, 50)])
            
            parentR2 = self.get_representative_radius(cl)
            
            relativeRadiusAngle = {}
            relativeAngleRadius2 = {}
            for CID in listChildCLID:
                childCL = skeleton.get_centerline(CID)
                childR = np.mean([np.percentile(childCL.Radius, 40),
                                  np.percentile(childCL.Radius, 50)])
                
                childR2 = self.get_representative_radius(childCL)
                    # 이전 대비 상대 angle, 상대 radius
                relativeRadiusAngle[CID] = ((1-childR/parentR), self.calculate_angle_radian_parent_child(cl, childCL))
                relativeAngleRadius2[CID] = ((1-childR2/parentR2), self.calculate_angle_radian_parent_child(cl, childCL))
                
                # print(f"CID : {childCL.Vertex.shape[0]}")
                
                # if childCL.Vertex.shape[0] < 5 and (1-childR2/parentR2) < RadiusRatioThreshold:
                    
                #     print(f"!!!!!!!!{CID}", file=sys.__stdout__, flush=True)
                #     if not childCL.is_leaf():
                #         print(f"!!!!!222222222222222222222!!!{CID}", file=sys.__stdout__, flush=True)
                        
                # if childCL.Vertex.shape[0] < 5 and (1-childR2/parentR2) < RadiusRatioThreshold and not childCL.is_leaf():
                #     print(f"!!!!!33333333333333333333333333333333333!!!{CID}", file=sys.__stdout__, flush=True)
#            print(relativeRadiusAngle, file=sys.__stdout__, flush=True)
            print(relativeAngleRadius2, file=sys.__stdout__, flush=True)
            print(f"Radius: {parentR2}", file=sys.__stdout__, flush=True)
            print(f"min Radius: {np.min(parentR2)}", file=sys.__stdout__, flush=True)
            
            
        #     parentCLID, listChildCLID = skeleton.get_conn_centerline_id(id)
            
        #     score = 0
            
        #     for clID_1 in listChildCLID:
                
        #         for clID_2 in listChildCLID:
                    
        #             if clID_1 == clID_2:
        #                 continue
        #             else:
        #                 cl1 = skeleton.get_centerline(clID_1)
        #                 cl2 = skeleton.get_centerline(clID_2)
        #                 score = max(score, self.calculate_angle_radian(cl1, cl2))
                    
        # return score
            
            
    def _select_minor_vessel(self, skeleton, order, segmentSet = []):
        if len(segmentSet) ==  0:
            startDepth = 0
            listcl = []
            visited = set()
            listcl.append(skeleton.RootCenterline.ID)
            visited.add(skeleton.RootCenterline.ID)
            queue = deque([(skeleton.RootCenterline.ID, startDepth)])
        

            iCLCnt = skeleton.get_centerline_count()
            radiusList = []
            for inx in range(0, iCLCnt) :
                cl = skeleton.get_centerline(inx)
                radiusList.append(np.mean(cl.Radius))
                
            q2 = np.percentile(radiusList, 50)  # median
            
            while queue:
                id, d = queue.popleft()
                # if d >= order:
                #     continue
                
                cl = skeleton.get_centerline(id)
                parentCLID, listChildCLID = skeleton.get_conn_centerline_id(id)

                for CID in listChildCLID:
                    if CID in visited:
                        continue
                    
                    childCL = skeleton.get_centerline(CID)
                    childMeanR = np.mean(childCL.Radius)
                    if d+1 > order and childMeanR < q2:
                        continue
                    visited.add(CID)
                    listcl.append(CID)
                    queue.append((CID, d+1))
        else:

            listClID = self.build_backbone_by_angle_based_depth(skeleton, segmentSet, order)
                            
        listKey = []
        for clID in listClID:
            pickingKey = data.CData.make_key(data.CData.s_skelTypeCenterline, self.InputSkelGroupID, clID)
            listKey.append(pickingKey)
        self.m_opDragToggleCL.process_reset_for_en()
        self.m_opDragToggleCL.add_toggle_selection_keys(listKey)
        self.m_opDragToggleCL.process()

    # protected
    def _find_selection_clid(self) -> list :
        '''
        ret : [clID0, clID1, .. ]
        '''
        xmin, xmax = sorted([self.m_startX, self.m_endX])
        ymin, ymax = sorted([self.m_startY, self.m_endY])

        npPt = self.App.project_points_to_display(self.InputSkeleton.m_listKDTreeAnchor)
        inside = ((npPt[:,0] >= xmin) & (npPt[:,0] <= xmax) & (npPt[:,1] >= ymin) & (npPt[:,1] <= ymax))
        selectedIndex = np.where(inside)[0]

        listID = set()
        for inx in selectedIndex :
            listID.add(self.InputSkeleton.m_listKDTreeAnchorID[inx])
        
        listID = list(listID)
        if len(listID) == 0 :
            return None
        return listID
    def _create_rt_actor(self) :
        self.m_rt = vtk.vtkPoints()
        self.m_rt.SetNumberOfPoints(4)
        for i in range(4):
            self.m_rt.SetPoint(i, 0, 0, 0)

        rect_poly = vtk.vtkPolyData()
        rect_poly.SetPoints(self.m_rt)

        rect_cells = vtk.vtkCellArray()
        rect_cells.InsertNextCell(5)
        for i in [0, 1, 2, 3, 0]:
            rect_cells.InsertCellPoint(i)
        rect_poly.SetLines(rect_cells)

        mapper = vtk.vtkPolyDataMapper2D()
        mapper.SetInputData(rect_poly)

        actor = vtk.vtkActor2D()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.3, 1.0, 0.3)
        actor.GetProperty().SetLineWidth(2.0)
        return actor
    def _update_rt_actor(self) :
        x0 = self.m_startX
        y0 = self.m_startY
        x1 = self.m_endX
        y1 = self.m_endY
        self.m_rt.SetPoint(0, x0, y0, 0)
        self.m_rt.SetPoint(1, x1, y0, 0)
        self.m_rt.SetPoint(2, x1, y1, 0)
        self.m_rt.SetPoint(3, x0, y1, 0)
        self.m_rt.Modified()
    

    @property
    def InputSkeleton(self) -> algSkeletonGraph.CSkeleton :
        return self.m_inputSkeleton
    @InputSkeleton.setter
    def InputSkeleton(self, skeleton : algSkeletonGraph.CSkeleton) :
        self.m_inputSkeleton = skeleton
    @property
    def InputSkelGroupID(self) -> int :
        return self.m_inputSkelGroupID
    @InputSkelGroupID.setter
    def InputSkelGroupID(self, inputSkelGroupID : int) -> int :
        self.m_inputSkelGroupID = inputSkelGroupID

    @property
    def ChildSelectionMode(self) -> bool :
        return self.m_opDragToggleCL.ChildSelectionMode
    @ChildSelectionMode.setter
    def ChildSelectionMode(self, mode : bool) :
        self.m_opDragToggleCL.ChildSelectionMode = mode
    


if __name__ == '__main__' :
    pass


# print ("ok ..")

