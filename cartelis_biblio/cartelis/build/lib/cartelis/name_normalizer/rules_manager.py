import os
import shutil
import pandas as pd

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION DES MODES
# ══════════════════════════════════════════════════════════════════════════════

AVAILABLE_MODES = {
    "light":   "regles_normalisation_light.xlsx",
    "heavy": "regles_normalisation_heavy.xlsx",
}

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS INTERNES
# ══════════════════════════════════════════════════════════════════════════════

def _get_filename(mode: str) -> str:
    mode = mode.strip().lower()
    if mode not in AVAILABLE_MODES:
        raise ValueError(f"Mode '{mode}' inconnu. Modes disponibles : {list(AVAILABLE_MODES.keys())}")
    return AVAILABLE_MODES[mode]


def _get_default_path(mode: str) -> str:
    """Chemin vers le fichier Excel du paquet installé."""
    return os.path.join(_DATA_DIR, _get_filename(mode))


def _get_local_path(mode: str) -> str:
    """Chemin vers le fichier Excel local (dossier courant de l'utilisateur)."""
    return os.path.join(os.getcwd(), _get_filename(mode))


def _get_active_path(mode: str) -> str:
    """
    Retourne le chemin actif :
    - fichier local s'il existe (modifications de l'utilisateur)
    - sinon fichier du paquet installé (règles par défaut)
    """
    local = _get_local_path(mode)
    return local if os.path.exists(local) else _get_default_path(mode)


def _sheet_name(target: str) -> str:
    target = target.strip().lower()
    if target in ("prenom", "prénom"):
        return "regles_prenom"
    if target == "nom":
        return "regles_nom"
    raise ValueError(f"target doit être 'nom' ou 'prenom', reçu: '{target}'")


def _ensure_local_copy(mode: str) -> str:
    """Copie le fichier du paquet en local si pas encore fait. Retourne le chemin local."""
    local_path = _get_local_path(mode)
    if not os.path.exists(local_path):
        shutil.copy2(_get_default_path(mode), local_path)
    return local_path


# ══════════════════════════════════════════════════════════════════════════════
# MÉTHODES PUBLIQUES
# ══════════════════════════════════════════════════════════════════════════════

def show_rules(target: str, mode: str = "light") -> pd.DataFrame:
    '''
    Affiche les règles de normalisation pour "nom" ou "prenom".

    Parameters
    ----------
    target : str
        "nom" ou "prenom"
    mode : str, default "light"
        Mode de normalisation. Modes disponibles : "light", "heavy".

    Returns
    -------
    pandas.DataFrame
        Tableau des règles avec colonnes : pattern, description_pattern,
        regle_id, regle_description, colonne_source, action,
        colonne_secondaire, exemple_avant, exemple_apres.

    Examples
    --------
    >>> from cartelis_name_normalizer import show_rules
    >>> show_rules("prenom", mode="light")
    >>> show_rules("nom", mode="heavy")
    '''
    sheet = _sheet_name(target)
    path = _get_active_path(mode)
    return pd.read_excel(path, sheet_name=sheet, dtype=str).fillna("")


def update_rule(target: str, pattern: str, mode: str = "light", **kwargs) -> pd.DataFrame:
    '''
    Modifie une règle existante et sauvegarde dans un fichier local.

    Parameters
    ----------
    target : str
        "nom" ou "prenom"
    pattern : str
        Pattern de la règle à modifier (ex: "*S*", "W", "NA").
    mode : str, default "light"
        Mode de normalisation ciblé. Modes disponibles : "light", "heavy".
    **kwargs : dict
        Colonnes à modifier et leurs nouvelles valeurs.
        Ex: action="keep_as_is", regle_id="R1"

    Returns
    -------
    pandas.DataFrame
        Tableau mis à jour.

    Examples
    --------
    >>> from cartelis_name_normalizer import update_rule
    >>> update_rule("prenom", pattern="*S*", action="keep_as_is", mode="light")
    >>> update_rule("nom", pattern="W", action="keep_as_is", mode="heavy")
    '''
    sheet = _sheet_name(target)
    local_path = _ensure_local_copy(mode)

    all_sheets = pd.read_excel(local_path, sheet_name=None, dtype=str)
    df = all_sheets[sheet].fillna("")

    mask = df["pattern"] == pattern
    if not mask.any():
        raise ValueError(f"Pattern '{pattern}' introuvable dans l'onglet '{sheet}' (mode {mode}).")

    for col, val in kwargs.items():
        if col not in df.columns:
            raise ValueError(f"Colonne '{col}' inexistante. Colonnes disponibles : {list(df.columns)}")
        df.loc[mask, col] = val

    all_sheets[sheet] = df
    with pd.ExcelWriter(local_path, engine="openpyxl") as writer:
        for sname, sdf in all_sheets.items():
            sdf.to_excel(writer, sheet_name=sname, index=False)

    return df


