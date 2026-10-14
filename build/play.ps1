$ErrorActionPreference='Stop'
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$sceneRuntime=Join-Path $PSScriptRoot 'runtime'
$sceneDescriptor=Join-Path $sceneRuntime 'application.xml'
if(-not(Test-Path -LiteralPath (Join-Path $sceneRuntime 'mods/ContinuousSceneProbe/release/ContinuousSceneProbe.swf'))) {
    throw 'Build the isolated scene first with build/build.ps1.'
}
[xml]$sceneManifest=Get-Content -LiteralPath $sceneDescriptor -Raw
if($sceneManifest.application.id -ne 'pfe-modsettings-continuous-scene') {throw 'Refusing a non-isolated AIR id'}
$sceneLock=[IO.File]::Open((Join-Path $sceneRuntime 'session.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
$sceneFlag=Join-Path $sceneRuntime 'manual.flag'
try {
    [IO.File]::WriteAllText($sceneFlag,'manual')
    Write-Output 'Loading the isolated scene (about 20 seconds). A fresh demo starts each time.'
    # This is the user-invoked interactive launcher; the driver shows its AIR window.
    $sceneProcess=Start-Process -FilePath (Join-Path $sceneRoot 'adl64.exe') -PassThru `
        -ArgumentList @('-runtime',('"'+(Join-Path $sceneRoot 'runtimes/air/win64')+'"'),('"'+$sceneDescriptor+'"'))
    $sceneProcess.WaitForExit()
    if($sceneProcess.ExitCode -ne 0) {throw ('Scene exited with code '+$sceneProcess.ExitCode)}
}
finally {
    Remove-Item -LiteralPath $sceneFlag -ErrorAction SilentlyContinue
    $sceneLock.Dispose()
}
