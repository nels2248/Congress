namespace Congress.Web.Models;

public class Bill
{
    public int? BillNumber { get; set; }
    public DateTime? UpdateDate { get; set; }
    public string? OriginChamber { get; set; }
    public DateTime? IntroducedDate { get; set; }
    public string? LegislationUrl { get; set; }
    public string? PolicyArea { get; set; }
    public string Title { get; set; } = "";
    public DateTime? LatestActionDate { get; set; }
    public string? LatestAction { get; set; }
    public int FileId { get; set; }
}