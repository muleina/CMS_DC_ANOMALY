import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os

from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler, normalize, MinMaxScaler
# customize
from data.prompt_reco.setting import REDUCED_FEATURES, FEATURES, SELECT_PD
import data.prompt_reco.utility as utility

COLORS = ('green', 'blue')
GROUP_LABELS = ('A', 'B')
HUMAN_LABELS = ('Good', 'Bad')

def main():
    # Setting
    is_reduced_data = True
    # data
    files = utility.get_file_list(chosed_pd=SELECT_PD) # choosing only ZeroBias

    # feature_names = utility.get_feature_name()
    # data = pd.DataFrame(utility.get_data(files), columns=feature_names)
    # data["run"] = data["run"].astype(int)
    # data["lumi"] = data["lumi"].astype(int)
    # data.drop(["_foo", "_bar", "_baz"], axis=1, inplace=True)
    # data = data.sort_values(["run", "lumi"], ascending=[True,True])
    # data = data.reset_index(drop=True)
    # data["label"] = data.apply(utility.add_flags, axis=1)

    feature_names = utility.get_feature_name(features=FEATURES)
    reduced_feature_names = utility.get_feature_name(features=REDUCED_FEATURES)
    data = pd.DataFrame(utility.get_data(files), columns=feature_names)
    data["run"] = data["run"].astype(int)
    data["lumi"] = data["lumi"].astype(int)
    data.drop(["_foo", "_bar", "_baz"], axis=1, inplace=True)
    if is_reduced_data:
        not_reduced_column = feature_names
        for intersected_elem in reduced_feature_names: not_reduced_column.remove(intersected_elem)
        data.drop(not_reduced_column, axis=1, inplace=True)
    data = data.sort_values(["run", "lumi"], ascending=[True,True])
    data = data.reset_index(drop=True)
    data["label"] = data.apply(utility.add_flags, axis=1)

    # training
    print("Preparing dataset...")
    dataset = data.iloc[:].copy()
    df_train = dataset.copy()
    X_train = df_train.iloc[:, 0:len(REDUCED_FEATURES)-1]
    y_train = df_train["label"]

    print("Training KMeans")
    # standardize data
    transformer = StandardScaler()
    # transformer = MinMaxScaler(feature_range=(0,1))
    transformer.fit(X_train.values)
    X_train = transformer.transform(X_train.values)
    # X_train = normalize(X_train, norm='l1')
    # training
    kmeans_model = KMeans(n_clusters=2).fit(X_train)
    y_pred = kmeans_model.predict(X_train)
    # PCA
    pca = PCA(n_components=2)
    principal_components = pca.fit_transform(X_train)
    # visualzie K-means
    fig, ax = plt.subplots()

    for i, group_label in enumerate(GROUP_LABELS):
        scat_data = principal_components[y_pred == i]
        ax.scatter(
            scat_data[:, 0], scat_data[:, 1], alpha=0.8,
            c = COLORS[i],
            label = GROUP_LABELS[i]
        )
    ax.legend()
    plt.title('Clustering by K-Means, visual in Principal Basis (JetHT)')
    plt.savefig('JetHT.png')

    # visual labeld 
    fig, ax = plt.subplots()
    for i, group_label in enumerate(GROUP_LABELS):
        scat_data = principal_components[y_train == i]
        ax.scatter(
            scat_data[:, 0], scat_data[:, 1], alpha=0.8,
            c = COLORS[i],
            label = HUMAN_LABELS[i]
        )

    ax.legend()
    plt.title('Human Labeled data, visual in Principal Basis (JetHT)')
    plt.savefig('JetHT_label.png')