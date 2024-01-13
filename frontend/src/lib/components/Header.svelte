<script lang="ts">
	import { pageTitle } from "$lib/stores/page";
</script>

<header class="min-w-max overflow-auto border-b border-bg-accent px-4 py-2">
	<section class="flex h-full items-center justify-between gap-4">
		<h1 class="text-xl font-semibold">{$pageTitle}</h1>
	</section>
</header>
