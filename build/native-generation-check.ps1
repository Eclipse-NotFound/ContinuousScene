# Reproduce a pre-merge native error on installed 0.7 bytes, then restore v0.8.
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$runtime=Join-Path $PSScriptRoot 'runtime'
$saved=Join-Path $PSScriptRoot ('generated/generation-restore-'+(Get-Date -Format yyyyMMdd-HHmmssfff))
$files=@('pfe.swf','mods/ContinuousScene/release/ContinuousSceneMod.swf','mods/TDFC/release/TDFCMod.swf','mods/WallBlend/release/WallBlendMod.swf')
$expected=@('2A4662488BA3B690EB23ACFE4B79ACA3F0D9AE114E5E2DEE7595AF3CABFFB3EA','70C06879A2CFFE85901E5C8E19FC1715028D5C38934975E970569468737309D5','99BFBAA68229635FBAA496EF9287A94BB9EA7C65D71339CEF3FDE65F47E30275','DF9AA07265E2538E115A5F048D272B85FC1C34D00EC4BC81585CD40D96648F76')
for($i=0;$i -lt $files.Count;$i++){if((Get-FileHash (Join-Path $root $files[$i])).Hash -ne $expected[$i]){throw 'Installed native baseline changed'}}
New-Item -ItemType Directory -Path $saved|Out-Null
$lock=[IO.File]::Open((Join-Path $runtime 'session.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {foreach($path in $files){Copy-Item -LiteralPath (Join-Path $runtime $path) -Destination (Join-Path $saved (Split-Path $path -Leaf));Copy-Item -LiteralPath (Join-Path $root $path) -Destination (Join-Path $runtime $path) -Force}}
finally {$lock.Dispose()}
try {
    [IO.File]::WriteAllText((Join-Path $runtime 'generation-controls.flag'),'original native generation')
    & (Join-Path $PSScriptRoot 'test.ps1') -Issues -Progressive -DiagnosticsOnly -HighQoS -TimeoutSeconds 500 -EvidenceName 'native-generation-v07-seed4077752896'
} finally {
    Remove-Item -LiteralPath (Join-Path $runtime 'generation-controls.flag') -ErrorAction SilentlyContinue
    $lock=[IO.File]::Open((Join-Path $runtime 'session.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
    try{foreach($path in $files){Copy-Item -LiteralPath (Join-Path $saved (Split-Path $path -Leaf)) -Destination (Join-Path $runtime $path) -Force}}finally{$lock.Dispose()}
}
