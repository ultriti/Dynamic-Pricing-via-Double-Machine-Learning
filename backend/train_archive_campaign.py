import json

from archive_campaign import train_archive_campaign_model


if __name__ == "__main__":
    result = train_archive_campaign_model()
    report = result["report"]
    print(
        json.dumps(
            {
                "model": "EconML CausalForestDML",
                "campaign_id": report["campaign_id"],
                "cohort_rows": report["cohort_rows"],
                "treated_households": report["treated_households"],
                "control_households": report["control_households"],
                "outcome_mean_ite": report["outcome_mean_ite"],
                "heldout_outperforms_random": report["holdout_evaluation"][
                    "outperforms_random"
                ],
                "propensity_matched_households": report["propensity_matching"][
                    "treated_matched"
                ],
                "completed_refutations": report["dowhy_audit"][
                    "completed_refutations"
                ],
                "model_artifact": "models/archive_campaign_18_dml.joblib",
                "review_report": "data/processed/archive_campaign_18_review.json",
            },
            indent=2,
        )
    )
