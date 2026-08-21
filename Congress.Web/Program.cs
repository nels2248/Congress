using Microsoft.EntityFrameworkCore;
using Congress.Web.Data;

var builder = WebApplication.CreateBuilder(args);

// ALL builder.Services.Add___() CALLS GO HERE, BEFORE Build()
builder.Services.AddRazorPages();
builder.Services.AddDbContext<CongressDbContext>(opt =>
    opt.UseSqlServer(builder.Configuration.GetConnectionString("AzureSql")));

var app = builder.Build();   // <-- EVERYTHING ABOVE THIS LINE IS "REGISTER SERVICES"
                              //     EVERYTHING BELOW THIS LINE IS "CONFIGURE THE PIPELINE"

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseHttpsRedirection();
app.UseStaticFiles();
app.UseRouting();
app.UseAuthorization();
app.MapRazorPages();

app.Run();