# get connections from existing csv

# open existing pandas corresponding to correct dataset

import pandas as pd

all_pids = []
noi = [] # list of neurons of interest
conn_partners = [] # leave blank if all synaptic partners

fullConnsSpec = pd.DataFrame(columns = ['connector_id',
                                                        'length',
                                                        'dist_from_root',
                                                        'neuron',
                                                        'project',
                                                        'type',
                                                        'inputs',
                                                        'outputs'])

for project in all_pids:
    proj_data = pd.read_csv('/' + str(project) +  '_conns.csv') # open project csv

    # cleaning neuron names
    proj_data['neuron'] = proj_data['neuron'].str.split('(').str[0]

    connsList = proj_data.loc[proj_data['neuron'].isin(noi)] #subset where df.neuron in noi df.loc[df['column_name'].isin(some_values)]

    conns_specific = pd.DataFrame(columns = ['connector_id',
                                                        'length',
                                                        'dist_from_root',
                                                        'neuron',
                                                        'project',
                                                        'type',
                                                        'inputs',
                                                        'outputs'])

    if conn_partners:
        for connection in connsList.iterrows():
            if connection[1].inputs in conn_partners:
                conns_specific = conns_specific.append(connection)
            elif any(i in connection[1].outputs for i in conn_partners):
                conns_specific = conns_specific.append(connection[1])

        conns_specific = conns_specific.reset_index(drop = True)
    else:
        conns_specific = connsList

    fullConnsSpec = fullConnsSpec.append(conns_specific)