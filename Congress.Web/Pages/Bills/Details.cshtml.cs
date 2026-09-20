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

public async Task<IActionResult> OnGetAsync(string type, int billNumber)
{
    // Get the most recent prediction for this bill
    Bill = await _db.BillPredictions
        .Where(p =>
            p.Type == type &&
            p.BillNumber == billNumber)
        .OrderByDescending(p => p.PredictionRunId)
        .FirstOrDefaultAsync();

    if (Bill == null)
    {
        return Page();
    }

    // Get the reasons associated with the same bill and prediction run
    Reasons = await _db.BillPassageReasons
        .Where(r =>
            r.Type == type &&
            r.BillNumber == billNumber &&
            r.PredictionRunId == Bill.PredictionRunId)
        .OrderBy(r => r.ReasonRank)
        .Take(5)
        .ToListAsync();

    return Page();
} 

}
