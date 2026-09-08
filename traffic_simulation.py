import networkx as nx


def create_road_network(roads):
    """
    Creates a graph representing the road network.
    """

    graph = nx.Graph()

    for _, road in roads.iterrows():

        graph.add_edge(
            road["start_node"],
            road["end_node"],
            road_id=road["road_id"],
            road_name=road["road_name"]
        )

    return graph


def find_connected_roads(roads, selected_road_id):
    """
    Finds roads directly connected to the selected road.
    """

    selected_road = roads[
        roads["road_id"] == selected_road_id
    ].iloc[0]

    start_node = selected_road["start_node"]
    end_node = selected_road["end_node"]

    connected = roads[
        (
            (roads["start_node"] == start_node) |
            (roads["end_node"] == start_node) |
            (roads["start_node"] == end_node) |
            (roads["end_node"] == end_node)
        )
        &
        (roads["road_id"] != selected_road_id)
    ]

    return connected


def find_roads_within_hops(roads, selected_road_id, max_hops):
    """
    Finds roads within a specified number of network hops
    from the selected road.
    """

    graph = create_road_network(roads)

    selected_road = roads[
        roads["road_id"] == selected_road_id
    ].iloc[0]

    start_node = selected_road["start_node"]
    end_node = selected_road["end_node"]

    # Find nodes reachable from both ends

    reachable_nodes = set()

    for node in [start_node, end_node]:

        try:

            lengths = nx.single_source_shortest_path_length(
                graph,
                node,
                cutoff=max_hops
            )

            reachable_nodes.update(
                lengths.keys()
            )

        except nx.NetworkXError:
            pass

    affected_roads = []

    for _, road in roads.iterrows():

        if road["road_id"] == selected_road_id:
            continue

        if (
            road["start_node"] in reachable_nodes
            or
            road["end_node"] in reachable_nodes
        ):
            affected_roads.append(
                road["road_id"]
            )

    return affected_roads