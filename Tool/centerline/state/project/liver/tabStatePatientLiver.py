import sys
import os
import csv
import vtk

from PySide6.QtCore import Qt, QItemSelectionModel
from PySide6.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QPushButton,
    QLineEdit,
    QLabel,
    QSizePolicy,
    QFileDialog,
    QFrame,
    QApplication,
    QStackedLayout,
    QTableView,
    QCheckBox,
    QHBoxLayout,
    QAbstractItemView,
    QRadioButton
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QPixmap
import command.commandExtractionCL as commandExtractionCL
from collections import Counter
import copy

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAppPath = os.path.dirname(fileAbsPath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import state.project.liver.userDataLiver as userDataLiver

import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath

import operationColored as operation

# import AlgUtil.algImage as algImage

# import Block.optionInfo as optionInfo
# import Block.niftiContainer as niftiContainer
# import Block.reconstruction as reconstruction

# import VtkObj.vtkObj as vtkObj

# import command.commandInterface as commandInterface
import command.commandLoadingPatient as commandLoadingPatient

# import command.commandExtractionCL as commandExtractionCL
# import command.commandRecon as commandRecon

import data as data

# import operation as op
import tabState as tabState

# sally
import liver.makeInputFolderLiver as makeInputFolder
import subUtils.predictNavel as predictNavel
import subUtils.generateSkinScreenshot as generateSkinScreenshot
import subRecon.subReconLiver as reconLiver
import liver.subDetectOverlap.subDetectOverlapLiver as detectOverlap
from PySide6.QtCore import QThread, Signal, Qt, QSize
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QDialog, QProgressBar, QMessageBox, QTableWidget, QTableWidgetItem
import Algorithm.scoUtil as scoUtil
from Algorithm.scoReg import CRegTransform
from PySide6.QtGui import QMovie
import Block.optionInfo as optionInfo
import Block.makeInputFolder as makeInputFolder
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import dlgCommon as dlgCommon
from pathlib import Path

class LoadingWorkerThread(QThread):
    result_ready = Signal(object)

    def __init__(self, target_object, parent=None):
        super().__init__(parent)
        self.target_object = target_object
        self.loadedFunction = lambda x: None

    def run(self):
        result = self.loadedFunction(self.target_object)
        self.result_ready.emit(result)


class LoadingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)

        self.spinner_label = QLabel(self)
        spinner_size = QSize(50, 50) 
        self.spinner_label.setFixedSize(spinner_size)
        self.spinner_label.setAlignment(Qt.AlignCenter)

        self.movie = QMovie("spinner.gif")
        self.movie.setScaledSize(spinner_size) 
        self.spinner_label.setMovie(self.movie)
        self.movie.start()

        self.resize(spinner_size)
