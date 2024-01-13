<script lang="ts">
	import { pageTitle } from "$lib/stores/page";
	import H2 from "$lib/components/base/H2.svelte";
</script>

<header class="min-w-max overflow-auto border-b border-bg-accent px-4 py-2">
	<section class="flex h-full items-center justify-between gap-4">
		<H2>{$pageTitle}</H2>
	</section>
</header>
