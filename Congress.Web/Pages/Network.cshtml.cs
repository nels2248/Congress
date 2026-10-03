using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.Data.SqlClient;
using System.Data;

namespace Congress.Web.Pages;

public class NetworkModel : PageModel
{
    private readonly IConfiguration _configuration;

    public NetworkModel(IConfiguration configuration)
    {
        _configuration = configuration;
    }

    public IActionResult OnGet()
    {
        return Page();
    }

    public async Task<IActionResult> OnGetMembersAsync()
    {
        var connectionString = _configuration.GetConnectionString("AzureSql");

        if (string.IsNullOrWhiteSpace(connectionString))
            return BadRequest("AzureSql connection string was not found.");

        var members = new List<object>();

        await using var connection = new SqlConnection(connectionString);
        await connection.OpenAsync();

        var sql = @"
SELECT
    BioguideId,
    FullName,
    Party,
    State
FROM congress.Gold.NetworkNodes
ORDER BY FullName;
";

        await using var command = new SqlCommand(sql, connection);
        await using var reader = await command.ExecuteReaderAsync();

        while (await reader.ReadAsync())
        {
            members.Add(new
            {
                Id = reader["BioguideId"]?.ToString() ?? "",
                Name = reader["FullName"]?.ToString() ?? "",
                Party = reader["Party"]?.ToString() ?? "",
                State = reader["State"]?.ToString() ?? ""
            });
        }

        return new JsonResult(members);
    }

