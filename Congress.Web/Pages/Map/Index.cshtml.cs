using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;

namespace Congress.Web.Pages.Map;

public class IndexModel : PageModel
{
    private static readonly HttpClient HttpClient = new();

    public void OnGet()
    {
    }

    public async Task<IActionResult> OnGetDistrictsAsync()
    {
        var url =
            "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/0/query" +
            "?where=1%3D1" +
            "&outFields=GEOID%2CSTATE%2CCD120%2CNAME" +
            "&returnGeometry=true" +
            "&outSR=4326" +
            "&f=geojson";

        try
        {
            using var request = new HttpRequestMessage(
                HttpMethod.Get,
                url);

            request.Headers.UserAgent.ParseAdd(
                "Congress.Web/1.0");

            var response = await HttpClient.SendAsync(request);

            var content =
                await response.Content.ReadAsStringAsync();

            if (!response.IsSuccessStatusCode)
            {
                return StatusCode(
                    (int)response.StatusCode,
                    content);
            }

            return Content(
                content,
                "application/geo+json");
        }
        catch (Exception ex)
        {
            return StatusCode(
                500,
                "Error retrieving congressional district data: " +
                ex.Message);
        }
    }
}
