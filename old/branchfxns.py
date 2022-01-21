# branch 2021-04-24
import re
import treelib
import math
import numpy as np
import pandas as pd
import pymaid

def strip_neurName(neurName):
    """ Strips a neuron name to letters and numbers only
    """
    return re.sub(r'\W+', '', neurName)

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
            if node[1] == -1:
                tree.create_node("root",node[0])
                nodeList.remove(node[0])
            if tree.contains(node[1]):
                tree.create_node("neuron",node[0],parent=node[1])
                nodeList.remove(node[0])
            else:
                continue
    return(tree)

def crop_tree_nr(skTree,skid):
    """ Input:  treelib Tree object
                Catmaid skeleton ID
        Output: treelib Tree object cropped at nerve_ring_starts to nerve_ring_ends
    """
    nr_starts = pymaid.find_nodes(tags=['nerve_ring_starts'],
                              skeleton_ids=skid)

    if len(nr_starts) > 1:
        treelist = []
        for starting_node in nr_starts.iterrows():
            treelist.append(skTree.subtree(starting_node[1].node_id))
        return treelist

    nr_subtree = skTree.subtree(nr_starts.node_id.to_numpy()[0])

    nr_ends = pymaid.find_nodes(tags=['nerve_ring_ends'],
                                skeleton_ids=skid)
                                
    if nr_ends.empty:
        print("no segments outside nr")
    else:
        for row in nr_ends.iterrows():
            nr_subtree.remove_node(row[1].node_id)
            #try:
            #    nr_subtree.remove_node(row[1].node_id)
            #except:
            #    print('tag outside of subtree')

    return [nr_subtree]

def lin_dist(node1,node2,neuron):
    """ Input:  two node_ids from CatmaidNeuron object
                numpy array ["node_id","parent_id","x","y","z"]
        Output: Linear distance between node1 and node2
    """
    node1Info = neuron[neuron[:,0] == node1]
    node2Info = neuron[neuron[:,0] == node2]

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
        nodeList.append(c_node[0][0])
        c_node = neuron[neuron[:,0] == c_node[0][1]]
    nodeList.append(c_node[0][0])
    return nodeList[::-1]

def path_to_trunk(node,neuron,trunk):
    """ Input:  node id
                numpy array ["node_id","parent_id","x","y","z"]
                List of nodes in trunk
        Output: List of nodes from node to first node in trunk
    """
    path = path_to_node(node,neuron,trunk[0])
    pathNew= []
    
    if len(trunk) >= len(path):
        for j in range(len(path)):
            if path[j] == trunk[j]:
                continue
            else:
                pathNew.append(path[j-1])
    else:
        for j in range(len(trunk)):
            if path[j] == trunk[j]:
                continue
            else:
                pathNew.append(path[j-1])
    pathNew.append(path[-1])

    return pathNew

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

def get_branchList(skTree,neuron,dist=0):
    """ Input:  treelib Tree object
                CatmaidNeuron object
                distance threshold (as % of main branch) 
        Output: [0] returns a pandas dataframe of branches reaching length threshold
                [1] returns a numpy array of nodes on branches in [0]
                [2] returns path of main branch
    """
    neurnumpy = neuron.nodes[["node_id","parent_id","x","y","z"]].to_numpy()

    pathList = np.array(skTree.paths_to_leaves(),dtype='object')
    root = skTree.root

    branchList = branch_distance_df(pathList,neurnumpy,root)
    trunkEnd = branchList.iloc[branchList['length'].idxmax()]

    # calculate distance of each leafnode to a member of trunk
    trunk = pathList[branchList['length'].idxmax()]

    pathListBranch = np.delete(pathList,branchList['length'].idxmax())
    pathListCrop = []

    if isinstance(pathListBranch[0], list):
        for i in range(len(pathListBranch)):
            pathListCrop.append(path_to_trunk(pathListBranch[i][-1],neurnumpy,trunk))
    else: 
        pathListCrop.append(path_to_trunk(pathListBranch[-1],neurnumpy,trunk))

    branchListCrop = branch_distance_df(pathListCrop,neurnumpy,root)

    # set distance threshold for branch
    dist_threshold = dist*trunkEnd['length']

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