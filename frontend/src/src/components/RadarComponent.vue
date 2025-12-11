<template>
  <canvas ref="canvas"></canvas>
</template>

<script>
import {
  Chart as ChartJS,
  RadarController,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip
} from 'chart.js'

ChartJS.register(
  RadarController,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip
)

export default {
  name: 'RadarComponent',
  data() {
    return {
      isVisible: false,
      chartInstance: null,
      chartData: {
        labels: [
          'Measurement Process',
          'Timeliness',
          'Representativeness',
          'Informativeness',
          'Consistency'
        ],
        datasets: []
      },
      chartOptions: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            beginAtZero: true,
            suggestedMin: 0,
            suggestedMax: 100,
            ticks: {
              stepSize: 20,
              color: '#bbb',
              backdropColor: 'transparent',
              font: { size: 12 }
            },
            pointLabels: {
              color: '#fff',
              font: { size: 13 }
            },
            grid: {
              color: 'rgba(255,255,255,0.05)'
            },
            angleLines: {
              color: 'rgba(255,255,255,0.1)'
            }
          }
        },
        plugins: {
          legend: { display: false },
          title: { display: false }
        }
      }
    }
  },
  methods: {
    renderChart() {
      if (this.chartInstance) {
        this.chartInstance.destroy()
      }
      const ctx = this.$refs.canvas.getContext('2d')
      return this.chartInstance = new ChartJS(ctx, {
        type: 'radar',
        data: this.chartData,
        options: this.chartOptions
      })
    },
    addChartData(newData) {
      const colorSchemes = [
        { bg: 'rgba(255, 99, 132, 0.2)', border: 'rgba(255, 99, 132, 1)' },   
        { bg: 'rgba(54, 162, 235, 0.2)', border: 'rgba(54, 162, 235, 1)' },  
      ];
      
      const colorIndex = this.chartData.datasets.length % colorSchemes.length;
      const selectedColor = colorSchemes[colorIndex];
      
      this.chartData.datasets.push({
        label: `Dataset${this.chartData.datasets.length + 1}`,
        data: newData,
        backgroundColor: selectedColor.bg,
        borderColor: selectedColor.border,
        pointBackgroundColor: selectedColor.border,
        borderWidth: 2
      });
      
      this.renderChart();
    },
    updateChartData(newData, index) {
      if (index < this.chartData.datasets.length) {
        const colorSchemes = [
          { bg: 'rgba(255, 99, 132, 0.2)', border: 'rgba(255, 99, 132, 1)' },
          { bg: 'rgba(54, 162, 235, 0.2)', border: 'rgba(54, 162, 235, 1)' },
        ];
        
        const colorIndex = index % colorSchemes.length;
        const selectedColor = colorSchemes[colorIndex];
        this.chartData.datasets[index] = {
          label: `Dataset ${index + 1}`,
          data: newData,
          backgroundColor: selectedColor.bg,
          borderColor: selectedColor.border,
          pointBackgroundColor: selectedColor.border,
          borderWidth: 2
        };

        
        
        this.renderChart();
      }
    }
  }
}
</script>

