<script lang="ts">
	import "../app.css";
	import "@fontsource/roboto-condensed";
	import Logo from "./Logo.svelte";
	import Header from "./Header.svelte";
	import Sidebar from "./Sidebar.svelte";
	import { Alerts } from "$lib/components/base/alerts";
	import { page } from "$app/stores";
	import type { LayoutData } from "./$types";

	export let data: LayoutData;

	const setTitle = (pathname: string) => {
		const path = decodeURI(pathname);
		if (path === "/") {
			return "Summary";
		}
		const lastSlash = path.lastIndexOf("/");

		return path[lastSlash + 1].toUpperCase() + path.substring(lastSlash + 2);
	};

	$: title = setTitle($page.url.pathname);
</script>

<svelte:head>
	<title>POptimizer - {title}</title>
</svelte:head>

<section class="grid-cols-layout grid-rows-layout grid h-screen w-screen">
	<Logo />
	<Header {title} />
	<Sidebar tickers={data.tickers} />
	<main class="overflow-scroll px-4 py-2">
		<slot />
		<Alerts />
	</main>
</section>
