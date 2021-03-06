import numpy as np
import torch
from itertools import product
from torchvision.datasets import MNIST, FashionMNIST
from utils.MNIST import get_dl as get_MNIST
from utils.Add10 import Add10Dataset, get_dl as get_Add10
from utils.Airfoil import AirfoilDataset, get_dl as get_Airfoil
from utils.misc import PreloadedDataloader
from models.MultiLayerDynamicPerceptron import MultiLayerDynamicPerceptron
from uuid import uuid4
from sys import argv
from compress_training import ITERATIONS, DATASETS, SIZES_PER_LAYER, LAYERS
from expriment_summary import get_experiments, get_summary
from algorithms.block_sparse_training_dynamic import compress_train, grow

def get_corresponding_configurations(dataset_name):
    ids, experiments = get_experiments(dataset_name)
    summaries = get_summary(experiments)
    possible_capacities = list(summaries.columns)
    capacities_to_get = [x for x in possible_capacities if 'capacity_l' in x]
    configurations = summaries[capacities_to_get]
    configurations = configurations.astype(int).drop_duplicates() # Don't evaluate the same model multiple times
    return configurations.as_matrix().tolist()

def get_model_from_configuration(configuration, dataset):
    layers = sum(x > 0 for x in configuration)
    f_in = DATASETS[DS]['features_in']
    f_out = DATASETS[DS]['features_out']
    if hasattr(f_in, '__len__'): # This is a tuple, so a picture => CNN
        model = DynamicCNN(
            layers,
            in_features=f_in,
            out_features=f_out,
            conv_initial_size=initial_size
        )
        for i in range(layers):
            model.processor[3 * i].grow(configuration[i])
        model.processor[3*layers].grow()
        model.processor[3*layers + 1].grow(configuration[-1])
        model.processor[3*layers +3].grow()
    else:
        model = MultiLayerDynamicPerceptron(
            layers,
            in_features=f_in,
            out_features=f_out,
            initial_size=0
        )
        for i in range(layers):
            model.processor[2 * i].grow(configuration[i])
        model.processor[2 * (i + 1)].grow()
    model()
    return model

if __name__ == "__main__":
    DS = 'MNIST'
    if argv[-1] in DATASETS.keys():
        DS = argv[-1]
        print(DS)
        train_set, val_set = PreloadedDataloader(DATASETS[DS]['get_train_dl']()).split(0.9)
        test_set = PreloadedDataloader(DATASETS[DS]['get_test_dl']())
        static_configurations = get_corresponding_configurations(DS)
        path_template = "./experiments/%s/%s.experiment"
        layers = LAYERS[0]
        # Filter only the configurations we are interested in 
        static_configurations = [x for x in static_configurations if sum(y > 0 for y in x) == layers]
        print(len(static_configurations))
        for configuration in static_configurations:
            print(configuration)
            continue
            for iteration in range(2):
                params = (0, 1, layers, iteration, 'static')
                initial_size = SIZES_PER_LAYER[layers]
                print(params, sum(configuration))
                id = uuid4()
                filename = path_template % (DS, id)
                model = get_model_from_configuration(configuration, DS).cuda()
                stats = compress_train(model, train_set, val_set,
                                       test_set, 0, 1, 0, 5, mode = DATASETS[DS]['mode'])
                logs = stats.logs
                summary = (params, logs)
                torch.save(summary, open(filename, 'wb'))
