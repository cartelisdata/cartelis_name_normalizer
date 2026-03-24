import re
import unicodedata
import pandas as pd
import numpy as np
import re
import pandas as pd
import unicodedata
from rapidfuzz import process, fuzz
import os
from .rule_engine import _load_rules, apply_rule, _normalize_token


# Chargement du dictionnaire de prénoms
_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
base_prenoms = pd.read_csv(os.path.join(_DATA_DIR, "base_prenoms.csv"))
PRENOM_SET = {_normalize_token(p) for p in base_prenoms["first_name_norm"].dropna().unique() if p}


def normalize_names(df, mode: str = "light", colonne_nom = "nom", colonne_prenom = "prenom", nettoyage: bool = True, overlap_cleaning: bool = True, pattern_detection: bool = True, normalization: bool = True, inplace: bool = False):
    '''
    Nettoie, détecte des schémas et normalise les colonnes de nom et prénom d'une DataFrame.

    Description
    ----------
    Cette fonction prend une DataFrame contenant idéalement des colonnes `nom` et/ou `prenom`,
    et applique une série d'étapes (nettoyage, résolution de chevauchements, détection de
    pattern/token classes, et normalisation via un moteur de règles) pour produire une
    DataFrame enrichie. Toutes les opérations sont effectuées sur une copie de la DataFrame
    d'entrée et la fonction renvoie la copie modifiée.

    Comportement / colonnes ajoutées
    --------------------------------
    Selon les options activées, la fonction ajoute notamment :
    - `nom_clean`, `prenom_clean` : version "nettoyée" (punctuation réduite, accents retirés,
      apostrophes/tirets harmonisés, espaces normalisés).
    - `overlap_action` : action appliquée si un chevauchement entre tokens de nom/prénom a été détecté.
    - `schema_nom`, `schema_prenom` : schéma de classes de tokens (ex: 'W-L-A', 'NA', ...).
    - `prenom_normalized`, `nom_normalized` : résultat des règles de normalisation appliquées
      via `apply_rule`/`_load_rules` (dépend de `mode`).
    Note : lorsque certaines colonnes `nom`/`prenom` sont absentes, les colonnes "clean" sont créées
    mais peuvent contenir None.

    Paramètres
    ----------
    df : pandas.DataFrame
        DataFrame source contenant au minimum les colonnes `nom` et/ou `prenom` (facultatif,
        mais recommandé).
    mode : str, optional
        Mode passé au chargeur de règles `_load_rules` (ex: "light", "heavy"). Par défaut "light".
        Influe sur les règles utilisées pour la normalisation.
    nettoyage : bool, optional
        Si True (par défaut), applique la phase de nettoyage (création de `nom_clean`/`prenom_clean`).
    overlap_cleaning : bool, optional
        Si True, applique la logique de résolution des chevauchements (overlaps) entre tokens de nom/prénom.
    pattern_detection : bool, optional
        Si True, calcule `schema_nom` et `schema_prenom` (classes de tokens : W, L, H, A, P, S).
    normalization : bool, optional
        Si True, applique les règles de normalisation (utilise `_load_rules` et `apply_rule`) et
        créé `prenom_normalized` et `nom_normalized`.
    inplace : bool, default False
        Si True, modifie le DataFrame d'entrée directement.
        Si False, retourne une copie du DataFrame avec les colonnes ajoutées.

    Valeurs retournées
    ------------------
    pandas.DataFrame
        Une copie de `df` enrichie avec les colonnes décrites ci-dessus. La fonction ne modifie
        pas la DataFrame en place.

    Dépendances et prérequis
    -----------------------
    - `rule_engine._load_rules`, `rule_engine.apply_rule`, `rule_engine._normalize_token`.
    - Le fichier `data/base_prenoms.csv` doit être présent dans le paquet pour initialiser le dictionnaire
      de prénoms (`PRENOM_SET`).
    - `pandas`, `unicodedata`, `re` doivent être disponibles.

    Cas particuliers et comportements
    --------------------------------
    - Les valeurs NaN/None sont conservées et traitées proprement (ex : `schema_*` -> "NA").
    - Les particules (ex: DE, DU, LA, ...) sont traitées spécifiquement par la logique d'overlap.
    - L'ordre des colonnes est réarrangé pour insérer `schema_nom` après `nom` et `schema_prenom` après `prenom`.

    Exemple
    -------
    >>> df = pd.DataFrame([{"nom": "D'ARAGON", "prenom": "Jean-Paul"}, {"nom": "DOE", "prenom": None}])
    >>> out = normalize_names(df, mode="light")
    >>> "prenom_normalized" in out.columns
    True
    '''



    #_____________________NETTOYAGE____________________________________



    df_final = df if inplace else df.copy()

    if nettoyage:
        def clean_name_display(value: str) -> str:
            if pd.isna(value):
                return None

            v = str(value).strip()

            # Normaliser unicode (sans enlever les accents)
            v = unicodedata.normalize("NFKC", v)
                
            # Harmoniser apostrophes et tirets typographiques
            v = v.replace("’", "'").replace("`", "'").replace("´", "'")
            v = v.replace("–", "-").replace("—", "-").replace("−", "-")

            # Supprimer les accents
            v = "".join(
                c for c in unicodedata.normalize("NFD", v)
                if unicodedata.category(c) != "Mn"
            )

            # Supprimer certaines ponctuations partout
            v = re.sub(r"[.,;:!?()/\\[\]{}\"]", "", v)

            # Réduire les espaces multiples
            v = re.sub(r"\s+", " ", v).strip()

            return v if v else None
        
        

        # NEWWWWW
        if colonne_nom in df_final.columns:
            df_final["nom_clean"] = df_final[colonne_nom].apply(clean_name_display)
        else:
            df_final["nom_clean"] = None

        if colonne_prenom in df_final.columns:
            df_final["prenom_clean"] = df_final[colonne_prenom].apply(clean_name_display)
        else:
            df_final["prenom_clean"] = None









    #_____________________TRAITEMENT DES OVERLAPS____________________________________


    # --- Paramètres ---
    PARTICULES = {
        "DE","DU","DES","LA","LE","LES","DEL","DA","DI","EL","LAS","LOS","ET","Y","E",
        "DOS","DO","DA","DAS","DELA","DELLOS","DELAS"  # élargis si besoin
    }

    if overlap_cleaning:
        def _tok_split(s: str):
            """Tokenisation simple sur l’espace. On garde les tirets/apostrophes au sein des tokens."""
            if pd.isna(s) or str(s).strip()=="":
                return []
            s = re.sub(r"\s+", " ", str(s).strip())
            return s.split(" ")

        def _join_tokens(toks):
            out = " ".join([t for t in toks if t])
            return out if out else None

        def _remove_tokens(source_tokens, tokens_to_remove_set):
            """Supprime TOUTES les occurrences des tokens_to_remove_set (exact match, insensible à la casse car données déjà upper)."""
            return [t for t in source_tokens if t not in tokens_to_remove_set]



        def clean_overlap_row(nom_clean, prenom_clean):
            """
            Règles:
            - Si nom_clean == prenom_clean (exact) -> aucune action.
            - Si chevauchement uniquement de particules -> aucune action.
            - Si l'un des champs est exactement "<PARTICULE> <MOT>" et que l'autre contient MOT -> aucune action.
            - Sinon, supprimer les mots communs non-particules du champ le plus long (égalité -> côté prénom).
            """
            # 0) Egalité stricte -> ne rien faire
            if (pd.isna(nom_clean) and pd.isna(prenom_clean)) or (nom_clean == prenom_clean):
                return nom_clean, prenom_clean, "no_action_equal_fields"

            nom_toks    = _tok_split(nom_clean)
            prenom_toks = _tok_split(prenom_clean)

            if not nom_toks or not prenom_toks:
                return nom_clean, prenom_clean, "no_action_empty_side"

            set_nom    = set(nom_toks)
            set_prenom = set(prenom_toks)
            common = set_nom.intersection(set_prenom)
            if not common:
                return nom_clean, prenom_clean, "no_action_no_overlap"

            # 1) Chevauchement uniquement de particules ?
            common_non_particles = {w for w in common if w not in PARTICULES}
            if not common_non_particles:
                return nom_clean, prenom_clean, "no_action_particles_only"

            # 2) Cas spécial: "<PARTICULE> <MOT>" vs l'autre contient MOT -> aucune action
            def is_particle_plus_word(tokens):
                return (len(tokens) == 2) and (tokens[0] in PARTICULES) and (tokens[1] not in PARTICULES)

            # nom = "<P> <W>" et prénom contient W
            if is_particle_plus_word(nom_toks) and (nom_toks[1] in set_prenom):
                return nom_clean, prenom_clean, "no_action_particle_plus_word"

            # prénom = "<P> <W>" et nom contient W (symétrique)
            if is_particle_plus_word(prenom_toks) and (prenom_toks[1] in set_nom):
                return nom_clean, prenom_clean, "no_action_particle_plus_word"

            # 3) Choix du côté à nettoyer : champ le plus long (en nb de tokens). Égalité -> prénom
            len_nom = len(nom_toks)
            len_pre = len(prenom_toks)

            if len_nom > len_pre:
                nom_toks_new = _remove_tokens(nom_toks, common_non_particles)
                prenom_toks_new = prenom_toks
                action = "removed_from_nom"
            elif len_pre > len_nom:
                prenom_toks_new = _remove_tokens(prenom_toks, common_non_particles)
                nom_toks_new = nom_toks
                action = "removed_from_prenom"
            else:
                prenom_toks_new = _remove_tokens(prenom_toks, common_non_particles)
                nom_toks_new = nom_toks
                action = "removed_from_prenom_equal_len"

            return _join_tokens(nom_toks_new), _join_tokens(prenom_toks_new), action



        # ---------- Application sur la DF ----------
        def apply_overlap_cleaning(df: pd.DataFrame,
                                col_nom="nom_clean",
                                col_pre="prenom_clean"):
            out = df.copy()
            res = out[[col_nom, col_pre]].apply(
                lambda r: clean_overlap_row(r[col_nom], r[col_pre]), axis=1
            )

            out["nom_clean"]     = res.apply(lambda t: t[0])
            out["prenom_clean"]  = res.apply(lambda t: t[1])
            out["overlap_action"] = res.apply(lambda t: t[2])
            return out

        # Application sur la df :
        df_clean = apply_overlap_cleaning(df_final)

        # --- Petit résumé  ---
        df_clean["overlap_action"].value_counts()
        df_clean.loc[df_clean["overlap_action"].str.startswith("removed_"),
                                ["nom","prenom","nom_clean","prenom_clean","overlap_action"]]
        

        df_final = df_clean

    






    #_____________________DETECTION PATTERN____________________________________

    # Fonction -> Ajout des colonnes schéma

    if pattern_detection:
        # ---------- Helpers pour détecter le schéma W/L/H/P/A/S ----------
        PARTICULES = {"DE","DU","DES","LA","LE","LES","DEL","DA","DI","EL","LAS","LOS","ET","Y","E","DOS","DO","DA","DAS","DELA","DELLOS","DELAS"} 

        def _normalize_value(v: str) -> str:
            if pd.isna(v):
                return ""
            v = str(v).upper().strip()
            v = re.sub(r"\s+", " ", v)
            return v

        def _clean_token(tok: str) -> str:
            t = tok.strip().upper()
            t = re.sub(r"^[\.\,;:]+|[\.\,;:]+$", "", t)
            return t

        def tokenize(value: str):
            v = _normalize_value(value)
            return [t for t in re.split(r"\s+", v) if t]

        # --- Regex pour les classes ---
        RE_APO  = re.compile(r"[’']")                  # contient une apostrophe
        RE_LET1 = re.compile(r"^[A-ZÀ-Ÿ]$")            # 1 lettre (initiale)
        RE_HYPH = re.compile(r"^[A-ZÀ-Ÿ]+-[A-ZÀ-Ÿ]+$") # mot avec tiret
        RE_WORD = re.compile(r"^[A-ZÀ-Ÿ]{2,}$")        # mot alphabétique (>=2)

        def classify_token(tok: str) -> str:
            """
            W = mot alphabétique (>=2 lettres)
            L = 1 lettre (initiale)
            H = mot avec tiret (ex: ANNE-MARIE)
            A = mot contenant une apostrophe (ex: O'CONNOR, D’ALMEIDA, L'ABBAYE)
            P = particule (DE, DU, DES, LA, LE, LES, DEL, DA, DI, EL, LAS, LOS, ET, Y, E)
            S = chiffres ou caractères spéciaux
            """
            t = _clean_token(tok)
            if not t:
                return ""

            # Particule (si tu veux que D' soit classé en A et non P, commente ce bloc)
            if t in PARTICULES:
                return "P"

            # Apostrophe
            if RE_APO.search(t):
                return "A"

            if RE_HYPH.fullmatch(t):
                return "H"
            if RE_LET1.fullmatch(t):
                return "L"
            if RE_WORD.fullmatch(t):
                return "W"

            return "S"

        def detect_pattern(value: str) -> str:
            if pd.isna(value) or not str(value).strip():
                return "NA"
            toks = tokenize(value)
            classes = [classify_token(t) for t in toks if classify_token(t)]
            return "-".join(classes) if classes else "NA"


        # ---------- Replacer les nouvelles colonnes juste après nom / prenom ----------
        def move_after(cols, col_to_move, after_col):
            cols = cols.copy()
            if col_to_move in cols:
                cols.remove(col_to_move)
            if after_col in cols:
                idx = cols.index(after_col)
                cols.insert(idx+1, col_to_move)
            else:
                cols.append(col_to_move)
            return cols

        def insert_columns(df):
            cols = df.columns.tolist()
            cols = move_after(cols, "schema_nom", colonne_nom)
            cols = move_after(cols, "schema_prenom", colonne_prenom)
            df = df[cols]
            return df
        

    # NEWWWwW


        if "nom_clean" in df_final.columns:
            df_final["schema_nom"] = df_final["nom_clean"].apply(detect_pattern)
        elif colonne_nom in df_final.columns:
            df_final["schema_nom"] = df_final[colonne_nom].apply(detect_pattern)
        else:
            df_final["schema_nom"] = None

        if "prenom_clean" in df_final.columns:
            df_final["schema_prenom"] = df_final["prenom_clean"].apply(detect_pattern)
        elif colonne_prenom in df_final.columns:
            df_final["schema_prenom"] = df_final[colonne_prenom].apply(detect_pattern)
        else:
            df_final["schema_prenom"] = None

        # Ensuite seulement, réorganiser les colonnes
        df_final = insert_columns(df_final)






    #_____________________NORMALISATION____________________________________


    if normalization:
        # Chargement des règles depuis l'Excel
        rules_prenom = _load_rules("regles_prenom", mode)
        rules_nom    = _load_rules("regles_nom", mode)

        # Chargement du dictionnaire de prénoms
        _DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
        base_prenoms = pd.read_csv(os.path.join(_DATA_DIR, "base_prenoms.csv"))
        PRENOM_SET = {_normalize_token(p) for p in base_prenoms["first_name_norm"].dropna().unique() if p}

        # Application nom
        df_final["nom_normalized"] = df_final.apply(
            lambda row: apply_rule(row, rules=rules_nom, schema_col="schema_nom"),
            axis=1)
        
        # Application prenom
        df_final["prenom_normalized"] = df_final.apply(
            lambda row: apply_rule(row, rules=rules_prenom, schema_col="schema_prenom", prenom_set=PRENOM_SET),
            axis=1
        )



    
    return df_final



    #_______________________________VERIFICATION DICT____________________________________

