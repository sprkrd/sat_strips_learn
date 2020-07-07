import graphviz as gv
import re

from .action import Action, ActionCluster


ACTION_NODE_STYLE = {
    "style": "filled, bold",
    "penwidth": "1",
    "fillcolor": "white",
    "fontname": "sans",
    "shape": "none",
    "margin": "0"
}


ACTION_NODE_TMP = \
    '<<table style="rounded" border="1" cellborder="0" cellspacing="4" cellpadding="3">'\
        '<tr>'\
            '<td style="rounded" cellpadding="3" align="center" bgcolor="black">'\
                '<font color="white">{action_name}</font>'\
            '</td>'\
        '</tr>'\
        '<tr>'\
            '<td valign="top" align="left" balign="left">'\
                '<b>params:</b> {action_params}'\
            '</td>'\
        '</tr>'\
        '<tr>'\
            '<td valign="top" align="left" balign="left">'\
                '<b>pre:</b> {action_pre}'\
            '</td>'\
        '</tr>'\
        '<tr>'\
            '<td valign="top" align="left" balign="left">'\
                '<b>add:</b> {action_add}'\
            '</td>'\
        '</tr>'\
        '<tr>'\
            '<td valign="top" align="left" balign="left">'\
                '<b>del:</b> {action_del}'\
            '</td>'\
        '</tr>'\
    '</table>>'


def flatten(actions):
    flat_actions = []
    flat_clusters = []
    stack = actions[:]
    while stack:
        item = stack.pop()
        if isinstance(item, Action):
            flat_actions.append(item)
            if item.up:
                stack.append(item.up)
        else: # isinstance(item, ActionCluster):
            flat_clusters.append(item)
            stack.append(item.left)
            stack.append(item.right)
    flat_actions.sort(key=lambda a: a.name)
    flat_clusters.sort(key=lambda c: c.down.name)
    return flat_actions, flat_clusters


def draw_action_node(g, action):
    pass


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


def wrap_text(text, max_length=72):
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


def build_cluster_graph(actions):
    g = gv.Graph("g")
    g.attr("node", **ACTION_NODE_STYLE)
    g.node("node1", label=ACTION_NODE_TMP.format(action_name="action-1",
        action_params="?x ?y", action_pre="(p ?x ?y)",
        action_add="(q ?x)<br/>(q ?x)<br/>(q;?x)", action_del="(r ?y)"))
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
    text = "p(?x,?y); q(?x); r(); <asdfjdjsfdasdfadhfadskfjahkdsf>s(?asd,?dyf)</asdjkfhakjsdhfkajhsdfjhskjf>"
    wrapped = wrap_text(text, 42)
    print(text)
    print(wrapped)
#    action1 = Action("action-1", [], [], [])
#    action2 = Action("action-2", [], [], [])
#    action3 = Action("action-3", [], [], [])
#    action4 = Action("action-4", [], [], [])
#    action5 = Action("action-5", [], [], [])
#    action6 = Action("action-6", [], [], [])
#    action7 = Action("action-7", [], [], [])
#    action8 = ActionCluster(action2, action3, action4, 0)
#    action9 = ActionCluster(action8, action5, action6, 0)
#    actions = [action1, action7, action9]

    g = build_cluster_graph([])
    g.render("g.gv", view=True)

