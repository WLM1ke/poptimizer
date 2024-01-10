<script lang="ts">
	import { pageTitle } from "$lib/stores/page";

	export let title: string;
	export let href: string;
	export let subItem = false;
</script>

<li>
	<a
		{href}
		class="flex items-center gap-2 rounded-lg p-2 font-medium text-text-muted hover:bg-bg-medium"
		class:px-4={subItem}
		class:bg-bg-medium={$pageTitle === title}
	>
		<slot />
		<span class="text-text-main">{title}</span>
	</a>
</li>
