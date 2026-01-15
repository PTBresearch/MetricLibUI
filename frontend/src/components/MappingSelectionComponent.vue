<template>
  <div class="overlay-container">
    <div class="left-panel">

      <h3>Field Selection</h3>
      <div class="field-selection">
        <div
          v-for="key in cols"
          :key="key"
          class="toggle-container"
        >
          <span class="toggle-label">{{ key }}</span>
          <label class="switch">
            <input
              :ref="'toggle-' + key"
              type="checkbox"
              :checked="!!mapping[key]"
              @change="onToggleChange(key)"
            />
            <span class="slider"></span>
          </label>
        </div>
      </div>
    </div>

    <div class="right-panel">
      <h3>Selected Mapping:</h3>
      <div
        class="mapping-box"
        v-for="(target, source) in mapping"
        :key="source"
      >
        {{ source }}: {{ target }}
      </div>
      <button @click="close" class="close-button">Save</button>
    </div>

    <div v-if="showOverlay" class="custom-overlay">
      <div class="overlay-content">
        <p>Map <strong>{{ pendingField }}</strong> to:</p>
        <select v-model="selectedTargetField" class="dropdown-select">
          <option v-for="option in targetFieldOptions" :key="option" :value="option">
            {{ option }}
          </option>
        </select>
        <div style="margin-top: 20px;">
          <button @click="confirmAddField">Add</button>
          <button @click="cancelAddField">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "MappingSelectionOverlay",
  props: {
    cols: {
      type: Array,
      required: false
    }
  },
  data() {
    return {
      selectedUseCase: "ECG diagnosis",
      useCases: ["ECG diagnosis"],
      fieldToggles: {
        age: false,
        sex: false,
        height: false,
        weight: false,
        ethnicity: false,
        nurse: false,
        site: false,
        device: false,
        recording_date: false,
        labels: false,
      },
      mapping: {
        "age": "age",
        "sex": "sex",
        "device": "device",
        "created_at": "recording_date"
      },
      showOverlay: false,
      pendingField: null,
      selectedTargetField: null,
      targetFieldOptions: ["age", "sex", "height", "weight", "nurse", "site", "device", "model_input", "ethnicity", "recording_date", "label", "other"]
    };
  },
  methods: {
    close() {
      this.$emit("close", this.mapping);
    },
    onToggleChange(field) {
      if (this.mapping[field]) {
        delete this.mapping[field];
      } else {
        this.pendingField = field;
        this.selectedTargetField = this.targetFieldOptions[0];
        this.showOverlay = true;
      }
    },
    confirmAddField() {
      if (this.pendingField && this.selectedTargetField) {
        this.mapping[this.selectedTargetField] = this.pendingField;
        this.pendingField = null;
        this.selectedTargetField = null;
        this.showOverlay = false;
      }
    },
    cancelAddField() {
      if (this.pendingField) {
        const refName = 'toggle-' + this.pendingField;
        const refEl = this.$refs[refName];
        const inputEl = Array.isArray(refEl) ? refEl[0] : refEl;
        if (inputEl) inputEl.checked = false;
      }
      this.pendingField = null;
      this.selectedTargetField = null;
      this.showOverlay = false;
    }
  }
};
</script>

<style scoped>
.overlay-container {
  display: flex;
  gap: 120px;
  background-color: #1e1e1e;
  padding: 60px 120px;
  border-radius: 20px;
  color: #f5f6fa;
  max-width: 2600px;
  margin: 20px auto;
  font-size: 15px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
}

.left-panel, .right-panel {
  flex: 2;
  min-width: 420px;
}

.left-panel h3, .right-panel h3 {
  font-size: 1.08em;
  font-weight: 600;
  margin-bottom: 18px;
  letter-spacing: 0.5px;
}

.dropdown-select {
  width: 100%;
  padding: 10px 14px;
  margin-bottom: 24px;
  background-color: #353b48;
  color: #f5f6fa;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.field-selection {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.toggle-container {
  display: flex;
  flex-direction: row;
  align-items: center;
  padding: 4px 0;
  border-bottom: 1px solid #353b48;
  gap: 0;
}

.toggle-label {
  font-size: 15px;
  color: #b2becd;
  flex: 1;
  text-align: left;
  margin-right: 32px;
}

.switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 22px;
  flex-shrink: 0;
  margin-left: auto;
}
.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.slider {
  position: absolute;
  cursor: pointer;
  top: 0; left: 0; right: 0; bottom: 0;
  background-color: #555;
  transition: 0.3s;
  border-radius: 22px;
}
.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 2px;
  bottom: 2px;
  background-color: #fff;
  transition: 0.3s;
  border-radius: 50%;
}
input:checked + .slider {
  background-color: #2196f3;
}
input:checked + .slider:before {
  transform: translateX(22px);
}

.right-panel {
  flex: 2;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  position: relative;
  font-size: 13px;
}

.mapping-box {
  background-color: #1e1e1e;
  border: 1px solid #353b48;
  border-radius: 2px;
  padding: 0px 2px;
  margin-top: 2px;
  margin-bottom: 2px;
  font-size: 13px;
  width: 100%;
  min-height: 40px;
  box-sizing: border-box;
  color: #e1e6f0;
  letter-spacing: 0.2px;
  display: flex;
  align-items: center;
}

.close-button {
  padding: 14px 0;
  margin-top: 40px;
  background: linear-gradient(90deg, #28a745 60%, #218838 100%);
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  align-self: center;
  width: 180px;
  font-size: 17px;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(40,167,69,0.10);
  transition: background 0.2s;
}
.close-button:hover {
  background: linear-gradient(90deg, #218838 60%, #28a745 100%);
}

.custom-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.overlay-content {
  background-color: #2f3640;
  padding: 40px;
  border-radius: 12px;
  color: #f5f6fa;
  text-align: center;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  width: 320px;
}

.overlay-content button {
  background-color: #27ae60;
  color: white;
  padding: 10px 18px;
  margin: 10px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
}

.overlay-content button:last-child {
  background-color: #c0392b;
}
</style>
