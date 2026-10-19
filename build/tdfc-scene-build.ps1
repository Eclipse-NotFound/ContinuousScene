$ErrorActionPreference='Stop'
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$sceneJava='D:/Program Files/Adobe Animate 2024/jre/bin/java.exe'
$scenePython='C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$sceneFlex=Join-Path $sceneRoot 'mods/Sandevistan/build/tools/flexsdk'
$sceneLock=[IO.File]::Open((Join-Path $PSScriptRoot 'runtime/session.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {
    & $scenePython (Join-Path $PSScriptRoot 'tdfc_scene_compat.py')
    if($LASTEXITCODE -ne 0){throw 'TDFC compatibility source preparation failed'}
    $sceneSource=Join-Path $PSScriptRoot 'generated/tdfc-scene-compat'
    $sceneOutput=Join-Path $PSScriptRoot 'candidate-v08-final/TDFCMod.swf'
    & $sceneJava '-Dfile.encoding=UTF-8' '-jar' (Join-Path $sceneFlex 'lib/mxmlc.jar') ('+flexlib='+(Join-Path $sceneFlex 'frameworks')) '+configname=air' ('-load-config='+(Join-Path $PSScriptRoot 'generated/compiler.xml')) ('-source-path='+$sceneSource) ('-output='+$sceneOutput) (Join-Path $sceneSource 'TDFCMod.as')
    if($LASTEXITCODE -ne 0){throw 'TDFC compatibility compilation failed'}
    Copy-Item -LiteralPath $sceneOutput -Destination (Join-Path $PSScriptRoot 'runtime/mods/TDFC/release/TDFCMod.swf') -Force
    Get-FileHash -LiteralPath $sceneOutput
}finally{$sceneLock.Dispose()}
