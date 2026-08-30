using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;
using Congress.Web.Models;
using Congress.Web.Data;

namespace Congress.Web.Pages;

public class IndexModel : PageModel
{
private readonly CongressDbContext _db;

public IndexModel(CongressDbContext db)
{
    _db = db;
}

public List<Bill> Bills { get; set; } = new();

public int TotalBills { get; set; }

public async Task OnGetAsync()
{
    TotalBills = await _db.Bills.CountAsync();

    Bills = await _db.Bills
        .OrderByDescending(b => b.LatestActionDate)
        .Take(5)
        .ToListAsync();
}
}
