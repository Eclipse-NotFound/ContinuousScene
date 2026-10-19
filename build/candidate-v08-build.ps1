$ErrorActionPreference='Stop'
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$scenePython='C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$sceneJava='D:/Program Files/Adobe Animate 2024/jre/bin/java.exe'
$sceneFfdec=Join-Path $sceneRoot 'mods/Sandevistan/build/tools/ffdec/ffdec-cli.jar'
$sceneBaseline=Join-Path $PSScriptRoot 'cache/v08-baseline'
$sceneExpected='2A4662488BA3B690EB23ACFE4B79ACA3F0D9AE114E5E2DEE7595AF3CABFFB3EA'
if((Get-FileHash (Join-Path $sceneBaseline 'pfe.swf')).Hash -ne $sceneExpected){throw 'Frozen v08 baseline mismatch'}
if((Get-FileHash (Join-Path $sceneRoot 'pfe.swf')).Hash -ne $sceneExpected){throw 'Installed host changed; review before merging'}
$sceneLock=[IO.File]::Open((Join-Path $PSScriptRoot 'runtime/session.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {
    & $scenePython (Join-Path $PSScriptRoot 'prepare.py') (Join-Path $sceneRoot 'pfe_before_ContinuousScene_20261014-181702.swf') '--sources-only'
    if($LASTEXITCODE -ne 0){throw 'Source preparation failed'}
    $sceneInput=Join-Path $PSScriptRoot 'generated/v08-renderer-only'
    New-Item -ItemType Directory -Force -Path (Join-Path $sceneInput 'fe/graph')|Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'generated/scripts/fe/graph/Grafon.as') -Destination (Join-Path $sceneInput 'fe/graph/Grafon.as') -Force
    $sceneFinal=Join-Path $PSScriptRoot 'candidate-v08-final'
    New-Item -ItemType Directory -Force -Path $sceneFinal|Out-Null
    & $sceneJava '-Xmx1400m' '-jar' $sceneFfdec '-importScript' (Join-Path $sceneBaseline 'pfe.swf') (Join-Path $sceneFinal 'renderer.swf') $sceneInput
    if($LASTEXITCODE -ne 0){throw 'Renderer compilation failed'}
    & (Join-Path $PSScriptRoot 'objects-native-build.ps1') -InputHost (Join-Path $sceneFinal 'renderer.swf') -OutputHost (Join-Path $sceneFinal 'pfe.swf')
    & (Join-Path $PSScriptRoot 'build.ps1') -DriverOnly
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'runtime/mods/ContinuousScene/release/ContinuousSceneMod.swf') -Destination (Join-Path $sceneFinal 'ContinuousSceneMod.swf') -Force
    if(-not(Test-Path -LiteralPath (Join-Path $sceneBaseline 'host.xml'))) {
        & $sceneJava '-Xmx1400m' '-jar' $sceneFfdec '-swf2xml' (Join-Path $sceneBaseline 'pfe.swf') (Join-Path $sceneBaseline 'host.xml')
        if($LASTEXITCODE -ne 0){throw 'Baseline metadata export failed'}
    }
    & $sceneJava '-Xmx1400m' '-jar' $sceneFfdec '-swf2xml' (Join-Path $sceneFinal 'pfe.swf') (Join-Path $sceneFinal 'pfe.xml')
    if($LASTEXITCODE -ne 0){throw 'Candidate metadata export failed'}
    & $scenePython (Join-Path $PSScriptRoot 'renderer-audit.py') (Join-Path $sceneFinal 'pfe.swf') $sceneBaseline (Join-Path $PSScriptRoot 'generated/v08-objects/methods.json')
    if($LASTEXITCODE -ne 0){throw 'Unrelated-code audit failed'}
    Copy-Item -LiteralPath (Join-Path $sceneFinal 'pfe.swf') -Destination (Join-Path $PSScriptRoot 'runtime/pfe.swf') -Force
    Copy-Item -LiteralPath (Join-Path $sceneFinal 'pfe.audit.json') -Destination (Join-Path $PSScriptRoot 'runtime/renderer-audit.json') -Force
}finally{$sceneLock.Dispose()}
