<template>
  <div style="margin-top: 0px;">
      <ErrorBarComponent v-if="hasError" :message="errorMessage" />
  </div>
  <div id="app-body" class="dark">
    <div class="left-panel">
      <div class="grid-container">
        <div
          v-for="(button, index) in buttons"
          :key="index"
          class="button-container"
        >
          <InfoboxComponent :info="button" />
        </div>
        <div class="button-container">
          <PlusComponent @click="triggerFileInput" />
        </div>
      </div>

      <div
        v-for="(button, index) in buttons"
        :key="index"
        class="table-wrapper"
      >
        <DataTable
          :data="records[index]"
          :dbName="dbNames[index]"
          :mapping="mappings[index]"
          @update:data="updateRecord(index, $event)"
          @update:image="showImage"
          @loading="handleLoading"
        />
      </div>
    </div>

    <div class="right-panel">
      <div class="radar-chart-container" ref="radarChartContainer">
        <RadarComponent ref="radarChart" />
      </div>
      <div ref="metricSelection" class="metric-selection-container">
        <MetricSelectionComponent :dbNames="dbNames" :report="report" ref="metrics" />
      </div>
    </div>

    <div v-if="isLoading" class="loading-overlay">
      <div class="spinner"></div>
    </div>

    <div v-if="showDatapoint" class="overlay" @click.self="hideDatapoint">
      <DatapointComponent :currentImage="currentImage" />
    </div>

    <div v-if="showDatasetSelector" class="overlay overlay--top" @click.self="closeDatasetSelector">
      <div class="app-overlay-content">
        <DatasetSelectionComponent
          @cancel="closeDatasetSelector"
          @select="handleDatasetSelected"
          @loading="handleLoading"
        />
      </div>
    </div>

    <div v-if="showOverlay" class="overlay overlay--top">
      <div class="app-overlay-content">
        <MappingSelectionComponent class="mapping-scroll" @close="handleOverlayClose" :cols="cols[cols.length - 1]" />
      </div>
    </div>
  </div>
</template>

<script>
import PlusComponent from "./components/PlusComponent.vue";
import ErrorBarComponent from "./components/ErrorBarComponent.vue";
import MappingSelectionComponent from "./components/MappingSelectionComponent.vue";
import DatasetSelectionComponent from "./components/DatasetSelectionComponent.vue";
import InfoboxComponent from "./components/InfoboxComponent.vue";
import DataTable from "./components/TableComponent.vue";
import RadarComponent from "./components/RadarComponent.vue";
import MetricSelectionComponent from "./components/MetricSelectionComponent.vue";
import DatapointComponent from "./components/DatapointComponent.vue";

