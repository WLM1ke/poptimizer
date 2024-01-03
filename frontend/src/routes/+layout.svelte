<script>
	import '../app.css';
	import { pageTitle } from '$lib/stores';
</script>

<svelte:head>
	<title>POptimizer - {$pageTitle}</title>
</svelte:head>

<slot />
