import pymaid
import numpy as np
import pandas as pd
from . import branchfxns as bf

# connectivity analysis functions
def sum_Conns_on_Branch(path,neuron,confidence = 5):
    """ Input:  list of leafnode ids
                CatmaidNeuron object
                Confidence value
        Output: 
    """

    conn_dets = pymaid.get_connector_links(neuron)

    neuron_conns = neuron.connectors[neuron.connectors.connector_id.isin(conn_dets.connector_id[conn_dets.confidence == confidence])]
    
    return sum(neuron_conns.node_id.isin(path))

def get_branches(all_pids, noi, branch_threshold=0.05, confidence = 5):
    """ Input:  list of all project ids
                list of neurons of interest
                % of main branch for threshold to consider branch
                Confidence value for connections
        Output: 
    """
    fullBranchList = pd.DataFrame(columns = ['leafnode',
                                                'length',
                                                'dist_from_root',
                                                'neurName',
                                                'project',
                                                'n_conns'])

    for project in all_pids:    
        # open an instance of CATMAID containing data https://zhencatmaid.com
        catmaid = pymaid.CatmaidInstance(server = 'https://zhencatmaid.com/',
                                            api_token='c48243e19b85edf37345ced8049ce5d6c5802412',
                                            project_id = project)
        
        for neurName in noi:
            print('Working on ' + neurName + ' in project ' + str(project))
            try:
                catNeur = pymaid.get_neuron(neurName)
            except:
                print(neurName + " not found in project " + str(project))
                continue

            if isinstance(catNeur, pymaid.CatmaidNeuron):
                catNeur = [catNeur]

            for neur in catNeur:
                if neur.n_nodes < 10:
                    continue

                skid = neur.id
                    
                if pymaid.find_nodes(tags=['nerve_ring_starts'],skeleton_ids=skid).empty:
                    continue

                catNeurnumpy = neur.nodes[["node_id","parent_id","x","y","z"]].to_numpy()

                skTree = bf.build_tree(neur)
                nr_subtree = bf.crop_tree_nr(skTree,skid)
                
                for i in range(0,len(nr_subtree)):
                    if len(nr_subtree) > 1:
                        strneurName = bf.strip_neurName(list(pymaid.get_names(skid).values())[0]) + "(" + str(i) + ")"
                    else: 
                        strneurName = bf.strip_neurName(list(pymaid.get_names(skid).values())[0])
                    bl_output = bf.get_branchList(nr_subtree[i],neur,branch_threshold)
                    branchList = bl_output[0]
                    pathList = bl_output[1]
                    trunk = bl_output[2]
                    trunklen = bf.cable_length(trunk[-1],catNeurnumpy,trunk[0])
                    lengthTemp = []
                    connTemp = []
                    for path in pathList:
                        lengthTemp.append(bf.cable_length(path[0],catNeurnumpy,trunk[0]))  
                        connTemp.append(sum_Conns_on_Branch(path,neur,confidence))
                    branchList['length'] = branchList['length']/trunklen
                    branchList['dist_from_root'] = [i/trunklen for i in lengthTemp] 
                    branchList['neurName'] = strneurName
                    branchList['project'] = project
                    branchList['n_conns'] = connTemp
                    try:
                            float).astype(int).isin(neur.tags['not a branch'])]
                    except:
                        pass
                    fullBranchList = fullBranchList.append(branchList)
    return fullBranchList