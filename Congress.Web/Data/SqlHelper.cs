using Microsoft.Data.SqlClient;

namespace Congress.Web.Data;

/// <summary>
/// Thin wrapper for read-only SQL against the Silver/Gold tables
/// (same raw SqlConnection pattern as the Network page).
/// </summary>
public class SqlHelper
{
    private readonly string _connectionString;

    public SqlHelper(IConfiguration configuration)
    {
        _connectionString = configuration.GetConnectionString("AzureSql")
            ?? throw new InvalidOperationException("AzureSql connection string was not found.");
    }

    public async Task<List<T>> QueryAsync<T>(
        string sql,
        Func<SqlDataReader, T> map,
        params SqlParameter[] parameters)
    {
        var results = new List<T>();

        await using var connection = new SqlConnection(_connectionString);
        await connection.OpenAsync();

        await using var command = new SqlCommand(sql, connection);
        command.Parameters.AddRange(parameters);

        await using var reader = await command.ExecuteReaderAsync();
        while (await reader.ReadAsync())
        {
            results.Add(map(reader));
        }

        return results;
    }

    /// <summary>Parameter that sends DBNull for null/empty, so "@x IS NULL OR col = @x" filters work.</summary>
    public static SqlParameter P(string name, object? value) =>
        new(name, value is null || (value is string s && s.Length == 0) ? DBNull.Value : value);

    // Small null-safe readers so the page code stays short
    public static string Str(SqlDataReader r, string col) =>
        r[col] is DBNull ? "" : r[col].ToString() ?? "";

    public static int Int(SqlDataReader r, string col) =>
        r[col] is DBNull ? 0 : Convert.ToInt32(r[col]);

    public static int? IntOrNull(SqlDataReader r, string col) =>
        r[col] is DBNull ? null : Convert.ToInt32(r[col]);

    public static DateTime? Date(SqlDataReader r, string col) =>
        r[col] is DBNull ? null : Convert.ToDateTime(r[col]);

    /// <summary>
    /// Same status buckets as bill_status_label in the Fabric notebook.
    /// Use as: SELECT ... BillStatusSql("b") AS Status FROM Silver.Bills b
    /// </summary>
    public static string BillStatusSql(string alias) => $@"
        CASE
            WHEN {alias}.LatestAction LIKE '%enacted%'                THEN 'Enacted'
            WHEN {alias}.LatestAction LIKE '%signed by president%'    THEN 'Enacted'
            WHEN {alias}.LatestAction LIKE '%became public law%'      THEN 'Enacted'
            WHEN {alias}.LatestAction LIKE '%passed senate%'          THEN 'Passed Senate'
            WHEN {alias}.LatestAction LIKE '%passed house%'           THEN 'Passed House'
            WHEN {alias}.LatestAction LIKE '%received in the senate%' THEN 'Passed House'
            WHEN {alias}.LatestAction LIKE '%referred to%'            THEN 'Referred'
            ELSE 'Other'
        END";
}
