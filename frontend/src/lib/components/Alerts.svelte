<script lang="ts">
	import { flip } from "svelte/animate";
	import { scale } from "svelte/transition";
	import InfoIcon from "$lib/icons/InfoIcon.svelte";

	interface AlertData {
		id: number;
		msg: string;
		info: boolean;
	}

	let { alerts }: { alerts: AlertData[] } = $props();
</script>

{#snippet alert(info: boolean, msg: string)}
	<div
		class="m-2 flex items-center gap-1 rounded-lg border p-2"
		class:bg-bg-info={info}
		class:border-bdr-info={info}
		class:text-text-info={info}
		class:bg-bg-alert={!info}
		class:border-bdr-alert={!info}
		class:text-text-alert={!info}
		role="alert"
	>
		<InfoIcon />
		<span class="text-sm">{msg}</span>
	</div>
{/snippet}

<aside class="absolute bottom-0 right-0 p-2">
	<ol>
		{#each alerts.reverse() as { id, info, msg } (id)}
			<li transition:scale animate:flip>
				{@render alert(info, msg)}
			</li>
		{/each}
	</ol>
</aside>
