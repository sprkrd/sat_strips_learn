import graphviz as gv

from .action import Action, ActionCluster


def flatten_actions(actions):
    flatten = []
    stack = actions[:]
    while stack:
        act = stack.pop()
        flatten.append(act)
        if isinstance(act, ActionCluster):
            stack.append(act.left)
            stack.append(act.right)
    flatten.sort(key=lambda a: a.name)
    return flatten


def draw_action_node(g, action):
    pass


ACTION_NODE_STYLE = {
    "style": "filled, bold",
    "penwidth": "1",
    "fillcolor": "white",
    "fontname": "mono",
    "shape": "Mrecord"
}


def build_cluster_graph(actions):
    g = gv.Graph("g")
    g.attr("node", **ACTION_NODE_STYLE)
    g.node("V", label='<<table border="0" cellborder="0" cellpadding="3"><tr><td colspan="2">action</td></tr><tr><td align="left">params</td><td align="left">?x ?y</td></tr><tr><td align="left">pre</td><td align="left">(p ?x ?y)<br align="left"/>(q ?y)<br align="left"/></td></tr><tr><td align="left">add</td><td align="left">(r ?y)</td></tr><tr><td align="left">del</td><td align="left">(p ?x ?y) (q ?y)</td></tr></table>>')

    # g.attr(rankdir="BT")
    # all_actions = flatten_actions(actions)
    # print(all_actions)
    # for act in all_actions:
        # g.node(act.name, label=act.name)
    # for act in all_actions:
        # if isinstance(act, ActionCluster):
            # g.edge(act.left.name, act.name)
            # g.edge(act.right.name, act.name)
    return g


if __name__ == "__main__":
    action1 = Action("action-1", [], [], [])
    action2 = Action("action-2", [], [], [])
    action3 = Action("action-3", [], [], [])
    action4 = Action("action-4", [], [], [])
    action5 = Action("action-5", [], [], [])
    action6 = Action("action-6", [], [], [])
    action7 = Action("action-7", [], [], [])
    action8 = ActionCluster(action2, action3, action4, 0)
    action9 = ActionCluster(action8, action5, action6, 0)
    actions = [action1, action7, action9]

    g = build_cluster_graph(actions)
    g.render("g.gv", view=True)

