<script lang="ts">
	import { page } from "$app/stores";

	export let title: string;
	export let href: string | null = null;
	export let subItem = false;

	$: selected = href === $page.url.pathname;
</script>

{#if href}
	<a
		{href}
		class="flex items-center gap-2 rounded-lg p-2 font-medium text-text-muted hover:bg-bg-medium"
		class:px-4={subItem}
		class:bg-bg-medium={selected}
	>
		<slot />
		<span class="text-text-main">{title}</span>
	</a>
{:else}
	<div
		class="flex items-center gap-2 rounded-lg p-2 font-medium text-text-muted"
		class:px-4={subItem}
		class:bg-bg-medium={selected}
	>
		<slot />
		<span class="text-text-main">{title}</span>
	</div>
{/if}
