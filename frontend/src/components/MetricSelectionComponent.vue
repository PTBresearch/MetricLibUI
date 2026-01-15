<template>
  <div class="dashboard-container">
    <div class="dashboard">
      <div class="tabs">
        <button
          v-for="tab in topTabs"
          :key="tab"
          :class="{ active: tab === activeTopTab }"
          @click="changeTopTab(tab)"
        >
          {{ tab }}
        </button>
      </div>

      <div
        v-if="subTabsMap[activeTopTab] && subTabsMap[activeTopTab].length"
        class="sub-tabs"
      >
        <button
          v-for="subTab in subTabsMap[activeTopTab]"
          :key="subTab"
          :class="[
            { active: subTab === activeSubTab },
            isDisabledSubtab(subTab) ? 'disabled-subtab' : (isEmptySubtab(subTab) ? 'empty-subtab' : '')
          ]"
          @click="!isDisabledSubtab(subTab) && !isEmptySubtab(subTab) && (activeSubTab = subTab)"
          :disabled="isDisabledSubtab(subTab) || isEmptySubtab(subTab)"
        >
          {{ subTab }}
        </button>
      </div>

      <!-- Content display -->
      <div v-if="tableHeaders.length" class="content-section">
        <table class="content-table">
          <thead>
            <tr>
              <th v-for="(key, idx) in tableHeaders" :key="idx">{{ key }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="i in maxRows" :key="i">
              <td v-for="(col, j) in columns" :key="j">
                <button
                  v-if="col[i - 1]"
                  class="content-button"
                  :class="{ selected: isMetricSelected(col[i - 1]) }"
                  @click="handleMetricClick(col[i - 1])"
                >
                  {{ col[i - 1] }}
                </button>
                <div v-else class="content-placeholder"></div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div
      v-if="plotlyVisible"
      id="plotly-chart"
      class="plotly-wrapper"
    ></div>
  </div>
</template>

<script>
import Plotly from "plotly.js-dist";

export default {
  name: "MetricsSelectionComponent",
  props: {
    report: Object
  },
  data() {
    return {
      activeTopTab: "Representativeness",
      activeSubTab: "variety",
      selectedItems: null,
      plotlyVisible: false,

      topTabs: [
        "Measurement Process",
        "Timeliness",
        "Representativeness",
        "Informativeness",
        "Consistency",
      ],
      subTabsMap: {
        "Measurement Process": [
          "device error",
          "human induced error",
          "completeness",
          "source credibility",
        ],
        Timeliness: ["timeliness"],
        Representativeness: [
          "variety",
          "depth of data",
          "target class balance",
        ],
        Informativeness: [
          "understandability",
          "redundancy",
          "informative missingness",
          "feature importance",
        ],
        Consistency: [
          "rule-based consistency",
          "logical consistency",
          "distribution consistency",
        ],
      },
      metricsData: {
        "Measurement Process": {
          "device error": {
            accuracy: [],
            precision: [],
          },
          "human induced error": {
            "noisy labels": [],
            carelessness: [],
            outliers: ["local_outlier_factor"],
          },
          completeness: ["completeness"],
          "source credibility": {
            expertise: [],
            traceability: [],
            "data poisoning": [],
          },
        },
        Timeliness: {
          timeliness: {
            age: [],
            currency: ["currency"],
          },
        },
        Representativeness: {
          variety: {
            "variety in demographics": [
              "variety_age",
              "variety_sex",
              "variety_height",
              "variety_weight",
            ],
            "variety in data sources": [
              "variety_device",
              "variety_site",
            ],
          },
          "depth of data": {
            "dataset size": ["dataset_size"],
            granularity: [],
            coverage: ["coverage_device_sex"],
          },
          "target class balance": ["class_balance"],
        },
        Informativeness: {
          understandability: [],
          redundancy: {
            conceciseness: [],
            uniqueness: ["uniqueness"],
          },
          "informative missingness": [],
          "feature importance": ["correlations"],
        },
        Consistency: {
          "rule-based consistency": {
            "syntactic consistency": [],
            compliance: [],
          },
          "logical consistency": {
            "semantic consistency": [],
            plausibility: [],
          },
          "distrbution consistency": {
            homogeneity: [],
            "distribution drift": [],
          },
        },
      },
      additionalMerged: false,
    };
  },
  computed: {
    rawSubData() {
      const topLevel = this.metricsData[this.activeTopTab];
      return topLevel?.[this.activeSubTab];
    },
    isDirectList() {
      return Array.isArray(this.rawSubData);
    },
    tableHeaders() {
      if (this.isDirectList) return [this.activeSubTab];
      if (typeof this.rawSubData === "object" && this.rawSubData !== null) {
        return Object.keys(this.rawSubData);
      }
      return [];
    },
    columns() {
      if (this.isDirectList) return [this.rawSubData];
      if (typeof this.rawSubData === "object" && this.rawSubData !== null) {
        return Object.values(this.rawSubData);
      }
      return [];
    },
    maxRows() {
      return Math.max(1, ...this.columns.map((col) => col.length));
    },
  },
  methods: {
    changeTopTab(tab) {
      this.activeTopTab = tab;
      const defaultSubTab = this.subTabsMap[tab]?.[0] || "";
      this.activeSubTab = defaultSubTab;
      this.plotlyVisible = false;
      this.selectedItems = null;
      this.$nextTick(() => {
        this.renderPlotlyChart(null);
      });
    },
    isMetricSelected(item) {
      return this.selectedItems === item;
    },
    handleMetricClick(item) {
      if (this.selectedItems === item) {
        this.selectedItems = null;
        this.plotlyVisible = false;
        this.$nextTick(() => {
          this.renderPlotlyChart(null);
        });
      } else {
        this.selectedItems = item;
        this.plotlyVisible = true;
        this.$nextTick(() => {
          this.renderPlotlyChart(item);
        });
      }
    },
    async renderPlotlyChart(item) {
      if (!item) item = this.selectedItems;
      const chartId = 'plotly-chart';
      const chartEl = document.getElementById(chartId);
      if (!chartEl) return;

      chartEl.innerHTML = '';

      try {
        const metrics = this.report.metrics;
      
        if (!this.additionalMerged && metrics && metrics.additional_metrics) {
          this.mergeAdditionalMetrics(metrics.additional_metrics);
          this.additionalMerged = true;
        }
      
        const metric_values = (metrics.value ?? metrics).filter(
          entry => entry?.name === item
        );
      
        if (!metric_values.length) {
          chartEl.innerHTML = '<div style="color:red">No data found for this metric.</div>';
          return;
        }
      
        const allDescriptions = new Set();
        metric_values.forEach(entry => {
          if (entry.result?.description) {
            allDescriptions.add(entry.result.description);
          }
        });
      
        const orderedDescriptions = [...allDescriptions].sort();

        const datasetMap = new Map();
        metric_values.forEach(entry => {
          const dataset = entry.dataset;
          if (!datasetMap.has(dataset)) {
            datasetMap.set(dataset, {});
          }

          const rowData = datasetMap.get(dataset);
          const description = entry.result?.description;
          const value = entry.result?.value;

          if (description) {
            rowData[description] = value;
          }
        });
      
        const scoreTableHTML = `
          <h5 style="margin: 0 0 6px 0; font-size: 0.8rem;">Scores</h5>
          <table style="width: 100%; border-collapse: collapse; font-size: 0.7rem; text-align: center;">
            <thead>
              <tr>
                <th style="border: 1px solid #555; padding: 4px 8px; background: #222; color: #ddd;">Dataset</th>
                ${orderedDescriptions.map(desc => `
                  <th style="border: 1px solid #555; padding: 4px 8px; background: #222; color: #ddd;">${desc}</th>
                `).join('')}
              </tr>
            </thead>
            <tbody>
              ${Array.from(datasetMap.entries()).map(([dataset, rowData]) => {
                return `
                  <tr>
                    <td style="border: 1px solid #555; padding: 4px 8px; background: #111; color: #ccc;">${dataset}</td>
                    ${orderedDescriptions.map(desc => {
                      const value = rowData[desc];
                      const displayValue = typeof value === 'number' ? value.toFixed(4) : (value ?? '-');
                      return `
                        <td style="border: 1px solid #555; padding: 4px 8px; background: #111; color: #ccc;">
                          ${displayValue}
                        </td>
                      `;
                    }).join('')}
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        `;

        const figures = this.report.charts.filter(
          entry => entry?.name === item
        );

        if (Array.isArray(figures) && figures.length > 0) {
          figures.forEach((fig, idx) => {
            const containerDiv = document.createElement("div");
            containerDiv.style.marginBottom = "24px";
          
            if (idx === 0 && scoreTableHTML) {
              const scoreDiv = document.createElement("div");
              scoreDiv.className = "score-values";
              scoreDiv.style.marginBottom = "12px";
              scoreDiv.innerHTML = scoreTableHTML;
              containerDiv.appendChild(scoreDiv);
            }
          
            const figDiv = document.createElement("div");
            figDiv.id = `plotly-figure-${idx}`;
            containerDiv.style.width = "100%";
            containerDiv.appendChild(figDiv);
            chartEl.appendChild(containerDiv);
          
            const layout = {
              ...fig.figure.layout,
              autosize: true,
              margin: { l: 0, r: 0, b: 0, t: 0, pad: 0, ...fig.figure.layout?.margin }
            };
            
          
            window.Plotly.react(figDiv, fig.figure.data, layout, { responsive: true });
          });
        } else if (scoreTableHTML) {
          const scoreDiv = document.createElement("div");
          scoreDiv.className = "score-values";
          scoreDiv.style.marginBottom = "12px";
          scoreDiv.innerHTML = scoreTableHTML;
          chartEl.appendChild(scoreDiv);
        } else {
          chartEl.innerHTML = '<div style="color:red">No chart data found in report.</div>';
        }
      
      } catch (err) {
        chartEl.innerHTML = '<div style="color:red">Failed to load chart data.</div>';
        console.error(err);
      }
    },
    mergeAdditionalMetrics(extra) {
      // Expected structure:
      // { Cluster: { Dimension: { Subdimension: ["metric", ...] } } }
      Object.entries(extra || {}).forEach(([topKey, subMap]) => {
        if (!this.topTabs.includes(topKey)) {
          this.topTabs.push(topKey);
          this.subTabsMap[topKey] = [];
          this.metricsData[topKey] = {};
        }

        Object.entries(subMap || {}).forEach(([subKey, innerMap]) => {
          if (!this.subTabsMap[topKey].includes(subKey)) {
            this.subTabsMap[topKey].push(subKey);
          }
          if (!this.metricsData[topKey][subKey]) {
            this.metricsData[topKey][subKey] = {};
          }

          Object.entries(innerMap || {}).forEach(([innerKey, metrics]) => {
            const existing = this.metricsData[topKey][subKey][innerKey] || [];
            const merged = Array.from(new Set([...(existing || []), ...((metrics || []))]));
            this.metricsData[topKey][subKey][innerKey] = merged;
          });
        });
      });
    },
    isDisabledSubtab(subTab) {
      const disabled = [
        'understandability',
        'logical consistency',
        'source credibility'
      ];
      return disabled.includes(subTab.toLowerCase());
    },
    isEmptySubtab(subTab) {
      const subData = this.metricsData[this.activeTopTab]?.[subTab];
      if (Array.isArray(subData)) {
        return subData.length === 0;
      }
      if (typeof subData === 'object' && subData !== null) {
        return Object.values(subData).every(val => {
          if (Array.isArray(val)) return val.length === 0;
          if (typeof val === 'object' && val !== null) return Object.keys(val).length === 0;
          return !val;
        });
      }
      return !subData;
    },
  },
  watch: {
    activeSubTab() {
      this.plotlyVisible = false;
      this.selectedItems = null;
      this.$nextTick(() => {
        this.renderPlotlyChart(null);
      });
    },
  },
};
</script>

<style scoped>
.dashboard-container {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.dashboard {
  width: 90%;
  max-width: 1000px;
  padding: 8px;
  background-color: #111;
  color: white;
  font-family: Arial, sans-serif;
  font-size: 0.8rem;
}

.tabs,
.sub-tabs {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  margin-bottom: 6px;
}

.tabs button,
.sub-tabs button {
  background: #222;
  color: white;
  border: none;
  padding: 6px 10px;
  margin: 3px;
  cursor: pointer;
  min-width: 80px;
  font-size: 0.75rem;
  border-radius: 4px;
}

.tabs button.active,
.sub-tabs button.active {
  background: #444;
}

.content-section {
  margin-top: 8px;
}

.content-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 4px;
  table-layout: fixed;
}

.content-table th,
.content-table td {
  border: 1px solid #333;
  padding: 8px;
  vertical-align: top;
  text-align: center;
  font-size: 0.75rem;
}

.content-button {
  width: 100%;
  background: #333;
  color: white;
  border: none;
  padding: 6px;
  cursor: pointer;
  text-align: center;
  border-radius: 3px;
  font-weight: 500;
  font-size: 0.75rem;
}

.content-button:hover {
  background: #555;
}

.content-button.selected {
  background: #1abc9c;
  color: #fff;
}

.content-placeholder {
  height: 32px;
}

.plotly-wrapper {
  max-width: 1000px;
  width: 90%;
  margin: 24px auto 0;
  padding: 12px;
  background-color: #111;
  overflow-x: hidden;
}

.plotly-wrapper > div {
  width: 100% !important;
}

/* Keep Plotly internals within wrapper width */
.plotly-wrapper .js-plotly-plot,
.plotly-wrapper .plot-container,
.plotly-wrapper .svg-container {
  max-width: 100% !important;
  width: 100% !important;
  box-sizing: border-box;
}

.scores-display {
  background-color: #222;
  padding: 12px;
  margin-bottom: 12px;
  border-radius: 6px;
  color: #eee;
  font-size: 0.8rem;
}

.scores-display h4 {
  margin-top: 0;
  margin-bottom: 8px;
  color: #1abc9c;
  font-size: 0.9rem;
}

.figure-score-wrapper {
  display: flex;
  flex-direction: column;
  background-color: #1a1a1a;
  margin-bottom: 16px;
  padding: 12px;
  border-radius: 6px;
  gap: 12px;
}

.plotly-chart-div {
  width: 100%;
}

.score-block {
  background-color: #222;
  padding: 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  color: #eee;
}

.score-block h5 {
  margin: 0 0 6px 0;
  color: #1abc9c;
  font-size: 0.8rem;
}

.disabled-subtab {
  background-color: #ffcccc !important;
  color: #a33 !important;
  cursor: not-allowed !important;
  opacity: 0.8;
}

.empty-subtab {
  background-color: #e0e0e0 !important;
  color: #888 !important;
  cursor: default !important;
  opacity: 0.7;
}
</style>
