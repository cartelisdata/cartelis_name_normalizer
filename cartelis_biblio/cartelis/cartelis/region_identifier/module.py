import pandas as pd
import os
from rapidfuzz import process, fuzz



def extract_csv_region():
    """
    Extrait les données de la région à partir du fichier CSV.
    """
    _DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
    base_regions = pd.read_csv(os.path.join(_DATA_DIR, "regions.csv"), dtype=str)
    return base_regions



def code_postal_to_region(code_postal):
    """
    Convertit un code postal en région.
    """
    base_regions = extract_csv_region()
    region = base_regions[base_regions["code_postal"] == code_postal]["nom_commune"].values
    if len(region) > 0:
        return region[0]
    else:
        return None




def region_to_code_postal(region, threshold=80):
    """
    Convertit un nom de région (approché) en code postal.
    Retourne un dict {"nom_commune": ..., "code_postal": ...} ou None.
    """
    base_regions = extract_csv_region()
    
    communes = base_regions["nom_commune"].dropna().tolist()
    
    # Recherche du meilleur match approximatif
    result = process.extractOne(
        region.strip().upper(),
        [c.upper() for c in communes],
        scorer=fuzz.token_sort_ratio,
        score_cutoff=threshold  # en dessous de ce seuil → None
    )
    
    if result is None:
        return None
    
    best_match, score, idx = result
    matched_commune = communes[idx]
    
    code_postal = base_regions[
        base_regions["nom_commune"] == matched_commune
    ]["code_postal"].values[0]
    
    return {
        "nom_commune": matched_commune,
        "code_postal": code_postal,
        "score": score  # utile pour débugger la qualité du match
    }