<template>
  <div class="data-visualization">
    <div class="filter-row">
      <select v-model="filter.column">
        <option v-for="col in columns" :key="col" :value="col">{{ col }}</option>
      </select>

      <select v-model="filter.operator">
        <option value="=">=</option>
        <option value="!=">≠</option>
        <option value=">=">&ge;</option>
        <option value=">=">&gt;</option>
        <option value="<">&lt;</option>
        <option value="<=">&le;</option>
      </select>

      <template v-if="showDropdownForValue">
        <select v-model="filter.value" class="value-control">
          <option v-for="val in valueOptions" :key="val" :value="val">{{ val }}</option>
        </select>
      </template>
      <template v-else>
        <input v-model="filter.value" type="text" placeholder="Enter a value..." class="value-control" />
      </template>

      <select v-model="filter.condition">
        <option value="AND">AND</option>
        <option value="OR">OR</option>
      </select>

      <button class="add-btn" @click="applyFilter">+</button>
    </div>

    <div class="custom-query-row" style="display: flex; align-items: flex-start; gap: 8px;">
      <textarea class="custom-query" placeholder="Enter your custom query here..."></textarea>
      <div style="display: flex; flex-direction: column; gap: 6px;">
        <button class="refresh-btn" @click="refreshTable" title="Refresh table">⟳</button>
        <button class="refresh-btn clear-query-btn" @click="clearQuery" title="Clear query">✕</button>
      </div>
    </div>

    <div class="result-count"># result: {{ filteredData.length }}</div>

    <!-- Scrollable Table Wrapper -->
    <div class="table-scroll-container">
      <table class="data-table">
        <thead>
          <tr>
            <th v-for="col in columns" :key="col">{{ col }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, index) in filteredData" :key="index" @click="getImage(row)">
            <td v-for="col in columns" :key="col">{{ row[col] }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
export default {
  name: "DataTable",
  props: {
    data: {
      type: Array,
      default: () => []
    },
    dbName: {
      type: String,
      required: true
    },
    mapping: {
      type: Object,
      default: () => ({})
    },
  },
  data() {
    return {
      filter: {
        column: "",
        operator: "=",
        value: "",
        condition: "AND",
        values: [],
      },
      valueOptions: [],
    };
  },
  computed: {
    columns() {
      if (!Array.isArray(this.data) || this.data.length === 0) return [];
      return Object.keys(this.data[0]).filter(col => col !== 'model_input');
    },
    rows() {
      return Array.isArray(this.data) ? this.data : [];
    },
    filteredData() {
      return this.rows;
    },
    showDropdownForValue() {
      return this.valueOptions.length > 0 && this.valueOptions.length < 15;
    }
  },
  watch: {
    columns(newCols) {
      if (newCols.length > 0) {
        if (!this.filter.column || !newCols.includes(this.filter.column)) {
          this.filter.column = newCols[0];
        }
      } else {
        this.filter.column = "";
      }
    },
    'filter.column': {
      immediate: true,
      handler() {
        this.valueOptions = this.computeValueOptions();
      }
    }
  },
  methods: {
    computeValueOptions() {
      if (!this.filter.column) return [];
      const values = this.rows.map(row => row[this.filter.column]);
      // Remove undefined/null and deduplicate
      return Array.from(new Set(values.filter(v => v !== undefined && v !== null)));
    },
    applyFilter(event) {
      if (event) event.preventDefault();
      const textarea = this.$el.querySelector('.custom-query');
      const value = this.filter.value;
      const operator = this.filter.operator === '=' ? '==' : this.filter.operator;
      const field = this.filter.column;
      const logicalOperator = this.filter.condition;
      let query = textarea.value;
      if (query.includes("AND") || query.includes("OR")) {
        query = `(${query}) ${logicalOperator} `;
      } else if (query !== "") {
        query = `${query} ${logicalOperator} `;
      }
      const formattedValue = /\D/.test(value) && value != "null" ? `'${value}'` : value;
      textarea.value = `${query}[${field}${operator}${formattedValue}]`;

    },
    async refreshTable() {
      const textarea = this.$el.querySelector('.custom-query');
      const query = textarea.value;
      const dbName = this.dbName;
      const mapping = this.mapping;
      this.$emit('loading', true);
      try {
        const response = await fetch(`/api/dataset?name=${encodeURIComponent(dbName)}&query=${encodeURIComponent(query)}&mapping=${encodeURIComponent(JSON.stringify(mapping))}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          },
        });

        if (!response.ok) throw new Error('Failed to fetch dataset');
        const newData = await response.json();
        this.$emit('update:data', {"data": newData, "query": query});
        this.$emit('table-refreshed');
      } catch (err) {
        alert('Error fetching data: ' + err.message);
      } finally {
        this.$emit('loading', false);
      }
    },
    clearQuery() {
      const textarea = this.$el.querySelector('.custom-query');
      if (textarea) textarea.value = '';
    },
    async getImage(row) {
      const name = this.dbName
      const idx = row["idx"]
      this.$emit('loading', true);
      try {
        const response = await fetch(`/api/image?name=${encodeURIComponent(name)}&index=${encodeURIComponent(idx)}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          },
        })
        if (!response.ok) throw new Error('Failed to fetch image');
        const data = await response.json()
        this.$emit('update:image', "data:image/png;base64," + data["image_base64"]);
      } catch (err) {
        alert('Error fetching image: ' + err.message);
      } finally {
        this.$emit('loading', false);
      }
      return
    }
  }
};
</script>

