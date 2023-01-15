

from .openworld import Action
from .directed_weighted_graph import DirectedWeightedGraph


class BasicObjectFilter:
    def __init__(self, constants=None):
        self.constants = constants

    def __call__(self, action):
        affected_objects = action.get_referenced_objects(sections=["add","del"])
        if self.constants is not None:
            affected_objects.update(self.constants)
        latoms = [latom for latom in action.atoms if affected_objects.issuperset(latom.atom.args)]
        return Action(action.name, action.parameters, latoms)


def default_edge_creator(graph, latom):
    args = latom.atom.args
    for i, u in enumerate(args):
        for v in args[i+1:]:
            graph.add_edge(u, v, 1)
            graph.add_edge(v, u, 1)


def create_object_graph(action, edge_creator=default_edge_creator):
    graph = DirectedWeightedGraph()
    for latom in action.atoms:
        edge_creator(graph, latom)
    return graph


class ObjectGraphFilter:
    def __init__(self, max_distance, fn=max, edge_creator=default_edge_creator, root_objects=None):
        self.edge_creator = edge_creator
        self.max_distance = max_distance
        self.root_objects = root_objects
        self.fn = fn

    def __call__(self, action):
        object_graph = create_object_graph(action, self.edge_creator)
        
        root_objects = self.root_objects or action.get_referenced_objects(
            sections=["add", "del"])
        object_graph.add_node("root_objects")
        for obj in root_objects:
            object_graph.add_edge("root_objects", obj, 0)
        
        distances = object_graph.dijkstra("root_objects")
        filtered_latoms = []
        for latom in action.atoms:
            score = self.fn((distances[arg] for arg in latom.atom.args), default=0)
            if score <= self.max_distance:
                filtered_latoms.append(latom)
        return Action(action.name, atoms=filtered_latoms)



