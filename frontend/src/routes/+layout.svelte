<script lang="ts">
  export let data;
</script>

<svelte:head>
  <title>Eternal Stories</title>
</svelte:head>

<slot />

<style>
  :global(body) {
    margin: 0;
    font-family: 'Inter', system-ui, sans-serif;
    background: #020617;
    color: #e2e8f0;
    min-height: 100vh;
  }

  :global(*) {
    box-sizing: border-box;
  }

  :global(a) {
    color: inherit;
    text-decoration: none;
  }

  :global(.page-container) {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem 1.5rem 4rem;
  }
</style>
