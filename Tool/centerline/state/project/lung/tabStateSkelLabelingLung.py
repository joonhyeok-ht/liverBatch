import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

from PySide6.QtCore import Qt, QObject
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QTextEdit
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileStateProjectPath = os.path.dirname(fileAbsPath)
fileStatePath = os.path.dirname(fileStateProjectPath)
fileAppPath = os.path.dirname(fileStatePath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileStateProjectPath)
sys.path.append(fileStatePath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)



import AlgUtil.algSpline as algSpline
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algLinearMath as algLinearMath

import data as data

import operationLung as operation #sally
import command.commandTerritory as commandTerritory
import command.commandTerritoryVessel as commandTerritoryVessel

import command.curveInfo as curveInfo

import tabState as tabState

import VtkObj.vtkObjText as vtkObjText
import vtkObjGuideMeshBound as vtkObjGuideMeshBound
import vtkObjGuideCLBound as vtkObjGuideCLBound
import vtkObjInterface as vtkObjInterface


class CTabStateSkelLabeling(tabState.CTabState) :
    s_guideBoundType = "guideBound"


    def __init__(self, mediator):
        super().__init__(mediator)
        try:
        # PyInstaller로 패키징된 실행 파일의 경우
            self.fileAbsPath = sys._MEIPASS
            self.fileAbsPath = os.getcwd() #"."
        except AttributeError:
            # 개발 환경에서
            self.fileAbsPath = os.path.abspath(os.path.dirname(__file__))
        #sally
        self.m_opSelectionCL = operation.COperationSelectionCL(mediator)
        self.m_guideBoundKey = ""
        self.m_skelCircle = None
        self.labelColorSeg = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 0.0]) #ff88ff #ffff00
        self.labelColorSub = algLinearMath.CScoMath.to_vec3([0.0, 1.0, 1.0]) #00ffff
        self.s_textTypeSub = 'textsub' # subsement labeling text
        

    def clear(self) :
        # input your code
        self.m_guideBoundKey = ""
        self.m_opSelectionCL.clear()
        self.m_opSelectionCL = None
        self.m_skelCircle = None
        super().clear()

    def process_init(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)
        if skeleton is None :
            return 

        opSelectionCL = self.m_opSelectionCL
        opSelectionCL.Skeleton = skeleton

        self.m_skelCircle = curveInfo.CSkelCircle(skeleton, 30)
        
        # labeling obj
        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            iCLInx = int(cl.get_vertex_count() / 2)
            pos = cl.get_vertex(iCLInx)
            activeCamera = self.m_mediator.get_active_camera()
            clName = cl.Name
           
            ## label이 없는 cl인 경우 초기 keytype을 sub로 설정함. (TODO : 초기값을 sub로 설정하는게 문제가 되는지 확인해야함)
            # if clName == '' :
            #     keytype = self.s_textTypeSub
            #     color = dataInst.CLColor
            # else :
            #     if self._is_seg_label(clName) :
            #         keytype = data.CData.s_textType
            #         color = self.labelColorSeg
            #     else :
            #         keytype = self.s_textTypeSub
            #         color = self.labelColorSub
            
            is_seg, color, keytype = self._is_seg_label(clName)

            key = data.CData.make_key(keytype, 0, cl.ID)
            vtkText = vtkObjText.CVTKObjText(activeCamera, pos, clName, 1.0)
            vtkText.KeyType = keytype
            vtkText.Key = key
            vtkText.Color = color
            dataInst.add_vtk_obj(vtkText)
        self.m_mediator.ref_key_type(data.CData.s_textType)
        self.m_mediator.ref_key_type(self.s_textTypeSub)

                
        # # centerline을 뽑은 object 외의 object를 가져와서 함께 화면에 표시 sally
        # dat_info_cnt = dataInst.DataInfo.get_info_count()
        # self.m_dispVesselIdx = (clinfoInx+1) % dat_info_cnt 
        # self.m_mediator.ref_key_type_groupID(dataInst.s_vesselType, self.m_dispVesselIdx) #sally
        self.m_checkDisplaySubLabel.setChecked(True)

        # display label list
        self.display_label_list(dataInst)
        self.arrange_checkboxes()

        self.m_mediator.update_viewer()
    def process(self) :
        pass
    def process_end(self) :
        opSelectionCL = self.m_opSelectionCL
        opSelectionCL.process_reset()
        if self.m_skelCircle is not None :
            self.m_skelCircle.clear()
            self.m_skelCircle = None
        self.m_mediator.remove_key_type(CTabStateSkelLabeling.s_guideBoundType)
        self.m_mediator.remove_key_type(data.CData.s_territoryType)
        self.m_mediator.remove_key_type(data.CData.s_textType) #sally
        self.m_mediator.remove_key_type(self.s_textTypeSub) #sally

        # 함께 화면에 표시된 object를 tab 전환시 안보이게 함. sally
        # dataInst = self.get_data()
        # self.m_mediator.unref_key_type_groupID(dataInst.s_vesselType, self.m_dispVesselIdx) #sally
        self.m_otherVesselCheckBoxList[0][0].setChecked(False)
        self.m_otherVesselCheckBoxList[1][0].setChecked(False)
        self.m_otherVesselCheckBoxList[2][0].setChecked(False)
        # self.m_checkDisplayOtherVessel.setChecked(False) #sally

        self.m_mediator.update_viewer()
    
    def display_label_list(self, dataInst : data.CData) :
        # TODO : clInfo 의 blenderName으로는 L,R을 완벽히 구분할 수 없음(Bronchus같은 경우엔 메쉬이름에 LR구분이 없으므로), 
        # 그래서 terriInfo에서 blenderName을 가지고 있는 organ명을 찾아서 organ(lobe) 의 이름을 보고 L,R을 알아내야함.
        
        clinfoInx = self.get_clinfo_index()
        clInfo = dataInst.DataInfo.get_clinfo(clinfoInx)
        vesselName = clInfo.get_input_blender_name()
        print(f"curr centerline obj : {vesselName}")  #Artery or Bronchus 구분용

        # organName : "Lung_LLL_L" or "Lung_RLL_R"  => L, R 구분용
        terriInfo = dataInst.get_terriinfo(0) # 어떤 Lobe이든 L,R만 보면되므로 처음 하나만 가져와도 됨.
        organName = terriInfo.BlenderName
        
        # 라벨 생성하기
        # 같은 Name으로 labeling된 cl 모으기 #sally        
        # seg_list_in_lobe_r = [[1,2,3], [4,5], [6,7,8,9,10]] # Right Lung lobe index
        # seg_list_in_lobe_l = [[12,3,4,5],[6,78,9,10]] # Left Lung lobe index
        seg_list_in_lobe_r = [1,2,3, 4,5, 6,7,8,9,10] # Right Lung lobe index
        # subseg_list_in_lobe_r = [{1:['a','b']},{2:['a','b']},{3:['a','b']}, {4:['a','b']},{5:['a','b']}, {6:['a','b','c']},{7:['a','b']},{8:['a','b']},{9:['a','b']},{10:['a','b','c']}] 
        subseg_list_in_lobe_r = {1:['a','b'],2:['a','b'],3:['a','b'], 4:['a','b'],5:['a','b'], 6:['a','b','c'],7:['a','b'],8:['a','b'],9:['a','b'],10:['a','b','c']} 
        seg_list_in_lobe_l = [12,3,4,5, 6,78,9,10] # Left Lung lobe index
        subseg_list_in_lobe_l = {12:['a','b','c'],3:['a','b','c'],4:['a','b'],5:['a','b'], 6:['a','b','c','s'],78:['a','b'],9:['a','b'],10:['a','b','c']} 

        dr = ''
        if '_R' in organName : # Right
            subseg_idx_list = subseg_list_in_lobe_r
            dr = 'R'
        else : # Left
            subseg_idx_list = subseg_list_in_lobe_l
            dr = 'L'
        ve = 'A'
        if 'Bronchus' in vesselName :
            ve = 'B'
        elif 'Vein' in vesselName :
            ve = 'V'
        
        label_list = ["----- Label List -----"]
        for segIdx in subseg_idx_list.keys() :
            seg_label = f"TP_{dr}{ve}{segIdx}"
            label_list.append(seg_label)
            for sub in subseg_idx_list[segIdx] :
                subseg_label = f"TP_{dr}{ve}{segIdx}_{sub}"
                label_list.append(subseg_label)

        joined_text = "\n".join(label_list)
        self.m_editLabelList.setPlainText(joined_text)

    def arrange_checkboxes(self) :
        dataInst = self.get_data()
        # clinfoCnt = dataInst.DataInfo.get_info_count()
        clinfoInx = self.get_clinfo_index() #현재 활성화된 cl의 index
        # clInfo = dataInst.DataInfo.get_clinfo(clinfoInx)
        # vesselName = clInfo.get_input_blender_name()
        
        for idx, checkBoxSet in enumerate(self.m_otherVesselCheckBoxList):
            clInfo = dataInst.DataInfo.get_clinfo(idx)
            vesselName = clInfo.get_input_blender_name()            
            checkBoxSet[0].setChecked(False)
            checkBoxSet[0].setText(vesselName)
            checkBoxSet[1] = vesselName
            if idx == clinfoInx : #현재 활성화된 centerline object는 선택되지 않도록 disable함.
                checkBoxSet[0].setEnabled(False)
            else :
                checkBoxSet[0].setEnabled(True)

    def init_ui(self) :
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        label = QLabel("-- Selection Operator --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        self.m_checkCLHierarchy = QCheckBox("Selection Centerline Hierarchy ")
        self.m_checkCLHierarchy.setChecked(False)
        self.m_checkCLHierarchy.stateChanged.connect(self._on_check_cl_hierarchy)
        tabLayout.addWidget(self.m_checkCLHierarchy)

        self.m_checkCLAncestor = QCheckBox("Selection Centerline Ancestor ")
        self.m_checkCLAncestor.setChecked(False)
        self.m_checkCLAncestor.stateChanged.connect(self._on_check_cl_ancestor)
        tabLayout.addWidget(self.m_checkCLAncestor)

        # btn = QPushButton("Apply Centerline Root to Selection")
        # btn.setStyleSheet(self.m_mediator.m_styleSheetBtn)
        # btn.clicked.connect(self._on_btn_apply_root_cl)
        # tabLayout.addWidget(btn)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)


        label = QLabel("-- Centerline Info --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        layout, self.m_editCLID = self.m_mediator.create_layout_label_editbox("Centerline ID", True)
        tabLayout.addLayout(layout)

        layout, self.m_editCLName = self.m_mediator.create_layout_label_editbox("Centerline Label", False)
        self.m_editCLName.returnPressed.connect(self._on_return_pressed_clname)
        tabLayout.addLayout(layout)

        layout, self.m_editCLPtCnt = self.m_mediator.create_layout_label_editbox("Centerline Point Count", True)
        tabLayout.addLayout(layout)

        layout, self.m_editCLLength = self.m_mediator.create_layout_label_editbox("Centerline Length(mm)", True)
        tabLayout.addLayout(layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        # sally : Artery, Bronchus, Vein 체크박스 생성. 
        self.m_otherVesselCheckBoxList = []
        for idx in range(0, 3):
            vesselCheckBox = QCheckBox('--')
            vesselCheckBox.setChecked(False)
            vesselCheckBox.stateChanged.connect(self._on_check_diplay_other_vessel)
            tabLayout.addWidget(vesselCheckBox)
            self.m_otherVesselCheckBoxList.append([vesselCheckBox, vesselCheckBox.text()])
        # self.m_checkDisplayOtherVessel = QCheckBox("Display The Other Vessel ")
        # self.m_checkDisplayOtherVessel.setChecked(False)
        # self.m_checkDisplayOtherVessel.stateChanged.connect(self._on_check_diplay_other_vessel)
        # tabLayout.addWidget(self.m_checkDisplayOtherVessel)
        #sally
        self.m_checkDisplaySubLabel = QCheckBox("Display SubSegment Labels ")
        self.m_checkDisplaySubLabel.setChecked(True)
        self.m_checkDisplaySubLabel.stateChanged.connect(self._on_check_diplay_subsegment_labels)
        tabLayout.addWidget(self.m_checkDisplaySubLabel)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        btn = QPushButton("Save Centerline")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_save_centerline)
        tabLayout.addWidget(btn)

        self.m_editLabelList = QTextEdit()
        self.m_editLabelList.setTextInteractionFlags(Qt.TextSelectableByMouse)
        # scrollbar style
        scrollbar_style = """
        QScrollBar:vertical {
            background: #f0f0f0;
            width: 12px;
            margin: 0px 0px 0px 0px;
        }
        QScrollBar::handle:vertical {
            background: #8888ff;
            min-height: 20px;
            border-radius: 6px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            background: none;
            height: 0px;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }
        """
        self.m_editLabelList.setStyleSheet(scrollbar_style)

        # 사이즈 설정
        self.m_editLabelList.setMinimumSize(300, 300)  # 창이 작으면 스크롤 생김
        tabLayout.addWidget(self.m_editLabelList)

        # lastUI = line
        lastUI = self.m_editLabelList
        tabLayout.setAlignment(lastUI, Qt.AlignmentFlag.AlignTop)



        


    def clicked_mouse_rb(self, clickX, clickY) :
        listExceptKeyType = [
            # data.CData.s_territoryType,
            data.CData.s_vesselType,
            # data.CData.s_organType,
            data.CData.s_textType,
            self.s_textTypeSub, #sally (subsegment label)
        ]
        key = self.m_mediator.picking(clickX, clickY, listExceptKeyType)
        if key == "" or data.CData.get_type_from_key(key) != data.CData.s_skelTypeCenterline :
            key = ""
        operation.COperationSelectionCL.clicked(self.m_opSelectionCL, key)
        self._update_clinfo()
        self.m_mediator.update_viewer()
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        listExceptKeyType = [
            # data.CData.s_territoryType,
            data.CData.s_vesselType,
            # data.CData.s_organType,
            data.CData.s_textType,
        ]
        key = self.m_mediator.picking(clickX, clickY, listExceptKeyType)
        if key == "" or data.CData.get_type_from_key(key) != data.CData.s_skelTypeCenterline :
            key = ""
        operation.COperationSelectionCL.multi_clicked(self.m_opSelectionCL, key)
        self._update_clinfo()
        self.m_mediator.update_viewer()


    # protected   
    def _check_cl_hierarchy(self, bCheck : bool) :
        operation.COperationSelectionCL.checked_hierarchy(self.m_opSelectionCL, bCheck)
        self.m_mediator.update_viewer()
    def _check_cl_ancestor(self, bCheck : bool) :
        operation.COperationSelectionCL.checked_ancestor(self.m_opSelectionCL, bCheck)
        self.m_mediator.update_viewer()
    def _check_display_other_vessel(self, sender : QObject, bCheck : bool) : #sally
        # centerline을 뽑은 object 외의 object를 가져와서 함께 화면에서 표시or숨김 
        clinfoInx = self.get_clinfo_index()
        dataInst = self.get_data()            
        # clinfoCnt = dataInst.DataInfo.get_info_count()
        # self.m_dispVesselIdx = (clinfoInx+1) % clinfoCnt 
        for index, chbox in enumerate(self.m_otherVesselCheckBoxList) :
            # chbox[0].
            # if sender.text() in chbox :
            
                # if bCheck :
                if index == clinfoInx :
                    continue
                if chbox[0].isChecked() :
                    self.m_mediator.ref_key_type_groupID(dataInst.s_vesselType, index) 
                    self.m_mediator.refresh_key_type_groupID(dataInst.s_vesselType, index, algLinearMath.CScoMath.to_vec3(self.m_mediator.m_colorList[7]), 1.0)
                else :
                    self.m_mediator.refresh_key_type_groupID(dataInst.s_vesselType, index, algLinearMath.CScoMath.to_vec3([1.0, 1.0, 1.0]), 0.3)
                    self.m_mediator.unref_key_type_groupID(dataInst.s_vesselType, index) 
                    
        self.m_mediator.update_viewer()
    # def _check_display_other_vessel(self, bCheck : bool) : #sally
    #     # centerline을 뽑은 object 외의 object를 가져와서 함께 화면에서 표시or숨김 
    #     clinfoInx = self.get_clinfo_index()
    #     dataInst = self.get_data()            
    #     dat_info_cnt = dataInst.DataInfo.get_info_count()
    #     self.m_dispVesselIdx = (clinfoInx+1) % dat_info_cnt 
    #     if bCheck :
    #         self.m_mediator.ref_key_type_groupID(dataInst.s_vesselType, self.m_dispVesselIdx) 
    #         self.m_mediator.refresh_key_type_groupID(dataInst.s_vesselType, self.m_dispVesselIdx, algLinearMath.CScoMath.to_vec3(self.m_mediator.m_colorList[7]), 1.0)
    #     else :
    #         self.m_mediator.refresh_key_type_groupID(dataInst.s_vesselType, self.m_dispVesselIdx, algLinearMath.CScoMath.to_vec3([1.0, 1.0, 1.0]), 0.3)
    #         self.m_mediator.unref_key_type_groupID(dataInst.s_vesselType, self.m_dispVesselIdx) 
            
    #     self.m_mediator.update_viewer()
    def _check_display_subsegment_labels(self, bCheck : bool) : #sally
        # subsegment label 들을 화면에 표시/숨김 한다.
        if bCheck : # display subsegment label
            self.m_mediator.ref_key_type(self.s_textTypeSub)
        
        else :
            self.m_mediator.unref_key_type(self.s_textTypeSub)
        self.m_mediator.update_viewer()

    def _is_seg_label(self, label) : # label 이 Seg or Sub 중 어느 타입인지 검사. 빈문자열인 경우 디폴트 Sub-Seg임.
        splt = label.split('_')
        if label == '' or len(splt) > 2: # ex) '' or 'TP_RA5_a'     Sub-Segment type
            return False, self.labelColorSub, self.s_textTypeSub
        else :            # ex)'TP_RA5'  Segment type
            return True, self.labelColorSeg, data.CData.s_textType

    def _update_clinfo(self) :
        self.m_editCLID.setText("-1")
        self.m_editCLName.setText("")
        self.m_editCLPtCnt.setText("0")
        self.m_editCLLength.setText("0")

        opSelectionCL = self.m_opSelectionCL
        iCnt = opSelectionCL.get_selection_key_count()
        if iCnt == 0 :
            return
        
        clKey = opSelectionCL.get_selection_key(0)
        keyType, groupID, id = data.CData.get_keyinfo(clKey)
        skeleton = opSelectionCL.Skeleton
        if skeleton is None :
            return
        
        cl = skeleton.get_centerline(id)
        length = float(algSpline.CCurveInfo.get_curve_len(cl.Vertex))
        self.m_editCLID.setText(f"{cl.ID}")
        self.m_editCLName.setText(f"{cl.Name}")
        self.m_editCLPtCnt.setText(f"{cl.Vertex.shape[0]}")
        self.m_editCLLength.setText(f"{length}")
    def _update_clname(self, clName : str) :
        opSelectionCL = self.m_opSelectionCL
        iCnt = opSelectionCL.get_selection_key_count()
        if iCnt == 0 :
            return
        skeleton = opSelectionCL.Skeleton
        if skeleton is None :
            return
        
        retListKey = []
        retListKey += opSelectionCL.m_listSelectionKey
        retListKey += opSelectionCL.m_listChildSelectionKey
        retListKey += opSelectionCL.m_listParentSelectionKey
        
        self.__update_clname_with_key(skeleton, retListKey, clName)
        self.m_mediator.update_viewer()

    # def _changed_terri_organ_index(self, index : int) : #sally Territory탭에 있던 코드 가져와서 수정함
    #     # self.m_mediator.remove_key_type(data.CData.s_territoryType)

    #     dataInst = self.get_data()
    #     if dataInst.Ready == False : 
    #         return
    #     if self.m_organKey == "" :
    #         return
    #     self.m_mediator.unref_key(self.m_organKey)

    #     self.m_organKey = data.CData.make_key(data.CData.s_organType, 0, index)
    #     organObj = dataInst.find_obj_by_key(self.m_organKey)
    #     if organObj is None :
    #         print(f"not found organObj : {self.m_organKey}")
    #         return
    #     self.m_mediator.ref_key(self.m_organKey)
    #     self.m_mediator.update_viewer()

    # ui event
    def _on_check_cl_hierarchy(self, state) :
        '''
        state
            - 0 : unchecked
            - 1 : partially checked
            - 2 : checked
        '''
        if state == 2 :
            bCheck = True
        else :
            bCheck = False
        self._check_cl_hierarchy(bCheck)
    def _on_check_cl_ancestor(self, state) :
        '''
        state
            - 0 : unchecked
            - 1 : partially checked
            - 2 : checked
        '''
        if state == 2 :
            bCheck = True
        else :
            bCheck = False
        self._check_cl_ancestor(bCheck)
    def _on_return_pressed_clname(self):
        # Enter키를 누르면 호출되는 함수
        clName = self.m_editCLName.text()  # QLineEdit에 입력된 텍스트를 가져옴
        self._update_clname(clName)
    def _on_check_diplay_other_vessel(self, state) : #sally
        '''
        state
            - 0 : unchecked
            - 1 : partially checked
            - 2 : checked
        '''
        if state == 2 :
            bCheck = True
        else :
            bCheck = False
        sender: QObject = self.m_mediator.m_mainWidget.sender()
        self._check_display_other_vessel(sender, bCheck)
    def _on_check_diplay_subsegment_labels(self, state) : #sally
        '''
        state
            - 0 : unchecked
            - 1 : partially checked
            - 2 : checked
        '''
        if state == 2 :
            bCheck = True
        else :
            bCheck = False
        self._check_display_subsegment_labels(bCheck) #sally
    def _on_btn_save_centerline(self) : #sally
        self.m_mediator.save_cl()

    # private
    def __update_clname_with_key(self, skeleton : algSkeletonGraph.CSkeleton, listKey : list, clName : str) :
        dataInst = self.get_data()

        for clKey in listKey :
            keyType, groupID, id = data.CData.get_keyinfo(clKey)
            cl = skeleton.get_centerline(id)
            oldName = cl.Name
            cl.Name = clName
            
            # 빈clName 입력된 경우 원래 라벨 타입이 뭔지 알아야 textObj를 찾을 수 있으므로 기존값도 얻어옴.
            # if clName == '' :
            #     cmpName = oldName
            # else :
            #     cmpName = clName
            oldType, old_txt_color, old_txt_type = self._is_seg_label(oldName)
            newType, new_txt_color, new_txt_type = self._is_seg_label(clName)
            
            # if self._is_seg_label(cmpName) : # segment label인 경우 subsegment라벨과 다른 색상으로 설정
            #     txtcolor = self.labelColorSeg
            #     texttype = data.CData.s_textType
            # else :
            #     txtcolor = self.labelColorSub
            #     texttype = self.s_textTypeSub

            # 우선 기존key로 obj를 찾아옴.
            textKey = data.CData.make_key(old_txt_type, 0, cl.ID)
            textObj = dataInst.find_obj_by_key(textKey)

            if textObj is not None :
                if oldType != newType : # 기존 text type과 입력 label의 type이 다르면 기존 txt obj를 삭제하고 새로 obj를 등록한다.
                    self.m_mediator.remove_key(textKey)

                    newTextKey = data.CData.make_key(new_txt_type, 0, cl.ID)
                    activeCamera = self.m_mediator.get_active_camera()
                    iCLInx = int(cl.get_vertex_count() / 2)
                    pos = cl.get_vertex(iCLInx)
                    vtkText = vtkObjText.CVTKObjText(activeCamera, pos, clName, 1.0)
                    vtkText.KeyType = new_txt_type
                    vtkText.Key = newTextKey
                    vtkText.Color = new_txt_color
                    vtkText.Text = clName
                    dataInst.add_vtk_obj(vtkText)
                    self.m_mediator.ref_key(newTextKey)
                else : # 기존과 같은 text type이고 label만 바뀌는 경우.
                    textObj.Text = clName
                    textObj.Color = new_txt_color
                
                #sally
                # self.m_mediator.refresh_key(clKey, algLinearMath.CScoMath.to_vec3([0.0, 0.0, 1.0])) #sally
                clcolor = self.m_mediator.get_cl_color(clName)
                clkey = data.CData.make_key(data.CData.s_skelTypeCenterline, groupID, cl.ID)
                clObj = dataInst.find_obj_by_key(clkey)
                clObj.Color = clcolor #algLinearMath.CScoMath.to_vec3([0.0, 0.0, 1.0]) 
                

if __name__ == '__main__' :
    pass


# print ("ok ..")

