# Congressional Intelligence Platform

Live Web App Link here (may require multiple clicks when app goes cold)
https://congress-web-app.azurewebsites.net/

An open-source platform for exploring, analyzing, and understanding the U.S. Congress through legislative data, analytics, and web applications.

## Architecture

- **Congress.Web** — ASP.NET Core / .NET 8 Razor Pages web application.
- **Congress.Functions** — Azure Functions for background processing and data loading.
- **Congress Database** — Azure SQL Database storing congressional data and application tables.

## Infrastructure

- Web application: Azure App Service
- Background processing: Azure Functions
- Database: Azure SQL Database
- Source control: GitHub and Azure DevOps

The long-term goal is to make the platform portable, open-source, and accessible to outside contributors while reducing dependencies on proprietary cloud services where practical.

## Repository Structure

- `Congress.Web/` — Web application
- `Congress.Functions/` — Azure Functions
- `Congress.Database` - Database  
- `README.md` — Project documentation

*Update this structure as additional projects are added.*

## Development

1. Clone the repository.
2. Open the solution in Visual Studio or VS Code.
3. Configure local application settings and database connections.
4. Build and run the appropriate project.
5. Test changes before committing.

Never commit passwords, credentials, connection strings containing secrets, or API keys.

## Database

The application currently uses Azure SQL Database. Database schema and deployment procedures will be documented as the database project is incorporated into source control.

## Roadmap

- [ ] Fix issues with silver layer co sponsors taking a long time to run
- [ ] Add usable functionality to GIS
- [ ] Enhance Network graphs
- [ ] Fine tune prediction piece
- [ ] Add Pages for each congress person
- [ ] Update for 120th Congress

## Contributing

Contributions, suggestions, and improvements are welcome. The goal is to build a maintainable platform for exploring congressional legislation, activity, and relationships.

## License

A project license will be added once the licensing approach is established.