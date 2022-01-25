# branchfxns 2022-01-18
import re
import treelib
import math
import numpy as np
import pandas as pd
import pymaid
import logging
logging.getLogger("pymaid").setLevel(logging.WARNING)

def build_tree(neuron):
    """ Input:  pymaid CatmaidNeuron object
        Output: treelib Tree object containing all nodes
    """
    tree = treelib.Tree()

    try: 
        isinstance(neuron, pymaid.CatmaidNeuron)
    except: 
        raise Exception('neuron needs to be CatmaidNeuron object')

    nodeList = neuron.nodes.node_id.tolist()
    nodeInfo = neuron.nodes[['node_id','parent_id']].to_numpy()

    while len(nodeList) > 0:
        for node in nodeInfo:
            if tree.contains(node[0]):
                continue
            elif node[1] == -1:
                tree.create_node("root",node[0])
                nodeList.remove(node[0])
            elif tree.contains(node[1]):
                tree.create_node(node[0],node[0],parent=node[1])
                nodeList.remove(node[0])
            else:
                continue
    return(tree)

def crop_tree_nr(tree,skid):
    """ Input:  treelib Tree object
                Catmaid skeleton ID
        Output: treelib Tree object cropped at nerve_ring_starts to nerve_ring_ends
    """
    nr_starts = pymaid.find_nodes(tags=['nerve_ring_starts'],
                              skeleton_ids=skid)
    nr_ends = pymaid.find_nodes(tags=['nerve_ring_ends'],
                              skeleton_ids=skid)

    if len(nr_starts) > 1:
        treelist = []
        for starting_node in nr_starts.iterrows():
            nr_subtree = tree.subtree(starting_node[1].node_id)
            if nr_ends.empty:
                print("Subtree has no tag 'nerve_ring_ends'")
            else:
                for row in nr_ends.iterrows():
                    try:
                        for child in nr_subtree.children(row[1].node_id):
                            nr_subtree.remove_node(child.identifier)
                    except:
                        pass
            treelist.append(nr_subtree)
        return treelist
    else:
        nr_subtree = tree.subtree(nr_starts.node_id.to_numpy()[0])

        if nr_ends.empty:
            print("Subtree has no tag 'nerve_ring_ends'")
        else:
            for row in nr_ends.iterrows():
                for child in nr_subtree.children(row[1].node_id):
                    nr_subtree.remove_node(child.identifier)

        return [nr_subtree]

def lin_dist(node1,node2,neuron):
    """ Input:  two node_ids from CatmaidNeuron object
                numpy array ["node_id","parent_id","x","y","z"]
        Output: Linear distance between node1 and node2
    """
    node1Info = neuron[neuron[:,0] == int(node1)]
    node2Info = neuron[neuron[:,0] == int(node2)]

    return (math.sqrt((node1Info[0][2]-node2Info[0][2])**2 + 
                        (node1Info[0][3]-node2Info[0][3])**2 + 
                        (node1Info[0][4]-node2Info[0][4])**2))
    
def path_to_node(node,neuron,root):
    """ Input:  node id
                numpy array ["node_id","parent_id","x","y","z"]
                Specify root node
        Output: list of nodes from root to node
    """
    nodeList = []
    c_node = neuron[neuron[:,0] == node]
    while c_node[0][0] != root:
        nodeList.append(int(c_node[0][0]))
        c_node = neuron[neuron[:,0] == c_node[0][1]]
    nodeList.append(int(c_node[0][0]))
    return nodeList[::-1]

def cable_length(node,neuron,root):
    """ Input:  node id
                numpy array ["node_id","parent_id","x","y","z"]
                Specify root node
        Output: length from root to node
    """
    pathList = path_to_node(node,neuron,root)
    branchLength = 0
    for i in range(0,(len(pathList)-1)):
        branchLength = branchLength + lin_dist(pathList[i],pathList[i+1],neuron)   
    return branchLength

def branch_distance_df(pathList,neuron,root):
    """ Input:  a list of paths (each path is a list of nodes) 
                numpy array ["node_id","parent_id","x","y","z"]
                Specify root node
        Output: a Pandas dataframe with columns "leafnode" and "length" to trunk
    """
    branchList = pd.DataFrame(columns = ["leafnode","length"])

    for i in range(0,len(pathList)):
        branchLength = cable_length(pathList[i][-1],neuron,root) - cable_length(pathList[i][0],neuron,root)
        branchList = branchList.append({"leafnode": str(pathList[i][-1]), "length": branchLength}, ignore_index = True)

    return (branchList)

