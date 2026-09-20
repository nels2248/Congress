namespace Congress.Web.Models;

public class ModelCoefficient
{
    public long CoefficientId { get; set; }
    public long PredictionRunId { get; set; }
    public string FeatureName { get; set; } = "";
    public double Coefficient { get; set; }
    public DateTime RunAt { get; set; }
}
