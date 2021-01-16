import graphviz as gv
import re

from .action import Action, ActionCluster


COLOR_TGA = "#00008b"
COLOR_CLOSEST_ACTION = "#c9211e"
COLOR_LAST_ADDED_ACTION = "#008000"


ACTION_NODE_STYLE = {
    "fontname": "Arial",
    "shape": "none",
    "margin": "0",
    "fontcolor": "black"
}

CLUSTER_NODE_STYLE = {
    "fontname": "Arial",
    "shape": "none",
    "margin": "0",
    "fontcolor": "white",
    "penwidth": "0",
}

COARSE_ACTION_NODE_STYLE = {
    "shape": "square",
    "width": "0.5",
    "fixedsize": "true",
    "style": "filled",
}

COARSE_CLUSTER_NODE_STYLE = {
    "shape": "square",
    "width": "0.25",
    "fixedsize": "true",
    "style": "filled",
    "fillcolor": "black",
    "penwidth": "0",
}


ACTION_NODE_TMP = \
    '<<table color="{color}" style="rounded" border="{border}" cellborder="0" cellspacing="4" cellpadding="3">'\
        '<tr>'\
            '<td style="rounded" align="center" bgcolor="{color}">'\
                '<font color="white"><b>{action_name}</b></font>'\
            '</td>'\
        '</tr>'\
        '<tr>'\
            '<td valign="top" align="left" balign="left">'\
                '<b>params:</b><br/>{action_params}'\
            '</td>'\
        '</tr>'\
        '<tr>'\
            '<td valign="top" align="left" balign="left">'\
                '<b>pre:</b><br/>{action_pre}'\
            '</td>'\
        '</tr>'\
        '<tr>'\
            '<td valign="top" align="left" balign="left">'\
                '<b>add:</b><br/>{action_add}'\
            '</td>'\
        '</tr>'\
        '<tr>'\
            '<td valign="top" align="left" balign="left">'\
                '<b>del:</b><br/>{action_del}'\
            '</td>'\
        '</tr>'\
    '</table>>'


CLUSTER_NODE_TMP = \
    '<<table bgcolor="black" style="rounded" border="0" cellborder="0" cellspacing="4" cellpadding="3">'\
        '<tr>'\
            '<td style="rounded" align="center">'\
                '<b>{cluster_name} </b>'\
            '</td>'\
        '</tr>'\
        '<tr>'\
            '<td style="rounded" align="left">'\
                '<b>dist.:  </b> {cluster_distance:.02f}'\
            '</td>'\
        '</tr>'\
    '</table>>'


def action_key(action):
    if action.name.startswith("action-"):
        return int(action.name[len("action-"):])
    return action.name 


def flatten(actions):
    flat_actions = []
    stack = actions[:]
    while stack:
        item = stack.pop()
        if isinstance(item, Action):
            flat_actions.append(item)
            if item.parent is not None:
                stack.append(item.parent.left_parent)
                stack.append(item.parent.right_parent)
    flat_actions.sort(key=action_key)
    flat_clusters = [a.parent for a in flat_actions if a.parent is not None]
    return flat_actions, flat_clusters


def _wrap_text_count_chars(word, inside_tag=False):
    count = 0
    for c in word:
        if c == "<":
            inside_tag = True
        elif c == ">":
            inside_tag = False
        elif not inside_tag:
            count += 1
    return count, inside_tag


def wrap_text(text, max_length=72, initial_break=False):
    words = text.split()
    line = []
    line_len = 0
    wrapped_lines = []
    inside_tag = False
    for word in words:
        word_len, inside_tag = _wrap_text_count_chars(word, inside_tag)
        count_ws = 1 if word_len > 0 and line_len > 0 else 0
        if line_len + count_ws + word_len <= max_length:
            line.append(word)
            line_len += count_ws + word_len
        else:
            wrapped_lines.append(" ".join(line))
            line = [word]
            line_len = word_len
    if line:
        wrapped_lines.append(" ".join(line))
    return "<br/>".join(wrapped_lines)


    # for i in range(len(wrapped_lines)):
        # wrapped_lines[i] = wrapped_lines[i].replace("</b>", "  </b>")
def format_atom_list(atom_list, atom_limit=1000, line_len=40):
    if not atom_list:
        text = "&lt;<i>empty</i>&gt;"
    elif atom_limit > 0:
        text = ", ".join(str(atom) for atom in atom_list[:atom_limit])
        if atom_limit < len(atom_list):
            text += f" &lt;<i>{len(atom_list) - atom_limit} more</i>&gt;"
    else:
        text = f"&lt;<i>{len(atom_list)} atom(s)</i>&gt;"
    wrapped_text = wrap_text(text, max_length=line_len)
    return wrapped_text


