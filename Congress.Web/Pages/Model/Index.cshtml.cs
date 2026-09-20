using Congress.Web.Data;
using Congress.Web.Models;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;

namespace Congress.Web.Pages.Model;

public class IndexModel : PageModel
{
    private readonly CongressDbContext _db;

    public IndexModel(CongressDbContext db)
    {
        _db = db;
    }

    public long? LatestRunId { get; set; }

    public DateTime? RunAt { get; set; }

    public List<ModelCoefficient> Coefficients { get; set; } = new();

    public int FeatureCount => Coefficients.Count;

    public double MaxCoefficientMagnitude =>
        Coefficients.Count == 0
            ? 0
            : Coefficients.Max(c => Math.Abs(c.Coefficient));

    public List<CoefficientGroup> CoefficientGroups { get; set; } = new();

    public async Task OnGetAsync()
    {
        LatestRunId = await _db.BillPassageModelCoefficients
            .MaxAsync(c => (long?)c.PredictionRunId);

        if (LatestRunId == null)
        {
            return;
        }

        Coefficients = await _db.BillPassageModelCoefficients
            .Where(c => c.PredictionRunId == LatestRunId)
            .OrderByDescending(c => Math.Abs(c.Coefficient))
            .ToListAsync();

        CoefficientGroups = BuildGroups(Coefficients);

        RunAt = await _db.BillPredictions
            .Where(p => p.PredictionRunId == LatestRunId)
            .Select(p => (DateTime?)p.RunAt)
            .FirstOrDefaultAsync();
    }

    private static List<CoefficientGroup> BuildGroups(
        List<ModelCoefficient> coefficients)
    {
        var groups = new List<CoefficientGroup>();

        AddGroup(
            groups,
            coefficients,
            "Type_",
            "Bill Type",
            "The type of legislation, such as HR, S, HRES, or HJRES.");

        AddGroup(
            groups,
            coefficients,
            "OriginChamber_",
            "Origin Chamber",
            "The chamber where the legislation originated.");

        AddGroup(
            groups,
            coefficients,
            "PolicyArea_",
            "Policy Area",
            "The congressional policy area associated with the legislation.");

        var knownPrefixes = new[]
        {
            "Type_",
            "OriginChamber_",
            "PolicyArea_"
        };

        var otherCoefficients = coefficients
            .Where(c => !knownPrefixes.Any(prefix =>
                c.FeatureName.StartsWith(
                    prefix,
                    StringComparison.OrdinalIgnoreCase)))
            .ToList();

        if (otherCoefficients.Count > 0)
        {
            groups.Add(new CoefficientGroup
            {
                Name = "Other Features",
                Description = "Additional features used by the model.",
                Coefficients = otherCoefficients
            });
        }

        return groups;
    }

    private static void AddGroup(
        List<CoefficientGroup> groups,
        List<ModelCoefficient> coefficients,
        string prefix,
        string name,
        string description)
    {
        var groupCoefficients = coefficients
            .Where(c => c.FeatureName.StartsWith(
                prefix,
                StringComparison.OrdinalIgnoreCase))
            .OrderByDescending(c => Math.Abs(c.Coefficient))
            .ToList();

        if (groupCoefficients.Count == 0)
        {
            return;
        }

        groups.Add(new CoefficientGroup
        {
            Name = name,
            Description = description,
            Coefficients = groupCoefficients
        });
    }
}

public class CoefficientGroup
{
    public string Name { get; set; } = "";

    public string Description { get; set; } = "";

    public List<ModelCoefficient> Coefficients { get; set; } = new();

    public List<ModelCoefficient> Positive =>
        Coefficients
            .Where(c => c.Coefficient > 0)
            .OrderByDescending(c => c.Coefficient)
            .ToList();

    public List<ModelCoefficient> Negative =>
        Coefficients
            .Where(c => c.Coefficient < 0)
            .OrderBy(c => c.Coefficient)
            .ToList();
}
