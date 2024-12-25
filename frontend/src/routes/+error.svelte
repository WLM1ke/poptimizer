<svelte:options runes />

<script>
	import { state } from "$app/stores";
	import H2 from "$lib/components/H2.svelte";
</script>

<section class="flex h-full flex-col items-center justify-center">
	<H2 text={`${state.status}: ${state.error.message}`} />
</section>
