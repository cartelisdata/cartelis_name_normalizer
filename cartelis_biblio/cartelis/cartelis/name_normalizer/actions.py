import re
import os
import pandas as pd
import numpy as np
import unicodedata



# ══════════════════════════════════════════════════════════════════════════════
# ACTIONS DISPONIBLES
# ══════════════════════════════════════════════════════════════════════════════

def _keep_as_is(value, **_):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return str(value).strip() or None

def _concat(source, secondary, **_):
    s = None if not source or (isinstance(source, float) and np.isnan(source)) else str(source).strip()
    sec = None if not secondary or (isinstance(secondary, float) and np.isnan(secondary)) else str(secondary).strip()
    if sec:
        return f"{s} {sec}".strip() if s else sec
    return s

def _replace_by_secondary(source, secondary, **_):
    sec = None if not secondary or (isinstance(secondary, float) and np.isnan(secondary)) else str(secondary).strip()
    if sec:
        return sec
    return None if not source else str(source).strip() or None

def _filter_dict_tokens(value, prenom_set, **_):
    if not value:
        return None
    tokens = re.split(r"[\s\-]+", str(value))
    kept = [t for t in tokens if t and _normalize_token(t) in prenom_set]
    return " ".join(kept) or None

def _drop_truncated_last(value, schema, prenom_set, **_):
    if not value:
        return None
    real = re.sub(r"\s+", " ", str(value)).strip().split(" ")
    schema_parts = str(schema).strip().upper().split("-") if schema else []

    def drop_PL(tokens):
        while tokens and tokens[-1] in {"P", "L"}:
            tokens.pop()
        return tokens

    last_schema = schema_parts[-1] if schema_parts else None

    if last_schema == "H":
        sub = real[-1].split("-")
        last_sub = sub[-1] if sub else None
        if last_sub and last_sub not in prenom_set:
            sub = sub[:-1]
            if sub:
                real[-1] = "-".join(sub)
            else:
                real.pop()
            real = drop_PL(real)
        return " ".join(real).strip() or None

    last_sub = real[-1].split("-")[-1] if real else None
    if last_sub and last_sub in prenom_set:
        return " ".join(real).strip() or None

    real.pop()
    real = drop_PL(real)
    return " ".join(real).strip() or None

def _clean_s_subtokens(value, **_):
    if not value:
        return None
    s = str(value).strip().replace("?", "")
    tokens = [t for t in re.split(r"[\s\-_/\.,]+", s) if t]
    cleaned = []
    for t in tokens:
        t = re.sub(r"\d+", "", t)
        t = re.sub(r"[^A-Za-z']", "", t)
        t = re.sub(r"^'+|'+$", "", t)
        if t:
            cleaned.append(t)
    return " ".join(cleaned) or None

def _drop_final_LP(value, schema, **_):
    if not value:
        return None
    s = str(value).strip().replace("?", "")
    schema_parts = [x for x in str(schema).strip().upper().split("-") if x] if schema else []
    toks = [t for t in re.split(r"[\s\-_/\.,]+", s) if t]
    while schema_parts and schema_parts[-1] in {"L", "P"} and toks:
        schema_parts.pop()
        toks.pop()
    return " ".join(toks).strip() or None


def _normalize_token(s):
    import unicodedata
    if not isinstance(s, str):
        return None
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z\s]", " ", s.lower())
    return " ".join(s.split()).upper() or None



def _keep_first_token(value, **_):
    """Garde uniquement le premier token (premier prénom)."""
    if not value or (isinstance(value, float) and np.isnan(value)):
        return None
    return str(value).strip().split(" ")[0] or None
