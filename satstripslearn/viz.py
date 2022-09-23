import graphviz as gv

from .strips import _untyped_objlist_to_pddl

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
            '<td style="rounded" align="left">'\
                '<b>dist.:  </b> {cluster_distance:.02f}'\
            '</td>'\
        '</tr>'\
        '<tr>'\
            '<td style="rounded" align="center">'\
                '<b>norm. dist.: </b> {norm_distance:.02f} '\
            '</td>'\
        '</tr>'\
    '</table>>'


def action_key(action):
    name = action.action.name
    if name.startswith("action-"):
        return int(name[len("action-"):])
    return 0


def flatten(actions):
    flat_actions = []
    stack = actions[:]
    while stack:
        item = stack.pop()
        flat_actions.append(item)
        if not item.is_tga():
            stack.append(item.left_parent)
            stack.append(item.right_parent)
    flat_actions.sort(key=action_key)
    return flat_actions


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
        text = ", ".join(atom.to_str(False, False) for atom in atom_list[:atom_limit])
        if atom_limit < len(atom_list):
            text += f" &lt;<i>{len(atom_list) - atom_limit} more</i>&gt;"
    else:
        text = f"&lt;<i>{len(atom_list)} atom(s)</i>&gt;"
    wrapped_text = wrap_text(text, max_length=line_len)
    return wrapped_text


def draw_action_node(g, action, atom_limit=1000, line_len=40, highlight=False,
        color="black"):
    action = action.action
    label = ACTION_NODE_TMP.format(
        color=color,
        action_name=action.name,
        border=4 if highlight else 1,
        action_params=wrap_text(_untyped_objlist_to_pddl(action.parameters), max_length=line_len),
        action_pre=format_atom_list(action.get_atoms_in_section("pre"), atom_limit=atom_limit, line_len=line_len),
        action_add=format_atom_list(action.get_atoms_in_section("add"), atom_limit=atom_limit, line_len=line_len),
        action_del=format_atom_list(action.get_atoms_in_section("del"), atom_limit=atom_limit, line_len=line_len))
    g.node(action.name, label=label)


def draw_cluster_node(g, cluster):
    label = CLUSTER_NODE_TMP.format(cluster_distance=cluster.distance,
                                    norm_distance=cluster.normalized_distance)
    g.node("cluster-" + cluster.action.name, label=label)


def action_color_dict(flat_actions):
    colors = {}
    last_added_action = flat_actions[-1]
    colors[last_added_action.action.name] = COLOR_LAST_ADDED_ACTION
    if not last_added_action.is_tga():
        # OARU always stores the previous closest action in the left parent
        # and the TGA generated from the transition in the right parent
        closest = last_added_action.left_parent
        tga = last_added_action.right_parent
        colors[closest.action.name] = COLOR_CLOSEST_ACTION
        colors[tga.action.name] = COLOR_TGA
    return colors


def draw_cluster_graph(top_actions, line_len=30, atom_limit_top=1000, atom_limit_middle=2,
        highlight_top=True, highlight_last_actions=False, rankdir="BT"):
    g = gv.Graph("g")
    g.attr(fontname="Arial")
    g.attr(rankdir=rankdir)
    flat_actions = flatten(top_actions)
    colors = action_color_dict(flat_actions) if highlight_last_actions else {}
    middle_actions = [act for act in flat_actions if act not in top_actions]
    g.attr("node", **ACTION_NODE_STYLE)
    # for action in top_actions:
        # draw_action_node(g, action, atom_limit=atom_limit_top, line_len=line_len,
                # color=colors.get(action.name,"black"), highlight=highlight_top)
    with g.subgraph(name="cluster_actionlib") as s:
        s.attr(rank="same", label="<<b>Action library</b>>")
        for action in top_actions:
            draw_action_node(s, action, atom_limit=atom_limit_top, line_len=line_len,
                    color=colors.get(action.action.name,"black"), highlight=highlight_top)
    for action in middle_actions:
        draw_action_node(g, action, atom_limit=atom_limit_middle,
                color=colors.get(action.action.name,"black"), line_len=line_len)
    g.attr("node", **CLUSTER_NODE_STYLE)
    clusters = [action for action in flat_actions if not action.is_tga()]
    for cluster in clusters:
        draw_cluster_node(g, cluster)
    for action in flat_actions:
        if not action.is_tga():
            left_parent = action.left_parent.action.name
            right_parent = action.right_parent.action.name
            cluster = "cluster-" + action.action.name
            g.edge(left_parent, cluster)
            g.edge(right_parent, cluster)
            g.edge(cluster, action.action.name)
    return g


