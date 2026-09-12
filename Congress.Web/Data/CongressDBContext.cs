using Microsoft.EntityFrameworkCore;
using Congress.Web.Models;

namespace Congress.Web.Data;

public class CongressDbContext : DbContext
{
    public CongressDbContext(DbContextOptions<CongressDbContext> options) : base(options) { }

    public DbSet<Bill> Bills => Set<Bill>();
    public DbSet<BillPrediction> BillPredictions => Set<BillPrediction>();
    public DbSet<BillPassageReason> BillPassageReasons => Set<BillPassageReason>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Bill>(e =>
        {
            e.ToTable("Bills", "Silver", t => t.ExcludeFromMigrations());
            e.HasNoKey();

            e.Property(b => b.BillNumber).HasColumnName("BillNumber");
            e.Property(b => b.UpdateDate).HasColumnName("UpdateDate");
            e.Property(b => b.OriginChamber).HasColumnName("OriginChamber");
            e.Property(b => b.IntroducedDate).HasColumnName("IntroducedDate");
            e.Property(b => b.LegislationUrl).HasColumnName("LegislationUrl");
            e.Property(b => b.PolicyArea).HasColumnName("PolicyArea");
            e.Property(b => b.Title).HasColumnName("Title");
            e.Property(b => b.LatestActionDate).HasColumnName("LatestActionDate");
            e.Property(b => b.LatestAction).HasColumnName("LatestAction");
            e.Property(b => b.FileId).HasColumnName("FileId");
        });

        modelBuilder.Entity<BillPrediction>(e =>
        {
            e.ToTable("BillPassagePredictions", "Silver", t => t.ExcludeFromMigrations());
            e.HasKey(p => p.PredictionId);

            e.Property(p => p.PredictionId).HasColumnName("PredictionId");
            e.Property(p => p.FileId).HasColumnName("FileId");
            e.Property(p => p.Title).HasColumnName("Title");
            e.Property(p => p.ActualBecameLaw).HasColumnName("ActualBecameLaw");
            e.Property(p => p.PredictedProbability).HasColumnName("PredictedProbability");
            e.Property(p => p.PredictedOutcome).HasColumnName("PredictedOutcome");
            e.Property(p => p.PredictionRunId).HasColumnName("PredictionRunId");
            e.Property(p => p.RunAt).HasColumnName("RunAt");
        });

        modelBuilder.Entity<BillPassageReason>(e =>
        {
            e.ToTable("BillPassageReasons", "Silver", t => t.ExcludeFromMigrations());
            e.HasKey(r => r.ReasonId);

            e.Property(r => r.ReasonId).HasColumnName("ReasonId");
            e.Property(r => r.FileId).HasColumnName("FileId");
            e.Property(r => r.FeatureName).HasColumnName("FeatureName");
            e.Property(r => r.Contribution).HasColumnName("Contribution");
            e.Property(r => r.Direction).HasColumnName("Direction");
            e.Property(r => r.ReasonRank).HasColumnName("ReasonRank");
            e.Property(r => r.PredictionRunId).HasColumnName("PredictionRunId");
            e.Property(r => r.RunAt).HasColumnName("RunAt");
        });
    }
}
