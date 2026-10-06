"""Arcade 3.3.3 packaging: VERSION must be a file, not a directory.

Override the bundled hook's VERSION destination; include only system resources
required by this demo, not Arcade's sample media or macOS codec libraries.
"""
from PyInstaller.utils.hooks import collect_data_files

hiddenimports = ["arcade.gl.backends.opengl.provider", "arcade.gl.backends.opengl"]
datas = collect_data_files("arcade", includes=["resources/system/**/*", "VERSION"])
binaries = []
