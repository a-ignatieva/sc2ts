import logging

import tsinfer
import numpy as np

def infer(sd, *, mismatch_ratio=None, **kwargs):
    if mismatch_ratio is None:
        # Default to no recombination
        mismatch_ratio = 1e10

    dates = np.array([ind.metadata["date"] for ind in sd.individuals()])
    unique_dates = np.unique(dates)
    print("mismatch_ratio", mismatch_ratio)
    extender = tsinfer.SequentialExtender(sd)
    for date in unique_dates:
        samples = np.where(dates == date)[0]
        logging.info(f"date={date} {len(samples)} samples")
        ts = extender.extend(samples,
                recombination_rate=1e-8,
                mismatch_ratio=mismatch_ratio,
                **kwargs)
        yield date, ts


