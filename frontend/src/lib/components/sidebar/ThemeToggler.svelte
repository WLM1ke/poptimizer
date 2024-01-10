<script context="module" lang="ts">
	import { persistent } from "$lib/stores/persistent";

	const theme = persistent<"system" | "light" | "dark">("theme", "system");
</script>

<script lang="ts">
	import SunIcon from "$lib/icons/SunIcon.svelte";
	import MoonIcon from "$lib/icons/MoonIcon.svelte";
	import SystemIcon from "$lib/icons/SystemIcon.svelte";

	document.querySelector("body")?.setAttribute("data-theme", $theme);

	const icons = {
		light: SunIcon,
		dark: MoonIcon,
		system: SystemIcon
	};

	const toggleTheme = () => {
		$theme = $theme === "system" ? "light" : $theme === "light" ? "dark" : "system";
		document.querySelector("body")?.setAttribute("data-theme", $theme);
	};
</script>

<button class="rounded-lg p-2 hover:bg-bg-medium" title={`Color theme: ${$theme}`} on:click={toggleTheme}>
	<svelte:component this={icons[$theme]} />
</button>