def draw_coarse_cluster_graph(top_actions, highlight_top=True,
        highlight_last_actions=False, rankdir="BT"):
    g = gv.Graph("g")
    g.attr(rankdir=rankdir)
    flat_actions = flatten(top_actions)
    colors = action_color_dict(flat_actions) if highlight_last_actions else {}
    middle_actions = [act for act in flat_actions if act not in top_actions]
    g.attr("node", **COARSE_ACTION_NODE_STYLE)
    with g.subgraph(name="cluster_actionlib") as s:
        s.attr(rank="same")
        for action in top_actions:
            s.node(action.action.name, label="", fillcolor=colors.get(action.action.name,"white"),
                    penwidth="4" if highlight_top else "1")
    for action in middle_actions:
        g.node(action.action.name, label="", fillcolor=colors.get(action.action.name,"white"))
    g.attr("node", **COARSE_CLUSTER_NODE_STYLE)
    clusters = [action for action in flat_actions if not action.is_tga()]
    for cluster in clusters:
        g.node("cluster-" + cluster.action.name, label="")
    for action in flat_actions:
        if not action.is_tga():
            left_parent = action.left_parent.action.name
            right_parent = action.right_parent.action.name
            cluster = "cluster-" + action.action.name
            g.edge(left_parent, cluster)
            g.edge(right_parent, cluster)
            g.edge(cluster, action.action.name)
    return g


# if __name__ == "__main__":
    # from .feature import Feature

    # a1 = Action("move-odd-piece-right",
            # [
                # Feature(("at", "Token", "Source"), feature_type="pre"),
                # Feature(("odd", "Token"), feature_type="pre"),
                # Feature(("empty", "Destination"), feature_type="pre"),
                # Feature(("right", "Source", "Destination"), feature_type="pre"),
                
                # Feature(("at", "Token", "Destination"), feature_type="add"),
                # Feature(("empty", "Source"), feature_type="add"),

                # Feature(("at", "Token", "Source"), feature_type="del"),
                # Feature(("empty", "Destination"), feature_type="del"),
            # ], parameters_in_canonical_order=["Token","Source","Destination"])
    # a2 = Action("move-even-piece-up",
            # [
                # Feature(("at", "Token", "Source"), feature_type="pre"),
                # Feature(("even", "Token"), feature_type="pre"),
                # Feature(("empty", "Destination"), feature_type="pre"),
                # Feature(("up", "Source", "Destination"), feature_type="pre"),
                
                # Feature(("at", "Token", "Destination"), feature_type="add"),
                # Feature(("empty", "Source"), feature_type="add"),

                # Feature(("at", "Token", "Source"), feature_type="del"),
                # Feature(("empty", "Destination"), feature_type="del"),
            # ], parameters_in_canonical_order=["Token","Source","Destination"])

    # g = draw_cluster_graph([a1, a2], line_len=60, highlight_top=False, rankdir="LR")
    # g.render("example_split", view=True, cleanup=True)

    # action1 = Action("action-1", [Feature(("on", "x", "y"))])
    # action2 = Action("action-2", [])
    # action3 = Action("action-3", [])
    # action4 = Action("action-4", [])
    # action5 = Action("action-5", [])
    # action6 = Action("action-6", [])
    # cluster1 = ActionCluster(action1, action2, 0)
    # cluster2 = ActionCluster(action3, action4, 0)
    # action3.parent = cluster1
    # action5.parent = cluster2
    # actions = [action5, action6]
    # g = draw_cluster_graph(actions, highlight_last_actions=True)
    # g.render("g.gv", view=True, cleanup=True)
