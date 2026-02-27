from metriclib.metric import TabularMetric, MetricResult
from abc import ABC


class CustomMetric:
    """A custom metric example."""

    def __init__(self):
        pass


# Example of a custom metric that calculates the mean of a numeric field
# class AgeMean(CustomMetric, TabularMetric):
#     """A custom metric that calculates the mean of a numeric field."""
#
#     def __init__(self):
#         self.dimension = "variety_device"
#
#     def compute(self, data, **kwargs):
#         return MetricResult(
#             value=data["age"].mean(),
#             cluster="Representativeness",
#             description="Mean age in the dataset",
#         )
