using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Congress.Web.Migrations
{
    /// <inheritdoc />
    public partial class IntitialCreate : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "bills",
                columns: table => new
                {
                    bill_id = table.Column<string>(type: "nvarchar(450)", nullable: false),
                    title = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    sponsor = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    passed = table.Column<bool>(type: "bit", nullable: false),
                    passage_probability = table.Column<double>(type: "float", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_bills", x => x.bill_id);
                });
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "bills");
        }
    }
}