export default {
  name: "App",
  components: {
    PlusComponent,
    ErrorBarComponent,
    MappingSelectionComponent,
    InfoboxComponent,
    DataTable,
    RadarComponent,
    MetricSelectionComponent,
    DatapointComponent,
    DatasetSelectionComponent
  },
  data() {
    return {
      showOverlay: false,
      showDatapoint: false,
      isLoading: false,
      loadingCount: 0,
      showDatasetSelector: false,
      hasError: false,
      errorMessage: "An error has occurred.",
      buttons: [],
      cols: [],
      mappings: [],
      records: [],
      dbNames: [],
      queries: [],
      report: {},
      currentImage: null,
    };
  },
  methods: {
    startLoading() {
      this.loadingCount += 1;
      this.isLoading = true;
    },
    stopLoading() {
      this.loadingCount = Math.max(0, this.loadingCount - 1);
      this.isLoading = this.loadingCount > 0;
    },
    handleLoading(flag) {
      if (flag) this.startLoading();
      else this.stopLoading();
    },
    showImage(imageBase64) {
      this.showDatapoint = true
      this.currentImage = imageBase64;
    },
    hideDatapoint() {
      this.showDatapoint = false;
      this.currentImage = null;
    },
    async updateRecord(index, newData) {
      this.startLoading();
      try {
        this.records.splice(index, 1, newData["data"]);
        this.queries[index] = newData["query"];
        let response;
        try {
          response = await fetch('http://localhost:8000/api/report', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              dataset_names: this.dbNames,
              mappings: this.mappings,
              queries: this.queries
            }),
          });
        } catch (error) {
          this.hasError = true;
          this.errorMessage = "Error creating report.";
          console.error('Error sending report request:', error);
          return;
        }

        this.report = await response.json();

        this.$refs.metrics.renderPlotlyChart();

        const datasetName = this.dbNames[index];
        const scores = this.report?.scores?.[index] ?? this.report?.scores?.[datasetName];
        if (!scores) {
          this.hasError = true;
          this.errorMessage = `Missing scores in report for dataset: ${datasetName}`;
          console.error('Missing scores in report:', { index, datasetName, report: this.report });
          return;
        }

        this.$refs.radarChart.updateChartData([
          scores["Measurement Process"] * 100,
          scores["Timeliness"] * 100,
          scores["Representativeness"] * 100,
          scores["Informativeness"] * 100,
          scores["Consistency"] * 100,
        ], index);
      } finally {
        this.stopLoading();
      }
    },
    triggerFileInput() {
      this.showDatasetSelector = true;
    },
    closeDatasetSelector() {
      this.showDatasetSelector = false;
    },
    async handleDatasetSelected(filename) {
      this.showDatasetSelector = false;
      this.startLoading();
      try {
        const response = await fetch(`/api/upload_file?name=${encodeURIComponent(filename)}`);
        const result = await response.json();
        this.showOverlay = true;
        this.buttons.push(result);
        this.dbNames.push(filename);
        this.cols.push(result.cols);
      } catch (error) {
        this.hasError = true;
        this.errorMessage = "Dataset selection failed.";
        console.error('Dataset selection failed:', error);
      } finally {
        this.hasError = false;
        this.stopLoading();
      }
    },
    async handleOverlayClose(mapping) {
      this.showOverlay = false;
      this.startLoading();
      try {
        try {
          const response = await fetch('http://localhost:8000/api/dataset', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              name: this.dbNames[this.dbNames.length - 1].replace('.csv', ''),
              mapping: mapping
            }),
          });

          const data = await response.json()
          this.records.push(data);
        } catch (error) {
          console.error('Error sending mapping:', error);
        }
        this.mappings.push(mapping);
        this.queries.push("")
        const reportResponse = await fetch('http://localhost:8000/api/report', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            dataset_names: this.dbNames,
            mappings: this.mappings,
            queries: this.queries
          }),
        }).catch(error => {
          console.error('Error sending report request:', error);
        });

        this.report = await reportResponse.json();
        this.$refs.radarChartContainer.style.display = "block";

        this.$refs.radarChart.addChartData([
          this.report.scores[this.dbNames.length - 1]["Measurement Process"] * 100,
          this.report.scores[this.dbNames.length - 1]["Timeliness"] * 100,
          this.report.scores[this.dbNames.length - 1]["Representativeness"] * 100,
          this.report.scores[this.dbNames.length - 1]["Informativeness"] * 100,
          this.report.scores[this.dbNames.length - 1]["Consistency"] * 100,
        ]);
        this.$refs.metricSelection.style.display = "block";

        this.$refs.metrics.renderPlotlyChart();
      } finally {
        this.stopLoading();
      }
    },
  },
};
</script>

<style>
body {
  background-color: #2e2e2e;
  margin: 0;
  padding: 0;
}

#app-body {
  width: 100%;
  display: flex;
  justify-content: space-between;
  padding: 20px;
  box-sizing: border-box;
  font-family: Arial, sans-serif;
  color: white;
}

.left-panel {
  width: 50%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.right-panel {
  width: 50%;
  padding-left: 2%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
}

.right-panel > * + * {
  margin-top: 20px;
}

.grid-container {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
}

.button-container {
  flex: 0 0 auto;
}

.table-wrapper {
  width: 100%;
  background-color: #1e1e1e;
  padding: 20px;
  border-radius: 10px;
  overflow-x: auto;
}

.radar-chart-container {
  display: none;
  width: 100%;
  max-width: 500px;
  height: 350px;
  margin: 0 auto 20px auto;
  padding: 20px;
  background-color: #1e1e1e;
  border-radius: 12px;
  box-shadow: 0 0 20px rgba(0, 123, 255, 0.1);
}

.metric-selection-container {
  width: 100%;
  padding: 0px;
  border-radius: 10px;
  display: none;
  align-items: flex-start;
  justify-content: flex-start;
}

.overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 20px;
  box-sizing: border-box;
}

.overlay--top {
  align-items: flex-start;
}

.app-overlay-content {
  max-width: 90vw;
  display: flex;
  align-items: stretch;
  justify-content: center;
}

.mapping-scroll {
  max-width: 90vw;
  width: 100%;
  box-sizing: border-box;
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0,0,0,0.7);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
}

.spinner {
  border: 8px solid #f3f3f3;
  border-top: 8px solid #3498db;
  border-radius: 50%;
  width: 60px;
  height: 60px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
