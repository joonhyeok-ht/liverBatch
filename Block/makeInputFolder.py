'''
File : makeInputFolder.py
Version : 2025_03_27
'''
# 24.11.01 : add Lung
# 25.03.27 : 25'3월 기준으로 output 폴더구조 변경, nifti파일만 따로 zip으로 묶는기능 추가

import os
import shutil
import sys
from distutils.dir_util import copy_tree
import glob
from pathlib import Path


class CFileOper : 
    @staticmethod
    def rename_file(fullPath : str, rename : str) :
        pass
    @staticmethod
    def get_files_fullpath(folderPath : str, extensions : tuple) -> list :
        '''
        ret 
            - [fullPath0, fullPath1, ..]
            - None : error or empty list
        '''
        target = Path(folderPath)
        listFullPath = []

        for file in target.rglob("*") :
            if file.is_file() and file.name.lower().endswith(extensions) :
                listFullPath.append(str(file))

        if len(listFullPath) == 0 :
            return None
        return listFullPath

    @staticmethod
    def copy_file(targetPath : str, fullPath : str) :
        target = Path(targetPath)
        target.mkdir(parents=True, exist_ok=True)

        src = Path(fullPath)
        if not src.is_file() :
            return

        dst = target / src.name
        shutil.copy2(src, dst)
    @staticmethod
    def copy_folder(targetPath : str, folderPath : str) :
        '''
        desc
            - folderPath의 모든 내용을 targetPath로 복사 
            - targetPath가 존재하지 않을 경우, 내부적으로 폴더를 생성한다. 
        '''
        target = Path(targetPath)
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(folderPath, targetPath, dirs_exist_ok=True)
    @staticmethod
    def copy_folder_ext(targetPath : str, folderPath : str, extensions : tuple) :
        '''
        desc
            - folderPath의 extensions 확장자들을 targetPath로 복사
            - folderPath의 하위 folder들을 포함한다. 
            - targetPath가 존재하지 않을 경우, 내부적으로 폴더를 생성한다. 
        
        input
            - extensions : ("nii.gz", "zip")
        '''
        target = Path(targetPath)
        target.mkdir(parents=True, exist_ok=True)

        for file in Path(folderPath).rglob("*") :
            if file.is_file() and file.name.lower().endswith(extensions) :
                shutil.copy2(file, target / file.name)
    
    @staticmethod
    def remove_file(fullPath : str) :
        path = Path(fullPath)

        if path.exists() and path.is_file() :
            path.unlink()
    @staticmethod
    def remove_folder(folderPath : str) :
        path = Path(folderPath)

        if path.exists() and path.is_dir() :
            shutil.rmtree(path)

    @staticmethod
    def unzip_file(targetPath : str, zipFullPath : str) :
        '''
        desc
            - targetPath에는 폴더를 별도로 생성하지 않고 zip이 바로 풀림
            - 따라서 targetPath의 특정 폴더에 zip이 풀리길 원한다면 targetPath에 해당 foler도 지정되어야 함 
        '''
        if os.path.exists(zipFullPath) == False :
            return
        target = Path(targetPath)
        target.mkdir(parents=True, exist_ok=True)
        shutil.unpack_archive(zipFullPath, targetPath, "zip")
    @staticmethod
    def zip_folder(targetPath : str, folderPath : str) -> str :
        '''
        ret : zip fullPath
        '''
        if os.path.exists(targetPath) == False :
            return
        if os.path.exists(folderPath) == False :
            return
        zipName = os.path.basename(folderPath)
        zipName = os.path.join(targetPath, zipName)
        shutil.make_archive(zipName, 'zip', folderPath)
        return f"{zipName}.zip"
    
    @staticmethod
    def unzip_in_folder(folderPath : str) :
        '''
        desc
            - folderPath 내에 있는 모든 .zip의 압축을 같은 위치에서 푼다.
            - 하위 폴더도 포함하여 검색한다. 
        '''
        if os.path.exists(folderPath) == False :
            return
        
        root = Path(folderPath)

        for zip_file in root.rglob("*.zip") :
            if zip_file.is_file() :
                extract_dir = zip_file.parent / zip_file.stem
                extract_dir.mkdir(exist_ok=True)
                shutil.unpack_archive(zip_file, extract_dir, "zip")


    def __init__(self) :
        pass
    def clear(self) :
        pass


