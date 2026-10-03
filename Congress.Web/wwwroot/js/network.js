(() => {

    let currentData = null;
    let currentMode = "overview";
    let selectedMemberId = null;

    const width = 1200;
    const height = 750;

    // =========================================================
    // TEMPORARY TEST SUBSET
    // =========================================================

    const TEST_MEMBER_IDS = new Set([
        "B001277",
        "S001227"
    ]);


    // =========================================================
    // SVG
    // =========================================================

    const svg = d3.select("#networkGraph")
        .append("svg")
        .attr("viewBox", `0 0 ${width} ${height}`)
        .attr("preserveAspectRatio", "xMidYMid meet");

    const root = svg.append("g");

    const zoom = d3.zoom()
        .scaleExtent([0.25, 5])
        .on("zoom", event => {
            root.attr("transform", event.transform);
        });

    svg.call(zoom);

    const graphLayer = root.append("g");
    const edgeLayer = graphLayer.append("g");
    const nodeLayer = graphLayer.append("g");
    const labelLayer = graphLayer.append("g");

    const tooltip = d3.select("body")
        .append("div")
        .attr("class", "network-tooltip")
        .style("display", "none");


    // =========================================================
    // PARTY COLOR
    // =========================================================

    function partyColor(party) {

        if (party === "D") {
            return "#2b6cb0";
        }

        if (party === "R") {
            return "#c53030";
        }

        return "#718096";
    }


    // =========================================================
    // GET NODE ID
    // =========================================================

    function getNodeId(node) {

        return (
            node.bioguideId ??
            node.BioguideId ??
            node.bioGuideId ??
            node.BioGuideId ??
            node.person1BioguideId ??
            node.Person1BioguideId
        );

    }


    // =========================================================
    // GET EDGE SOURCE
    // =========================================================

    function getEdgeSource(edge) {

        return (
            edge.source ??
            edge.Source ??
            edge.person1BioguideId ??
            edge.Person1BioguideId ??
            edge.person1BioGuideId ??
            edge.Person1BioGuideId
        );

    }


    // =========================================================
    // GET EDGE TARGET
    // =========================================================

    function getEdgeTarget(edge) {

        return (
            edge.target ??
            edge.Target ??
            edge.person2BioguideId ??
            edge.Person2BioguideId ??
            edge.person2BioGuideId ??
            edge.Person2BioGuideId
        );

    }


    // =========================================================
    // GET SHARED BILL COUNT
    // =========================================================

    function getSharedBillCount(edge) {

        return Number(
            edge.sharedBillCount ??
            edge.SharedBillCount ??
            0
        );

    }


    // =========================================================
    // GET CROSS PARTY
    // =========================================================

    function getCrossParty(edge) {

        return (
            edge.crossParty ??
            edge.CrossParty ??
            edge.isCrossParty ??
            edge.IsCrossParty ??
            false
        );

    }


    // =========================================================
    // NORMALIZE DATA
    // =========================================================

    function normalizeData(data) {

        const nodes =
            (data.nodes || []).map(node => ({
                ...node,
                bioguideId: getNodeId(node)
            }));


        const edges =
            (data.edges || []).map(edge => ({
                ...edge,

                source:
                    getEdgeSource(edge),

                target:
                    getEdgeTarget(edge),

                sharedBillCount:
                    getSharedBillCount(edge),

                crossParty:
                    Boolean(
                        getCrossParty(edge)
                    )

            }));


        return {
            ...data,
            nodes,
            edges
        };

    }


    // =========================================================
    // TEMPORARY TEST FILTER
    // =========================================================

    function createTestSubset(data) {

        const normalized =
            normalizeData(data);


        // Keep any relationship where either
        // endpoint is one of our two test members.

        const testEdges =
            normalized.edges.filter(edge => {

                return (
                    TEST_MEMBER_IDS.has(
                        edge.source
                    )
                    ||
                    TEST_MEMBER_IDS.has(
                        edge.target
                    )
                );

            });


        const testNodeIds =
            new Set();


        testEdges.forEach(edge => {

            testNodeIds.add(
                edge.source
            );

            testNodeIds.add(
                edge.target
            );

        });


        const testNodes =
            normalized.nodes.filter(node => {

                return testNodeIds.has(
                    node.bioguideId
                );

            });


        console.log(
            "================================="
        );

        console.log(
            "TEMPORARY NETWORK TEST"
        );

        console.log(
            "Original nodes:",
            normalized.nodes.length
        );

        console.log(
            "Original edges:",
            normalized.edges.length
        );

        console.log(
            "Test nodes:",
            testNodes.length
        );

        console.log(
            "Test edges:",
            testEdges.length
        );

        console.log(
            "Test members:",
            Array.from(
                TEST_MEMBER_IDS
            )
        );

        console.log(
            "Test edges:",
            testEdges
        );

        console.log(
            "================================="
        );


        return {
            ...normalized,
            nodes: testNodes,
            edges: testEdges
        };

    }


    // =========================================================
    // EDGE STYLE
    // =========================================================

    function edgeStyle(selection) {

        selection
            .attr(
                "stroke-width",
                d => {

                    if (
                        d.sharedBillCount < 10
                    ) {
                        return 1;
                    }

                    return Math.min(
                        8,
                        1.2 +
                        Math.sqrt(
                            d.sharedBillCount
                        ) * 0.7
                    );

                }
            )
            .attr(
                "stroke",
                d =>
                    d.sharedBillCount < 10
                        ? "#d3d3d3"
                        : null
            )
            .attr(
                "stroke-dasharray",
                d =>
                    d.sharedBillCount < 10
                        ? "3,4"
                        : null
            );

    }


    // =========================================================
    // CLEAR GRAPH
    // =========================================================

    function clearGraph() {

        edgeLayer
            .selectAll("*")
            .remove();

        nodeLayer
            .selectAll("*")
            .remove();

        labelLayer
            .selectAll("*")
            .remove();

    }


    // =========================================================
    // LOAD NETWORK
    // =========================================================

    async function loadNetwork() {

        try {

            const minShared =
                document.getElementById(
                    "minSharedBills"
                ).value || 5;


            const response =
                await fetch(
                    `/Network?handler=Data&minSharedBills=${minShared}`
                );


            if (!response.ok) {

                throw new Error(
                    `Network request failed: ${response.status}`
                );

            }


            const data =
                await response.json();


            console.log(
                "RAW NETWORK DATA:",
                data
            );


            console.log(
                "FIRST NODE:",
                data.nodes?.[0]
            );


            console.log(
                "FIRST EDGE:",
                data.edges?.[0]
            );


            // -------------------------------------------------
            // TEMPORARY SUBSET
            // -------------------------------------------------

            currentData =
                createTestSubset(data);


            drawCurrentView();

        }
        catch (error) {

            console.error(
                "Network loading error:",
                error
            );


            document.getElementById(
                "networkStats"
            ).textContent =
                "Unable to load network.";

        }

    }


    // =========================================================
    // CENTRALITY
    // =========================================================

    function calculateCentrality(
        nodes,
        edges
    ) {

        const centrality =
            new Map();


        nodes.forEach(node => {

            centrality.set(
                node.bioguideId,
                0
            );

        });


        edges.forEach(edge => {

            centrality.set(
                edge.source,
                (
                    centrality.get(
                        edge.source
                    ) || 0
                )
                +
                edge.sharedBillCount
            );


            centrality.set(
                edge.target,
                (
                    centrality.get(
                        edge.target
                    ) || 0
                )
                +
                edge.sharedBillCount
            );

        });


        return centrality;

    }


    // =========================================================
    // DRAW CURRENT VIEW
    // =========================================================

    function drawCurrentView() {

        if (!currentData) {
            return;
        }


        clearGraph();


        const partyFilter =
            document.getElementById(
                "partyFilter"
            ).value;


        const communityFilter =
            document.getElementById(
                "communityFilter"
            ).value;


        if (
            currentMode === "overview"
        ) {

            drawOverview(
                currentData,
                false,
                partyFilter,
                communityFilter
            );

        }
        else if (
            currentMode === "communities"
        ) {

            drawOverview(
                currentData,
                true,
                partyFilter,
                communityFilter
            );

        }
        else if (
            currentMode === "members"
            &&
            selectedMemberId
        ) {

            showMemberNetwork(
                selectedMemberId
            );

        }
        else {

            drawOverview(
                currentData,
                false,
                partyFilter,
                communityFilter
            );

        }

    }


    // =========================================================
    // OVERVIEW
    // =========================================================

    function drawOverview(
        data,
        communityOnly = false,
        partyFilter = "ALL",
        communityFilter = ""
    ) {

        let nodes =
            data.nodes.map(d => ({
                ...d
            }));


        let edges =
            data.edges.map(d => ({
                ...d
            }));


        // -----------------------------------------------------
        // PARTY FILTER
        // -----------------------------------------------------

        if (
            partyFilter !== "ALL"
        ) {

            nodes =
                nodes.filter(
                    n =>
                        n.party === partyFilter
                );

        }


        // -----------------------------------------------------
        // COMMUNITY FILTER
        // -----------------------------------------------------

        if (
            communityFilter !== ""
        ) {

            nodes =
                nodes.filter(
                    n =>
                        String(
                            n.communityId
                        )
                        ===
                        String(
                            communityFilter
                        )
                );

        }


        const visibleIds =
            new Set(
                nodes.map(
                    n =>
                        n.bioguideId
                )
            );


        edges =
            edges.filter(
                e =>
                    visibleIds.has(
                        e.source
                    )
                    &&
                    visibleIds.has(
                        e.target
                    )
            );


        // -----------------------------------------------------
        // CENTRALITY
        // -----------------------------------------------------

        const centrality =
            calculateCentrality(
                nodes,
                edges
            );


        // -----------------------------------------------------
        // POSITION NODES
        // -----------------------------------------------------

        if (communityOnly) {

            const communityGroups =
                d3.group(
                    nodes,
                    d =>
                        d.communityId
                );


            const groups =
                Array.from(
                    communityGroups.entries()
                );


            nodes.forEach(node => {

                const group =
                    communityGroups.get(
                        node.communityId
                    ) || [];


                const index =
                    group.indexOf(
                        node
                    );


                const angle =
                    (
                        index /
                        Math.max(
                            group.length,
                            1
                        )
                    )
                    *
                    Math.PI *
                    2;


                const radius =
                    100 +
                    Math.sqrt(
                        group.length
                    ) * 12;


                const communityIndex =
                    groups.findIndex(
                        ([id]) =>
                            id ===
                            node.communityId
                    );


                const columns = 4;


                const row =
                    Math.floor(
                        communityIndex /
                        columns
                    );


                const column =
                    communityIndex %
                    columns;


                const centerX =
                    180 +
                    column * 280;


                const centerY =
                    150 +
                    row * 260;


                node.x =
                    centerX +
                    Math.cos(angle) *
                    radius;


                node.y =
                    centerY +
                    Math.sin(angle) *
                    radius;


            });

        }
        else {

            const communities =
                d3.group(
                    nodes,
                    d =>
                        d.communityId
                );


            const communityArray =
                Array.from(
                    communities.entries()
                );


            communityArray.forEach(
                (
                    [communityId, group],
                    communityIndex
                ) => {

                    const angle =
                        (
                            communityIndex /
                            Math.max(
                                communityArray.length,
                                1
                            )
                        )
                        *
                        Math.PI *
                        2;


                    const communityRadius =
                        Math.min(
                            260,
                            100 +
                            communityArray.length *
                            12
                        );


                    const centerX =
                        width / 2 +
                        Math.cos(angle) *
                        communityRadius;


                    const centerY =
                        height / 2 +
                        Math.sin(angle) *
                        communityRadius;


                    group.forEach(
                        (
                            node,
                            index
                        ) => {

                            const memberAngle =
                                (
                                    index /
                                    Math.max(
                                        group.length,
                                        1
                                    )
                                )
                                *
                                Math.PI *
                                2;


                            const radius =
                                60 +
                                Math.sqrt(
                                    group.length
                                ) * 10;


                            node.x =
                                centerX +
                                Math.cos(
                                    memberAngle
                                ) *
                                radius;


                            node.y =
                                centerY +
                                Math.sin(
                                    memberAngle
                                ) *
                                radius;


                            node.centrality =
                                centrality.get(
                                    node.bioguideId
                                ) || 0;

                        }
                    );

                }
            );

        }


        // -----------------------------------------------------
        // COLLISION ADJUSTMENT
        // -----------------------------------------------------

        for (
            let iteration = 0;
            iteration < 5;
            iteration++
        ) {

            for (
                let i = 0;
                i < nodes.length;
                i++
            ) {

                for (
                    let j = i + 1;
                    j < nodes.length;
                    j++
                ) {

                    const a =
                        nodes[i];

                    const b =
                        nodes[j];


                    const dx =
                        b.x - a.x;

                    const dy =
                        b.y - a.y;


                    const distance =
                        Math.sqrt(
                            dx * dx +
                            dy * dy
                        );


                    const minimumDistance =
                        32;


                    if (
                        distance > 0
                        &&
                        distance <
                        minimumDistance
                    ) {

                        const push =
                            (
                                minimumDistance -
                                distance
                            ) / 2;


                        const nx =
                            dx / distance;

                        const ny =
                            dy / distance;


                        a.x -=
                            nx * push;

                        a.y -=
                            ny * push;


                        b.x +=
                            nx * push;

                        b.y +=
                            ny * push;

                    }

                }

            }

        }


        // -----------------------------------------------------
        // PREPARE EDGES
        // -----------------------------------------------------

        const overviewEdges =
            edges
                .map(edge => ({

                    ...edge,

                    sourceNode:
                        nodes.find(
                            n =>
                                n.bioguideId
                                ===
                                edge.source
                        ),

                    targetNode:
                        nodes.find(
                            n =>
                                n.bioguideId
                                ===
                                edge.target
                        )

                }))
                .filter(
                    e =>
                        e.sourceNode
                        &&
                        e.targetNode
                );


        // -----------------------------------------------------
        // DRAW EDGES
        // -----------------------------------------------------

        const links =
            edgeLayer
                .selectAll("line")
                .data(
                    overviewEdges,
                    d =>
                        `${d.source}-${d.target}`
                )
                .enter()
                .append("line")
                .attr(
                    "class",
                    d =>
                        d.crossParty
                            ? "network-edge cross-party"
                            : "network-edge same-party"
                )
                .attr(
                    "x1",
                    d =>
                        d.sourceNode.x
                )
                .attr(
                    "y1",
                    d =>
                        d.sourceNode.y
                )
                .attr(
                    "x2",
                    d =>
                        d.targetNode.x
                )
                .attr(
                    "y2",
                    d =>
                        d.targetNode.y
                )
                .attr(
                    "opacity",
                    d =>
                        d.sharedBillCount < 10
                            ? 0.8
                            : Math.min(
                                0.65,
                                0.15 +
                                d.sharedBillCount *
                                0.01
                            )
                );


        edgeStyle(links);


        // -----------------------------------------------------
        // DRAW NODES
        // -----------------------------------------------------

        const nodesSelection =
            nodeLayer
                .selectAll("circle")
                .data(
                    nodes,
                    d =>
                        d.bioguideId
                )
                .enter()
                .append("circle")
                .attr(
                    "class",
                    "network-node"
                )
                .attr(
                    "cx",
                    d =>
                        d.x
                )
                .attr(
                    "cy",
                    d =>
                        d.y
                )
                .attr(
                    "r",
                    d =>
                        Math.max(
                            7,
                            Math.min(
                                22,
                                6 +
                                Math.sqrt(
                                    d.centrality ||
                                    0
                                ) *
                                0.8
                            )
                        )
                )
                .attr(
                    "fill",
                    d =>
                        partyColor(
                            d.party
                        )
                )
                .on(
                    "mouseenter",
                    function(event, d) {

                        tooltip
                            .style(
                                "display",
                                "block"
                            )
                            .html(`
                                <strong>${d.name || "Unknown"}</strong><br>
                                ${d.party || ""} ${d.state || ""}<br>
                                Collaboration weight:
                                ${d.centrality || 0}
                            `);

                    }
                )
                .on(
                    "mousemove",
                    function(event) {

                        tooltip
                            .style(
                                "left",
                                `${event.pageX + 12}px`
                            )
                            .style(
                                "top",
                                `${event.pageY + 12}px`
                            );

                    }
                )
                .on(
                    "mouseleave",
                    function() {

                        tooltip
                            .style(
                                "display",
                                "none"
                            );

                    }
                )
                .on(
                    "click",
                    function(event, d) {

                        event.stopPropagation();


                        selectedMemberId =
                            d.bioguideId;


                        showMemberDetails(
                            d,
                            data
                        );


                        highlightMember(
                            d.bioguideId
                        );

                    }
                );


        // -----------------------------------------------------
        // DRAG
        // -----------------------------------------------------

        nodesSelection.call(

            d3.drag()

                .on(
                    "start",
                    function(event, d) {

                        d.fx =
                            d.x;

                        d.fy =
                            d.y;

                    }
                )

                .on(
                    "drag",
                    function(event, d) {

                        d.fx =
                            event.x;

                        d.fy =
                            event.y;


                        d3.select(this)
                            .attr(
                                "cx",
                                d.fx
                            )
                            .attr(
                                "cy",
                                d.fy
                            );


                        links
                            .filter(
                                e =>
                                    e.sourceNode
                                    ===
                                    d
                                    ||
                                    e.targetNode
                                    ===
                                    d
                            )
                            .attr(
                                "x1",
                                e =>
                                    e.sourceNode.x
                            )
                            .attr(
                                "y1",
                                e =>
                                    e.sourceNode.y
                            )
                            .attr(
                                "x2",
                                e =>
                                    e.targetNode.x
                            )
                            .attr(
                                "y2",
                                e =>
                                    e.targetNode.y
                            );

                    }
                )

                .on(
                    "end",
                    function(event, d) {

                        d.fx =
                            null;

                        d.fy =
                            null;

                    }
                )

        );


        // -----------------------------------------------------
        // COMMUNITY LABELS
        // -----------------------------------------------------

        const communityGroups =
            d3.group(
                nodes,
                d =>
                    d.communityId
            );


        communityGroups.forEach(
            (group, communityId) => {

                if (
                    !group.length
                ) {
                    return;
                }


                const centerX =
                    d3.mean(
                        group,
                        d =>
                            d.x
                    );


                const centerY =
                    d3.mean(
                        group,
                        d =>
                            d.y
                    );


                labelLayer
                    .append("text")
                    .attr(
                        "class",
                        "community-label"
                    )
                    .attr(
                        "x",
                        centerX
                    )
                    .attr(
                        "y",
                        centerY - 70
                    )
                    .attr(
                        "text-anchor",
                        "middle"
                    )
                    .text(
                        `Community ${communityId}`
                    );

            }
        );


        // -----------------------------------------------------
        // STATS
        // -----------------------------------------------------

        const crossPartyCount =
            edges.filter(
                e =>
                    e.crossParty
            ).length;


        document.getElementById(
            "networkStats"
        ).textContent =
            `${nodes.length} members • ` +
            `${edges.length} relationships • ` +
            `${crossPartyCount} cross-party`;

    }


    // =========================================================
    // HIGHLIGHT MEMBER
    // =========================================================

    function highlightMember(id) {

        const connectedEdges =
            new Set();


        currentData.edges.forEach(
            edge => {

                if (
                    edge.source === id
                    ||
                    edge.target === id
                ) {

                    connectedEdges.add(
                        `${edge.source}-${edge.target}`
                    );

                    connectedEdges.add(
                        `${edge.target}-${edge.source}`
                    );

                }

            }
        );


        edgeLayer
            .selectAll("line")
            .attr(
                "opacity",
                d => {

                    const key =
                        `${d.source}-${d.target}`;


                    return connectedEdges.has(
                        key
                    )
                        ? 0.9
                        : 0.03;

                }
            );


        nodeLayer
            .selectAll("circle")
            .attr(
                "opacity",
                d =>
                    d.bioguideId === id
                        ? 1
                        : 0.25
            );

    }


    // =========================================================
    // RESET HIGHLIGHT
    // =========================================================

    function resetHighlight() {

        edgeLayer
            .selectAll("line")
            .attr(
                "opacity",
                d =>
                    d.sharedBillCount < 10
                        ? 0.8
                        : Math.min(
                            0.65,
                            0.15 +
                            d.sharedBillCount *
                            0.01
                        )
            );


        nodeLayer
            .selectAll("circle")
            .attr(
                "opacity",
                1
            );

    }


    // =========================================================
    // MEMBER DETAILS
    // =========================================================

    function showMemberDetails(
        member,
        data
    ) {

        document.getElementById(
            "memberEmpty"
        ).style.display =
            "none";


        document.getElementById(
            "memberDetails"
        ).style.display =
            "block";


        document.getElementById(
            "memberName"
        ).textContent =
            member.name ||
            "Unknown";


        document.getElementById(
            "memberPartyState"
        ).textContent =
            `${member.party || ""} ${member.state || ""}`;


        document.getElementById(
            "memberBills"
        ).textContent =
            member.billCount ??
            member.bills ??
            "-";


        document.getElementById(
            "memberCommunity"
        ).textContent =
            member.communityId ??
            "-";


        const connections =
            data.edges.filter(
                e =>
                    e.source ===
                    member.bioguideId
                    ||
                    e.target ===
                    member.bioguideId
            );


        document.getElementById(
            "memberConnections"
        ).textContent =
            connections.length;


        const crossParty =
            connections.filter(
                e =>
                    e.crossParty
            ).length;


        document.getElementById(
            "memberCrossParty"
        ).textContent =
            crossParty;


        // -----------------------------------------------------
        // TOP COLLABORATORS
        // -----------------------------------------------------

        const collaborators =
            connections
                .map(edge => {

                    const otherId =
                        edge.source ===
                        member.bioguideId
                            ? edge.target
                            : edge.source;


                    const other =
                        data.nodes.find(
                            n =>
                                n.bioguideId
                                ===
                                otherId
                        );


                    return {

                        member: other,

                        sharedBillCount:
                            edge.sharedBillCount,

                        crossParty:
                            edge.crossParty

                    };

                })
                .filter(
                    x =>
                        x.member
                )
                .sort(
                    (a, b) =>
                        b.sharedBillCount
                        -
                        a.sharedBillCount
                )
                .slice(
                    0,
                    10
                );


        const container =
            document.getElementById(
                "topCollaborators"
            );


        container.innerHTML =
            "";


        collaborators.forEach(
            item => {

                const div =
                    document.createElement(
                        "div"
                    );


                div.className =
                    "collaborator-item";


                div.innerHTML = `
                    <div>
                        <strong>
                            ${item.member.name || "Unknown"}
                        </strong>
                        <small>
                            ${item.member.party || ""}
                            ${item.member.state || ""}
                        </small>
                    </div>

                    <span>
                        ${item.sharedBillCount}
                    </span>
                `;


                div.addEventListener(
                    "click",
                    () => {

                        selectedMemberId =
                            item.member.bioguideId;


                        showMemberDetails(
                            item.member,
                            data
                        );


                        highlightMember(
                            item.member.bioguideId
                        );

                    }
                );


                container.appendChild(
                    div
                );

            }
        );


        // -----------------------------------------------------
        // FOCUS BUTTON
        // -----------------------------------------------------

        const focusButton =
            document.getElementById(
                "focusMemberButton"
            );


        focusButton.onclick =
            () => {

                selectedMemberId =
                    member.bioguideId;


                currentMode =
                    "members";


                updateModeButtons();


                showMemberNetwork(
                    member.bioguideId
                );

            };


        // -----------------------------------------------------
        // COMMUNITY BUTTON
        // -----------------------------------------------------

        const communityButton =
            document.getElementById(
                "showCommunityButton"
            );


        communityButton.onclick =
            () => {

                const communitySelect =
                    document.getElementById(
                        "communityFilter"
                    );


                communitySelect.value =
                    member.communityId;


                currentMode =
                    "communities";


                updateModeButtons();


                drawCurrentView();

            };

    }


    // =========================================================
    // MEMBER NETWORK
    // =========================================================

    function showMemberNetwork(
        memberId
    ) {

        if (!currentData) {
            return;
        }


        clearGraph();


        const member =
            currentData.nodes.find(
                n =>
                    n.bioguideId ===
                    memberId
            );


        if (!member) {
            return;
        }


        const memberEdges =
            currentData.edges
                .filter(
                    e =>
                        e.source ===
                        memberId
                        ||
                        e.target ===
                        memberId
                )
                .sort(
                    (a, b) =>
                        b.sharedBillCount
                        -
                        a.sharedBillCount
                )
                .slice(
                    0,
                    25
                );


        const relatedIds =
            new Set(
                [memberId].concat(
                    memberEdges.flatMap(
                        e => [
                            e.source,
                            e.target
                        ]
                    )
                )
            );


        const nodes =
            currentData.nodes
                .filter(
                    n =>
                        relatedIds.has(
                            n.bioguideId
                        )
                )
                .map(
                    n => ({
                        ...n
                    })
                );


        const nodeMap =
            new Map(
                nodes.map(
                    n => [
                        n.bioguideId,
                        n
                    ]
                )
            );


        const edges =
            memberEdges
                .map(
                    e => ({

                        ...e,

                        sourceNode:
                            nodeMap.get(
                                e.source
                            ),

                        targetNode:
                            nodeMap.get(
                                e.target
                            )

                    })
                )
                .filter(
                    e =>
                        e.sourceNode
                        &&
                        e.targetNode
                );


        // -----------------------------------------------------
        // FORCE SIMULATION
        // -----------------------------------------------------

        const simulation =
            d3.forceSimulation(
                nodes
            )
                .force(
                    "link",
                    d3.forceLink(
                        edges
                    )
                        .id(
                            d =>
                                d.bioguideId
                        )
                        .distance(
                            d =>
                                Math.max(
                                    60,
                                    180 -
                                    d.sharedBillCount *
                                    2
                                )
                        )
                        .strength(
                            0.6
                        )
                )
                .force(
                    "charge",
                    d3.forceManyBody()
                        .strength(
                            -300
                        )
                )
                .force(
                    "center",
                    d3.forceCenter(
                        width / 2,
                        height / 2
                    )
                )
                .force(
                    "collision",
                    d3.forceCollide()
                        .radius(
                            28
                        )
                );


        // -----------------------------------------------------
        // EDGES
        // -----------------------------------------------------

        const link =
            edgeLayer
                .selectAll("line")
                .data(edges)
                .enter()
                .append("line")
                .attr(
                    "class",
                    d =>
                        d.crossParty
                            ? "network-edge cross-party"
                            : "network-edge same-party"
                )
                .attr(
                    "opacity",
                    d =>
                        d.sharedBillCount < 10
                            ? 0.8
                            : 0.65
                );


        edgeStyle(link);


        // -----------------------------------------------------
        // NODES
        // -----------------------------------------------------

        const node =
            nodeLayer
                .selectAll("circle")
                .data(nodes)
                .enter()
                .append("circle")
                .attr(
                    "class",
                    "network-node"
                )
                .attr(
                    "r",
                    d =>
                        d.bioguideId ===
                        memberId
                            ? 22
                            : 10
                )
                .attr(
                    "fill",
                    d =>
                        partyColor(
                            d.party
                        )
                )
                .on(
                    "mouseenter",
                    function(event, d) {

                        tooltip
                            .style(
                                "display",
                                "block"
                            )
                            .html(`
                                <strong>${d.name || "Unknown"}</strong><br>
                                ${d.party || ""} ${d.state || ""}
                            `);

                    }
                )
                .on(
                    "mousemove",
                    function(event) {

                        tooltip
                            .style(
                                "left",
                                `${event.pageX + 12}px`
                            )
                            .style(
                                "top",
                                `${event.pageY + 12}px`
                            );

                    }
                )
                .on(
                    "mouseleave",
                    function() {

                        tooltip
                            .style(
                                "display",
                                "none"
                            );

                    }
                )
                .on(
                    "click",
                    function(event, d) {

                        event.stopPropagation();


                        selectedMemberId =
                            d.bioguideId;


                        showMemberDetails(
                            d,
                            currentData
                        );

                    }
                );


        // -----------------------------------------------------
        // FIX CENTER MEMBER
        // -----------------------------------------------------

        member.fx =
            width / 2;

        member.fy =
            height / 2;


        // -----------------------------------------------------
        // SIMULATION
        // -----------------------------------------------------

        simulation.on(
            "tick",
            () => {

                link
                    .attr(
                        "x1",
                        d =>
                            d.source.x
                    )
                    .attr(
                        "y1",
                        d =>
                            d.source.y
                    )
                    .attr(
                        "x2",
                        d =>
                            d.target.x
                    )
                    .attr(
                        "y2",
                        d =>
                            d.target.y
                    );


                node
                    .attr(
                        "cx",
                        d =>
                            d.x
                    )
                    .attr(
                        "cy",
                        d =>
                            d.y
                    );

            }
        );


        // -----------------------------------------------------
        // DRAG
        // -----------------------------------------------------

        node.call(

            d3.drag()

                .on(
                    "start",
                    function(event, d) {

                        if (
                            !event.active
                        ) {

                            simulation
                                .alphaTarget(
                                    0.3
                                )
                                .restart();

                        }


                        d.fx =
                            d.x;

                        d.fy =
                            d.y;

                    }
                )

                .on(
                    "drag",
                    function(event, d) {

                        d.fx =
                            event.x;

                        d.fy =
                            event.y;

                    }
                )

                .on(
                    "end",
                    function(event, d) {

                        if (
                            !event.active
                        ) {

                            simulation
                                .alphaTarget(
                                    0
                                );

                        }


                        if (
                            d.bioguideId
                            !==
                            memberId
                        ) {

                            d.fx =
                                null;

                            d.fy =
                                null;

                        }

                    }
                )

        );


        document.getElementById(
            "networkStats"
        ).textContent =
            `${nodes.length} members • ` +
            `${edges.length} relationships`;

    }


    // =========================================================
    // MODE BUTTONS
    // =========================================================

    function updateModeButtons() {

        document
            .querySelectorAll(
                ".view-button"
            )
            .forEach(
                button =>
                    button.classList.remove(
                        "active"
                    )
            );


        if (
            currentMode ===
            "overview"
        ) {

            document
                .getElementById(
                    "overviewMode"
                )
                .classList.add(
                    "active"
                );

        }
        else if (
            currentMode ===
            "communities"
        ) {

            document
                .getElementById(
                    "communityMode"
                )
                .classList.add(
                    "active"
                );

        }
        else if (
            currentMode ===
            "members"
        ) {

            document
                .getElementById(
                    "memberMode"
                )
                .classList.add(
                    "active"
                );

        }

    }


    // =========================================================
    // BUTTON EVENTS
    // =========================================================

    document
        .getElementById(
            "overviewMode"
        )
        .addEventListener(
            "click",
            () => {

                currentMode =
                    "overview";

                selectedMemberId =
                    null;

                updateModeButtons();

                resetHighlight();

                drawCurrentView();

            }
        );


    document
        .getElementById(
            "communityMode"
        )
        .addEventListener(
            "click",
            () => {

                currentMode =
                    "communities";

                selectedMemberId =
                    null;

                updateModeButtons();

                resetHighlight();

                drawCurrentView();

            }
        );


    document
        .getElementById(
            "memberMode"
        )
        .addEventListener(
            "click",
            () => {

                if (
                    selectedMemberId
                ) {

                    currentMode =
                        "members";

                    updateModeButtons();

                    showMemberNetwork(
                        selectedMemberId
                    );

                }

            }
        );


    document
        .getElementById(
            "loadNetwork"
        )
        .addEventListener(
            "click",
            () => {

                currentMode =
                    "overview";

                selectedMemberId =
                    null;

                updateModeButtons();

                loadNetwork();

            }
        );


    document
        .getElementById(
            "overviewButton"
        )
        .addEventListener(
            "click",
            () => {

                currentMode =
                    "overview";

                selectedMemberId =
                    null;

                updateModeButtons();


                document.getElementById(
                    "partyFilter"
                ).value =
                    "ALL";


                document.getElementById(
                    "communityFilter"
                ).value =
                    "";


                resetHighlight();

                drawCurrentView();

            }
        );


    // =========================================================
    // BACKGROUND CLICK
    // =========================================================

    svg.on(
        "click",
        () => {

            selectedMemberId =
                null;

            resetHighlight();

        }
    );


    // =========================================================
    // INITIAL LOAD
    // =========================================================

    loadNetwork();

})();(() => {

    let currentData = null;
    let currentMode = "overview";
    let selectedMemberId = null;

    const width = 1200;
    const height = 750;

    // =========================================================
    // TEMPORARY TEST SUBSET
    // =========================================================

    const TEST_MEMBER_IDS = new Set([
        "B001277",
        "S001227"
    ]);


    // =========================================================
    // SVG
    // =========================================================

    const svg = d3.select("#networkGraph")
        .append("svg")
        .attr("viewBox", `0 0 ${width} ${height}`)
        .attr("preserveAspectRatio", "xMidYMid meet");

    const root = svg.append("g");

    const zoom = d3.zoom()
        .scaleExtent([0.25, 5])
        .on("zoom", event => {
            root.attr("transform", event.transform);
        });

    svg.call(zoom);

    const graphLayer = root.append("g");
    const edgeLayer = graphLayer.append("g");
    const nodeLayer = graphLayer.append("g");
    const labelLayer = graphLayer.append("g");

    const tooltip = d3.select("body")
        .append("div")
        .attr("class", "network-tooltip")
        .style("display", "none");


    // =========================================================
    // PARTY COLOR
    // =========================================================

    function partyColor(party) {

        if (party === "D") {
            return "#2b6cb0";
        }

        if (party === "R") {
            return "#c53030";
        }

        return "#718096";
    }


    // =========================================================
    // GET NODE ID
    // =========================================================

    function getNodeId(node) {

        return (
            node.bioguideId ??
            node.BioguideId ??
            node.bioGuideId ??
            node.BioGuideId ??
            node.person1BioguideId ??
            node.Person1BioguideId
        );

    }


    // =========================================================
    // GET EDGE SOURCE
    // =========================================================

    function getEdgeSource(edge) {

        return (
            edge.source ??
            edge.Source ??
            edge.person1BioguideId ??
            edge.Person1BioguideId ??
            edge.person1BioGuideId ??
            edge.Person1BioGuideId
        );

    }


    // =========================================================
    // GET EDGE TARGET
    // =========================================================

    function getEdgeTarget(edge) {

        return (
            edge.target ??
            edge.Target ??
            edge.person2BioguideId ??
            edge.Person2BioguideId ??
            edge.person2BioGuideId ??
            edge.Person2BioGuideId
        );

    }


    // =========================================================
    // GET SHARED BILL COUNT
    // =========================================================

    function getSharedBillCount(edge) {

        return Number(
            edge.sharedBillCount ??
            edge.SharedBillCount ??
            0
        );

    }


    // =========================================================
    // GET CROSS PARTY
    // =========================================================

    function getCrossParty(edge) {

        return (
            edge.crossParty ??
            edge.CrossParty ??
            edge.isCrossParty ??
            edge.IsCrossParty ??
            false
        );

    }


    // =========================================================
    // NORMALIZE DATA
    // =========================================================

    function normalizeData(data) {

        const nodes =
            (data.nodes || []).map(node => ({
                ...node,
                bioguideId: getNodeId(node)
            }));


        const edges =
            (data.edges || []).map(edge => ({
                ...edge,

                source:
                    getEdgeSource(edge),

                target:
                    getEdgeTarget(edge),

                sharedBillCount:
                    getSharedBillCount(edge),

                crossParty:
                    Boolean(
                        getCrossParty(edge)
                    )

            }));


        return {
            ...data,
            nodes,
            edges
        };

    }


    // =========================================================
    // TEMPORARY TEST FILTER
    // =========================================================

    function createTestSubset(data) {

        const normalized =
            normalizeData(data);


        // Keep any relationship where either
        // endpoint is one of our two test members.

        const testEdges =
            normalized.edges.filter(edge => {

                return (
                    TEST_MEMBER_IDS.has(
                        edge.source
                    )
                    ||
                    TEST_MEMBER_IDS.has(
                        edge.target
                    )
                );

            });


        const testNodeIds =
            new Set();


        testEdges.forEach(edge => {

            testNodeIds.add(
                edge.source
            );

            testNodeIds.add(
                edge.target
            );

        });


        const testNodes =
            normalized.nodes.filter(node => {

                return testNodeIds.has(
                    node.bioguideId
                );

            });


        console.log(
            "================================="
        );

        console.log(
            "TEMPORARY NETWORK TEST"
        );

        console.log(
            "Original nodes:",
            normalized.nodes.length
        );

        console.log(
            "Original edges:",
            normalized.edges.length
        );

        console.log(
            "Test nodes:",
            testNodes.length
        );

        console.log(
            "Test edges:",
            testEdges.length
        );

        console.log(
            "Test members:",
            Array.from(
                TEST_MEMBER_IDS
            )
        );

        console.log(
            "Test edges:",
            testEdges
        );

        console.log(
            "================================="
        );


        return {
            ...normalized,
            nodes: testNodes,
            edges: testEdges
        };

    }


    // =========================================================
    // EDGE STYLE
    // =========================================================

    function edgeStyle(selection) {

        selection
            .attr(
                "stroke-width",
                d => {

                    if (
                        d.sharedBillCount < 10
                    ) {
                        return 1;
                    }

                    return Math.min(
                        8,
                        1.2 +
                        Math.sqrt(
                            d.sharedBillCount
                        ) * 0.7
                    );

                }
            )
            .attr(
                "stroke",
                d =>
                    d.sharedBillCount < 10
                        ? "#d3d3d3"
                        : null
            )
            .attr(
                "stroke-dasharray",
                d =>
                    d.sharedBillCount < 10
                        ? "3,4"
                        : null
            );

    }


    // =========================================================
    // CLEAR GRAPH
    // =========================================================

    function clearGraph() {

        edgeLayer
            .selectAll("*")
            .remove();

        nodeLayer
            .selectAll("*")
            .remove();

        labelLayer
            .selectAll("*")
            .remove();

    }


    // =========================================================
    // LOAD NETWORK
    // =========================================================

    async function loadNetwork() {

        try {

            const minShared =
                document.getElementById(
                    "minSharedBills"
                ).value || 5;


            const response =
                await fetch(
                    `/Network?handler=Data&minSharedBills=${minShared}`
                );


            if (!response.ok) {

                throw new Error(
                    `Network request failed: ${response.status}`
                );

            }


            const data =
                await response.json();


            console.log(
                "RAW NETWORK DATA:",
                data
            );


            console.log(
                "FIRST NODE:",
                data.nodes?.[0]
            );


            console.log(
                "FIRST EDGE:",
                data.edges?.[0]
            );


            // -------------------------------------------------
            // TEMPORARY SUBSET
            // -------------------------------------------------

            currentData =
                createTestSubset(data);


            drawCurrentView();

        }
        catch (error) {

            console.error(
                "Network loading error:",
                error
            );


            document.getElementById(
                "networkStats"
            ).textContent =
                "Unable to load network.";

        }

    }


    // =========================================================
    // CENTRALITY
    // =========================================================

    function calculateCentrality(
        nodes,
        edges
    ) {

        const centrality =
            new Map();


        nodes.forEach(node => {

            centrality.set(
                node.bioguideId,
                0
            );

        });


        edges.forEach(edge => {

            centrality.set(
                edge.source,
                (
                    centrality.get(
                        edge.source
                    ) || 0
                )
                +
                edge.sharedBillCount
            );


            centrality.set(
                edge.target,
                (
                    centrality.get(
                        edge.target
                    ) || 0
                )
                +
                edge.sharedBillCount
            );

        });


        return centrality;

    }


    // =========================================================
    // DRAW CURRENT VIEW
    // =========================================================

    function drawCurrentView() {

        if (!currentData) {
            return;
        }


        clearGraph();


        const partyFilter =
            document.getElementById(
                "partyFilter"
            ).value;


        const communityFilter =
            document.getElementById(
                "communityFilter"
            ).value;


        if (
            currentMode === "overview"
        ) {

            drawOverview(
                currentData,
                false,
                partyFilter,
                communityFilter
            );

        }
        else if (
            currentMode === "communities"
        ) {

            drawOverview(
                currentData,
                true,
                partyFilter,
                communityFilter
            );

        }
        else if (
            currentMode === "members"
            &&
            selectedMemberId
        ) {

            showMemberNetwork(
                selectedMemberId
            );

        }
        else {

            drawOverview(
                currentData,
                false,
                partyFilter,
                communityFilter
            );

        }

    }


    // =========================================================
    // OVERVIEW
    // =========================================================

    function drawOverview(
        data,
        communityOnly = false,
        partyFilter = "ALL",
        communityFilter = ""
    ) {

        let nodes =
            data.nodes.map(d => ({
                ...d
            }));


        let edges =
            data.edges.map(d => ({
                ...d
            }));


        // -----------------------------------------------------
        // PARTY FILTER
        // -----------------------------------------------------

        if (
            partyFilter !== "ALL"
        ) {

            nodes =
                nodes.filter(
                    n =>
                        n.party === partyFilter
                );

        }


        // -----------------------------------------------------
        // COMMUNITY FILTER
        // -----------------------------------------------------

        if (
            communityFilter !== ""
        ) {

            nodes =
                nodes.filter(
                    n =>
                        String(
                            n.communityId
                        )
                        ===
                        String(
                            communityFilter
                        )
                );

        }


        const visibleIds =
            new Set(
                nodes.map(
                    n =>
                        n.bioguideId
                )
            );


        edges =
            edges.filter(
                e =>
                    visibleIds.has(
                        e.source
                    )
                    &&
                    visibleIds.has(
                        e.target
                    )
            );


        // -----------------------------------------------------
        // CENTRALITY
        // -----------------------------------------------------

        const centrality =
            calculateCentrality(
                nodes,
                edges
            );


        // -----------------------------------------------------
        // POSITION NODES
        // -----------------------------------------------------

        if (communityOnly) {

            const communityGroups =
                d3.group(
                    nodes,
                    d =>
                        d.communityId
                );


            const groups =
                Array.from(
                    communityGroups.entries()
                );


            nodes.forEach(node => {

                const group =
                    communityGroups.get(
                        node.communityId
                    ) || [];


                const index =
                    group.indexOf(
                        node
                    );


                const angle =
                    (
                        index /
                        Math.max(
                            group.length,
                            1
                        )
                    )
                    *
                    Math.PI *
                    2;


                const radius =
                    100 +
                    Math.sqrt(
                        group.length
                    ) * 12;


                const communityIndex =
                    groups.findIndex(
                        ([id]) =>
                            id ===
                            node.communityId
                    );


                const columns = 4;


                const row =
                    Math.floor(
                        communityIndex /
                        columns
                    );


                const column =
                    communityIndex %
                    columns;


                const centerX =
                    180 +
                    column * 280;


                const centerY =
                    150 +
                    row * 260;


                node.x =
                    centerX +
                    Math.cos(angle) *
                    radius;


                node.y =
                    centerY +
                    Math.sin(angle) *
                    radius;


            });

        }
        else {

            const communities =
                d3.group(
                    nodes,
                    d =>
                        d.communityId
                );


            const communityArray =
                Array.from(
                    communities.entries()
                );


            communityArray.forEach(
                (
                    [communityId, group],
                    communityIndex
                ) => {

                    const angle =
                        (
                            communityIndex /
                            Math.max(
                                communityArray.length,
                                1
                            )
                        )
                        *
                        Math.PI *
                        2;


                    const communityRadius =
                        Math.min(
                            260,
                            100 +
                            communityArray.length *
                            12
                        );


                    const centerX =
                        width / 2 +
                        Math.cos(angle) *
                        communityRadius;


                    const centerY =
                        height / 2 +
                        Math.sin(angle) *
                        communityRadius;


                    group.forEach(
                        (
                            node,
                            index
                        ) => {

                            const memberAngle =
                                (
                                    index /
                                    Math.max(
                                        group.length,
                                        1
                                    )
                                )
                                *
                                Math.PI *
                                2;


                            const radius =
                                60 +
                                Math.sqrt(
                                    group.length
                                ) * 10;


                            node.x =
                                centerX +
                                Math.cos(
                                    memberAngle
                                ) *
                                radius;


                            node.y =
                                centerY +
                                Math.sin(
                                    memberAngle
                                ) *
                                radius;


                            node.centrality =
                                centrality.get(
                                    node.bioguideId
                                ) || 0;

                        }
                    );

                }
            );

        }


        // -----------------------------------------------------
        // COLLISION ADJUSTMENT
        // -----------------------------------------------------

        for (
            let iteration = 0;
            iteration < 5;
            iteration++
        ) {

            for (
                let i = 0;
                i < nodes.length;
                i++
            ) {

                for (
                    let j = i + 1;
                    j < nodes.length;
                    j++
                ) {

                    const a =
                        nodes[i];

                    const b =
                        nodes[j];


                    const dx =
                        b.x - a.x;

                    const dy =
                        b.y - a.y;


                    const distance =
                        Math.sqrt(
                            dx * dx +
                            dy * dy
                        );


                    const minimumDistance =
                        32;


                    if (
                        distance > 0
                        &&
                        distance <
                        minimumDistance
                    ) {

                        const push =
                            (
                                minimumDistance -
                                distance
                            ) / 2;


                        const nx =
                            dx / distance;

                        const ny =
                            dy / distance;


                        a.x -=
                            nx * push;

                        a.y -=
                            ny * push;


                        b.x +=
                            nx * push;

                        b.y +=
                            ny * push;

                    }

                }

            }

        }


        // -----------------------------------------------------
        // PREPARE EDGES
        // -----------------------------------------------------

        const overviewEdges =
            edges
                .map(edge => ({

                    ...edge,

                    sourceNode:
                        nodes.find(
                            n =>
                                n.bioguideId
                                ===
                                edge.source
                        ),

                    targetNode:
                        nodes.find(
                            n =>
                                n.bioguideId
                                ===
                                edge.target
                        )

                }))
                .filter(
                    e =>
                        e.sourceNode
                        &&
                        e.targetNode
                );


        // -----------------------------------------------------
        // DRAW EDGES
        // -----------------------------------------------------

        const links =
            edgeLayer
                .selectAll("line")
                .data(
                    overviewEdges,
                    d =>
                        `${d.source}-${d.target}`
                )
                .enter()
                .append("line")
                .attr(
                    "class",
                    d =>
                        d.crossParty
                            ? "network-edge cross-party"
                            : "network-edge same-party"
                )
                .attr(
                    "x1",
                    d =>
                        d.sourceNode.x
                )
                .attr(
                    "y1",
                    d =>
                        d.sourceNode.y
                )
                .attr(
                    "x2",
                    d =>
                        d.targetNode.x
                )
                .attr(
                    "y2",
                    d =>
                        d.targetNode.y
                )
                .attr(
                    "opacity",
                    d =>
                        d.sharedBillCount < 10
                            ? 0.8
                            : Math.min(
                                0.65,
                                0.15 +
                                d.sharedBillCount *
                                0.01
                            )
                );


        edgeStyle(links);


        // -----------------------------------------------------
        // DRAW NODES
        // -----------------------------------------------------

        const nodesSelection =
            nodeLayer
                .selectAll("circle")
                .data(
                    nodes,
                    d =>
                        d.bioguideId
                )
                .enter()
                .append("circle")
                .attr(
                    "class",
                    "network-node"
                )
                .attr(
                    "cx",
                    d =>
                        d.x
                )
                .attr(
                    "cy",
                    d =>
                        d.y
                )
                .attr(
                    "r",
                    d =>
                        Math.max(
                            7,
                            Math.min(
                                22,
                                6 +
                                Math.sqrt(
                                    d.centrality ||
                                    0
                                ) *
                                0.8
                            )
                        )
                )
                .attr(
                    "fill",
                    d =>
                        partyColor(
                            d.party
                        )
                )
                .on(
                    "mouseenter",
                    function(event, d) {

                        tooltip
                            .style(
                                "display",
                                "block"
                            )
                            .html(`
                                <strong>${d.name || "Unknown"}</strong><br>
                                ${d.party || ""} ${d.state || ""}<br>
                                Collaboration weight:
                                ${d.centrality || 0}
                            `);

                    }
                )
                .on(
                    "mousemove",
                    function(event) {

                        tooltip
                            .style(
                                "left",
                                `${event.pageX + 12}px`
                            )
                            .style(
                                "top",
                                `${event.pageY + 12}px`
                            );

                    }
                )
                .on(
                    "mouseleave",
                    function() {

                        tooltip
                            .style(
                                "display",
                                "none"
                            );

                    }
                )
                .on(
                    "click",
                    function(event, d) {

                        event.stopPropagation();


                        selectedMemberId =
                            d.bioguideId;


                        showMemberDetails(
                            d,
                            data
                        );


                        highlightMember(
                            d.bioguideId
                        );

                    }
                );


        // -----------------------------------------------------
        // DRAG
        // -----------------------------------------------------

        nodesSelection.call(

            d3.drag()

                .on(
                    "start",
                    function(event, d) {

                        d.fx =
                            d.x;

                        d.fy =
                            d.y;

                    }
                )

                .on(
                    "drag",
                    function(event, d) {

                        d.fx =
                            event.x;

                        d.fy =
                            event.y;


                        d3.select(this)
                            .attr(
                                "cx",
                                d.fx
                            )
                            .attr(
                                "cy",
                                d.fy
                            );


                        links
                            .filter(
                                e =>
                                    e.sourceNode
                                    ===
                                    d
                                    ||
                                    e.targetNode
                                    ===
                                    d
                            )
                            .attr(
                                "x1",
                                e =>
                                    e.sourceNode.x
                            )
                            .attr(
                                "y1",
                                e =>
                                    e.sourceNode.y
                            )
                            .attr(
                                "x2",
                                e =>
                                    e.targetNode.x
                            )
                            .attr(
                                "y2",
                                e =>
                                    e.targetNode.y
                            );

                    }
                )

                .on(
                    "end",
                    function(event, d) {

                        d.fx =
                            null;

                        d.fy =
                            null;

                    }
                )

        );


        // -----------------------------------------------------
        // COMMUNITY LABELS
        // -----------------------------------------------------

        const communityGroups =
            d3.group(
                nodes,
                d =>
                    d.communityId
            );


        communityGroups.forEach(
            (group, communityId) => {

                if (
                    !group.length
                ) {
                    return;
                }


                const centerX =
                    d3.mean(
                        group,
                        d =>
                            d.x
                    );


                const centerY =
                    d3.mean(
                        group,
                        d =>
                            d.y
                    );


                labelLayer
                    .append("text")
                    .attr(
                        "class",
                        "community-label"
                    )
                    .attr(
                        "x",
                        centerX
                    )
                    .attr(
                        "y",
                        centerY - 70
                    )
                    .attr(
                        "text-anchor",
                        "middle"
                    )
                    .text(
                        `Community ${communityId}`
                    );

            }
        );


        // -----------------------------------------------------
        // STATS
        // -----------------------------------------------------

        const crossPartyCount =
            edges.filter(
                e =>
                    e.crossParty
            ).length;


        document.getElementById(
            "networkStats"
        ).textContent =
            `${nodes.length} members • ` +
            `${edges.length} relationships • ` +
            `${crossPartyCount} cross-party`;

    }


    // =========================================================
    // HIGHLIGHT MEMBER
    // =========================================================

    function highlightMember(id) {

        const connectedEdges =
            new Set();


        currentData.edges.forEach(
            edge => {

                if (
                    edge.source === id
                    ||
                    edge.target === id
                ) {

                    connectedEdges.add(
                        `${edge.source}-${edge.target}`
                    );

                    connectedEdges.add(
                        `${edge.target}-${edge.source}`
                    );

                }

            }
        );


        edgeLayer
            .selectAll("line")
            .attr(
                "opacity",
                d => {

                    const key =
                        `${d.source}-${d.target}`;


                    return connectedEdges.has(
                        key
                    )
                        ? 0.9
                        : 0.03;

                }
            );


        nodeLayer
            .selectAll("circle")
            .attr(
                "opacity",
                d =>
                    d.bioguideId === id
                        ? 1
                        : 0.25
            );

    }


    // =========================================================
    // RESET HIGHLIGHT
    // =========================================================

    function resetHighlight() {

        edgeLayer
            .selectAll("line")
            .attr(
                "opacity",
                d =>
                    d.sharedBillCount < 10
                        ? 0.8
                        : Math.min(
                            0.65,
                            0.15 +
                            d.sharedBillCount *
                            0.01
                        )
            );


        nodeLayer
            .selectAll("circle")
            .attr(
                "opacity",
                1
            );

    }


    // =========================================================
    // MEMBER DETAILS
    // =========================================================

    function showMemberDetails(
        member,
        data
    ) {

        document.getElementById(
            "memberEmpty"
        ).style.display =
            "none";


        document.getElementById(
            "memberDetails"
        ).style.display =
            "block";


        document.getElementById(
            "memberName"
        ).textContent =
            member.name ||
            "Unknown";


        document.getElementById(
            "memberPartyState"
        ).textContent =
            `${member.party || ""} ${member.state || ""}`;


        document.getElementById(
            "memberBills"
        ).textContent =
            member.billCount ??
            member.bills ??
            "-";


        document.getElementById(
            "memberCommunity"
        ).textContent =
            member.communityId ??
            "-";


        const connections =
            data.edges.filter(
                e =>
                    e.source ===
                    member.bioguideId
                    ||
                    e.target ===
                    member.bioguideId
            );


        document.getElementById(
            "memberConnections"
        ).textContent =
            connections.length;


        const crossParty =
            connections.filter(
                e =>
                    e.crossParty
            ).length;


        document.getElementById(
            "memberCrossParty"
        ).textContent =
            crossParty;


        // -----------------------------------------------------
        // TOP COLLABORATORS
        // -----------------------------------------------------

        const collaborators =
            connections
                .map(edge => {

                    const otherId =
                        edge.source ===
                        member.bioguideId
                            ? edge.target
                            : edge.source;


                    const other =
                        data.nodes.find(
                            n =>
                                n.bioguideId
                                ===
                                otherId
                        );


                    return {

                        member: other,

                        sharedBillCount:
                            edge.sharedBillCount,

                        crossParty:
                            edge.crossParty

                    };

                })
                .filter(
                    x =>
                        x.member
                )
                .sort(
                    (a, b) =>
                        b.sharedBillCount
                        -
                        a.sharedBillCount
                )
                .slice(
                    0,
                    10
                );


        const container =
            document.getElementById(
                "topCollaborators"
            );


        container.innerHTML =
            "";


        collaborators.forEach(
            item => {

                const div =
                    document.createElement(
                        "div"
                    );


                div.className =
                    "collaborator-item";


                div.innerHTML = `
                    <div>
                        <strong>
                            ${item.member.name || "Unknown"}
                        </strong>
                        <small>
                            ${item.member.party || ""}
                            ${item.member.state || ""}
                        </small>
                    </div>

                    <span>
                        ${item.sharedBillCount}
                    </span>
                `;


                div.addEventListener(
                    "click",
                    () => {

                        selectedMemberId =
                            item.member.bioguideId;


                        showMemberDetails(
                            item.member,
                            data
                        );


                        highlightMember(
                            item.member.bioguideId
                        );

                    }
                );


                container.appendChild(
                    div
                );

            }
        );


        // -----------------------------------------------------
        // FOCUS BUTTON
        // -----------------------------------------------------

        const focusButton =
            document.getElementById(
                "focusMemberButton"
            );


        focusButton.onclick =
            () => {

                selectedMemberId =
                    member.bioguideId;


                currentMode =
                    "members";


                updateModeButtons();


                showMemberNetwork(
                    member.bioguideId
                );

            };


        // -----------------------------------------------------
        // COMMUNITY BUTTON
        // -----------------------------------------------------

        const communityButton =
            document.getElementById(
                "showCommunityButton"
            );


        communityButton.onclick =
            () => {

                const communitySelect =
                    document.getElementById(
                        "communityFilter"
                    );


                communitySelect.value =
                    member.communityId;


                currentMode =
                    "communities";


                updateModeButtons();


                drawCurrentView();

            };

    }


    // =========================================================
    // MEMBER NETWORK
    // =========================================================

    function showMemberNetwork(
        memberId
    ) {

        if (!currentData) {
            return;
        }


        clearGraph();


        const member =
            currentData.nodes.find(
                n =>
                    n.bioguideId ===
                    memberId
            );


        if (!member) {
            return;
        }


        const memberEdges =
            currentData.edges
                .filter(
                    e =>
                        e.source ===
                        memberId
                        ||
                        e.target ===
                        memberId
                )
                .sort(
                    (a, b) =>
                        b.sharedBillCount
                        -
                        a.sharedBillCount
                )
                .slice(
                    0,
                    25
                );


        const relatedIds =
            new Set(
                [memberId].concat(
                    memberEdges.flatMap(
                        e => [
                            e.source,
                            e.target
                        ]
                    )
                )
            );


        const nodes =
            currentData.nodes
                .filter(
                    n =>
                        relatedIds.has(
                            n.bioguideId
                        )
                )
                .map(
                    n => ({
                        ...n
                    })
                );


        const nodeMap =
            new Map(
                nodes.map(
                    n => [
                        n.bioguideId,
                        n
                    ]
                )
            );


        const edges =
            memberEdges
                .map(
                    e => ({

                        ...e,

                        sourceNode:
                            nodeMap.get(
                                e.source
                            ),

                        targetNode:
                            nodeMap.get(
                                e.target
                            )

                    })
                )
                .filter(
                    e =>
                        e.sourceNode
                        &&
                        e.targetNode
                );


        // -----------------------------------------------------
        // FORCE SIMULATION
        // -----------------------------------------------------

        const simulation =
            d3.forceSimulation(
                nodes
            )
                .force(
                    "link",
                    d3.forceLink(
                        edges
                    )
                        .id(
                            d =>
                                d.bioguideId
                        )
                        .distance(
                            d =>
                                Math.max(
                                    60,
                                    180 -
                                    d.sharedBillCount *
                                    2
                                )
                        )
                        .strength(
                            0.6
                        )
                )
                .force(
                    "charge",
                    d3.forceManyBody()
                        .strength(
                            -300
                        )
                )
                .force(
                    "center",
                    d3.forceCenter(
                        width / 2,
                        height / 2
                    )
                )
                .force(
                    "collision",
                    d3.forceCollide()
                        .radius(
                            28
                        )
                );


        // -----------------------------------------------------
        // EDGES
        // -----------------------------------------------------

        const link =
            edgeLayer
                .selectAll("line")
                .data(edges)
                .enter()
                .append("line")
                .attr(
                    "class",
                    d =>
                        d.crossParty
                            ? "network-edge cross-party"
                            : "network-edge same-party"
                )
                .attr(
                    "opacity",
                    d =>
                        d.sharedBillCount < 10
                            ? 0.8
                            : 0.65
                );


        edgeStyle(link);


        // -----------------------------------------------------
        // NODES
        // -----------------------------------------------------

        const node =
            nodeLayer
                .selectAll("circle")
                .data(nodes)
                .enter()
                .append("circle")
                .attr(
                    "class",
                    "network-node"
                )
                .attr(
                    "r",
                    d =>
                        d.bioguideId ===
                        memberId
                            ? 22
                            : 10
                )
                .attr(
                    "fill",
                    d =>
                        partyColor(
                            d.party
                        )
                )
                .on(
                    "mouseenter",
                    function(event, d) {

                        tooltip
                            .style(
                                "display",
                                "block"
                            )
                            .html(`
                                <strong>${d.name || "Unknown"}</strong><br>
                                ${d.party || ""} ${d.state || ""}
                            `);

                    }
                )
                .on(
                    "mousemove",
                    function(event) {

                        tooltip
                            .style(
                                "left",
                                `${event.pageX + 12}px`
                            )
                            .style(
                                "top",
                                `${event.pageY + 12}px`
                            );

                    }
                )
                .on(
                    "mouseleave",
                    function() {

                        tooltip
                            .style(
                                "display",
                                "none"
                            );

                    }
                )
                .on(
                    "click",
                    function(event, d) {

                        event.stopPropagation();


                        selectedMemberId =
                            d.bioguideId;


                        showMemberDetails(
                            d,
                            currentData
                        );

                    }
                );


        // -----------------------------------------------------
        // FIX CENTER MEMBER
        // -----------------------------------------------------

        member.fx =
            width / 2;

        member.fy =
            height / 2;


        // -----------------------------------------------------
        // SIMULATION
        // -----------------------------------------------------

        simulation.on(
            "tick",
            () => {

                link
                    .attr(
                        "x1",
                        d =>
                            d.source.x
                    )
                    .attr(
                        "y1",
                        d =>
                            d.source.y
                    )
                    .attr(
                        "x2",
                        d =>
                            d.target.x
                    )
                    .attr(
                        "y2",
                        d =>
                            d.target.y
                    );


                node
                    .attr(
                        "cx",
                        d =>
                            d.x
                    )
                    .attr(
                        "cy",
                        d =>
                            d.y
                    );

            }
        );


        // -----------------------------------------------------
        // DRAG
        // -----------------------------------------------------

        node.call(

            d3.drag()

                .on(
                    "start",
                    function(event, d) {

                        if (
                            !event.active
                        ) {

                            simulation
                                .alphaTarget(
                                    0.3
                                )
                                .restart();

                        }


                        d.fx =
                            d.x;

                        d.fy =
                            d.y;

                    }
                )

                .on(
                    "drag",
                    function(event, d) {

                        d.fx =
                            event.x;

                        d.fy =
                            event.y;

                    }
                )

                .on(
                    "end",
                    function(event, d) {

                        if (
                            !event.active
                        ) {

                            simulation
                                .alphaTarget(
                                    0
                                );

                        }


                        if (
                            d.bioguideId
                            !==
                            memberId
                        ) {

                            d.fx =
                                null;

                            d.fy =
                                null;

                        }

                    }
                )

        );


        document.getElementById(
            "networkStats"
        ).textContent =
            `${nodes.length} members • ` +
            `${edges.length} relationships`;

    }


    // =========================================================
    // MODE BUTTONS
    // =========================================================

    function updateModeButtons() {

        document
            .querySelectorAll(
                ".view-button"
            )
            .forEach(
                button =>
                    button.classList.remove(
                        "active"
                    )
            );


        if (
            currentMode ===
            "overview"
        ) {

            document
                .getElementById(
                    "overviewMode"
                )
                .classList.add(
                    "active"
                );

        }
        else if (
            currentMode ===
            "communities"
        ) {

            document
                .getElementById(
                    "communityMode"
                )
                .classList.add(
                    "active"
                );

        }
        else if (
            currentMode ===
            "members"
        ) {

            document
                .getElementById(
                    "memberMode"
                )
                .classList.add(
                    "active"
                );

        }

    }


    // =========================================================
    // BUTTON EVENTS
    // =========================================================

    document
        .getElementById(
            "overviewMode"
        )
        .addEventListener(
            "click",
            () => {

                currentMode =
                    "overview";

                selectedMemberId =
                    null;

                updateModeButtons();

                resetHighlight();

                drawCurrentView();

            }
        );


    document
        .getElementById(
            "communityMode"
        )
        .addEventListener(
            "click",
            () => {

                currentMode =
                    "communities";

                selectedMemberId =
                    null;

                updateModeButtons();

                resetHighlight();

                drawCurrentView();

            }
        );


    document
        .getElementById(
            "memberMode"
        )
        .addEventListener(
            "click",
            () => {

                if (
                    selectedMemberId
                ) {

                    currentMode =
                        "members";

                    updateModeButtons();

                    showMemberNetwork(
                        selectedMemberId
                    );

                }

            }
        );


    document
        .getElementById(
            "loadNetwork"
        )
        .addEventListener(
            "click",
            () => {

                currentMode =
                    "overview";

                selectedMemberId =
                    null;

                updateModeButtons();

                loadNetwork();

            }
        );


    document
        .getElementById(
            "overviewButton"
        )
        .addEventListener(
            "click",
            () => {

                currentMode =
                    "overview";

                selectedMemberId =
                    null;

                updateModeButtons();


                document.getElementById(
                    "partyFilter"
                ).value =
                    "ALL";


                document.getElementById(
                    "communityFilter"
                ).value =
                    "";


                resetHighlight();

                drawCurrentView();

            }
        );


    // =========================================================
    // BACKGROUND CLICK
    // =========================================================

    svg.on(
        "click",
        () => {

            selectedMemberId =
                null;

            resetHighlight();

        }
    );


    // =========================================================
    // INITIAL LOAD
    // =========================================================

    loadNetwork();

})();