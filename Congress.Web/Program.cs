using Microsoft.EntityFrameworkCore;
using Congress.Web.Data;
using Microsoft.AspNetCore.StaticFiles;

var builder = WebApplication.CreateBuilder(args);

// ALL builder.Services.Add___() CALLS GO HERE, BEFORE Build()
builder.Services.AddRazorPages();
builder.Services.AddDbContext<CongressDbContext>(opt =>
    opt.UseSqlServer(builder.Configuration.GetConnectionString("AzureSql")));
builder.Services.AddHttpClient();
var app = builder.Build();   // <-- EVERYTHING ABOVE THIS LINE IS "REGISTER SERVICES"
                              //     EVERYTHING BELOW THIS LINE IS "CONFIGURE THE PIPELINE"

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseHttpsRedirection();
var provider = new FileExtensionContentTypeProvider();
provider.Mappings[".geojson"] = "application/geo+json";

app.UseStaticFiles(new StaticFileOptions
{
    ContentTypeProvider = provider
});
app.UseRouting();
app.UseAuthorization();
app.MapRazorPages();

app.Run();