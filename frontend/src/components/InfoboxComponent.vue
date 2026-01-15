<template>
  <div class="infobox">
    <h2 class="plus-header">General Information</h2>
    <div class="plus-row">
      <span class="plus-label">Name</span>
      <span class="plus-value">{{ info.filename }}</span>
    </div>
    <div class="plus-row">
      <span class="plus-label"># records</span>
      <span class="plus-value">{{ info.rows.toLocaleString() }}</span>
    </div>
    <div class="plus-row">
      <span class="plus-label"># features</span>
      <span class="plus-value">{{ info.features.toLocaleString() }}</span>
    </div>
    <div class="plus-row">
      <span class="plus-label"># missing</span>
      <span class="plus-value">{{ info.missing_values.toLocaleString() }}</span>
    </div>
    <div class="plus-row no-border">
      <span class="plus-label">input type</span>
      <span class="plus-value"> WFDB </span>
    </div>
  </div>
</template>

<script>
export default {
  name: "InfoBox",
  props: {
    info: {
      type: Object,
      required: false,
      default: () => ({})
    }
  }
};
</script>

<style scoped>
.infobox {
  width: 250px;
  height: 150;
  background-color: #1c1c1e;
  color: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  font-family: sans-serif;
}

.plus-header {
  font-size: 1.05rem;
  font-weight: 600;
  margin-bottom: 12px;
  border-bottom: 1px solid #2c2c2e;
  padding-bottom: 6px;
}

.plus-row {
  display: flex;
  justify-content: space-between;
  padding: 5px 0;
  border-bottom: 1px solid #2c2c2e;
  font-size: 0.82rem;
}

.plus-row.no-border {
  border-bottom: none;
}

.plus-label {
  color: #a1a1aa;
}

.plus-value {
  color: #ffffff;
}
</style>
