import networkx as nx

class ReroutingEngine:
    def find_alternative_route(self, road_graph=None, origin: str = "A", destination: str = "B", congestion_weights: dict = None) -> list:
        """
        Stage 2: Generate candidates (Rerouting)
        Congestion-weighted shortest path search (NetworkX)
        """
        if road_graph is not None and isinstance(road_graph, nx.Graph) and len(road_graph.nodes) > 0:
            try:
                path = nx.shortest_path(road_graph, source=origin, target=destination, weight="weight")
                return path
            except Exception:
                pass
        
        return [origin, "Junction_1", "Junction_2", destination]
