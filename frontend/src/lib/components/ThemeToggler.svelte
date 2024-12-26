<script lang="ts">
	import SunIcon from "$lib/icons/SunIcon.svelte";
	import MoonIcon from "$lib/icons/MoonIcon.svelte";
	import SystemIcon from "$lib/icons/SystemIcon.svelte";
	import { theme } from "$lib/state/settings.svelte";

	document.querySelector("body")?.setAttribute("data-theme", theme.get());

	const toggleTheme = () => {
		theme.toggle();
		document.querySelector("body")?.setAttribute("data-theme", theme.get());
	};
</script>

<button class="hover:bg-bg-medium rounded-lg p-2" title={`Color theme: ${theme.get()}`} onclick={toggleTheme}>
	{#if theme.get() === "system"}
		<SystemIcon />
	{:else if theme.get() === "light"}
		<SunIcon />
	{:else if theme.get() === "dark"}
		<MoonIcon />
	{/if}
</button>