def verify_prenom(df, colonne_nom = "nom", colonne_prenom = "prenom", inplace: bool = False) -> pd.DataFrame:

    '''
    Vérifie si tous les tokens d'un prénom existent dans le dictionnaire de prénoms.

    Description
    -----------
    Vérifie, pour la colonne `colonne_prenom` de la DataFrame normalisée, si **tous** 
    les tokens appartiennent au dictionnaire canonique `PRENOM_SET`. Produit une 
    colonne `prenom_all_exist` avec les valeurs "oui" ou "non".

    Paramètres
    ----------
    df : pandas.DataFrame
        DataFrame d'entrée contenant idéalement les colonnes `nom` et `prenom`.
    colonne_nom : str, optional
        Nom de la colonne contenant les noms. Par défaut "nom".
    colonne_prenom : str, optional
        Nom de la colonne contenant les prénoms. Par défaut "prenom".
    inplace : bool, default False
        Si True, modifie le DataFrame d'entrée directement.
        Si False, retourne une copie enrichie.

    Valeur retournée
    ----------------
    pandas.DataFrame
        DataFrame avec les colonnes `colonne_nom`, `colonne_prenom` et `prenom_all_exist`.
        - `prenom_all_exist` : "oui" si chaque token figure dans `PRENOM_SET`, sinon "non".

    Comportement et cas limites
    ---------------------------
    - Les valeurs None/NaN donnent "non".
    - La comparaison est insensible à la casse (tokens comparés en majuscules).
    - Le découpage se fait via `r"[\s\-_/\.]+"`.

    Exemple
    -------
    >>> df = pd.DataFrame([{"nom": "MARTIN", "prenom": "Jean Paul"}, {"nom": "DOE", "prenom": "Xxx"}])
    >>> verify_prenom(df, mode="light")["prenom_all_exist"].tolist()
    ['oui', 'non']
    '''
    
    df_normalized = normalize_names(df, "light", colonne_nom=colonne_nom, colonne_prenom=colonne_prenom, inplace=inplace)


    def canon(s):
        if s is None or pd.isna(s):
            return None
        s = s.upper()
        return s

    def prenom_exists_all_tokens(prenom_raw, prenom_set_canon):
        if prenom_raw is None or pd.isna(prenom_raw):
            return "non"
        
        # split sur séparateurs identifiés
        tokens = re.split(r"[\s\-_/\.]+", str(prenom_raw).strip())
        tokens = [t for t in tokens if t]
        
        if not tokens:
            return "non"
        
        for token in tokens:
            if canon(token) not in prenom_set_canon:
                return "non"
        
        return "oui"


    df_normalized["prenom_all_exist"] = df_normalized[colonne_prenom].apply(lambda x: prenom_exists_all_tokens(x, PRENOM_SET))

    return df_normalized[[colonne_nom, colonne_prenom, "prenom_all_exist"]]




    #_______________________________PRENOM PLUS PROCHE____________________________________

