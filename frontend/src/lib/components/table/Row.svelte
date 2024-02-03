<script lang="ts">
	export let muted: boolean = false;
</script>

<tr class:text-text-muted={muted}>
	<slot />
</tr>
