param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,

    [Parameter(Mandatory = $true)]
    [string]$BucketName,

    [string]$Region = "us-central1",
    [string]$Zone = "us-central1-a",
    [string]$InstanceName = "mlops-serve",
    [switch]$ProvisionVm,
    [switch]$CreateServiceAccountKey
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    throw "Google Cloud CLI is not installed or is not available on PATH."
}

$ServiceAccountName = "mlops-lab-sa"
$ServiceAccountEmail = "$ServiceAccountName@$ProjectId.iam.gserviceaccount.com"

gcloud config set project $ProjectId
gcloud services enable storage.googleapis.com compute.googleapis.com --project $ProjectId

$ExistingBucket = gcloud storage buckets list `
    --project $ProjectId `
    --filter "name=$BucketName" `
    --format "value(name)"
if (-not $ExistingBucket) {
    gcloud storage buckets create "gs://$BucketName" `
        --project $ProjectId `
        --location $Region `
        --uniform-bucket-level-access
}

$ExistingServiceAccount = gcloud iam service-accounts list `
    --project $ProjectId `
    --filter "email=$ServiceAccountEmail" `
    --format "value(email)"
if (-not $ExistingServiceAccount) {
    gcloud iam service-accounts create $ServiceAccountName `
        --display-name "MLOps Lab Service Account" `
        --project $ProjectId
}

gcloud storage buckets add-iam-policy-binding "gs://$BucketName" `
    --member "serviceAccount:$ServiceAccountEmail" `
    --role roles/storage.objectAdmin `
    --project $ProjectId

if ($CreateServiceAccountKey) {
    $KeyPath = Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..")).Path "sa-key.json"
    if (-not (Test-Path -LiteralPath $KeyPath)) {
        gcloud iam service-accounts keys create $KeyPath `
            --iam-account $ServiceAccountEmail `
            --project $ProjectId
        if ($LASTEXITCODE -ne 0) {
            if ((Test-Path -LiteralPath $KeyPath) -and ((Get-Item $KeyPath).Length -eq 0)) {
                Remove-Item -LiteralPath $KeyPath
            }
            throw "Service-account key creation failed. Use Workload Identity Federation instead."
        }
    }
    Write-Host "Created $KeyPath. It is ignored by Git; never commit it."
}

if ($ProvisionVm) {
    $ExistingInstance = gcloud compute instances list `
        --project $ProjectId `
        --filter "name=$InstanceName AND zone:($Zone)" `
        --format "value(name)"
    if (-not $ExistingInstance) {
        gcloud compute instances create $InstanceName `
            --zone $Zone `
            --machine-type e2-small `
            --image-family ubuntu-2204-lts `
            --image-project ubuntu-os-cloud `
            --service-account $ServiceAccountEmail `
            --scopes https://www.googleapis.com/auth/cloud-platform `
            --tags mlops-serve `
            --project $ProjectId
    }

    $ExistingFirewallRule = gcloud compute firewall-rules list `
        --project $ProjectId `
        --filter "name=allow-mlops-serve" `
        --format "value(name)"
    if (-not $ExistingFirewallRule) {
        gcloud compute firewall-rules create allow-mlops-serve `
            --allow tcp:8000 `
            --target-tags mlops-serve `
            --project $ProjectId
    }

    $VmIp = gcloud compute instances describe $InstanceName `
        --zone $Zone `
        --project $ProjectId `
        --format "value(networkInterfaces[0].accessConfigs[0].natIP)"
    Write-Host "VM public IP: $VmIp"
}

Write-Host "GCP bootstrap complete."
Write-Host "Service account: $ServiceAccountEmail"
Write-Host "Bucket: gs://$BucketName"
