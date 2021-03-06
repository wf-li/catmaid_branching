# connectivityfxns
import pymaid
from . import branchfxns as bf

# connectivity analysis functions
def sum_Conns_on_Branch(path,neuron,conn_dets = None, confidence = 5):
    """ Input:  list of leafnode ids
                CatmaidNeuron object
                Pre-loaded connection details, if available, otherwise None
                Confidence value for connection, if pulling from CATMAID
        Output: Number of connectors associated with branch
    """
    if isinstance(conn_dets,pd.DataFrame):
        neuron_conns = neuron.connectors[neuron.connectors.connector_id.isin(conn_dets.connector_id)]
    else:        
        conn_dets = pymaid.get_connector_links(neuron)

        neuron_conns = neuron.connectors[neuron.connectors.connector_id.isin(conn_dets.connector_id[conn_dets.confidence == confidence])]

    return sum(neuron_conns.node_id.isin(path))


def get_norm_dist(node,neuron,trunk):
    """ Input:  node id
                numpy array ["node_id","parent_id","x","y","z"]
                List of nodes in trunk
        Output: 
    """
    branch = bf.path_to_trunk(node,neuron,trunk)
    trunklen = bf.cable_length(trunk[-1],neuron,trunk[0])

    return bf.cable_length(branch[0],neuron,trunk[0])/trunklen

def get_norm_length(node,neuron,trunk):
    """ Input:  node id
                numpy array ["node_id","parent_id","x","y","z"]
                List of nodes in trunk
        Output: 
    """
    if node in trunk:
        return 0

    branch = bf.path_to_trunk(node,neuron,trunk)
    trunklen = bf.cable_length(trunk[-1],neuron,trunk[0])

    return (bf.cable_length(branch[-1],neuron,trunk[0])-bf.cable_length(branch[0],neuron,trunk[0]))/trunklen