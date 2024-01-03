<script>
	import '../app.css';
	import { pageTitle } from '$lib/stores';
	import Logo from '$lib/components/Logo.svelte';
</script>

<svelte:head>
	<title>POptimizer - {$pageTitle}</title>
</svelte:head>

<section class="grid-cols-layout grid-rows-layout grid h-screen w-screen">
	<Logo />
	<slot />
</section>
