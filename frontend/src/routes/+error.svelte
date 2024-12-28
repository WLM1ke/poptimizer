<svelte:options runes />

<script>
	import { page } from "$app/state";
	import H2 from "$lib/components/H2.svelte";
</script>

<section class="flex h-full flex-col items-center justify-center">
	<H2 text={`${page.status}: ${page.error.message}`} />
</section>
