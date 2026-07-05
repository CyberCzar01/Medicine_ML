import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from urotriage.train import train


def main():
    results = train()
    m = results["test_metrics"]
    u = results["ml_green_upgrade_uplift_test"]
    print(f"cohort n: {results['cohort_n_features']}  target prevalence: {results['target_prevalence']:.3f}")
    print(f"target components: {results['target_components']}")
    print(f"calibration: {results['calibration_method']}  threshold: {results['green_upgrade_threshold']}")
    print(f"TEST roc={m['roc_auc']:.3f} pr={m['pr_auc']:.3f} brier={m['brier']:.3f} ece={m['ece']:.3f}")
    print(f"rule zones (test): {results['rule_zone_distribution_test']}")
    print(f"green-upgrade uplift (test): {u}")


if __name__ == "__main__":
    main()
