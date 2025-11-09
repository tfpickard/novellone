<script lang="ts">
  import { onMount } from 'svelte';
  import {
    getUniversePrompts,
    createUniversePrompt,
    deleteUniversePrompt,
    getStories,
    extractUniverseElements,
    type UniversePromptSummary,
    type UniversePromptCreate
  } from '$lib/api';

  let universePrompts: UniversePromptSummary[] = [];
  let loading = true;
  let error = '';
  let showCreateForm = false;
  let showExtractForm = false;
  let selectedPromptId = '';
  let availableStories: any[] = [];
  let selectedStoryIds: string[] = [];

  // Create form fields
  let newName = '';
  let newDescription = '';
  let characterWeight = 0.5;
  let settingWeight = 0.5;
  let themeWeight = 0.5;
  let loreWeight = 0.5;

  onMount(async () => {
    await loadUniversePrompts();
    await loadStories();
  });

  async function loadUniversePrompts() {
    try {
      loading = true;
      const response = await getUniversePrompts();
      universePrompts = response.items;
    } catch (err: any) {
      error = err.message || 'Failed to load universe prompts';
    } finally {
      loading = false;
    }
  }

  async function loadStories() {
    try {
      const params = new URLSearchParams({ page: '1', page_size: '100' });
      const response = await getStories(params);
      availableStories = response.items;
    } catch (err: any) {
      console.error('Failed to load stories:', err);
    }
  }

  async function handleCreate() {
    if (!newName.trim()) {
      error = 'Name is required';
      return;
    }

    try {
      const payload: UniversePromptCreate = {
        name: newName.trim(),
        description: newDescription.trim() || null,
        character_weight: characterWeight,
        setting_weight: settingWeight,
        theme_weight: themeWeight,
        lore_weight: loreWeight,
      };

      await createUniversePrompt(payload);
      showCreateForm = false;
      newName = '';
      newDescription = '';
      characterWeight = 0.5;
      settingWeight = 0.5;
      themeWeight = 0.5;
      loreWeight = 0.5;
      await loadUniversePrompts();
    } catch (err: any) {
      error = err.message || 'Failed to create universe prompt';
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Are you sure you want to delete this universe prompt?')) return;

    try {
      await deleteUniversePrompt(id);
      await loadUniversePrompts();
    } catch (err: any) {
      error = err.message || 'Failed to delete universe prompt';
    }
  }

  async function handleExtract() {
    if (!selectedPromptId || selectedStoryIds.length === 0) {
      error = 'Please select a universe prompt and at least one story';
      return;
    }

    try {
      await extractUniverseElements(selectedPromptId, selectedStoryIds);
      showExtractForm = false;
      selectedPromptId = '';
      selectedStoryIds = [];
      alert('Universe extraction started! This may take a few moments.');
    } catch (err: any) {
      error = err.message || 'Failed to start universe extraction';
    }
  }

  function toggleStorySelection(storyId: string) {
    if (selectedStoryIds.includes(storyId)) {
      selectedStoryIds = selectedStoryIds.filter(id => id !== storyId);
    } else {
      selectedStoryIds = [...selectedStoryIds, storyId];
    }
  }
</script>

<svelte:head>
  <title>Universe Prompts - Novellone</title>
</svelte:head>

<div class="container">
  <header>
    <h1>Universe Prompts</h1>
    <p class="subtitle">Manage shared universe contexts for story generation</p>
  </header>

  {#if error}
    <div class="error-banner">{error}</div>
  {/if}

  <div class="actions">
    <button class="btn btn-primary" on:click={() => showCreateForm = !showCreateForm}>
      {showCreateForm ? 'Cancel' : '+ Create Universe Prompt'}
    </button>
    <button class="btn btn-secondary" on:click={() => showExtractForm = !showExtractForm}>
      {showExtractForm ? 'Cancel' : '⚡ Extract from Stories'}
    </button>
  </div>

  {#if showCreateForm}
    <div class="form-card">
      <h2>Create New Universe Prompt</h2>
      <form on:submit|preventDefault={handleCreate}>
        <div class="form-group">
          <label for="name">Name *</label>
          <input type="text" id="name" bind:value={newName} required />
        </div>

        <div class="form-group">
          <label for="description">Description</label>
          <textarea id="description" bind:value={newDescription} rows="3"></textarea>
        </div>

        <div class="weights-grid">
          <div class="form-group">
            <label for="char-weight">Character Weight: {characterWeight.toFixed(2)}</label>
            <input type="range" id="char-weight" bind:value={characterWeight} min="0" max="1" step="0.1" />
          </div>

          <div class="form-group">
            <label for="setting-weight">Setting Weight: {settingWeight.toFixed(2)}</label>
            <input type="range" id="setting-weight" bind:value={settingWeight} min="0" max="1" step="0.1" />
          </div>

          <div class="form-group">
            <label for="theme-weight">Theme Weight: {themeWeight.toFixed(2)}</label>
            <input type="range" id="theme-weight" bind:value={themeWeight} min="0" max="1" step="0.1" />
          </div>

          <div class="form-group">
            <label for="lore-weight">Lore Weight: {loreWeight.toFixed(2)}</label>
            <input type="range" id="lore-weight" bind:value={loreWeight} min="0" max="1" step="0.1" />
          </div>
        </div>

        <button type="submit" class="btn btn-primary">Create Universe Prompt</button>
      </form>
    </div>
  {/if}

  {#if showExtractForm}
    <div class="form-card">
      <h2>Extract Universe from Stories</h2>
      <p>Select a universe prompt and stories to analyze for common elements.</p>

      <div class="form-group">
        <label for="prompt-select">Universe Prompt</label>
        <select id="prompt-select" bind:value={selectedPromptId}>
          <option value="">-- Select Universe Prompt --</option>
          {#each universePrompts as prompt}
            <option value={prompt.id}>{prompt.name}</option>
          {/each}
        </select>
      </div>

      <div class="form-group">
        <label>Stories to Analyze ({selectedStoryIds.length} selected)</label>
        <div class="story-list">
          {#each availableStories as story}
            <label class="story-checkbox">
              <input
                type="checkbox"
                checked={selectedStoryIds.includes(story.id)}
                on:change={() => toggleStorySelection(story.id)}
              />
              {story.title} ({story.chapter_count} chapters)
            </label>
          {/each}
        </div>
      </div>

      <button class="btn btn-primary" on:click={handleExtract}>
        Extract Universe Elements
      </button>
    </div>
  {/if}

  {#if loading}
    <p class="loading">Loading universe prompts...</p>
  {:else if universePrompts.length === 0}
    <p class="empty">No universe prompts yet. Create one to get started!</p>
  {:else}
    <div class="prompts-grid">
      {#each universePrompts as prompt}
        <div class="prompt-card">
          <div class="prompt-header">
            <h3>{prompt.name}</h3>
            <span class="version">v{prompt.version}</span>
          </div>

          {#if prompt.description}
            <p class="description">{prompt.description}</p>
          {/if}

          <div class="prompt-stats">
            <div class="stat">
              <span class="label">Elements:</span>
              <span class="value">{prompt.element_count}</span>
            </div>
            <div class="stat">
              <span class="label">Updated:</span>
              <span class="value">{new Date(prompt.updated_at).toLocaleDateString()}</span>
            </div>
          </div>

          <div class="weights">
            <div class="weight">Char: {prompt.character_weight.toFixed(1)}</div>
            <div class="weight">Set: {prompt.setting_weight.toFixed(1)}</div>
            <div class="weight">Theme: {prompt.theme_weight.toFixed(1)}</div>
            <div class="weight">Lore: {prompt.lore_weight.toFixed(1)}</div>
          </div>

          <div class="prompt-actions">
            <a href="/universe/{prompt.id}" class="btn btn-small">View Details</a>
            <button class="btn btn-small btn-danger" on:click={() => handleDelete(prompt.id)}>
              Delete
            </button>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
  }

  header {
    margin-bottom: 2rem;
  }

  h1 {
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
  }

  .subtitle {
    color: #666;
    font-size: 1.1rem;
  }

  .error-banner {
    background: #fee;
    border: 1px solid #fcc;
    color: #c00;
    padding: 1rem;
    border-radius: 4px;
    margin-bottom: 1rem;
  }

  .actions {
    display: flex;
    gap: 1rem;
    margin-bottom: 2rem;
  }

  .btn {
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 4px;
    font-size: 1rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-primary {
    background: #007bff;
    color: white;
  }

  .btn-primary:hover {
    background: #0056b3;
  }

  .btn-secondary {
    background: #6c757d;
    color: white;
  }

  .btn-secondary:hover {
    background: #545b62;
  }

  .btn-small {
    padding: 0.5rem 1rem;
    font-size: 0.875rem;
  }

  .btn-danger {
    background: #dc3545;
    color: white;
  }

  .btn-danger:hover {
    background: #c82333;
  }

  .form-card {
    background: white;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 2rem;
    margin-bottom: 2rem;
  }

  .form-group {
    margin-bottom: 1.5rem;
  }

  .form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
  }

  .form-group input[type="text"],
  .form-group textarea,
  .form-group select {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;
  }

  .form-group input[type="range"] {
    width: 100%;
  }

  .weights-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
  }

  .story-list {
    max-height: 300px;
    overflow-y: auto;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 1rem;
  }

  .story-checkbox {
    display: block;
    padding: 0.5rem;
    cursor: pointer;
  }

  .story-checkbox:hover {
    background: #f8f9fa;
  }

  .loading, .empty {
    text-align: center;
    padding: 2rem;
    color: #666;
    font-size: 1.1rem;
  }

  .prompts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.5rem;
  }

  .prompt-card {
    background: white;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 1.5rem;
    transition: box-shadow 0.2s;
  }

  .prompt-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  .prompt-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .prompt-header h3 {
    margin: 0;
    font-size: 1.25rem;
  }

  .version {
    background: #e9ecef;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.875rem;
    color: #6c757d;
  }

  .description {
    color: #666;
    margin-bottom: 1rem;
  }

  .prompt-stats {
    display: flex;
    gap: 1rem;
    margin-bottom: 1rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #eee;
  }

  .stat {
    display: flex;
    flex-direction: column;
  }

  .stat .label {
    font-size: 0.75rem;
    color: #999;
    text-transform: uppercase;
  }

  .stat .value {
    font-size: 1rem;
    font-weight: 500;
  }

  .weights {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }

  .weight {
    background: #f8f9fa;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
  }

  .prompt-actions {
    display: flex;
    gap: 0.5rem;
  }
</style>
