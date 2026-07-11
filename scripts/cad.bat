@echo off
REM /cad wrapper for Windows
REM Usage: /cad create tube mounting plate 4x3 inches with 1.5 inch socket

python "C:\Github\paramAItric\scripts\cad_cli.py" %*
