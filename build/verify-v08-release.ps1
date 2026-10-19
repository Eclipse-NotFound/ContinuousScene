# All runtime mutations/builds must finish before starting this sequence.
param([switch]$SkipReference)
$ErrorActionPreference='Stop'
$sceneRuntime=Join-Path $PSScriptRoot 'runtime'
function Run-Issues([string]$name,[string[]]$flags,[bool]$performance=$false) {
    try {
        foreach($flag in $flags){[IO.File]::WriteAllText((Join-Path $sceneRuntime $flag),'isolated verification')}
        if($performance) {
            & (Join-Path $PSScriptRoot 'test.ps1') -Issues -Progressive -HighQoS -WaitForIdleSeconds 300 -TimeoutSeconds 500 -EvidenceName $name
        } else {
            & (Join-Path $PSScriptRoot 'test.ps1') -Issues -Progressive -DiagnosticsOnly -HighQoS -TimeoutSeconds 500 -EvidenceName $name
        }
    } finally {foreach($flag in $flags){Remove-Item -LiteralPath (Join-Path $sceneRuntime $flag) -ErrorAction SilentlyContinue}}
}
if(-not $SkipReference){Run-Issues 'issues-v08-native-combat-release' @('combat-controls.flag','native-rooms-controls.flag','user-vision-controls.flag','stage5-controls.flag') $true}
Run-Issues 'issues-v08-mechanics-release' @('mechanics-controls.flag','stage5-controls.flag')
Run-Issues 'issues-v08-wall-trim-release' @('wall-trim-controls.flag','stage5-controls.flag')
& (Join-Path $PSScriptRoot 'regression-v08.ps1')
& 'C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' (Join-Path $PSScriptRoot 'verify_factory.py') 'factory-v08-release'
if($LASTEXITCODE -ne 0){throw 'Factory pixel/content audit failed'}