<style scoped>
.data-visualization {
  background-color: #121212;
  color: white;
  padding: 20px;
  font-family: Arial, sans-serif;
}

.filter-row {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

.filter-row select,
.filter-row input {
  padding: 5px;
  background-color: #1e1e1e;
  color: white;
  border: 1px solid #444;
  border-radius: 4px;
}

.add-btn {
  background-color: #1abc9c;
  border: none;
  padding: 6px 12px;
  border-radius: 50%;
  color: white;
  font-size: 20px;
  cursor: pointer;
}

.custom-query-row {
  display: flex;
  align-items: flex-start;
  margin-bottom: 10px;
}

.custom-query {
  width: 95%;
  background-color: #1e1e1e;
  color: white;
  border: 1px solid #444;
  border-radius: 6px;
  height: 100px;
  padding: 10px;
  margin-bottom: 0;
  margin-right: 10px;
  resize: vertical;
  flex: 1 1 0;
}

.refresh-btn {
  background-color: #2980b9;
  border: none;
  color: white;
  font-size: 20px;
  border-radius: 8px;
  padding: 0;
  margin-left: 0;
  cursor: pointer;
  transition: background 0.2s;
  height: 40px;
  width: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
}

.refresh-btn:hover {
  background-color: #3498db;
}

.clear-query-btn {
  background-color: #e74c3c;
  border: none;
  color: white;
  font-size: 14px;
  border-radius: 4px;
  padding: 6px 12px;
  cursor: pointer;
  width: 100%;
  margin-top: 6px;
}

.clear-query-btn:hover {
  background-color: #c0392b;
}

.result-count {
  margin-bottom: 10px;
  background-color: #222;
  padding: 6px 12px;
  border-radius: 6px;
  display: inline-block;
  font-size: 14px;
}

.table-scroll-container {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid #333;
  border-radius: 6px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 600px;
}

.data-table th,
.data-table td {
  border: 1px solid #333;
  padding: 6px;
  text-align: left;
  font-size: 12px;
}

.data-table tr:nth-child(even) {
  background-color: #1c1c1c;
}

.data-table tbody tr:hover {
  background-color: #2a2a2a;
  cursor: pointer;
  transition: background-color 0.15s ease-in-out;
}

.value-control {
  width: 220px;
  height: 36px;
  box-sizing: border-box;
}
</style>
