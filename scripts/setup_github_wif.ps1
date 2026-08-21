param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,

    [Parameter(Mandatory = $true)]
    [string]$GitHubOwner,

    [Parameter(Mandatory = $true)]
    [string]$GitHubRepository,

    [string]$ServiceAccountName = "mlops-lab-sa",
    [string]$PoolId = "github-actions-pool",
    [string]$ProviderId = "github-actions-provider"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    throw "Google Cloud CLI is not installed or is not available on PATH."
}

$ProjectNumber = gcloud projects describe $ProjectId --format "value(projectNumber)"
$ServiceAccountEmail = "$ServiceAccountName@$ProjectId.iam.gserviceaccount.com"
$Repository = "$GitHubOwner/$GitHubRepository"

gcloud services enable iamcredentials.googleapis.com sts.googleapis.com --project $ProjectId

$ExistingPool = gcloud iam workload-identity-pools list `
    --location global `
    --project $ProjectId `
    --filter "name:$PoolId" `
    --format "value(name)"
if (-not $ExistingPool) {
    gcloud iam workload-identity-pools create $PoolId `
        --location global `
        --project $ProjectId `
        --display-name "GitHub Actions Pool"
}

$ExistingProvider = gcloud iam workload-identity-pools providers list `
    --workload-identity-pool $PoolId `
    --location global `
    --project $ProjectId `
    --filter "name:$ProviderId" `
    --format "value(name)"
if (-not $ExistingProvider) {
    gcloud iam workload-identity-pools providers create-oidc $ProviderId `
        --workload-identity-pool $PoolId `
        --location global `
        --project $ProjectId `
        --display-name "GitHub Actions Provider" `
        --issuer-uri "https://token.actions.githubusercontent.com" `
        --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" `
        --attribute-condition "assertion.repository=='$Repository'"
}

$Principal = "principalSet://iam.googleapis.com/projects/$ProjectNumber/locations/global/workloadIdentityPools/$PoolId/attribute.repository/$Repository"
gcloud iam service-accounts add-iam-policy-binding $ServiceAccountEmail `
    --project $ProjectId `
    --role roles/iam.workloadIdentityUser `
    --member $Principal

$ProviderResource = "projects/$ProjectNumber/locations/global/workloadIdentityPools/$PoolId/providers/$ProviderId"
Write-Host "Workload Identity Federation configured."
Write-Host "GCP_WORKLOAD_IDENTITY_PROVIDER=$ProviderResource"
Write-Host "GCP_SERVICE_ACCOUNT=$ServiceAccountEmail"
