from .actions import (
    _keep_as_is,
    _concat,
    _replace_by_secondary,
    _filter_dict_tokens,
    _drop_truncated_last,
    _clean_s_subtokens,
    _drop_final_LP,
    _keep_first_token,
)

ACTION_MAP = {
    "keep_as_is":           _keep_as_is,
    "concat_prenom2":       _concat,
    "concat_nom_usage":     _concat,
    "replace_by_nom_usage": _replace_by_secondary,
    "filter_dict_tokens":   _filter_dict_tokens,
    "drop_truncated_last":  _drop_truncated_last,
    "clean_s_subtokens":    _clean_s_subtokens,
    "drop_final_LP":        _drop_final_LP,
    "keep_first_token":     _keep_first_token,
}