$ErrorActionPreference='Stop'
$sceneBaseline=Join-Path $PSScriptRoot 'cache/v08-impact-baseline'
New-Item -ItemType Directory -Force -Path $sceneBaseline|Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'candidate-v08-final/pfe.swf') -Destination (Join-Path $sceneBaseline 'pfe.swf') -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'candidate-v08-final/pfe.xml') -Destination (Join-Path $sceneBaseline 'host.xml') -Force
'[]'|Set-Content -LiteralPath (Join-Path $sceneBaseline 'methods.json') -Encoding utf8
& 'C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' (Join-Path $PSScriptRoot 'renderer-audit.py') (Join-Path $PSScriptRoot 'candidate-v08-impact/pfe.swf') $sceneBaseline (Join-Path $sceneBaseline 'methods.json') (Join-Path $PSScriptRoot 'candidate-v08-impact/pfe.delta-audit.json')
if($LASTEXITCODE -ne 0){throw 'Incremental audit failed'}
