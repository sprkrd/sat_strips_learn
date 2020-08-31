from collections import deque

from .utils import INF


class UndirectedGraph:
    """
    Utility class that represents an undirected graph.

    Parameters
    ----------
    nodes: list
        The set of nodes of this graph
    edges: iterable
        a sequence of tuples (u,v) that represent the edges of the graph. This
        sequence must be clean of duplicates.
    """

    def __init__(self, nodes, edges):
        """
        See help(type(self)) for accurate signature.
        """
        self.nodes = nodes
        self.edges = edges
        adjacency = {u:[] for u in nodes}
        for u,v in edges:
            adjacency[u].append(v)
            adjacency[v].append(u)
        self.adjacency = adjacency

    def bfs(self, startset):
        """
        Breadth First Search to calculate the distance from a set of starting
        nodes to the rest of nodes in the graph.

        Parameters
        ----------
        startset: any iterable
            the set of starting nodes

        Returns
        -------
        out : dict
            A dictionary from nodes to the distance to these nodes from the
            starting set.
        """
        openset = deque((0,node) for node in startset)
        closedset = {}
        while openset:
            level,u = openset.popleft()
            if u not in closedset:
                closedset[u] = level
                for v in self.adjacency[u]:
                    openset.append((level+1, v))
        for node in self.nodes:
            closedset.setdefault(node, INF)
        return closedset

    def __str__(self):
        lines = ["UndirectedGraph{"]
        for u,adjacent in self.adjacency.items():
            lines.append(f"  {u} -> {', '.join(adjacent)}")
        lines.append("}")
        return "\n".join(lines)
