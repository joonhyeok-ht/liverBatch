# -*- mode: python ; coding: utf-8 -*-
# virtual env :  "d:\jys\pyenvs\venv311\Scripts\activate"
# 월요일에 이 옵션으로 다시 해보기.
block_cipher = None

added_files = [	("../../Algorithm/*", './Algorithm'),
                ("../../Algorithm/DetectingOverlap/*", './Algorithm/DetectingOverlap'),
                ("../../Algorithm/Kidney/blockKidney.py", './Algorithm/Kidney'),
                ("../../Algorithm/Kidney/SepKidneyTumor/sepKidneyTumor2.py", './Algorithm/Kidney/SepKidneyTumor'),
                
                ("../../AlgUtil/*.py", './AlgUtil'),
                ("../../Block/*.py", './Block'),

                ("../VtkObj/*.py", './VtkObj'),
                ("../VtkUI/*.py", './VtkUI'),
                ("./command/*.py", './command'),
                ("./state/*.py", './state'),
                ("./state/skelEdit/*.py", './state/skelEdit'),

                ("./state/subTerritory/*.py", './state/subTerritory'),
                ("./state/project/*.py", './state/project'),
                ("./state/project/colon/*.py", './state/project/colon'),
                ("./state/project/kidney/*.py", './state/project/kidney'),
                ("./state/project/kidneyBatch/*.py", './state/project/kidneyBatch'),

                ("./state/project/kidneyBatch/subRecon/convertMaskPhase.py", './state/project/kidneyBatch/subRecon'),
                ("./state/project/kidneyBatch/subRecon/createDiaphragm.py", './state/project/kidneyBatch/subRecon'),
                ("./state/project/kidneyBatch/subRecon/subReconKidney.py", './state/project/kidneyBatch/subRecon'),
                                
                ("./state/project/kidneyBatch/subDetectOverlap/subDetectOverlap.py", './state/project/kidneyBatch/subDetectOverlap'),

                ("./state/project/lung/*.py", './state/project/lung'),
                ("./state/project/stomach/*.py", './state/project/stomach'),
                ("./state/project/test/*.py", './state/project/test'),
                ("./state/project/lung/subTerritory/*.py", './state/project/lung/subTerritory'),
                ("./state/project/lung/subRecon/*.py", './state/project/lung/subRecon'),
                ("./state/project/lung/subSkelEdit/*.py", './state/project/lung/subSkelEdit'),
                ("*.py", '.'),
                
		 ]
		
a = Analysis(
    ['processKidney.py'],
    pathex=['D:\\jys\\git_Solution\\Solution\\UnitTestPrev\\CommonPipeline_10_0509_lung\\Tool\centerline'], 
    binaries=[],
    datas=added_files,
    hiddenimports=['distutils.dir_util', 'meshlib.mrmeshnumpy','meshlib.mrmeshpy','PySide6.QtWidgets','PySide6.QtCore','scipy.spatial', 'open3d', 'vtk', 'pyquaternion', 'networkx', 
        'vtkmodules','vtkmodules.all','vtkmodules.qt.QVTKRenderWindowInteractor','vtkmodules.util','vtkmodules.util.numpy_support', 
        'vmtk.pypescript', 'vmtk.pypebatch', 'vtkmodules.numpy_interface', 'vtkmodules.numpy_interface.dataset_adapter'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='kidney_batch_gui',
    debug=False,
    bootloader_ignore_signals=True,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='kidney_batch_gui'
)
