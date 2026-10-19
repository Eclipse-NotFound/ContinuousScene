# Sequential functional coverage on the already-frozen isolated runtime.
$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'test.ps1') -NativeMap -Progressive -HighQoS -TimeoutSeconds 500 -EvidenceName 'native-v08-release-r2'
& (Join-Path $PSScriptRoot 'test.ps1') -Factory -HighQoS -TimeoutSeconds 500 -EvidenceName 'factory-v08-release'
& (Join-Path $PSScriptRoot 'test.ps1') -Factory -Experience -HighQoS -TimeoutSeconds 500 -EvidenceName 'experience-v08-release'
& (Join-Path $PSScriptRoot 'test.ps1') -Factory -Loading -LoadNative -Progressive -DiagnosticsOnly -HighQoS -TimeoutSeconds 500 -EvidenceName 'upcoming-v08-release'