def draw_action_node(g, action, atom_limit=1000, line_len=40, highlight=False,
        color="black"):
    label = ACTION_NODE_TMP.format(
        color=color,
        action_name=action.name,
        border=4 if highlight else 1,
        action_params=wrap_text(", ".join(action.get_parameters()), max_length=line_len),
        action_pre=format_atom_list(action.get_features_of_type("pre"), atom_limit=atom_limit, line_len=line_len),
        action_add=format_atom_list(action.get_features_of_type("add"), atom_limit=atom_limit, line_len=line_len),
        action_del=format_atom_list(action.get_features_of_type("del"), atom_limit=atom_limit, line_len=line_len))
    g.node(action.name, label=label)


def draw_cluster_node(g, cluster):
    label = CLUSTER_NODE_TMP.format(cluster_name=cluster.name, cluster_distance=cluster.distance)
    g.node(cluster.name, label=label)


def action_color_dict(flat_actions):
    colors = {}
    last_added_action = flat_actions[-1]
    colors[last_added_action.name] = COLOR_LAST_ADDED_ACTION
    if last_added_action.parent:
        # OARU always stores the previous closest action in the left parent
        # and the TGA generated from the transition in the right parent
        closest = last_added_action.parent.left_parent
        tga = last_added_action.parent.right_parent
        colors[closest.name] = COLOR_CLOSEST_ACTION
        colors[tga.name] = COLOR_TGA
    return colors


def draw_cluster_graph(top_actions, line_len=30, atom_limit_top=1000, atom_limit_middle=2,
        highlight_top=True, highlight_last_actions=False, rankdir="BT"):
    g = gv.Graph("g")
    g.attr(fontname="Arial")
    g.attr(rankdir=rankdir)
    flat_actions, flat_clusters = flatten(top_actions)
    colors = action_color_dict(flat_actions) if highlight_last_actions else {}
    middle_actions = [act for act in flat_actions if act not in top_actions]
    g.attr("node", **ACTION_NODE_STYLE)
    with g.subgraph(name="cluster_actionlib") as s:
        s.attr(rank="same", label="<<b>Action library</b>>")
        for action in top_actions:
            draw_action_node(s, action, atom_limit=atom_limit_top, line_len=line_len,
                    color=colors.get(action.name,"black"), highlight=highlight_top)
    for action in middle_actions:
        draw_action_node(g, action, atom_limit=atom_limit_middle,
                color=colors.get(action.name,"black"), line_len=line_len)
    g.attr("node", **CLUSTER_NODE_STYLE)
    for cluster in flat_clusters:
        draw_cluster_node(g, cluster)
    for action in flat_actions:
        if action.parent:
            g.edge(action.parent.name, action.name)
    for cluster in flat_clusters:
        g.edge(cluster.left_parent.name, cluster.name)
        g.edge(cluster.right_parent.name, cluster.name)
    return g


def draw_coarse_cluster_graph(top_actions, highlight_top=True,
        highlight_last_actions=False, rankdir="BT"):
    g = gv.Graph("g")
    g.attr(rankdir=rankdir)
    flat_actions, flat_clusters = flatten(top_actions)
    colors = action_color_dict(flat_actions) if highlight_last_actions else {}
    middle_actions = [act for act in flat_actions if act not in top_actions]
    g.attr("node", **COARSE_ACTION_NODE_STYLE)
    with g.subgraph(name="cluster_actionlib") as s:
        s.attr(rank="same")
        for action in top_actions:
            s.node(action.name, label="", fillcolor=colors.get(action.name,"white"),
                    penwidth="4" if highlight_top else "1")
    for action in middle_actions:
        g.node(action.name, label="", fillcolor=colors.get(action.name,"white"))
    g.attr("node", **COARSE_CLUSTER_NODE_STYLE)
    for cluster in flat_clusters:
        g.node(cluster.name, label="")
    for action in flat_actions:
        if action.parent:
            g.edge(action.parent.name, action.name)
    for cluster in flat_clusters:
        g.edge(cluster.left_parent.name, cluster.name)
        g.edge(cluster.right_parent.name, cluster.name)
    return g


if __name__ == "__main__":
    from .feature import Feature
    action1 = Action("action-1", [Feature(("on", "x", "y"))])
    action2 = Action("action-2", [])
    action3 = Action("action-3", [])
    action4 = Action("action-4", [])
    action5 = Action("action-5", [])
    action6 = Action("action-6", [])
    cluster1 = ActionCluster(action1, action2, 0)
    cluster2 = ActionCluster(action3, action4, 0)
    action3.parent = cluster1
    action5.parent = cluster2
    actions = [action5, action6]
    g = draw_cluster_graph(actions, highlight_last_actions=True)
    g.render("g.gv", view=True, cleanup=True)
