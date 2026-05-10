# Beep.AI.Code installer for Windows
# Usage: irm https://raw.githubusercontent.com/The-Tech-Idea/Beep.AI.Code/master/scripts/install.ps1 | iex
[CmdletBinding()]
param(
    [string]$InstallDir = ""
)
$ErrorActionPreference = "Stop"

$Repo    = "The-Tech-Idea/Beep.AI.Code"
$Binary  = "beep.exe"

function Write-Info  { param($Msg) Write-Host "[beep] $Msg" -ForegroundColor Cyan }
function Write-Ok    { param($Msg) Write-Host "[beep] $Msg" -ForegroundColor Green }
function Write-Err   { param($Msg) Write-Host "[beep] $Msg" -ForegroundColor Red }

# Architecture
$Arch = switch ($env:PROCESSOR_ARCHITECTURE) {
    "AMD64" { "x86_64" }
    "ARM64" { "aarch64" }
    default { Write-Err "Unsupported architecture: $env:PROCESSOR_ARCHITECTURE"; exit 1 }
}

# Resolve install directory
if (-not $InstallDir) {
    $InstallDir = "$env:LOCALAPPDATA\beep\bin"
}
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

# Fetch latest version
Write-Info "Fetching latest release..."
$ApiUrl  = "https://api.github.com/repos/$Repo/releases/latest"
$Headers = @{ "User-Agent" = "beep-install" }
$Release = Invoke-RestMethod -Uri $ApiUrl -Headers $Headers
$Version = $Release.tag_name

if (-not $Version) {
    Write-Err "Could not determine the latest release version."
    exit 1
}

$AssetName = "beep-windows-$Arch.exe"
$DownloadUrl = "https://github.com/$Repo/releases/download/$Version/$AssetName"
$Destination = Join-Path $InstallDir $Binary

Write-Info "Downloading $AssetName $Version..."
Invoke-WebRequest -Uri $DownloadUrl -OutFile $Destination -UseBasicParsing

# Smoke-test
$TestOutput = & $Destination --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Err "Downloaded binary failed a smoke-test. Please report this at https://github.com/$Repo/issues"
    Remove-Item $Destination -Force
    exit 1
}

Write-Ok "Installed beep $Version to $Destination"

# Add to PATH for current user if not already present
$UserPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
if ($UserPath -notlike "*$InstallDir*") {
    $NewPath = "$InstallDir;$UserPath"
    [System.Environment]::SetEnvironmentVariable("PATH", $NewPath, "User")
    Write-Info "Added $InstallDir to your user PATH."
    Write-Info "Restart your terminal (or run: `$env:PATH = '$InstallDir;' + `$env:PATH) to use beep."
} else {
    Write-Info "Run: beep --version"
}
