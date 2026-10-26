"""Azure job entry point: train and evaluate Radar inside Azure compute."""
import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from data.validate import radar_schema
from ml.common import SEED, sha256, write_json
from ml.radar import FEATURES


def main(data,output):
    frame = radar_schema.validate(pd.read_csv(data))
    train,test = train_test_split(frame,test_size=0.25,stratify=frame.nonrenewed,random_state=SEED)
    model = make_pipeline(StandardScaler(),LogisticRegression(max_iter=1000,random_state=SEED))
    model.fit(train[FEATURES],train.nonrenewed)
    output = Path(output)
    output.mkdir(parents=True,exist_ok=True)
    joblib.dump(model,output / "model.joblib")
    write_json(output / "training_metrics.json",{"roc_auc":float(roc_auc_score(test.nonrenewed,model.predict_proba(test[FEATURES])[:,1])),
        "seed":SEED,"synthetic":True,"data_sha256":sha256(data),"train_n":len(train),"test_n":len(test)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data",required=True)
    parser.add_argument("--output",required=True)
    args = parser.parse_args()
    main(args.data,args.output)
