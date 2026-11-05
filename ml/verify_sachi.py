"""Technical real-model evidence with central eligibility; not a production access grant."""
import argparse
import json
import math
import os
from datetime import date
from pathlib import Path

import joblib
import pandas as pd

from ml.common import ROOT, ARTIFACTS, sha256, write_json
from ml.radar import score_rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of',type=date.fromisoformat,required=True)
    parser.add_argument('--output',type=Path,default=ARTIFACTS/'sachi_integration.json')
    args=parser.parse_args()
    os.environ['SAATHI_AS_OF_DATE']=args.as_of.isoformat()
    from app.services.customers import load_customers
    customers=load_customers()
    frame=pd.read_json(ROOT/'data/radar_input.json')
    model_path=ARTIFACTS/'radar/model.joblib'
    model=joblib.load(model_path)
    eligible=frame[frame.customer_id.map(lambda cid:customers[cid].renewal_eligible)]
    scores=score_rows(model,eligible)
    assert len(scores)==len(eligible) and all(math.isfinite(r['risk_score']) and 0<=r['risk_score']<=1 for r in scores)
    records=[]
    for row in frame.itertuples():
        c=customers[row.customer_id]
        assert row.days_to_renewal==(c.renewal_date-args.as_of).days
        result=next((r for r in scores if r['customer_id']==c.customer_id),None)
        records.append({'customer_id':c.customer_id,'agent_id':c.agent_id,'product':c.product,
                        'days_to_renewal':row.days_to_renewal,'policy_status':c.policy_status,
                        'renewal_eligible':c.renewal_eligible,'eligibility_reason':c.eligibility_reason,
                        'consent':c.consent,'risk_score':result['risk_score'] if result else None})
    evidence={'as_of_date':args.as_of.isoformat(),'synthetic':True,'model_sha256':sha256(model_path),
              'input_sha256':sha256(ROOT/'data/radar_input.json'),'scoring':'real trained local model',
              'approved_product_access_verified':False,
              'limitations':'Technical eligibility/scoring evidence only. Protected endpoint uses test-only scoped identities in automated tests. Approved deployment credentials/product mapping and live Azure remain pending.',
              'customers':records}
    write_json(args.output,evidence)
    print(json.dumps(records,indent=2))


if __name__=='__main__': main()
