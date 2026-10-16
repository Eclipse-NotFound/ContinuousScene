$ErrorActionPreference='Stop'
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$scenePython='C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$sceneJava='D:/Program Files/Adobe Animate 2024/jre/bin/java.exe'
$sceneTools=Join-Path $sceneRoot 'mods/Sandevistan/build/tools'
& $scenePython (Join-Path $PSScriptRoot 'prepare.py') (Join-Path $sceneRoot 'pfe_before_ContinuousScene_20261014-181702.swf') '--sources-only'
if($LASTEXITCODE -ne 0){throw 'Source preparation failed'}
& (Join-Path $PSScriptRoot 'renderer-build.ps1') -SkipProbe
& (Join-Path $PSScriptRoot 'build.ps1') -DriverOnly
& (Join-Path $PSScriptRoot 'wall-candidate-build.ps1')
$sceneLock=[IO.File]::Open((Join-Path $PSScriptRoot 'runtime/session.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'candidate-v07-wall/WallBlendMod.swf') -Destination (Join-Path $PSScriptRoot 'runtime/mods/WallBlend/release/WallBlendMod.swf') -Force
    $sceneFinal=Join-Path $PSScriptRoot 'candidate-v07-final'
    New-Item -ItemType Directory -Force -Path $sceneFinal|Out-Null
    foreach($sceneFile in @('pfe.swf','mods/ContinuousScene/release/ContinuousSceneMod.swf','mods/WallBlend/release/WallBlendMod.swf')) {
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot ('runtime/'+$sceneFile)) -Destination (Join-Path $sceneFinal (Split-Path $sceneFile -Leaf)) -Force
    }
    & $sceneJava '-Xmx1400m' '-jar' (Join-Path $sceneTools 'ffdec/ffdec-cli.jar') '-swf2xml' (Join-Path $sceneFinal 'pfe.swf') (Join-Path $sceneFinal 'pfe.xml')
    if($LASTEXITCODE -ne 0){throw 'Candidate metadata export failed'}
    & $scenePython (Join-Path $PSScriptRoot 'renderer-audit.py') (Join-Path $sceneFinal 'pfe.swf')
    if($LASTEXITCODE -ne 0){throw 'Unrelated-code audit failed'}
    Copy-Item -LiteralPath (Join-Path $sceneFinal 'pfe.audit.json') -Destination (Join-Path $PSScriptRoot 'runtime/renderer-audit.json') -Force
} finally {$sceneLock.Dispose()}
