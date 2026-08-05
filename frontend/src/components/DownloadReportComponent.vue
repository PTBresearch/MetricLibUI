<template>
  <button
    class="download-report-button"
    :disabled="busy || !hasReportData"
    :title="hasReportData ? 'Download all metric values and charts as a PDF' : 'Select a dataset first'"
    @click="downloadReport"
  >
    <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
      <path
        d="M12 3v10m0 0 4-4m-4 4-4-4M5 19h14"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </svg>
    <span>{{ busy ? "Preparing report…" : "Download report" }}</span>
  </button>
</template>

<script>
import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";
import Plotly from "plotly.js-dist";

// Pixel size the plotly figures are rasterized at before they go into the PDF.
const CHART_PIXEL_WIDTH = 940;
const DEFAULT_CHART_PIXEL_HEIGHT = 440;

const MARGIN = 14; // mm
const TEXT_COLOR = [40, 40, 40];
const MUTED_COLOR = [130, 130, 130];
const BORDER_COLOR = [215, 215, 215];

export default {
  name: "DownloadReportComponent",
  props: {
    report: { type: Object, default: () => ({}) },
    // [{ name, query, rows, selectedRows, features, missingValues }]
    datasets: { type: Array, default: () => [] },
    useCase: { type: String, default: null },
  },
  emits: ["loading", "error"],
  data() {
    return {
      busy: false,
    };
  },
  computed: {
    metricEntries() {
      const metrics = this.report?.metrics;
      const list = Array.isArray(metrics)
        ? metrics
        : Array.isArray(metrics?.value)
        ? metrics.value
        : [];
      return list.filter((entry) => entry?.name && entry?.result);
    },
    chartEntries() {
      const charts = this.report?.charts;
      return Array.isArray(charts) ? charts.filter(Boolean) : [];
    },
    datasetNames() {
      const names = this.datasets.map((dataset) => dataset?.name).filter(Boolean);
      if (names.length) return names;
      return [...new Set(this.metricEntries.map((entry) => entry.dataset))];
    },
    hasReportData() {
      return this.metricEntries.length > 0 || this.chartEntries.length > 0;
    },
  },
  methods: {
    async downloadReport() {
      if (this.busy || !this.hasReportData) return;
      this.busy = true;
      this.$emit("loading", true);
      try {
        const doc = await this.buildPdf();
        doc.save(`data-quality-report-${this.timestampSlug(new Date())}.pdf`);
      } catch (error) {
        console.error("Failed to build report:", error);
        this.$emit("error", "Report download failed.");
      } finally {
        this.busy = false;
        this.$emit("loading", false);
      }
    },

    /**
     * One section per metric name, holding the values of every dataset and all
     * charts published under that name (the same grouping the dashboard uses).
     */
    buildSections() {
      const sections = [];
      const byName = new Map();

      const sectionFor = (name) => {
        if (!byName.has(name)) {
          const section = { name, cluster: null, rows: [], charts: [] };
          byName.set(name, section);
          sections.push(section);
        }
        return byName.get(name);
      };

      this.metricEntries.forEach((entry) => {
        const section = sectionFor(entry.name);
        section.cluster = section.cluster || entry.result?.cluster || null;

        const label = entry.result?.description || entry.name;
        // A dataset that already has a value for this label means two metrics
        // share a description, so they get a row each instead of overwriting.
        let row = section.rows.find(
          (candidate) => candidate.label === label && !candidate.values.has(entry.dataset)
        );
        if (!row) {
          row = { label, values: new Map() };
          section.rows.push(row);
        }
        row.values.set(entry.dataset, entry.result?.value);
      });

      this.chartEntries.forEach((chart) => {
        sectionFor(chart.name || "charts").charts.push({ chart, image: null });
      });

      return sections;
    },

    async attachChartImages(sections) {
      for (const section of sections) {
        for (const item of section.charts) {
          const figure = item.chart?.figure;
          if (!figure || !Array.isArray(figure.data)) continue;
          const height = Math.min(
            Math.max(Number(figure.layout?.height) || DEFAULT_CHART_PIXEL_HEIGHT, 320),
            900
          );
          try {
            item.image = await Plotly.toImage(
              { data: figure.data, layout: figure.layout || {} },
              { format: "png", width: CHART_PIXEL_WIDTH, height, scale: 2 }
            );
            item.pixelWidth = CHART_PIXEL_WIDTH;
            item.pixelHeight = height;
          } catch (error) {
            console.error(`Failed to render chart "${item.chart?.name}":`, error);
          }
        }
      }
    },

    async buildPdf() {
      const sections = this.buildSections();
      await this.attachChartImages(sections);

      const doc = new jsPDF({ unit: "mm", format: "a4", compress: true });
      const layout = {
        doc,
        width: doc.internal.pageSize.getWidth() - 2 * MARGIN,
        pageHeight: doc.internal.pageSize.getHeight(),
        y: MARGIN,
      };

      this.drawHeader(layout, new Date());
      this.drawDatasets(layout);
      sections.forEach((section) => this.drawSection(layout, section));
      this.drawFooters(doc);

      return doc;
    },

    drawHeader(layout, generatedAt) {
      const { doc } = layout;
      doc.setTextColor(...TEXT_COLOR);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(18);
      layout.y += 6;
      doc.text("Data quality report", MARGIN, layout.y);

      const subtitle = [generatedAt.toLocaleString()];
      if (this.useCase) subtitle.push(`Use case: ${this.useCase}`);
      const lines = [subtitle.join("  |  "), this.datasetNames.join(", ")].filter(Boolean);

      doc.setFont("helvetica", "normal");
      doc.setFontSize(9);
      doc.setTextColor(...MUTED_COLOR);
      lines.forEach((line) => {
        layout.y += 5;
        doc.text(doc.splitTextToSize(line, layout.width), MARGIN, layout.y);
      });
      layout.y += 6;
    },

    drawDatasets(layout) {
      if (!this.datasets.length) return;
      this.drawHeading(layout, "Datasets", 13);
      this.drawTable(layout, {
        head: [
          ["Dataset", "Rows", "Rows after filter", "Features", "Missing values", "Filter"],
        ],
        body: this.datasets.map((dataset) => [
          dataset.name,
          this.formatValue(dataset.rows),
          this.formatValue(dataset.selectedRows),
          this.formatValue(dataset.features),
          this.formatValue(dataset.missingValues),
          dataset.query || "-",
        ]),
      });
    },

    drawSection(layout, section) {
      const columns = this.datasetNames.filter((name) =>
        section.rows.some((row) => row.values.has(name))
      );

      this.ensureSpace(layout, 30);
      this.drawHeading(layout, this.prettify(section.name), 12);

      if (section.cluster) {
        const { doc } = layout;
        doc.setFont("helvetica", "normal");
        doc.setFontSize(8);
        doc.setTextColor(...MUTED_COLOR);
        doc.text(section.cluster, MARGIN, layout.y);
        layout.y += 5;
      }

      if (section.rows.length) {
        this.drawTable(layout, {
          head: [["Metric", ...columns]],
          body: section.rows.map((row) => [
            row.label,
            ...columns.map((name) => this.formatValue(row.values.get(name))),
          ]),
        });
      }

      section.charts.forEach((item) => this.drawChart(layout, item));
      layout.y += 4;
    },

    drawChart(layout, item) {
      const { doc } = layout;
      const caption = this.chartCaption(item.chart);

      if (!item.image) {
        doc.setFont("helvetica", "italic");
        doc.setFontSize(8);
        doc.setTextColor(170, 90, 90);
        this.ensureSpace(layout, 8);
        doc.text(`Chart "${caption}" could not be rendered.`, MARGIN, layout.y);
        layout.y += 8;
        return;
      }

      const usableHeight = layout.pageHeight - 2 * MARGIN - 10;
      let width = layout.width;
      let height = (width * item.pixelHeight) / item.pixelWidth;
      if (height > usableHeight) {
        width = (width * usableHeight) / height;
        height = usableHeight;
      }

      this.ensureSpace(layout, height + 10);
      doc.addImage(item.image, "PNG", MARGIN, layout.y, width, height, undefined, "FAST");
      doc.setDrawColor(...BORDER_COLOR);
      doc.rect(MARGIN, layout.y, width, height);
      layout.y += height + 4;

      doc.setFont("helvetica", "normal");
      doc.setFontSize(8);
      doc.setTextColor(...MUTED_COLOR);
      doc.text(caption, MARGIN, layout.y);
      layout.y += 7;
    },

    drawHeading(layout, text, size) {
      const { doc } = layout;
      doc.setFont("helvetica", "bold");
      doc.setFontSize(size);
      doc.setTextColor(...TEXT_COLOR);
      layout.y += 3;
      doc.text(text, MARGIN, layout.y);
      layout.y += 5;
    },

    drawTable(layout, { head, body }) {
      autoTable(layout.doc, {
        head,
        body,
        startY: layout.y,
        margin: { left: MARGIN, right: MARGIN, top: MARGIN, bottom: MARGIN },
        styles: {
          font: "helvetica",
          fontSize: 8,
          cellPadding: 2,
          textColor: TEXT_COLOR,
          lineColor: BORDER_COLOR,
          lineWidth: 0.1,
          overflow: "linebreak",
        },
        headStyles: {
          fillColor: [242, 242, 242],
          textColor: TEXT_COLOR,
          fontStyle: "bold",
        },
        columnStyles: { 0: { fontStyle: "bold", cellWidth: "auto" } },
      });
      layout.y = layout.doc.lastAutoTable.finalY + 6;
    },

    drawFooters(doc) {
      const pageCount = doc.internal.getNumberOfPages();
      const pageWidth = doc.internal.pageSize.getWidth();
      const pageHeight = doc.internal.pageSize.getHeight();
      for (let page = 1; page <= pageCount; page += 1) {
        doc.setPage(page);
        doc.setFont("helvetica", "normal");
        doc.setFontSize(8);
        doc.setTextColor(...MUTED_COLOR);
        doc.text("Data quality report", MARGIN, pageHeight - 8);
        doc.text(`Page ${page} of ${pageCount}`, pageWidth - MARGIN, pageHeight - 8, {
          align: "right",
        });
      }
    },

    ensureSpace(layout, needed) {
      if (layout.y + needed <= layout.pageHeight - MARGIN) return;
      layout.doc.addPage();
      layout.y = MARGIN;
    },

    chartCaption(chart) {
      const type = this.prettify(chart?.type || "chart");
      const field = chart?.config?.field;
      return field ? `${type} - ${field}` : type;
    },

    formatValue(value) {
      if (value === null || value === undefined || value === "") return "-";
      if (typeof value === "number") {
        if (!Number.isFinite(value)) return "-";
        return Number.isInteger(value) ? String(value) : value.toFixed(4);
      }
      if (typeof value === "boolean") return value ? "true" : "false";
      if (Array.isArray(value)) {
        return value.map((item) => this.formatValue(item)).join(", ");
      }
      if (typeof value === "object") {
        return Object.entries(value)
          .map(([key, item]) => `${key}: ${this.formatValue(item)}`)
          .join("; ");
      }
      return String(value);
    },

    prettify(name) {
      const text = String(name ?? "").replace(/_/g, " ").trim();
      return text ? text.charAt(0).toUpperCase() + text.slice(1) : "Unnamed";
    },

    timestampSlug(date) {
      const pad = (value) => String(value).padStart(2, "0");
      return [
        date.getFullYear(),
        pad(date.getMonth() + 1),
        pad(date.getDate()),
        "-",
        pad(date.getHours()),
        pad(date.getMinutes()),
      ].join("");
    },
  },
};
</script>

<style scoped>
.download-report-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #222;
  color: white;
  border: 1px solid #333;
  padding: 6px 12px;
  cursor: pointer;
  font-family: Arial, sans-serif;
  font-size: 0.75rem;
  border-radius: 4px;
}

.download-report-button:hover:not(:disabled) {
  background: #1abc9c;
  border-color: #1abc9c;
}

.download-report-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
