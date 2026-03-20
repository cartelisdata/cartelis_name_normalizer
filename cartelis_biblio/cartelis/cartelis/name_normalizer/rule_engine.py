import re
import os
import pandas as pd
import numpy as np
from .action_map import ACTION_MAP
from .actions import _normalize_token
from .rules_manager import _get_active_path, _get_local_path, _sheet_name


# ══════════════════════════════════════════════════════════════════════════════
# CHARGEMENT DES RÈGLES DEPUIS L'EXCEL
# ══════════════════════════════════════════════════════════════════════════════

_RULES_FILES = {
    "light":   "regles_normalisation_light.xlsx",
    "heavy": "regles_normalisation_heavy.xlsx"}

def _load_rules(sheet_name, mode: str = "light"):
    path = _get_active_path(mode)
    df = pd.read_excel(path, sheet_name=sheet_name, dtype=str).fillna("")
    return df.to_dict(orient="records")

def _match_pattern(pattern: str, schema: str) -> bool:
    """
    Vérifie si un schema correspond à un pattern du tableau :
    - "*S*"  : schema contient "S"
    - "*-L"  : schema finit par "-L"
    - "*-P"  : schema finit par "-P"
    - "W-*"  : schema commence par "W-" (W suivi d'un tiret et autre chose)
    - "*"    : catch-all (toujours vrai)
    - exact  : "W", "H", "NA", etc.
    """
    if pattern == "*": 
        return True
    if pattern == "NA":
        return schema in ("", "NA", None)
    if "*S*" in pattern:
        return "S" in schema
    if pattern.startswith("*-"):
        suffix = pattern[2:]
        parts = schema.split("-")
        return parts[-1] == suffix if parts else False
    if pattern.endswith("-*"):
        prefix = pattern[:-2]
        parts = schema.split("-")
        return parts[0] == prefix and len(parts) > 1 if parts else False
    return schema == pattern

def _find_rule(rules: list, schema: str) -> dict:
    """Parcourt les règles dans l'ordre et retourne la première qui matche."""
    schema_norm = "" if (schema is None or pd.isna(schema)) else str(schema).strip().upper()
    for rule in rules:
        if _match_pattern(rule["pattern"], schema_norm):
            return rule
    return None







# ══════════════════════════════════════════════════════════════════════════════
# FONCTIONS PRINCIPALES
# ══════════════════════════════════════════════════════════════════════════════

def apply_rule(row: dict, rules: list, schema_col : str, prenom_set: set = None) -> str:
    """
    Pour une ligne du DataFrame :
    1. Récupère le schema
    2. Trouve la règle correspondante dans le tableau
    3. Applique l'action
    """
    schema = row.get(schema_col)
    rule = _find_rule(rules, schema)
    if rule is None:
        return None

    action_fn = ACTION_MAP.get(rule["action"])
    if action_fn is None:
        return None

    source_col = rule["colonne_source"]
    secondary_col = rule.get("colonne_secondaire", "")

    source = row.get(source_col)
    secondary = row.get(secondary_col) if secondary_col else None

    return action_fn(
        value=source,
        source=source,
        secondary=secondary,
        schema=schema,
        prenom_set=prenom_set or set(),
    )


def build_prenom_normalized(row, prenom_set, rules_prenom):
    return apply_rule({**row, "schema_prenom": row.get("schema_prenom")},
                      rules=rules_prenom, prenom_set=prenom_set)

def build_nom_normalized(row, rules_nom):
    return apply_rule({**row, "schema_nom": row.get("schema_nom")},
                      rules=rules_nom)
