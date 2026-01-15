<template>
    <div class="error-bar">
        <p class="error-message">{{ message }}</p>
    </div>
</template>

<script>
export default {
    name: "ErrorBarComponent",
    props: {
        message: {
            type: String,
            required: false,
        }
    }
}
</script>
<style scoped>
    .error-bar {
        width: 100%;
        padding: 12px 16px;
        margin: 0;
        background-color: rgba(220, 38, 38, 0.7); /* strong red with opacity */
        text-align: center;
    }

    .error-message {
        color: #fff; /* white text for contrast */
        font-weight: bold;
        font-family: sans-serif;
        margin: 0;
        font-size: 16px;
    }
</style>
