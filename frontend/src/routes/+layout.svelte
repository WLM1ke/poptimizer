<script>
	import "../app.css";
	import "@fontsource/roboto-condensed";
	import Logo from "$lib/components/Logo.svelte";
	import Header from "$lib/components/Header.svelte";
	import Sidebar from "$lib/components/sidebar/Sidebar.svelte";
	import { portfolio } from "$lib/persistent";
	import { pageTitle } from "$lib/stores";

	export let data;

	portfolio.set(data);
</script>

<svelte:head>
	<title>POptimizer - {$pageTitle}</title>
</svelte:head>

<section class="grid h-screen w-screen grid-cols-layout grid-rows-layout">
	<Logo />
	<Header />
	<Sidebar accounts={Object.keys(data.accounts)} />
	<slot />
</section>
