$ErrorActionPreference = 'Stop'
$project = $PSScriptRoot
$python = (Get-Command python -ErrorAction Stop).Source
& $python -m venv (Join-Path $project '.venv')
$venvPython = Join-Path $project '.venv\Scripts\python.exe'
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $project 'rag-requirements.txt')
Write-Host 'Ready. Start with: .\start.ps1'