class ValueBarWidget(QWidget):
    value_changed = Signal(int)

    def __init__(self, dimZ):
        super().__init__()
        self.setMinimumSize(40, 200)
        self.dimZ = dimZ
        self.margin = 5
        self.value = 0

    def set_value(self, v):
        # -margin ~ dimZ+margin 범위로 clamp
        v = max(0, min(self.dimZ , v))
        self.value = v
        self.update()

    def mousePressEvent(self, event):
        self._handle_mouse(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._handle_mouse(event)

    def _handle_mouse(self, event):
        rect = self.rect()
        y = event.position().y() if hasattr(event, "position") else event.y()

        # 전체 값 범위는 dimZ + 2*margin
        total_range = self.dimZ + 2 * self.margin

        # y좌표를 -margin ~ dimZ+margin 값으로 매핑
        ratio = y / rect.height()
        value = int(ratio * total_range - self.margin)

        self.set_value(value)
        self.value_changed.emit(self.value)

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()

        # 테두리
        painter.setPen(QPen(Qt.black, 2))
        painter.drawRect(rect.adjusted(5, 5, -5, -5))

        # dimZ + 2*margin 범위에 따라 선 위치 계산
        total_range = self.dimZ + 2 * self.margin
        ratio = (self.value + self.margin) / total_range
        line_y = int(ratio * rect.height())

        # 빨간 선
        painter.setPen(QPen(Qt.red, 2))
        painter.drawLine(5, line_y, rect.width() - 5, line_y)
        
class SliceIDInputDialog(QDialog):
    def __init__(self, parent, initialSliceID=453, dimZ=588):
        super().__init__(parent)
        self.setWindowTitle("Input slice ID")
        self.setFixedSize(400, 600)

        # ----- 배경 이미지 라벨 -----
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("QLabel { border: 1px solid #666; }")
        self.preview_label.setMinimumHeight(220)
        self.preview_label.setScaledContents(False)

        self._orig_pixmap = QPixmap("skin.png")
        self.img_w = self._orig_pixmap.width() or 1
        self.img_h = self._orig_pixmap.height() or 1
        self.img_aspect = self.img_w / self.img_h
        

        self.bar = ValueBarWidget(dimZ)
        self.bar.set_value(initialSliceID)

        self.bar.setAttribute(Qt.WA_TranslucentBackground, True)
        self.bar.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.bar.setStyleSheet("background: transparent;")
        self.bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.bar.setFocusPolicy(Qt.StrongFocus)  # 키/마우스 포커스 가능 (선택)

        self.overlay_container = QWidget()
        stacked = QStackedLayout(self.overlay_container)
        stacked.setStackingMode(QStackedLayout.StackAll)
        stacked.setContentsMargins(0, 0, 0, 0)
        stacked.addWidget(self.preview_label)   # 바닥
        stacked.addWidget(self.bar)             # 맨 위

        self.bar.raise_()

        self.input = QLineEdit()
        self.input.setPlaceholderText(f"0~{dimZ} slice ID 입력")
        self.input.setText(str(initialSliceID))

        self.ok_button = QPushButton("Start Recon")
        self.ok_button.clicked.connect(self.accept)

        self.bar.value_changed.connect(self.on_bar_changed)
        self.input.textChanged.connect(self.on_text_changed)

        layout = QVBoxLayout(self)
        layout.addWidget(self.overlay_container)
        layout.addWidget(self.input)
        layout.addWidget(self.ok_button)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        w = self.overlay_container.width()
        h = int(w / self.img_aspect)
        if h > 0:
            self.overlay_container.setFixedHeight(h)

        avail = self.overlay_container.size()
        if not self._orig_pixmap.isNull() and avail.width() > 0 and avail.height() > 0:
            scaled = self._orig_pixmap.scaled(
                avail,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled)

        self.bar.resize(avail)
        self.bar.raise_()
    def on_text_changed(self, text):
        try:
            self.bar.set_value(int(text))
        except ValueError:
            pass

    def on_bar_changed(self, value):
        self.input.setText(str(value))

    def get_value(self):
        try:
            return int(self.input.text())
        except:
            return 0

# class WorkerThread(QThread):
#     progress_changed = Signal(int, str)
#     finished = Signal()
#     canceled = Signal()

#     def __init__(self, inst):
#         super().__init__()
#         self._is_interrupted = False
#         self.inst = inst

#     def run(self):
#         try:
#             self.inst.progress_callback = self.progress_callback
#             self.inst.is_interrupted = lambda: self._is_interrupted
#             success = self.inst.process()
#             if not success:
#                 self.canceled.emit()
#             else:
#                 self.finished.emit()
#         except Exception as e:
#             print(f"[WorkerThread] 예외 발생: {e}")
#             self.canceled.emit()

#     def progress_callback(self, value, status=""):
#         self.progress_changed.emit(value, status)

#     def cancel(self):
#         self._is_interrupted = True


# class ProgressWindow(QDialog):
#     def __init__(self, parent, inst):
#         super().__init__(parent)
#         self.setWindowTitle("Processing...")
#         self.setFixedSize(300, 120)

#         layout = QVBoxLayout(self)

#         self.progress_bar = QProgressBar()
#         self.progress_bar.setMinimum(0)
#         self.progress_bar.setMaximum(100)
#         layout.addWidget(self.progress_bar)

#         self.status_label = QLabel("Loading ...")
#         layout.addWidget(self.status_label)

#         self.cancel_button = QPushButton("Cancel")
#         self.cancel_button.clicked.connect(self.cancel_task)
#         layout.addWidget(self.cancel_button)

#         self._was_canceled = False
#         self._done = False

#         self.worker = WorkerThread(inst)
#         self.worker.progress_changed.connect(self.update_progress, Qt.QueuedConnection)
#         self.worker.finished.connect(self.on_finished)
#         self.worker.canceled.connect(self.on_canceled)
#         self.worker.start()

#     def update_progress(self, value: int, status: str):
#         self.progress_bar.setValue(value)
#         self.status_label.setText(status)

#     def cancel_task(self):
#         self._was_canceled = True
#         self.worker.cancel()

#     def on_finished(self):
#         if self._done:
#             return
#         self._done = True
#         self.accept()

#     def on_canceled(self):
#         if self._done:
#             return
#         self._done = True
#         self.reject()


class CTabStatePatient(tabState.CTabState):
    """
    state
        - optionInfo, patientPath가 준비되지 않은 상태
        - optionInfo, patientPath가 준비된 상태
            - clInfo change 상태
    """

    s_listStepName = ["Recon", "Overlap", "MeshClean", "Centerline"]
    s_intermediatePathAlias = "OutTemp"
    
    @staticmethod
    def extract_cell_polydata(polydata : vtk.vtkPolyData, cellID : int) -> vtk.vtkPolyData :
        ids = vtk.vtkIdList()
        ids.InsertNextId(cellID)

        extractor = vtk.vtkExtractCells()
        extractor.SetInputData(polydata)
        extractor.SetCellList(ids)
        extractor.Update()

        geometry = vtk.vtkGeometryFilter()
        geometry.SetInputConnection(extractor.GetOutputPort())
        geometry.Update()

        return geometry.GetOutput()
    

    def __init__(self, mediator):
        self.m_bReady = False
        self.m_listStepBtnEvent = [
            #self._on_btn_integrity_mask,
            self._on_btn_recon,
            self._on_btn_overlap,
            self._on_btn_clean,
            self._on_btn_centerline
        ]

        super().__init__(mediator)
        # input your code
        self.m_bReady = True
        self.m_reconStomach = None  # sally
        self.m_reconReady = False  # sally

        # sally
        try:
            # PyInstaller로 패키징된 실행 파일의 경우
            self.fileAbsPath = sys._MEIPASS
            self.fileAbsPath = "."
        except AttributeError:
            # 개발 환경에서
            self.fileAbsPath = os.path.abspath(os.path.dirname(__file__))

        self.m_outputPath = ""
        self.m_zipPathPatientID = ""
        self.m_stateSelCell = 0
        self.m_bReady = False
        self.m_reconStomach = None  # sally
        self.m_reconReady = False  # sally

        self.m_dataRootPath = ""
        self.m_patientID = ""
        self.m_tumorPhase = ""
        
        self.m_advancementRatio = "1.001"
        
        self.m_opSelectionCL = operation.COperationSelectionCL(mediator)
        self.m_mapperHL = vtk.vtkPolyDataMapper()
        self.m_actorHL = vtk.vtkActor()
        self.m_actorHL.SetMapper(self.m_mapperHL)
        self.m_actorHL.GetProperty().SetColor(1, 0, 0) 
        self.m_actorHL.GetProperty().SetLineWidth(3.0)
        
        self.m_mapperClikedCell = vtk.vtkPolyDataMapper()
        self.m_actorClikedCell = vtk.vtkActor()
        self.m_actorClikedCell.SetMapper(self.m_mapperClikedCell)
        self.m_actorClikedCell.GetProperty().SetColor(0, 1, 0) 
        self.m_actorClikedCell.GetProperty().SetLineWidth(3.0)
    def clear(self):
        # input your code
        #self.m_btnCL = None
        self.m_outputPath = ""
        self.m_zipPathPatientID = ""
        self.m_stateSelCell = 0
        self.m_bReady = False
        self.m_reconStomach = None  # sally
        self.m_reconReady = False  # sally

        self.m_dataRootPath = ""
        self.m_patientID = ""
        self.m_tumorPhase = ""
        self.m_advancementRatio = ""
        
        self.m_actorHL = None
        self.m_opSelectionCL.clear()
        self.m_opSelectionCL = None
        super().clear()

    def process_init(self):
        dataInst = self.get_data()
        if dataInst.Ready == False :
            print("not setting patient path")
            return
        
        self.setui_clear_clinfo()
        iCnt = dataInst.get_skelinfo_count()
        for inx in range(0, iCnt) :
            skelinfo = dataInst.get_skelinfo(inx)
            self.setui_add_clinfo(inx, skelinfo)

        self.setui_clinfo_inx(dataInst.CLInfoIndex)
        self._command_clinfo_inxs()
        self.setui_check_sel_cell(True)

    def process(self):
        pass

    def process_end(self):
        self.setui_check_sel_cell(False)

    def changed_project_type(self):
        self.m_optionFullPath = os.path.join(self.m_mediator.FilePath, "option.json")
        if os.path.exists(self.m_optionFullPath) == False:
            self.m_optionFullPath = os.path.join(
                self.m_mediator.CommonPipelinePath, "option.json"
            )
            if os.path.exists(self.m_optionFullPath) == False:
                self.m_optionFullPath = ""
                
        self.command_option_path(self.m_optionFullPath)
        # sally : 아래 두 루틴은 _chaged_unzip_path() 안으로 옮김. 0526
        # self._command_option_path()
        # self._command_patientID()

    def init_ui(self):
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        # path ui
        label = QLabel("-- Path Info --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        layout, self.m_editOptionPath, btn = self.m_mediator.create_layout_label_dropeditbox_btn(
            "Option", False, "..",
            placeHolderText="Drag&Drop Option File", slotFunc=self.slot_drop_option_path
            )
        btn.clicked.connect(self._on_btn_option_path)
        tabLayout.addLayout(layout)
        # sally
        layout, self.m_editInputPath, btn = self.m_mediator.create_layout_label_dropeditbox_btn(
            "Input", False, "..",
            placeHolderText="Drag&Drop Patient Zip Folder", slotFunc=self.slot_drop_input_zip_path
            )
        btn.clicked.connect(self._on_btn_input_zip_path)
        tabLayout.addLayout(layout)

        # sally
        layout, self.m_editUnzipPath = self.m_mediator.create_layout_label_editbox("Output", False)
        tabLayout.addLayout(layout) 
        layout, self.m_editHuIDPath = self.m_mediator.create_layout_label_editbox("HuIDIn", False)
        tabLayout.addLayout(layout) 
        layout, self.m_editOutputPath = self.m_mediator.create_layout_label_editbox(f"{CTabStatePatient.s_intermediatePathAlias}", False)
        tabLayout.addLayout(layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        label = QLabel("-- Reconstruction STEP --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)
        
        label = QLabel("Registration Method :")
        self.m_rbNonrigid = QRadioButton("non-rigid")
        self.m_rbRigid = QRadioButton("rigid")
        self.m_rbNonrigid.toggled.connect(self._on_rb_nonrigid)
        self.m_rbRigid.toggled.connect(self._on_rb_rigid)
        self.m_rbNonrigid.setChecked(True)
        radio_layout = QHBoxLayout()
        radio_layout.addWidget(label)
        radio_layout.addWidget(self.m_rbNonrigid)
        radio_layout.addWidget(self.m_rbRigid)
        tabLayout.addLayout(radio_layout)

        layout, btnList = self.m_mediator.create_layout_btn_array(
            CTabStatePatient.s_listStepName
        )
        for inx, stepName in enumerate(CTabStatePatient.s_listStepName):
            btnList[inx].clicked.connect(self.m_listStepBtnEvent[inx])
        tabLayout.addLayout(layout)
        #self.m_btnCL = btnList[2]
        
        label = QLabel("-- Individual Reconstruction STEP --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        layout = QHBoxLayout()
        btn = QPushButton("Individual Recon")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_individual_recon)
        layout.addWidget(btn)
        tabLayout.addLayout(layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)
        
        label = QLabel("-- Centerline --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        self.m_modelCLInfo = QStandardItemModel()
        self.m_modelCLInfo.setHorizontalHeaderLabels(["Index", "BlenderName", "Output"])
        self.m_tvCLInfo = QTableView()
        self.m_tvCLInfo.setModel(self.m_modelCLInfo)
        self.m_tvCLInfo.setEditTriggers(QTableView.NoEditTriggers)
        self.m_tvCLInfo.horizontalHeader().setStretchLastSection(True)
        self.m_tvCLInfo.verticalHeader().setVisible(False)
        self.m_tvCLInfo.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.m_tvCLInfo.setSelectionMode(QAbstractItemView.ExtendedSelection)
        #self.m_tvCLInfo.clicked.connect(self._on_tv_clicked_clinfo)
        self.m_tvCLInfo.selectionModel().selectionChanged.connect(self._on_selection_changed)
        tabLayout.addWidget(self.m_tvCLInfo)
        
        self.m_checkSelectionStartCell = QCheckBox("Selection Start Cell ")
        self.m_checkSelectionStartCell.setChecked(False)
        self.m_checkSelectionStartCell.stateChanged.connect(self._on_check_sel_cell)
        tabLayout.addWidget(self.m_checkSelectionStartCell)

        layout = QHBoxLayout()
        label = QLabel("CellID ")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.m_editBoxCellID = QLineEdit()
        self.m_editBoxCellID.returnPressed.connect(self.on_cellID_changed)
        layout.addWidget(self.m_checkSelectionStartCell)
        layout.addWidget(label)
        layout.addWidget(self.m_editBoxCellID)
        tabLayout.addLayout(layout)


        # input_advancementRatio = QLineEdit()
        # input_advancementRatio.setPlaceholderText(f"advancement ratio 입력")
        # input_advancementRatio.setText(str(1.001))
        # input_advancementRatio.textChanged.connect(self.on_advancement_ratio_changed)
        # tabLayout.addWidget(input_advancementRatio)
        
        btn = QPushButton("Delete Centerline")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_delete_centerline)
        tabLayout.addWidget(btn)

        btn = QPushButton("Extraction Centerline")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_extraction_centerline)
        tabLayout.addWidget(btn)
        
        btn = QPushButton("Import Remodeled")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_import_remodeled)
        tabLayout.addWidget(btn)
        

        # sally
        # btn = QPushButton("Do Blender")
        # btn.setStyleSheet(self.get_btn_stylesheet())
        # btn.clicked.connect(self._on_btn_do_blender)
        # tabLayout.addWidget(btn)
        

        # btn = QPushButton("Extract Centerline")
        # btn.setStyleSheet(self.get_btn_stylesheet())
        # btn.clicked.connect(self._on_btn_extraction_centerline)
        # tabLayout.addWidget(btn)

        # line = QFrame()
        # line.setFrameShape(QFrame.Shape.HLine)
        # line.setFrameShadow(QFrame.Shadow.Sunken)
        # tabLayout.addWidget(line)

        lastUI = line
        tabLayout.setAlignment(lastUI, Qt.AlignmentFlag.AlignTop)
        
    def extract_cell_polydata_from_current_cellID(self):
        dataInst = self.get_data()
        clinfoInx = self.getui_clinfo_inx()

        vesselKey = data.CData.make_key(data.CData.s_vesselType, clinfoInx, 0)
        vesselObj = dataInst.find_obj_by_key(vesselKey)
        if vesselObj is None :
            return
        
        # vessel의 min-max 추출 및 정육면체 생성
        vesselPolyData = vesselObj.PolyData
        try:
            pickedPoly = CTabStatePatient.extract_cell_polydata(vesselPolyData, self.m_selCellID)
        except:
            pickedPoly = vtk.vtkPolyData()
        
        return pickedPoly
        
    def clicked_mouse_rb(self, clickX, clickY) :
        if self.m_stateSelCell == 0 : 
            return
        self.setui_cellID(self.m_selCellID)
        
        if self.m_selCellID == -1:
            self.m_mapperClikedCell.SetInputData(vtk.vtkPolyData())
            self.m_mapperClikedCell.Update()
        else:
            self.m_mapperClikedCell.SetInputData(self.extract_cell_polydata_from_current_cellID())
            self.m_mapperClikedCell.Update()
        self.m_mediator.update_viewer()
    def mouse_move(self, clickX, clickY) :
        # vessel과 마우스와의 picking 수행
        # 가장 가까운 cell을 찾음
        # cell의 중심 vertex를 guideEPKey에 세팅 
        listExceptKeyType = [
            data.CData.s_skelTypeCenterline,
        ]

        if self.m_stateSelCell == 0 : 
            return
        
        # self.m_picker.Pick(clickX, clickY, 0, self.m_mediator.get_viewercl_renderer())
        # selCellID = self.m_picker.GetCellId()
        # print(f"state : {self.m_stateSelCell} cellID : {selCellID}")
        # # 정확한 pick이 아니면 무시
        # if selCellID < 0 or not self.m_picker.GetActor() == self.m_actorHL :
        #     return
        selcellID = self.m_mediator.picking_cellid(clickX, clickY, listExceptKeyType)
        
        if selcellID < 0 :
            self.m_selCellID = selcellID
            return

        if selcellID > 0 :
            self.m_selCellID = selcellID
            dataInst = self.get_data()
            clinfoInx = self.getui_clinfo_inx()

            vesselKey = data.CData.make_key(data.CData.s_vesselType, clinfoInx, 0)
            vesselObj = dataInst.find_obj_by_key(vesselKey)
            if vesselObj is None :
                return
            
            # vessel의 min-max 추출 및 정육면체 생성
            vesselPolyData = vesselObj.PolyData

            pickedPoly = CTabStatePatient.extract_cell_polydata(vesselPolyData, self.m_selCellID)
            self.m_mapperHL.SetInputData(pickedPoly)
            self.m_mapperHL.Update()
        self.m_mediator.update_viewer()

        
    def _on_check_sel_cell(self, state) :
        '''
        state
            - 0 : unchecked
            - 1 : partially checked
            - 2 : checked
        '''
        if state == 2 :
            bCheck = True
            self.__set_selcellstate(1)
        else :
            bCheck = False
            self.__set_selcellstate(0)
            
    def __set_selcellstate(self, state : int) :
        # state exit
        if self.m_stateSelCell == 0 :
            pass
        else :
            self.m_mediator.get_viewercl_renderer().RemoveActor(self.m_actorHL)
            self.m_mediator.get_viewercl_renderer().RemoveActor(self.m_actorClikedCell)

        self.m_stateSelCell = state
        self.setui_cellID(-1)
        self.m_selCellID = -1

        # state start
        if state == 0 :
            pass
        else :
            self.m_picker = vtk.vtkCellPicker()
            self.m_picker.SetTolerance(0.0005)
            self.m_mediator.get_viewercl_renderer().AddActor(self.m_actorHL)
            self.m_mediator.get_viewercl_renderer().AddActor(self.m_actorClikedCell)
            self.m_mapperClikedCell.SetInputData(vtk.vtkPolyData())
            self.m_mapperClikedCell.Update()
        self.m_mediator.update_viewer()

        
    def on_advancement_ratio_changed(self, input_advancementRation):
        self.m_advancementRatio = input_advancementRation
        
    def on_cellID_changed(self):
        text = self.m_editBoxCellID.text().strip()
        try:
            self.m_selCellID = int(text)
        except ValueError:
            self.m_selCellID = -1 

        if self.m_selCellID == -1:
            self.m_mapperClikedCell.SetInputData(vtk.vtkPolyData())
            self.m_mapperClikedCell.Update()
        else:
            self.m_mapperClikedCell.SetInputData(self.extract_cell_polydata_from_current_cellID())
            self.m_mapperClikedCell.Update()

        self.m_mediator.update_viewer()
        
    def setui_check_sel_cell(self, bCheck : bool) -> bool :
        self.m_checkSelectionStartCell.setChecked(bCheck)
        
    def setui_cellID(self, cellID : int) :
        self.m_editBoxCellID.setText(str(cellID))
    # ui 
    def setui_edit_input_path(self, inputPath : str) :
        self.m_editInputPath.setText(inputPath)
    def setui_edit_unzip_path(self, unzipPath : str) :
        self.m_editUnzipPath.setText(unzipPath)
    def setui_edit_huid_path(self, huidPath : str) :
        self.m_editHuIDPath.setText(huidPath)
    def setui_edit_option_path(self, optionPath : str) :
        self.m_editOptionPath.setText(optionPath)
    def setui_edit_outtemp_path(self, outtempPath : str) :
        self.m_editOutputPath.setText(outtempPath)
        
    def setui_clinfo_inx(self, inx : int) :
        QIndex = self.m_modelCLInfo.index(inx, 0)
        if not QIndex.isValid() :
            return
        
        self.m_tvCLInfo.blockSignals(True)
        self.m_tvCLInfo.selectionModel().clearSelection()  # 기존 선택 지우기
        self.m_tvCLInfo.selectionModel().select(
            QIndex, 
            QItemSelectionModel.Select | QItemSelectionModel.Rows
        )
        self.m_tvCLInfo.setCurrentIndex(QIndex)
        self.m_tvCLInfo.blockSignals(False)
    def getui_clinfo_inx(self) -> int :
        '''
        ret : clinfoInx
                -1 : non-selection
        '''
        selectedIndex = self.m_tvCLInfo.selectionModel().selectedIndexes()
        if selectedIndex :
            row = selectedIndex[0].row()
            index = int(self.m_modelCLInfo.item(row, 0).text())
            return index
        return -1

    def getui_clinfo_inxs(self) -> list[int]:
        """
        returns: 선택된 행들의 clinfo index 목록 (0번 컬럼의 값이 정수라고 가정)
                아무 것도 없으면 [] 반환
        """
        sel_rows = self.m_tvCLInfo.selectionModel().selectedRows()  # 각 요소는 QModelIndex(컬럼=0)
        result = []
        for mi in sel_rows:
            row = mi.row()
            # QStandardItemModel이라면:
            idx_text = self.m_modelCLInfo.item(row, 0).text()
            try:
                result.append(int(idx_text))
            except ValueError:
                pass
        # 선택 순서가 섞일 수 있으니 정렬이 필요하면:
        result.sort()
        return result
    
    def getui_edit_input_path(self) -> str :
        return self.m_editInputPath.text()
    def getui_edit_unzip_path(self) -> str :
        return self.m_editUnzipPath.text()
    def getui_edit_huid_path(self) -> str :
        return self.m_editHuIDPath.text()
    def getui_edit_option_path(self) -> str :
        return self.m_editOptionPath.text()
    def getui_edit_outtemp_path(self) -> str :
        return self.m_editOutputPath.text()
    
    def getui_cellID(self) -> int :
        cellID = -1
        try :
            cellID = int(self.m_editBoxCellID.text())
        except ValueError:
            cellID = -1
        return cellID

    # command
    def command_option_path(self, optionFullPath : str) :
        self._clear_optioninfo()
        dataInst = self.get_data()

        self.setui_edit_input_path("")
        self.setui_edit_unzip_path("")
        self.setui_edit_huid_path("")
        self.setui_edit_outtemp_path("")

        if os.path.exists(optionFullPath) == False :
            QMessageBox.information(self.m_mediator, "Alarm", "not found option file")
            optionFullPath = ""
            dataInst.OptionInfo = None
        else :
            optionInfoInst = optionInfo.COptionInfo(optionFullPath)
            dataInst.OptionInfo = optionInfoInst
        self.setui_edit_option_path(optionFullPath)
        self.m_mediator.update_viewer()
        
    def command_input_zip_path(self, inputZipPath : str) :
        '''
        - 이 부분에서 반드시 data clear가 일어나야 되며, patientID와 outputTempPath가 세팅이 된 상태여야만 한다. 
        '''
        self._clear_patient()

        self.setui_edit_input_path(inputZipPath)
        self.setui_edit_unzip_path("")
        self.setui_edit_huid_path("")
        self.setui_edit_outtemp_path("")
        if inputZipPath == "" :
            return
        
        dataInst = self.get_data()
        userdata = dataInst.UserData
        userdata.set_patient_zippath(inputZipPath)
        folderInfo = userdata.MakeInputFolder
        if folderInfo.Ready == False :
            return
        rootPath = folderInfo.DataRootPath
        huid = folderInfo.PatientID
        self.m_dataRootPath = rootPath

        self.setui_edit_unzip_path(rootPath)
        self.setui_edit_huid_path(huid)

        self.command_outtemp_path(rootPath)
        #self.command_refresh_optioninfo()

        self.m_mediator.update_viewer()
    def _command_option_path(self) -> bool:
        dataInst = self.get_data()
        self.m_mediator.remove_all_key()
        dataInst.clear_patient()
        


        self.m_editOptionPath.setText(self.m_optionFullPath)
        if self.m_optionFullPath == "":
            return False
        # unzipPath = self.m_editUnzipPath.text() #sally

        optionFullPath = self.m_optionFullPath
        if os.path.exists(optionFullPath) == False :
            QMessageBox.information(self.m_mediator, "Alarm", "not found option file")
            self.m_editOptionPath.setText("")
            dataInst.OptionInfo = None
            return
        
        optionInfoInst = optionInfo.COptionInfo(optionFullPath)
        dataInst.OptionInfo = optionInfoInst
        
        dataInst.s_clColor = algLinearMath.CScoMath.to_vec3([0.3, 0.3, 0.0])
        dataInst.RootCLColor = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 0.0])
        dataInst.SelectionCLColor = algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0])
        dataInst.CLSize = 0.4
        dataInst.BrColor = algLinearMath.CScoMath.to_vec3([1.0, 0.647, 0.0])
        dataInst.SelectionBrColor = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        dataInst.BrSize = 0.5
        dataInst.EPColor = algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0])
        dataInst.SelectionEPColor = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        dataInst.EPSize = 0.5

        self._command_reset_clinfo_inx()
        self.setui_output_path("")
        self.m_mediator.update_viewer()
        
        # if self.m_dataRootPath != "" and self.m_patientID != "" :
        #     realPhaseMaskList = self._get_real_phase_name(self.m_dataRootPath, self.m_patientID)
        #     # 마스크들의 실제 Phase 폴더에 맞춰 maskInfo를 갱신함.
        #     for phaseMask in realPhaseMaskList :
        #         for maskfile in phaseMask['files'] :
        #             maskname = maskfile.split('.')[0]
        #             maskInfo = dataInst.m_optionInfo.find_maskinfo_by_blender_name(maskname)
        #             if maskInfo != None :
        #                 maskInfo.Phase = phaseMask['phase']
        # else:
        #     return False
        
        return True
    
    def _get_real_phase_name(self, dataRootPath, patientID) :
        phaseMaskList = []

        unzipPath = dataRootPath
        maskRoot = os.path.join(unzipPath, patientID, "02_SAVE", "01_MASK")
        apPath = os.path.join(maskRoot, "Mask_AP")
        ppPath = os.path.join(maskRoot, "Mask_PP")
        hvpPath = os.path.join(maskRoot, "Mask_HVP")
        mrPath = os.path.join(maskRoot, "Mask_MR")
        list_ap = os.listdir(apPath)
        list_pp = os.listdir(ppPath)
        list_hvp = os.listdir(hvpPath)
        list_mr = os.listdir(mrPath)
        phaseMaskList.append({'phase':'AP', 'files': list_ap})
        phaseMaskList.append({'phase':'PP', 'files': list_pp})
        phaseMaskList.append({'phase':'DP', 'files': list_hvp})
        phaseMaskList.append({'phase':'MR', 'files': list_mr})
        print(f"PhaseMaskList : {phaseMaskList}", file=sys.__stdout__, flush=True)
        
        return phaseMaskList
        

    def command_outtemp_path(self, dataRootPath) :
        outputTempPath = os.path.join(os.path.dirname(dataRootPath), CTabStatePatient.s_intermediatePathAlias)
        if os.path.exists(outputTempPath) == False :
            os.makedirs(outputTempPath, exist_ok=True)
        self.setui_edit_outtemp_path(outputTempPath)

        huid = self.getui_edit_huid_path()

        dataInst = self.get_data()
        dataInst.PatientID = huid
        dataInst.OutputPath = outputTempPath
        self.OutputPath = outputTempPath

        self.m_mediator.set_title(huid)
        self.m_mediator.update_viewer()
    # protected
    def _get_userdata(self) -> userDataLiver.CUserDataLiver:
        return self.get_data().find_userdata(
            userDataLiver.CUserDataLiver.s_userDataKey
        )
    def setui_clear_clinfo(self) :
        self.m_tvCLInfo.blockSignals(True)
        self.m_modelCLInfo.removeRows(0, self.m_modelCLInfo.rowCount())
        self.m_tvCLInfo.blockSignals(False)
        
    def setui_add_clinfo(self, inx : int, skelinfo : data.CSkelInfo) :
        blenderName = skelinfo.BlenderName
        jsonName = skelinfo.JsonName
        self.m_tvCLInfo.blockSignals(True)
        self.m_modelCLInfo.appendRow([QStandardItem(f"{inx}"), QStandardItem(blenderName), QStandardItem(jsonName)])
        self.m_tvCLInfo.blockSignals(False)
    
    # def getui_lv_cuttednode_selected_node(self) -> remodelingNode.CRemodelingNode :
    #     selectedItems = self.m_lvCuttedNode.selectedItems()
    #     if not selectedItems :
    #         return None
        
    #     item = selectedItems[0]
    #     text = item.text()
    #     node = item.data(Qt.UserRole) 
    #     return node
    
    def _remove_file(self, path):
        if os.path.exists(path):
            os.remove(path)
            print(f"deletion completed: {path}")
        else:
            pass
            #print(f"cannot found: {path}")
            
    def _re_align_ref_key(self, inx):
        dataInst = self.get_data()
        objKeys = [k for k in dataInst.m_dicObj.keys()]
        for k in objKeys:
            if data.CData.get_groupID_from_key(k) > inx:
                kSplit = k.split("_")
                kSplit[1] = str(data.CData.get_groupID_from_key(k)-1)
                newKey = "_".join(kSplit)
                dataInst.m_dicObj[newKey] = dataInst.m_dicObj.pop(k)
    
    def _command_delete_cl(self) :
        dataInst = self.get_data()
        clinfoIndices = self.get_clinfo_indices()
        clInPath = dataInst.get_cl_in_path()
        terriOutPath = dataInst.get_terri_out_path()
        clOutPath = dataInst.get_cl_out_path()
        
        for clinfoinx in sorted(clinfoIndices, reverse=True):
            skelinfo = dataInst.get_skelinfo(clinfoinx)
            if dataInst.OptionInfo.is_recon_blender_name(skelinfo.BlenderName):
                QMessageBox.information(self.m_mediator, "Alarm", f"cannot remove centerline")
                return
            if clinfoinx == dataInst.OptionInfo.find_centerline_index_of_blendername(skelinfo.BlenderName):
                print(f"cannot remove {skelinfo.BlenderName}", file=sys.__stdout__, flush=True)
                continue
            
            clInStlPath = os.path.join(clInPath, f"{skelinfo.JsonName}.stl")
            terriOutStlPath = os.path.join(terriOutPath, f"{skelinfo.JsonName}.stl")
            clOutJsonPath = os.path.join(clOutPath, f"{skelinfo.JsonName}.json")
    
            self._remove_file(clInStlPath)
            self._remove_file(terriOutStlPath)
            self._remove_file(clOutJsonPath)
            
            dataInst.remove_skelinfo(clinfoinx)
            
            self.m_mediator.remove_vessel_obj(clinfoinx)
            self.m_mediator.remove_skeleton_obj(clinfoinx)
            
            self.m_mediator.unref_key_type_groupID(data.CData.s_vesselType, clinfoinx)
            self.m_mediator.unref_key_type_groupID(data.CData.s_skelTypeCenterline, clinfoinx)
            
            self._re_align_ref_key(clinfoinx)
            
        self.setui_clear_clinfo()
        iCnt = dataInst.get_skelinfo_count()
        for inx in range(0, iCnt) :
            skelinfo = dataInst.get_skelinfo(inx)
            self.setui_add_clinfo(inx, skelinfo)

        self.setui_clinfo_inx(dataInst.CLInfoIndex)
        self._command_clinfo_inxs()
        self.setui_check_sel_cell(False)
        
        fullPath = os.path.join(dataInst.OutputPatientPath, f"{data.CData.s_fileName}.json")
        dataInst.save(fullPath)
        
        self.m_mediator.update_viewer()
        
    def _command_extraction_cl(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            print("not setting patient path")
            return
        clOutPath = dataInst.get_cl_out_path()
        if os.path.exists(clOutPath) == False :
            print("not found clOutPath")
            return 
        clInPath = dataInst.get_cl_in_path()
        if os.path.exists(clInPath) == False :
            print("not found clInPath")
            return 
        
        clinfoinx = dataInst.CLInfoIndex
        self.m_mediator.remove_skeleton_obj(clinfoinx)

        skelinfo = dataInst.get_skelinfo(clinfoinx)
        vtpName = skelinfo.BlenderName

        # centerline 시작 cell이 있으므로 현재 vessel polydata를 vtp로 저장. 
        startCellID = self.getui_cellID()
        if startCellID < 0 :
            QMessageBox.warning(self.m_mediator, "Error", "Please select start cell.")
            return
            #startCellID = 0

        vesselKey = data.CData.make_key(data.CData.s_vesselType, clinfoinx, 0)
        vesselObj = dataInst.find_obj_by_key(vesselKey)
        if vesselObj is None :
            print("not found vessel polydata")
            return

        vesselPolyData = vesselObj.PolyData
        vtpFullPath = os.path.join(clInPath, f"{vtpName}.vtp")
        algVTK.CVTK.save_poly_data_vtp(vtpFullPath, vesselPolyData)

        cmd = commandExtractionCL.CCommandExtractionCL(self.m_mediator)
        cmd.InputData = dataInst
        cmd.InputIndex = clinfoinx
        cmd.InputVTPName = vtpName
        cmd.InputCellID = startCellID
        cmd.InputEn = 0
        cmd.process()

        clOutputFullPath = os.path.join(clOutPath, f"{vtpName}.json")
        if os.path.exists(clOutputFullPath) == False :
            print(f"not found skelinfo : {clOutputFullPath}")
            return 
        
        preSkeleton = dataInst.get_skeleton(clinfoinx)
        
        skeleton = algSkeletonGraph.CSkeleton()
        skeleton.load(clOutputFullPath)
        skelinfo.Skeleton = skeleton
        self.m_mediator.add_skeleton_obj(clinfoinx)

        self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeCenterline, clinfoinx)
        
        if preSkeleton != None:
            self.copy_skeleton_cl_label(skeleton, preSkeleton)
            
        ketList = dataInst.find_key_list_by_type_groupID(dataInst.s_skelTypeCenterline, clinfoinx)
        self.m_opSelectionCL._color_setting(ketList, dataInst.s_rootCLColor, dataInst.s_clColor)
        
        self.save_skeleton(preSkeleton) ## 작업중 꺼질 때 방지
        self.m_mediator.update_viewer()
        
    def save_skeleton(self, skeleton) :
        dataInst = self.get_data()
        if dataInst.Ready == False : 
            return
        
        clinfoInx = self.getui_clinfo_inx()
        if skeleton is None :
            return

        clOutPath = dataInst.get_cl_out_path()

        skelinfo = dataInst.get_skelinfo(clinfoInx)
        blenderName = skelinfo.BlenderName
        jsonName = skelinfo.JsonName
        outputFullPath = os.path.join(clOutPath, f"{jsonName}.json")
        skeleton.save(outputFullPath, blenderName)
        
    def copy_skeleton_cl_label(self, skeleton, preSkeleton):
        clNearestCount = {i:[] for i in range(skeleton.get_centerline_count())}
        
        for i, v in enumerate(skeleton.m_listKDTreeAnchor):
            mainCL = preSkeleton.find_nearest_centerline(v.reshape(1, 3))
            clNearestCount[skeleton.m_listKDTreeAnchorID[i]].append(mainCL.Name)
        
        for ci in range(skeleton.get_centerline_count()):
            enCL = skeleton.get_centerline(ci)
            enCL.Name = Counter(clNearestCount[enCL.ID]).most_common(1)[0][0]
        
        
    def _command_import_remodeling(self):
        dataInst = self.get_data()
        userdata = dataInst.UserData
        userdata.clean_remodel_blender()
        
        self._clear_centerline()
        dataInst = self.get_data()
        if dataInst.Ready == False :
            QMessageBox.information(self.m_mediator, "Alarm", "please setting option, outputPath, patientID")
            return

        blenderFullPath = os.path.join(os.path.dirname(userData.OutputReconBlenderFullPath), f"{dataInst.PatientID}_remodel.blend")

        if os.path.exists(blenderFullPath) == False :
            QMessageBox.information(self.m_mediator, "Alarm", f"not found {os.path.basename(blenderFullPath)}")
            return

        cmd = commandLoadingPatient.CCommandLoadingPatient(self.m_mediator)
        cmd.InputData = dataInst
        cmd.PatientBlenderFullPath = blenderFullPath
        cmd.process()

        self.setui_clear_clinfo()
        iCnt = dataInst.get_skelinfo_count()
        clInPath = dataInst.get_cl_in_path()
        for inx in range(0, iCnt) :
            skelinfo = dataInst.get_skelinfo(inx)
            blenderName = skelinfo.BlenderName
            vesselFullPath = os.path.join(f"{clInPath}", f"{blenderName}.stl")
            if os.path.exists(vesselFullPath) == False :
                continue
            self.setui_add_clinfo(inx, skelinfo)

        dataInst.CLInfoIndex = 0
        self.setui_clinfo_inx(dataInst.CLInfoIndex)
        self._command_clinfo_inx()

        fullPath = os.path.join(dataInst.OutputPatientPath, f"{data.CData.s_fileName}.json")
        dataInst.save(fullPath)
        self.m_mediator.remove_key_type(dataInst.s_skelTypeCenterline)
        self.m_mediator.update_viewer()


    def _changed_unzip_path(self, option_path, data_root_path) -> str:
        # 현재 option 파일의 dataRootPath를 변경해줘야 함.
        new_data_root_path = data_root_path.replace("\\", "\\\\").replace("/", "\\\\")
        jsonpath = option_path
        
        if os.path.exists(jsonpath):
            # 임시 파일에 업데이트된 DataRootPath 포함해서 json내용 복사
            temp_path = os.path.join(os.path.dirname(jsonpath), "tmp.json")
            target_str = '"DataRootPath"'

            with open(jsonpath, "r", encoding="utf-8") as org_file, open(
                temp_path, "w", encoding="utf-8"
            ) as temp_file:
                for line in org_file:
                    # DataRootPath 부분 찾아서 새로운 패스로 바꿈
                    if target_str in line:
                        # line = line.replace(target_str, replacement_string)
                        line = f'\t"DataRootPath" : "{new_data_root_path}",\n'
                    temp_file.write(line)

            os.replace(temp_path, jsonpath)

        # get patientID
        patientID = "--"
        for dirfile in os.listdir(new_data_root_path):
            if os.path.isdir(os.path.join(new_data_root_path, dirfile)):
                patientID = dirfile

        self.m_dataRootPath = new_data_root_path
        self.m_patientID = patientID
        self._command_option_path()  # sally 0526
        self._command_patientID()  # sally 0526


        return patientID
        
    def _out_temp_auto_setting(self, new_data_root_path):
        # OutTemp auto setting
        outputTempPath = os.path.join(os.path.dirname(new_data_root_path), "OutTemp")
        if os.path.exists(outputTempPath) == False:
            os.makedirs(outputTempPath, exist_ok=True)
        self._changed_output_temp_path(outputTempPath)
        
        

    def do_blender(self):
        dataInst = self.get_data()

        currPatientID = self.getui_edit_huid_path()
        if currPatientID == "":
            print(f"ERROR : CurrPatientID is empty.")
            return
        stlPath = os.path.join(dataInst.OutputPath, currPatientID, "Result")
        savePath = os.path.join(
            self.m_dataRootPath, currPatientID, "02_SAVE", "02_BLENDER_SAVE"
        )
        cmd = f"{dataInst.OptionInfo.BlenderExe} --python {os.path.join(self.fileAbsPath, 'blenderScriptLiver.py')} -- --patient_id {currPatientID} --stl_path {stlPath} --out_path {savePath} --func_mode Basic --option_path {self.m_optionFullPath}"
        os.system(cmd)
        
    def execute_blender_save(self):
        dataInst = self.get_data()
        unzipPath = self.m_editUnzipPath.text()
        
        BlenderPath = os.path.join(
            unzipPath, self.getui_edit_huid_path(), "02_SAVE", "02_BLENDER_SAVE", f"{self.getui_edit_huid_path()}_recon.blend"
        )
        cmd = f'{dataInst.OptionInfo.BlenderExe} "{BlenderPath}"'
        os.system(cmd)
            

    def _clicked_do_blender(self):
        if self.m_reconStomach != None and self.m_reconReady == True:
            self.do_blender()
            self.m_mediator.show_dialog("Do Blender Done!")
        else:
            print(
                f"tabStatereconKidney - Error : m_reconStomach None or m_reconReady False!"
            )
            self.m_mediator.show_dialog(
                f"Do Blender FAIL! \nOption 또는 {CTabStatePatient.s_intermediatePathAlias} 경로를 확인해주세요."
            )

    def _clicked_recon_mask(self, inputSliceID: int):
        # dataInst = self.get_data()
        # userdata = dataInst.UserData
        # if userdata is not None :
        #     userdata.override_recon()
            
        
        
        # if dataInst.OptionInfo.m_registrationInfo == None:
        #     self.m_mediator.show_dialog("ERROR !!!! : m_registrationInfo is None .")
        #     return

        if self.m_reconReady == True:
            dataInst = self.get_data()
            userdata = dataInst.UserData
            if self.m_rbNonrigid.isChecked():
                userdata.m_registrationMethod = "non-rigid"
            else:
                userdata.m_registrationMethod = "rigid"
            if userdata is not None :
                userdata.override_recon(inputSliceID)
            else :
                QMessageBox.information(self.m_mediator, "Alarm", f"failed reconstruction : not setting userdata")
            
            return
            optioninfo = dataInst.OptionInfo
            folderInfo = userdata.MakeInputFolder
            if folderInfo.Ready == False :
                return
            
            # dataRoot의 Mask를 OutTemp로 복사
            copiedMaskPath = os.path.join(dataInst.OutputPatientPath, "Mask")
            if os.path.exists(self.OutputReconBlenderFullPath) == False :
                folderInfo.copy_mask(copiedMaskPath)
            reconStlPath = os.path.join(dataInst.OutputPatientPath, "Result")
            blendSavePath = dataInst.OutputPatientPath
            
            reconInst = reconLiver.CSubReconLiver()
            reconInst.InputSliceID = inputSliceID
            reconInst.OptionPath = self.m_optionFullPath
            reconInst.PatientID = self.getui_edit_huid_path()
            unzipPath = self.m_editUnzipPath.text()
            # maskRoot = os.path.join(
            #     unzipPath, self.getui_edit_huid_path(), "02_SAVE", "01_MASK"
            # )
            # reconInst.APPath = os.path.join(maskRoot, "Mask_AP")
            # reconInst.PPPath = os.path.join(maskRoot, "Mask_PP")
            # reconInst.HVPPath = os.path.join(maskRoot, "Mask_HVP")
            # reconInst.MRPath = os.path.join(maskRoot, "Mask_MR")
            reconInst.m_optionInfo = self.get_optioninfo()
            reconInst.PatientBlenderFullPath = os.path.join(
                unzipPath, self.getui_edit_huid_path(), "02_SAVE", "02_BLENDER_SAVE", "Auto01_Recon" , str(self.getui_edit_huid_path())+".blender"
            )
            reconInst.IntermediateDataPath = self.m_outputPath
            reconInst.InputData = self.get_data()
            #dataInst = self.get_data()
            #result = reconInst.init(dataInst.OptionInfo, userData)
            success = self._generate_progress_window(reconInst)
            # self.m_reconStomach.process()
            reconInst.clear()
            if not success:
                return
            self.do_blender()
            # self.m_mediator.show_dialog("Reconstruction(.blend) Done.")
        else:
            # self.m_mediator.show_dialog(f"Reconstruction FAIL! \nOption 또는 {CTabStatePatient.s_intermediatePathAlias} 경로를 확인해주세요.")
            return

        # self._clicked_do_blender()
        
    def _clicked_overlap_loading(self):
        self.loading_dialog = LoadingDialog(self.m_mediator)
        self.loading_dialog.show()
        
        def _clicked_overlap(self):
            dataInst = self.get_data()
            userdata = dataInst.UserData
            if userdata is not None :
                userdata.override_overlap()
            else :
                QMessageBox.information(self.m_mediator, "Alarm", f"failed reconstruction : not setting userdata")
            return
            
        def end_overlap(result):
            self.loading_dialog.close()
            self.m_mediator.show_dialog(f"OverlapDetection(.blend) Done.")
        
        self.worker = LoadingWorkerThread(self)
        self.worker.loadedFunction = _clicked_overlap
        self.worker.result_ready.connect(end_overlap)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def _cliked_clean_loading(self):
        self.loading_dialog = LoadingDialog(self.m_mediator)
        self.loading_dialog.show()
        currPatientID = self.getui_edit_huid_path()

        if currPatientID == "":
            print(f"ERROR : CurrPatientID is empty.")
            return

        def _clicked_clean(self):
            dataInst = self.get_data()
            userdata = dataInst.UserData
            if userdata is not None :
                userdata.override_clean()
            else :
                QMessageBox.information(self.m_mediator, "Alarm", f"failed reconstruction : not setting userdata")
            return
            
        def end_clean(result):
            self.loading_dialog.close()
            self.m_mediator.show_dialog(f"Mesh-Clean Done")
            
            # openPath = os.path.join(
            #     unzipPath, self.getui_edit_huid_path(), "02_SAVE", "02_BLENDER_SAVE", f"{self.getui_edit_huid_path()}_clean.blend"
            # )
            
            # cmd = f'{dataInst.OptionInfo.BlenderExe} "{cleanupBlenderPath}"'
            # os.system(cmd)
            
            # cmd = f"{dataInst.OptionInfo.BlenderExe} --python {os.path.join(self.fileAbsPath, 'blenderScriptLiver.py')} -- --patientID {currPatientID} --stlPath {stlPath} --optionFullPath {self.m_optionFullPath} --openPath {openPath} --outputPath {openPath} --funcMode OpenBlend"
            # os.system(cmd)
            
        self.worker = LoadingWorkerThread(self)
        self.worker.loadedFunction = _clicked_clean
        self.worker.result_ready.connect(end_clean)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()
        

    # ui event
    def _on_btn_delete_centerline(self):
        self._command_delete_cl()
        
    def _on_btn_extraction_centerline(self) :
        self._command_extraction_cl()
    
    def _on_btn_option_path(self):
        #self.m_btnCL.setEnabled(True)
        optionPath, _ = QFileDialog.getOpenFileName(
            self.get_main_widget(), "Select Option File", "", "JSON Files (*.json)"
        )
        if optionPath == "":
            return
        self.m_optionFullPath = optionPath
        self._command_option_path()
        
    def _on_btn_input_zip_path(self) :
        #self.m_btnCL.setEnabled(True)
        self.m_reconReady = True
        dataInst = self.get_data()
        if dataInst.OptionInfo is None :
            QMessageBox.information(self.m_mediator, "Alarm", "please setting option file")
            return 

        inputPath = QFileDialog.getExistingDirectory(self.get_main_widget(), "Select Zip Folder")
        self.command_input_zip_path(inputPath)

    def _on_btn_unzip_path(self):  # sally
        unzipPath = QFileDialog.getExistingDirectory(
            self.get_main_widget(), "Select Output Path"
        )
        self.m_editUnzipPath.setText(unzipPath)  # Output 폴더구조 path
        if unzipPath != "":
            option_path = self.m_optionFullPath
            huid = self._changed_unzip_path(option_path, unzipPath)
            self.setui_reset_patientID([huid])

            ## _on_btn_input_zip_path() 수행시 감지된 huid와 현재 huid가 서로 다르면 다른 환자의 데이터를 가져오는 것이므로 input path 칸은 혼통 방지를 위해 클리어한다.
            if huid != self.m_zipPathPatientID:
                self.m_editInputPath.setText("")
            self._out_temp_auto_setting(unzipPath)

    def _changed_output_temp_path(self, outputPath):
        self.setui_output_path(outputPath)
        self.m_outputPath = outputPath

        self.m_reconReady = True
        dataInst = self.get_data()
        dataInst.PatientID = self.getui_edit_huid_path()
        dataInst.OutputPath = self.m_outputPath
        
        self.m_mediator.show_dialog("입력데이터 로딩 완료. Recon 버튼을 클릭하세요!")

    def _on_btn_output_temp_path(self):
        #self.m_btnCL.setEnabled(True)
        outputPath = QFileDialog.getExistingDirectory(
            self.get_main_widget(),
            f"Select {CTabStatePatient.s_intermediatePathAlias} Path",
        )
        self._changed_output_temp_path(outputPath)

    def _cliked_recon_get_sliceID(self):

        def _predict_navel_position(self) -> int:
            unzipPath = self.m_editUnzipPath.text()
            DicomPPPath = os.path.join(
                unzipPath, self.getui_edit_huid_path(), "01_DICOM", "PP"
            )
            try:
                shape, spacing, origin, ct = predictNavel.ctLoader(DicomPPPath,returnImage=True)
                predicted, method, score, ct = predictNavel.predictNavel(ct, spacing, "both")
                navelZID = predicted[2]
            except:
                navelZID = -1
            return navelZID
        
        def _manually_detect_navel():
            self.m_mediator.show_dialog("배꼽을 찾을 수 없습니다. 직접 입력하세요.")

            unzipPath = self.m_editUnzipPath.text()
            maskRoot = os.path.join(
                unzipPath, self.getui_edit_huid_path(), "02_SAVE", "01_MASK"
            )
            HVPPath = os.path.join(maskRoot, "DP")
            PPPath = os.path.join(maskRoot, "PP")
            APPath = os.path.join(maskRoot, "AP")
            
            def _generate_skin_png(self):
                generateSkinScreenshot.generateSkinPng(os.path.join(HVPPath, "Skin.nii.gz"))
            def _end_generate_skin_png(result):
                self.loading_dialog2.close()
                if os.path.exists(os.path.join(HVPPath, "Skin.nii.gz")) == True:
                    skinImgPath = os.path.join(HVPPath, "Skin.nii.gz")
                    sitkImg = scoUtil.CScoUtilSimpleITK.load_image(skinImgPath, None)
                    skinMask = CRegTransform.create_buffer3d(sitkImg)
                    dimZ = skinMask.Shape[2]
                elif os.path.exists(os.path.join(APPath, "Skin.nii.gz")) == True:
                    skinImgPath = os.path.join(APPath, "Skin.nii.gz")
                    sitkImg = scoUtil.CScoUtilSimpleITK.load_image(skinImgPath, None)
                    skinMask = CRegTransform.create_buffer3d(sitkImg)
                    dimZ = skinMask.Shape[2]
                elif os.path.exists(os.path.join(PPPath, "Skin.nii.gz")) == True:
                    skinImgPath = os.path.join(PPPath, "Skin.nii.gz")
                    sitkImg = scoUtil.CScoUtilSimpleITK.load_image(skinImgPath, None)
                    skinMask = CRegTransform.create_buffer3d(sitkImg)
                    dimZ = skinMask.Shape[2] 
                else:
                    print("not found skin nifti")
                    dimZ = 588
                
                initialSliceID = int(dimZ//2) + 125
                input_dialog = SliceIDInputDialog(self.m_mediator, initialSliceID=initialSliceID, dimZ=dimZ)
                if input_dialog.exec() == QDialog.Accepted:
                    os.remove("skin.png")
                    inputSliceID = input_dialog.get_value()
                    inputSliceID = dimZ - inputSliceID
                    self._clicked_recon_mask(inputSliceID)
                
            self.loading_dialog2 = LoadingDialog(self.m_mediator)
            self.loading_dialog2.show()
            self.worker2 = LoadingWorkerThread(self)
            self.worker2.loadedFunction = _generate_skin_png
            self.worker2.result_ready.connect(_end_generate_skin_png)
            self.worker2.finished.connect(self.worker.deleteLater)
            self.worker2.start()

        
        def _calculate_input_slice(navelZID):
            if navelZID != -1:
                unzipPath = self.m_editUnzipPath.text()
                maskRoot = os.path.join(
                    unzipPath, self.getui_edit_huid_path(), "02_SAVE", "01_MASK"
                )
                PPPath = os.path.join(maskRoot, "PP")
                APPath = os.path.join(maskRoot, "AP")
                HVPPath = os.path.join(maskRoot, "DP")
                _manually_detect_navel()

                # if os.path.exists(os.path.join(PPPath, "Skin.nii.gz")) == True:
                #     skinImgPath = os.path.join(PPPath, "Skin.nii.gz")
                #     sitkImg = scoUtil.CScoUtilSimpleITK.load_image(skinImgPath, None)
                #     spacing_z = sitkImg.GetSpacing()[2]

                #     clipPosition = int((navelZID * spacing_z - 100)//spacing_z)
                #     self._clicked_recon_mask(clipPosition)
                # elif os.path.exists(os.path.join(APPath, "Skin.nii.gz")) == True:
                #     skinImgPath = os.path.join(APPath, "Skin.nii.gz")
                #     sitkImg = scoUtil.CScoUtilSimpleITK.load_image(skinImgPath, None)
                #     spacing_z = sitkImg.GetSpacing()[2]

                #     clipPosition = int((navelZID * spacing_z - 100)//spacing_z)
                #     self._clicked_recon_mask(clipPosition)
                # elif os.path.exists(os.path.join(HVPPath, "Skin.nii.gz")) == True:
                #     skinImgPath = os.path.join(HVPPath, "Skin.nii.gz")
                #     sitkImg = scoUtil.CScoUtilSimpleITK.load_image(skinImgPath, None)
                #     spacing_z = sitkImg.GetSpacing()[2]

                #     clipPosition = int((navelZID * spacing_z - 100)//spacing_z)
                #     self._clicked_recon_mask(clipPosition)
                # else:
                #     self._clicked_recon_mask(300) # 어차피 자를 필요 없음
                    #_manually_detect_navel()
            else:
                self._clicked_recon_mask(300) # 어차피 자를 필요 없음
                #_manually_detect_navel()


        def _check_blend_exist(navelZID):
            self.loading_dialog.close()
            
            unzipPath = self.m_editUnzipPath.text()
            blenderRoot = os.path.join(
                unzipPath, self.getui_edit_huid_path(), "02_SAVE", "02_BLENDER_SAVE"
            )
            if os.path.exists(os.path.join(blenderRoot, f"{self.getui_edit_huid_path()}_recon.blend")):
                reply = QMessageBox.question(
                    self.m_mediator,
                    "Re Do Recon",           
                    "이미 Recon blender가 존재합니다 다시 Recon 할까요?",   
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No 
                )

                if reply == QMessageBox.StandardButton.Yes:
                    _calculate_input_slice(navelZID)
                else:
                    self.execute_blender_save()
                    #self.do_blender()
            else:
                _calculate_input_slice(navelZID)
                
        self.loading_dialog = LoadingDialog(self.m_mediator)
        self.loading_dialog.show()
        self.worker = LoadingWorkerThread(self)
        self.worker.loadedFunction = _predict_navel_position
        self.worker.result_ready.connect(_check_blend_exist)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()
        
    def _command_reset_clinfo_inx(self) :
        dataInst = self.get_data()
        optionInfo = self.get_optioninfo()
            
        self.m_tvCLInfo.blockSignals(True)
        self.m_modelCLInfo.removeRows(0, self.m_modelCLInfo.rowCount())
        
        # for dataInfoInx in range(0, dataInst.DataInfo.get_info_count()) :
        #     clInfo = dataInst.DataInfo.get_clinfo(dataInfoInx)
        #     blenderName = clInfo.get_input_blender_name()
        #     outputName = clInfo.OutputName
        #     self.m_modelCLInfo.appendRow([QStandardItem(f"{dataInfoInx}"), QStandardItem(blenderName), QStandardItem(outputName)])
        globalCLinx = 0
        for clInx in range(optionInfo.get_centerline_count()):
            for listInx in range(optionInfo.get_centerline_list_count(clInx)):
                blenderName, outputName = optionInfo.get_centerline_list(clInx, listInx)
                self.m_modelCLInfo.appendRow([QStandardItem(f"{globalCLinx}"), QStandardItem(blenderName), QStandardItem(outputName)])
                globalCLinx += 1
                
            
        self.m_tvCLInfo.blockSignals(False)

        clinfoInx = dataInst.CLInfoIndex
        if clinfoInx == -1 :
            clinfoInx = 0
        if clinfoInx > optionInfo.get_centerline_list_count(clInx) :
            dataInst.CLInfoIndex = -1
            return

        self.setui_clinfo_inx(clinfoInx)
        self._command_clinfo_inx()

    def _command_clinfo_inx(self) :
        dataInst = self.get_data()
        self.m_mediator.unref_all_key()

        if dataInst.get_skelinfo_count() == 0 :
            self.m_mediator.update_viewer()
            return

        clinfoInx = self.getui_clinfo_inx()

        dataInst.CLInfoIndex = clinfoInx
        self.m_mediator.ref_key_type_groupID(dataInst.s_vesselType, clinfoInx)
        skeleton = dataInst.get_skeleton(clinfoInx)
        if skeleton is not None :
            self.m_mediator.ref_key_type_groupID(dataInst.s_skelTypeCenterline, clinfoInx)
        
        self.setui_check_sel_cell(False)
        self.setui_check_sel_cell(True)
        self.m_mediator.update_viewer()

        
    def _command_clinfo_inxs(self) :
        dataInst = self.get_data()
        self.m_mediator.unref_all_key()

        if dataInst.get_skelinfo_count() == 0 :
            self.m_mediator.update_viewer()
            return

        clinfoInxs = self.getui_clinfo_inxs()
        dataInst.m_clinfoIndexList = clinfoInxs
        
        if clinfoInxs:
            dataInst.CLInfoIndex = clinfoInxs[0]
            
        
        dataInst.m_clinfoIndexList = clinfoInxs
        #print(clinfoInxs, file=sys.__stdout__, flush=True)
        self.setui_check_sel_cell(False)
        self.setui_check_sel_cell(True)
        for clinfoInx in clinfoInxs:
            self.m_mediator.ref_key_type_groupID(dataInst.s_vesselType, clinfoInx)
            skeleton = dataInst.get_skeleton(clinfoInx)
            if skeleton is not None :
                self.m_mediator.ref_key_type_groupID(dataInst.s_skelTypeCenterline, clinfoInx)
            
            self.m_mediator.update_viewer()
            
    def command_centerline(self) :
        self._clear_centerline()
        dataInst = self.get_data()
        if dataInst.Ready == False :
            QMessageBox.information(self.m_mediator, "Alarm", "please setting option, outputPath, patientID")
            return

        userData = dataInst.UserData
        
        blenderFullPath = os.path.join(os.path.dirname(userData.OutputReconBlenderFullPath), f"{dataInst.PatientID}_clean.blend")

        if os.path.exists(blenderFullPath) == False :
            QMessageBox.information(self.m_mediator, "Alarm", f"not found {os.path.basename(blenderFullPath)}")
            return

        cmd = commandLoadingPatient.CCommandLoadingPatient(self.m_mediator)
        cmd.InputData = dataInst
        cmd.PatientBlenderFullPath = blenderFullPath
        cmd.process()

        self.setui_clear_clinfo()
        iCnt = dataInst.get_skelinfo_count()
        clInPath = dataInst.get_cl_in_path()
        for inx in range(0, iCnt) :
            skelinfo = dataInst.get_skelinfo(inx)
            blenderName = skelinfo.BlenderName
            vesselFullPath = os.path.join(f"{clInPath}", f"{blenderName}.stl")
            if os.path.exists(vesselFullPath) == False :
                continue
            self.setui_add_clinfo(inx, skelinfo)

        dataInst.CLInfoIndex = 0
        self.setui_clinfo_inx(dataInst.CLInfoIndex)
        self._command_clinfo_inx()

        fullPath = os.path.join(dataInst.OutputPatientPath, f"{data.CData.s_fileName}.json")
        dataInst.save(fullPath)
        self.m_mediator.update_viewer()
        #self.m_btnCL.setEnabled(False)

    def _on_btn_recon(self):
        if not self.m_reconReady: 
            self.m_mediator.show_dialog("Path Info 정보를 먼저 입력하세요.")
        else:
            self._cliked_recon_get_sliceID()
        # self._clicked_recon_mask() #sally
        
    def _on_btn_individual_recon(self) :
        if self.getui_edit_huid_path() == "" :
            print("not selection patientID")
            return
        if self.getui_edit_outtemp_path() == "" :
            print("not setting output path")
            return 
        
        dataInst = self.get_data()
        userdata = dataInst.UserData
        if userdata is None :
            print("not setting userdata")
            return
        
        if self.m_rbNonrigid.isChecked():
            userdata.m_registrationMethod = "non-rigid"
        else:
            userdata.m_registrationMethod = "rigid"
        if os.path.exists(userdata.OutputReconBlenderFullPath) == False :
            QMessageBox.information(self.m_mediator, "Alarm", f"must be reconstructed")
            return
        
        optioninfo = self.get_optioninfo()
        phaseNameList = optioninfo.get_phase_list()
        
        dlg = dlgCommon.CDlgIndividualReconInfo(self.m_mediator, phaseNameList)
        result = dlg.exec()

        if result == QDialog.Accepted :
            userdata.override_individual_recon(dlg.PhaseInfo)
        else :
            print("Cancel 클릭")
            
    def _on_btn_import_remodeled(self):
        patientID = self.getui_edit_huid_path()
        outputPatientPath = os.path.join(self.OutputPath, patientID)
        if os.path.exists(outputPatientPath) == False :
            print("not found output recon patient path")
            return 

        dataInst = self.get_data()
        #dataInst.load_patient(outputPatientPath)

        if dataInst.Ready == False :
            print("not setting option or patientID")
            return
        
        self._command_import_remodeling()
        return
        
    def _on_rb_nonrigid(self) :
        if self.m_bReady == False :
            return

        
    def _on_rb_rigid(self) :
        if self.m_bReady == False :
            return

    def _on_btn_overlap(self):
        if not self.m_reconReady: 
            self.m_mediator.show_dialog("Path Info 정보를 먼저 입력하세요.")
        else:
            self._clicked_overlap_loading()
        #self._clicked_overlap()
        
    def _on_btn_centerline(self):
        
        patientID = self.getui_edit_huid_path()
        outputPatientPath = os.path.join(self.OutputPath, patientID)
        if os.path.exists(outputPatientPath) == False :
            print(outputPatientPath)
            print("not found output recon patient path")
            return 

        dataInst = self.get_data()
        #dataInst.load_patient(outputPatientPath)

        if dataInst.Ready == False :
            print("not setting option or patientID")
            return
        self.command_centerline()

    def _on_btn_clean(self):
        if not self.m_reconReady: 
            self.m_mediator.show_dialog("Path Info 정보를 먼저 입력하세요.")
        else:
            self._cliked_clean_loading()
        #self._clicked_clean()  # sally
    
    def _on_tv_clicked_clinfo(self, index) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        self._command_clinfo_inx()
        
    def _on_selection_changed(self, selected, deselected):
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        self._command_clinfo_inxs()
        
    def _on_btn_do_blender(self):
        self._clicked_do_blender()

    def _on_cb_patientID_changed(self, index):
        #self.m_btnCL.setEnabled(True)
        patientID = self.getui_edit_huid_path()
        if patientID == "":
            print("not select patientID")
            return
        self._command_patientID()
        
    @property
    def OutputPath(self) -> str:
        return self.m_outputPath

    @OutputPath.setter
    def OutputPath(self, outputPath: str):
        self.m_outputPath = outputPath
        
    # protected 
    def _clear_optioninfo(self) :
        dataInst = self.get_data()
        self.m_mediator.remove_all_key()
        dataInst.clear_optioninfo()
    def _clear_patient(self) :
        dataInst = self.get_data()
        self.m_mediator.remove_all_key()
        dataInst.clear_patient()
    def _clear_centerline(self) :
        dataInst = self.get_data()
        self.m_mediator.remove_all_key()
        dataInst.clear_centerline()


    # slot
    def slot_drop_option_path(self, optionFullPath : str) :
        self.setui_edit_option_path("")

        if os.path.exists(optionFullPath) == False :
            return
        if optionFullPath.lower().endswith(".json") == False :
            return
        
        #self.m_btnCL.setEnabled(True)
        self.command_option_path(optionFullPath)
    def slot_drop_input_zip_path(self, inputZipFolderPath : str) :
        self.m_reconReady = True
        inputZipFolderPath = os.path.normpath(inputZipFolderPath)
        if os.path.exists(inputZipFolderPath) == False :
            return
        if os.path.isdir(inputZipFolderPath) == False :
            return
        
        #self.m_btnCL.setEnabled(True)
        dataInst = self.get_data()
        if dataInst.OptionInfo is None :
            QMessageBox.information(self.m_mediator, "Alarm", "please setting option file")
            return 

        self.command_input_zip_path(inputZipFolderPath)
        
    def command_refresh_optioninfo(self) :
        dataInst = self.get_data()
        dataRootPath = self.getui_edit_unzip_path()
        patientID = self.getui_edit_huid_path()
        outputPath = dataInst.OutputPath

        optioninfo = dataInst.OptionInfo
        optioninfo.DataRootPath = dataRootPath

        # 지정된 folder에서 mask list를 얻어옴 

        phaseMaskList = []

        unzipPath = dataRootPath
        maskRoot = os.path.join(unzipPath, patientID, "02_SAVE", "01_MASK")
        apPath = os.path.join(maskRoot, "AP")
        ppPath = os.path.join(maskRoot, "PP")
        hvpPath = os.path.join(maskRoot, "DP")        
        mrPath = os.path.join(maskRoot, "MR")
        list_ap = os.listdir(apPath)
        list_ap = [f.split('.')[0] for f in list_ap]
        list_pp = os.listdir(ppPath)
        list_pp = [f.split('.')[0] for f in list_pp]
        list_hvp = os.listdir(hvpPath)
        list_hvp = [f.split('.')[0] for f in list_hvp]
        list_mr = os.listdir(mrPath)
        list_mr = [f.split('.')[0] for f in list_mr]
        phaseMaskList.append({'phase':'AP', 'files': list_ap})
        phaseMaskList.append({'phase':'PP', 'files': list_pp})
        phaseMaskList.append({'phase':'DP', 'files': list_hvp})
        phaseMaskList.append({'phase':'MR', 'files': list_mr})

        '''
        key : maskName
        value : phase
        '''
        dicMaskPhase = {}
        '''
        key : phase
        value : kidneyName
        '''
        dicKidneyPhase = {}
        tumorToken = 'Tumor_'
        kidneyToken = 'Kidney_'
        tumorPhase = ""
        # tumor phase 감지 
        # phase별 kidney name 감지 
        for maskinfo in phaseMaskList :
            phase = maskinfo['phase']
            listMask = maskinfo['files']
            for maskName in listMask :
                dicMaskPhase[maskName] = phase
                # tumor phase 감지 
                if tumorToken in maskName :
                    tumorPhase = phase
                if kidneyToken in maskName :
                    dicKidneyPhase[phase] = maskName

        # optioninfo mask의 phase refresh
        iCnt = optioninfo.get_recon_count()
        for reconInx in range(0, iCnt) :
            listCnt = optioninfo.get_recon_list_count(reconInx)
            for listInx in range(0, listCnt) :
                maskName, _, _, _ = optioninfo.get_recon_list(reconInx, listInx)
                phase = ""
                if maskName in dicMaskPhase :
                    phase = dicMaskPhase[maskName]
                if tumorToken in maskName :
                    phase = tumorPhase
                if maskName == "Kidney" :
                    phase = tumorPhase
                optioninfo.set_recon_phase(maskName, phase)

        # kidney registration refresh 
        targetKidney = ""
        listSrcKidney = []

        for key, value in dicKidneyPhase.items() :
            if key == tumorPhase :
                targetKidney = value
            else :
                listSrcKidney.append(value)

        optioninfo.clear_registrationinfo()
        if targetKidney != "" :
            for srcKidney in listSrcKidney :
                optioninfo.add_registrationinfo(targetKidney, srcKidney, 0)

        self.command_post_refresh_optioninfo()
    def command_post_refresh_optioninfo(self) :
        dataInst = self.get_data()
        optioninfo = dataInst.OptionInfo

        # ResamplingToPhase 
        iCnt = optioninfo.get_resampling_phase_count()
        for inx in range(0, iCnt) :
            _, outMaskName, phase = optioninfo.get_resampling_phase(inx)
            optioninfo.set_recon_phase(outMaskName, phase)
        # ResamplingToMinSpacing 
        iCnt = optioninfo.get_resampling_minspacing_count()
        for inx in range(0, iCnt) :
            inMaskName, outMaskName = optioninfo.get_resampling_minspacing(inx)
            inPhase = optioninfo.find_phase_of_mask(inMaskName)
            optioninfo.set_recon_phase(outMaskName, inPhase)
        # Stricture
        iCnt = optioninfo.get_stricture_count()
        for inx in range(0, iCnt) :
            inMaskName, outMaskName = optioninfo.get_stricture(inx)
            inPhase = optioninfo.find_phase_of_mask(inMaskName)
            optioninfo.set_recon_phase(outMaskName, inPhase)
        # Diaphragm
        skinPhase = optioninfo.find_phase_of_mask("Skin")
        optioninfo.set_recon_phase("Diaphragm", skinPhase)

        optioninfo.process_phase_alignment()
        
    def _get_rootpath_huid(self, inputPath : str) -> tuple :
        '''
        ret 
            - (rootpath, huid)
            - rootpath : zip이 있는 path에서 dataRootPath가 생성 됨
            - huid : dataRootPath안에 huid 폴더가 생성 (기존 PatientID)
        '''
        rootpath = ''
        huid = ''
        mkInputFold = makeInputFolder.CMakeInputFolder()
        mkInputFold.ZipPath = inputPath
        mkInputFold.FolderMode = mkInputFold.eMode_Kidney 
        result = mkInputFold.process()
        if result == True :
            rootpath = mkInputFold.get_data_root_path()
            huid = mkInputFold.PatientID
            print(f"Making Input Folder Done. RootPath={rootpath}")
            
        return (rootpath, huid)
    
        
    # private


if __name__ == "__main__":
    pass


# print ("ok ..")

