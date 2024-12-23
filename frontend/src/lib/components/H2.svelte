<script lang="ts">
	import type { Snippet } from "svelte";

	let { text }: { text: Snippet } = $props();
</script>

<h2 class="text-xl font-semibold">
	{@render text()}
</h2>
