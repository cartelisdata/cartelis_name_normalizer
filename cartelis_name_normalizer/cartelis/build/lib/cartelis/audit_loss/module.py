import pandas as pd

def audit_loss(df, col_raw, col_clean):
    """
    Audit des valeurs perdues et transformées après nettoyage, avec rapport par colonne clean.

    Parameters
    ----------
    df : pd.DataFrame
    col_raw : str
        Colonne source
    col_clean : str ou list[str]
        Colonne(s) nettoyée(s)

    Returns
    -------
    str
    """
    

    if isinstance(col_clean, str):
        col_clean = [col_clean]

    # Valeurs considérées comme "réelles" en entrée
    raw_as_str = df[col_raw].astype("string")
    mask_valid_raw = (
        df[col_raw].notna()
        & ~raw_as_str.str.strip().str.lower().isin(["none", "nan", ""])
    )

    nb_valid = mask_valid_raw.sum()

    output = []
    output.append("=== AUDIT LOSS ===")
    output.append(f"Colonne source : {col_raw}")
    output.append(f"Valeurs valides en entrée : {nb_valid}")
    output.append("")

    for clean_col in col_clean:
        clean_as_str = df[clean_col].astype("string")

        # Valeurs perdues
        mask_lost = mask_valid_raw & df[clean_col].isna()
        nb_lost = mask_lost.sum()
        pct_lost = round((nb_lost / nb_valid) * 100, 2) if nb_valid > 0 else 0

        top_lost = (
            df.loc[mask_lost, col_raw]
            .value_counts(dropna=False)
            .head(25)
        )

        # Valeurs transformées :
        # - source valide
        # - cible non nulle
        # - valeur différente après trim
        mask_transformed = (
            mask_valid_raw
            & df[clean_col].notna()
            & (raw_as_str.str.strip() != clean_as_str.str.strip())
        )

        nb_transformed = mask_transformed.sum()
        pct_transformed = round((nb_transformed / nb_valid) * 100, 2) if nb_valid > 0 else 0

        top_transformed = (
            df.loc[mask_transformed, [col_raw, clean_col]]
            .value_counts(dropna=False)
            .head(25)
        )

        output.append(f"--- Rapport pour : {clean_col} ---")
        output.append(f"Valeurs perdues : {nb_lost} ({pct_lost}%)")
        output.append(f"Valeurs transformées : {nb_transformed} ({pct_transformed}%)")
        output.append("")

        output.append("Top 25 valeurs perdues :")
        if len(top_lost) > 0:
            output.append(top_lost.to_string())
        else:
            output.append("Aucune valeur perdue.")
        output.append("")

        output.append("Top 25 transformations :")
        if len(top_transformed) > 0:
            output.append(top_transformed.to_string())
        else:
            output.append("Aucune transformation.")
        output.append("")

    return "\n".join(output)