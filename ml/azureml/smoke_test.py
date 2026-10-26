"""Real Azure invocation; stores a redacted endpoint test receipt, not a screenshot."""
import asyncio

import pandas as pd

from api.app.services.ml_service import renewal_worklist
from ml.common import ARTIFACTS, DATA, write_json


async def main():
    import os
    if os.getenv("ML_PROVIDER")!="azure":
        raise RuntimeError("Set ML_PROVIDER=azure for a real endpoint smoke test")
    frame = pd.read_csv(DATA / "radar.csv").head(10)
    result = await renewal_worklist(frame)
    write_json(ARTIFACTS / "azure_smoke_test.json",{"status":"passed","provider":"azure","synthetic":True,
        "submitted_n":int(frame.consent.sum()),"received_n":len(result),"response":result})
    print("Real Azure endpoint test passed; receipt: artifacts/azure_smoke_test.json")


if __name__ == "__main__":
    asyncio.run(main())
