# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

added_files = [	("../../Algorithm/*", './Algorithm'),
                ("../../AlgUtil/*", './AlgUtil'),
                ("../../Block/*", './Block'),

                ("../VtkObj/*", './VtkObj'),
                ("../VtkUI/*", './VtkUI'),
                ("./command/*", './command'),
                ("./state/*", './state'),
                ("./state/skelEdit/*", './state/skelEdit'),

                ("./state/subTerritory/*", './state/subTerritory'),
                ("./state/project/*", './state/project'),
                ("./state/project/colon/*", './state/project/colon'),
                ("./state/project/kidney/*", './state/project/kidney'),

                ("./state/project/lung/*", './state/project/lung'),
                ("./state/project/stomachBatch/*", './state/project/stomachBatch'),
                ("./state/project/stomach/*", './state/project/stomach'),
                ("./state/project/test/*", './state/project/test'),
                ("./state/project/lung/subTerritory/*", './state/project/lung/subTerritory'),
                ("./state/project/lung/subRecon/*", './state/project/lung/subRecon'),
                ("./state/project/lung/subSkelEdit/*", './state/project/lung/subSkelEdit'),
                ("*.py", '.'),
                
		 ]
a = Analysis(
    ['processStomach.py'],
    pathex=['C:\\Users\\hutom\\Desktop\\jh_test\\CommonPipelines\\CommonPipeline_10_0509_stomach\\CommonPipeline_10_0509_stomach\\Tool\\centerline'], 
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
    name='stomach_batch_gui',
    debug=False,
    strip=False,
    upx=True,
    console=True
)

coll = COLLECT(
    exe,      
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='stomach_batch_gui'
)