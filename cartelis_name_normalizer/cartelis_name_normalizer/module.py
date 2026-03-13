


def normalize_names(df, value = None, nettoyage=True, overlap_cleaning=True, pattern_detection=True, normalization=True):
    '''
    Nettoie et normalise une ou plusieurs colonnes de noms dans un pandas.DataFrame.

    Parameters
    ----------
    - df : pandas.DataFrame : DataFrame d'entrée contenant la(les) colonne(s) à normaliser.
    - value : str or list of str or None, default None : Nom de la colonne à normaliser, ou liste de colonnes. Si None, la fonction tente
        d'identifier automatiquement les colonnes candidates.
    - nettoyage : bool, default True : Effectue le nettoyage de base (trim, collapse d'espaces, suppression de ponctuation).
    - overlap_cleaning : bool, default True : Résout les chevauchements et doublons internes (ex. "Jean Jean" -> "Jean").
    - pattern_detection : bool, default True : Détecte et corrige des motifs fréquents (inversion "Last, First", titres, initiales).
    - normalization : bool, default True : Applique les règles de normalisation (capitalisation, ordre Prénom/Nom, translittération).
    - dict_check : bool, default True : Vérifie et, si possible, corrige les noms à partir d'un dictionnaire/fichier de référence
        (fuzzy matching). Requiert un dictionnaire optionnel pour être pleinement efficace.

    Returns
    -------
    pandas.DataFrame : Copie du DataFrame d'entrée avec une ou plusieurs colonnes ajoutées/remplacées par leur version normalisée 
    (nom_colonne_normalized). Peut aussi inclure une colonne nom_colonne_notes contenant le journal des transformations réalisées.

    '''



    #_____________________NETTOYAGE____________________________________

    import re
    import unicodedata
    import pandas as pd
    import numpy as np

    df_final = df.copy()

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
        
        df_final = df.copy()

        # NEWWWWW
        if "nom" in df_final.columns:
            df_final["nom_clean"] = df_final["nom"].apply(clean_name_display)
        else:
            df_final["nom_clean"] = None

        if "prenom" in df_final.columns:
            df_final["prenom_clean"] = df_final["prenom"].apply(clean_name_display)
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
            cols = move_after(cols, "schema_nom", "nom")
            cols = move_after(cols, "schema_prenom", "prenom")
            df = df[cols]
            return df
        

    # NEWWWwW


        if "nom_clean" in df_final.columns:
            df_final["schema_nom"] = df_final["nom_clean"].apply(detect_pattern)
        elif "nom" in df_final.columns:
            df_final["schema_nom"] = df_final["nom"].apply(detect_pattern)
        else:
            df_final["schema_nom"] = None

        if "prenom_clean" in df_final.columns:
            df_final["schema_prenom"] = df_final["prenom_clean"].apply(detect_pattern)
        elif "prenom" in df_final.columns:
            df_final["schema_prenom"] = df_final["prenom"].apply(detect_pattern)
        else:
            df_final["schema_prenom"] = None

        # Ensuite seulement, réorganiser les colonnes
        df_final = insert_columns(df_final)














    #_____________________NORMALISATION____________________________________



    if normalization:
        #_____________________PRENOM___________________________________________

        import os
        _DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
        base_prenoms = pd.read_csv(os.path.join(_DATA_DIR, "base_prenoms.csv"))

        def normalize_name(s):
            if not isinstance(s, str):
                return None
            s = str(s).strip()
            
            # suppression des accents
            s = "".join(
                c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn"
            )
            
            # 🔹 garder uniquement lettres et espaces
            s = re.sub(r"[^a-z\s]", " ", s)
            
            # suppression espaces multiples
            s = " ".join(s.split())
            
            return s.upper() if s else None

        prenoms_base = set(
            base_prenoms["first_name_norm"].dropna().unique()
        )

        PRENOM_SET = {
            normalize_name(p)
            for p in prenoms_base
            if p is not None
        }

        def strip_accents(s: str) -> str:
            return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

        def normalize_prenom(s):
            if pd.isna(s):
                return None
            s = str(s).strip()
            if not s:
                return None
            s = strip_accents(s)
            s = s.upper()
            # uniformiser séparateurs
            s = re.sub(r"[’'`]", " ", s)      # apostrophes -> espace
            s = re.sub(r"[_/]", " ", s)       # séparateurs divers -> espace
            s = re.sub(r"[.]", " ", s) 
            s = re.sub(r"[,]", " ", s) 
            s = re.sub(r"[?]", "", s) 
            s = re.sub(r"\s+", " ", s).strip()
            return s if s else None

        def split_tokens_space_and_hyphen(prenom_norm: str):
            """
            Découpe en tokens en éclatant espaces et tirets.
            Ex: "MARIE-THERESE GDS" -> ["MARIE","THERESE","GDS"]
            """
            if not prenom_norm:
                return []
            # remplacer tirets par espaces pour split
            s = prenom_norm.replace("-", " ")
            s = re.sub(r"\s+", " ", s).strip()
            return [t for t in s.split(" ") if t]

        def is_valid_token(token: str, prenom_set: set) -> bool:
            return (token is not None) and (token in prenom_set)

        def join_tokens(tokens):
            return " ".join([t for t in tokens if t]).strip() or None

        # -------------------------------------------------------------------
        # 3) Règles
        # -------------------------------------------------------------------
        RULE1_NO_CHANGE = {"W", "H", "A", "P-W", "L-W"}
        RULE2_CONCAT = {None, np.nan, "L", "P"}  # NA + L + P

        def apply_rule_2_concat(prenom_norm, prenom2_norm):
            """
            Si prenom2 non null => concat prenom + prenom2, sinon inchangé.
            """
            if prenom2_norm:
                if prenom_norm:
                    return f"{prenom_norm} {prenom2_norm}"
                return prenom2_norm
            return prenom_norm

        def clean_token_for_dict_compare(token: str) -> str:
            if token is None:
                return ""
            
            token = str(token).strip()
            
            # Supprimer les chiffres
            token = re.sub(r"\d+", "", token)
            
            # Supprimer la ponctuation parasite sauf apostrophe et tiret
            token = re.sub(r"[^A-Za-zÀ-ÿ'’-]", "", token)
            
            return token.strip()


        def apply_rule_3_patterns_S(prenom_norm, prenom_set):
            """
            Pour patterns contenant 'S':
            - split en sous-tokens (espaces + tirets)
            - nettoyer chaque sous-token avant comparaison
            - garder seulement ceux présents dans le dictionnaire
            - reconstruire
            """
            toks = split_tokens_space_and_hyphen(prenom_norm)

            kept = []
            for t in toks:
                t_clean = clean_token_for_dict_compare(t)
                if t_clean and is_valid_token(t_clean, prenom_set):
                    kept.append(t_clean)

            return join_tokens(kept)

        def apply_rule_4_drop_truncated_last(prenom_norm, schema_prenom, prenom_set):
            """
            Règle principale:
            - vérifier le dernier token réel (space-split)
            - s'il n'existe pas dans le dico => supprimer dernier token
            - puis supprimer aussi les particules isolées P/L qui précèdent immédiatement
            Cas particulier: si le dernier élément du pattern (schema) == 'H':
            - on regarde le dernier sous-token réel (après split '-')
            - si non valide => supprimer ce sous-token dans le dernier token réel
            - puis même logique de suppression P/L si nécessaire
            """
            if not prenom_norm:
                return None

            # tokens "réels" = split par espace (on conserve les tirets dans le token pour cas H)
            real = re.sub(r"\s+", " ", prenom_norm).strip().split(" ")
            if not real:
                return None

            # déterminer dernier élément de schema (ex: "W-H" -> "H", "H-P-P-W" -> "W")
            last_schema = None
            if schema_prenom is not None and not pd.isna(schema_prenom):
                sp = str(schema_prenom).strip().upper()
                if sp:
                    parts = sp.split("-")
                    last_schema = parts[-1] if parts else None

            def drop_particles_PL(tokens):
                while tokens and tokens[-1] in {"P", "L"}:
                    tokens.pop()
                return tokens

            # --- cas particulier: dernier schema == H
            if last_schema == "H":
                # dernier token réel (peut contenir des tirets: ex "MARIE-THERE")
                last_real = real[-1]
                sub = last_real.split("-")
                # dernier sous-token réel
                last_sub = sub[-1] if sub else None
                if last_sub and not is_valid_token(last_sub, prenom_set):
                    # supprimer le dernier sous-token
                    sub = sub[:-1]
                    if sub:
                        real[-1] = "-".join(sub)  # on conserve le reste (ex: "MARIE")
                    else:
                        real.pop()                # plus rien => enlever le token entier

                    # ensuite supprimer particules P/L à la fin si présentes
                    real = drop_particles_PL(real)

                # si le dernier sous-token est valide => rien à faire
                return " ".join(real).strip() or None

            # --- cas général: vérifier le dernier token réel (en éclatant aussi les tirets)
            # on considère que le "dernier token" à valider = dernier sous-token après split tiret
            last_real = real[-1]
            last_sub = last_real.split("-")[-1] if last_real else None

            if last_sub and is_valid_token(last_sub, prenom_set):
                return " ".join(real).strip() or None

            # sinon tronqué => supprimer le dernier token réel
            real.pop()

            # puis supprimer P/L isolés qui précèdent immédiatement
            real = drop_particles_PL(real)

            return " ".join(real).strip() or None

        # -------------------------------------------------------------------
        # 4) Fonction finale : prenom_CRM
        # -------------------------------------------------------------------
        def build_prenom_crm(row, prenom_set: set):
            prenom_norm = normalize_prenom(row.get("prenom_clean"))
            schema = row.get("schema_prenom")
            schema_norm = None if pd.isna(schema) else str(schema).strip().upper()

            prenom2_norm = normalize_prenom(row.get("prenom2")) if "prenom2" in row else None

            # Règle 1 — aucune transformation
            if schema_norm in RULE1_NO_CHANGE:
                return prenom_norm

            # Règle 2 — concat avec prenom2 (schema NA, L, P)
            if schema_norm in {"L", "P"} or schema_norm is None:
                base = apply_rule_2_concat(prenom_norm, prenom2_norm)
                return base

            # Règle 3 — patterns contenant S
            if schema_norm and "S" in schema_norm:
                return apply_rule_3_patterns_S(prenom_norm, prenom_set)

            # Règle 4 — suppression du dernier élément tronqué (cas général)
            return apply_rule_4_drop_truncated_last(prenom_norm, schema_norm, prenom_set)

        # -------------------------------------------------------------------
        # 5) Application
        # -------------------------------------------------------------------
        personne_CRM_1 = df_final.copy()
        personne_CRM_1["prenom_normalized"] = personne_CRM_1.apply(build_prenom_crm, axis=1, prenom_set=PRENOM_SET)


    #__________________________________NOM_____________________________________

        SEP_PATTERN_NAME = r"[\s\-_/\.,]+"   # séparateurs identifiés pour les noms


        def split_name_tokens_raw(nom_raw: str):
            """
            Découpe un nom en sous-tokens selon les séparateurs identifiés.
            On enlève seulement les '?' avant split.
            """
            if nom_raw is None or pd.isna(nom_raw):
                return []
            s = str(nom_raw).strip()
            if not s:
                return []
            s = s.replace("?", "")
            tokens = [t for t in re.split(SEP_PATTERN_NAME, s) if t]
            return tokens


        def clean_name_subtoken(token: str) -> str:
            """
            Nettoyage d'un sous-token pour la règle S :
            - suppression des accents
            - suppression des chiffres
            - suppression des caractères parasites
            - conservation des lettres + apostrophe interne éventuelle
            """
            if token is None or pd.isna(token):
                return None

            t = str(token).strip()
            if not t:
                return None

            # normalisation unicode + suppression accents
            t = unicodedata.normalize("NFKD", t)
            t = "".join(c for c in t if not unicodedata.combining(c))

            # harmonisation apostrophes
            t = t.replace("’", "'").replace("`", "'").replace("´", "'")

            # suppression chiffres
            t = re.sub(r"\d+", "", t)

            # garder seulement lettres + apostrophe
            # ex: D' -> conservé ; EDDLESTON3 -> EDDLESTON
            t = re.sub(r"[^A-Za-z']", "", t)

            # enlever apostrophes parasites en début/fin
            t = re.sub(r"^'+|'+$", "", t)

            return t if t else None


        def normalize_spaces(s: str) -> str:
            if s is None:
                return None
            s = re.sub(r"\s+", " ", str(s)).strip()
            return s if s else None


        # =========================================================
        # 2. RÈGLE 1 — patterns contenant "S"
        # =========================================================

        def apply_rule_1_S_clean_subtokens(nom_raw):
            """
            Règle 1 — patterns contenant 'S'
            - split en sous-tokens (espaces, tirets, _, /, ., ,)
            - nettoyer chaque sous-token
            - reconstruire avec des espaces
            Ex:
            SAINT-LOUIS-AUGUSTIN   -> SAINT LOUIS AUGUSTIN
            MORAN EDDLESTON3       -> MORAN EDDLESTON
            FOSSART DE ROZEVILLE-  -> FOSSART DE ROZEVILLE
            """
            toks = split_name_tokens_raw(nom_raw)
            cleaned = [clean_name_subtoken(t) for t in toks]
            cleaned = [t for t in cleaned if t]
            return " ".join(cleaned).strip() or None


        # =========================================================
        # 3. RÈGLE 2 — patterns P / P-P / L-P
        # =========================================================

        RULE2_CONCAT_USAGE = {"P", "P-P", "L-P"}

        def apply_rule_2_concat_nom_usage(nom_raw, nom_usage_raw):
            """
            Si nomUsage non null => concaténer nom + nomUsage
            Sinon => conserver nom tel quel
            """
            nom = None if nom_raw is None or pd.isna(nom_raw) else str(nom_raw).strip()
            nom_usage = None if nom_usage_raw is None or pd.isna(nom_usage_raw) else str(nom_usage_raw).strip()

            if nom_usage:
                if nom:
                    return f"{nom} {nom_usage}".strip()
                return nom_usage
            return nom if nom else None


        # =========================================================
        # 4. RÈGLE 3 — patterns L / L-L
        # =========================================================

        RULE3_REPLACE_BY_USAGE = {"L", "L-L"}

        def apply_rule_3_replace_by_nom_usage(nom_raw, nom_usage_raw):
            """
            Si nomUsage non null => remplacer le nom par nomUsage
            Sinon => conserver nom tel quel
            """
            nom = None if nom_raw is None or pd.isna(nom_raw) else str(nom_raw).strip()
            nom_usage = None if nom_usage_raw is None or pd.isna(nom_usage_raw) else str(nom_usage_raw).strip()

            if nom_usage:
                return nom_usage
            return nom if nom else None


        # =========================================================
        # 5. RÈGLE 4 — suppression des particules finales L / P
        # =========================================================

        def apply_rule_4_drop_final_LP_tokens(nom_raw, schema_nom):
            """
            Pour tous les autres patterns :
            si le pattern se termine par L ou P, on supprime les tokens finaux
            tant que les derniers éléments du schéma sont L ou P.

            Hypothèse : on travaille au niveau des sous-tokens découpés selon
            les séparateurs identifiés, puis on reconstruit avec des espaces.
            """
            if nom_raw is None or pd.isna(nom_raw):
                return None

            s = str(nom_raw).strip().replace("?", "")
            if not s:
                return None

            schema_norm = None if schema_nom is None or pd.isna(schema_nom) else str(schema_nom).strip().upper()
            if not schema_norm:
                return normalize_spaces(s)

            schema_parts = [x for x in schema_norm.split("-") if x]
            if not schema_parts:
                return normalize_spaces(s)

            toks = split_name_tokens_raw(s)
            if not toks:
                return None

            # Tant que le schéma finit par L/P, on supprime en cascade
            while schema_parts and schema_parts[-1] in {"L", "P"} and toks:
                schema_parts.pop()
                toks.pop()

            return " ".join(toks).strip() or None


        # =========================================================
        # 6. RÈGLE 5 — conserver tel quel
        # =========================================================

        def apply_rule_5_keep_as_is(nom_raw):
            if nom_raw is None or pd.isna(nom_raw):
                return None
            out = str(nom_raw).strip()
            return out if out else None


        # =========================================================
        # 7. FONCTION PRINCIPALE
        # =========================================================

        def build_nom_crm(row):
            nom_raw = row.get("nom_clean")
            nom_usage_raw = row.get("nomUsage") if "nomUsage" in row else None
            schema_nom = row.get("schema_nom")

            schema_norm = None if schema_nom is None or pd.isna(schema_nom) else str(schema_nom).strip().upper()

            # Règle 1 — patterns contenant S
            if schema_norm and "S" in schema_norm:
                return apply_rule_1_S_clean_subtokens(nom_raw)

            # Règle 2 — P / P-P / L-P
            if schema_norm in RULE2_CONCAT_USAGE:
                return apply_rule_2_concat_nom_usage(nom_raw, nom_usage_raw)

            # Règle 3 — L / L-L
            if schema_norm in RULE3_REPLACE_BY_USAGE:
                return apply_rule_3_replace_by_nom_usage(nom_raw, nom_usage_raw)

            # Règle 4 — autres patterns finissant par L/P
            if schema_norm:
                schema_parts = [x for x in schema_norm.split("-") if x]
                if schema_parts and schema_parts[-1] in {"L", "P"}:
                    return apply_rule_4_drop_final_LP_tokens(nom_raw, schema_norm)

            # Règle 5 — tous les autres patterns
            return apply_rule_5_keep_as_is(nom_raw)


        # =========================================================
        # 8. APPLICATION
        # =========================================================

        personne_CRM_2 = personne_CRM_1.copy()
        personne_CRM_2["nom_normalized"] = personne_CRM_2.apply(build_nom_crm, axis=1)
        
        df_final = personne_CRM_2



    #_______________________________VERIFICATION DICT____________________________________

    import re
    import pandas as pd
    import unicodedata

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

    df_final["prenom_all_exist"] = df_final["prenom"].apply(lambda x: prenom_exists_all_tokens(x, PRENOM_SET))


    #_______________________________VERIFICATION DICT____________________________________
    import re
    import pandas as pd
    import unicodedata
    from rapidfuzz import process, fuzz

    MIN_TOKEN_LENGTH = 2
    THRESHOLD = 90

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


    # ── Application ────────────────────────────────────────────────────────────────
    # On applique UNE SEULE FOIS et on stocke dans une Series de dicts
    corrections = df_final["prenom"].apply(
        lambda x: corriger_prenom(x, PRENOM_SET, threshold=THRESHOLD, min_length=MIN_TOKEN_LENGTH)
    )

    # Ensuite on dépaque chaque clé séparément
    df_final["prenom_corrige"]      = corrections.apply(lambda x: x["prenom_corrige"])
    df_final["correction_faite"]    = corrections.apply(lambda x: x["correction_faite"])
    df_final["detail_corrections"]  = corrections.apply(lambda x: x["tokens_corriges"])


    return df_final


