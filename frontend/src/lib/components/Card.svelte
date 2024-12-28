<script lang="ts">
	import H2 from "$lib/components/H2.svelte";

	let { upper, main, lower }: { upper: string; main: string; lower: string } = $props();
</script>

<section class="w-80 rounded-lg bg-bg-accent p-4">
	<div class="italic text-text-muted">
		{upper}
	</div>
	<H2 text={main} />
	<div class="italic text-text-muted">
		{lower}
	</div>
</section>
