<script lang="ts">
	import SunIcon from "$lib/icons/SunIcon.svelte";
	import MoonIcon from "$lib/icons/MoonIcon.svelte";
	import SystemIcon from "$lib/icons/SystemIcon.svelte";
	import { theme } from "$lib/state/persistent.svelte";

	let themeName = $derived(theme.get());
	document.querySelector("body")?.setAttribute("data-theme", theme.get());

	const toggleTheme = () => {
		const current = themeName;
		const next = current === "system" ? "light" : current === "light" ? "dark" : "system";
		theme.set(next);
		document.querySelector("body")?.setAttribute("data-theme", next);
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
