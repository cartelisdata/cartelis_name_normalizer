# test.py
import pandas as pd
from cartelis.name_normalizer import normalize_names, verify_prenom, rapprocher_prenom, normalize_names_pipeline

df = pd.read_csv("/Users/adamelhachimi/Desktop/pip install cartelis/cartelis_name_normalizer/cartelis_biblio/cartelis/cartelis/name_normalizer/data/sample_personne_test.csv")


df_test = pd.read_csv("/Users/adamelhachimi/Desktop/pip install cartelis/cartelis_name_normalizer/cartelis_biblio/cartelis/cartelis/name_normalizer/data/sample_personne_test.csv")


#print(normalize_names(df, 'heavy'))

print(normalize_names(df_test, 'heavy'))
print(verify_prenom(df_test))
print(rapprocher_prenom(df_test))
print(normalize_names_pipeline(df_test, mode="heavy"))