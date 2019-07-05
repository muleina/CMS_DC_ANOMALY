import numpy as np
import pandas as pd
import os
from sklearn.preprocessing import StandardScaler, normalize, MinMaxScaler
from sklearn.utils import shuffle
from sklearn.metrics import roc_curve, auc
from sklearn.model_selection import train_test_split

from data.new_prompt_reco.setting import ( EXTENDED_FEATURES, FEATURES, FRAC_VALID, FRAC_TEST,
                                            PD_GOOD_DATA_DIRECTORY, PD_BAD_DATA_DIRECTORY )
import data.new_prompt_reco.utility as utility

from model.reco.autoencoder import ( VanillaAutoencoder, SparseAutoencoder,
                                     ContractiveAutoencoder, VariationalAutoencoder )


def main():
    # setting
    selected_pd = "SingleMuon"
    data_preprocessing_mode = 'minmaxscalar'
    BS = 2**15
    EPOCHS = 1200
    DATA_SPLIT_TRAIN = [0.6, 0.8] # [0.2, 0.4, 0.6, 0.8, 1.0]
    is_fillna_zero = True

    features = utility.get_full_features(selected_pd)
    df_good = utility.read_data(selected_pd=selected_pd, pd_data_directory=PD_GOOD_DATA_DIRECTORY)
    df_bad = utility.read_data(selected_pd=selected_pd, pd_data_directory=PD_BAD_DATA_DIRECTORY)
    if is_fillna_zero:
        df_good = df_good.fillna(0)
        df_bad = df_bad.fillna(0)
    x = df_good[features]
    x_train_full, x_valid, x_test = utility.split_dataset(x, frac_test=FRAC_TEST, frac_valid=FRAC_VALID)
    y_test = np.concatenate((np.full(x_test.shape[0], 0), np.full(df_bad[features].shape[0], 1)))
    x_test = np.concatenate([x_test, df_bad[features].to_numpy()])

    file_auc = open('report/reco/eval/roc_auc.txt', 'w')
    file_auc.write("model_name data_fraction roc_auc\n")
    for model_name, Autoencoder in zip(
            [ "Vanilla", "Sparse", "Contractive", "Variational"],
            [ VanillaAutoencoder, SparseAutoencoder, ContractiveAutoencoder, VariationalAutoencoder]
            ):
        model_list = [
            Autoencoder(
                input_dim = [len(features)],
                summary_dir = "model/reco/summary",
                model_name = "{} model {}".format(model_name, i),
                batch_size = BS
            )
            for i in range(1,len(DATA_SPLIT_TRAIN) + 1)
        ]
        for dataset_fraction, autoencoder in zip(DATA_SPLIT_TRAIN, model_list):
            print("Model: {}, Chunk of Training Dataset fraction: {}".format(autoencoder.model_name, dataset_fraction))
            file_log = open('report/reco/logs/{}.txt'.format(autoencoder.model_name), 'w')
            file_log.write("EP loss_train loss_valid\n")

            x_train = x_train_full[:int(dataset_fraction*len(x_train_full))]
            # Data Preprocessing
            if data_preprocessing_mode == 'standardize':
                transformer = StandardScaler()
            elif data_preprocessing_mode == 'minmaxscalar':
                transformer = MinMaxScaler(feature_range=(0,1))
            transformer.fit(x_train)
            if data_preprocessing_mode == 'normalize':
                x_train = normalize(x_train, norm='l1')
                x_valid = normalize(x_valid, norm='l1')
                x_test = normalize(x_test, norm='l1')
            else:
                x_train = transformer.transform(x_train)
                x_valid = transformer.transform(x_valid)
                x_test = transformer.transform(x_test)

            autoencoder.init_variables()
            for EP in range(EPOCHS):
                x_train_shuf = shuffle(x_train)
                for iteration_i in range(int(len(x_train_shuf)/BS)):
                    x_batch = x_train_shuf[BS*iteration_i: BS*(iteration_i+1)]
                    autoencoder.train(x_batch)
                autoencoder.log_summary(x_train, EP)
            file_log.write("{} {} {}\n".format(
                    EP,
                    autoencoder.get_loss(x_train)["loss_total"],
                    autoencoder.get_loss(x_valid)["loss_total"]
                    ))
            file_log.close()

            try:
                file_eval = open('report/reco/eval/{} {}.txt'.format(autoencoder.model_name, dataset_fraction), 'w')
            except FileNotFoundError:
                os.makedirs("./report/reco/eval/")
                file_eval = open('report/reco/eval/{} {}.txt'.format(autoencoder.model_name, dataset_fraction), 'w')
            file_eval.write("fpr tpr threshold\n")
            fprs, tprs, thresholds = roc_curve(y_test, autoencoder.get_sd(x_test, scalar=True))
            for fpt, tpr, threshold in zip(fprs, tprs, thresholds):
                file_eval.write("{} {} {}\n".format(fpt, tpr, threshold))
            file_eval.close()

            print("AUC {}".format(auc(fprs, tprs)))
            file_auc.write("{} {} {}\n".format(model_name, dataset_fraction, auc(fprs, tprs)))

            autoencoder.save()