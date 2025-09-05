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
import operationColored as operation
import component as component
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
    def __init__(self, mediator):
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
        # if self.get_tpinfo_count() == 0 :
        #     return False
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
                color = dataInst.CLColor

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
                color = dataInst.CLColor
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

if __name__ == '__main__' :
    pass


# print ("ok ..")