def rapprocher_prenom(df, colonne_nom = "nom", colonne_prenom = "prenom", THRESHOLD=90, MIN_TOKEN_LENGTH=2, inplace: bool = False) -> pd.DataFrame:
    '''
    Propose des corrections orthographiques pour les tokens de prénom via fuzzy matching.

    Description
    -----------
    Pour chaque valeur de `prenom_normalized`, tente de rapprocher chaque token vers 
    le meilleur candidat dans `PRENOM_SET` via `rapidfuzz.process.extractOne`. Si 
    le score >= `THRESHOLD`, le token est remplacé.

    Paramètres
    ----------
    df : pandas.DataFrame
        DataFrame d'entrée contenant idéalement les colonnes `nom` et `prenom`.
    colonne_nom : str, optional
        Nom de la colonne contenant les noms. Par défaut "nom".
    colonne_prenom : str, optional
        Nom de la colonne contenant les prénoms. Par défaut "prenom".
    THRESHOLD : int, optional
        Seuil (0-100) de similarité pour accepter une correspondance fuzzy. Par défaut 90.
    MIN_TOKEN_LENGTH : int, optional
        Longueur minimale d'un token pour tenter un rapprochement. Par défaut 2.
    inplace : bool, default False
        Si True, modifie le DataFrame d'entrée directement.
        Si False, retourne une copie enrichie.

    Valeur retournée
    ----------------
    pandas.DataFrame
        DataFrame avec les colonnes `colonne_nom`, `colonne_prenom` et :
        - `prenom_corrige`     : prénom après correction (str | None).
        - `correction_faite`   : True si au moins une correction a été appliquée.
        - `detail_corrections` : liste de dicts par token avec les clés
          `{ "original", "corrige", "score", "remplace", "garde" }`.

    Comportement et cas limites
    ---------------------------
    - Token déjà exact dans `PRENOM_SET` → score=100, conservé.
    - Token de longueur < `MIN_TOKEN_LENGTH` → score=0, non gardé.
    - Aucun candidat trouvé → token original conservé, score=None.

    Exemple
    -------
    >>> df = pd.DataFrame([{"nom": "DOE", "prenom": "Jhn"}])
    >>> out = rapprocher_prenom(df, mode="light", THRESHOLD=85)
    >>> out.loc[0, "prenom_corrige"]  # si "JOHN" est dans PRENOM_SET
    'JOHN'
    '''

    df_normalized = normalize_names(df, mode= "light", colonne_nom=colonne_nom, colonne_prenom=colonne_prenom, inplace=inplace)

    def canon(s):
        if s is None or pd.isna(s):
            return None
        s = s.upper()
        return s
    def rapprocher_token(token, prenom_set_canon, threshold, min_length=MIN_TOKEN_LENGTH):
        token_canon = canon(token)
        
        if len(token_canon) < min_length:
            return token_canon, 0
        
        if token_canon in prenom_set_canon:
            return token_canon, 100
        
        result = process.extractOne(
            token_canon,
            prenom_set_canon,
            scorer=fuzz.ratio
        )
        
        if result is None:
            return token_canon, None
        
        best_match, score, _ = result
        
        if score >= threshold:
            return best_match, score
        else:
            return token_canon, score


    def corriger_prenom(prenom_raw, prenom_set_canon, threshold=80, min_length=MIN_TOKEN_LENGTH):
        if prenom_raw is None or pd.isna(prenom_raw):
            return {"prenom_corrige": None, "tokens_corriges": [], "correction_faite": False}
        
        tokens = re.split(r"[\s\-_/\.]+", str(prenom_raw).strip())
        tokens = [t for t in tokens if t]
        
        if not tokens:
            return {"prenom_corrige": prenom_raw, "tokens_corriges": [], "correction_faite": False}
        
        tokens_corriges = []
        correction_faite = False
        
        for token in tokens:
            token_canon = canon(token)
            
            if len(token_canon) < min_length:
                correction_faite = True
                tokens_corriges.append({
                    "original": token,
                    "corrige": token_canon,
                    "score": 0,
                    "remplace": False,
                    "garde": False
                })
                continue
            
            if token_canon in prenom_set_canon:
                tokens_corriges.append({
                    "original": token,
                    "corrige": token_canon,
                    "score": 100,
                    "remplace": False,
                    "garde": True
                })
            else:
                best, score = rapprocher_token(token, prenom_set_canon, threshold, min_length)
                remplace = (score is not None and score >= threshold and best != token_canon)
                garde = (score is not None and score >= threshold)
                
                if remplace or not garde:
                    correction_faite = True
                    
                tokens_corriges.append({
                    "original": token,
                    "corrige": best if remplace else token_canon,
                    "score": score,
                    "remplace": remplace,
                    "garde": garde
                })
        
        tokens_valides = [t["corrige"] for t in tokens_corriges if t["garde"]]
        prenom_corrige = " ".join(tokens_valides) if tokens_valides else None

        return {
            "prenom_corrige": prenom_corrige,
            "tokens_corriges": tokens_corriges,
            "correction_faite": correction_faite
        }


    # ______________________________________ Application __________________________________________
    # On applique UNE SEULE FOIS et on stocke dans une Series de dicts
    corrections = df_normalized["prenom_normalized"].apply(
        lambda x: corriger_prenom(x, PRENOM_SET, threshold=THRESHOLD, min_length=MIN_TOKEN_LENGTH)
    )

    # Ensuite on dépaque chaque clé séparément
    df_normalized["prenom_corrige"]      = corrections.apply(lambda x: x["prenom_corrige"])
    df_normalized["correction_faite"]    = corrections.apply(lambda x: x["correction_faite"])
    df_normalized["detail_corrections"]  = corrections.apply(lambda x: x["tokens_corriges"])


    return df_normalized[[colonne_nom, colonne_prenom, "prenom_corrige", "correction_faite", "detail_corrections"]]





