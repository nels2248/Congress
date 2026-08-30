using Microsoft.EntityFrameworkCore;
using Congress.Web.Models;

namespace Congress.Web.Data;

public class CongressDbContext : DbContext
{
    public CongressDbContext(DbContextOptions<CongressDbContext> options) : base(options) { }

    public DbSet<Bill> Bills => Set<Bill>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Bill>(e =>
        {
            e.ToTable("Bills", "Silver", t => t.ExcludeFromMigrations());
            e.HasNoKey();               // Silver.Bills has no PK — this is a reporting/read table
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
    }
}