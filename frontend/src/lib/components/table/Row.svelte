<script lang="ts">
	import type { Snippet } from "svelte";

	let { cells, muted = false }: { cells: Snippet; muted?: boolean } = $props();
</script>

<tr class:text-text-muted={muted}>
	{@render cells()}
</tr>