def define_trunk(tree,skid,neuron):
    """ Defines the set of nodes that form the main branch based on the
        following priority:
          1. tag: main_branch_ends
          2. tag: nerve_ring_ends
          3. longest branch

        Input:  a treelib tree object
                Catmaid skeleton ID
                numpy array ["node_id","parent_id","x","y","z"]

        Output: list of nodes defined as main branch
    """ 
    nr_starts = pymaid.find_nodes(tags=['nerve_ring_starts'],
                        skeleton_ids=skid)
    mb_ends = pymaid.find_nodes(tags=['main_branch_ends'],
                        skeleton_ids=skid)
    nr_ends = pymaid.find_nodes(tags=['nerve_ring_ends'],
                          skeleton_ids=skid)
    
    if len(nr_starts) > 1:
        for starting_node in nr_starts.iterrows():
            if (tree.contains(starting_node[1].node_id)):
                nr_starts_node = starting_node[1].node_id
            else:
                pass
    else:
        nr_starts_node = nr_starts.node_id.values[0]

    if not mb_ends.empty:
        if len(mb_ends) > 1:
            for ending_node in mb_ends.iterrows():
                if tree.contains(ending_node[1].node_id):
                    print("Subtree has tag 'main_branch_ends'")
                    return path_to_node(ending_node[1].node_id,neuron,nr_starts_node)
        else:
            if tree.contains(mb_ends.node_id):
                print("Subtree has tag 'main_branch_ends'")
                return path_to_node(mb_ends.node_id,neuron,nr_starts_node)
            else:
                print("Define_trunk has tag main_branch_ends but not in tree")
    elif not nr_ends.empty:
        if len(nr_ends) > 1:
            for ending_node in nr_ends.iterrows():
                if tree.contains(ending_node[1].node_id):
                    return path_to_node(ending_node[1].node_id,neuron,nr_starts_node)
        else:
            if tree.contains(nr_ends.node_id.values[0]):
                return path_to_node(nr_ends.node_id.values[0],neuron,nr_starts_node)
            else:
                pass
    else:
        print("No tag for main branch or nr_ends; defaulting to longest branch")
        pathList = np.array(tree.paths_to_leaves(),dtype='object')
        root = tree.root

        branchList = branch_distance_df(pathList,neuron,root)
        return pathList[branchList['length'].idxmax()]

def get_branchList(tree,skid,neuron,dist=0):
    """ Input:  treelib Tree object
                Catmaid skeleton ID
                numpy array ["node_id","parent_id","x","y","z"]
                distance threshold (as % of main branch) 
        Output: [0] returns a pandas dataframe of branches reaching length threshold
                [1] returns a numpy array of nodes on branches in [0]
                [2] returns path of main branch
    """
    pathList = np.array(tree.paths_to_leaves(),dtype='object')
    root = tree.root

    branchList = branch_distance_df(pathList,neuron,root)

    trunk = define_trunk(tree,skid,neuron)
    
    trunkEnd = branchList.loc[branchList['leafnode'] == str(trunk[-1])]

    pathListBranch = np.delete(pathList,trunkEnd.index)
    pathListCrop = []

    if isinstance(pathListBranch[0], list):
        for i in range(len(pathListBranch)):
            pathListCrop.append(path_to_trunk(pathListBranch[i][-1],neuron,trunk))
    else: 
        pathListCrop.append(path_to_trunk(pathListBranch[-1],neuron,trunk))

    branchListCrop = branch_distance_df(pathListCrop,neuron,root)

    # set distance threshold for branch
    dist_threshold = dist*(trunkEnd['length'].values[0])

    # list of leaf nodes, and branch lengths to trunk
    branchListFinal = branchListCrop[branchListCrop.length >= dist_threshold].reset_index(drop = True)

    pathListFinal = [] # list of nodes on branches

    for leafnode in branchListFinal["leafnode"]:
        for path in pathListCrop:
            if str(path[-1]) == leafnode:
                pathListFinal.append(path)
            else:
                continue

    return (branchListFinal, pathListFinal, trunk)

def get_norm_dist(node,neuron,trunk):
    """ Input:  node id
                numpy array ["node_id","parent_id","x","y","z"]
                List of nodes in trunk
        Output: 
    """
    branch = path_to_trunk(node,neuron,trunk)
    trunklen = cable_length(trunk[-1],neuron,trunk[0])

    return cable_length(branch[0],neuron,trunk[0])/trunklen

def get_norm_length(node,neuron,trunk):
    """ Input:  node id
                numpy array ["node_id","parent_id","x","y","z"]
                List of nodes in trunk
        Output: 
    """
    if node in trunk:
        return 0

    branch = path_to_trunk(node,neuron,trunk)
    trunklen = cable_length(trunk[-1],neuron,trunk[0])

    return (cable_length(branch[-1],neuron,trunk[0])-cable_length(branch[0],neuron,trunk[0]))/trunklen

def strip_neurName(neurName):
    """ Strips a neuron name to letters and numbers only
    """
    return re.sub(r'\W+', '', neurName)