def add_rule(target: str, pattern: str, action: str, colonne_source: str,
             mode: str = "light", regle_id: str = "", regle_description: str = "",
             colonne_secondaire: str = "", exemple_avant: str = "",
             exemple_apres: str = "", description_pattern: str = "",
             position: int = None) -> pd.DataFrame:
    '''
    Ajoute une nouvelle règle et sauvegarde dans un fichier local.

    Parameters
    ----------
    target : str
        "nom" ou "prenom"
    pattern : str
        Pattern à heavyer (ex: "W-W-W", "*S*", "NA").
    action : str
        Nom de l'action à appliquer (doit exister dans ACTION_MAP).
    colonne_source : str
        Colonne du DataFrame à utiliser comme source.
    mode : str, default "light"
        Mode de normalisation ciblé. Modes disponibles : "light", "heavy".
    regle_id : str, optional
        Identifiant de la règle (ex: "R1", "R5").
    regle_description : str, optional
        Description de la règle.
    colonne_secondaire : str, optional
        Colonne secondaire utilisée par certaines actions.
    exemple_avant : str, optional
        Exemple de valeur avant normalisation.
    exemple_apres : str, optional
        Exemple de valeur après normalisation.
    description_pattern : str, optional
        Description du pattern.
    position : int or None, optional
        Position d'insertion. Si None, ajouté avant le catch-all "*".

    Returns
    -------
    pandas.DataFrame
        Tableau mis à jour avec la nouvelle règle.

    Examples
    --------
    >>> from cartelis_name_normalizer import add_rule
    >>> add_rule("prenom", pattern="W-W-W", action="keep_as_is",
    ...          colonne_source="prenom_clean", mode="light", regle_id="R1")
    >>> add_rule("nom", pattern="W-W-W", action="keep_as_is",
    ...          colonne_source="nom_clean", mode="heavy", regle_id="R1")
    '''
    sheet = _sheet_name(target)
    local_path = _ensure_local_copy(mode)

    all_sheets = pd.read_excel(local_path, sheet_name=None, dtype=str)
    df = all_sheets[sheet].fillna("")

    if pattern in df["pattern"].values:
        raise ValueError(f"Pattern '{pattern}' existe déjà. Utilisez update_rule() pour le modifier.")

    new_row = {
        "pattern":             pattern,
        "description_pattern": description_pattern,
        "regle_id":            regle_id,
        "regle_description":   regle_description,
        "colonne_source":      colonne_source,
        "action":              action,
        "colonne_secondaire":  colonne_secondaire,
        "exemple_avant":       exemple_avant,
        "exemple_apres":       exemple_apres,
    }

    if position is None:
        catchall_idx = df.index[df["pattern"] == "*"].tolist()
        position = catchall_idx[0] if catchall_idx else len(df)

    df = pd.concat([df.iloc[:position], pd.DataFrame([new_row]), df.iloc[position:]], ignore_index=True)
    all_sheets[sheet] = df

    with pd.ExcelWriter(local_path, engine="openpyxl") as writer:
        for sname, sdf in all_sheets.items():
            sdf.to_excel(writer, sheet_name=sname, index=False)

    return df


def reset_rules(mode: str = "light") -> None:
    '''
    Supprime le fichier local et revient aux règles par défaut du paquet.

    Parameters
    ----------
    mode : str, default "light"
        Mode dont on veut réinitialiser les règles. Modes disponibles : "light", "heavy".

    Examples
    --------
    >>> from cartelis_name_normalizer import reset_rules
    >>> reset_rules(mode="light")
    >>> reset_rules(mode="heavy")
    '''
    local_path = _get_local_path(mode)
    if os.path.exists(local_path):
        os.remove(local_path)



def list_modes() -> list:
    '''
    Retourne la liste des modes de normalisation disponibles.

    Returns
    -------
    list
        Liste des modes disponibles.

    Examples
    --------
    >>> from cartelis_name_normalizer import list_modes
    >>> list_modes()
    ['light', 'heavy']
    '''
    return list(AVAILABLE_MODES.keys())