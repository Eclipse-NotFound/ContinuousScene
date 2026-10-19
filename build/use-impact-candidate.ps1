$ErrorActionPreference='Stop'
$sceneRuntime=Join-Path $PSScriptRoot 'runtime'
$sceneLock=[IO.File]::Open((Join-Path $sceneRuntime 'session.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {
    $source=Join-Path $PSScriptRoot 'candidate-v08-impact/pfe.swf'
    $audit=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'candidate-v08-impact/pfe.audit.json') -Raw|ConvertFrom-Json
    if(-not $audit.passed -or (Get-FileHash -LiteralPath $source).Hash -ne $audit.finalHostSHA256){throw 'Unaudited impact candidate'}
    Copy-Item -LiteralPath $source -Destination (Join-Path $sceneRuntime 'pfe.swf') -Force
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'candidate-v08-impact/pfe.audit.json') -Destination (Join-Path $sceneRuntime 'renderer-audit.json') -Force
    & (Join-Path $PSScriptRoot 'build.ps1') -ProbeOnly
}finally{$sceneLock.Dispose()}
