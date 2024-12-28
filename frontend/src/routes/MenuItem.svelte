<script lang="ts">
	import { page } from "$app/state";
	import type { Snippet } from "svelte";

	let {
		icon,
		title,
		href = null,
		subItem = false
	}: { icon: Snippet; title: string; href?: string | null; subItem?: boolean } = $props();
	let selected = $derived(href === page.url.pathname);
</script>

{#if href}
	<a
		{href}
		class="flex items-center gap-2 rounded-lg p-2 font-medium text-text-muted hover:bg-bg-medium"
		class:px-4={subItem}
		class:bg-bg-medium={selected}
	>
		{@render icon()}
		<span class="text-text-main">{title}</span>
	</a>
{:else}
	<div
		class="flex items-center gap-2 rounded-lg p-2 font-medium text-text-muted"
		class:px-4={subItem}
		class:bg-bg-medium={selected}
	>
		{@render icon()}
		<span class="text-text-main">{title}</span>
	</div>
{/if}
