<template>
  <div class="plus-component">
    +
  </div>
</template>

<script>
export default {
  name: "PlusComponent",
};
</script>

<style scoped>
.plus-component {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 120px;
  height: 120px;
  background-color: #1c1c1e;
  color: white;
  font-size: 48px;
  font-weight: bold;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  cursor: pointer;
  transition: background-color 0.2s ease, transform 0.2s ease;
}

.plus-component:hover {
  background-color: #2a2a2c;
  transform: scale(1.05);
}
</style>
