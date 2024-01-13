<script>
	import "../app.css";
	import "@fontsource/roboto-condensed";
	import Logo from "$lib/components/Logo.svelte";
	import Header from "$lib/components/Header.svelte";
	import Sidebar from "$lib/components/sidebar/Sidebar.svelte";
	import Alerts from "$lib/components/alerts/Alerts.svelte";
	import { accounts, load } from "$lib/stores/portfolio";
	import { pageTitle } from "$lib/stores/page";
	import { onMount } from "svelte";

	onMount(() => {
		load();
	});
</script>

<svelte:head>
	<title>POptimizer - {$pageTitle}</title>
</svelte:head>

<section class="grid h-screen w-screen grid-cols-layout grid-rows-layout">
	<Logo />
	<Header />
	<Sidebar accounts={$accounts} />
	<slot />
	<Alerts />
</section>
