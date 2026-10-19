# Restore only this task's frozen candidate after isolated timing instrumentation.
$ErrorActionPreference='Stop'
$sceneRuntime=Join-Path $PSScriptRoot 'runtime'
$sceneLock=[IO.File]::Open((Join-Path $sceneRuntime 'session.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {
    foreach($relative in @('pfe.swf','mods/ContinuousScene/release/ContinuousSceneMod.swf','mods/TDFC/release/TDFCMod.swf')) {
        $source=Join-Path $PSScriptRoot ('candidate-v08-final/'+(Split-Path $relative -Leaf))
        Copy-Item -LiteralPath $source -Destination (Join-Path $sceneRuntime $relative) -Force
        if((Get-FileHash -LiteralPath $source).Hash -ne (Get-FileHash -LiteralPath (Join-Path $sceneRuntime $relative)).Hash){throw 'Runtime candidate copy mismatch'}
    }
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'candidate-v08-final/pfe.audit.json') -Destination (Join-Path $sceneRuntime 'renderer-audit.json') -Force
}finally{$sceneLock.Dispose()}
