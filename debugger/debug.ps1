[CmdletBinding()]

param (
    [Parameter(Mandatory = $true)]
    [string]$Path,
    
    [Parameter(Mandatory = $false)]
    [string]$StdOutFile = $null,

    [Parameter(Mandatory = $false)]
    [string]$StdErrFile = $null,

    [Parameter(Mandatory = $false, ValueFromRemainingArguments = $true)]
    [string[]]$params = @()
)

$StdOutFile
$StdErrFile
$Path
$params

$ScriptFolder = Split-Path -Parent $MyInvocation.MyCommand.Path
$GFlagsPath = Join-Path -Path $ScriptFolder -ChildPath 'bin\gflags.exe'
$cdbPath = Join-Path -Path $ScriptFolder -ChildPath 'bin\cdb.exe'

$ScriptFolder
$GFlagsPath
$cdbPath

$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object System.Security.Principal.WindowsPrincipal($currentUser)
$isAdmin = $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warning "This script is not running as administrator, restarting ..."
    if ($OutFile) {
        $params = @("-StdOutFile", $OutFile) + $params
    }
    if ($ErrFile) {
        $params = @("-StdErrFile", $ErrFile) + $params
    }
    Start-Process -FilePath (Get-Process -Id $PID).Path -ArgumentList (@("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $MyInvocation.MyCommand.Path, $Path) + $params) -Verb RunAs
    exit 0
}

$gflags = Start-Process -FilePath $GFlagsPath -ArgumentList "/i", $Path, "+sls" -PassThru -Wait -NoNewWindow
if ($gflags.ExitCode -ne 0) {
    Write-Error "Failed to set gflags for $Path"
    $gflags = Start-Process -FilePath $GFlagsPath -ArgumentList "/i", $Path, "-sls" -PassThru -Wait -NoNewWindow
    if ($gflags.ExitCode -ne 0) {
        Write-Error "Failed to clear gflags for $Path"
        exit 1
    }
    exit 1
}
$ArgumentList = @("-o", "-c", '"~*g; q"', $Path) + $params
if ($StdOutFile) {
    if ($StdErrFile) {
        $cdb = Start-Process -FilePath $cdbPath -ArgumentList $ArgumentList -PassThru -Wait -NoNewWindow -RedirectStandardOutput $StdOutFile -RedirectStandardError $StdErrFile
    }
    else {
        $cdb = Start-Process -FilePath $cdbPath -ArgumentList $ArgumentList -PassThru -Wait -NoNewWindow -RedirectStandardOutput $StdOutFile
    }
}
else {
    if ($StdErrFile) {
        $cdb = Start-Process -FilePath $cdbPath -ArgumentList $ArgumentList -PassThru -Wait -NoNewWindow -RedirectStandardError $StdErrFile
    }
    else {
        $cdb = Start-Process -FilePath $cdbPath -ArgumentList $ArgumentList -PassThru -Wait -NoNewWindow
    }
}
if ($cdb.ExitCode -ne 0) {
    Write-Host "Found error"
}
$gflags = Start-Process -FilePath $GFlagsPath -ArgumentList "/i", $Path, "-sls" -PassThru -Wait -NoNewWindow
if ($gflags.ExitCode -ne 0) {
    Write-Error "Failed to clear gflags for $Path"
    exit 1
}
exit 0
