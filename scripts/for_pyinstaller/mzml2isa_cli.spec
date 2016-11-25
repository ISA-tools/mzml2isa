# -*- mode: python -*-

block_cipher = None


a = Analysis(['mzml2isa_cli.py'],
             pathex=['..\\mzml2isa'],
             binaries=None,
             datas= [ ('..\\..\\mzml2isa\\templates\\a_imzML.txt', 'mzml2isa\\templates' ),
		      ('..\\..\\mzml2isa\\templates\\a_mzML.txt', 'mzml2isa\\templates' ),
		      ('..\\..\\mzml2isa\\templates\\i_imzML.txt', 'mzml2isa\\templates' ),
                      ('..\\..\\mzml2isa\\templates\\i_mzML.txt', 'mzml2isa\\templates' ),
                      ('..\\..\\mzml2isa\\templates\\s_imzML.txt', 'mzml2isa\\templates' ),
                      ('..\\..\\mzml2isa\\templates\\s_mzML.txt', 'mzml2isa\\templates' ),
                      ('..\\..\\mzml2isa\\ontologies\\imagingMS.obo', 'mzml2isa\\ontologies' ),
		      ('..\\..\\mzml2isa\\ontologies\\psi-ms.obo', 'mzml2isa\\ontologies' )],
             hiddenimports=[],
             hookspath=['.'],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='mzml2isa_cli',
          debug=False,
          strip=False,
          upx=True,
          console=True )
