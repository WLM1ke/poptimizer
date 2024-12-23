<script lang="ts">
	import H2 from "$lib/components/H2.svelte";
	import type { Snippet } from "svelte";

	let { upper, main, lower }: { upper: Snippet; main: Snippet; lower: Snippet } = $props();
</script>

<section class="bg-bg-accent w-80 rounded-lg p-4">
	<div class="text-text-muted italic">
		{@render upper()}
	</div>
	<H2>
		{@render main()}
	</H2>
	<div class="text-text-muted italic">
		{@render lower()}
	</div>
</section>
