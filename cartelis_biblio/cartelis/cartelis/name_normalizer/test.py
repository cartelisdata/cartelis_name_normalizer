# test.py
import pandas as pd
from cartelis.module import normalize_names, verify_prenom, rapprocher_prenom

df = pd.read_csv("/Users/adamelhachimi/Desktop/cartelis_name_normalizer/cartelis_name_normalizer/cartelis_name_normalizer/data/sample_personne_test.csv")


df_test = pd.read_csv("/Users/adamelhachimi/Desktop/cartelis_name_normalizer/cartelis_name_normalizer/cartelis_name_normalizer/data/sample_personne_test.csv")


#print(normalize_names(df, 'heavy'))

print(normalize_names(df_test, 'heavy'))
print(verify_prenom(df_test, 'heavy'))
print(rapprocher_prenom(df_test, 'heavy'))