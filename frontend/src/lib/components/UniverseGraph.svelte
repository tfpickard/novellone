<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import * as d3 from 'd3';

  // Props
  export let width = 800;
  export let height = 600;
  export let minWeight = 0.3;

  // State
  let container: HTMLDivElement;
  let svg: d3.Selection<SVGSVGElement, unknown, null, undefined>;
  let simulation: d3.Simulation<any, any>;
  let graphData: { nodes: any[]; links: any[] } = { nodes: [], links: [] };
  let loading = true;
  let error = '';

  // Color scales by status and tone
  const statusColors = {
    active: '#3b82f6', // blue
    completed: '#10b981', // green
    killed: '#ef4444', // red
  };

  const toneColors = {
    dark: '#1f2937',
    humorous: '#f59e0b',
    philosophical: '#8b5cf6',
    surreal: '#ec4899',
    absurd: '#f97316',
  };

  // Fetch graph data
  async function fetchGraphData() {
    try {
      loading = true;
      error = '';

      const response = await fetch(`/api/universe/graph?minWeight=${minWeight}&limit=50`);
      const result = await response.json();

      if (!result.success) {
        throw new Error(result.error || 'Failed to fetch graph data');
      }

      graphData = result.data;
      renderGraph();
    } catch (err) {
      console.error('Error fetching graph data:', err);
      error = err instanceof Error ? err.message : 'Failed to load graph';
    } finally {
      loading = false;
    }
  }

  // Render the graph using D3
  function renderGraph() {
    if (!container || graphData.nodes.length === 0) return;

    // Clear previous graph
    d3.select(container).select('svg').remove();

    // Create SVG
    svg = d3
      .select(container)
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', [0, 0, width, height])
      .attr('style', 'max-width: 100%; height: auto;');

    // Create force simulation
    simulation = d3
      .forceSimulation(graphData.nodes)
      .force(
        'link',
        d3
          .forceLink(graphData.links)
          .id((d: any) => d.id)
          .distance((d: any) => 100 / d.weight) // Closer for higher weight
      )
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(30));

    // Add links
    const link = svg
      .append('g')
      .attr('stroke', '#999')
      .attr('stroke-opacity', 0.6)
      .selectAll('line')
      .data(graphData.links)
      .join('line')
      .attr('stroke-width', (d: any) => Math.sqrt(d.weight) * 3);

    // Add nodes
    const node = svg
      .append('g')
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5)
      .selectAll('circle')
      .data(graphData.nodes)
      .join('circle')
      .attr('r', (d: any) => 5 + Math.sqrt(d.chapterCount || 1) * 2)
      .attr('fill', (d: any) => toneColors[d.tone as keyof typeof toneColors] || statusColors[d.status as keyof typeof statusColors])
      .call(drag(simulation) as any);

    // Add labels
    const label = svg
      .append('g')
      .selectAll('text')
      .data(graphData.nodes)
      .join('text')
      .text((d: any) => d.title)
      .attr('font-size', 10)
      .attr('dx', 12)
      .attr('dy', 4)
      .style('pointer-events', 'none');

    // Add tooltips
    node.append('title').text((d: any) => `${d.title}\n${d.status} • ${d.chapterCount} chapters`);

    link.append('title').text(
      (d: any) =>
        `Weight: ${d.weight.toFixed(2)}\nShared: ${d.sharedEntities.length} entities, ${d.sharedThemes.length} themes`
    );

    // Update positions on tick
    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      node.attr('cx', (d: any) => d.x).attr('cy', (d: any) => d.y);

      label.attr('x', (d: any) => d.x).attr('y', (d: any) => d.y);
    });
  }

  // Drag behavior
  function drag(simulation: d3.Simulation<any, any>) {
    function dragstarted(event: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }

    function dragged(event: any) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragended(event: any) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

    return d3.drag().on('start', dragstarted).on('drag', dragged).on('end', dragended);
  }

  // Lifecycle
  onMount(() => {
    fetchGraphData();
  });

  onDestroy(() => {
    if (simulation) {
      simulation.stop();
    }
  });

  // Reactive: Update when minWeight changes
  $: if (!loading) {
    fetchGraphData();
  }
</script>

<div class="universe-graph">
  {#if loading}
    <div class="loading">
      <div class="spinner"></div>
      <p>Loading universe graph...</p>
    </div>
  {:else if error}
    <div class="error">
      <p>Error: {error}</p>
      <button on:click={fetchGraphData}>Retry</button>
    </div>
  {:else}
    <div class="graph-container" bind:this={container}></div>

    <div class="controls">
      <label>
        Min Connection Weight: {minWeight.toFixed(1)}
        <input type="range" bind:value={minWeight} min="0.1" max="1.0" step="0.1" />
      </label>

      <div class="stats">
        <span>{graphData.nodes.length} stories</span>
        <span>•</span>
        <span>{graphData.links.length} connections</span>
      </div>
    </div>

    <div class="legend">
      <h4>Legend</h4>
      <div class="legend-item">
        <span class="legend-color" style="background-color: {statusColors.active}"></span>
        <span>Active</span>
      </div>
      <div class="legend-item">
        <span class="legend-color" style="background-color: {statusColors.completed}"></span>
        <span>Completed</span>
      </div>
      <div class="legend-item">
        <span class="legend-color" style="background-color: {statusColors.killed}"></span>
        <span>Killed</span>
      </div>
      <p class="legend-note">
        Node size represents chapter count. Line thickness represents connection strength.
      </p>
    </div>
  {/if}
</div>

<style>
  .universe-graph {
    position: relative;
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .loading,
  .error {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 400px;
    gap: 1rem;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 4px solid #f3f3f3;
    border-top: 4px solid #3b82f6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
  }

  .graph-container {
    flex: 1;
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
    background-color: #fafafa;
    overflow: hidden;
  }

  .controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    border: 1px solid #e5e7eb;
    border-top: none;
    border-radius: 0 0 0.5rem 0.5rem;
    background-color: white;
  }

  .controls label {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .stats {
    display: flex;
    gap: 0.5rem;
    font-size: 0.875rem;
    color: #6b7280;
  }

  .legend {
    margin-top: 1rem;
    padding: 1rem;
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
    background-color: white;
  }

  .legend h4 {
    margin: 0 0 0.5rem 0;
    font-size: 0.875rem;
    font-weight: 600;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.25rem;
  }

  .legend-color {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    border: 1px solid #fff;
  }

  .legend-note {
    margin-top: 0.5rem;
    font-size: 0.75rem;
    color: #6b7280;
    font-style: italic;
  }

  .error button {
    padding: 0.5rem 1rem;
    background-color: #3b82f6;
    color: white;
    border: none;
    border-radius: 0.25rem;
    cursor: pointer;
  }

  .error button:hover {
    background-color: #2563eb;
  }
</style>
