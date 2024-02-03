<script>
	import { page } from "$app/stores";
	import H2 from "$lib/components/H2.svelte";
</script>

<section class="flex h-full flex-col items-center justify-center">
	<H2>{$page.error.message} {$page.status}</H2>
</section>
