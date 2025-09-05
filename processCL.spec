# -*- mode: python ; coding: utf-8 -*-
# virtual env :  "conda activate venvpy38"

block_cipher = None

added_files = [	("./Algorithm/*", './Algorithm'),
                ("./AlgUtil/*", './AlgUtil'),
                ("./Block/*", './Block')
		 ]
		
a = Analysis(
    ['processCL.py'],
    pathex=['C:\\Users\\hutom\\Desktop\\jh_test\\jh_algorithm\\COMMONPIPELINE_LIVER\\latest\\liverBatch'],    
    
    binaries=[],
    datas=added_files,
    hiddenimports=['scipy.spatial', 'open3d', 'vtk', 'pyquaternion', 'networkx', 
        'vtkmodules','vtkmodules.all','vtkmodules.qt.QVTKRenderWindowInteractor','vtkmodules.util','vtkmodules.util.numpy_support', 
        'vmtk.pypescript', 'vmtk.pypebatch', 'vtkmodules.numpy_interface', 'vtkmodules.numpy_interface.dataset_adapter'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5'],
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
    name='processCL',
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
               name='processCL'
)
