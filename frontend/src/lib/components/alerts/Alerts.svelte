<script lang="ts">
	import Alert from "$lib/components/alerts/Alert.svelte";
	import { alerts } from "$lib/stores/alerts";
</script>

<aside class="absolute bottom-0 right-0 p-2">
	<ol>
		{#each $alerts as { id, info, msg } (id)}
			<Alert {info} {msg}></Alert>
		{/each}
	</ol>
</aside>
