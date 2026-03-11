$scriptDir = $PSScriptRoot
$scripts = @(
    "build_msvc2005.cmd",
    "build_msvc2022.cmd",
    "build_msvc2026.cmd",
    "build_mingw.cmd",
    "build_cygwin.cmd",
    "build_docker_ubuntu.cmd",
    "build_docker_alpine.cmd"
)

$jobs = @()
$cwd = (Get-Location).Path

foreach ($script in $scripts) {
    $scriptPath = Join-Path $scriptDir $script
    Write-Host "Starting job for $script..."
    $jobs += Start-Job -ScriptBlock {
        param($path, $pwd)
        Set-Location $pwd
        & cmd.exe /c $path
    } -ArgumentList $scriptPath, $cwd
}

Wait-Job -Job $jobs
Receive-Job -Job $jobs
