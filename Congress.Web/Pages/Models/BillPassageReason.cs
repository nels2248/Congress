namespace Congress.Web.Models;

public class BillPassageReason
{
    public long ReasonId { get; set; }
    public int FileId { get; set; }
    public string FeatureName { get; set; } = "";
    public double? Contribution { get; set; }
    public string Direction { get; set; } = "";
    public int ReasonRank { get; set; }
    public long? PredictionRunId { get; set; }
    public DateTime RunAt { get; set; }
}
