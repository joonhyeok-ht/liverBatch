import sys
import os
import numpy as np
import re
import shutil
import vtk
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox
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

import userDataLung as userDataLung
import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algSkeletonGraph as algSkeletonGraph

import command.commandTerritory as commandTerritory

import data as data

import operationLung as operation  #sally

import tabState as tabState

import subTerritory.clMaskLung as clMask #sally

import vtkObjInterface as vtkObjInterface
import vtkObjOutsideCL as vtkObjOutsideCL


class CTabStateTerritory(tabState.CTabState) :
    s_outsideKeyType = "outsideCLType"

    def __init__(self, mediator):
        super().__init__(mediator)

        try:
        # PyInstaller로 패키징된 실행 파일의 경우
            self.fileAbsPath = sys._MEIPASS
            self.fileAbsPath = os.getcwd() #"."
        except AttributeError:
            # 개발 환경에서
            self.fileAbsPath = os.path.abspath(os.path.dirname(__file__))
        # input your code
        self.m_organKey = ""
        self.m_clMask = None
        self.m_userData = None
        self.m_opSelectionCL = operation.COperationSelectionCL(mediator)
        self.m_opSelectionBr = operation.operation.COperationSelectionBr(mediator)#sally
    def clear(self) :
        # input your code
        self.m_opSelectionBr.clear()
        self.m_opSelectionBr = None
        self.m_opSelectionCL.clear()
        self.m_opSelectionCL = None
        self.m_clMask = None
        self.m_userData = None
        self.m_organKey = ""
        super().clear()    
    def process_init(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        
        self.m_userData = self._get_userdata()
        if self.m_userData is None :
            return
        
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)
        if skeleton is None :
            return 
        
        iCnt = dataInst.get_terriinfo_count()
        for terriInx in range(0, iCnt) :
            terriInfo = dataInst.get_terriinfo(terriInx)
            organName = terriInfo.BlenderName
            self._add_terricb_organ_name(organName)
        
        selectedOrganName = self._get_terricb_organ_name()
        findTerriInx = dataInst.find_terriinfo_index_by_blender_name(selectedOrganName)
        self.m_organKey = data.CData.make_key(data.CData.s_organType, 0, findTerriInx)
        organObj = dataInst.find_obj_by_key(self.m_organKey)
        if organObj is None :
            print(f"not found organObj : {self.m_organKey}")
            return
        self.m_mediator.ref_key(self.m_organKey)

        opSelectionCL = self.m_opSelectionCL
        opSelectionCL.Skeleton = skeleton

        self.m_mediator.remove_key_type(CTabStateTerritory.s_outsideKeyType)
        self.m_clMask = clMask.CCLMask(organObj.PolyData)
        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            self.m_clMask.attach_cl(cl)
        self._load_outside_key(clinfoInx)
        self.m_mediator.ref_key_type(CTabStateTerritory.s_outsideKeyType)

        self.m_mediator.update_viewer()
        
    def process(self) :
        pass
    def process_end(self) :
        if self.m_clMask is not None :
            self.m_clMask.clear()
        self.m_clMask = None
        self._clear_terricb_organ_name()

        opSelectionCL = self.m_opSelectionCL
        opSelectionCL.process_reset()
        if self.m_organKey == "" :
            return

        self.m_mediator.unref_key(self.m_organKey)
        self.m_mediator.remove_key_type(data.CData.s_territoryType)
        self.m_mediator.remove_key_type(CTabStateTerritory.s_outsideKeyType)
        self.m_mediator.update_viewer()

    def init_ui(self) :
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        label = QLabel("-- Territory Info --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        layout, self.m_cbTerriOrganName = self.m_mediator.create_layout_label_combobox("Select Organ")
        self.m_cbTerriOrganName.currentIndexChanged.connect(self._on_cb_terri_organ_name)
        tabLayout.addLayout(layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        btn = QPushButton("Do Territory")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_territory)
        tabLayout.addWidget(btn)
        
        btn = QPushButton("Save Territory")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_save_territory)
        tabLayout.addWidget(btn)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        btn = QPushButton("Do All Territory (Segment)")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_all_territory)
        tabLayout.addWidget(btn)

        btn = QPushButton("Do All Territory (SubSegment)")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_all_territorySub)
        tabLayout.addWidget(btn)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        btn = QPushButton("Territory.blend (overwrite)")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_import_territory)
        tabLayout.addWidget(btn)

        btn = QPushButton("PatientID.blend (overwrite)")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_open_patientid_blender_with_terri)
        tabLayout.addWidget(btn)

        btn = QPushButton("Wrap-up (overwrite) + Check Decimation")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_wrap_up)
        tabLayout.addWidget(btn)

        btn = QPushButton("Project UV Mapping (overwrite)")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_wrap_up_second)
        tabLayout.addWidget(btn)

        # btn = QPushButton("Save All Territory")
        # btn.setStyleSheet(self.get_btn_stylesheet())
        # btn.clicked.connect(self._on_btn_save_all_territory)
        # tabLayout.addWidget(btn)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        lastUI = line
        tabLayout.setAlignment(lastUI, Qt.AlignmentFlag.AlignTop)

    def clicked_mouse_rb(self, clickX, clickY) :
        listExceptKeyType = [
            data.CData.s_territoryType,
            data.CData.s_vesselType,
            data.CData.s_organType,
        ]
        key = self.m_mediator.picking(clickX, clickY, listExceptKeyType)
        if key == "" or data.CData.get_type_from_key(key) != data.CData.s_skelTypeCenterline :
            key = ""

        self.m_mediator.remove_key_type(data.CData.s_territoryType)
        operation.COperationSelectionCL.clicked(self.m_opSelectionCL, key)
        self.m_mediator.update_viewer()
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        listExceptKeyType = [
            data.CData.s_territoryType,
            data.CData.s_vesselType,
            data.CData.s_organType,
        ]
        key = self.m_mediator.picking(clickX, clickY, listExceptKeyType)
        if key == "" or data.CData.get_type_from_key(key) != data.CData.s_skelTypeCenterline :
            key = ""

        self.m_mediator.remove_key_type(data.CData.s_territoryType)
        operation.COperationSelectionCL.multi_clicked(self.m_opSelectionCL, key)
        self.m_mediator.update_viewer()
    def check_cl_hierarchy(self, bCheck : bool) :
        self.m_mediator.remove_key_type(data.CData.s_territoryType)
        operation.COperationSelectionCL.checked_hierarchy(self.m_opSelectionCL, bCheck)
        self.m_mediator.update_viewer()


    # protected
    def _get_userdata(self) -> userDataLung.CUserDataLung :
        return self.get_data().find_userdata(userDataLung.CUserDataLung.s_userDataKey)  
    def _load_outside_key(self, groupID : int) :
        dataInst = self.get_data()
        skeleton = dataInst.get_skeleton(groupID)
        if skeleton is None :
            return

        clCnt = skeleton.get_centerline_count()
        for clInx in range(0, clCnt) :
            cl = skeleton.get_centerline(clInx)
            clObj = vtkObjOutsideCL.CVTKObjOutsideCL(cl, self.m_clMask, dataInst.CLSize)
            if clObj.Ready == False :
                continue

            key = data.CData.make_key(CTabStateTerritory.s_outsideKeyType, 0, cl.ID)
            clObj.KeyType = CTabStateTerritory.s_outsideKeyType
            clObj.Key = key
            clObj.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
            clObj.Opacity = 1.0
            dataInst.add_vtk_obj(clObj)
    def _changed_terri_organ_index(self, index : int) :
        self.m_mediator.remove_key_type(data.CData.s_territoryType)

        dataInst = self.get_data()
        if dataInst.Ready == False : 
            return
        if self.m_organKey == "" :
            return
        self.m_mediator.unref_key(self.m_organKey)

        self.m_organKey = data.CData.make_key(data.CData.s_organType, 0, index)
        organObj = dataInst.find_obj_by_key(self.m_organKey)
        if organObj is None :
            print(f"not found organObj : {self.m_organKey}")
            return
        self.m_mediator.ref_key(self.m_organKey)

        # outside centerline point 수정 루틴을 추가 (sally)
        self.m_mediator.remove_key_type(CTabStateTerritory.s_outsideKeyType)
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)
        self.m_clMask = clMask.CCLMask(organObj.PolyData)
        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            self.m_clMask.attach_cl(cl)
        self._load_outside_key(clinfoInx)
        self.m_mediator.ref_key_type(CTabStateTerritory.s_outsideKeyType)


        self.m_mediator.update_viewer()

    def extract_number(label_txt) : #sally
        return re.sub(r'\D', '', label_txt)
    
    def _do_all_terri(self, isSegMode : bool) : #sally
        self.m_mediator.remove_key_type(data.CData.s_territoryType)
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        if self.m_organKey == "" :
            return

        clinfoinx = self.get_clinfo_index()  # lung artery 0 or bronchus 1
        skeleton = dataInst.get_skeleton(clinfoinx)
        if skeleton is None :
            return
      
        # opSelectionCL = self.m_opSelectionCL
        # retList = opSelectionCL.get_selection_cl_list() #territory나눌 대상 혈관센터라인들 id list
        # if retList is None :
        #     print("not selecting centerline")
        #     return
        
        selectedOrganName = self._get_terricb_organ_name() # Lung_RUL_R, Lung_RML_R, Lung_RLL_R or Lung_LUL_L, Lung_LLL_L 중에서 현재 리스트박스에서 선택된 organ명
        selectedOrganIdx = self._get_terricb_organ_index() # sally: 현재 선택된 organ의 index
        findTerriInx = dataInst.find_terriinfo_index_by_blender_name(selectedOrganName) #option.json에서 Lung_RML_R의 SegmentInfo상에서의 인덱스
        if findTerriInx == -1 :
            return
        
        # 이건 어디서 사용하는 거지?
        self.m_organKey = data.CData.make_key(data.CData.s_organType, 0, findTerriInx)
        # terriInfo에는 blendername, reconType, spacing이 저장돼있음
        terriInfo = dataInst.find_terriinfo_by_blender_name(selectedOrganName)
        
        # 같은 Name으로 labeling된 cl 모으기 #sally        
        seg_list_in_lobe_r = [[1,2,3], [4,5], [6,7,8,9,10]] # Right Lung lobe index
        seg_list_in_lobe_l = [[12,3,4,5],[6,78,9,10]] # Left Lung lobe index
        if '_R' in selectedOrganName : # Right
            seg_idx_list = seg_list_in_lobe_r
        else : # Left
            seg_idx_list = seg_list_in_lobe_l


        cl_ids_by_label_dic = {}
        for inx in range(0, skeleton.get_centerline_count()) :
            cl = skeleton.get_centerline(inx)
            if cl.Name != '': # cl.Name = label text
                print(f"_do_all_terri() cl.Name = {cl.Name}")
                # 해당 lobe에 포함된 segment index만 저장하기 위한 검사
                segnum = CTabStateTerritory.extract_number(cl.Name)
                if int(segnum) in seg_idx_list[selectedOrganIdx] :

                    ###아래 코드는 segment, subsegment 혼합 라벨링을 사용하는 경우에 쓰는 코드임.
                    # # TP_RA1, TP_RA1_a 등 seg와 subseg명이 섞여있으므로 모드(seg or subseg)에 따라 cl.Name을 원하는 범위까지만 사용해야함.
                    
                    if isSegMode : # seg mode인경우, sub-seg label에서 처음 두 토큰만 가져와서 같은 이름끼리 seg로 그룹을 만듬.
                        splt = cl.Name.split('_') 
                        clValidName = f"{splt[0]}_{splt[1]}" # segment mode인 경우에 한함.
                    else :
                        clValidName = cl.Name

                    if clValidName not in cl_ids_by_label_dic.keys() :
                        cl_ids_by_label_dic[clValidName] = [inx]
                    else : # cl.Name이 이미 dic에 있으면 id를 추가
                        cl_ids_by_label_dic[clValidName].append(inx)
                    # if cl.Name not in cl_ids_by_label_dic.keys() :
                    #     cl_ids_by_label_dic[cl.Name] = [inx]
                    # else : # cl.Name이 이미 dic에 있으면 id를 추가
                    #     cl_ids_by_label_dic[cl.Name].append(inx)

        
        print(f"_do_all_terri() : {cl_ids_by_label_dic}")  
        # {'TP_RA1': [81, 99, 110, 111, 124, 125, 134, 135, 136, 137, 144, 145, 146, 147, 148, 153, 154, 155, 156, 157, 158, 174], 
        #  'TP_RA0': [96], 
        #  'TP_RA4': [100, 112, 113, 126, 127, 128, 129, 138, 139], 
        #  'TP_RA2': [119, 130, 131, 140, 141, 142, 143, 149, 150, 151, 152, 159, 160, 161, 162, 163, 164, 175, 176], 
        #  'TP_RA3': [120, 132, 133]}


        for index, labelstr in enumerate(cl_ids_by_label_dic.keys()) :
            print(f"_do_all_terri() : territory - {labelstr} --->")
            # 아래 루틴을 Name으로 구분된 혈관별로 수행
            # skeleton에서 같은 Name을 가지는 CL의 id들을 가져오기->territory수행 Name을 보고 territory의 이름정하기
            cmd = commandTerritory.CCommandTerritory(self.m_mediator)
            cmd.InputData = dataInst
            cmd.InputSkeleton = skeleton
            cmd.InputCLMask = self.m_clMask 
            cmd.InputTerriInfo = terriInfo
            for clid in cl_ids_by_label_dic[labelstr] :
                cmd.add_cl_id(clid)
            cmd.process()
            terriPolyData = cmd.OutputTerriPolyData
            cmd.clear() #sally
            if terriPolyData is None :
                print("_do_all_terri() : failed to territory")
                return
            
            # key = data.CData.make_key(data.CData.s_territoryType, organ 인덱스로하면될듯, label명?)
            key = data.CData.make_key(data.CData.s_territoryType, selectedOrganIdx, index)
            terriObj = vtkObjInterface.CVTKObjInterface()
            terriObj.KeyType = data.CData.s_territoryType
            terriObj.Key = key
            terriObj.Color = algLinearMath.CScoMath.to_vec3([0.5, 0.0, 0.5])
            terriObj.Opacity = 1.0 #0.5
            terriObj.PolyData = terriPolyData
            dataInst.add_vtk_obj(terriObj)

            # save 
            polyData = terriObj.PolyData
            saveFullPath = os.path.join(dataInst.get_terri_out_path(), f"{labelstr}.stl")
            algVTK.CVTK.save_poly_data_stl(saveFullPath, polyData)
            print(f"_do_all_terri() : Territory({saveFullPath}) file saved.")
        
            self.m_mediator.ref_key(key)
        self.m_mediator.update_viewer()

    def _do_terri(self) :
        self.m_mediator.remove_key_type(data.CData.s_territoryType)

        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        if self.m_organKey == "" :
            return

        clinfoinx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoinx)
        if skeleton is None :
            return
        
        opSelectionCL = self.m_opSelectionCL
        retList = opSelectionCL.get_selection_cl_list()
        if retList is None :
            print("not selecting centerline")
            return
        
        selectedOrganName = self._get_terricb_organ_name()
        findTerriInx = dataInst.find_terriinfo_index_by_blender_name(selectedOrganName)
        if findTerriInx == -1 :
            return
        
        self.m_organKey = data.CData.make_key(data.CData.s_organType, 0, findTerriInx)
        terriInfo = dataInst.find_terriinfo_by_blender_name(selectedOrganName)
        
        cmd = commandTerritory.CCommandTerritory(self.m_mediator)
        cmd.InputData = dataInst
        cmd.InputSkeleton = skeleton
        cmd.InputCLMask = self.m_clMask
        cmd.InputTerriInfo = terriInfo
        for id in retList :
            cmd.add_cl_id(id)
        cmd.process()
        terriPolyData = cmd.OutputTerriPolyData
        if terriPolyData is None :
            print("failed to territory")
            return
        
        key = data.CData.make_key(data.CData.s_territoryType, 0, 0)
        terriObj = vtkObjInterface.CVTKObjInterface()
        terriObj.KeyType = data.CData.s_territoryType
        terriObj.Key = key
        terriObj.Color = algLinearMath.CScoMath.to_vec3([0.5, 0.0, 0.5])
        terriObj.Opacity = 0.5
        terriObj.PolyData = terriPolyData
        dataInst.add_vtk_obj(terriObj)
        self.m_mediator.ref_key(key)
        self.m_mediator.update_viewer()
    def _save_terri(self, stlFullPath : str) :
        dataInst = self.get_data()
        if dataInst.Ready == False : 
            return 
        if self.m_organKey == "" :
            return

        clinfoinx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoinx)
        if skeleton is None :
            return
        
        key = data.CData.make_key(data.CData.s_territoryType, 0, 0)
        obj = dataInst.find_obj_by_key(key)
        if obj is None :
            print("not found territory")
            return
        polyData = obj.PolyData
        algVTK.CVTK.save_poly_data_stl(stlFullPath, polyData)
        print("Territory file saved successfully.")

    #sally
    # def _save_all_terri(self) :
    #     dataInst = self.get_data()
    #     if dataInst.Ready == False : 
    #         return 
    #     if self.m_organKey == "" :
    #         return

    #     clinfoinx = self.get_clinfo_index()
    #     skeleton = dataInst.get_skeleton(clinfoinx)
    #     if skeleton is None :
    #         return
        
    #     objlist = dataInst.find_obj_list_by_type(data.CData.s_territoryType)  ## key의 id에 TP_RA1 이런식으로 언더바들어있으면 에러....
        
    #     if objlist :
    #         for obj in objlist :
    #             polyData = obj.PolyData
    #             key = dataInst.find_key_by_obj(obj)
    #             saveFullPath = os.path.join(dataInst.get_terri_out_path(), f"{key}.stl")
    #             algVTK.CVTK.save_poly_data_stl(saveFullPath, polyData)
    #             print(f"Territory({saveFullPath}) file saved successfully.")
    
    def _import_territory(self) :
        ## 생성된 모든 territory들을 모아서 Territory.blend 생성.
        dataInst = self.get_data()
        if dataInst.Ready == False : 
            return 
        if self.m_organKey == "" :
            return

        currPatientID = self.m_userData.Data.DataInfo.PatientID
        if currPatientID == '' :
            print(f"_import_territory()-ERROR : CurrPatientID is empty.")
            return
        terriStlPath = dataInst.get_terri_out_path()
        # blender background 실행
        # saveAs = dataInst.OptionInfo.get_blender_name(dataInst.OptionInfo.s_processName, currPatientID)
        saveAs = f"{currPatientID}.blend"
        print(f"_import_territory() terriSavePath : {terriStlPath}")
        print(f"_import_territory() saveAs : {saveAs}")
        # option = "--new"  #기존 object 제거 옵션임
        # if passInst.TriOpt == 1 :
        #     option += " --triOpt"
        # projectUV 적용때문에 background로 실행하면 안됨.
        cmd = f"{dataInst.OptionInfo.BlenderExe} --python {os.path.join(self.fileAbsPath, 'blenderScriptLung.py')} -- --patientID {currPatientID} --path {terriStlPath} --saveAs {saveAs} --funcMode Territory"
        os.system(cmd)
    def _open_patientid_blender_with_terri(self) :
        #TODO : 사용자가 선택한 territory blender파일의 object들을 patientid.blend 파일을 열어서 import하고, arrange하기. sphere도 생성하기.
        terriBlendPath, _ = QFileDialog.getOpenFileName(self.get_main_widget(), "Select Terrtory.Blend File", "", "blender Files (*.blend)")
        if terriBlendPath == "" :
            return
        dataInst = self.get_data()
        if dataInst.Ready == False : 
            return 
        if self.m_organKey == "" :
            return
        currPatientID = self.m_userData.Data.DataInfo.PatientID
        if currPatientID == '' :
            print(f"_open_patientid_blender_with_terri()-ERROR : CurrPatientID is empty.")
            return
        terriStlPath = dataInst.get_terri_out_path()
        # blender background 실행
        # saveAs = dataInst.OptionInfo.get_blender_name(dataInst.OptionInfo.s_processName, currPatientID)
        saveAs = f"{currPatientID}.blend"
        cmd = f"{dataInst.OptionInfo.BlenderExe} -b --python {os.path.join(self.fileAbsPath, 'blenderScriptLung.py')} -- --patientID {currPatientID} --path {terriStlPath} --saveAs {saveAs} --terriBlendPath {terriBlendPath} --funcMode ViewAll"
        os.system(cmd)
        
    def _wrap_up(self) :
        patientBlendPath, _ = QFileDialog.getOpenFileName(self.get_main_widget(), "Select Terrtory.Blend File", "", "blender Files (*.blend)")
        if patientBlendPath == "" :
            return
        dataInst = self.get_data()
        if dataInst.Ready == False : 
            return 
        currPatientID = self.m_userData.Data.DataInfo.PatientID
        if currPatientID == '' :
            print(f"_wrap_up()-ERROR : CurrPatientID is empty.")
            return
        terriStlPath = dataInst.get_terri_out_path()
        # blender background 실행
        # saveAs = dataInst.OptionInfo.get_blender_name(dataInst.OptionInfo.s_processName, currPatientID)
        saveAs = f"{currPatientID}.blend"
        cmd = f"{dataInst.OptionInfo.BlenderExe} -b --python {os.path.join(self.fileAbsPath, 'blenderScriptLung.py')} -- --patientID {currPatientID} --path {terriStlPath} --saveAs {saveAs} --patientBlendPath {patientBlendPath} --funcMode WrapUp"
        os.system(cmd)
    def _wrap_up_second(self) :
        patientBlendPath, _ = QFileDialog.getOpenFileName(self.get_main_widget(), "Select Terrtory.Blend File", "", "blender Files (*.blend)")
        if patientBlendPath == "" :
            return
        dataInst = self.get_data()
        if dataInst.Ready == False : 
            return 
        currPatientID = self.m_userData.Data.DataInfo.PatientID
        if currPatientID == '' :
            print(f"_wrap_up_second()-ERROR : CurrPatientID is empty.")
            return
        terriStlPath = dataInst.get_terri_out_path()
        
        # saveAs = dataInst.OptionInfo.get_blender_name(dataInst.OptionInfo.s_processName, currPatientID)
        saveAs = f"{currPatientID}.blend"
        cmd = f"{dataInst.OptionInfo.BlenderExe} -b --python {os.path.join(self.fileAbsPath, 'blenderScriptLung.py')} -- --patientID {currPatientID} --path {terriStlPath} --saveAs {saveAs} --patientBlendPath {patientBlendPath}  --funcMode WrapUpSecond"
        os.system(cmd)  

    # ui event
    def _on_cb_terri_organ_name(self, index) :
        self._changed_terri_organ_index(index)
    def _on_btn_territory(self) :
        self._do_terri()
    def _on_btn_all_territory(self) : #sally    
        self._do_all_terri(True) #seg mode
    def _on_btn_all_territorySub(self) : #sally
        self._do_all_terri(False) #subseg mode
    def _on_btn_save_territory(self) :
        savePath, _ = QFileDialog.getSaveFileName(
            self.get_main_widget(),
            "Save Mesh File", 
            "", 
            "STL Files (*.stl)"
        )
        if savePath != "" : 
            self._save_terri(savePath)
    # def _on_btn_save_all_territory(self) :
    #     self._save_all_terri() 
    def _on_btn_import_territory(self) :
        self._import_territory()
    def _on_btn_open_patientid_blender_with_terri(self) :
        self._open_patientid_blender_with_terri()
    def _on_btn_wrap_up(self) :
        self._wrap_up()
    def _on_btn_wrap_up_second(self) :
        self._wrap_up_second()
    # private
    def _clear_terricb_organ_name(self) :
        self.m_cbTerriOrganName.clear()
    def _add_terricb_organ_name(self, organName : str) :
        self.m_cbTerriOrganName.addItem(organName)
    def _get_terricb_organ_name_count(self) -> int :
        return self.m_cbTerriOrganName.count()
    def _get_terricb_organ_index(self) -> int :
        return self.m_cbTerriOrganName.currentIndex()
    def _get_terricb_organ_name(self) -> str :
        return self.m_cbTerriOrganName.currentText()  



if __name__ == '__main__' :
    pass


# print ("ok ..")

