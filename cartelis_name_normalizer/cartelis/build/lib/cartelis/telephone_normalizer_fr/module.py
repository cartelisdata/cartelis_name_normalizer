import pandas as pd

def normalize_phone_vectorized(s: pd.Series, mode: str = "safe") -> pd.Series:
    if mode not in {"safe", "match"}:
        raise ValueError("mode must be 'safe' or 'match'")

    s = s.copy()

    # nettoyage de base
    s = s.astype("string").str.strip()
    s = s.mask(s.str.lower().isin(["none", "nan", ""]), pd.NA)

    phone_clean = s.str.replace(r"[^\d+]", "", regex=True)
    digits = phone_clean.str.replace(r"\D", "", regex=True)

    result = pd.Series(pd.NA, index=s.index, dtype="string")

    # --------------------------------------------------
    # 1) formats déjà propres
    # --------------------------------------------------

    # FR métropole / DOM en format national : 0 + 9 chiffres
    mask_fr_10 = digits.str.match(r"^0\d{9}$", na=False)
    result.loc[mask_fr_10] = digits.loc[mask_fr_10]

    # formats locaux à 8 chiffres (Polynésie / NC / autres contextes locaux)
    mask_local_8 = digits.str.match(r"^\d{8}$", na=False) & result.isna()
    result.loc[mask_local_8] = digits.loc[mask_local_8]

    # 9 chiffres nus -> on suppose qu'il manque juste le 0 initial
    mask_9 = digits.str.match(r"^\d{9}$", na=False) & result.isna()
    result.loc[mask_9] = "0" + digits.loc[mask_9]

    # --------------------------------------------------
    # 2) formats internationaux France métropole
    # --------------------------------------------------

    # +33XXXXXXXXX -> 0XXXXXXXXX
    mask_plus33 = (
        phone_clean.str.startswith("+33", na=False)
        & digits.str.match(r"^33\d{9}$", na=False)
        & result.isna()
    )
    result.loc[mask_plus33] = "0" + digits.loc[mask_plus33].str[2:]

    # 0033XXXXXXXXX -> 0XXXXXXXXX
    mask_0033 = (
        phone_clean.str.startswith("0033", na=False)
        & digits.str.match(r"^0033\d{9}$", na=False)
        & result.isna()
    )
    result.loc[mask_0033] = "0" + digits.loc[mask_0033].str[4:]

    # +330XXXXXXXXX -> 0XXXXXXXXX
    mask_plus330 = (
        phone_clean.str.startswith("+330", na=False)
        & digits.str.match(r"^330\d{9}$", na=False)
        & result.isna()
    )
    result.loc[mask_plus330] = "0" + digits.loc[mask_plus330].str[3:]

    # 00330XXXXXXXXX -> 0XXXXXXXXX
    mask_00330 = (
        phone_clean.str.startswith("00330", na=False)
        & digits.str.match(r"^00330\d{9}$", na=False)
        & result.isna()
    )
    result.loc[mask_00330] = "0" + digits.loc[mask_00330].str[5:]

    # --------------------------------------------------
    # 3) territoires avec numéros locaux à 9 chiffres
    # sortie: 0 + 9 chiffres
    # --------------------------------------------------

    overseas_prefixes_9_to_10 = ["262", "590", "594", "596", "687", "681"]

    for prefix in overseas_prefixes_9_to_10:
        # +prefix + 9 chiffres -> 0 + local
        mask_plus = phone_clean.str.startswith("+" + prefix, na=False) & result.isna()
        local_plus = digits.loc[mask_plus].str[len(prefix):]
        valid_plus = local_plus.str.match(r"^\d{9}$", na=False)
        idx_plus = local_plus[valid_plus].index
        result.loc[idx_plus] = "0" + local_plus.loc[idx_plus]

        # 00prefix + 9 chiffres -> 0 + local
        mask_00 = phone_clean.str.startswith("00" + prefix, na=False) & result.isna()
        local_00 = digits.loc[mask_00].str[len("00" + prefix):]
        valid_00 = local_00.str.match(r"^\d{9}$", na=False)
        idx_00 = local_00[valid_00].index
        result.loc[idx_00] = "0" + local_00.loc[idx_00]

        # +prefix0 + 9 chiffres -> 0 + local (0 parasite après indicatif)
        mask_plus_zero = phone_clean.str.startswith("+" + prefix + "0", na=False) & result.isna()
        local_plus_zero = digits.loc[mask_plus_zero].str[len(prefix):].str.lstrip("0")
        valid_plus_zero = local_plus_zero.str.match(r"^\d{9}$", na=False)
        idx_plus_zero = local_plus_zero[valid_plus_zero].index
        result.loc[idx_plus_zero] = "0" + local_plus_zero.loc[idx_plus_zero]

        # 00prefix0 + 9 chiffres -> 0 + local (0 parasite après indicatif)
        mask_00_zero = phone_clean.str.startswith("00" + prefix + "0", na=False) & result.isna()
        local_00_zero = digits.loc[mask_00_zero].str[len("00" + prefix):].str.lstrip("0")
        valid_00_zero = local_00_zero.str.match(r"^\d{9}$", na=False)
        idx_00_zero = local_00_zero[valid_00_zero].index
        result.loc[idx_00_zero] = "0" + local_00_zero.loc[idx_00_zero]

    # --------------------------------------------------
    # 4) territoires avec numéros locaux à 8 chiffres
    # ex: +68940410900 -> 40410900
    # --------------------------------------------------

    overseas_prefixes_8 = ["689"]

    for prefix in overseas_prefixes_8:
        # +689XXXXXXXX -> XXXXXXXX
        mask_plus = phone_clean.str.startswith("+" + prefix, na=False) & result.isna()
        local_plus = digits.loc[mask_plus].str[len(prefix):]
        valid_plus = local_plus.str.match(r"^\d{8}$", na=False)
        idx_plus = local_plus[valid_plus].index
        result.loc[idx_plus] = local_plus.loc[idx_plus]

        # 00689XXXXXXXX -> XXXXXXXX
        mask_00 = phone_clean.str.startswith("00" + prefix, na=False) & result.isna()
        local_00 = digits.loc[mask_00].str[len("00" + prefix):]
        valid_00 = local_00.str.match(r"^\d{8}$", na=False)
        idx_00 = local_00[valid_00].index
        result.loc[idx_00] = local_00.loc[idx_00]

        # +6890XXXXXXXX -> XXXXXXXX (0 parasite)
        mask_plus_zero = phone_clean.str.startswith("+" + prefix + "0", na=False) & result.isna()
        local_plus_zero = digits.loc[mask_plus_zero].str[len(prefix):].str.lstrip("0")
        valid_plus_zero = local_plus_zero.str.match(r"^\d{8}$", na=False)
        idx_plus_zero = local_plus_zero[valid_plus_zero].index
        result.loc[idx_plus_zero] = local_plus_zero.loc[idx_plus_zero]

        # 006890XXXXXXXX -> XXXXXXXX (0 parasite)
        mask_00_zero = phone_clean.str.startswith("00" + prefix + "0", na=False) & result.isna()
        local_00_zero = digits.loc[mask_00_zero].str[len("00" + prefix):].str.lstrip("0")
        valid_00_zero = local_00_zero.str.match(r"^\d{8}$", na=False)
        idx_00_zero = local_00_zero[valid_00_zero].index
        result.loc[idx_00_zero] = local_00_zero.loc[idx_00_zero]
        
        # 33XXXXXXXXX -> 0XXXXXXXXX
        mask_33 = (digits.str.match(r"^33\d{9}$", na=False)& result.isna())
        result.loc[mask_33] = "0" + digits.loc[mask_33].str[2:]

        # 330XXXXXXXXX -> 0XXXXXXXXX
        mask_330 = (digits.str.match(r"^330\d{9}$", na=False)& result.isna())
        result.loc[mask_330] = "0" + digits.loc[mask_330].str[3:]

    # --------------------------------------------------
    # 5) heuristiques supplémentaires uniquement en mode match
    # --------------------------------------------------

    if mode == "match":
        # 11 chiffres commençant par 0 :
        # on tente de garder les 10 derniers si cela donne un format national plausible
        mask_11 = digits.str.match(r"^0\d{10}$", na=False) & result.isna()
        last10 = digits.loc[mask_11].str[-10:]
        valid_last10 = last10.str.match(r"^0\d{9}$", na=False)
        idx_last10 = last10[valid_last10].index
        result.loc[idx_last10] = last10.loc[idx_last10]

        # 9 chiffres commençant par 0 :
        # on tente de garder les 8 derniers pour les numéros locaux
        mask_9_leading0 = digits.str.match(r"^0\d{8}$", na=False) & result.isna()
        last8 = digits.loc[mask_9_leading0].str[-8:]
        valid_last8 = last8.str.match(r"^\d{8}$", na=False)
        idx_last8 = last8[valid_last8].index
        result.loc[idx_last8] = last8.loc[idx_last8]

        # chaînes longues : on tente de récupérer la fin si elle ressemble à un numéro exploitable
        mask_long = digits.str.len().gt(11) & result.isna()

        # priorité au format national 10 chiffres sur la fin
        last10_long = digits.loc[mask_long].str[-10:]
        valid_last10_long = last10_long.str.match(r"^0\d{9}$", na=False)
        idx_last10_long = last10_long[valid_last10_long].index
        result.loc[idx_last10_long] = last10_long.loc[idx_last10_long]

        # puis format local 8 chiffres sur la fin
        remaining_long = mask_long & result.isna()
        last8_long = digits.loc[remaining_long].str[-8:]
        valid_last8_long = last8_long.str.match(r"^\d{8}$", na=False)
        idx_last8_long = last8_long[valid_last8_long].index
        result.loc[idx_last8_long] = last8_long.loc[idx_last8_long]

        # cas 10 chiffres nus ne commençant pas par 0 :
        # on les garde tels quels pour matching
        mask_10_no0 = digits.str.match(r"^[1-9]\d{9}$", na=False) & result.isna()
        result.loc[mask_10_no0] = digits.loc[mask_10_no0]

        # cas internationaux en 00* : on tente de récupérer les 10 derniers chiffres
        mask_00_intl = (
            phone_clean.str.startswith("00", na=False)
            & digits.str.len().ge(10)
            & result.isna()
        )
        last10_00 = digits.loc[mask_00_intl].str[-10:]
        valid_last10_00 = last10_00.str.match(r"^\d{10}$", na=False)
        idx_last10_00 = last10_00[valid_last10_00].index
        result.loc[idx_last10_00] = last10_00.loc[idx_last10_00]

        # cas internationaux en +* hors préfixes déjà traités : on récupère les 10 derniers chiffres
        known_plus_prefixes = ["+33", "+262", "+590", "+594", "+596", "+687", "+681", "+689"]
        mask_plus_intl = phone_clean.str.startswith("+", na=False) & result.isna()
        for kp in known_plus_prefixes:
            mask_plus_intl = mask_plus_intl & ~phone_clean.str.startswith(kp, na=False)

        last10_plus = digits.loc[mask_plus_intl].str[-10:]
        valid_last10_plus = last10_plus.str.match(r"^\d{10}$", na=False)
        idx_last10_plus = last10_plus[valid_last10_plus].index
        result.loc[idx_last10_plus] = last10_plus.loc[idx_last10_plus]
        
        # --------------------------------------------------
        # 6) cas FR avec 11 chiffres -> on prend les 10 premiers
        # ex: 02996208134 -> 0299620813
        # --------------------------------------------------

        mask_11_fr = (
            digits.str.match(r"^0\d{10}$", na=False)
            & result.isna()
        )

        first10 = digits.loc[mask_11_fr].str[:10]
        valid_first10 = first10.str.match(r"^0\d{9}$", na=False)

        idx_first10 = first10[valid_first10].index
        result.loc[idx_first10] = first10.loc[idx_first10]

    return result