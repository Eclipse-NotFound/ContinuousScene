# Production bytes, no profiling. Each run rejects overlapping AIR instances.
$ErrorActionPreference='Stop'
$runtime=Join-Path $PSScriptRoot 'runtime'
if((Get-FileHash (Join-Path $runtime 'mods/RealisticVision/release/RealisticVisionMod.swf')).Hash -ne '76314B819151FBA6F67F6D740B21030A9EEC8359AF4C9C9DDEB83D4CAF5C46B7'){throw 'Unexpected RV input'}
if((Get-FileHash (Join-Path $runtime 'mods/LightAndDarkness/release/LightAndDarknessMod.swf')).Hash -ne '514A7671D4DA517A31045AEAF8FFAD3089AA66705FE58D14DC339F849589A7F6'){throw 'Diagnostic LAD must be restored first'}
$flags=@('combat-controls.flag','native-rooms-controls.flag','user-vision-controls.flag','stage5-controls.flag')
try {
    foreach($flag in $flags){[IO.File]::WriteAllText((Join-Path $runtime $flag),'isolated native comparison')}
    & (Join-Path $PSScriptRoot 'test.ps1') -Issues -Progressive -HighQoS -WaitForIdleSeconds 300 -TimeoutSeconds 500 -EvidenceName 'issues-v08-native-combat-rv323'
    Remove-Item -LiteralPath (Join-Path $runtime 'native-rooms-controls.flag')
    & (Join-Path $PSScriptRoot 'test.ps1') -Issues -Progressive -HighQoS -WaitForIdleSeconds 300 -TimeoutSeconds 500 -EvidenceName 'issues-v08-combat-rv323'
} finally {foreach($flag in $flags){Remove-Item -LiteralPath (Join-Path $runtime $flag) -ErrorAction SilentlyContinue}}
try {
    [IO.File]::WriteAllText((Join-Path $runtime 'user-vision-controls.flag'),'current user RV preference')
    foreach($i in 1..3){
        & (Join-Path $PSScriptRoot 'test.ps1') -Factory -Loading -LoadNative -EntryOnly -Progressive -HighQoS -WaitForIdleSeconds 300 -TimeoutSeconds 500 -EvidenceName ('loading-v08-rv323-'+$i)
    }
} finally {Remove-Item -LiteralPath (Join-Path $runtime 'user-vision-controls.flag') -ErrorAction SilentlyContinue}
