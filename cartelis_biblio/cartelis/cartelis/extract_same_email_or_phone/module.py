import pandas as pd
import os
import re

def extract_same_address_or_phone(
    input_csv,
    output_dir="Duplicates_csvs",
    col_address="EMAIL",
    col_phone="PORTABLE",
    sep = ";"):
    """
    Pour chaque email dupliqué → un CSV dans output_dir/email_<email>.csv
    Pour chaque téléphone dupliqué → un CSV dans output_dir/phone_<tel>.csv
    """
    os.makedirs(output_dir, exist_ok=True)

    df = pd.read_csv(
        input_csv,
        encoding="utf-8",
        dtype={col_phone: str},
        sep=sep,
        on_bad_lines="skip"
    )

    # Nettoyage (fillna avant astype pour éviter la string "nan")
    df[col_address] = df[col_address].fillna("").astype(str).str.strip()
    df[col_phone]   = df[col_phone].str.strip().fillna("")

    def safe_filename(value):
        """Supprime les caractères interdits dans un nom de fichier."""
        return re.sub(r'[^\w\-@.]', '_', value)

    files_created = 0
    rows_email    = 0
    rows_phone    = 0

    # ── Groupes par EMAIL ──────────────────────────────────────────────────────
    for email, group in df[df[col_address] != ""].groupby(col_address):
        if len(group) > 1:
            path = os.path.join(output_dir, f"email_{safe_filename(email)}.csv")
            group.to_csv(path, index=False, encoding="utf-8")
            files_created += 1
            rows_email    += len(group)

    # ── Groupes par TÉLÉPHONE ─────────────────────────────────────────────────
    for phone, group in df[df[col_phone] != ""].groupby(col_phone):
        if len(group) > 1:
            path = os.path.join(output_dir, f"phone_{safe_filename(phone)}.csv")
            group.to_csv(path, index=False, encoding="utf-8")
            files_created += 1
            rows_phone    += len(group)

    # ── Résumé ────────────────────────────────────────────────────────────────
    print(f"=== Résumé ===")
    print(f"Fichiers créés     : {files_created}  (dans '{output_dir}/')")
    print(f"Lignes (email)     : {rows_email}")
    print(f"Lignes (téléphone) : {rows_phone}")

    return files_created




