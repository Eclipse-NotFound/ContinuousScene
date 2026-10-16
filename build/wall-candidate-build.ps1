$ErrorActionPreference='Stop'
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$sceneTools=Join-Path $sceneRoot 'mods/Sandevistan/build/tools'
$scenePython='C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$sceneJava='D:/Program Files/Adobe Animate 2024/jre/bin/java.exe'
& $scenePython (Join-Path $PSScriptRoot 'wallblend_compat.py')
if($LASTEXITCODE -ne 0) {throw 'Wall source preparation failed'}
$sceneWallSource=Join-Path $PSScriptRoot 'generated/wb-production'
$sceneOutput=Join-Path $PSScriptRoot 'candidate-v07-wall/WallBlendMod.swf'
New-Item -ItemType Directory -Force -Path (Split-Path $sceneOutput) | Out-Null
& $sceneJava '-Dfile.encoding=UTF-8' '-jar' (Join-Path $sceneTools 'flexsdk/lib/mxmlc.jar') ('+flexlib='+(Join-Path $sceneTools 'flexsdk/frameworks')) '+configname=air' ('-load-config='+(Join-Path $sceneWallSource 'air-config.xml')) ('-source-path='+$sceneWallSource) ('-output='+$sceneOutput) (Join-Path $sceneWallSource 'WallBlendDoc.as')
if($LASTEXITCODE -ne 0) {throw 'Wall candidate compilation failed'}
