<script lang="ts">
	import SettingsIcon from "../../icons/SettingsIcon.svelte";
	import GitHubIcon from "../../icons/GitHubIcon.svelte";
	import ThemeToggler from "./ThemeToggler.svelte";
</script>

<nav class="flex w-full items-center justify-around border-t border-bg-medium pt-2">
	<a href="/settings" class="rounded-lg p-2 hover:bg-bg-medium" title="Settings">
		<SettingsIcon />
	</a>
	<ThemeToggler />
	<a
		href="https://github.com/WLM1ke/poptimizer"
		class="rounded-lg p-2 hover:bg-bg-medium"
		title="Go to GitHub"
		target="_blank"
		rel="noopener"
	>
		<GitHubIcon />
	</a>
</nav>
