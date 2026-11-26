using Congress.Web.Data;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using static Congress.Web.Data.SqlHelper;

namespace Congress.Web.Pages.Members;

public class DetailsModel : PageModel
{
    private readonly SqlHelper _sql;

    public DetailsModel(SqlHelper sql) => _sql = sql;

    public const int MaxBills = 100;

    public IndexModel.MemberRow? Member { get; set; }
    public List<BillRow> SponsoredBills { get; set; } = new();
    public List<BillRow> CosponsoredBills { get; set; } = new();
    public List<Collaborator> TheirSupporters { get; set; } = new();   // co-sponsor this member's bills
    public List<Collaborator> TheySupport { get; set; } = new();       // sponsors whose bills this member co-signs

    public class BillRow
    {
        public string Type { get; set; } = "";
        public int BillNumber { get; set; }
        public string Title { get; set; } = "";
        public DateTime? IntroducedDate { get; set; }
        public DateTime? LatestActionDate { get; set; }
        public string Status { get; set; } = "";
        public string LegislationUrl { get; set; } = "";
        public string SponsorName { get; set; } = "";
        public string SponsorParty { get; set; } = "";
        public DateTime? SponsorshipDate { get; set; }
        public bool IsOriginal { get; set; }
    }

    public record Collaborator(string BioguideId, string FullName, string Party, string State, int Bills);

    public async Task<IActionResult> OnGetAsync(string id)
    {
        if (string.IsNullOrWhiteSpace(id))
            return RedirectToPage("/Members/Index");

        var member = await _sql.QueryAsync(
            $"{IndexModel.MemberSql} SELECT * FROM Members WHERE BioguideId = @id;",
            IndexModel.MapMember,
            P("@id", id));

        Member = member.FirstOrDefault();
        if (Member == null)
            return Page();

        SponsoredBills = await _sql.QueryAsync($@"
            SELECT TOP ({MaxBills})
                b.Type, b.BillNumber, b.Title, b.IntroducedDate, b.LatestActionDate, b.LegislationUrl,
                {BillStatusSql("b")} AS Status
            FROM Silver.Sponsors s
            INNER JOIN Silver.Bills b
                ON b.Type = s.Type AND b.BillNumber = s.BillNumber
            WHERE s.BioguideId = @id
            ORDER BY b.LatestActionDate DESC, b.Type, b.BillNumber;",
            r => new BillRow
            {
                Type = Str(r, "Type"),
                BillNumber = Int(r, "BillNumber"),
                Title = Str(r, "Title"),
                IntroducedDate = Date(r, "IntroducedDate"),
                LatestActionDate = Date(r, "LatestActionDate"),
                LegislationUrl = Str(r, "LegislationUrl"),
                Status = Str(r, "Status"),
            },
            P("@id", id));

        CosponsoredBills = await _sql.QueryAsync($@"
            SELECT TOP ({MaxBills})
                b.Type, b.BillNumber, b.Title, b.LatestActionDate, b.LegislationUrl,
                {BillStatusSql("b")} AS Status,
                s.FullName AS SponsorName,
                s.Party    AS SponsorParty,
                c.SponsorshipDate,
                c.IsOriginalCosponsor
            FROM Silver.Cosponsors c
            INNER JOIN Silver.Bills b
                ON b.Type = c.Type AND b.BillNumber = c.BillNumber
            LEFT JOIN Silver.Sponsors s
                ON s.Type = c.Type AND s.BillNumber = c.BillNumber
            WHERE c.BioguideId = @id
            ORDER BY c.SponsorshipDate DESC, b.Type, b.BillNumber;",
            r => new BillRow
            {
                Type = Str(r, "Type"),
                BillNumber = Int(r, "BillNumber"),
                Title = Str(r, "Title"),
                LatestActionDate = Date(r, "LatestActionDate"),
                LegislationUrl = Str(r, "LegislationUrl"),
                Status = Str(r, "Status"),
                SponsorName = Str(r, "SponsorName"),
                SponsorParty = Str(r, "SponsorParty"),
                SponsorshipDate = Date(r, "SponsorshipDate"),
                IsOriginal = string.Equals(Str(r, "IsOriginalCosponsor"), "True", StringComparison.OrdinalIgnoreCase),
            },
            P("@id", id));

        static Collaborator MapCollab(Microsoft.Data.SqlClient.SqlDataReader r) => new(
            Str(r, "BioguideId"), Str(r, "FullName"), Str(r, "Party"), Str(r, "State"), Int(r, "Bills"));

        TheirSupporters = await _sql.QueryAsync(@"
            SELECT TOP (10)
                c.BioguideId, MAX(c.FullName) AS FullName, MAX(c.Party) AS Party, MAX(c.State) AS State,
                COUNT(*) AS Bills
            FROM Silver.Sponsors s
            INNER JOIN Silver.Cosponsors c
                ON c.Type = s.Type AND c.BillNumber = s.BillNumber
            WHERE s.BioguideId = @id
            GROUP BY c.BioguideId
            ORDER BY COUNT(*) DESC, MAX(c.FullName);",
            MapCollab, P("@id", id));

        TheySupport = await _sql.QueryAsync(@"
            SELECT TOP (10)
                s.BioguideId, MAX(s.FullName) AS FullName, MAX(s.Party) AS Party, MAX(s.State) AS State,
                COUNT(*) AS Bills
            FROM Silver.Cosponsors c
            INNER JOIN Silver.Sponsors s
                ON s.Type = c.Type AND s.BillNumber = c.BillNumber
            WHERE c.BioguideId = @id
            GROUP BY s.BioguideId
            ORDER BY COUNT(*) DESC, MAX(s.FullName);",
            MapCollab, P("@id", id));

        return Page();
    }
}
