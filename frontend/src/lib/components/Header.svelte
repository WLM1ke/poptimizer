<script lang="ts">
	import InfoIcon from '$lib/icons/InfoIcon.svelte';
	import { pageTitle } from '$lib/stores';
</script>

<header class="border-bg-accent min-w-max overflow-auto border-b px-4 py-2">
	<section class="flex h-full items-center justify-between gap-4">
		<h1 class="text-xl font-semibold">{$pageTitle}</h1>
		<div
			class="border-text-info text-text-info flex items-center gap-1 rounded-lg border p-2"
			role="alert"
		>
			<InfoIcon />
			<span class="text-sm"> Info alert! Change a few things up and try submitting again. </span>
		</div>
	</section>
</header>
