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
        TotalBills = await _db.BillPredictions.CountAsync();

        HighCount = await _db.BillPredictions
            .CountAsync(b => b.PredictedOutcome == "High");

        ModerateCount = await _db.BillPredictions
            .CountAsync(b => b.PredictedOutcome == "Moderate");

        LowCount = await _db.BillPredictions
            .CountAsync(b => b.PredictedOutcome == "Low");

        VeryLowCount = await _db.BillPredictions
            .CountAsync(b => b.PredictedOutcome == "Very Low");

        Bills = await _db.BillPredictions
            .OrderByDescending(b => b.PredictedProbability)
            .Take(10)
            .ToListAsync();
    }
} 