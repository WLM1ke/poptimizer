<script lang="ts">
	import H2 from "$lib/components/H2.svelte";

	let { upper, main, lower }: { upper: string; main: string; lower: string } = $props();
</script>

<section class="bg-bg-accent w-96 rounded-lg p-4">
	<div class="text-text-muted italic">
		{upper}
	</div>
	<H2 text={main} />
	<div class="text-text-muted italic">
		{lower}
	</div>
</section>
