# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

"""
Optional GPU/CPU dataframe accelerator for Deduplab.
Prefers cuDF, then pandas, else builtin Python structures.
"""
import importlib

def get_backend():
    cudf_spec = importlib.util.find_spec("cudf")
    if cudf_spec is not None:
        import cudf  # type: ignore
        return "cudf", cudf
    pd_spec = importlib.util.find_spec("pandas")
    if pd_spec is not None:
        import pandas as pd  # type: ignore
        return "pandas", pd
    return "builtin", None

class DataFrameWrapper:
    def __init__(self, records):
        self.backend, self.mod = get_backend()
        self.data = self._wrap(records)

    def _wrap(self, records):
        if self.backend == "cudf":
            return self.mod.DataFrame(records)
        if self.backend == "pandas":
            return self.mod.DataFrame(records)
        return list(records)  # builtin

    def groupby(self, key):
        if self.backend in ("cudf", "pandas"):
            return self.data.groupby(key)
        # builtin fallback
        from collections import defaultdict
        g = defaultdict(list)
        for r in self.data:
            g[r.get(key)].append(r)
        # yield as iterable of (key, list) to mirror groupby semantics
        return list(g.items())

    def sum(self, col):
        if self.backend in ("cudf", "pandas"):
            return int(self.data[col].sum())
        return int(sum(int(r.get(col, 0)) for r in self.data))

    def value_counts(self, col):
        if self.backend == "cudf":
            s = self.data[col].value_counts()
            return s.to_pandas().to_dict()
        if self.backend == "pandas":
            return self.data[col].value_counts().to_dict()
        # builtin
        from collections import Counter
        return dict(Counter([r.get(col) for r in self.data]))

    def to_records(self):
        if self.backend in ("cudf", "pandas"):
            return self.data.to_dict(orient="records")
        return list(self.data)
