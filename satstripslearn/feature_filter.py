

from .action import Action
from .directed_weighted_graph import DirectedWeightedGraph


def insert_and_simplify(edges, edge, w):
    try:
        w = min(edges[edge], w)
    except KeyError:
        pass
    edges[edge] = w


def merge_and_simplify(edges, edges_out=None):
    if edges_out is None:
        edges_out = edges.copy()
    else:
        for edge, weight in edges.items():
            insert_and_simplify(edges_out, edge, weight)
    return edges_out


def default_edge_creator(atom, atom_type):
    edges = {}
    for i in range(1,len(atom)):
        for j in range(i+1,len(atom)):
            uv = (atom[i], atom[j])
            vu = (atom[j], atom[i])
            edges[uv] = 1
            edges[vu] = 1
    return edges


def create_object_graph(action, edge_creator=default_edge_creator):
    grouped_features = action.get_grouped_features()
    atoms = {}
    for _,feat in grouped_features["pre"]:
        atoms[feat.atom] = "active"
    for _,feat in grouped_features["add"]:
        atoms[feat.atom] = "added"
    for _,feat in grouped_features["del"]:
        atoms[feat.atom] = "deleted"

    nodes = action.get_referenced_objects(as_set=True)
    edges = {}

    for atom, atom_type in atoms.items():
        new_edges = edge_creator(atom, atom_type)
        merge_and_simplify(new_edges, edges)

    return DirectedWeightedGraph(nodes, edges)


def basic_object_filter(action):
    affected_objects = action.get_referenced_objects(feature_types=["add","del"], as_set=True)
    filtered_features = []
    for feat in action.features:
        if all(arg in affected_objects for arg in feat.arguments):
            filtered_features.append(feat)
    return Action(action.name, filtered_features, action.parent)


class ObjectGraphFilter:
    def __init__(self, max_distance, edge_creator=default_edge_creator, root_objects=None):
        self.edge_creator = edge_creator
        self.max_distance = max_distance
        self.root_objects = root_objects

    def __call__(self, action):
        object_graph = create_object_graph(action, self.edge_creator)
        
        root_objects = self.root_objects or action.get_referenced_objects(
            feature_types=["add", "del"], as_set=True)
        object_graph.add_node("root_objects")
        for obj in root_objects:
            object_graph.add_edge("root_objects", obj, 0)
        
        distances = object_graph.dijkstra("root_objects")
        filtered_features = []
        for feat in action.features:
            feat_score = max((distances[arg] for arg in feat.arguments), default=0)
            if feat_score <= self.max_distance:
                filtered_features.append(feat)
        return Action(action.name, filtered_features, action.parent)