def normalize_names_pipeline(df, mode: str = "light", colonne_nom = "nom", colonne_prenom = "prenom", inplace: bool = False, THRESHOLD=90, MIN_TOKEN_LENGTH=2):
    '''
    Pipeline complet : normalisation + vérification + rapprochement des prénoms.

    Description
    -----------
    Applique en une seule passe les 3 étapes du pipeline :
    1. `normalize_names` : nettoyage, overlap, pattern detection, normalisation.
    2. Vérification dictionnaire : colonne `prenom_all_exist`.
    3. Rapprochement : colonnes `prenom_corrige`, `correction_faite`, `detail_corrections`.

    Paramètres
    ----------
    df : pandas.DataFrame
        DataFrame d'entrée contenant idéalement les colonnes `nom` et `prenom`.
    mode : str, optional
        Mode de normalisation (ex: "light", "heavy"). Par défaut "light".
    colonne_nom : str, optional
        Nom de la colonne contenant les noms. Par défaut "nom".
    colonne_prenom : str, optional
        Nom de la colonne contenant les prénoms. Par défaut "prenom".
    inplace : bool, default False
        Si True, modifie le DataFrame d'entrée directement.
        Si False, retourne une copie enrichie.
    THRESHOLD : int, optional
        Seuil de similarité pour le rapprochement fuzzy. Par défaut 90.
    MIN_TOKEN_LENGTH : int, optional
        Longueur minimale d'un token pour tenter un rapprochement. Par défaut 2.

    Valeur retournée
    ----------------
    pandas.DataFrame
        DataFrame enrichie avec toutes les colonnes ajoutées par le pipeline :
        - `nom_clean`, `prenom_clean`
        - `overlap_action`
        - `schema_nom`, `schema_prenom`
        - `nom_normalized`, `prenom_normalized`
        - `prenom_all_exist`
        - `prenom_corrige`, `correction_faite`, `detail_corrections`

    Exemple
    -------
    >>> df = pd.DataFrame([{"nom": "D'ARAGON", "prenom": "Jean-Paul"}, {"nom": "DOE", "prenom": None}])
    >>> out = normalize_names_pipeline(df, mode="light")
    >>> "prenom_corrige" in out.columns
    True
    '''
    
    df_normalized = normalize_names(df, mode=mode, colonne_nom = colonne_nom, colonne_prenom = colonne_prenom, inplace=inplace)
    def canon(s):
        if s is None or pd.isna(s):
            return None
        s = s.upper()
        return s

    def prenom_exists_all_tokens(prenom_raw, prenom_set_canon):
        if prenom_raw is None or pd.isna(prenom_raw):
            return "non"
        
        # split sur séparateurs identifiés
        tokens = re.split(r"[\s\-_/\.]+", str(prenom_raw).strip())
        tokens = [t for t in tokens if t]
        
        if not tokens:
            return "non"
        
        for token in tokens:
            if canon(token) not in prenom_set_canon:
                return "non"
        
        return "oui"


    df_normalized["prenom_all_exist"] = df_normalized[colonne_prenom].apply(lambda x: prenom_exists_all_tokens(x, PRENOM_SET))
    

    def rapprocher_token(token, prenom_set_canon, threshold, min_length=MIN_TOKEN_LENGTH):
        token_canon = canon(token)
        
        if len(token_canon) < min_length:
            return token_canon, 0
        
        if token_canon in prenom_set_canon:
            return token_canon, 100
        
        result = process.extractOne(
            token_canon,
            prenom_set_canon,
            scorer=fuzz.ratio
        )
        
        if result is None:
            return token_canon, None
        
        best_match, score, _ = result
        
        if score >= threshold:
            return best_match, score
        else:
            return token_canon, score


    def corriger_prenom(prenom_raw, prenom_set_canon, threshold=80, min_length=MIN_TOKEN_LENGTH):
        if prenom_raw is None or pd.isna(prenom_raw):
            return {"prenom_corrige": None, "tokens_corriges": [], "correction_faite": False}
        
        tokens = re.split(r"[\s\-_/\.]+", str(prenom_raw).strip())
        tokens = [t for t in tokens if t]
        
        if not tokens:
            return {"prenom_corrige": prenom_raw, "tokens_corriges": [], "correction_faite": False}
        
        tokens_corriges = []
        correction_faite = False
        
        for token in tokens:
            token_canon = canon(token)
            
            if len(token_canon) < min_length:
                correction_faite = True
                tokens_corriges.append({
                    "original": token,
                    "corrige": token_canon,
                    "score": 0,
                    "remplace": False,
                    "garde": False
                })
                continue
            
            if token_canon in prenom_set_canon:
                tokens_corriges.append({
                    "original": token,
                    "corrige": token_canon,
                    "score": 100,
                    "remplace": False,
                    "garde": True
                })
            else:
                best, score = rapprocher_token(token, prenom_set_canon, threshold, min_length)
                remplace = (score is not None and score >= threshold and best != token_canon)
                garde = (score is not None and score >= threshold)
                
                if remplace or not garde:
                    correction_faite = True
                    
                tokens_corriges.append({
                    "original": token,
                    "corrige": best if remplace else token_canon,
                    "score": score,
                    "remplace": remplace,
                    "garde": garde
                })
        
        tokens_valides = [t["corrige"] for t in tokens_corriges if t["garde"]]
        prenom_corrige = " ".join(tokens_valides) if tokens_valides else None

        return {
            "prenom_corrige": prenom_corrige,
            "tokens_corriges": tokens_corriges,
            "correction_faite": correction_faite
        }


    # ______________________________________ Application __________________________________________
    # On applique UNE SEULE FOIS et on stocke dans une Series de dicts
    corrections = df_normalized["prenom_normalized"].apply(
        lambda x: corriger_prenom(x, PRENOM_SET, threshold=THRESHOLD, min_length=MIN_TOKEN_LENGTH)
    )

    # Ensuite on dépaque chaque clé séparément
    df_normalized["prenom_corrige"]      = corrections.apply(lambda x: x["prenom_corrige"])
    df_normalized["correction_faite"]    = corrections.apply(lambda x: x["correction_faite"])
    df_normalized["detail_corrections"]  = corrections.apply(lambda x: x["tokens_corriges"])


    return df_normalized