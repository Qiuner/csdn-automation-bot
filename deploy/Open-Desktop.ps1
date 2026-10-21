[CmdletBinding()]
param(
    [string]$Server = '47.254.201.254',
    [int]$LocalPort = 16088,
    [string]$KeyPath = 'D:/Code-Mi/future-maker-ops-ed25519',
    [string]$AskPass = 'D:/Code-Mi/FutureMaker-Security/OpsKeyAskPass.exe'
)
$ErrorActionPreference = 'Stop'
if ($LocalPort -lt 1024 -or $LocalPort -gt 65535) { throw 'Invalid local port.' }
foreach ($path in @($KeyPath, $AskPass, 'D:/Git/usr/bin/ssh.exe')) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing local file: $path" }
}
$physical = @(Get-NetAdapter -Physical | Where-Object Status -eq 'Up' | Select-Object -ExpandProperty ifIndex)
$route = Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' |
    Where-Object { $_.InterfaceIndex -in $physical -and $_.NextHop -ne '0.0.0.0' } |
    Sort-Object RouteMetric | Select-Object -First 1
if (-not $route) { throw 'No physical IPv4 default route.' }
$address = Get-NetIPAddress -InterfaceIndex $route.InterfaceIndex -AddressFamily IPv4 |
    Where-Object { $_.AddressState -eq 'Preferred' -and -not $_.SkipAsSource } |
    Select-Object -First 1 -ExpandProperty IPAddress
if (-not $address) { throw 'No physical IPv4 source address.' }
$saved = @{}
try {
    $settings = @{ SSH_ASKPASS = $AskPass; SSH_ASKPASS_REQUIRE = 'force'; DISPLAY = 'future-maker-local' }
    foreach ($name in $settings.Keys) {
        $saved[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        [Environment]::SetEnvironmentVariable($name, $settings[$name], 'Process')
    }
    Write-Host "Desktop tunnel: http://127.0.0.1:$LocalPort/vnc.html (keep this terminal open; Ctrl+C stops it)"
    & 'D:/Git/usr/bin/ssh.exe' -F /dev/null -4 -b $address -i $KeyPath `
        -o BatchMode=no -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes `
        -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no -o NumberOfPasswordPrompts=1 `
        -o ConnectTimeout=15 -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 `
        -N -L "127.0.0.1:${LocalPort}:127.0.0.1:6088" "fmops@$Server"
    if ($LASTEXITCODE -ne 0) { throw "SSH tunnel exited with code $LASTEXITCODE" }
} finally {
    foreach ($name in $saved.Keys) {
        [Environment]::SetEnvironmentVariable($name, $saved[$name], 'Process')
    }
}
