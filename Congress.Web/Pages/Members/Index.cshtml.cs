using Congress.Web.Data;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using static Congress.Web.Data.SqlHelper;

namespace Congress.Web.Pages.Members;

/// <summary>
/// Port of the Fabric "Nodes" page as a member list: every person who
/// sponsored or co-sponsored a bill, with activity counts.
/// </summary>
public class IndexModel : PageModel
{
    private readonly SqlHelper _sql;

    public IndexModel(SqlHelper sql) => _sql = sql;

    // Whitelist: sort value -> ORDER BY clause
    public static readonly Dictionary<string, (string Label, string OrderBy)> Sorts = new()
    {
        ["sponsored"]   = ("Bills sponsored",   "Sponsored DESC, LastName"),
        ["cosponsored"] = ("Bills co-sponsored", "Cosponsored DESC, LastName"),
        ["crossparty"]  = ("Cross-party %",     "CrossPartyPct DESC, LastName"),
        ["name"]        = ("Name",              "LastName, FirstName"),
    };

    [BindProperty(SupportsGet = true)] public string? Chamber { get; set; }
    [BindProperty(SupportsGet = true)] public string? Party { get; set; }
    [BindProperty(SupportsGet = true)] public string? State { get; set; }
    [BindProperty(SupportsGet = true)] public string? Search { get; set; }
    [BindProperty(SupportsGet = true)] public string Sort { get; set; } = "sponsored";

    public List<string> Parties { get; set; } = new();
    public List<string> States { get; set; } = new();
    public List<MemberRow> Members { get; set; } = new();

    public class MemberRow
    {
        public string BioguideId { get; set; } = "";
        public string FullName { get; set; } = "";
        public string Party { get; set; } = "";
        public string State { get; set; } = "";
        public int? District { get; set; }
        public string Chamber { get; set; } = "";
        public int Sponsored { get; set; }
        public int Cosponsored { get; set; }
        public double CrossPartyPct { get; set; }
    }

    /// <summary>
    /// One row per person with sponsor / co-sponsor counts. Shared with the Details page.
    /// Chamber: no district = Senate (same rule as the Fabric notebook's sponsor_is_senator).
    /// </summary>
    public const string MemberSql = @"
        WITH People AS
        (
            SELECT BioguideId, FullName, FirstName, LastName, Party, State, District FROM Silver.Sponsors
            UNION ALL
            SELECT BioguideId, FullName, FirstName, LastName, Party, State, District FROM Silver.Cosponsors
        ),
        Info AS
        (
            SELECT
                BioguideId,
                MAX(FullName)  AS FullName,
                MAX(FirstName) AS FirstName,
                MAX(LastName)  AS LastName,
                MAX(Party)     AS Party,
                MAX(State)     AS State,
                MAX(District)  AS District
            FROM People
            WHERE BioguideId IS NOT NULL
            GROUP BY BioguideId
        ),
        Sp AS
        (
            SELECT BioguideId, COUNT(*) AS Sponsored
            FROM Silver.Sponsors
            GROUP BY BioguideId
        ),
        Co AS
        (
            SELECT
                c.BioguideId,
                COUNT(*) AS Cosponsored,
                SUM(CASE WHEN s.Party <> c.Party THEN 1 ELSE 0 END) AS CrossParty
            FROM Silver.Cosponsors c
            LEFT JOIN Silver.Sponsors s
                ON s.Type = c.Type
               AND s.BillNumber = c.BillNumber
            GROUP BY c.BioguideId
        ),
        Members AS
        (
            SELECT
                i.BioguideId, i.FullName, i.FirstName, i.LastName, i.Party, i.State, i.District,
                CASE WHEN i.District IS NULL THEN 'Senate' ELSE 'House' END AS Chamber,
                ISNULL(sp.Sponsored, 0)   AS Sponsored,
                ISNULL(co.Cosponsored, 0) AS Cosponsored,
                CASE WHEN ISNULL(co.Cosponsored, 0) = 0 THEN 0.0
                     ELSE CAST(co.CrossParty AS FLOAT) / co.Cosponsored END AS CrossPartyPct
            FROM Info i
            LEFT JOIN Sp sp ON sp.BioguideId = i.BioguideId
            LEFT JOIN Co co ON co.BioguideId = i.BioguideId
        )";

    public static MemberRow MapMember(Microsoft.Data.SqlClient.SqlDataReader r) => new()
    {
        BioguideId    = Str(r, "BioguideId"),
        FullName      = Str(r, "FullName"),
        Party         = Str(r, "Party"),
        State         = Str(r, "State"),
        District      = IntOrNull(r, "District"),
        Chamber       = Str(r, "Chamber"),
        Sponsored     = Int(r, "Sponsored"),
        Cosponsored   = Int(r, "Cosponsored"),
        CrossPartyPct = r["CrossPartyPct"] is DBNull ? 0 : Convert.ToDouble(r["CrossPartyPct"]),
    };

    public async Task OnGetAsync()
    {
        if (!Sorts.ContainsKey(Sort)) Sort = "sponsored";

        Parties = await _sql.QueryAsync(
            "SELECT DISTINCT Party FROM Silver.Sponsors WHERE Party IS NOT NULL ORDER BY Party",
            r => Str(r, "Party"));

        States = await _sql.QueryAsync(
            "SELECT DISTINCT State FROM Silver.Sponsors WHERE State IS NOT NULL ORDER BY State",
            r => Str(r, "State"));

        Members = await _sql.QueryAsync($@"
            {MemberSql}
            SELECT *
            FROM Members
            WHERE (@chamber IS NULL OR Chamber = @chamber)
              AND (@party   IS NULL OR Party = @party)
              AND (@state   IS NULL OR State = @state)
              AND (@search  IS NULL OR FullName LIKE '%' + @search + '%')
            ORDER BY {Sorts[Sort].OrderBy};",
            MapMember,
            P("@chamber", Chamber), P("@party", Party), P("@state", State), P("@search", Search));
    }
}
