# Build a downloadable Atticus.exe for Windows.
# Run from the repo root in PowerShell:
#   powershell -ExecutionPolicy Bypass -File scripts\build_windows_app.ps1

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "Installing build dependencies..."
python -m pip install -e ".[api,desktop]"
python -m pip install "pyinstaller>=6.3"

Write-Host "Building Atticus.exe..."
python -m PyInstaller --noconfirm --clean atticus.spec

$exe = Join-Path (Get-Location) "dist\Atticus.exe"
if (-not (Test-Path $exe)) {
  throw "Build failed: $exe not found"
}

Write-Host ""
Write-Host "Downloadable app ready:"
Write-Host "  $exe"
Write-Host ""
Write-Host "Double-click Atticus.exe to open The Listener."
Write-Host "Set OPENAI_API_KEY / ATTICUS_APPROVAL_TOKEN in your user environment or a .env beside the exe."
