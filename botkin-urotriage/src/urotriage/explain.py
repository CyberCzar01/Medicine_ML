import math


def global_top_features(importances, k=8):
    items = [(name, float(w)) for name, w in importances.items()]
    items.sort(key=lambda kv: kv[1], reverse=True)
    return items[:k]


def explain_patient(importances, feature_values, k=6):
    out = []
    for name, weight in global_top_features(importances, k):
        v = feature_values.get(name)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            value = None
        else:
            value = float(v) if isinstance(v, (int, float)) else v
        out.append({"feature": name, "value": value, "importance": round(weight, 4), "kind": "global_importance"})
    return out
