<script lang="ts">
	import SettingsIcon from "$lib/icons/SettingsIcon.svelte";
	import GitHubIcon from "$lib/icons/GitHubIcon.svelte";
	import ThemeToggler from "$lib/components/ThemeToggler.svelte";
</script>

<nav class="border-bg-medium flex w-full items-center justify-around border-t pt-2">
	<a href="/settings" class="hover:bg-bg-medium rounded-lg p-2" title="Settings">
		<SettingsIcon />
	</a>
	<ThemeToggler />
	<a
		href="https://github.com/WLM1ke/poptimizer"
		class="hover:bg-bg-medium rounded-lg p-2"
		title="Go to GitHub"
		target="_blank"
		rel="noopener"
	>
		<GitHubIcon />
	</a>
</nav>
