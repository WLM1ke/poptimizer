<script>
	import { page } from "$app/stores";
	import H2 from "$lib/components/H2.svelte";
</script>

<section class="flex h-full flex-col items-center justify-center">
	<H2>{#snippet text()}{$page.status}: {$page.error.message}{/snippet}</H2>
</section>
