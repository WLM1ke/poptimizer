<script lang="ts">
	import H2 from "$lib/components/H2.svelte";

	export let title: string;
</script>

<header class="border-bg-accent min-w-max overflow-auto border-b px-4 py-2">
	<section class="flex h-full items-center justify-between gap-4">
		<H2>{title}</H2>
	</section>
</header>
