from heapq import heappop, heappush

INF = 2147483647 # Just some big number

class DirectedWeightedGraph:

    def __init__(self, nodes, edges):
        adjacency = {u:[] for u in nodes}
        for (u,v),w in edges.items():
            adjacency[u].append((v,w))
        self._adjacency = adjacency

    def get_nodes(self):
        return list(self._adjacency.keys())

    def get_edges(self):
        edges = {}
        for u,adjacent in self._adjacency.items():
            for v,w in adjacent:
                edges[(u,v)] = w
        return edges

    def add_node(self, u):
        self._adjacency.setdefault(u, [])

    def add_edge(self, u, v, w):
        self._adjacency[u].append((v,w))

    def dijkstra(self, start):
        distance = {u:INF for u in self._adjacency}
        distance[start] = 0
        openset = [(0,start)]
        closedset = set()
        while openset:
            dist_u, u = heappop(openset)
            if u in closedset:
                # this is an outdated element in the heap
                continue
            closedset.add(u)
            for v, w in self._adjacency[u]:
                dist_v = dist_u + w
                if dist_v < distance[v]:
                    distance[v] = dist_v
                    heappush(openset, (dist_v, v))
        return distance

    def dot(self):
        import graphviz as gv
        g = gv.Digraph()
        for u in self._adjacency:
            g.node(u)
        for (u,v),w in self.get_edges().items():
            g.edge(u, v, label=str(w))
        return g

