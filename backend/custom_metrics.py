from metriclib.metric import StreamMetric, TabularMetric, MetricResult
import numpy as np
from abc import ABC


class CustomMetric:
    def __init__(self):
        pass


# Example of a custom tabular metric that calculates the mean of a numeric field
# class AgeMean(CustomMetric, TabularMetric):
#    """A custom metric that calculates the mean of a numeric field."""
#
#    def __init__(self):
#        self.dimension = "variety_age"
#
#    def compute(self, data, **kwargs):
#        return MetricResult(
#            value=data["age"].mean(),
#            cluster="Representativeness",
#            description="Mean age in the dataset",
#        )


#
# Example of a custom stream metric that
# class ECGNoise(CustomMetric, StreamMetric):
#    """A custom metric that calculates the noise level in ECG signals."""
#
#    def __init__(self):
#        self.dimension = "signal_precision"
#
#    def aggregate(self, datapoint, reference=None, metric_config=None):
#        return np.std(np.array(datapoint[0]))
#
#    def compute(self, data, **kwargs):
#        return MetricResult(
#            value=np.array(data).mean(),
#            cluster=None,
#            description="Average noise level in ECG signals",
#        )