class CMakeInputFolder :
    TAG = "[MakeInputFolder] "
    s_dataRootName = "dataRoot"

    s_dicomName = "01_DICOM"
    s_saveName = "02_SAVE"

    s_maskName = "01_MASK"
    s_blenderSaveName = "02_BLENDER_SAVE"
    s_pneumoSaveName = "03_PNEUMO_SAVE"

    sZip_Dicom = "DICOM.zip"


    def __init__(self) -> None :
        self.m_zipPath = ""

        self.m_patientID = "" 
        self.m_dataRootPath = "" 
        self.m_dataRootPatientPath = "" 

        self.m_dicomPath = ""
        self.m_savePath = ""

        self.m_maskPath = ""
        self.m_blenderSavePath = ""
        self.m_pneumoSavePath = ""

        self.m_listPhaseZip = []
        self.m_listPhaseZipName = []

        self.m_bReady = False
        self.m_optionInfo = None
    def clear(self) :
        self.m_zipPath = ""

        self.m_patientID = ""
        self.m_dataRootPath = ""
        self.m_dataRootPatientPath = ""

        self.m_dicomPath = ""
        self.m_savePath = ""

        self.m_maskPath = ""
        self.m_blenderSavePath = ""
        self.m_pneumoSavePath = ""

        self.m_listPhaseZip.clear()
        self.m_listPhaseZipName.clear()

        self.m_bReady = False
        self.m_optionInfo = None
    def process(self) -> bool :
        self.Ready = False

        if self.m_zipPath == "" :
            print(self.TAG, "ERROR - please setting zip full path")
            return False
        
        self.m_patientID = os.path.basename(self.m_zipPath)
        self.m_dataRootPath = os.path.join(self.m_zipPath, CMakeInputFolder.s_dataRootName)
        self.m_dataRootPatientPath = os.path.join(self.m_dataRootPath, self.m_patientID)

        self.m_dicomPath = os.path.join(self.m_dataRootPatientPath, CMakeInputFolder.s_dicomName)
        self.m_savePath = os.path.join(self.m_dataRootPatientPath, CMakeInputFolder.s_saveName)

        self.m_maskPath = os.path.join(self.m_savePath, CMakeInputFolder.s_maskName)
        self.m_blenderSavePath = os.path.join(self.m_savePath, CMakeInputFolder.s_blenderSaveName)
        self.m_pneumoSavePath = os.path.join(self.m_savePath, CMakeInputFolder.s_pneumoSaveName)

        if os.path.exists(self.m_dicomPath) == False :
            os.makedirs(self.m_dicomPath)
        if os.path.exists(self.m_maskPath) == False :
            os.makedirs(self.m_maskPath)
        if os.path.exists(self.m_blenderSavePath) == False :
            os.makedirs(self.m_blenderSavePath)
        if os.path.exists(self.m_pneumoSavePath) == False :
            os.makedirs(self.m_pneumoSavePath)

        # dicom unzip
        dicomFullPath = os.path.join(self.m_zipPath, self.sZip_Dicom)
        CFileOper.unzip_file(self.m_dicomPath, dicomFullPath)

        files = os.listdir(self.m_zipPath)
        self.m_listPhaseZip = [
            file for file in files 
            if file.endswith(".zip") and file != CMakeInputFolder.sZip_Dicom
        ]
        if len(self.m_listPhaseZip) == 0 :
            print(self.TAG, "ERROR - not found zip files.")
            
            if os.path.exists(self.m_blenderSavePath) == True:
                self.Ready = True
            return False
        
        self.m_listPhaseZipName = [zipFile.split('.')[0] for zipFile in self.m_listPhaseZip]

        # create mask phase folder & unzip 
        for phase in self.m_listPhaseZipName :
            tmpTargetPath = os.path.join(self.m_zipPath, phase)
            targetPath = os.path.join(self.m_maskPath, phase)
            zipFullPath = os.path.join(self.m_zipPath, f"{phase}.zip")

            CFileOper.unzip_file(tmpTargetPath, zipFullPath)    # 임시로 zip을 푼다 
            CFileOper.copy_folder_ext(targetPath, tmpTargetPath, ("nii.gz"))    # 재귀적으로 돌면서 nifti 파일만 maskPath에 복사한다. 
            CFileOper.remove_folder(tmpTargetPath)              # 임시 폴더를 삭제한다. 
            
            # print("!!!!!!!!!!!!!!targetPath", file=sys.__stdout__, flush=True)
            # print(targetPath, file=sys.__stdout__, flush=True)
            
            # for maskName in os.listdir(targetPath):
            #     full_path = os.path.join(targetPath, maskName)

            #     # 파일만 대상 (폴더 제외)
            #     if os.path.isfile(full_path):
            #         name_no_ext = os.path.splitext(maskName)[0]
            #         self.OptionInfo.set_recon_phase(name_no_ext, phase)
                    
            #         print(name_no_ext, file=sys.__stdout__, flush=True)
            #         print(phase, file=sys.__stdout__, flush=True)
            
        # make mask zip
        # zipFullPath = CFileOper.zip_folder(self.m_dataRootPath, self.m_maskPath)
        zipName = os.path.join(self.m_dataRootPath, f"{self.m_patientID}_mask_miop")
        shutil.make_archive(zipName, 'zip', self.m_maskPath)

        self.Ready = True
        return True
    
    def copy_mask(self, copiedMaskPath : str) :
        phaseList = self.m_listPhaseZipName
        for phase in phaseList :
            if phase == "" :
                continue
            originMaskPhasePath = os.path.join(self.m_maskPath, phase)
            if os.path.exists(originMaskPhasePath) == False :
                continue

            CFileOper.copy_folder_ext(copiedMaskPath, originMaskPhasePath, ("nii.gz"))
    def copy_target_mask(self, targetMaskFolder : str, individualPhase : str, copiedMaskPath : str) :
        '''
        - input
            - targetMaskFolder : individual mask folder
            - individualPhase : individual phase
            - copiedMaskPaht : outTemp folder
        '''
        if os.path.exists(copiedMaskPath) == False :
            os.makedirs(copiedMaskPath, exist_ok=True)
        
        inputFolder = Path(targetMaskFolder)
        maskList = [
            f.name
            for f in inputFolder.iterdir()
            if f.is_file() and f.name.lower().endswith(".nii.gz")
        ]

        # 해당 mask file이 기존 phase 폴더에 있다면 지운다. 
        phaseList = self.m_listPhaseZipName
        for phase in phaseList :
            if phase == "" :
                continue

            originMaskPhasePath = os.path.join(self.m_maskPath, phase)
            if os.path.exists(originMaskPhasePath) == False :
                continue

            for maskFile in maskList :
                checkOriginMaskFullPath = os.path.join(originMaskPhasePath, maskFile)
                if os.path.exists(checkOriginMaskFullPath) == True :
                    os.remove(checkOriginMaskFullPath)
            
        # 해당 mask folder를 originMaskPhasePath로 복사
        originMaskPhasePath = os.path.join(self.m_maskPath, individualPhase)
        if os.path.exists(originMaskPhasePath) == False :
            os.makedirs(originMaskPhasePath, exist_ok=True)
        # 해당 mask folder를 copiedMaskPath와 dataRoot Mask Path로 복사 
        for maskFile in maskList :
            maskFullPath = os.path.join(targetMaskFolder, maskFile)
            shutil.copy(maskFullPath, copiedMaskPath)
            shutil.copy(maskFullPath, originMaskPhasePath)

        # make mask zip 
        # zipFullPath = CFileOper.zip_folder(self.m_dataRootPath, self.m_maskPath)
        zipName = os.path.join(self.m_dataRootPath, f"{self.m_patientID}_mask_miop")
        shutil.make_archive(zipName, 'zip', self.m_maskPath)

        # refresh origin zip 
        listFolderName = [folderName for folderName in os.listdir(self.m_maskPath) if os.path.isdir(os.path.join(self.m_maskPath, folderName))]
        for folderName in listFolderName :
            if folderName not in self.m_listPhaseZipName : 
                continue
            zipName = os.path.join(self.m_zipPath, f"{folderName}")
            folderPath = os.path.join(self.m_maskPath, folderName)
            shutil.make_archive(zipName, 'zip', folderPath)

    

    @property
    def Ready(self) -> bool :
        return self.m_bReady
    @Ready.setter
    def Ready(self, bReady : bool) :
        self.m_bReady = bReady
    @property
    def ZipPath(self) :
        return self.m_zipPath
    @ZipPath.setter
    def ZipPath(self, zipPath : str) :
        self.m_zipPath = zipPath
    @property
    def PatientID(self) -> str :
        return self.m_patientID
    @property
    def DataRootPath(self) -> str :
        return self.m_dataRootPath
    @property
    def MaskPath(self) -> str :
        return self.m_maskPath
    @property
    def BlenderSavePath(self) -> str :
        return self.m_blenderSavePath
    @property
    def OptionInfo(self):
        return self.m_optionInfo
    @OptionInfo.setter
    def OptionInfo(self, optionInfo):
        self.m_optionInfo = optionInfo


if __name__ == "__main__" :
    pass
    # test = CMakeInputFolder()
    # test.ZipPath = "D:\\jys\\StomachKidney_newfolder\\zippath" #01014urk_4input"
    # test.FolderMode = test.eMode_Kidney #test.eMode_Kidney  #test.eMode_Stomach
    # test.process()

    

    