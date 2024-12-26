<script lang="ts">
	import SunIcon from "$lib/icons/SunIcon.svelte";
	import MoonIcon from "$lib/icons/MoonIcon.svelte";
	import SystemIcon from "$lib/icons/SystemIcon.svelte";
	import { theme } from "$lib/state/settings.svelte";

	let themeName = $derived(theme.get());
	document.querySelector("body")?.setAttribute("data-theme", theme.get());

	const toggleTheme = () => {
		theme.toggle();
		document.querySelector("body")?.setAttribute("data-theme", theme.get());
	};
</script>

<button class="hover:bg-bg-medium rounded-lg p-2" title={`Color theme: ${themeName}`} onclick={toggleTheme}>
	{#if themeName === "system"}
		<SystemIcon />
	{:else if themeName === "light"}
		<SunIcon />
	{:else if themeName === "dark"}
		<MoonIcon />
	{/if}
</button>
