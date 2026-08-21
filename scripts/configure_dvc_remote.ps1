param(
    [Parameter(Mandatory = $true)]
    [string]$BucketName,

    [string]$CredentialPath = ""
)

$ErrorActionPreference = "Stop"
$DvcExecutable = Join-Path $PSScriptRoot "..\.venv\Scripts\dvc.exe"

if (-not (Test-Path -LiteralPath $DvcExecutable)) {
    throw "DVC was not found at $DvcExecutable. Create .venv and install requirements first."
}

& $DvcExecutable remote add --force --default myremote "gs://$BucketName/dvc"

if ($CredentialPath) {
    $ResolvedCredential = (Resolve-Path -LiteralPath $CredentialPath).Path
    & $DvcExecutable remote modify --local myremote credentialpath $ResolvedCredential
    Write-Host "Credential path stored in .dvc/config.local (not tracked by Git)."
}

Write-Host "Configured DVC remote: gs://$BucketName/dvc"
Write-Host "Run '.\.venv\Scripts\dvc.exe push' after authenticating to GCP."
