$ErrorActionPreference='Stop'
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$sceneJava='D:/Program Files/Adobe Animate 2024/jre/bin/java.exe'
$scenePython='C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$sceneFfdec=Join-Path $sceneRoot 'mods/Sandevistan/build/tools/ffdec/ffdec-cli.jar'
$sceneLock=[IO.File]::Open((Join-Path $PSScriptRoot 'runtime/session.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {
    & $scenePython (Join-Path $PSScriptRoot 'issues-combat-profile.py')
    if($LASTEXITCODE -ne 0){throw 'Combat profiler preparation failed'}
    & $sceneJava '-Xmx1400m' '-jar' $sceneFfdec '-importScript' (Join-Path $PSScriptRoot 'candidate-v08-final/pfe.swf') (Join-Path $PSScriptRoot 'runtime/pfe.swf') (Join-Path $PSScriptRoot 'generated/issues-combat-profile')
    if($LASTEXITCODE -ne 0){throw 'Combat diagnostic host build failed'}
    & (Join-Path $PSScriptRoot 'build.ps1') -ProbeOnly
}finally{$sceneLock.Dispose()}
