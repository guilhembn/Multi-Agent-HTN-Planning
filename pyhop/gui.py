from graphviz import Digraph

def show_plan(agentss, controlable_agent, uncontrolable_agent):
    dot = Digraph(comment='Plan')
    plotted_edge = set()

    for agents in agentss:
        reconstituted_plan = [None] * (2*len(agents[controlable_agent].plan))
        reconstituted_plan[::2] = agents[controlable_agent].plan
        reconstituted_plan[1::2] = agents[uncontrolable_agent].plan
        for i, a in enumerate(reconstituted_plan):
            color = "#AAAAFF" if i % 2 == 0 else "#FFFFAA"
            color_darker = "#5555CC" if i % 2 == 0 else "#CCCC55"
            shape = "octagon" if a.name == "IDLE" else "ellipse"
            dot.node(str(a.id), a.name + "\n(" + ",".join(map(lambda x: str(x), a.parameters)) + ")", style="filled", fillcolor=color, shape=shape)
            why = a.why
            how = a
            while why is not None:
                if (why.id, how.id) not in plotted_edge:
                    dot.node(str(why.id), why.name, shape="rectangle", style="filled", fillcolor=color_darker)
                    dot.edge(str(why.id), str(how.id), color="#999999", label=str(how.decompo_number),
                             fontcolor="#999999")
                    plotted_edge.add((why.id, how.id))
                how = why
                why = why.why
            if i != len(reconstituted_plan) - 1:
                if (a.id, reconstituted_plan[i + 1].id) not in plotted_edge:
                    plotted_edge.add((a.id, reconstituted_plan[i + 1].id))
                    dot.edge(str(a.id), str(reconstituted_plan[i + 1].id), color="#FF5555")

        for na in agents[controlable_agent].non_applicable_tasks:
            print("plop")
            dot.node(str(na.id), na.name + "\n(" + ",".join(na.parameters) + ")", style="filled", fillcolor="red",
                     shape="ellipse")
            dot.edge(str(na.previous.id), str(na.id), color="#FF5555")
    dot.render("/home/gbuisan/test", view=True)