    public async Task<IActionResult> OnGetDataAsync(
        string selectedIds,
        int networkSize = 50,
        int minSharedBills = 50)
    {
        var connectionString = _configuration.GetConnectionString("AzureSql");

        if (string.IsNullOrWhiteSpace(connectionString))
            return BadRequest("AzureSql connection string was not found.");

        if (string.IsNullOrWhiteSpace(selectedIds))
            return BadRequest("At least one person must be selected.");

        networkSize = Math.Clamp(networkSize, 2, 1000);
        minSharedBills = Math.Max(minSharedBills, 1);

        var selectedPeople = selectedIds
            .Split(
                ',',
                StringSplitOptions.RemoveEmptyEntries |
                StringSplitOptions.TrimEntries
            )
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();

        if (selectedPeople.Count == 0)
            return BadRequest("At least one person must be selected.");

        var selectedSet =
            new HashSet<string>(
                selectedPeople,
                StringComparer.OrdinalIgnoreCase
            );

        await using var connection = new SqlConnection(connectionString);
        await connection.OpenAsync();

        /*
         * ------------------------------------------------------------
         * STEP 1
         *
         * Load all qualifying relationships.
         *
         * SharedBillCount is the strength of the relationship.
         * ------------------------------------------------------------
         */

        var allEdges = new List<NetworkEdge>();

        var edgeSql = @"
SELECT
    Person1BioguideId,
    Person2BioguideId,
    SharedBillCount,
    IsCrossParty
FROM congress.Gold.NetworkEdges
WHERE SharedBillCount >= @MinSharedBills;
";

        await using (var command = new SqlCommand(edgeSql, connection))
        {
            command.Parameters.Add(
                "@MinSharedBills",
                SqlDbType.Int
            ).Value = minSharedBills;

            await using var reader =
                await command.ExecuteReaderAsync();

            while (await reader.ReadAsync())
            {
                allEdges.Add(new NetworkEdge
                {
                    Source =
                        reader["Person1BioguideId"]?.ToString()
                        ?? "",

                    Target =
                        reader["Person2BioguideId"]?.ToString()
                        ?? "",

                    SharedBillCount =
                        Convert.ToInt32(
                            reader["SharedBillCount"]
                        ),

                    CrossParty =
                        Convert.ToBoolean(
                            reader["IsCrossParty"]
                        )
                });
            }
        }

        /*
         * ------------------------------------------------------------
         * STEP 2
         *
         * Build the network using strongest relationships.
         *
         * The first relationship is the strongest relationship
         * available between selected people.
         *
         * After that, each new person is the person with the
         * strongest relationship to ANY person already in the
         * network.
         *
         * This creates a relationship-driven expansion.
         * ------------------------------------------------------------
         */

        var displayIds = new List<string>();

        var displaySet =
            new HashSet<string>(
                StringComparer.OrdinalIgnoreCase
            );

        /*
         * ------------------------------------------------------------
         * FIRST:
         *
         * Find the strongest edge where BOTH people were selected.
         * ------------------------------------------------------------
         */

        var strongestSelectedEdge =
            allEdges
                .Where(e =>
                    selectedSet.Contains(e.Source) &&
                    selectedSet.Contains(e.Target))
                .OrderByDescending(e => e.SharedBillCount)
                .ThenBy(e => e.Source)
                .ThenBy(e => e.Target)
                .FirstOrDefault();

        if (strongestSelectedEdge != null)
        {
            displayIds.Add(strongestSelectedEdge.Source);
            displaySet.Add(strongestSelectedEdge.Source);

            if (displayIds.Count < networkSize)
            {
                displayIds.Add(strongestSelectedEdge.Target);
                displaySet.Add(strongestSelectedEdge.Target);
            }
        }
        else
        {
            /*
             * If the selected people have no qualifying relationship
             * with each other, start with the first selected person.
             *
             * We will then try to connect outward from that person.
             */
            var firstSelected =
                selectedPeople.FirstOrDefault();

            if (!string.IsNullOrWhiteSpace(firstSelected))
            {
                displayIds.Add(firstSelected);
                displaySet.Add(firstSelected);
            }
        }

        /*
         * ------------------------------------------------------------
         * Keep expanding until we reach Network Size.
         *
         * Priority:
         *
         * 1. Unselected people connected to the current network.
         * 2. Other selected people connected to the current network.
         * 3. If there is no connection, use the strongest remaining
         *    relationship anywhere.
         *
         * This keeps the graph relationship-driven.
         * ------------------------------------------------------------
         */

        while (displayIds.Count < networkSize)
        {
            /*
             * Find the strongest edge where exactly ONE endpoint is
             * already in the network.
             *
             * This identifies the best next person to add.
             */
            var expansionEdge =
                allEdges
                    .Where(e =>
                        displaySet.Contains(e.Source) !=
                        displaySet.Contains(e.Target))
                    .OrderByDescending(e => e.SharedBillCount)
                    .ThenBy(e => e.Source)
                    .ThenBy(e => e.Target)
                    .FirstOrDefault();

            if (expansionEdge != null)
            {
                var newPerson =
                    displaySet.Contains(expansionEdge.Source)
                        ? expansionEdge.Target
                        : expansionEdge.Source;

                if (displaySet.Add(newPerson))
                {
                    displayIds.Add(newPerson);
                    continue;
                }
            }

            /*
             * --------------------------------------------------------
             * No edge can expand the current network.
             *
             * Find the strongest remaining edge anywhere and add
             * its endpoints as needed.
             * --------------------------------------------------------
             */

            var remainingEdge =
                allEdges
                    .Where(e =>
                        !displaySet.Contains(e.Source) ||
                        !displaySet.Contains(e.Target))
                    .OrderByDescending(e => e.SharedBillCount)
                    .ThenBy(e => e.Source)
                    .ThenBy(e => e.Target)
                    .FirstOrDefault();

            if (remainingEdge == null)
                break;

            if (displaySet.Add(remainingEdge.Source))
            {
                displayIds.Add(remainingEdge.Source);

                if (displayIds.Count >= networkSize)
                    break;
            }

            if (displaySet.Add(remainingEdge.Target))
            {
                displayIds.Add(remainingEdge.Target);
            }
        }

        /*
         * ------------------------------------------------------------
         * STEP 3
         *
         * Load node information.
         * ------------------------------------------------------------
         */

        var nodes = new List<NetworkNode>();

        if (displayIds.Count > 0)
        {
            var nodeParameters = new List<string>();

            for (int i = 0; i < displayIds.Count; i++)
                nodeParameters.Add($"@Node{i}");

            var nodeSql = $@"
SELECT
    BioguideId,
    FullName,
    Party,
    State,
    CommunityId,
    BillCount
FROM congress.Gold.NetworkNodes
WHERE BioguideId IN
(
    {string.Join(",", nodeParameters)}
);
";

            await using var command =
                new SqlCommand(nodeSql, connection);

            for (int i = 0; i < displayIds.Count; i++)
            {
                command.Parameters.Add(
                    nodeParameters[i],
                    SqlDbType.VarChar,
                    20
                ).Value = displayIds[i];
            }

            await using var reader =
                await command.ExecuteReaderAsync();

            while (await reader.ReadAsync())
            {
                var id =
                    reader["BioguideId"]?.ToString()
                    ?? "";

                nodes.Add(new NetworkNode
                {
                    Id = id,

                    Name =
                        reader["FullName"]?.ToString()
                        ?? "",

                    Party =
                        reader["Party"]?.ToString()
                        ?? "",

                    State =
                        reader["State"]?.ToString()
                        ?? "",

                    Community =
                        Convert.ToInt32(
                            reader["CommunityId"]
                        ),

                    BillCount =
                        Convert.ToInt32(
                            reader["BillCount"]
                        ),

                    IsSelected =
                        selectedSet.Contains(id)
                });
            }
        }

        /*
         * ------------------------------------------------------------
         * STEP 4
         *
         * Only return edges where BOTH endpoints are actually
         * displayed.
         * ------------------------------------------------------------
         */

        var nodeIds =
            new HashSet<string>(
                nodes.Select(n => n.Id),
                StringComparer.OrdinalIgnoreCase
            );

        var edges =
            allEdges
                .Where(e =>
                    nodeIds.Contains(e.Source) &&
                    nodeIds.Contains(e.Target))
                .ToList();

        /*
         * ------------------------------------------------------------
         * STEP 5
         *
         * Calculate relationship counts for node tooltips.
         * ------------------------------------------------------------
         */

        var relationshipCounts =
            nodes.ToDictionary(
                n => n.Id,
                n => 0,
                StringComparer.OrdinalIgnoreCase
            );

        foreach (var edge in edges)
        {
            if (relationshipCounts.ContainsKey(edge.Source))
                relationshipCounts[edge.Source]++;

            if (relationshipCounts.ContainsKey(edge.Target))
                relationshipCounts[edge.Target]++;
        }

        foreach (var node in nodes)
        {
            node.RelationshipCount =
                relationshipCounts[node.Id];
        }

        return new JsonResult(new
        {
            nodes,
            edges,
            selected = selectedPeople
        });
    }
}

public class NetworkNode
{
    public string Id { get; set; } = "";
    public string Name { get; set; } = "";
    public string Party { get; set; } = "";
    public string State { get; set; } = "";
    public int Community { get; set; }
    public int BillCount { get; set; }
    public int RelationshipCount { get; set; }
    public bool IsSelected { get; set; }
}

public class NetworkEdge
{
    public string Source { get; set; } = "";
    public string Target { get; set; } = "";
    public int SharedBillCount { get; set; }
    public bool CrossParty { get; set; }
}
