namespace Congress.Web.Models;

public class Bill
{
    public string BillId { get; set; } = "";
    public string Title { get; set; } = "";
    public string Sponsor { get; set; } = "";
    public bool Passed { get; set; }
    public double PassageProbability { get; set; }
}