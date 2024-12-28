<script lang="ts">
	import SunIcon from "$lib/icons/SunIcon.svelte";
	import MoonIcon from "$lib/icons/MoonIcon.svelte";
	import SystemIcon from "$lib/icons/SystemIcon.svelte";
	import { theme } from "$lib/state/settings.svelte";

	document.querySelector("body")?.setAttribute("data-theme", theme.theme);

	const toggleTheme = () => {
		theme.toggle();
		document.querySelector("body")?.setAttribute("data-theme", theme.theme);
	};
</script>

<button class="hover:bg-bg-medium rounded-lg p-2" title={`Color theme: ${theme.theme}`} onclick={toggleTheme}>
	{#if theme.theme === "system"}
		<SystemIcon />
	{:else if theme.theme === "light"}
		<SunIcon />
	{:else if theme.theme === "dark"}
		<MoonIcon />
	{/if}
</button>
