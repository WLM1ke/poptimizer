<script lang="ts">
	import "../app.css";
	import "@fontsource/roboto-condensed";
	import Logo from "./Logo.svelte";
	import Header from "./Header.svelte";
	import Sidebar from "./Sidebar.svelte";
	import { Alerts } from "$lib/components/alerts";
	import { page } from "$app/stores";

	export let data;

	$: title = data.getTitle($page.url.pathname);
</script>

<svelte:head>
	<title>POptimizer - {title}</title>
</svelte:head>

<section class="grid h-screen w-screen grid-cols-layout grid-rows-layout">
	<Logo />
	<Header {title} />
	<Sidebar />
	<main class="overflow-scroll px-4 py-2">
		<slot />
		<Alerts />
	</main>
</section>
