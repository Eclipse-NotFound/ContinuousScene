$ErrorActionPreference='Stop'
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$sceneJava='D:/Program Files/Adobe Animate 2024/jre/bin/java.exe'
$scenePython='C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$sceneFlex=Join-Path $sceneRoot 'mods/Sandevistan/build/tools/flexsdk'
$sceneLock=[IO.File]::Open((Join-Path $PSScriptRoot 'runtime/session.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {
    & $scenePython (Join-Path $PSScriptRoot 'issues_rv_profile.py')
    if($LASTEXITCODE -ne 0){throw 'RV profiler preparation failed'}
    & (Join-Path $PSScriptRoot 'build.ps1') -ProbeOnly
    $sceneSource=Join-Path $PSScriptRoot 'generated/issues-rv-profile'
    & $sceneJava '-Dfile.encoding=UTF-8' '-jar' (Join-Path $sceneFlex 'lib/mxmlc.jar') ('+flexlib='+(Join-Path $sceneFlex 'frameworks')) '+configname=air' ('-load-config='+(Join-Path $PSScriptRoot 'generated/compiler.xml')) ('-source-path='+$sceneSource) ('-external-library-path+='+(Join-Path $sceneRoot 'mods/RealisticVision/build/GameStubs.swc')) ('-output='+(Join-Path $PSScriptRoot 'runtime/mods/RealisticVision/release/RealisticVisionMod.swf')) (Join-Path $sceneSource 'RealisticVisionMod.as')
    if($LASTEXITCODE -ne 0){throw 'RV profiler compilation failed'}
}finally{$sceneLock.Dispose()}
