<script lang="ts">
	import "../app.css";
	import "@fontsource/roboto-condensed";
	import Logo from "./Logo.svelte";
	import Header from "./Header.svelte";
	import Sidebar from "./Sidebar.svelte";
	import { page } from "$app/stores";
	import Alerts from "$lib/components/alerts/Alerts.svelte";
	import { alerts } from "$lib/state/states";

	let { data } = $props();

	let title = data.getTitle($page.url.pathname);
</script>

<svelte:head>
	<title>POptimizer - {title}</title>
</svelte:head>

<section class="grid-cols-layout grid-rows-layout grid h-screen w-screen">
	<Logo />
	<Header {title} />
	<Sidebar />
	<main class="overflow-scroll px-4 py-2">
		<slot />
		<Alerts alerts={alerts.getAlerts()} />
	</main>
</section>
