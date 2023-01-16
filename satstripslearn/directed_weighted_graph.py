from heapq import heappop, heappush

INF = 2147483647 # Just some big number

class DirectedWeightedGraph:

    def __init__(self, nodes=None, edges=None):
        self.nodes = nodes or set()
        self.edges = edges or {}

    def get_adjacency_list(self):
        adjacency = {u:[] for u in self.nodes}
        for (u,v),w in self.edges.items():
            adjacency[u].append((v,w))
        return adjacency

    def add_node(self, u):
        self.nodes.add(u)

    def add_edge(self, u, v, w):
        self.nodes.add(u)
        self.nodes.add(v)
        old_weight = self.edges.get((u,v), INF)
        self.edges[(u,v)] = min(old_weight, w)

    def dijkstra(self, start):
        adjacency = self.get_adjacency_list()
        distance = {u:INF for u in self.nodes}
        distance[start] = 0
        openset = [(0,start)]
        closedset = set()
        while openset:
            dist_u, u = heappop(openset)
            if u in closedset:
                # this is an outdated element in the heap
                continue
            closedset.add(u)
            for v, w in adjacency[u]:
                dist_v = dist_u + w
                if dist_v < distance[v]:
                    distance[v] = dist_v
                    heappush(openset, (dist_v, v))
        return distance

    def dot(self):
        import graphviz as gv
        g = gv.Digraph()
        for u in self.nodes:
            g.node(str(u))
        for (u,v),w in self.edges.items():
            g.edge(str(u), str(v), label=str(w))
        return g
