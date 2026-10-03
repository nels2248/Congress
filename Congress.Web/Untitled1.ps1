@'
$ErrorActionPreference = "Stop"

# Always work relative to the folder where this script is located.
# Expected location:
# C:\Users\nels2\source\repos\Congress\Congress.Web\update-network.ps1

$projectRoot = $PSScriptRoot
$path = Join-Path $projectRoot "Pages\Network.cshtml"

# Verify the target file exists before doing anything.
if (-not (Test-Path $path)) {
    throw "Could not find Network.cshtml at: $path"
}

# Create timestamped backup in the same Pages folder.
$backup = Join-Path $projectRoot (
    "Pages\Network.cshtml.backup-" +
    (Get-Date -Format "yyyyMMdd-HHmmss")
)

Copy-Item $path $backup -Force

Write-Host "Backup created: $backup"

# Read the existing page.
$cshtml = Get-Content $path -Raw

# Add a simple Top 20 panel if it does not already exist.
if ($cshtml -notmatch 'id="connectionsList"') {

    $panel = @"
<div class="connections-panel">
    <div class="connections-title">Top 20 Connections</div>
    <div class="connections-subtitle">
        Strongest relationships in displayed network
    </div>
    <div id="connectionsList">
        <div class="connection-empty">
            Load a network to see connections.
        </div>
    </div>
</div>
"@

    $networkEnd = $cshtml.LastIndexOf('</div>')

    if ($networkEnd -lt 0) {
        throw "Could not find a closing </div> tag to insert the connections panel."
    }

    $cshtml =
        $cshtml.Substring(0, $networkEnd) +
        $panel +
        $cshtml.Substring($networkEnd)
}

# Add panel CSS if not already present.
if ($cshtml -notmatch '\.connections-panel') {

    $css = @"
    
    .network-content {
        display: flex;
        flex: 1 1 auto;
        min-height: 0;
        min-width: 0;
        overflow: hidden;
    }

    #network {
        flex: 1 1 75%;
        min-width: 0;
        min-height: 0;
        position: relative;
        overflow: hidden;
        background: #fafafa;
        cursor: grab;
    }

    .connections-panel {
        flex: 0 0 25%;
        min-width: 280px;
        max-width: 420px;
        overflow-y: auto;
        background: white;
        border-left: 1px solid #ccc;
        padding: 14px;
        box-sizing: border-box;
    }

    .connections-title {
        font-size: 16px;
        font-weight: 700;
        margin-bottom: 3px;
    }

    .connections-subtitle {
        font-size: 12px;
        color: #777;
        margin-bottom: 12px;
    }

    .connection-row {
        display: grid;
        grid-template-columns: 28px 1fr auto;
        gap: 8px;
        padding: 8px 4px;
        border-bottom: 1px solid #eee;
    }

    .connection-row:hover {
        background: #f5f5f5;
    }

    .connection-rank {
        color: #888;
        text-align: right;
    }

    .connection-person {
        font-weight: 600;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .connection-meta {
        color: #777;
        font-size: 11px;
    }

    .connection-count {
        font-size: 16px;
        font-weight: 700;
        text-align: right;
    }

    .connection-count-label {
        display: block;
        font-size: 9px;
        color: #777;
        font-weight: 400;
    }

    .connection-empty {
        color: #777;
        font-size: 13px;
    }
"@

    if ($cshtml -notmatch '</style>') {
        throw "Could not find </style> tag to insert connections panel CSS."
    }

    $cshtml = $cshtml.Replace(
        '</style>',
        "$css`n</style>"
    )
}

# Add JavaScript function if it doesn't exist.
if ($cshtml -notmatch 'function updateConnectionsPanel') {

    $function = @"

    function updateConnectionsPanel(data) {

        const list =
            document.getElementById("connectionsList");

        if (!list)
            return;

        list.innerHTML = "";

        if (!data.edges || data.edges.length === 0) {

            list.innerHTML =
                '<div class="connection-empty">' +
                'No qualifying connections.' +
                '</div>';

            return;
        }

        const nodeMap =
            new Map(
                data.nodes.map(n => [n.id, n])
            );

        const topConnections =
            [...data.edges]
                .sort(
                    (a, b) =>
                        b.sharedBillCount -
                        a.sharedBillCount
                )
                .slice(0, 20);

        topConnections.forEach(
            function(edge, index) {

                const source =
                    typeof edge.source === "object"
                        ? edge.source
                        : nodeMap.get(edge.source);

                const target =
                    typeof edge.target === "object"
                        ? edge.target
                        : nodeMap.get(edge.target);

                if (!source || !target)
                    return;

                const row =
                    document.createElement("div");

                row.className =
                    "connection-row";

                row.innerHTML =
                    '<div class="connection-rank">' +
                    (index + 1) +
                    '</div>' +

                    '<div>' +

                    '<div class="connection-person">' +
                    source.name +
                    '</div>' +

                    '<div class="connection-person">' +
                    target.name +
                    '</div>' +

                    '<div class="connection-meta">' +
                    (source.party || "?") +
                    "-" +
                    (source.state || "?") +
                    " ↔ " +
                    (target.party || "?") +
                    "-" +
                    (target.state || "?") +
                    (
                        edge.crossParty
                            ? " • Cross-party"
                            : " • Same party"
                    ) +
                    '</div>' +

                    '</div>' +

                    '<div class="connection-count">' +
                    edge.sharedBillCount +
                    '<span class="connection-count-label">' +
                    'bills' +
                    '</span>' +
                    '</div>';

                list.appendChild(row);
            }
        );
    }

"@

    $marker = 'function drawNetwork(data)'

    $position = $cshtml.IndexOf($marker)

    if ($position -ge 0) {

        $cshtml =
            $cshtml.Substring(0, $position) +
            $function +
            $cshtml.Substring($position)

        Write-Host "Added updateConnectionsPanel() JavaScript function."
    }
    else {
        Write-Host "WARNING: function drawNetwork(data) was not found."
    }
}

# Make sure the panel gets refreshed whenever the graph loads.
if ($cshtml -notmatch 'updateConnectionsPanel\(data\);') {

    if ($cshtml -match 'drawNetwork\(data\);') {

        $cshtml =
            $cshtml.Replace(
                'drawNetwork(data);',
                'drawNetwork(data);' + "`n        updateConnectionsPanel(data);"
            )

        Write-Host "Added connections panel refresh after drawNetwork()."
    }
    else {
        Write-Host "WARNING: drawNetwork(data); call was not found."
    }
}

# Save the modified page.
$cshtml | Set-Content $path -Encoding UTF8

Write-Host ""
Write-Host "======================================"
Write-Host "NETWORK UPDATE COMPLETE"
Write-Host "======================================"
Write-Host "Project: $projectRoot"
Write-Host "Updated: $path"
Write-Host "Backup:  $backup"
Write-Host ""
Write-Host "Restart the app and press Ctrl+F5."
'@ | Set-Content "C:\Users\nels2\source\repos\Congress\Congress.Web\update-network.ps1" -Encoding UTF8

powershell -ExecutionPolicy Bypass -File "C:\Users\nels2\source\repos\Congress\Congress.Web\update-network.ps1"