using Microsoft.AspNetCore.Mvc;
using Microsoft.Data.SqlClient;
using Microsoft.Extensions.Configuration;
using System;
using System.Collections.Generic;
using System.Data;
using System.Threading.Tasks;

namespace CongressWeb.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class NetworkEdgesController : ControllerBase
    {
        private readonly string _connectionString;

        // Automatically pulls your existing database connection string from appsettings.json
        public NetworkEdgesController(IConfiguration configuration)
        {
            _connectionString = configuration.GetConnectionString("DefaultConnection") 
                                ?? configuration.GetConnectionString("SqlServer") 
                                ?? "";
        }

        // Endpoint: api/NetworkEdges/pages?page=1&pageSize=5000
        [HttpGet("pages")]
        public async Task<IActionResult> GetEdgePage([FromQuery] int page = 1, [FromQuery] int pageSize = 5000)
        {
            if (page < 1) page = 1;
            if (pageSize > 10000) pageSize = 10000;

            var offset = (page - 1) * pageSize;

            var edges = new List<object>();
            int totalCount = 0;

            // Raw SQL Execution using high-performance pagination
            using (var connection = new SqlConnection(_connectionString))
            {
                await connection.OpenAsync();

                // 1. Get the total row count
                using (var countCmd = new SqlCommand("SELECT COUNT(*) FROM [congress].[Gold].[NetworkEdges]", connection))
                {
                    totalCount = (int)await countCmd.ExecuteScalarAsync();
                }

                // 2. Fetch the specific page rows
                var query = @"
                    SELECT Person1BioguideId, Person2BioguideId, SharedBillCount, IsCrossParty
                    FROM [congress].[Gold].[NetworkEdges]
                    ORDER BY Person1BioguideId
                    OFFSET @Offset ROWS
                    FETCH NEXT @PageSize ROWS ONLY;";

                using (var cmd = new SqlCommand(query, connection))
                {
                    cmd.Parameters.AddWithValue("@Offset", offset);
                    cmd.Parameters.AddWithValue("@PageSize", pageSize);

                    using (var reader = await cmd.ExecuteReaderAsync())
                    {
                        while (await reader.ReadAsync())
                        {
                            edges.Add(new
                            {
                                source = reader["Person1BioguideId"].ToString(),
                                target = reader["Person2BioguideId"].ToString(),
                                weight = Convert.ToInt32(reader["SharedBillCount"]),
                                isCrossParty = Convert.ToInt32(reader["IsCrossParty"]) == 1
                            });
                        }
                    }
                }
            }

            var totalPages = (int)Math.Ceiling((double)totalCount / pageSize);

            return Ok(new
            {
                CurrentPage = page,
                PageSize = pageSize,
                TotalPages = totalPages,
                TotalEdges = totalCount,
                Data = edges
            });
        }
    }
}
