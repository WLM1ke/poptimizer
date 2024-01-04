<script lang="ts">
	import InfoIcon from "$lib/icons/InfoIcon.svelte";
	import { pageTitle } from "$lib/stores";
</script>

<header class="min-w-max overflow-auto border-b border-bg-accent px-4 py-2">
	<section class="flex h-full items-center justify-between gap-4">
		<h1 class="text-xl font-semibold">{$pageTitle}</h1>
		<div class="flex items-center gap-1 rounded-lg border border-text-info p-2 text-text-info" role="alert">
			<InfoIcon />
			<span class="text-sm"> Info alert! Change a few things up and try submitting again. </span>
		</div>
	</section>
</header>
