from .name_normalizer import normalize_names, verify_prenom, rapprocher_prenom, normalize_names_pipeline, show_rules, update_rule, add_rule, reset_rules, list_modes
from .telephone_normalizer_fr import normalize_phone_vectorized
from .audit_loss import audit_loss
from .region_identifier import *
from .extract_same_email_or_phone import *

__version__ = "1.8.7"