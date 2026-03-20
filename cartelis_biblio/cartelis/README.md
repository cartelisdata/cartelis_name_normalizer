# cartelis.name_normalizer

Bibliothèque Python de nettoyage et normalisation de noms et prénoms, conçue pour les équipes CRM et data.

---

## Installation

```bash
pip install cartelis
```

---

## Fonctionnement général

La bibliothèque applique une pipeline en 4 étapes sur les colonnes `nom` et `prenom` d'un DataFrame :

```
DataFrame brut
     │
     ▼
1. Nettoyage          → suppression accents, ponctuation, espaces multiples
     │
     ▼
2. Overlap cleaning   → résolution chevauchements nom/prénom (ex: "Jean Jean" → "Jean")
     │
     ▼
3. Pattern detection  → détection du schéma de chaque valeur (W, L, H, P, A, S)
     │
     ▼
4. Normalisation      → application des règles définies dans un fichier Excel (selon le mode)
     │
     ▼
DataFrame enrichi
```

### Schémas de tokens

| Classe | Description | Exemple |
|--------|-------------|---------|
| `W` | Mot alphabétique (≥2 lettres) | `MARIE` |
| `L` | Initiale (1 lettre) | `J` |
| `H` | Mot avec tiret | `ANNE-MARIE` |
| `A` | Mot avec apostrophe | `O'CONNOR` |
| `P` | Particule | `DE`, `DU`, `LA` |
| `S` | Caractère spécial ou chiffre | `MARIE123` |

---

## Utilisation

### Normalisation de base

```python
import pandas as pd
from cartelis import normalize_names

df = pd.DataFrame({
    "nom":    ["DE LA CROIX", "MARTIN3", "J M"],
    "prenom": ["MARIE PIER",  "JEAN",    "Anne-Marie"]
})

df_result = normalize_names(df, mode="light")
```

### Avec `inplace`

```python
# Sans inplace — retourne une copie, df original intact
df_result = normalize_names(df, mode="light")

# Avec inplace — modifie df directement
normalize_names(df, mode="light", inplace=True)
```

### Contrôle des étapes

```python
# Désactiver certaines étapes
df_result = normalize_names(
    df,
    mode="light",
    nettoyage=True,
    overlap_cleaning=False,
    pattern_detection=True,
    normalization=True,
)
```

### Modes disponibles

```python
from cartelis import list_modes
list_modes()  # → ['light', 'heavy']
```

| Mode | Description |
|------|-------------|
| `light` | Normalisation standard — conserve les prénoms composés, concat avec prenom2 si tronqué |
| `heavy` | Normalisation stricte — garde uniquement le premier prénom |

---

## Vérification et correction des prénoms

### Vérifier si les prénoms existent dans le dictionnaire

```python
from cartelis import verify_prenom

df_verified = verify_prenom(df, mode="light")
# Ajoute une colonne "prenom_all_exist" : "oui" ou "non"
```

### Rapprocher les prénoms mal orthographiés

```python
from cartelis import rapprocher_prenom

df_corrected = rapprocher_prenom(df, mode="light", THRESHOLD=90)
# Ajoute :
# - prenom_corrige      : prénom corrigé
# - correction_faite    : True si une correction a été appliquée
# - detail_corrections  : détail token par token
```

---

## Gestion des règles

Les règles de normalisation sont stockées dans des fichiers Excel (`regles_light.xlsx`, `regles_heavy.xlsx`) inclus dans le paquet. Vous pouvez les consulter, les modifier et les réinitialiser.

### Visualiser les règles

```python
from cartelis import show_rules

show_rules("prenom", mode="light")   # retourne un DataFrame
show_rules("nom", mode="heavy")
```

### Modifier une règle existante

```python
from cartelis import update_rule

# Les modifications sont sauvegardées en local (dans votre dossier courant)
update_rule("prenom", pattern="*S*", action="keep_as_is", mode="light")
```

### Ajouter une nouvelle règle

```python
from cartelis import add_rule

add_rule(
    target="prenom",
    pattern="W-W-W",
    action="keep_as_is",
    colonne_source="prenom_clean",
    mode="light",
    regle_id="R1",
    description_pattern="3 mots alphabétiques",
    exemple_avant="MARIE ANNE CLAIRE",
    exemple_apres="MARIE ANNE CLAIRE",
)
```

### Réinitialiser les règles par défaut

```python
from cartelis import reset_rules

reset_rules(mode="light")   # supprime le fichier local, retour aux règles du paquet
```

---

## Actions disponibles

| Action | Description |
|--------|-------------|
| `keep_as_is` | Conserver tel quel |
| `concat_prenom2` | Concaténer avec `prenom2` si disponible |
| `concat_nom_usage` | Concaténer avec `nomUsage` si disponible |
| `replace_by_nom_usage` | Remplacer par `nomUsage` si disponible |
| `filter_dict_tokens` | Garder uniquement les tokens présents dans le dictionnaire |
| `drop_truncated_last` | Supprimer le dernier token s'il est tronqué (absent du dictionnaire) |
| `clean_s_subtokens` | Nettoyer les sous-tokens contenant des caractères spéciaux |
| `drop_final_LP` | Supprimer les tokens finaux de type L (initiale) ou P (particule) |
| `keep_first_token` | Garder uniquement le premier prénom *(mode heavy)* |
| `insert_apostrophe_after_initial` | Insérer une apostrophe après l'initiale *(mode heavy)* |

---

## Colonnes ajoutées par `normalize_names`

| Colonne | Description |
|---------|-------------|
| `nom_clean` | Nom après nettoyage de base |
| `prenom_clean` | Prénom après nettoyage de base |
| `overlap_action` | Action appliquée lors du traitement des chevauchements |
| `schema_nom` | Schéma détecté pour le nom (ex: `W`, `W-P`, `H`) |
| `schema_prenom` | Schéma détecté pour le prénom |
| `nom_normalized` | Nom après normalisation complète |
| `prenom_normalized` | Prénom après normalisation complète |

---

## Structure du projet

```
cartelis/
├── __init__.py
├── name_normalizer/
│   ├── __init__.py
│   ├── module.py          ← normalize_names, verify_prenom, rapprocher_prenom
│   ├── rule_engine.py     ← chargement et matching des règles
│   ├── rules_manager.py   ← show/update/add/reset rules
│   ├── actions.py         ← fonctions d'action (communes à tous les modes)
│   ├── action_map.py      ← dictionnaire nom → fonction
│   └── data/
│       ├── base_prenoms.csv
│       ├── regles_normalisation_light.xlsx
│       └── regles_normalisation_heavy.xlsx
```

---

## Dépendances

```
pandas>=1.3
numpy>=1.21
openpyxl>=3.0
rapidfuzz>=3.0
```

---

## Licence

MIT
