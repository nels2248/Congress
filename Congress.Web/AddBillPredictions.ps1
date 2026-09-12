$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Adding Congress Bill Prediction Pages" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Make sure we are running from the project directory.
$projectRoot = Get-Location

if (-not (Test-Path ".\Congress.Web.csproj")) {
    Write-Host "ERROR: Congress.Web.csproj was not found." -ForegroundColor Red
    Write-Host "Run this script from the Congress.Web project folder." -ForegroundColor Yellow
    exit 1
}

# ---------------------------------------------------------------------------
# IMPORTANT:
# We intentionally DO NOT modify:
#   Pages\Index.cshtml
#   Pages\Index.cshtml.cs
#   Data\CongressDBContext.cs
#
# CongressDBContext.cs is already configured correctly.
# ---------------------------------------------------------------------------

$modelsPath = ".\Pages\Models"
$billsPath  = ".\Pages\Bills"

New-Item -ItemType Directory -Force -Path $modelsPath | Out-Null
New-Item -ItemType Directory -Force -Path $billsPath | Out-Null

# ---------------------------------------------------------------------------
# Helper function
# ---------------------------------------------------------------------------

function Write-NewFile {
    param(
        [string]$Path,
        [string]$Content
    )

    if (Test-Path $Path) {
        Write-Host "SKIPPING existing file: $Path" -ForegroundColor Yellow
        return
    }

    Set-Content -Path $Path -Value $Content -Encoding UTF8
    Write-Host "Created: $Path" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# BillPrediction.cs
# ---------------------------------------------------------------------------

Write-NewFile ".\Pages\Models\BillPrediction.cs" @'
namespace Congress.Web.Models;

public class BillPrediction
{
    public long PredictionId { get; set; }
    public int FileId { get; set; }
    public string? Title { get; set; }
    public bool? ActualBecameLaw { get; set; }
    public double? PredictedProbability { get; set; }
    public string? PredictedOutcome { get; set; }
    public long? PredictionRunId { get; set; }
    public DateTime RunAt { get; set; }
}
'@

# ---------------------------------------------------------------------------
# BillPassageReason.cs
# ---------------------------------------------------------------------------

Write-NewFile ".\Pages\Models\BillPassageReason.cs" @'
namespace Congress.Web.Models;

public class BillPassageReason
{
    public long ReasonId { get; set; }
    public int FileId { get; set; }
    public string FeatureName { get; set; } = "";
    public double? Contribution { get; set; }
    public string Direction { get; set; } = "";
    public int ReasonRank { get; set; }
    public long? PredictionRunId { get; set; }
    public DateTime RunAt { get; set; }
}
'@

# ---------------------------------------------------------------------------
# Bills/Index.cshtml
# ---------------------------------------------------------------------------

Write-NewFile ".\Pages\Bills\Index.cshtml" @'
@page
@model Congress.Web.Pages.Bills.IndexModel

@{
    ViewData["Title"] = "Bill Predictions";
}

<h1>Bill Passage Predictions</h1>

<p class="text-muted">
    Machine-learning predictions generated from the latest congressional data.
</p>

@if (Model.Bills.Count == 0)
{
    <div class="alert alert-info">
        No bill predictions are currently available.
    </div>
}
else
{
    <p>
        <strong>@Model.Bills.Count.ToString("N0") bills</strong>
        with current model predictions.
    </p>

    <div class="table-responsive">
        <table class="table table-striped table-hover align-middle">
            <thead>
                <tr>
                    <th>Bill</th>
                    <th>Title</th>
                    <th>Predicted Likelihood</th>
                    <th>Model Category</th>
                    <th>Run At</th>
                </tr>
            </thead>

            <tbody>
                @foreach (var bill in Model.Bills)
                {
                    <tr>
                        <td>
                            <a asp-page="/Bills/Details"
                               asp-route-id="@bill.FileId">
                                @bill.FileId
                            </a>
                        </td>

                        <td>
                            <a asp-page="/Bills/Details"
                               asp-route-id="@bill.FileId"
                               class="text-decoration-none">
                                @bill.Title
                            </a>
                        </td>

                        <td>
                            @if (bill.PredictedProbability.HasValue)
                            {
                                <strong>
                                    @bill.PredictedProbability.Value.ToString("P1")
                                </strong>
                            }
                        </td>

                        <td>
                            @if (bill.PredictedOutcome == "High")
                            {
                                <span class="badge bg-success">High</span>
                            }
                            else if (bill.PredictedOutcome == "Moderate")
                            {
                                <span class="badge bg-primary">Moderate</span>
                            }
                            else if (bill.PredictedOutcome == "Low")
                            {
                                <span class="badge bg-warning text-dark">Low</span>
                            }
                            else
                            {
                                <span class="badge bg-secondary">
                                    @bill.PredictedOutcome
                                </span>
                            }
                        </td>

                        <td>
                            @bill.RunAt.ToLocalTime().ToString("MM/dd/yyyy h:mm tt")
                        </td>
                    </tr>
                }
            </tbody>
        </table>
    </div>
}
'@

# ---------------------------------------------------------------------------
# Bills/Index.cshtml.cs
# ---------------------------------------------------------------------------

Write-NewFile ".\Pages\Bills\Index.cshtml.cs" @'
using Congress.Web.Data;
using Congress.Web.Models;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;

namespace Congress.Web.Pages.Bills;

public class IndexModel : PageModel
{
    private readonly CongressDbContext _db;

    public IndexModel(CongressDbContext db)
    {
        _db = db;
    }

    public List<BillPrediction> Bills { get; set; } = new();

    public async Task OnGetAsync()
    {
        Bills = await _db.BillPredictions
            .OrderByDescending(b => b.PredictedProbability)
            .ToListAsync();
    }
}
'@

# ---------------------------------------------------------------------------
# Bills/Details.cshtml
# ---------------------------------------------------------------------------

Write-NewFile ".\Pages\Bills\Details.cshtml" @'
@page
@model Congress.Web.Pages.Bills.DetailsModel

@{
    ViewData["Title"] = "Bill Prediction Details";
}

@if (Model.Bill == null)
{
    <h1>Bill Not Found</h1>

    <div class="alert alert-warning">
        The requested bill prediction could not be found.
    </div>

    <a asp-page="/Bills/Index" class="btn btn-primary">
        Back to Bill Predictions
    </a>
}
else
{
    <div class="mb-3">
        <a asp-page="/Bills/Index">&larr; Back to Bill Predictions</a>
    </div>

    <h1>@Model.Bill.Title</h1>

    <div class="card mb-4">
        <div class="card-body">
            <h5 class="card-title">Model Prediction</h5>

            <div class="row">
                <div class="col-md-4">
                    <div class="text-muted">Predicted Likelihood</div>
                    <div class="display-6">
                        @(Model.Bill.PredictedProbability?.ToString("P1") ?? "N/A")
                    </div>
                </div>

                <div class="col-md-4">
                    <div class="text-muted">Model Category</div>
                    <div class="fs-3">
                        @Model.Bill.PredictedOutcome
                    </div>
                </div>

                <div class="col-md-4">
                    <div class="text-muted">Bill File ID</div>
                    <div class="fs-3">
                        @Model.Bill.FileId
                    </div>
                </div>
            </div>

            <hr />

            <p class="text-muted mb-0">
                This is a machine-learning model output, not a statement of
                what will happen to the bill. The factors below show which
                model features contributed most to this prediction.
            </p>
        </div>
    </div>

    <h2>Top Model Factors</h2>

    @if (Model.Reasons.Count == 0)
    {
        <div class="alert alert-info">
            No explanation factors are available for this prediction.
        </div>
    }
    else
    {
        <div class="table-responsive">
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Feature</th>
                        <th>Direction</th>
                        <th>Contribution</th>
                    </tr>
                </thead>

                <tbody>
                    @foreach (var reason in Model.Reasons)
                    {
                        <tr>
                            <td>@reason.ReasonRank</td>

                            <td>
                                @reason.FeatureName
                            </td>

                            <td>
                                @if (reason.Direction == "Positive")
                                {
                                    <span class="text-success">
                                        Positive
                                    </span>
                                }
                                else
                                {
                                    <span class="text-danger">
                                        Negative
                                    </span>
                                }
                            </td>

                            <td>
                                @(reason.Contribution?.ToString("0.0000") ?? "N/A")
                            </td>
                        </tr>
                    }
                </tbody>
            </table>
        </div>
    }
}
'@

# ---------------------------------------------------------------------------
# Bills/Details.cshtml.cs
# ---------------------------------------------------------------------------

Write-NewFile ".\Pages\Bills\Details.cshtml.cs" @'
using Congress.Web.Data;
using Congress.Web.Models;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;

namespace Congress.Web.Pages.Bills;

public class DetailsModel : PageModel
{
    private readonly CongressDbContext _db;

    public DetailsModel(CongressDbContext db)
    {
        _db = db;
    }

    public BillPrediction? Bill { get; set; }

    public List<BillPassageReason> Reasons { get; set; } = new();

    public async Task<IActionResult> OnGetAsync(int id)
    {
        Bill = await _db.BillPredictions
            .FirstOrDefaultAsync(p => p.FileId == id);

        if (Bill == null)
        {
            return Page();
        }

        Reasons = await _db.BillPassageReasons
            .Where(r => r.FileId == id)
            .OrderBy(r => r.ReasonRank)
            .Take(5)
            .ToListAsync();

        return Page();
    }
}
'@

# ---------------------------------------------------------------------------
# Update navigation
# ---------------------------------------------------------------------------

$layoutPath = ".\Pages\Shared\_Layout.cshtml"

if (-not (Test-Path $layoutPath)) {
    Write-Host "ERROR: Could not find $layoutPath" -ForegroundColor Red
    exit 1
}

$layout = Get-Content $layoutPath -Raw

$navLink = @'
                        <li class="nav-item">
                            <a class="nav-link text-dark" asp-area="" asp-page="/Bills/Index">Bill Predictions</a>
                        </li>
'@

if ($layout -match 'asp-page="/Bills/Index"') {
    Write-Host "Navigation link already exists. Skipping." -ForegroundColor Yellow
}
else {
    $homeLink = @'
                        <li class="nav-item">
                            <a class="nav-link text-dark" asp-area="" asp-page="/Index">Home</a>
                        </li>
'@

    if ($layout.Contains($homeLink)) {
        $layout = $layout.Replace($homeLink, $homeLink + $navLink)
        Set-Content -Path $layoutPath -Value $layout -Encoding UTF8
        Write-Host "Added Bill Predictions navigation link." -ForegroundColor Green
    }
    else {
        Write-Host "WARNING: Could not find the Home navigation item." -ForegroundColor Yellow
        Write-Host "No changes were made to _Layout.cshtml." -ForegroundColor Yellow
    }
}

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Building project..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

dotnet build

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "BUILD FAILED." -ForegroundColor Red
    Write-Host "No further action was taken." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " SUCCESS" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Bill prediction pages have been added." -ForegroundColor Green
Write-Host ""
Write-Host "Next:"
Write-Host "  1. Run: dotnet run"
Write-Host "  2. Open: /Bills"
Write-Host "" 
