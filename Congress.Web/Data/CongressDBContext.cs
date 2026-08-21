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
            e.ToTable("bills");
            e.HasKey(b => b.BillId);
            e.Property(b => b.BillId).HasColumnName("bill_id");
            e.Property(b => b.Title).HasColumnName("title");
            e.Property(b => b.Sponsor).HasColumnName("sponsor");
            e.Property(b => b.Passed).HasColumnName("passed");
            e.Property(b => b.PassageProbability).HasColumnName("passage_probability");
        });
    }
}