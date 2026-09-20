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

public int TotalBills { get; set; }
public int HighCount { get; set; }
public int ModerateCount { get; set; }
public int LowCount { get; set; }
public int VeryLowCount { get; set; }

public async Task OnGetAsync()
{
    // Get the latest prediction run
    var latestRunId = await _db.BillPredictions
        .MaxAsync(b => (long?)b.PredictionRunId);

    if (latestRunId == null)
    {
        return;
    }

    // Only use predictions from the latest model run
    var latestPredictions = _db.BillPredictions
        .Where(b => b.PredictionRunId == latestRunId);

    TotalBills = await latestPredictions.CountAsync();

    HighCount = await latestPredictions
        .CountAsync(b => b.PredictedOutcome == "High");

    ModerateCount = await latestPredictions
        .CountAsync(b => b.PredictedOutcome == "Moderate");

    LowCount = await latestPredictions
        .CountAsync(b => b.PredictedOutcome == "Low");

    VeryLowCount = await latestPredictions
        .CountAsync(b => b.PredictedOutcome == "Very Low");

    Bills = await latestPredictions
        .OrderByDescending(b => b.PredictedProbability)
        .Take(10)
        .ToListAsync();
} 

}
