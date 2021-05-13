import pymaid
import pandas as pd
from . import branchfxns as bf
from . import connectivityfxns as cf

def check_confidence(catmaid,project,connector,skid,direction,confidence = 5):
    """ Input:  catmaid client
                project id
                connector id
                skeleton id
                input or output
                confidence value
        Output: True or False if confidence reaches threshold
    """
    input_check = False
    output_check = False
    con_data = catmaid.fetch(url = 'https://zhencatmaid.com/'+ str(project) + '/connectors/' + str(connector))

    if direction == 'input':
        output_check = con_data['partners']['skeleton_id' == skid]['confidence'] >= confidence
        input_check = con_data['partners']['relation_name' == 'presynaptic_to']['confidence'] >= confidence
        return (output_check and input_check)

    elif direction == 'output':
        return (con_data['partners']['skeleton_id' == skid]['confidence'] >= confidence)

    else:
        raise ValueError('Only "input" and "output" are acceptable arguments for direction')

def get_outputs(catmaid,project,connector,confidence = 5):
    """ Input:  catmaid client
                project id
                connector id
                confidence value
        Output: List of neurons that reach confidence threshold
    """
    filt_list = []
    con_data = catmaid.fetch(url = 'https://zhencatmaid.com/'+ str(project) + '/connectors/' + str(connector))

    for partner in con_data['partners']:
        if partner['confidence'] >= confidence and partner['relation_name'] == 'postsynaptic_to':
            filt_list.append(partner['skeleton_id'])
    return filt_list

def clean_inputs(catmaid,project,connector):
    """ Input:  catmaid client
                project id
                connector id
                confidence value
        Output: Input neuron name
    """
    con_data = catmaid.fetch(url = 'https://zhencatmaid.com/'+ str(project) + '/connectors/' + str(connector.connector_id))

    target_skid = next(item for item in con_data['partners'] if item['relation_name'] == "presynaptic_to")['skeleton_id']

    return bf.strip_neurName(list(pymaid.get_names(target_skid).values())[0])

def clean_outputs(catmaid,project,connector):
    """ Input:  catmaid client
                project id
                connector id
                confidence value
        Output: Clean list of output neuron names
    """
    return [bf.strip_neurName(output) for output in list(pymaid.get_names(get_outputs(catmaid,project,connector.connector_id)).values())]

def get_connection_list(all_pids,noi,confidence = 5):
    """ Input:  list of all project ideas to get list for
                list of neurons of interest
        Output: list of all connections
    """
    fullConnsList = pd.DataFrame(columns = ['connector_id',
                                            'length',
                                            'dist_from_root',
                                            'neuron',
                                            'project',
                                            'type',])

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

                # define and filter connections
                connectors = neur.connectors
                filt_conns = connectors[connectors.type.isin([0,1])].reset_index(drop = True)

                for i in range(len(nr_subtree)):
                    if len(nr_subtree) > 1:
                        strneurName = bf.strip_neurName(list(pymaid.get_names(skid).values())[0]) + "(" + str(i) + ")"
                    else: 
                        strneurName = bf.strip_neurName(list(pymaid.get_names(skid).values())[0])
                    bl_output = bf.get_branchList(nr_subtree[i],neur)
                    trunk = bl_output[2]
                    
                    connsList = pd.DataFrame(columns = ['connector_id',
                                                    'length',
                                                    'dist_from_root',
                                                    'neuron',
                                                    'project',
                                                    'type',
                                                    'inputs',
                                                    'outputs'])
                    
                    filt_conns.connector_id = filt_conns.connector_id.astype(str)
                    filt_conns2 = pd.DataFrame(columns = filt_conns.columns)
                    inputsClean = []
                    outputsClean = []

                    for connector in filt_conns.iterrows():
                        connector = connector[1]
                        if connector.node_id in nr_subtree[i]:
                            if connector.type == 1:
                                if check_confidence(catmaid,project,connector.connector_id,skid,'input'):
                                    inputsClean.append(clean_inputs(catmaid,project,connector))
                                    outputsClean.append(clean_outputs(catmaid,project,connector))
                                    filt_conns2 = filt_conns2.append(connector)
                            if connector.type == 0:
                                if check_confidence(catmaid,project,connector.connector_id,skid,'output'):
                                    inputsClean.append(clean_inputs(catmaid,project,connector))
                                    outputsClean.append(clean_outputs(catmaid,project,connector))
                                    filt_conns2 = filt_conns2.append(connector)
                    filt_conns2 = filt_conns2.reset_index(drop = True)

                    lengthTemp = []
                    distTemp = []
                    for node in filt_conns2.node_id:                    
                        lengthTemp.append(cf.get_norm_length(node,catNeurnumpy,trunk))
                        distTemp.append(cf.get_norm_dist(node,catNeurnumpy,trunk))

                    connsList.connector_id = filt_conns2.connector_id
                    connsList.project = project
                    connsList.neuron = strneurName
                    connsList.length = lengthTemp
                    connsList.dist_from_root = distTemp
                    connsList.type = filt_conns2.type
                    connsList.inputs = inputsClean
                    connsList.outputs = outputsClean
                    fullConnsList = fullConnsList.append(connsList).reset_index(drop = True)

    return fullConnsList