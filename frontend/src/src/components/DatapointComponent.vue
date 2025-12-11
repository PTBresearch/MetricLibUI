<template>
  <div>
    <img
      v-if="imageSrc"
      :src="imageSrc"
      alt="Datapoint"
    />
  </div>
</template>

<script>
export default {
  name: "DatapointComponent",
  props: {
    currentImage: {
      type: String,
      default: null,
    },
  },
  computed: {
    imageSrc() {
      if (!this.currentImage) return null;

      return this.currentImage;
    },
  },
};
</script>

<style scoped>
img {
  width: 100%;
  border: 1px solid #ccc;
  border-radius: 8px;
}
</style>
