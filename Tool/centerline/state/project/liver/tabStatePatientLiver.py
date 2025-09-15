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
    QHBoxLayout
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QPixmap
import command.commandExtractionCL as commandExtractionCL

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAppPath = os.path.dirname(fileAbsPath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import state.project.liver.userDataLiverBatch as userDataLiver

import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath

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
import subUtils.checkIntegrityStomach as checkIntegrity
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



class CSVPopup(QDialog):
    def __init__(self, csv_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Integrity Table")

        layout = QVBoxLayout(self)
        table = QTableWidget(self)

        if csv_data:
            row_count = len(csv_data)
            col_count = len(csv_data[0])

            table.setRowCount(row_count)
            table.setColumnCount(col_count)

            for row_idx, row in enumerate(csv_data):
                for col_idx, value in enumerate(row):
                    table.setItem(row_idx, col_idx, QTableWidgetItem(value))

        layout.addWidget(table)
        self.setLayout(layout)

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

class WorkerThread(QThread):
    progress_changed = Signal(int, str)
    finished = Signal()
    canceled = Signal()

    def __init__(self, inst):
        super().__init__()
        self._is_interrupted = False
        self.inst = inst

    def run(self):
        try:
            self.inst.progress_callback = self.progress_callback
            self.inst.is_interrupted = lambda: self._is_interrupted
            success = self.inst.process()
            if not success:
                self.canceled.emit()
            else:
                self.finished.emit()
        except Exception as e:
            print(f"[WorkerThread] 예외 발생: {e}")
            self.canceled.emit()

    def progress_callback(self, value, status=""):
        self.progress_changed.emit(value, status)

    def cancel(self):
        self._is_interrupted = True


class ProgressWindow(QDialog):
    def __init__(self, parent, inst):
        super().__init__(parent)
        self.setWindowTitle("Processing...")
        self.setFixedSize(300, 120)

        layout = QVBoxLayout(self)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Loading ...")
        layout.addWidget(self.status_label)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_task)
        layout.addWidget(self.cancel_button)

        self._was_canceled = False
        self._done = False

        self.worker = WorkerThread(inst)
        self.worker.progress_changed.connect(self.update_progress, Qt.QueuedConnection)
        self.worker.finished.connect(self.on_finished)
        self.worker.canceled.connect(self.on_canceled)
        self.worker.start()

    def update_progress(self, value: int, status: str):
        self.progress_bar.setValue(value)
        self.status_label.setText(status)

    def cancel_task(self):
        self._was_canceled = True
        self.worker.cancel()

    def on_finished(self):
        if self._done:
            return
        self._done = True
        self.accept()

    def on_canceled(self):
        if self._done:
            return
        self._done = True
        self.reject()


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
        self.m_btnCL = None
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
        
        super().clear()

    def process_init(self):
        pass

    def process(self):
        pass

    def process_end(self):
        pass

    def changed_project_type(self):
        self.m_optionFullPath = os.path.join(self.m_mediator.FilePath, "option.json")
        if os.path.exists(self.m_optionFullPath) == False:
            self.m_optionFullPath = os.path.join(
                self.m_mediator.CommonPipelinePath, "option.json"
            )
            if os.path.exists(self.m_optionFullPath) == False:
                self.m_optionFullPath = ""

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

        # sally
        layout, self.m_editInputPath, btn = (
            self.m_mediator.create_layout_label_editbox_btn("Input", False, "..")
        )
        btn.clicked.connect(self._on_btn_input_zip_path)
        tabLayout.addLayout(layout)
        # sally
        layout, self.m_editUnzipPath, btn = (
            self.m_mediator.create_layout_label_editbox_btn("Output", False, "..")
        )
        btn.clicked.connect(self._on_btn_unzip_path)
        tabLayout.addLayout(layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        layout, self.m_editOptionPath, btn = (
            self.m_mediator.create_layout_label_editbox_btn("Option", False, "..")
        )
        btn.clicked.connect(self._on_btn_option_path)
        tabLayout.addLayout(layout)

        layout, self.m_editOutputPath, btn = (
            self.m_mediator.create_layout_label_editbox_btn(
                f"{CTabStatePatient.s_intermediatePathAlias}", False, ".."
            )
        )
        btn.clicked.connect(
            self._on_btn_output_temp_path
        )  # rename output -> media (sally)
        tabLayout.addLayout(layout)

        layout, self.m_cbPatientID = self.m_mediator.create_layout_label_combobox(
            "PatientID"
        )
        self.m_cbPatientID.currentIndexChanged.connect(self._on_cb_patientID_changed)
        tabLayout.addLayout(layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        label = QLabel("-- Reconstruction STEP --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        layout, btnList = self.m_mediator.create_layout_btn_array(
            CTabStatePatient.s_listStepName
        )
        for inx, stepName in enumerate(CTabStatePatient.s_listStepName):
            btnList[inx].clicked.connect(self.m_listStepBtnEvent[inx])
        tabLayout.addLayout(layout)
        self.m_btnCL = btnList[2]

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
        self.m_tvCLInfo.setSelectionBehavior(QTableView.SelectRows)
        self.m_tvCLInfo.clicked.connect(self._on_tv_clicked_clinfo)
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


        input_advancementRatio = QLineEdit()
        input_advancementRatio.setPlaceholderText(f"advancement ratio 입력")
        input_advancementRatio.setText(str(1.001))
        input_advancementRatio.textChanged.connect(self.on_advancement_ratio_changed)
        tabLayout.addWidget(input_advancementRatio)
        

        btn = QPushButton("Extraction Centerline")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_extraction_centerline)
        tabLayout.addWidget(btn)

        # sally
        btn = QPushButton("Do Blender")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_do_blender)
        tabLayout.addWidget(btn)
        

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
        
    def setui_cellID(self, cellID : int) :
        self.m_editBoxCellID.setText(str(cellID))

    def setui_patientID(self, inx: int):
        self.m_cbPatientID.blockSignals(True)
        self.m_cbPatientID.setCurrentIndex(inx)
        self.m_cbPatientID.blockSignals(False)

    def setui_reset_patientID(self, listPatientID: str):
        self.m_cbPatientID.blockSignals(True)
        self.m_cbPatientID.clear()
        for patientID in listPatientID:
            self.m_cbPatientID.addItem(f"{patientID}")
        self.m_cbPatientID.blockSignals(False)
        self.setui_patientID(0)

    def setui_output_path(self, outputPath: str):
        self.m_editOutputPath.setText(outputPath)
        
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
    def getui_patientID(self) -> str:
        return self.m_cbPatientID.currentText()

    def getui_output_path(self) -> str:
        return self.m_editOutputPath.text()
    
    def getui_cellID(self) -> int :
        cellID = -1
        try :
            cellID = int(self.m_editBoxCellID.text())
        except ValueError:
            cellID = -1
        return cellID

    # command
    def _command_option_path(self) -> bool:
        dataInst = self.get_data()
        self.m_mediator.remove_all_key()
        dataInst.clear_patient()

        self.m_editOptionPath.setText(self.m_optionFullPath)
        if self.m_optionFullPath == "":
            return False
        # unzipPath = self.m_editUnzipPath.text() #sally

        optionFullPath = self.m_optionFullPath
        dataInst.load_optioninfo(optionFullPath)
        dataInst.CLColor = algLinearMath.CScoMath.to_vec3([0.3, 0.3, 0.0])
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
        
        if self.m_dataRootPath != "" and self.m_patientID != "" :
            realPhaseMaskList = self._get_real_phase_name(self.m_dataRootPath, self.m_patientID)
            # 마스크들의 실제 Phase 폴더에 맞춰 maskInfo를 갱신함.
            for phaseMask in realPhaseMaskList :
                for maskfile in phaseMask['files'] :
                    maskname = maskfile.split('.')[0]
                    maskInfo = dataInst.m_optionInfo.find_maskinfo_by_blender_name(maskname)
                    if maskInfo != None :
                        maskInfo.Phase = phaseMask['phase']
        else:
            return False
        
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
        phaseMaskList.append({'phase':'HVP', 'files': list_hvp})
        phaseMaskList.append({'phase':'MR', 'files': list_mr})
        print(f"PhaseMaskList : {phaseMaskList}", file=sys.__stdout__, flush=True)
        
        return phaseMaskList
        

    def _command_patientID(self):
        dataInst = self.get_data()
        self.m_mediator.remove_all_key()
        dataInst.clear_patient()
        self.m_outputPath = self.getui_output_path()
        self.m_mediator.update_viewer()

    def _generate_progress_window(self, instance):

        dialog = ProgressWindow(self.m_mediator, instance)
        result = dialog.exec()

        if result == QDialog.Accepted:
            QMessageBox.information(self.m_mediator, "Done", "작업이 완료되었습니다!")
            return True
        elif result == QDialog.Rejected:
            QMessageBox.warning(self.m_mediator, "Canceled", "작업이 취소되었습니다.")
            return False

    # protected
    def _get_userdata(self) -> userDataLiver.CUserDataLiver:
        return self.get_data().find_userdata(
            userDataLiver.CUserDataLiver.s_userDataKey
        )
        
    def _command_extraction_cl(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            print("not setting patient path")
            return

        clOutPath = dataInst.get_cl_out_path()
        if os.path.exists(clOutPath) == False :
            print("not found clOutPath")
            return False
        clInPath = dataInst.get_cl_in_path()
        if os.path.exists(clInPath) == False :
            print("not found clInPath")
            return False

        clinfoInx = self.get_clinfo_index()
        clinfo = dataInst.DataInfo.get_clinfo(clinfoInx)

        self.m_mediator.remove_key_type_groupID(data.CData.s_skelTypeCenterline, clinfoInx)
        self.m_mediator.remove_key_type_groupID(data.CData.s_skelTypeBranch, clinfoInx)
        self.m_mediator.remove_key_type_groupID(data.CData.s_skelTypeEndPoint, clinfoInx)
        
        startCellID = self.getui_cellID()
        if startCellID > -1 :
            vesselKey = data.CData.make_key(data.CData.s_vesselType, clinfoInx, 0)
            vesselObj = dataInst.find_obj_by_key(vesselKey)
            if vesselObj is None :
                print("not found vessel polydata")
                return
            # vessel의 min-max 추출 및 정육면체 생성
            vesselPolyData = vesselObj.PolyData
            blenderName = clinfo.get_input_blender_name()
            vtpFullPath = os.path.join(clInPath, f"{blenderName}.vtp")
            algVTK.CVTK.save_poly_data_vtp(vtpFullPath, vesselPolyData)
        
        cmd = commandExtractionCL.CCommandExtractionCL(self.m_mediator)
        cmd.InputData = dataInst
        cmd.InputIndex = clinfoInx
        cmd.InputAdvancementRatio = self.m_advancementRatio
        cmd.InputCellID = self.getui_cellID()
        cmd.process()

        clOutput = clinfo.OutputName
        clOutputFullPath = os.path.join(clOutPath, f"{clOutput}.json")
        if os.path.exists(clOutputFullPath) == False :
            print(f"not found skelinfo : {clOutputFullPath}")
            return False
        
        dataInst.set_skeleton(clinfoInx, clOutputFullPath)
        self.m_mediator.load_cl_key(clinfoInx)
        self.m_mediator.load_br_key(clinfoInx)
        self.m_mediator.load_ep_key(clinfoInx)

        self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeCenterline, clinfoInx)
        self.m_mediator.update_viewer()


    def _changed_input_path(self, inputPath) -> str:
        rootpath = ""
        huid = ""
        mkInputFold = makeInputFolder.CMakeInputFolder()
        mkInputFold.ZipPath = inputPath  # "D:\\jys\\StomachKidney_newfolder\\zippath"
        mkInputFold.FolderMode = mkInputFold.eMode_Liver
        result = mkInputFold.process()
        if result == True:
            rootpath = mkInputFold.get_data_root_path()
            huid = mkInputFold.PatientID
            print(f"Making Input Folder Done. RootPath={rootpath}")

        return rootpath, huid

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

        currPatientID = self.getui_patientID()
        if currPatientID == "":
            print(f"ERROR : CurrPatientID is empty.")
            return
        stlPath = os.path.join(self.m_outputPath, currPatientID, "Result")
        savePath = os.path.join(
            self.m_dataRootPath, currPatientID, "02_SAVE", "02_BLENDER_SAVE"
        )
        cmd = f"{dataInst.OptionInfo.BlenderExe} --python {os.path.join(self.fileAbsPath, 'blenderScriptLiver.py')} -- --patient_id {currPatientID} --stl_path {stlPath} --out_path {savePath} --func_mode Basic --option_path {self.m_optionFullPath}"
        os.system(cmd)
        
    def execute_blender_save(self):
        dataInst = self.get_data()
        unzipPath = self.m_editUnzipPath.text()
        
        BlenderPath = os.path.join(
            unzipPath, self.getui_patientID(), "02_SAVE", "02_BLENDER_SAVE", "Auto01_Recon", f"{self.getui_patientID()}.blend"
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
        dataInst = self.get_data()
        if dataInst.OptionInfo.m_registrationInfo == None:
            self.m_mediator.show_dialog("ERROR !!!! : m_registrationInfo is None .")
            return

        if self.m_reconReady == True:
            reconInst = reconLiver.CSubReconLiver()
            reconInst.InputSliceID = inputSliceID
            reconInst.OptionPath = self.m_optionFullPath
            reconInst.PatientID = self.getui_patientID()
            unzipPath = self.m_editUnzipPath.text()
            maskRoot = os.path.join(
                unzipPath, self.getui_patientID(), "02_SAVE", "01_MASK"
            )
            reconInst.APPath = os.path.join(maskRoot, "Mask_AP")
            reconInst.PPPath = os.path.join(maskRoot, "Mask_PP")
            reconInst.HVPPath = os.path.join(maskRoot, "Mask_HVP")
            reconInst.MRPath = os.path.join(maskRoot, "Mask_MR")
            reconInst.IntermediateDataPath = self.m_outputPath

            self.m_mediator.load_userdata()
            userData = self._get_userdata()
            dataInst = self.get_data()
            result = reconInst.init(dataInst.OptionInfo, userData)
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
            # Step1 : Auto01_Recon의 .blend의 obj들을 export.
            dataInst = self.get_data()
            currPatientID = self.getui_patientID()
            if currPatientID == "":
                print(f"ERROR : CurrPatientID is empty.")
                return
            # stlPath = os.path.join(self.m_outputPath, currPatientID, "Result")
            savePath = os.path.join(
                self.m_dataRootPath, currPatientID, "02_SAVE", "02_BLENDER_SAVE"
            )

            outputPatientFullPath = os.path.join(self.m_outputPath, currPatientID)
            exportStlPath = os.path.join(outputPatientFullPath, "ExportStl")
            
            if not os.path.exists(exportStlPath):
                os.makedirs(exportStlPath)
            
            cmd = f"{dataInst.OptionInfo.BlenderExe} -b --python {os.path.join(self.fileAbsPath, 'blenderScriptLiver.py')} --\
                --patient_id {currPatientID} \
                --func_mode Export \
                --input_blend_path {os.path.join(savePath, 'Auto01_Recon')}\
                --export_path {exportStlPath}"
            os.system(cmd)

            # Step2 : Overlap Detect 수행
            # Step3 : Detecting결과를 다시 .blend 에 import
            overlap = detectOverlap.CSubDetectOverlap()
            outputPatientFullPath = os.path.join(self.m_outputPath, currPatientID)
            overlap.StlPath = os.path.join(outputPatientFullPath, "ExportStl")
            overlap.LogPath = outputPatientFullPath
            overlap.process()

            cmd = f"{dataInst.OptionInfo.BlenderExe} --python {os.path.join(self.fileAbsPath, 'blenderScriptLiver.py')} -- \
            --func_mode ImportSave \
            --patient_id {currPatientID} \
            --option_path {self.m_optionFullPath} \
            --stl_path {exportStlPath} \
            --out_path {savePath}"
            os.system(cmd)
            
        def end_overlap(result):
            self.loading_dialog.close()
            self.m_mediator.show_dialog(f"OverlapDetection(.blend) Done.")
        
        self.worker = LoadingWorkerThread(self)
        self.worker.loadedFunction = _clicked_overlap
        self.worker.result_ready.connect(end_overlap)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()
      
    def _cliked_integrity_check(self):
        integrityInst = checkIntegrity.CCheckIntegrityStomach()
        integrityInst.OptionPath = self.m_optionFullPath
        self._generate_progress_window(integrityInst)
        
        unzipPath = self.m_editUnzipPath.text()
        file_path = os.path.join(unzipPath, "Integrity_Check.csv")

        if os.path.exists(file_path):
            with open(file_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                data = list(reader)
                
            if len(data) == 0:
                self.m_mediator.show_dialog("No integrity issues.")
            else:
                integrityPopup = CSVPopup(data, self.m_mediator)
                integrityPopup.resize(600, 400)
                integrityPopup.exec()
                
        else:
            self.m_mediator.show_dialog("No integrity issues.")
        

    def _cliked_clean_loading(self):
        self.loading_dialog = LoadingDialog(self.m_mediator)
        self.loading_dialog.show()
        dataInst = self.get_data()
        unzipPath = self.m_editUnzipPath.text()
        currPatientID = self.getui_patientID()

        if currPatientID == "":
            print(f"ERROR : CurrPatientID is empty.")
            return
        stlPath = os.path.join(self.m_outputPath, currPatientID, "Result")
        savePath = os.path.join(
            self.m_dataRootPath, currPatientID, "02_SAVE", "02_BLENDER_SAVE"
        )
        def _clicked_clean(self):
            # currPatientID = self.getui_patientID()

            # if currPatientID == "":
            #     print(f"ERROR : CurrPatientID is empty.")
            #     return
            # stlPath = os.path.join(self.m_outputPath, currPatientID, "Result")
            # savePath = os.path.join(
            #     self.m_dataRootPath, currPatientID, "02_SAVE", "02_BLENDER_SAVE"
            # )
            
            overlapBlenderPath = os.path.join(
                unzipPath, self.getui_patientID(), "02_SAVE", "02_BLENDER_SAVE", "Auto02_Overlap", f"{self.getui_patientID()}.blend"
            )
            
            if os.path.exists(overlapBlenderPath) == False :
                print(f"ERROR : Not Found {overlapBlenderPath}. return.")
                self.m_mediator.show_dialog(f"Auto02_Overlap 폴더에 .blend 파일이 존재하지 않습니다.")
                return

            cmd = f'{dataInst.OptionInfo.BlenderExe} -b --python {os.path.join(self.fileAbsPath, "blenderScriptLiver.py")} -- \
            --func_mode "MeshClean" \
            --patient_id "{currPatientID}" \
            --option_path "{self.m_optionFullPath}" \
            --stl_path "{stlPath}" \
            --overlap_path "{overlapBlenderPath}" \
            --out_path "{savePath}"'

            os.system(cmd)
            
        def end_clean(result):
            self.loading_dialog.close()
            self.m_mediator.show_dialog(f"Mesh-Clean Done")
            
            openPath = os.path.join(
                unzipPath, self.getui_patientID(), "02_SAVE", "02_BLENDER_SAVE", "Auto03_MeshClean", f"{self.getui_patientID()}.blend"
            )
            
            # cmd = f'{dataInst.OptionInfo.BlenderExe} "{cleanupBlenderPath}"'
            # os.system(cmd)
            
            cmd = f"{dataInst.OptionInfo.BlenderExe} --python {os.path.join(self.fileAbsPath, 'blenderScriptLiver.py')} -- --patient_id {currPatientID} --stl_path {stlPath} --option_path {self.m_optionFullPath} --open_path {openPath} --out_path {savePath} --func_mode OpenBlend"
            os.system(cmd)
                
            
            
        self.worker = LoadingWorkerThread(self)
        self.worker.loadedFunction = _clicked_clean
        self.worker.result_ready.connect(end_clean)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()
        

    # ui event
    def _on_btn_extraction_centerline(self) :
        self._command_extraction_cl()
    
    def _on_btn_option_path(self):
        self.m_btnCL.setEnabled(True)
        optionPath, _ = QFileDialog.getOpenFileName(
            self.get_main_widget(), "Select Option File", "", "JSON Files (*.json)"
        )
        if optionPath == "":
            return
        self.m_optionFullPath = optionPath
        self._command_option_path()

    def _on_btn_input_zip_path(self):  # sally
        inputPath = QFileDialog.getExistingDirectory(
            self.get_main_widget(), "Select Zip Folder"
        )
        self.m_editInputPath.setText(inputPath)
        self.m_editUnzipPath.setText("")
        if inputPath == "":
            return
        root_path, huid = self._changed_input_path(inputPath)
        self.m_editUnzipPath.setText(root_path)
        option_path = self.m_optionFullPath
        self._changed_unzip_path(option_path, root_path)
        self.setui_reset_patientID([huid])
        self.m_zipPathPatientID = huid  # sally: 이값을 저장해 놓았다가 _on_btn_unzip_path() 수행시 감지한 huid 와 이 값이 다르면 self.m_editInputPath 칸을 클리어한다.

        self._out_temp_auto_setting(root_path)

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
        self.m_mediator.show_dialog("입력데이터 로딩 완료. Recon 버튼을 클릭하세요!")

    def _on_btn_output_temp_path(self):
        self.m_btnCL.setEnabled(True)
        outputPath = QFileDialog.getExistingDirectory(
            self.get_main_widget(),
            f"Select {CTabStatePatient.s_intermediatePathAlias} Path",
        )
        self._changed_output_temp_path(outputPath)

    def _cliked_recon_get_sliceID(self):

        def _predict_navel_position(self) -> int:
            unzipPath = self.m_editUnzipPath.text()
            DicomPPPath = os.path.join(
                unzipPath, self.getui_patientID(), "01_DICOM", "PP"
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
                unzipPath, self.getui_patientID(), "02_SAVE", "01_MASK"
            )
            HVPPath = os.path.join(maskRoot, "Mask_HVP")
            PPPath = os.path.join(maskRoot, "Mask_PP")
            APPath = os.path.join(maskRoot, "Mask_AP")
            
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
                    unzipPath, self.getui_patientID(), "02_SAVE", "01_MASK"
                )
                PPPath = os.path.join(maskRoot, "Mask_PP")

                if os.path.exists(os.path.join(PPPath, "Skin.nii.gz")) == True:
                    skinImgPath = os.path.join(PPPath, "Skin.nii.gz")
                    sitkImg = scoUtil.CScoUtilSimpleITK.load_image(skinImgPath, None)
                    spacing_z = sitkImg.GetSpacing()[2]

                    clipPosition = int((navelZID * spacing_z - 100)//spacing_z)
                    self._clicked_recon_mask(clipPosition)
            else:
                _manually_detect_navel()


        def _check_blend_exist(navelZID):
            self.loading_dialog.close()
            
            unzipPath = self.m_editUnzipPath.text()
            blenderRoot = os.path.join(
                unzipPath, self.getui_patientID(), "02_SAVE", "02_BLENDER_SAVE", "Auto01_Recon"
            )
            if os.path.exists(os.path.join(blenderRoot, f"{self.getui_patientID()}.blend")):
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

        self.m_tvCLInfo.blockSignals(True)
        self.m_modelCLInfo.removeRows(0, self.m_modelCLInfo.rowCount())
        for dataInfoInx in range(0, dataInst.DataInfo.get_info_count()) :
            clInfo = dataInst.DataInfo.get_clinfo(dataInfoInx)
            blenderName = clInfo.get_input_blender_name()
            outputName = clInfo.OutputName
            self.m_modelCLInfo.appendRow([QStandardItem(f"{dataInfoInx}"), QStandardItem(blenderName), QStandardItem(outputName)])
        self.m_tvCLInfo.blockSignals(False)

        clinfoInx = dataInst.CLInfoIndex
        if clinfoInx == -1 :
            clinfoInx = 0
        if clinfoInx > dataInst.DataInfo.get_info_count() :
            dataInst.CLInfoIndex = -1
            return

        self.setui_clinfo_inx(clinfoInx)
        self._command_clinfo_inx()

    def _command_clinfo_inx(self) :
        dataInst = self.get_data()
        self.m_mediator.unref_all_key()

        if dataInst.get_skeleton_count() == 0 :
            self.m_mediator.update_viewer()
            return

        clinfoInx = self.getui_clinfo_inx()
        dataInst.CLInfoIndex = clinfoInx
        self.m_mediator.ref_key_type_groupID(dataInst.s_vesselType, clinfoInx)
        skeleton = dataInst.get_skeleton(clinfoInx)
        if skeleton is not None :
            self.m_mediator.ref_key_type_groupID(dataInst.s_skelTypeCenterline, clinfoInx)
        
        self.m_mediator.update_viewer()

    def _command_centerline(self) :
        dataInst = self.get_data()
        self.m_mediator.remove_all_key()

        patientID = self.getui_patientID()
        outputPatientPath = os.path.join(self.OutputPath, patientID)

        cmd = commandLoadingPatient.CCommandLoadingPatient(self.m_mediator)
        cmd.InputData = dataInst
        
        unzipPath = self.m_editUnzipPath.text()
        blenderRoot = os.path.join(
            unzipPath, self.getui_patientID(), "02_SAVE", "02_BLENDER_SAVE", "Auto03_MeshClean"
        )
        cmd.PatientBlenderFullPath = os.path.join(blenderRoot, f"{self.getui_patientID()}.blend")
        #cmd.PatientBlenderFullPath = os.path.join(outputPatientPath, f"{self.getui_patientID()}_recon.blend")
        cmd.process()
        self.m_mediator.load_userdata()

        self._command_reset_clinfo_inx()
        self.m_btnCL.setEnabled(False)

    def _on_btn_integrity_mask(self):
        if not self.m_reconReady: 
            self.m_mediator.show_dialog("Path Info 정보를 먼저 입력하세요.")
        else:
            self._cliked_integrity_check()

    def _on_btn_recon(self):
        if not self.m_reconReady: 
            self.m_mediator.show_dialog("Path Info 정보를 먼저 입력하세요.")
        else:
            self._cliked_recon_get_sliceID()
        # self._clicked_recon_mask() #sally

    def _on_btn_overlap(self):
        if not self.m_reconReady: 
            self.m_mediator.show_dialog("Path Info 정보를 먼저 입력하세요.")
        else:
            self._clicked_overlap_loading()
        #self._clicked_overlap()
        
    def _on_btn_centerline(self):
        print("centerline")
        
        patientID = self.getui_patientID()
        outputPatientPath = os.path.join(self.OutputPath, patientID)
        if os.path.exists(outputPatientPath) == False :
            print("not found output recon patient path")
            return 

        dataInst = self.get_data()
        dataInst.load_patient(outputPatientPath)

        if dataInst.Ready == False :
            print("not setting option or patientID")
            return
        self._command_centerline()

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

    def _on_btn_do_blender(self):
        self._clicked_do_blender()

    def _on_cb_patientID_changed(self, index):
        self.m_btnCL.setEnabled(True)
        patientID = self.getui_patientID()
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

    # private


if __name__ == "__main__":
    pass


# print ("ok ..")
