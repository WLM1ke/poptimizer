<script>
	import "../app.css";
	import { pageTitle } from "$lib/stores";
	import Logo from "$lib/components/Logo.svelte";
	import Header from "$lib/components/Header.svelte";
	import Sidebar from "$lib/components/sidebar/Sidebar.svelte";

	export let data;
</script>

<svelte:head>
	<title>POptimizer - {$pageTitle}</title>
</svelte:head>

<section class="grid h-screen w-screen grid-cols-layout grid-rows-layout">
	<Logo />
	<Header />
	<Sidebar accounts={data.accounts} />
	<slot />
</section>
