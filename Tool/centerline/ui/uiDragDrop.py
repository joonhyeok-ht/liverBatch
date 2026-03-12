import sys
import os
import numpy as np
import shutil
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget, QLineEdit, QListWidget
from PySide6.QtCore import Qt


fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAppPath = os.path.dirname(fileAbsPath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import Block.makeInputFolder as makeInputFolder



class CUIDragDropLineEdit(QLineEdit) :
    def __init__(self, placeHolderText="Drop File Here") :
        super().__init__()
        self.setPlaceholderText(placeHolderText)
        self.setAcceptDrops(True)

        self.signal_drop_path = None    # slot_drop_path(fullPath : str)

    def dragEnterEvent(self, event) :
        if event.mimeData().hasUrls() :
            event.acceptProposedAction()
        else:
            event.ignore()
    def dropEvent(self, event) :
        if event.mimeData().hasUrls() :
            dropPath = event.mimeData().urls()[0].toLocalFile()
            # self.setText(file_path)
            if self.signal_drop_path is not None :
                self.signal_drop_path(dropPath)
            event.acceptProposedAction()


class CUIDragDropListWidget(QListWidget) :
    def __init__(self, tupleFileExt : tuple) :
        '''
        tupleFileExt
            - ex, (".nii.gz", ".zip")
        '''
        super().__init__()

        self.m_tupleFileExt = tupleFileExt
        self.m_setFullPath = set()
        self.m_listFullPath = []
        self.m_listFile = []

        # drag & drop 허용
        self.setAcceptDrops(True)

        # UI 스타일
        self.setStyleSheet("""
        QListWidget {
            border: 2px dashed #aaa;
            padding: 5px;
        }
        """)
    def clear(self) :
        self.m_setFullPath.clear()
        self.m_listFullPath.clear()
        self.m_listFile.clear()
        return super().clear()
    

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() :
            event.acceptProposedAction()
        else:
            event.ignore()
    def dragMoveEvent(self, event) :
        event.acceptProposedAction()
    def dropEvent(self, event) :
        if not event.mimeData().hasUrls() :
            event.ignore()
            return
        for url in event.mimeData().urls() :
            path = url.toLocalFile()
            path = os.path.normpath(path)
            # 폴더 드롭 처리
            if os.path.isdir(path) :
                listFullPath = makeInputFolder.CFileOper.get_files_fullpath(path, self.m_tupleFileExt)
                if listFullPath is None :
                    continue

                for fullPath in listFullPath :
                    self.add_file(fullPath)
            else :
                if path.lower().endswith(self.m_tupleFileExt) :
                    self.add_file(path)

        event.acceptProposedAction()

    # protected
    def add_file(self, path : str) :
        # 중복 방지 
        if path in self.m_setFullPath :
            return

        self.m_setFullPath.add(path)
        self.m_listFullPath.append(path)

        file = os.path.basename(path)
        self.m_listFile.append(file)
        self.addItem(file)


if __name__ == '__main__' :
    pass


# print ("ok ..")

