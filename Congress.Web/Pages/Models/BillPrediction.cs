namespace Congress.Web.Models;

public class BillPrediction
{
    public long PredictionId { get; set; }
    public int FileId { get; set; }
    public string? Title { get; set; }
    public bool? ActualBecameLaw { get; set; }
    public double? PredictedProbability { get; set; }
    public string? PredictedOutcome { get; set; }
    public long? PredictionRunId { get; set; }
    public DateTime RunAt { get; set; }
}
