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
