# Frozen LAD diagnostic, restored in finally. Never modifies installed releases.
$ErrorActionPreference='Stop'
$runtime=Join-Path $PSScriptRoot 'runtime'
$target=Join-Path $runtime 'mods/LightAndDarkness/release/LightAndDarknessMod.swf'
$original=Join-Path $PSScriptRoot 'cache/v08-baseline/mods/LightAndDarkness/release/LightAndDarknessMod.swf'
$profile=Join-Path $PSScriptRoot 'candidate-lad-profile/LightAndDarknessMod.swf'
if((Get-FileHash $target).Hash -ne '514A7671D4DA517A31045AEAF8FFAD3089AA66705FE58D14DC339F849589A7F6' -or (Get-FileHash $original).Hash -ne (Get-FileHash $target).Hash){throw 'LAD original mismatch'}
if((Get-FileHash $profile).Hash -ne 'EFC3E253D66CF3C838BEA33281D0FB9B8A1FE31DF7F4B697C6D382E1C90DCB3F'){throw 'Profile candidate mismatch'}
$flags=@('combat-controls.flag','user-vision-controls.flag','stage5-controls.flag')
try {
    $lock=[IO.File]::Open((Join-Path $runtime 'session.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
    try {Copy-Item -LiteralPath $profile -Destination $target -Force} finally {$lock.Dispose()}
    foreach($flag in $flags){[IO.File]::WriteAllText((Join-Path $runtime $flag),'isolated LAD attribution')}
    & (Join-Path $PSScriptRoot 'test.ps1') -Issues -Progressive -DiagnosticsOnly -HighQoS -TimeoutSeconds 500 -EvidenceName 'issues-v08-lad-profile'
} finally {
    foreach($flag in $flags){Remove-Item -LiteralPath (Join-Path $runtime $flag) -ErrorAction SilentlyContinue}
    $lock=[IO.File]::Open((Join-Path $runtime 'session.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
    try {Copy-Item -LiteralPath $original -Destination $target -Force} finally {$lock.Dispose()}
}
