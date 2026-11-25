using Congress.Web.Data;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using static Congress.Web.Data.SqlHelper;

namespace Congress.Web.Pages.Cosponsorship;

/// <summary>
/// Port of the Fabric "Co Sponsorship" page: for each co-sponsor, how many
/// bills they co-sponsored, split by the party of the bill's sponsor.
/// </summary>
public class IndexModel : PageModel
{
    private readonly SqlHelper _sql;

    public IndexModel(SqlHelper sql) => _sql = sql;

    public const int MaxRows = 150;

    [BindProperty(SupportsGet = true)] public string? Party { get; set; }     // sponsor party
    [BindProperty(SupportsGet = true)] public string? State { get; set; }     // sponsor state
    [BindProperty(SupportsGet = true)] public string? Sponsor { get; set; }   // sponsor BioguideId
    [BindProperty(SupportsGet = true)] public string? Search { get; set; }    // co-sponsor name contains

    public List<string> Parties { get; set; } = new();
    public List<string> States { get; set; } = new();
    public List<(string Id, string Name)> Sponsors { get; set; } = new();

    public List<string> SponsorParties { get; set; } = new();
    public List<CosponsorRow> Rows { get; set; } = new();
    public int TotalRows { get; set; }
    public int TotalCosponsorships { get; set; }
    public int CrossParty { get; set; }

    public class CosponsorRow
    {
        public string BioguideId { get; set; } = "";
        public string FullName { get; set; } = "";
        public string Party { get; set; } = "";
        public string State { get; set; } = "";
        public Dictionary<string, int> BySponsorParty { get; } = new();
        public int Total => BySponsorParty.Values.Sum();
    }

    public async Task OnGetAsync()
    {
        Parties = await _sql.QueryAsync(
            "SELECT DISTINCT Party FROM Silver.Sponsors WHERE Party IS NOT NULL ORDER BY Party",
            r => Str(r, "Party"));

        States = await _sql.QueryAsync(
            "SELECT DISTINCT State FROM Silver.Sponsors WHERE State IS NOT NULL ORDER BY State",
            r => Str(r, "State"));

        Sponsors = await _sql.QueryAsync(@"
            SELECT BioguideId, MAX(FullName) AS FullName
            FROM Silver.Sponsors
            WHERE BioguideId IS NOT NULL
              AND (@party IS NULL OR Party = @party)
              AND (@state IS NULL OR State = @state)
            GROUP BY BioguideId
            ORDER BY MAX(LastName), MAX(FirstName);",
            r => (Id: Str(r, "BioguideId"), Name: Str(r, "FullName")),
            P("@party", Party), P("@state", State));

        // One row per (co-sponsor, sponsor party) — pivoted into columns below
        var cells = await _sql.QueryAsync(@"
            SELECT
                c.BioguideId,
                MAX(c.FullName)  AS FullName,
                MAX(c.Party)     AS CoParty,
                MAX(c.State)     AS CoState,
                ISNULL(s.Party, '?') AS SponsorParty,
                COUNT(*)         AS Bills
            FROM Silver.Cosponsors c
            INNER JOIN Silver.Sponsors s
                ON s.Type = c.Type
               AND s.BillNumber = c.BillNumber
            WHERE (@party   IS NULL OR s.Party = @party)
              AND (@state   IS NULL OR s.State = @state)
              AND (@sponsor IS NULL OR s.BioguideId = @sponsor)
              AND (@search  IS NULL OR c.FullName LIKE '%' + @search + '%')
            GROUP BY c.BioguideId, ISNULL(s.Party, '?');",
            r => (Id: Str(r, "BioguideId"), Name: Str(r, "FullName"),
                  CoParty: Str(r, "CoParty"), CoState: Str(r, "CoState"),
                  SponsorParty: Str(r, "SponsorParty"), Bills: Int(r, "Bills")),
            P("@party", Party), P("@state", State), P("@sponsor", Sponsor), P("@search", Search));

        var byPerson = new Dictionary<string, CosponsorRow>();
        foreach (var c in cells)
        {
            if (!byPerson.TryGetValue(c.Id, out var row))
            {
                row = new CosponsorRow
                {
                    BioguideId = c.Id, FullName = c.Name, Party = c.CoParty, State = c.CoState
                };
                byPerson[c.Id] = row;
            }
            row.BySponsorParty[c.SponsorParty] = c.Bills;

            TotalCosponsorships += c.Bills;
            if (c.CoParty != c.SponsorParty) CrossParty += c.Bills;
        }

        SponsorParties = cells
            .GroupBy(c => c.SponsorParty)
            .OrderByDescending(g => g.Sum(x => x.Bills))
            .Select(g => g.Key)
            .ToList();

        TotalRows = byPerson.Count;
        Rows = byPerson.Values
            .OrderByDescending(r => r.Total)
            .ThenBy(r => r.FullName)
            .Take(MaxRows)
            .ToList();
    }

    public double CrossPartyPct =>
        TotalCosponsorships == 0 ? 0 : (double)CrossParty / TotalCosponsorships;
}
