using Congress.Web.Data;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using static Congress.Web.Data.SqlHelper;

namespace Congress.Web.Pages.Summary;

/// <summary>
/// Port of the Fabric "Summary" page: a bill-count pivot where you pick
/// the row and column groupings, filtered by sponsor party / state.
/// </summary>
public class IndexModel : PageModel
{
    private readonly SqlHelper _sql;

    public IndexModel(SqlHelper sql) => _sql = sql;

    // Whitelist: dropdown value -> column name in the BillBase CTE below.
    // (Never put user input straight into SQL — only these names.)
    public static readonly Dictionary<string, string> Groups = new()
    {
        ["PolicyArea"] = "Policy Area",
        ["Status"]     = "Status",
        ["Type"]       = "Bill Type",
        ["Chamber"]    = "Origin Chamber",
        ["Party"]      = "Sponsor Party",
        ["State"]      = "Sponsor State",
    };

    [BindProperty(SupportsGet = true)] public string RowGroup { get; set; } = "PolicyArea";
    [BindProperty(SupportsGet = true)] public string ColGroup { get; set; } = "Status";
    [BindProperty(SupportsGet = true)] public string? Party { get; set; }
    [BindProperty(SupportsGet = true)] public string? State { get; set; }

    public List<string> Parties { get; set; } = new();
    public List<string> States { get; set; } = new();

    public List<string> RowKeys { get; set; } = new();
    public List<string> ColKeys { get; set; } = new();
    public Dictionary<(string Row, string Col), int> Cells { get; set; } = new();
    public int MaxCell { get; set; }

    public int TotalBills { get; set; }
    public int Enacted { get; set; }
    public int PassedOneChamber { get; set; }
    public double AvgCosponsors { get; set; }

    // One row per bill with every groupable column. Sponsor = first sponsor on the bill.
    private static string BillBase => $@"
        WITH BillBase AS
        (
            SELECT
                b.Type,
                b.BillNumber,
                ISNULL(b.PolicyArea, '(None)')    AS PolicyArea,
                {BillStatusSql("b")}              AS Status,
                ISNULL(b.OriginChamber, '?')      AS Chamber,
                ISNULL(sp.Party, '?')             AS Party,
                ISNULL(sp.State, '?')             AS State
            FROM Silver.Bills b
            OUTER APPLY
            (
                SELECT TOP 1 s.Party, s.State
                FROM Silver.Sponsors s
                WHERE s.Type = b.Type AND s.BillNumber = b.BillNumber
                ORDER BY s.BioguideId
            ) sp
            WHERE (@party IS NULL OR sp.Party = @party)
              AND (@state IS NULL OR sp.State = @state)
        )";

    public async Task OnGetAsync()
    {
        if (!Groups.ContainsKey(RowGroup)) RowGroup = "PolicyArea";
        if (!Groups.ContainsKey(ColGroup)) ColGroup = "Status";

        Parties = await _sql.QueryAsync(
            "SELECT DISTINCT Party FROM Silver.Sponsors WHERE Party IS NOT NULL ORDER BY Party",
            r => Str(r, "Party"));

        States = await _sql.QueryAsync(
            "SELECT DISTINCT State FROM Silver.Sponsors WHERE State IS NOT NULL ORDER BY State",
            r => Str(r, "State"));

        // ---- KPI cards ----
        var kpis = await _sql.QueryAsync($@"
            {BillBase}
            SELECT
                COUNT(*)                                                      AS TotalBills,
                SUM(CASE WHEN bb.Status = 'Enacted' THEN 1 ELSE 0 END)        AS Enacted,
                SUM(CASE WHEN bb.Status IN ('Passed House','Passed Senate')
                         THEN 1 ELSE 0 END)                                   AS PassedOneChamber,
                AVG(CAST(ISNULL(c.Cnt, 0) AS FLOAT))                          AS AvgCosponsors
            FROM BillBase bb
            LEFT JOIN
            (
                SELECT Type, BillNumber, COUNT(*) AS Cnt
                FROM Silver.Cosponsors
                GROUP BY Type, BillNumber
            ) c ON c.Type = bb.Type AND c.BillNumber = bb.BillNumber;",
            r => (Total: Int(r, "TotalBills"), Enacted: Int(r, "Enacted"),
                  Passed: Int(r, "PassedOneChamber"),
                  Avg: r["AvgCosponsors"] is DBNull ? 0 : Convert.ToDouble(r["AvgCosponsors"])),
            P("@party", Party), P("@state", State));

        if (kpis.Count > 0)
        {
            (TotalBills, Enacted, PassedOneChamber, AvgCosponsors) = kpis[0];
        }

        // ---- Pivot: like a GROUP BY row, col and then PIVOT in C# ----
        var rowCol = RowGroup;   // safe: validated against Groups above
        var colCol = ColGroup;

        var cells = await _sql.QueryAsync($@"
            {BillBase}
            SELECT {rowCol} AS RowKey, {colCol} AS ColKey, COUNT(*) AS Bills
            FROM BillBase
            GROUP BY {rowCol}, {colCol};",
            r => (Row: Str(r, "RowKey"), Col: Str(r, "ColKey"), Bills: Int(r, "Bills")),
            P("@party", Party), P("@state", State));

        foreach (var c in cells)
        {
            Cells[(c.Row, c.Col)] = c.Bills;
        }

        MaxCell = cells.Count == 0 ? 0 : cells.Max(c => c.Bills);

        // Biggest rows/columns first
        RowKeys = cells.GroupBy(c => c.Row)
            .OrderByDescending(g => g.Sum(x => x.Bills)).Select(g => g.Key).ToList();
        ColKeys = cells.GroupBy(c => c.Col)
            .OrderByDescending(g => g.Sum(x => x.Bills)).Select(g => g.Key).ToList();
    }

    public int Cell(string row, string col) =>
        Cells.TryGetValue((row, col), out var n) ? n : 0;

    public int RowTotal(string row) => ColKeys.Sum(c => Cell(row, c));
    public int ColTotal(string col) => RowKeys.Sum(r => Cell(r, col));
}
