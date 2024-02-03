<script lang="ts">
	import Alert from "$lib/components/alerts/Alert.svelte";
	import { alerts } from "$lib/components/alerts/alerts";
	import { flip } from "svelte/animate";
	import { scale } from "svelte/transition";
</script>

<aside class="absolute bottom-0 right-0 p-2">
	<ol>
		{#each $alerts as { id, info, msg } (id)}
			<li transition:scale animate:flip>
				<Alert {info} {msg}></Alert>
			</li>
		{/each}
	</ol>
</aside>
