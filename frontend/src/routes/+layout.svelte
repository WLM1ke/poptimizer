<script lang="ts">
	import "../app.css";
	import "@fontsource/roboto-condensed";
	import Sidebar from "./Sidebar.svelte";
	import { page } from "$app/state";
	import Alerts from "$lib/components/Alerts.svelte";
	import LogoIcon from "$lib/icons/LogoIcon.svelte";
	import H2 from "$lib/components/H2.svelte";
	import type { Snippet } from "svelte";
	import { loadSettingsFromLocalStorage } from "$lib/state/settings.svelte";
	import { type PageData } from "./$types";

	let { data, children }: { data: PageData; children: Snippet } = $props();

	loadSettingsFromLocalStorage();

	let title = $derived.by(() => {
		const path = decodeURI(page.url.pathname);
		if (path === "/") {
			return "Summary";
		}
		const lastSlash = path.lastIndexOf("/");

		return path[lastSlash + 1].toUpperCase() + path.substring(lastSlash + 2);
	});
</script>

<svelte:head>
	<title>POptimizer - {title}</title>
</svelte:head>

<section class="grid-cols-layout grid-rows-layout grid h-screen w-screen">
	<section class="border-bg-accent bg-bg-sidebar min-w-max border-r px-4 py-2">
		<a href="/" class="flex h-full items-center gap-2">
			<LogoIcon />
			<h1 class="font-logo text-3xl font-semibold tracking-tighter">poptimizer</h1>
		</a>
	</section>
	<header class="border-bg-accent min-w-max overflow-auto border-b px-4 py-2">
		<section class="flex h-full items-center justify-between gap-4">
			<H2 text={title} />
		</section>
	</header>
	<Sidebar accounts={data.portfolio.account_names} divTickers={data.divTickers} />
	<main class="overflow-scroll px-4 py-2">
		{@render children()}
		<Alerts />
	</main>
</section>
