<script lang="ts">
	import type { Snippet } from "svelte";

	let { text }: { text: string } = $props();
</script>

<h2 class="text-xl font-semibold">
	{text}
</h2>
