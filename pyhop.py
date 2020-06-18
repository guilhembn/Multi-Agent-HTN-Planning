"""
Pyhop, version 1.2.2 -- a simple SHOP-like planner written in Python.
Author: Dana S. Nau, 2013.05.31

Copyright 2013 Dana S. Nau - http://www.cs.umd.edu/~nau

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
   
Pyhop should work correctly in both Python 2.7 and Python 3.2.
For examples of how to use it, see the example files that come with Pyhop.

Pyhop provides the following classes and functions:

- foo = State('foo') tells Pyhop to create an empty state object named 'foo'.
  To put variables and values into it, you should do assignments such as
  foo.var1 = val1

- bar = Goal('bar') tells Pyhop to create an empty goal object named 'bar'.
  To put variables and values into it, you should do assignments such as
  bar.var1 = val1

- print_state(foo) will print the variables and values in the state foo.

- print_goal(foo) will print the variables and values in the goal foo.

- declare_operators(o1, o2, ..., ok) tells Pyhop that o1, o2, ..., ok
  are all of the planning operators; this supersedes any previous call
  to declare_operators.

- print_operators() will print out the list of available operators.

- declare_methods('foo', m1, m2, ..., mk) tells Pyhop that m1, m2, ..., mk
  are all of the methods for tasks having 'foo' as their taskname; this
  supersedes any previous call to declare_methods('foo', ...).

- print_methods() will print out a list of all declared methods.

- pyhop(state1,tasklist) tells Pyhop to find a plan for accomplishing tasklist
  (a list of tasks), starting from an initial state state1, using whatever
  methods and operators you declared previously.

- In the above call to pyhop, you can add an optional 3rd argument called
  'verbose' that tells pyhop how much debugging printout it should provide:
- if verbose = 0 (the default), pyhop returns the solution but prints nothing;
- if verbose = 1, it prints the initial parameters and the answer;
- if verbose = 2, it also prints a message on each recursive call;
- if verbose = 3, it also prints info about what it's computing.
"""

# Pyhop's planning algorithm is very similar to the one in SHOP and JSHOP
# (see http://www.cs.umd.edu/projects/shop). Like SHOP and JSHOP, Pyhop uses
# HTN methods to decompose tasks into smaller and smaller subtasks, until it
# finds tasks that correspond directly to actions. But Pyhop differs from 
# SHOP and JSHOP in several ways that should make it easier to use Pyhop
# as part of other programs:
# 
# (1) In Pyhop, one writes methods and operators as ordinary Python functions
#     (rather than using a special-purpose language, as in SHOP and JSHOP).
# 
# (2) Instead of representing states as collections of logical assertions,
#     Pyhop uses state-variable representation: a state is a Python object
#     that contains variable bindings. For example, to define a state in
#     which box b is located in room r1, you might write something like this:
#     s = State()
#     s.loc['b'] = 'r1'
# 
# (3) You also can define goals as Python objects. For example, to specify
#     that a goal of having box b in room r2, you might write this:
#     g = Goal()
#     g.loc['b'] = 'r2'
#     Like most HTN planners, Pyhop will ignore g unless you explicitly
#     tell it what to do with g. You can do that by referring to g in
#     your methods and operators, and passing g to them as an argument.
#     In the same fashion, you could tell Pyhop to achieve any one of
#     several different goals, or to achieve them in some desired sequence.
# 
# (4) Unlike SHOP and JSHOP, Pyhop doesn't include a Horn-clause inference
#     engine for evaluating preconditions of operators and methods. So far,
#     I've seen no need for it; I've found it easier to write precondition
#     evaluations directly in Python. But I could consider adding such a
#     feature if someone convinces me that it's really necessary.
# 
# Accompanying this file are several files that give examples of how to use
# Pyhop. To run them, launch python and type "import blocks_world_examples"
# or "import simple_travel_example".


from __future__ import print_function
import copy,sys, pprint

############################################################
# States and goals
from typing import Dict, Any


class State():
    """A state is just a collection of variable bindings."""
    def __init__(self,name):
        self.__name__ = name

class Goal():
    """A goal is just a collection of variable bindings."""
    def __init__(self,name):
        self.__name__ = name


### print_state and print_goal are identical except for the name

def print_state(state,indent=4):
    """Print each variable in state, indented by indent spaces."""
    if state != False:
        for (name,val) in vars(state).items():
            if name != '__name__':
                for x in range(indent): sys.stdout.write(' ')
                sys.stdout.write(state.__name__ + '.' + name)
                print(' =', val)
    else: print('False')

def print_goal(goal,indent=4):
    """Print each variable in goal, indented by indent spaces."""
    if goal != False:
        for (name,val) in vars(goal).items():
            if name != '__name__':
                for x in range(indent): sys.stdout.write(' ')
                sys.stdout.write(goal.__name__ + '.' + name)
                print(' =', val)
    else: print('False')

############################################################
# Helper functions that may be useful in domain models

def forall(seq,cond):
    """True if cond(x) holds for all x in seq, otherwise False."""
    for x in seq:
        if not cond(x): return False
    return True

def find_if(cond,seq):
    """
    Return the first x in seq such that cond(x) holds, if there is one.
    Otherwise return None.
    """
    for x in seq:
        if cond(x): return x
    return None

############################################################
# Commands to tell Pyhop what the operators and methods are
class Agent:
    def __init__(self, name):
        self.name = name
        self.operators = {}
        self.methods = {}
        self.state = None
        self.goal = None
        self.tasks = []
        self.plan = []

agents = {}  # type: Dict[str, Agent]

