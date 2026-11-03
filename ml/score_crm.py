"""Record technical Radar compatibility evidence, without claiming policy eligibility."""
import argparse
import json
from datetime import date
from pathlib import Path

import joblib
import pandas as pd

from ml.common import ARTIFACTS, sha256, write_json
from ml.radar import FEATURES, score_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--as-of', type=date.fromisoformat, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    model_path = ARTIFACTS / 'radar/model.joblib'
    frame = pd.DataFrame(json.loads(args.input.read_text()))
    result = score_rows(joblib.load(model_path), frame)
    write_json(args.output, {
        'status': 'technical scoring compatibility passed', 'synthetic': True,
        'as_of_date': args.as_of.isoformat(), 'input_sha256': sha256(args.input),
        'model_sha256': sha256(model_path), 'features': FEATURES,
        'input_n': len(frame), 'scored_n': len(result),
        'no_consent_ids': frame.loc[~frame.consent, 'customer_id'].tolist(),
        'results': result,
        'limitations': 'Technical scoring only. Consent does not filter visibility. Policy eligibility and customer/product authorization are not verified; this output is not an approved application worklist. Synthetic model outcomes are not real-world risk probabilities.',
    })
    print(f'Scored {len(result)} of {len(frame)} synthetic CRM rows; evidence: {args.output}')


if __name__ == '__main__':
    main()
