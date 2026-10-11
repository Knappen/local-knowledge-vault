$ErrorActionPreference = 'Stop'
$project = $PSScriptRoot
$python = Join-Path $project '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $python)) { throw 'Run .\setup.ps1 first.' }
$env:AIWS_KNOWLEDGE_ROOT = if ($env:AIWS_KNOWLEDGE_ROOT) { $env:AIWS_KNOWLEDGE_ROOT } else { Join-Path $project 'data' }
$env:HF_HOME = if ($env:HF_HOME) { $env:HF_HOME } else { Join-Path $project '.cache\huggingface' }
$env:AIWS_FASTEMBED_CACHE = if ($env:AIWS_FASTEMBED_CACHE) { $env:AIWS_FASTEMBED_CACHE } else { Join-Path $project '.cache\fastembed' }
$env:AIWS_ACTIVE_BACKEND = if ($env:AIWS_ACTIVE_BACKEND) { $env:AIWS_ACTIVE_BACKEND } else { 'http://127.0.0.1:11434' }
$env:AIWS_PROFILE_ROUTER = if ($env:AIWS_PROFILE_ROUTER) { $env:AIWS_PROFILE_ROUTER } else { $env:AIWS_ACTIVE_BACKEND }
$env:AIWS_RAG_PYTHON = $python
& $python (Join-Path $project 'portable_server.py')