def declare_operators(agent, *op_list):
    """
    Call this after defining the operators, to tell Pyhop what they are. 
    op_list must be a list of functions, not strings.
    """
    if agent not in agents:
        agents[agent] = Agent(agent)

    agents[agent].operators.update({op.__name__:op for op in op_list})
    return agents

def declare_methods(agent, task_name,*method_list):
    """
    Call this once for each task, to tell Pyhop what the methods are.
    task_name must be a string.
    method_list must be a list of functions, not strings.
    """
    if agent not in agents:
        agents[agent] = Agent(agent)
    agents[agent].methods.update({task_name:list(method_list)})
    return agents

def set_state(agent, state):
    if agent not in agents:
        agents[agent] = Agent(agent)
    agents[agent].state = state

def set_goal(agent, goal):
    if agent not in agents:
        agents[agent] = Agent(agent)
    agents[agent].goal = goal

def add_tasks(agent, tasks):
    if agent not in agents:
        agents[agent] = Agent(agent)
    agents[agent].tasks.extend(tasks)

############################################################
# Commands to find out what the operators and methods are

def print_operators(agent=None):
    """Print out the names of the operators"""
    if agent is None:
        print("==OPERATORS==")
        for a, ag in agents.items():
            print("Agent:", a)
            print("\t", ', '.join(ag.operators))
    else:
        print('OPERATORS:', ', '.join(agents[agent].operators))

def print_methods(agent=None):
    """Print out a table of what the methods are for each task"""
    print("==METHODS==")
    print('\t{:<14}{}'.format('TASK:','METHODS:'))
    if agent is None:
        for a, ag in agents.items():
            print("Agent:", a)
            for task in ag.methods:
                print('\t{:<14}'.format(task) + ', '.join([f.__name__ for f in ag.methods[task]]))
    else:
        ag = agents[agent]
        for task in ag.methods:
            print('\t{:<14}'.format(task) + ', '.join([f.__name__ for f in ag.methods[task]]))


############################################################
# The actual planner

def multi_agent_planning(verbose=0):
    ag = plan_step(agents, list(agents.keys()), verbose)
    return {a.name: a.plan for a in ag.values()} if ag != False else False

def plan_step(agents, agents_order, verbose=0):
    if all(a.tasks == [] for a in agents.values()):
        print("A multi agent solution has been found")
        return agents

    ag_i = next(i for i in range(len(agents_order)) if agents[agents_order[i]].tasks != [])
    name = agents[agents_order[ag_i]].name
    new_agents_order = agents_order[:]
    new_agents_order.append(new_agents_order.pop(ag_i))
    newagents = pyhop(agents, name, verbose)
    if newagents != False:
        print("new order:", agents_order)
        return plan_step(copy.deepcopy(newagents), new_agents_order, verbose)
    else:
        if new_agents_order != agents_order:
            print("new order:", agents_order)
            return plan_step(copy.deepcopy(agents), new_agents_order, verbose)
        else:
            return False




def pyhop(agents, agent_name ,verbose=0):
    """
    Try to find a plan that accomplishes tasks in state. 
    If successful, return the plan. Otherwise return False.
    """
    if agent_name not in agents:
        print("Agent is not declared!")
        return
    if verbose>0: print('** pyhop, verbose={}: **\n  agent={}\n   state = {}\n   tasks = {}'.format(verbose, agent_name, agents[agent_name].state.__name__, agents[agent_name].tasks))
    result = seek_plan(agents, agent_name, 0, verbose)
    if verbose>0: print('** result =',result,'\n')
    return result

def seek_plan(agents, agent_name, depth, verbose=0):
    """
    Workhorse for pyhop. state and tasks are as in pyhop.
    - plan is the current partial plan.
    - depth is the recursion depth, for use in debugging
    - verbose is whether to print debugging messages
    """
    if verbose>1: print('depth {} tasks {}'.format(depth,agents[agent_name].tasks))
    if agents[agent_name].tasks == []:
        if verbose>2: print('depth {} returns plan {}'.format(depth, agents[agent_name].plan))
        return agents
    task1 = agents[agent_name].tasks[0]
    if task1[0] in agents[agent_name].operators:
        if verbose>2: print('depth {} action {}'.format(depth,task1))
        operator = agents[agent_name].operators[task1[0]]
        newagents = copy.deepcopy(agents)
        newagents = operator(newagents, newagents[agent_name].state, agent_name, *task1[1:])
        if verbose>2:
            print('depth {} new self state:'.format(depth))
            if newagents:
                print_state(newagents[agent_name].state)
            else:
                print("False")
        if newagents:
            newagents[agent_name].tasks = newagents[agent_name].tasks[1:]
            newagents[agent_name].plan = newagents[agent_name].plan + [task1]
            solution = seek_plan(newagents, agent_name, depth+1, verbose)
            if solution != False:
                return solution
    if task1[0] in agents[agent_name].methods:
        if verbose>2: print('depth {} method instance {}'.format(depth,task1))
        relevant = agents[agent_name].methods[task1[0]]
        for method in relevant:
            subtasks = method(list(agents.values()), agents[agent_name].state, agent_name, *task1[1:])
            # Can't just say "if subtasks:", because that's wrong if subtasks == []
            if verbose>2:
                print('depth {} new tasks: {}'.format(depth,subtasks))
            if subtasks != False:
                agents[agent_name].tasks = subtasks + agents[agent_name].tasks[1:]
                solution = seek_plan(agents, agent_name, depth+1, verbose)
                if solution != False:
                    return solution
    if depth > 0:
        # If nothing is applicable but we have made some progress return the new states of agents
        return agents
    if verbose>2: print('depth {} returns failure'.format(depth))
    return False