<script lang="ts">
	import Alert from "$lib/components/alerts/Alert.svelte";
	import { flip } from "svelte/animate";
	import { scale } from "svelte/transition";

	interface AlertData {
		id: number;
		info: boolean;
		msg: string;
	}

	let { alerts }: { alerts: AlertData[] } = $props();
</script>

<aside class="absolute bottom-0 right-0 p-2">
	<ol>
		{#each alerts as { id, info, msg } (id)}
			<li transition:scale animate:flip>
				<Alert {info} {msg}></Alert>
			</li>
		{/each}
	</ol>
</aside>
