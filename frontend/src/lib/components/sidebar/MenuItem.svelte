<script lang="ts">
	import { pageTitle } from "$lib/stores/page";

	export let title: string;
	export let href: string | null = null;
	export let subItem = false;
</script>

{#if href}
	<a
		{href}
		class="text-text-muted hover:bg-bg-medium flex items-center gap-2 rounded-lg p-2 font-medium"
		class:px-4={subItem}
		class:bg-bg-medium={$pageTitle === title}
	>
		<slot />
		<span class="text-text-main">{title}</span>
	</a>
{:else}
	<div
		class="text-text-muted flex items-center gap-2 rounded-lg p-2 font-medium"
		class:px-4={subItem}
		class:bg-bg-medium={$pageTitle === title}
	>
		<slot />
		<span class="text-text-main">{title}</span>
	</div>
{/if}
